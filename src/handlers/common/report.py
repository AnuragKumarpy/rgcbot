from datetime import datetime, timedelta
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ChatPermissions, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.report_service import ReportService
from src.utils.emojis import E_CHECK, E_CROSS, E_SHIELD, E_SIREN, animate_text

router = Router(name="common_report")


@router.message(Command("report", "admin"))
@router.message(F.text.regexp(r"(?i)\b@(admin|admins)\b"))
async def handle_report_trigger(
    message: Message,
    session: Optional[AsyncSession] = None,
):
    if not session or message.chat.id >= 0:
        return

    # Extract reason
    raw = message.text or message.caption or ""
    parts = raw.split(maxsplit=1)
    reason = parts[1].strip() if len(parts) > 1 and not parts[1].startswith("@") else "Rule violation reported by member"

    reporter = message.from_user
    if not reporter:
        return

    await ReportService.process_report(
        bot=message.bot,
        session=session,
        message=message,
        reporter=reporter,
        reason=reason,
    )


@router.callback_query(F.data.startswith("rep_act:"))
async def handle_report_action_callback(
    call: CallbackQuery,
    session: Optional[AsyncSession] = None,
):
    parts = call.data.split(":")
    action = parts[1]

    if action == "dismiss":
        await call.answer("Report dismissed.", show_alert=False)
        try:
            if call.message:
                await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return

    chat_id = int(parts[2])
    target_id = int(parts[3])

    try:
        if action == "ban":
            await call.bot.ban_chat_member(chat_id=chat_id, user_id=target_id)
            await call.answer("🔨 User has been banned from the group!", show_alert=True)
            if call.message:
                await call.message.reply(f"✅ Action executed: User <code>{target_id}</code> banned by admin.")

        elif action == "mute":
            until_date = datetime.utcnow() + timedelta(hours=24)
            await call.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=target_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date,
            )
            await call.answer("🔇 User has been muted for 24 hours!", show_alert=True)
            if call.message:
                await call.message.reply(f"✅ Action executed: User <code>{target_id}</code> muted for 24h.")

        elif action == "del":
            msg_id = target_id
            await call.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            await call.answer("🗑 Message deleted!", show_alert=True)
            if call.message:
                await call.message.reply(f"✅ Action executed: Message <code>{msg_id}</code> deleted.")

        if call.message:
            await call.message.edit_reply_markup(reply_markup=None)

    except Exception as e:
        logger.error(f"Report action failed: {e}")
        await call.answer(f"❌ Failed to execute action: {e}", show_alert=True)
