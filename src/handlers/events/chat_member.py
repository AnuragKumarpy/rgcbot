from typing import Optional

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters.chat_member_updated import IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import ActionType, CaptchaMode
from src.core.redis import redis_manager
from src.middlewares.ttl import schedule_auto_delete
from src.models.group import Group
from src.services.audit_service import AuditService
from src.services.captcha_service import CaptchaService
from src.utils.text_formatter import get_user_mention

router = Router(name="events_chat_member")


# 1. Handle new chat members joining via Message (Service message)
@router.message(F.new_chat_members)
async def handle_new_members(
    message: Message,
    db_group: Optional[Group] = None,
):
    if not message.new_chat_members:
        return

    chat_title = message.chat.title or "Group"
    log_channel = db_group.log_channel_id if db_group else None
    redis = await redis_manager.get_client()

    for new_user in message.new_chat_members:
        if new_user.is_bot:
            continue

        # Log User Join in Audit Channel
        await AuditService.log_action(
            bot=message.bot,
            chat_id=message.chat.id,
            chat_title=chat_title,
            target_user_id=new_user.id,
            target_user_name=new_user.full_name or new_user.first_name,
            admin_user_id=None,
            admin_user_name=None,
            action=ActionType.USER_JOIN,
            reason="Joined the group",
            channel_id=log_channel,
        )

        # Check if user already verified in DM via Join Request
        dm_key = f"rgcbot:verified_dm:{message.chat.id}:{new_user.id}"
        verified_in_dm = await redis.get(dm_key)
        if verified_in_dm:
            await redis.delete(dm_key)
            # Skip in-group captcha, send welcome directly
            if db_group and db_group.welcome_enabled:
                from src.services.welcome_service import WelcomeService
                await WelcomeService.send_welcome(message.bot, db_group, new_user)
            continue

        # Direct Join: Send in-group captcha if enabled
        if db_group and db_group.captcha_mode in (CaptchaMode.BUTTON.value, CaptchaMode.MATH.value):
            await CaptchaService.create_verification(
                bot=message.bot,
                group=db_group,
                new_user=new_user,
            )
        elif db_group and db_group.welcome_enabled:
            from src.services.welcome_service import WelcomeService
            await WelcomeService.send_welcome(message.bot, db_group, new_user)

    # Delete the service message "User joined the group" to keep chat clean if enabled
    if db_group and db_group.clean_service_enabled:
        try:
            await message.delete()
        except Exception:
            pass


# 2. Handle new chat members joining via ChatMemberUpdated (Invite link / direct join)
@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def handle_chat_member_joined(
    event: ChatMemberUpdated,
    db_group: Optional[Group] = None,
):
    new_user = event.new_chat_member.user
    if new_user.is_bot or not db_group:
        return

    chat_title = event.chat.title or "Group"
    log_channel = db_group.log_channel_id
    redis = await redis_manager.get_client()

    # Log User Join in Audit Channel
    await AuditService.log_action(
        bot=event.bot,
        chat_id=event.chat.id,
        chat_title=chat_title,
        target_user_id=new_user.id,
        target_user_name=new_user.full_name or new_user.first_name,
        admin_user_id=None,
        admin_user_name=None,
        action=ActionType.USER_JOIN,
        reason="Joined via link/invite",
        channel_id=log_channel,
    )

    # Check if user already verified in DM via Join Request
    dm_key = f"rgcbot:verified_dm:{event.chat.id}:{new_user.id}"
    verified_in_dm = await redis.get(dm_key)
    if verified_in_dm:
        await redis.delete(dm_key)
        # Skip in-group captcha, send welcome directly
        if db_group.welcome_enabled:
            from src.services.welcome_service import WelcomeService
            await WelcomeService.send_welcome(event.bot, db_group, new_user)
        return

    # Direct Join: Send in-group captcha if enabled
    if db_group.captcha_mode in (CaptchaMode.BUTTON.value, CaptchaMode.MATH.value):
        await CaptchaService.create_verification(
            bot=event.bot,
            group=db_group,
            new_user=new_user,
        )
    elif db_group.welcome_enabled:
        from src.services.welcome_service import WelcomeService
        await WelcomeService.send_welcome(event.bot, db_group, new_user)


# 3. Handle Member leaving via Message
@router.message(F.left_chat_member)
async def handle_left_member(
    message: Message,
    db_group: Optional[Group] = None,
):
    if not message.left_chat_member or message.left_chat_member.is_bot:
        return

    left_user = message.left_chat_member
    chat_title = message.chat.title or "Group"
    log_channel = db_group.log_channel_id if db_group else None

    await AuditService.log_action(
        bot=message.bot,
        chat_id=message.chat.id,
        chat_title=chat_title,
        target_user_id=left_user.id,
        target_user_name=left_user.full_name or left_user.first_name,
        admin_user_id=None,
        admin_user_name=None,
        action=ActionType.USER_LEAVE,
        reason="Left the group",
        channel_id=log_channel,
    )

    if db_group and db_group.clean_service_enabled:
        try:
            await message.delete()
        except Exception:
            pass


# 4. Handle in-group Captcha button callbacks
@router.callback_query(F.data.startswith("captcha:"))
async def handle_captcha_callback(
    call: CallbackQuery,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
):
    if not db_group or not call.data or not call.from_user or not call.message:
        return

    parts = call.data.split(":")
    mode = parts[1]
    chat_id = int(parts[2])
    target_user_id = int(parts[3])

    if call.from_user.id != target_user_id:
        await call.answer("❌ This verification challenge is for another member.", show_alert=True)
        return

    if mode == "btn":
        mention = get_user_mention(call.from_user)
        await CaptchaService.verify_success(
            bot=call.bot,
            group=db_group,
            user_id=target_user_id,
            user_mention=mention,
            message_id=call.message.message_id,
        )
        await call.answer("✅ Verification successful! Welcome to the group.")

    elif mode == "math":
        is_correct = parts[4] == "1"
        if is_correct:
            mention = get_user_mention(call.from_user)
            await CaptchaService.verify_success(
                bot=call.bot,
                group=db_group,
                user_id=target_user_id,
                user_mention=mention,
                message_id=call.message.message_id,
            )
            await call.answer("✅ Correct answer! Welcome!")
        else:
            await call.answer("❌ Incorrect answer! Please try again before time expires.", show_alert=True)
