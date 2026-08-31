from typing import Optional

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    ChatJoinRequest,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from loguru import logger

from src.core.enums import ActionType, CaptchaMode
from src.core.redis import redis_manager
from src.keyboards.captcha_kb import get_math_captcha_keyboard
from src.models.group import Group
from src.services.audit_service import AuditService
from src.utils.emojis import E_CHECK, E_DIAMOND, E_SHIELD, animate_text
from src.utils.text_formatter import escape_html

router = Router(name="events_join_request")


@router.chat_join_request()
async def handle_chat_join_request(
    event: ChatJoinRequest,
    db_group: Optional[Group] = None,
):
    """
    Triggered when a user clicks a join request invite link ('Request Admin Approval').
    Telegram allows the bot to send a direct message (DM) to the applicant.
    """
    chat_id = event.chat.id
    user_id = event.from_user.id
    chat_title = event.chat.title or "Group"
    user_name = event.from_user.first_name or "Applicant"

    logger.info(f"Received ChatJoinRequest from {user_id} for chat {chat_id}")

    # 1. If Captcha is OFF: Auto-approve immediately without DM verification
    if db_group and db_group.captcha_mode == CaptchaMode.OFF.value:
        try:
            await event.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            redis = await redis_manager.get_client()
            await redis.set(f"rgcbot:verified_dm:{chat_id}:{user_id}", "1", ex=300)

            await AuditService.log_action(
                bot=event.bot,
                chat_id=chat_id,
                chat_title=chat_title,
                target_user_id=user_id,
                target_user_name=event.from_user.full_name or user_name,
                admin_user_id=None,
                admin_user_name=None,
                action=ActionType.USER_JOIN,
                reason="Auto-approved join request (Captcha OFF)",
                channel_id=db_group.log_channel_id,
            )
            return
        except Exception as e:
            logger.warning(f"Failed to auto-approve join request for {user_id} in {chat_id}: {e}")
            return

    # 2. If Captcha is MATH: Send Math challenge in DM
    if db_group and db_group.captcha_mode == CaptchaMode.MATH.value:
        kb, question = get_math_captcha_keyboard(chat_id, user_id, 0)
        # Adapt callbacks for join_req prefix
        adapted_kb_rows = []
        for row in kb.inline_keyboard:
            new_row = []
            for b in row:
                cb_data = b.callback_data.replace("captcha:math:", "join_req:math:")
                new_row.append(
                    InlineKeyboardButton(
                        text=b.text,
                        callback_data=cb_data,
                        style=b.style,
                        icon_custom_emoji_id=b.icon_custom_emoji_id,
                    )
                )
            adapted_kb_rows.append(new_row)

        dm_text = animate_text(
            f"{E_SHIELD} <b>Security Verification</b>\n\n"
            f"Hello <b>{escape_html(user_name)}</b>!\n"
            f"You requested to join <b>{escape_html(chat_title)}</b>.\n\n"
            f"Please solve the math question below to verify you're human and enter the group:\n\n"
            f"👉 <b>{question}</b>"
        )
        try:
            await event.bot.send_message(
                chat_id=user_id,
                text=dm_text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=adapted_kb_rows),
            )
        except Exception as e:
            logger.warning(f"Could not send DM math captcha to {user_id}: {e}. Auto-approving.")
            try:
                await event.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
                redis = await redis_manager.get_client()
                await redis.set(f"rgcbot:verified_dm:{chat_id}:{user_id}", "1", ex=300)
            except Exception:
                pass
        return

    # 3. Default: Button "I am not a robot" in DM
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔘 I am not a robot (Verify to Join)",
                    callback_data=f"join_req:approve:{chat_id}:{user_id}",
                    style="success",
                    icon_custom_emoji_id="5237699328843200968",
                )
            ]
        ]
    )

    dm_text = animate_text(
        f"{E_SHIELD} <b>Security Verification</b>\n\n"
        f"Hello <b>{escape_html(user_name)}</b>!\n"
        f"You requested to join <b>{escape_html(chat_title)}</b>.\n\n"
        f"Please click the button below to verify you are human and enter the group."
    )

    try:
        await event.bot.send_message(
            chat_id=user_id,
            text=dm_text,
            parse_mode="HTML",
            reply_markup=kb,
        )
    except Exception as e:
        logger.warning(f"Could not send DM captcha to {user_id}: {e}. Auto-approving.")
        try:
            await event.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            redis = await redis_manager.get_client()
            await redis.set(f"rgcbot:verified_dm:{chat_id}:{user_id}", "1", ex=300)
        except Exception:
            pass


@router.callback_query(F.data.startswith("join_req:approve:"))
async def handle_join_request_approval(
    call: CallbackQuery,
    db_group: Optional[Group] = None,
):
    """
    Triggered when user clicks the verification button in DM.
    """
    parts = call.data.split(":")
    chat_id = int(parts[2])
    target_user_id = int(parts[3])

    if call.from_user.id != target_user_id:
        await call.answer("❌ This verification prompt is not for you.", show_alert=True)
        return

    try:
        # 1. Approve join request
        await call.bot.approve_chat_join_request(chat_id=chat_id, user_id=target_user_id)

        # 2. Mark in Redis that user was verified via DM so they won't get double-verified in group
        redis = await redis_manager.get_client()
        await redis.set(f"rgcbot:verified_dm:{chat_id}:{target_user_id}", "1", ex=300)

        success_text = animate_text(
            f"{E_CHECK} <b>Verification Successful!</b>\n\n"
            f"Your request has been approved. Welcome to the group! {E_DIAMOND}"
        )
        await call.message.edit_text(text=success_text, parse_mode="HTML")
        await call.answer("✅ Welcome to the group!")

        # 3. Audit log
        log_channel = db_group.log_channel_id if db_group else None
        chat_title = db_group.title if db_group else f"Chat {chat_id}"
        await AuditService.log_action(
            bot=call.bot,
            chat_id=chat_id,
            chat_title=chat_title,
            target_user_id=target_user_id,
            target_user_name=call.from_user.full_name or call.from_user.first_name,
            admin_user_id=None,
            admin_user_name=None,
            action=ActionType.CAPTCHA_PASS,
            reason="Approved via Private DM Join Request Verification",
            channel_id=log_channel,
        )
    except Exception as e:
        logger.warning(f"Failed to approve join request for {target_user_id} in {chat_id}: {e}")
        await call.message.edit_text(
            f"⚠️ Verification failed or invite request expired: {e}",
            parse_mode="HTML",
        )
        await call.answer("Error processing request.")


@router.callback_query(F.data.startswith("join_req:math:"))
async def handle_join_request_math_approval(
    call: CallbackQuery,
    db_group: Optional[Group] = None,
):
    """
    Triggered when user solves the math problem in DM.
    """
    parts = call.data.split(":")
    chat_id = int(parts[2])
    target_user_id = int(parts[3])
    is_correct = parts[4] == "1"

    if call.from_user.id != target_user_id:
        await call.answer("❌ This verification challenge is for another member.", show_alert=True)
        return

    if not is_correct:
        await call.answer("❌ Incorrect answer! Please try again.", show_alert=True)
        return

    try:
        # 1. Approve join request
        await call.bot.approve_chat_join_request(chat_id=chat_id, user_id=target_user_id)

        # 2. Mark in Redis that user was verified via DM so they won't get double-verified in group
        redis = await redis_manager.get_client()
        await redis.set(f"rgcbot:verified_dm:{chat_id}:{target_user_id}", "1", ex=300)

        success_text = animate_text(
            f"{E_CHECK} <b>Correct Answer & Verification Successful!</b>\n\n"
            f"Your request has been approved. Welcome to the group! {E_DIAMOND}"
        )
        await call.message.edit_text(text=success_text, parse_mode="HTML")
        await call.answer("✅ Correct answer! Welcome to the group!")

        # 3. Audit log
        log_channel = db_group.log_channel_id if db_group else None
        chat_title = db_group.title if db_group else f"Chat {chat_id}"
        await AuditService.log_action(
            bot=call.bot,
            chat_id=chat_id,
            chat_title=chat_title,
            target_user_id=target_user_id,
            target_user_name=call.from_user.full_name or call.from_user.first_name,
            admin_user_id=None,
            admin_user_name=None,
            action=ActionType.CAPTCHA_PASS,
            reason="Approved via Private DM Math Join Request Verification",
            channel_id=log_channel,
        )
    except Exception as e:
        logger.warning(f"Failed to approve join request for {target_user_id} in {chat_id}: {e}")
        await call.message.edit_text(
            f"⚠️ Verification failed or invite request expired: {e}",
            parse_mode="HTML",
        )
        await call.answer("Error processing request.")
