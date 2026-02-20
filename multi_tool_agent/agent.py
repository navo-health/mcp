from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, SseConnectionParams

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

toolset = McpToolset(
    connection_params=SseConnectionParams(url="http://localhost:8080/sse")
)


def _load_skill_instructions() -> str:
    """Read all SKILL.md files from the skills/ directory.

    Used as an InstructionProvider callable so the agent picks up
    new/removed skills on every invocation without a restart.
    """
    parts = []
    if SKILLS_DIR.is_dir():
        for skill_folder in sorted(SKILLS_DIR.iterdir()):
            skill_md = skill_folder / "SKILL.md"
            if skill_md.exists():
                parts.append(skill_md.read_text())
    return "\n\n".join(parts) if parts else "No skills are currently loaded."


root_agent = Agent(
    name="skill_agent",
    model="gemini-2.5-flash",
    instruction=_load_skill_instructions(),
    tools=[toolset],
)


def build_agent():
    return root_agent
