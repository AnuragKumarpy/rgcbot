from datetime import datetime
from typing import Optional
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import TTLType
from src.middlewares.ttl import reply_with_ttl
from src.models.user import User
from src.utils.text_formatter import escape_html, get_user_mention, mention_html
from src.utils.time_parser import format_duration

router = Router(name="fun_afk")


@router.message(Command("afk"))
async def handle_afk_command(message: Message, db_user: Optional[User] = None):
    if not db_user:
        return

    parts = message.text.split(maxsplit=1)
    reason = parts[1].strip() if len(parts) > 1 else "Away From Keyboard"

    db_user.is_afk = True
    db_user.afk_reason = reason
    db_user.afk_since = datetime.utcnow()

    mention = get_user_mention(message.from_user)
    text = f"💤 {mention} is now <b>AFK</b>.\n<b>Reason:</b> {escape_html(reason)}"
    await reply_with_ttl(message, text, ttl_type=TTLType.FUN)


@router.message(F.text, ~F.text.startswith("/"))
async def handle_afk_listener(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_user: Optional[User] = None,
):
    """
    1. If user who sent message was AFK, remove AFK and welcome back.
    2. If message mentions/replies to a user who is AFK, inform the chat.
    """
    # 1. Clear AFK if sender is AFK
    if db_user and db_user.is_afk:
        afk_duration = ""
        if db_user.afk_since:
            seconds = int((datetime.utcnow() - db_user.afk_since).total_seconds())
            afk_duration = f" (was away for {format_duration(seconds)})"

        db_user.is_afk = False
        db_user.afk_reason = None
        db_user.afk_since = None

        mention = get_user_mention(message.from_user)
        await reply_with_ttl(
            message,
            f"👋 Welcome back {mention}! You are no longer AFK{afk_duration}.",
            ttl_type=TTLType.FUN,
            custom_ttl=10,
            delete_trigger=False,
        )

    # 2. Check if replied user is AFK
    if session and message.reply_to_message and message.reply_to_message.from_user:
        replied_tg = message.reply_to_message.from_user
        if not replied_tg.is_bot and replied_tg.id != (
            message.from_user.id if message.from_user else 0
        ):
            res = await session.execute(select(User).where(User.user_id == replied_tg.id))
            replied_user = res.scalar_one_or_none()
            if replied_user and replied_user.is_afk:
                since_str = ""
                if replied_user.afk_since:
                    sec = int((datetime.utcnow() - replied_user.afk_since).total_seconds())
                    since_str = f" ({format_duration(sec)} ago)"

                mention = mention_html(replied_user.user_id, replied_user.first_name)
                text = (
                    f"💤 {mention} is currently <b>AFK</b>{since_str}.\n"
                    f"<b>Reason:</b> {escape_html(replied_user.afk_reason or 'Away')}"
                )
                await reply_with_ttl(
                    message, text, ttl_type=TTLType.FUN, custom_ttl=15, delete_trigger=False
                )
