from fastmcp import FastMCP 
from datetime import datetime
from zoneinfo import ZoneInfo

mcp = FastMCP(host="127.0.0.1", port=8080)

@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Adds two numbers together."""
    return a + b

@mcp.tool()

def get_current_datetime(timezone: str = "UTC") -> str:
    """
    Returns the current date and time for a given timezone.
    
    Args:
        timezone (str): IANA timezone name (default: "UTC")
                        e.g. "Asia/Singapore", "America/New_York"
    
    Returns:
        str: Current datetime in ISO format.
    """
    try:
        now = datetime.now(ZoneInfo(timezone))
        return now.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return "Invalid timezone. Please provide a valid IANA timezone (e.g., 'UTC', 'Asia/Singapore')."


if __name__ == "__main__":
    mcp.run(transport="sse")
