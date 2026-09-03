from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import TTLType
from src.middlewares.ttl import reply_with_ttl
from src.models.group import Group
from src.models.user import User
from src.services.stats_service import StatsService
from src.services.quote_service import QuoteService
from src.utils.emojis import E_CROWN, E_WARN, animate_text
from src.utils.target_resolver import resolve_target
from src.utils.text_formatter import mention_html

router = Router(name="admin_history")


def _format_history_caption(history: dict) -> str:
    user: Optional[User] = history.get("user")
    group: Optional[Group] = history.get("group")
    moderation_logs = history.get("moderation_logs", [])
    profile_changes = history.get("profile_changes", [])

    user_label = QuoteService.clean_emoji_text(user.full_name if user else "Member")
    group_label = QuoteService.clean_emoji_text(group.title if group else "Group")

    lines = [
        f"{E_CROWN} <b>Member History — {user_label}</b>",
        f"<i>Scope: {group_label}</i>\n",
    ]

    if moderation_logs:
        lines.append(f"{E_WARN} <b>Moderation Actions:</b>")
        for log in moderation_logs[:8]:
            action = log.action_type.replace("_", " ").title()
            duration = f" ({log.duration_seconds}s)" if log.duration_seconds else ""
            reason = f" — {QuoteService.clean_emoji_text(log.reason)}" if log.reason else ""
            lines.append(f"• <b>{action}</b>{duration}{reason}")
    else:
        lines.append("<i>No moderation actions recorded for this member in this group.</i>")

    if profile_changes:
        lines.append(f"\n{E_CROWN} <b>Username / Name Changes:</b>")
        for change in profile_changes[:8]:
            before = change.old_username or change.old_first_name or "Unknown"
            after = change.new_username or change.new_first_name or "Unknown"
            lines.append(f"• <code>{before}</code> → <code>{after}</code>")
    else:
        lines.append("\n<i>No username or profile changes recorded yet.</i>")

    return animate_text("\n".join(lines))


@router.message(Command("history", "audit", "memberhistory"))
async def handle_user_history_cmd(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
):
    if not session or not db_group:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not is_admin:
        await reply_with_ttl(
            message,
            "❌ You do not have permission to inspect member history.",
            ttl_type=TTLType.MODERATION,
        )
        return

    target = await resolve_target(message, session=session, bot=message.bot)
    if not target:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> <code>/history &lt;reply | @username | ID&gt;</code>",
            ttl_type=TTLType.MODERATION,
        )
        return

    history = await StatsService.get_group_user_history(
        session=session,
        chat_id=db_group.chat_id,
        user_id=target.user_id,
        limit=12,
    )

    caption = _format_history_caption(history)
    mention = mention_html(target.user_id, target.first_name)

    await reply_with_ttl(
        message,
        f"{caption}\n\n<b>Target:</b> {mention} [<code>{target.user_id}</code>]",
        ttl_type=TTLType.MODERATION,
    )