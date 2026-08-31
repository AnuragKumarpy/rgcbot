import re
from datetime import timedelta
from typing import Optional

TIME_REGEX = re.compile(r"(\d+)\s*([smhdw]|sec|second|min|minute|hr|hour|d|day|w|week)s?", re.IGNORECASE)

MULTIPLIERS = {
    "s": 1,
    "sec": 1,
    "second": 1,
    "m": 60,
    "min": 60,
    "minute": 60,
    "h": 3600,
    "hr": 3600,
    "hour": 3600,
    "d": 86400,
    "day": 86400,
    "w": 604800,
    "week": 604800,
}


def parse_time_string(time_str: str) -> Optional[int]:
    """
    Parses strings like '1d', '2h30m', '45s', '1 week' into total seconds.
    Returns None if no valid time components found.
    """
    if not time_str or not time_str.strip():
        return None

    matches = TIME_REGEX.findall(time_str)
    if not matches:
        # Check if plain integer is provided (treat as seconds)
        if time_str.strip().isdigit():
            return int(time_str.strip())
        return None

    total_seconds = 0
    for value, unit in matches:
        unit_lower = unit.lower()
        multiplier = MULTIPLIERS.get(unit_lower, 1)
        total_seconds += int(value) * multiplier

    return total_seconds if total_seconds > 0 else None


def format_duration(seconds: int) -> str:
    """
    Formats seconds into a human-readable string like '2 days, 3 hours' or '45 seconds'.
    """
    if seconds <= 0:
        return "0s"

    td = timedelta(seconds=seconds)
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 and (days == 0 and hours == 0):
        parts.append(f"{secs}s")

    return " ".join(parts) if parts else f"{seconds}s"
