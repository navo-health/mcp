from datetime import datetime
from zoneinfo import ZoneInfo


def get_current_datetime(timezone: str = "UTC") -> str:
    """
    Returns the current date and time for a given timezone.

    Args:
        timezone: IANA timezone name (default: "UTC")
                  e.g. "Asia/Singapore", "America/New_York"

    Returns:
        Current datetime as a formatted string.
    """
    try:
        now = datetime.now(ZoneInfo(timezone))
        return now.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return "Invalid timezone. Please provide a valid IANA timezone (e.g., 'UTC', 'Asia/Singapore')."
