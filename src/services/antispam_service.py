import re
import time
from typing import Optional, Tuple
from aiogram import Bot
from aiogram.types import Message
from loguru import logger
from src.config.settings import settings
from src.core.enums import ActionType
from src.core.redis import redis_manager
from src.models.group import Group
from src.services.audit_service import AuditService
from src.services.moderation_service import ModerationService
from src.utils.text_formatter import get_user_mention

# Regex patterns for link and telegram invite detection
URL_REGEX = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
TG_INVITE_REGEX = re.compile(
    r"(t\.me/(joinchat|\+)|telegram\.me/(joinchat|\+)|t\.me/[a-zA-Z0-9_]{5,})",
    re.IGNORECASE,
)


class AntiSpamService:
    @classmethod
    async def check_flood(
        cls, bot: Bot, group: Group, message: Message
    ) -> bool:
        """
        Returns True if message triggered flood control and was handled.
        """
        if not group.antispam_enabled or not message.from_user:
            return False

        chat_id = group.chat_id
        user_id = message.from_user.id
        limit = group.antiflood_limit or settings.default_flood_limit
        window = getattr(group, "antiflood_window_sec", None) or settings.default_flood_window



        try:
            redis = await redis_manager.get_client()
            key = f"rgcbot:antiflood:{chat_id}:{user_id}"
            current_time = time.time()

            # Add current timestamp to Redis Sorted Set
            await redis.zadd(key, {str(current_time): current_time})
            # Remove timestamps outside window
            await redis.zremrangebyscore(key, 0, current_time - window)
            # Count recent messages
            count = await redis.zcard(key)
            await redis.expire(key, window + 2)

            if count > limit:
                # Trigger flood mute for 10 minutes (600s)
                logger.info(f"Flood detected for user {user_id} in {chat_id} ({count} msgs in {window}s)")
                await redis.delete(key)

                # Delete flood message
                try:
                    await message.delete()
                except Exception:
                    pass

                # Mute user
                mute_duration = 600
                from src.models.user import User
                target_user = User(
                    user_id=user_id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                )
                from src.core.database import db
                async for session in db.get_session():
                    await ModerationService.mute_user(
                        bot=bot,
                        session=session,
                        group=group,
                        target_user=target_user,
                        admin_user=None,
                        reason=f"Auto-Flood Defense ({count} msgs in {window}s)",
                        duration_seconds=mute_duration,
                    )

                # Send temporary warning notice
                mention = get_user_mention(message.from_user)
                warn_text = (
                    f"🛑 {mention} has been muted for <b>10 minutes</b> for message flooding."
                )
                from src.middlewares.ttl import reply_with_ttl
                await reply_with_ttl(
                    message, warn_text, custom_ttl=10, delete_trigger=False
                )
                return True
        except Exception as e:
            logger.warning(f"Error checking flood for user {user_id} in {chat_id}: {e}")

        return False

    @classmethod
    async def check_links_and_forwards(
        cls, bot: Bot, group: Group, message: Message
    ) -> bool:
        """
        Checks for unauthorized links or forwards if enabled in group settings.
        Returns True if violation was found and message was deleted.
        """
        if not message.from_user:
            return False

        user_id = message.from_user.id
        chat_id = group.chat_id
        text = message.text or message.caption or ""

        # 1. Forward protection
        if group.antiforward_enabled and message.forward_origin:
            try:
                await message.delete()
                mention = get_user_mention(message.from_user)
                from src.middlewares.ttl import reply_with_ttl
                await reply_with_ttl(
                    message,
                    f"⚠️ {mention}, forwarded messages are not allowed in this group.",
                    custom_ttl=8,
                    delete_trigger=False,
                )
                return True
            except Exception:
                pass

        # 2. Link & Telegram Invite protection
        if group.antilink_enabled and text:
            if URL_REGEX.search(text) or TG_INVITE_REGEX.search(text):
                try:
                    await message.delete()
                    mention = get_user_mention(message.from_user)
                    from src.middlewares.ttl import reply_with_ttl
                    await reply_with_ttl(
                        message,
                        f"⚠️ {mention}, posting links or invites is restricted in this group.",
                        custom_ttl=8,
                        delete_trigger=False,
                    )
                    return True
                except Exception:
                    pass

        return False
