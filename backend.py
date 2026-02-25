from datetime import datetime
from pathlib import Path
from typing import Optional

# Load env before any google imports
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from elasticsearch import Elasticsearch, NotFoundError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel

from multi_tool_agent.agent import build_agent

ES_INDEX = "skills"

# ── Elasticsearch setup ─────────────────────────────────────────────
es = Elasticsearch("http://localhost:9200")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Agent state (mutable so we can rebuild dynamically) ─────────────
_state = {"runner": None}


def _load_skill_instructions_from_es() -> str:
    """Load skill instructions from Elasticsearch."""
    try:
        _ensure_es_index()
        result = es.search(
            index=ES_INDEX,
            body={"query": {"match_all": {}}, "size": 1000, "sort": [{"name": "asc"}]},
        )
        skill_names = [hit["_source"].get("name", "unknown") for hit in result["hits"]["hits"]]
        print(f"[ES Query] Found {len(skill_names)} skills: {skill_names}")
        parts = []
        for hit in result["hits"]["hits"]:
            description = hit["_source"].get("description", "")
            if description:
                parts.append(description)
        if not parts:
            return "You have no skills loaded. Tell the user to upload skills first."

        # Make instructions explicit for the LLM
        skill_list = ", ".join(skill_names)
        instructions = f"""You are a helpful assistant with the following skills: {skill_list}.

You MUST use these skills to help users. Here are your skill descriptions:

{chr(10).join(parts)}

IMPORTANT: You can perform ALL the skills listed above. Do not say you cannot do something if it's in your skills."""
        return instructions
    except Exception as exc:
        print(f"Warning: Failed to load skills from ES — {exc}")
        return "You have no skills loaded. Tell the user to upload skills first."


def _create_runner() -> InMemoryRunner:
    """Create a fresh runner with current skills from Elasticsearch."""
    instructions = _load_skill_instructions_from_es()
    print(f"[_create_runner] Instructions: {instructions[:200]}...")
    agent = build_agent(instructions)
    runner = InMemoryRunner(agent=agent, app_name="skills_gateway")
    print("[_create_runner] Fresh runner created")
    return runner


def _rebuild_agent():
    """Rebuild the agent and runner with current skills from Elasticsearch."""
    _state["runner"] = _create_runner()
    print(f"[_rebuild_agent] Global runner updated to: {id(_state['runner'])}")


def get_runner() -> InMemoryRunner:
    """Get the current runner, building if needed."""
    if _state["runner"] is None:
        _rebuild_agent()
    runner = _state["runner"]
    print(f"[get_runner] Returning runner: {id(runner)}")
    return runner


@app.on_event("startup")
def startup():
    """Initialize the agent."""
    _rebuild_agent()


# ── Request / Response models ────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class SkillCreateRequest(BaseModel):
    name: str
    description: str
    code: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────

def _ensure_es_index():
    """Create the skills index if it doesn't exist."""
    if not es.indices.exists(index=ES_INDEX):
        es.indices.create(
            index=ES_INDEX,
            body={
                "mappings": {
                    "properties": {
                        "name": {"type": "keyword"},
                        "description": {"type": "text"},
                        "code": {"type": "text"},
                        "created_at": {"type": "date"},
                    }
                }
            },
        )


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Skills Gateway running"}


@app.get("/debug/instructions")
def debug_instructions():
    """Debug endpoint to see current agent instructions."""
    return {"instructions": _load_skill_instructions_from_es()}


@app.post("/chat")
async def chat(request: ChatRequest):
    runner = get_runner()
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=request.message)],
    )

    # Try to use existing session, or create a new one
    session_id = None
    if request.session_id:
        # Check if session still exists (may be gone after agent rebuild)
        existing = await runner.session_service.get_session(
            app_name="skills_gateway",
            user_id="user1",
            session_id=request.session_id,
        )
        if existing:
            session_id = request.session_id

    if not session_id:
        session = await runner.session_service.create_session(
            app_name="skills_gateway",
            user_id="user1",
        )
        session_id = session.id

    final_response = ""
    async for event in runner.run_async(
        user_id="user1",
        session_id=session_id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    final_response = part.text

    return {"response": final_response, "session_id": session_id}


def _extract_description(text: str, max_length: int = 150) -> str:
    """Return the first meaningful paragraph line from SKILL.md content."""
    in_frontmatter = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if len(stripped) > max_length:
            return stripped[:max_length] + "..."
        return stripped
    return ""


def _get_skills_list():
    """Get all skills from Elasticsearch as a list."""
    result = es.search(
        index=ES_INDEX,
        body={"query": {"match_all": {}}, "size": 1000, "sort": [{"name": "asc"}]},
    )
    skills = []
    for hit in result["hits"]["hits"]:
        source = hit["_source"]
        skills.append({
            "name": source["name"],
            "has_skill_md": bool(source.get("description")),
            "has_skill_py": bool(source.get("code")),
            "description": _extract_description(source.get("description", "")),
        })
    return skills


@app.get("/skills")
def list_skills():
    """List all skills from Elasticsearch."""
    _ensure_es_index()
    try:
        return {"skills": _get_skills_list()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list skills: {exc}")


@app.post("/skills")
async def create_skill(request: SkillCreateRequest):
    """Create a new skill in Elasticsearch and sync to disk."""
    _ensure_es_index()

    # Check if skill already exists
    if es.exists(index=ES_INDEX, id=request.name):
        raise HTTPException(status_code=409, detail=f"Skill '{request.name}' already exists")

    # Store in Elasticsearch
    doc = {
        "name": request.name,
        "description": request.description,
        "code": request.code,
        "created_at": datetime.utcnow().isoformat(),
    }
    es.index(index=ES_INDEX, id=request.name, document=doc, refresh=True)
    print(f"[create_skill] Stored skill '{request.name}' in ES")

    # Rebuild agent to pick up new skill
    _rebuild_agent()
    return {"status": "created", "name": request.name, "skills": _get_skills_list()}


@app.delete("/skills/{name}")
async def delete_skill(name: str):
    """Delete a skill from Elasticsearch (keeps files on disk)."""
    _ensure_es_index()

    # Check if skill exists in ES
    try:
        es.delete(index=ES_INDEX, id=name, refresh=True)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")

    # Rebuild agent to remove deleted skill
    _rebuild_agent()
    return {"status": "deleted", "name": name, "skills": _get_skills_list()}
