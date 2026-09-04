import asyncio
import random
from typing import Optional
from aiogram import Bot
from aiogram.types import ChatPermissions, Message, User as TgUser
from loguru import logger
from src.core.enums import ActionType, CaptchaMode
from src.core.redis import redis_manager
from src.keyboards.captcha_kb import get_button_captcha_keyboard, get_math_captcha_keyboard
from src.middlewares.ttl import reply_with_ttl, schedule_auto_delete
from src.models.group import Group
from src.services.audit_service import AuditService
from src.utils.text_formatter import get_user_mention


class CaptchaService:
    @classmethod
    async def create_verification(
        cls, bot: Bot, group: Group, new_user: TgUser
    ) -> Optional[Message]:
        """
        Restricts the new user and sends a verification challenge message.
        """
        chat_id = group.chat_id
        user_id = new_user.id

        # 1. Restrict user from sending messages
        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
            )
        except Exception as e:
            logger.warning(f"Could not restrict new user {user_id} in {chat_id}: {e}")

        # 2. Prepare Challenge Keyboard
        mention = get_user_mention(new_user)
        timeout = 90  # Strict 90s TTL for in-group verification challenge

        from src.utils.emojis import E_SHIELD

        if group.captcha_mode == CaptchaMode.MATH.value:
            # Random seed
            keyboard, question = get_math_captcha_keyboard(chat_id, user_id, 0)
            text = (
                f"{E_SHIELD} <b>Security Verification</b>\n\n"
                f"Welcome {mention}! To speak in this group, please solve the math problem below within <b>{timeout}s</b>:\n\n"
                f"👉 <b>{question}</b>"
            )
        else:
            keyboard = get_button_captcha_keyboard(chat_id, user_id)
            text = (
                f"{E_SHIELD} <b>Security Verification</b>\n\n"
                f"Welcome {mention}! To speak in this group, please press the button below within <b>{timeout}s</b> to verify you're human."
            )

        # 3. Send message
        try:
            sent_msg = await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            # Store challenge in Redis
            redis = await redis_manager.get_client()
            key = f"rgcbot:captcha:{chat_id}:{user_id}"
            await redis.set(key, str(sent_msg.message_id), ex=timeout)

            # Launch background timeout checker
            asyncio.create_task(
                cls._timeout_checker(
                    bot=bot,
                    chat_id=chat_id,
                    user_id=user_id,
                    user_name=new_user.first_name,
                    chat_title=group.title,
                    message_id=sent_msg.message_id,
                    timeout=timeout,
                    log_channel_id=group.log_channel_id,
                )
            )

            return sent_msg
        except Exception as e:
            logger.error(f"Failed to send captcha for {user_id} in {chat_id}: {e}")
            return None

    @classmethod
    async def verify_success(
        cls, bot: Bot, group: Group, user_id: int, user_mention: str, message_id: int
    ):
        """
        Lifts restrictions and deletes captcha message.
        """
        # Restore permissions
        try:
            await bot.restrict_chat_member(
                chat_id=group.chat_id,
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_audios=True,
                    can_send_documents=True,
                    can_send_photos=True,
                    can_send_videos=True,
                    can_send_video_notes=True,
                    can_send_voice_notes=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_invite_users=True,
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to unrestrict user {user_id} in {group.chat_id}: {e}")

        # Delete captcha challenge message
        try:
            await bot.delete_message(chat_id=group.chat_id, message_id=message_id)
        except Exception:
            pass

        # Clear Redis key
        redis = await redis_manager.get_client()
        await redis.delete(f"rgcbot:captcha:{group.chat_id}:{user_id}")

        # Mark user verified in DB
        try:
            from src.core.database import db
            from src.models.user import User
            from sqlalchemy import select
            from datetime import datetime
            async for session in db.get_session():
                u_res = await session.execute(select(User).where(User.user_id == user_id))
                u = u_res.scalars().first()
                if u:
                    u.is_dm_active = True
                    u.has_started_bot = True
                    u.last_active_at = datetime.utcnow()
                    await session.commit()
                break
        except Exception as e:
            logger.debug(f"Note updating verified user in DB: {e}")

        # Send audit log
        await AuditService.log_action(
            bot=bot,
            chat_id=group.chat_id,
            chat_title=group.title,
            target_user_id=user_id,
            target_user_name=f"User {user_id}",
            admin_user_id=None,
            admin_user_name=None,
            action=ActionType.CAPTCHA_PASS,
            reason="Passed verification challenge",
            channel_id=group.log_channel_id,
        )

        # Send welcome message with TTL
        if group.welcome_enabled:
            from src.services.welcome_service import WelcomeService

            try:
                cm = await bot.get_chat_member(group.chat_id, user_id)
                tg_user = cm.user
            except Exception:
                tg_user = TgUser(id=user_id, is_bot=False, first_name="Member")
            await WelcomeService.send_welcome(bot, group, tg_user)

    @classmethod
    async def _timeout_checker(
        cls,
        bot: Bot,
        chat_id: int,
        user_id: int,
        user_name: str,
        chat_title: str,
        message_id: int,
        timeout: int,
        log_channel_id: Optional[int],
    ):
        await asyncio.sleep(timeout + 2)
        redis = await redis_manager.get_client()
        key = f"rgcbot:captcha:{chat_id}:{user_id}"

        # If key still exists, user never solved it
        exists = await redis.get(key)
        if exists:
            await redis.delete(key)
            # Kick user
            try:
                await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                await bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
                logger.info(f"User {user_id} kicked from {chat_id} due to captcha timeout.")
            except Exception as e:
                logger.warning(f"Failed to kick user {user_id} on captcha timeout: {e}")

            # Delete message
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception:
                pass

            # Log audit
            await AuditService.log_action(
                bot=bot,
                chat_id=chat_id,
                chat_title=chat_title,
                target_user_id=user_id,
                target_user_name=user_name,
                admin_user_id=None,
                admin_user_name=None,
                action=ActionType.CAPTCHA_FAIL,
                reason="Failed to complete verification in time",
                channel_id=log_channel_id,
            )
