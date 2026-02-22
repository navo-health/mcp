import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

# Load env before any google imports
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import httpx
from elasticsearch import Elasticsearch, NotFoundError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel

from multi_tool_agent.agent import build_agent

SKILLS_DIR = Path(__file__).parent / "skills"
MCP_RELOAD_URL = "http://127.0.0.1:8080/reload"
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

agent = build_agent()
runner = InMemoryRunner(agent=agent, app_name="skills_gateway")


@app.on_event("startup")
def import_existing_skills():
    """On startup, import any existing disk skills into Elasticsearch."""
    try:
        if not es.ping():
            print("Warning: Elasticsearch not available at startup, skipping import")
            return
        _ensure_es_index()
        if not SKILLS_DIR.is_dir():
            return
        for folder in SKILLS_DIR.iterdir():
            if not folder.is_dir() or folder.name.startswith("."):
                continue
            skill_md = folder / "SKILL.md"
            skill_py = folder / "skill.py"
            if not skill_md.exists():
                continue
            # Only import if not already in ES
            if not es.exists(index=ES_INDEX, id=folder.name):
                doc = {
                    "name": folder.name,
                    "description": skill_md.read_text(),
                    "code": skill_py.read_text() if skill_py.exists() else None,
                    "created_at": datetime.utcnow().isoformat(),
                }
                es.index(index=ES_INDEX, id=folder.name, document=doc)
                print(f"Imported skill '{folder.name}' into Elasticsearch")
    except Exception as exc:
        print(f"Warning: Failed to import skills to Elasticsearch — {exc}")


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


def _sync_skills_to_disk():
    """Sync all skills from Elasticsearch to the file system for the agent."""
    _ensure_es_index()
    try:
        result = es.search(index=ES_INDEX, body={"query": {"match_all": {}}, "size": 1000})
        for hit in result["hits"]["hits"]:
            skill = hit["_source"]
            skill_dir = SKILLS_DIR / skill["name"]
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(skill.get("description", ""))
            if skill.get("code"):
                (skill_dir / "skill.py").write_text(skill["code"])
    except Exception as exc:
        print(f"Warning: Failed to sync skills to disk — {exc}")


async def _reload_mcp():
    """Tell the MCP server to re-scan skills/."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(MCP_RELOAD_URL, timeout=5.0)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"Warning: MCP reload failed — {exc}")


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Skills Gateway running"}


@app.post("/chat")
async def chat(request: ChatRequest):
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=request.message)],
    )

    if request.session_id:
        session_id = request.session_id
    else:
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


@app.get("/skills")
def list_skills():
    """List all skills from Elasticsearch."""
    _ensure_es_index()
    try:
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
        return {"skills": skills}
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
    es.index(index=ES_INDEX, id=request.name, document=doc)

    # Sync to disk for the agent
    skill_dir = SKILLS_DIR / request.name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(request.description)
    if request.code:
        (skill_dir / "skill.py").write_text(request.code)

    await _reload_mcp()
    return {"status": "created", "name": request.name}


@app.delete("/skills/{name}")
async def delete_skill(name: str):
    """Delete a skill from Elasticsearch and disk."""
    _ensure_es_index()

    # Check if skill exists in ES
    try:
        es.delete(index=ES_INDEX, id=name)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")

    # Remove from disk
    skill_dir = SKILLS_DIR / name
    if skill_dir.exists():
        shutil.rmtree(skill_dir)

    await _reload_mcp()
    return {"status": "deleted", "name": name}
