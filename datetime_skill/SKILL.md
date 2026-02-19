# Current Date & Time Skill

You can provide the current date and time.

Tool available:

- get_current_datetime(timezone: str = "UTC")

This tool returns the current date and time in the specified timezone.

---

## When to Use This Tool

Use this tool when the user asks:

- "What time is it?"
- "What's the current date?"
- "Current time in Singapore"
- "What time is it in New York?"
- "Today's date"
- Any request related to current date or time

---

## How to Use It

- If the user specifies a location, convert it to a valid IANA timezone if possible.
  Examples:
  - Singapore → Asia/Singapore
  - New York → America/New_York
  - London → Europe/London

- If no timezone is specified, use the default ("UTC").

---

## Response Format

After calling the tool:

Respond clearly and naturally.

Example:

"The current date and time in Asia/Singapore is 2026-02-19 14:32:10 SGT."

---

## Important Rules

- Always call the tool for real-time information.
- Do NOT guess the time.
- Do NOT fabricate dates.
- If the tool returns an invalid timezone error, politely inform the user.
