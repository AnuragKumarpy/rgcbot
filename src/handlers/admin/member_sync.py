from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import TTLType
from src.middlewares.ttl import reply_with_ttl
from src.services.member_sync_service import MemberSyncService
from src.utils.emojis import E_CHECK, E_ROCKET, E_SPARKLES, animate_text

router = Router(name="admin_member_sync")


@router.message(Command("syncmembers", "sync", "loadmembers", "fetchmembers"))
async def handle_sync_members(
    message: Message,
    is_admin: bool = False,
    session: Optional[AsyncSession] = None,
):
    if not is_admin:
        await reply_with_ttl(message, "❌ Admin rights required.", ttl_type=TTLType.MODERATION)
        return
    if not session or message.chat.id >= 0:
        return

    status_msg = await reply_with_ttl(
        message,
        animate_text(
            f"{E_ROCKET} <b>Syncing group members...</b>\n<i>Fetching full member roster from Telegram...</i>"
        ),
        ttl_type=TTLType.MODERATION,
        delete_trigger=False,
    )

    # 1. Try MTProto sync first
    count = await MemberSyncService.sync_group_members_mtproto(session, message.chat.id)

    if count > 0:
        text = animate_text(
            f"{E_CHECK} <b>Group Members Synchronized!</b>\n\n"
            f"• <b>Total Members Synced:</b> <code>{count:,}</code>\n"
            "✨ <i>All members are now indexed for tagging, stats, and karma.</i>"
        )
    else:
        # Fallback to admins
        adm_count = await MemberSyncService.sync_admins_fallback(
            message.bot, session, message.chat.id
        )
        text = animate_text(
            f"{E_SPARKLES} <b>Admins Synchronized!</b> (<code>{adm_count}</code> admins)\n\n"
            "<i>Regular members will be automatically indexed as they join and send messages.</i>"
        )

    await reply_with_ttl(message, text, ttl_type=TTLType.MODERATION)
