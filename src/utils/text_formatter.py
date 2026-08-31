import html
from typing import Any, Optional


def escape_html(text: Optional[str]) -> str:
    """Escapes HTML special characters to prevent injection."""
    if text is None:
        return ""
    return html.escape(str(text))


def mention_html(user_id: int, name: str) -> str:
    """Creates a clickable HTML user mention."""
    safe_name = escape_html(str(name)) if name else f"User {user_id}"
    return f'<a href="tg://user?id={user_id}">{safe_name}</a>'


def get_user_mention(user: Any) -> str:
    """Creates an HTML mention from an aiogram User, DB User, or ID."""
    if user is None:
        return "Unknown User"

    if isinstance(user, (int, str)) and str(user).isdigit():
        uid = int(user)
        return mention_html(uid, f"User {uid}")

    user_id = getattr(user, "user_id", None) or getattr(user, "id", None)
    if user_id is None:
        return "User"

    first_name = getattr(user, "first_name", "") or ""
    last_name = getattr(user, "last_name", "") or ""
    full_name = getattr(user, "full_name", None) or f"{first_name} {last_name}".strip()
    name = full_name or first_name or f"User {user_id}"

    return mention_html(int(user_id), name)


def get_karma_tier(karma: int) -> str:
    """Returns an elite title and minimalist rank symbol based on karma score."""
    if karma >= 5000:
        return "◈ Grandmaster"
    elif karma >= 2500:
        return "◆ Ascendant"
    elif karma >= 1000:
        return "✦ Vanguard"
    elif karma >= 500:
        return "▲ Master"
    elif karma >= 200:
        return "■ Specialist"
    elif karma >= 50:
        return "▫ Contributor"
    elif karma >= 10:
        return "▪ Active"
    elif karma >= 0:
        return "• Initiate"
    else:
        return "✕ Restricted"


def format_card(title: str, fields: list[tuple[str, str]], footer: Optional[str] = None) -> str:
    """Formats a structured, elite monospace card layout with animated custom emojis."""
    from src.utils.emojis import animate_text
    lines = [f"<b>{animate_text(title)}</b>\n"]
    for label, val in fields:
        lines.append(f"• <b>{animate_text(str(label))}:</b> {animate_text(str(val))}")
    if footer:
        lines.append(f"\n<i>{animate_text(footer)}</i>")
    return "\n".join(lines)
