import asyncio
from typing import Optional
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from src.core.enums import TTLType
from src.middlewares.ttl import reply_with_ttl
from src.utils.emojis import E_NOTE, E_SHIELD

router = Router(name="admin_purge")


@router.message(Command("del", "delete"))
async def handle_del(message: Message, can_delete: bool = False):
    if not can_delete:
        await reply_with_ttl(
            message,
            "❌ You do not have permission to delete messages.",
            ttl_type=TTLType.MODERATION,
        )
        return

    if message.reply_to_message:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id, message_id=message.reply_to_message.message_id
            )
            await message.delete()
        except Exception:
            pass
    else:
        await reply_with_ttl(
            message,
            "⚠️ Reply to the message you want to delete with <code>/del</code>.",
            ttl_type=TTLType.MODERATION,
        )


@router.message(Command("purge"))
async def handle_purge(message: Message, can_delete: bool = False):
    if not can_delete:
        await reply_with_ttl(
            message,
            "❌ You do not have permission to purge messages.",
            ttl_type=TTLType.MODERATION,
        )
        return

    if not message.reply_to_message:
        await reply_with_ttl(
            message,
            "⚠️ Reply to the starting message you want to purge from.",
            ttl_type=TTLType.MODERATION,
        )
        return

    from_msg_id = message.reply_to_message.message_id
    to_msg_id = message.message_id
    chat_id = message.chat.id

    msg_ids = list(range(from_msg_id, to_msg_id + 1))
    if len(msg_ids) > 100:
        msg_ids = msg_ids[-100:]  # Telegram batch delete limit is 100

    deleted_count = 0
    try:
        await message.bot.delete_messages(chat_id=chat_id, message_ids=msg_ids)
        deleted_count = len(msg_ids)
    except Exception:
        # Fallback to single delete
        for mid in msg_ids:
            try:
                await message.bot.delete_message(chat_id=chat_id, message_id=mid)
                deleted_count += 1
            except Exception:
                pass

    notice = await message.answer(f"🧹 Purged <b>{deleted_count}</b> messages.")

    # Audit log
    if message.from_user:
        from src.services.audit_service import AuditService
        from src.core.enums import ActionType

        await AuditService.log_action(
            bot=message.bot,
            chat_id=chat_id,
            chat_title=message.chat.title or "Group",
            target_user_id=message.from_user.id,
            target_user_name=message.from_user.full_name or message.from_user.first_name,
            admin_user_id=message.from_user.id,
            admin_user_name=message.from_user.full_name or message.from_user.first_name,
            action=ActionType.PURGE,
            reason=f"Purged {deleted_count} messages",
        )

    await asyncio.sleep(4)
    try:
        await notice.delete()
    except Exception:
        pass


@router.message(Command("pin"))
async def handle_pin(message: Message, can_pin: bool = False):
    if not can_pin:
        await reply_with_ttl(
            message,
            "❌ You do not have permission to pin messages in this group.",
            ttl_type=TTLType.MODERATION,
        )
        return

    if not message.reply_to_message:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> Reply to any message with <code>/pin [loud | silent]</code> to pin it.",
            ttl_type=TTLType.MODERATION,
        )
        return

    raw_text = (message.text or "").lower()
    notify = "loud" in raw_text or "notify" in raw_text

    try:
        await message.bot.pin_chat_message(
            chat_id=message.chat.id,
            message_id=message.reply_to_message.message_id,
            disable_notification=not notify,
        )
        mode_str = "with notification" if notify else "silently"
        await reply_with_ttl(
            message,
            f"📌 <b>Message Pinned:</b> Successfully pinned {mode_str}.",
            ttl_type=TTLType.MODERATION,
        )
    except Exception as e:
        await reply_with_ttl(
            message, f"❌ Failed to pin message: {e}", ttl_type=TTLType.MODERATION
        )


@router.message(Command("unpin"))
async def handle_unpin(message: Message, can_pin: bool = False):
    if not can_pin:
        await reply_with_ttl(
            message,
            "❌ You do not have permission to unpin messages in this group.",
            ttl_type=TTLType.MODERATION,
        )
        return

    try:
        if message.reply_to_message:
            await message.bot.unpin_chat_message(
                chat_id=message.chat.id,
                message_id=message.reply_to_message.message_id,
            )
            await reply_with_ttl(
                message, "📌 <b>Message Unpinned:</b> Replied message was unpinned.", ttl_type=TTLType.MODERATION
            )
        else:
            await message.bot.unpin_chat_message(chat_id=message.chat.id)
            await reply_with_ttl(
                message, "📌 <b>Message Unpinned:</b> Latest pinned message was unpinned.", ttl_type=TTLType.MODERATION
            )
    except Exception as e:
        await reply_with_ttl(
            message, f"❌ Failed to unpin message: {e}", ttl_type=TTLType.MODERATION
        )


@router.message(Command("unpinall"))
async def handle_unpinall(message: Message, can_pin: bool = False):
    if not can_pin:
        await reply_with_ttl(
            message,
            "❌ You do not have permission to unpin messages in this group.",
            ttl_type=TTLType.MODERATION,
        )
        return

    try:
        await message.bot.unpin_all_chat_messages(chat_id=message.chat.id)
        await reply_with_ttl(
            message, "📌 <b>All Pinned Messages Cleared:</b> All pinned messages have been unpinned.", ttl_type=TTLType.MODERATION
        )
    except Exception as e:
        await reply_with_ttl(
            message, f"❌ Failed to unpin all messages: {e}", ttl_type=TTLType.MODERATION
        )
