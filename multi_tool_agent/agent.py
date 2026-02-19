from pathlib import Path
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import (McpToolset, SseConnectionParams)

# Path to your skill directory

toolset = McpToolset(connection_params=SseConnectionParams(url="http://localhost:8080/sse"))

# with open("simple_addition_skill/SKILL.md", "r") as f:
#     skills = f.read()

def load_skills(skill_paths):
    combined = []
    for path in skill_paths:
        with open(path, "r") as f:
            combined.append(f.read())
    return "\n\n".join(combined)


skills = load_skills([
    "skills/datetime_skill/SKILL.md",
    "skills/simple_addition_skill/SKILL.md"
])

# Initialize agent with SkillToolset
root_agent = Agent(
    name="skill_agent",
    model="gemini-2.5-flash",
    instruction=skills,
    tools=[toolset],
)

def build_agent():
    return root_agent