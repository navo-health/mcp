from google.adk.agents import Agent


def build_agent(instructions: str = "No skills are currently loaded."):
    """Build a fresh agent with the provided skill instructions."""
    print(f"[build_agent] Creating agent with instructions: {instructions[:100]}...")
    return Agent(
        name="skill_agent",
        model="gemini-2.5-flash",
        instruction=instructions,
    )
