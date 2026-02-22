import importlib.util
import inspect
import sys
from pathlib import Path

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

SKILLS_DIR = Path(__file__).parent / "skills"

mcp = FastMCP()

# Track registered tool names so we can cleanly remove them on reload
_registered_tools: list[str] = []


def load_skills():
    """Scan skills/ directories and register each skill.py's public functions as tools."""
    for skill_folder in sorted(SKILLS_DIR.iterdir()):
        if not skill_folder.is_dir():
            continue
        skill_file = skill_folder / "skill.py"
        if not skill_file.exists():
            continue

        module_name = f"skill_{skill_folder.name}"

        # Clear cached module so re-imports pick up code changes
        if module_name in sys.modules:
            del sys.modules[module_name]

        spec = importlib.util.spec_from_file_location(module_name, skill_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        for attr_name in dir(module):
            func = getattr(module, attr_name)
            if (
                inspect.isfunction(func)
                and not attr_name.startswith("_")
                and func.__module__ == module_name
            ):
                mcp.tool()(func)
                _registered_tools.append(attr_name)
                print(f"Registered tool: {attr_name}")


def reload_skills():
    """Remove all previously registered tools, then re-scan and re-register."""
    for name in _registered_tools:
        try:
            mcp.remove_tool(name)
        except Exception:
            pass
    _registered_tools.clear()
    load_skills()
    print(f"Reload complete — {len(_registered_tools)} tools registered")


@mcp.custom_route("/reload", methods=["POST"])
async def reload_endpoint(request: Request) -> JSONResponse:
    """HTTP endpoint to trigger a hot-reload of all skills."""
    reload_skills()
    return JSONResponse({"status": "reloaded", "tools": list(_registered_tools)})


# Initial load
load_skills()

if __name__ == "__main__":
    mcp.run(transport="sse", host="127.0.0.1", port=8080)
