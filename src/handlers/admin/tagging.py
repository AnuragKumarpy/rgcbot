from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import TTLType
from src.middlewares.ttl import reply_with_ttl
from src.services.mention_service import MentionService
from src.utils.emojis import E_CHECK, E_CROSS, E_FIRE, E_ROCKET, E_SPARKLES, animate_text

router = Router(name="admin_tagging")


def parse_tag_text(message: Message, prefix_len: int = 1) -> str:
    """Extracts custom message text following the command or tag trigger."""
    raw = message.text or message.caption or ""
    parts = raw.split(maxsplit=prefix_len)
    return parts[prefix_len].strip() if len(parts) > prefix_len else ""


@router.message(Command("tagstop", "stopall", "cancel"))
@router.message(F.text.lower().in_(["@cancel", "/cancel", "!cancel"]))
async def handle_stop_tagging(
    message: Message,
    is_admin: bool = False,
):
    if not is_admin:
        await reply_with_ttl(message, "❌ Admin permissions required.", ttl_type=TTLType.MODERATION)
        return

    stopped = MentionService.stop_tagging(message.chat.id)
    if stopped:
        await reply_with_ttl(
            message,
            animate_text(f"{E_CHECK} <b>Tagging loop stopped successfully.</b>"),
            ttl_type=TTLType.MODERATION,
        )
    else:
        await reply_with_ttl(
            message,
            "<i>No active tagging task running in this chat.</i>",
            ttl_type=TTLType.MODERATION,
        )


@router.callback_query(F.data.startswith("tag_stop:"))
async def handle_tag_stop_callback(
    call: CallbackQuery,
    is_admin: bool = False,
):
    if not is_admin:
        await call.answer("❌ Only admins can stop the tagging loop.", show_alert=True)
        return

    chat_id = int(call.data.split(":")[1])
    stopped = MentionService.stop_tagging(chat_id)

    if stopped:
        await call.answer("Tagging cancelled!")
        try:
            if call.message:
                await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
    else:
        await call.answer("No active tagging in progress.", show_alert=False)


# 1. Active Chatters Tagging (Must match before @all)
@router.message(Command("tagactive", "allactive", "active"))
@router.message(F.text.regexp(r"(?i)^@allactive\b") | F.text.regexp(r"(?i)^@active\b"))
async def handle_tag_active(
    message: Message,
    is_admin: bool = False,
    session: Optional[AsyncSession] = None,
):
    """Active tagging: tags only active members (zero-risk emoji masking)."""
    if not is_admin:
        await reply_with_ttl(
            message,
            "❌ <b>Admin-Only:</b> Only group administrators can use mass tagging commands.",
            ttl_type=TTLType.MODERATION,
        )
        return
    if not session or message.chat.id >= 0:
        return

    custom_text = parse_tag_text(message, prefix_len=1)
    members = await MentionService.get_target_members(
        message.bot, session, message.chat.id, active_only=True
    )

    if not members:
        await reply_with_ttl(
            message, "<i>No active members recorded recently.</i>", ttl_type=TTLType.MODERATION
        )
        return

    MentionService.start_tagging_task(
        bot=message.bot,
        chat_id=message.chat.id,
        members=members,
        custom_text=custom_text,
        mode="secret",
        reply_to_message_id=None,
    )


# 2. Reply Tagging
@router.message(Command("rtagall", "rall"))
@router.message(F.text.regexp(r"(?i)^@rall\b"))
async def handle_reply_tag_all(
    message: Message,
    is_admin: bool = False,
    session: Optional[AsyncSession] = None,
):
    """Reply tagging: tags all members replying directly to the target message (zero-risk emoji masking)."""
    if not is_admin:
        await reply_with_ttl(
            message,
            "❌ <b>Admin-Only:</b> Only group administrators can use mass tagging commands.",
            ttl_type=TTLType.MODERATION,
        )
        return
    if not session or message.chat.id >= 0:
        return

    target_reply_id = (
        message.reply_to_message.message_id if message.reply_to_message else message.message_id
    )
    custom_text = parse_tag_text(message, prefix_len=1)
    members = await MentionService.get_target_members(
        message.bot, session, message.chat.id, active_only=False
    )

    if not members:
        await reply_with_ttl(
            message, "<i>No members found in group record.</i>", ttl_type=TTLType.MODERATION
        )
        return

    MentionService.start_tagging_task(
        bot=message.bot,
        chat_id=message.chat.id,
        members=members,
        custom_text=custom_text,
        mode="secret",
        reply_to_message_id=target_reply_id,
    )


# 3. All Members Tagging
@router.message(Command("tagall", "all", "stagall", "sall", "secrettag"))
@router.message(F.text.regexp(r"(?i)^@all\b") | F.text.regexp(r"(?i)^@sall\b"))
async def handle_tag_all(
    message: Message,
    is_admin: bool = False,
    session: Optional[AsyncSession] = None,
):
    if not is_admin:
        await reply_with_ttl(
            message,
            "❌ <b>Admin-Only:</b> Only group administrators can use mass tagging commands.",
            ttl_type=TTLType.MODERATION,
        )
        return
    if not session or message.chat.id >= 0:
        return

    custom_text = parse_tag_text(message, prefix_len=1)
    members = await MentionService.get_target_members(
        message.bot, session, message.chat.id, active_only=False
    )

    if not members:
        await reply_with_ttl(
            message, "<i>No members found in group record.</i>", ttl_type=TTLType.MODERATION
        )
        return

    # Zero-risk secret emoji tagging is always enforced
    MentionService.start_tagging_task(
        bot=message.bot,
        chat_id=message.chat.id,
        members=members,
        custom_text=custom_text,
        mode="secret",
        reply_to_message_id=None,
    )
