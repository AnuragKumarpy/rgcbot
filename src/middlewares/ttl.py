import time
from typing import Optional, Union
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from loguru import logger
from src.config.settings import settings
from src.core.enums import TTLType
from src.core.redis import redis_manager


async def schedule_auto_delete(chat_id: int, message_id: int, ttl_seconds: int):
    """
    Registers a message into the Redis Sorted Set (ZSET) to be deleted after ttl_seconds.
    """
    if ttl_seconds <= 0:
        return

    try:
        redis = await redis_manager.get_client()
        delete_at = time.time() + ttl_seconds
        member = f"{chat_id}:{message_id}"
        await redis.zadd(settings.redis_ttl_queue_key, {member: delete_at})
        logger.debug(f"Scheduled auto-delete for {member} in {ttl_seconds}s (at {delete_at})")
    except Exception as e:
        logger.error(f"Failed to schedule auto-delete for {chat_id}:{message_id}: {e}")


async def reply_with_ttl(
    message: Message,
    text: str,
    ttl_type: TTLType = TTLType.GENERAL,
    custom_ttl: Optional[int] = None,
    delete_trigger: bool = True,
    reply_markup: Optional[
        Union[InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove]
    ] = None,
    parse_mode: Optional[str] = "HTML",
) -> Optional[Message]:
    """
    Sends a reply to a user message and automatically schedules both the bot's response
    and optionally the user's trigger message for auto-deletion based on group TTL settings.
    """
    # Determine TTL seconds
    ttl_seconds = custom_ttl
    if ttl_seconds is None:
        if ttl_type == TTLType.MODERATION:
            ttl_seconds = settings.default_mod_ttl
        elif ttl_type == TTLType.FUN:
            ttl_seconds = settings.default_fun_ttl
        elif ttl_type == TTLType.RULES:
            ttl_seconds = settings.default_rules_ttl
        elif ttl_type == TTLType.WARN:
            ttl_seconds = settings.default_warn_ttl
        elif ttl_type == TTLType.NONE:
            ttl_seconds = 0
        else:
            ttl_seconds = settings.default_general_ttl

    try:
        from src.utils.emojis import animate_text

        animated_text = animate_text(text)
        try:
            sent_msg = await message.answer(
                text=animated_text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        except Exception:
            sent_msg = await message.answer(
                text=animated_text,
                reply_markup=reply_markup,
                parse_mode=None,
            )

        if ttl_seconds and ttl_seconds > 0:
            # Schedule bot message for deletion
            await schedule_auto_delete(
                chat_id=sent_msg.chat.id,
                message_id=sent_msg.message_id,
                ttl_seconds=ttl_seconds,
            )

            # Also schedule user trigger command if enabled
            if delete_trigger and message.chat.type in ("group", "supergroup"):
                await schedule_auto_delete(
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                    ttl_seconds=ttl_seconds,
                )

        return sent_msg
    except Exception as e:
        logger.error(f"Failed to send and track TTL reply: {e}")
        return None


async def reply_photo_with_ttl(
    message: Message,
    photo: any,
    caption: str,
    ttl_type: TTLType = TTLType.GENERAL,
    custom_ttl: Optional[int] = None,
    delete_trigger: bool = True,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = "HTML",
) -> Optional[Message]:
    """
    Sends a photo reply to a user message and schedules both the photo and trigger for auto-deletion.
    """
    ttl_seconds = custom_ttl
    if ttl_seconds is None:
        if ttl_type == TTLType.MODERATION:
            ttl_seconds = settings.default_mod_ttl
        elif ttl_type == TTLType.FUN:
            ttl_seconds = settings.default_fun_ttl
        elif ttl_type == TTLType.RULES:
            ttl_seconds = settings.default_rules_ttl
        elif ttl_type == TTLType.WARN:
            ttl_seconds = settings.default_warn_ttl
        elif ttl_type == TTLType.NONE:
            ttl_seconds = 0
        else:
            ttl_seconds = settings.default_general_ttl

    try:
        from src.utils.emojis import animate_text

        animated_caption = animate_text(caption)
        sent_msg = await message.reply_photo(
            photo=photo,
            caption=animated_caption,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )

        if ttl_seconds and ttl_seconds > 0:
            await schedule_auto_delete(
                chat_id=sent_msg.chat.id,
                message_id=sent_msg.message_id,
                ttl_seconds=ttl_seconds,
            )
            if delete_trigger and message.chat.type in ("group", "supergroup"):
                await schedule_auto_delete(
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                    ttl_seconds=ttl_seconds,
                )

        return sent_msg
    except Exception as e:
        logger.error(f"Failed to send photo reply with TTL: {e}")
        return None
