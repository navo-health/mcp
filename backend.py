import os
import shutil
from pathlib import Path
from typing import Optional

# Load env before any google imports
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "multi_tool_agent" / ".env")

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel

from multi_tool_agent.agent import build_agent

SKILLS_DIR = Path(__file__).parent / "skills"
MCP_RELOAD_URL = "http://127.0.0.1:8080/reload"

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


# ── Request / Response models ────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class SkillCreateRequest(BaseModel):
    name: str
    description: str
    code: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────

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


def _extract_description(path: Path, max_length: int = 150) -> str:
    """Return the first meaningful paragraph line from a SKILL.md file."""
    try:
        in_frontmatter = False
        for line in path.read_text().splitlines():
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
    except OSError:
        pass
    return ""


@app.get("/skills")
def list_skills():
    skills = []
    if SKILLS_DIR.is_dir():
        for folder in sorted(SKILLS_DIR.iterdir()):
            if not folder.is_dir() or folder.name.startswith("."):
                continue
            skill_md = folder / "SKILL.md"
            skill_py = folder / "skill.py"
            skills.append({
                "name": folder.name,
                "has_skill_md": skill_md.exists(),
                "has_skill_py": skill_py.exists(),
                "description": _extract_description(skill_md) if skill_md.exists() else "",
            })
    return {"skills": skills}


@app.post("/skills")
async def create_skill(request: SkillCreateRequest):
    skill_dir = SKILLS_DIR / request.name
    if skill_dir.exists():
        raise HTTPException(status_code=409, detail=f"Skill '{request.name}' already exists")

    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(request.description)
    if request.code:
        (skill_dir / "skill.py").write_text(request.code)

    await _reload_mcp()
    return {"status": "created", "name": request.name}


@app.delete("/skills/{name}")
async def delete_skill(name: str):
    skill_dir = SKILLS_DIR / name
    if not skill_dir.exists():
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")

    shutil.rmtree(skill_dir)

    await _reload_mcp()
    return {"status": "deleted", "name": name}
