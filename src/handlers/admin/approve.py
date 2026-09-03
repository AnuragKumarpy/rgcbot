from typing import Optional
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import TTLType
from src.middlewares.ttl import reply_with_ttl
from src.services.approval_service import ApprovalService
from src.utils.emojis import E_CHECK, E_WARN

router = Router(name="admin_approve")


async def _resolve_target(message: Message):
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].strip().lstrip("-").isdigit():
        try:
            return await message.bot.get_chat(int(args[1].strip()))
        except Exception:
            return None
    return None


@router.message(Command("approve"))
async def handle_approve_cmd(message: Message, session: Optional[AsyncSession] = None):
    if not session or message.chat.id >= 0:
        return
    target = await _resolve_target(message)
    if not target:
        await reply_with_ttl(
            message, f"{E_WARN} Reply to a user or provide their user ID to approve.", ttl_type=TTLType.MODERATION
        )
        return
    parts = message.text.split(maxsplit=2)
    reason = parts[1] if message.reply_to_message and len(parts) > 1 else (parts[2] if len(parts) > 2 else None)

    created = await ApprovalService.approve(session, message.chat.id, target.id, message.from_user.id, reason)
    if created:
        await reply_with_ttl(
            message,
            f"{E_CHECK} <b>{target.full_name}</b> is now approved — exempt from link/media filters here.",
            ttl_type=TTLType.MODERATION,
        )
    else:
        await reply_with_ttl(message, f"{E_WARN} That user is already approved.", ttl_type=TTLType.MODERATION)


@router.message(Command("unapprove"))
async def handle_unapprove_cmd(message: Message, session: Optional[AsyncSession] = None):
    if not session or message.chat.id >= 0:
        return
    target = await _resolve_target(message)
    if not target:
        await reply_with_ttl(
            message, f"{E_WARN} Reply to a user or provide their user ID to unapprove.", ttl_type=TTLType.MODERATION
        )
        return
    removed = await ApprovalService.unapprove(session, message.chat.id, target.id)
    text = (
        f"{E_CHECK} Approval revoked for <b>{target.full_name}</b>."
        if removed
        else f"{E_WARN} That user wasn't approved."
    )
    await reply_with_ttl(message, text, ttl_type=TTLType.MODERATION)


@router.message(Command("approved"))
async def handle_list_approved_cmd(message: Message, session: Optional[AsyncSession] = None):
    if not session or message.chat.id >= 0:
        return
    approved = await ApprovalService.list_approved(session, message.chat.id)
    if not approved:
        await reply_with_ttl(message, "No approved users in this chat.", ttl_type=TTLType.MODERATION)
        return
    lines = [f"• <code>{a.user_id}</code>" + (f" — {a.reason}" if a.reason else "") for a in approved]
    await reply_with_ttl(message, "<b>Approved users:</b>\n" + "\n".join(lines), ttl_type=TTLType.MODERATION)
