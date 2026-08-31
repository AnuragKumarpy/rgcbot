from typing import Optional
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import TTLType
from src.middlewares.ttl import reply_with_ttl
from src.models.group import Group
from src.models.member import GroupMember
from src.models.user import User
from src.utils.text_formatter import escape_html, get_karma_tier, get_user_mention

router = Router(name="fun_profile")


@router.message(Command("profile", "me"))
async def handle_profile(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    db_user: Optional[User] = None,
):
    if not session or not message.from_user:
        return

    target_user = db_user
    target_tg_user = message.from_user

    if message.reply_to_message and message.reply_to_message.from_user:
        target_tg_user = message.reply_to_message.from_user
        res = await session.execute(
            select(User).where(User.user_id == target_tg_user.id)
        )
        target_user = res.scalar_one_or_none() or db_user

    if not target_user:
        return

    # Fetch group member stats if in group
    warns = 0
    max_warns = 3
    if db_group:
        res_m = await session.execute(
            select(GroupMember).where(
                GroupMember.chat_id == db_group.chat_id,
                GroupMember.user_id == target_user.user_id,
            )
        )
        member = res_m.scalar_one_or_none()
        warns = member.warnings_count if member else 0
        max_warns = db_group.max_warns

    mention = get_user_mention(target_tg_user)
    tier = get_karma_tier(target_user.karma)
    title_flair = (
        f"🏷️ <b>Title:</b> {escape_html(target_user.custom_title)}\n"
        if target_user.custom_title
        else ""
    )

    text = (
        f"👤 <b>Member Profile</b>\n\n"
        f"Name: {mention}\n"
        f"ID: <code>{target_user.user_id}</code>\n"
        f"{title_flair}"
        f"🏅 <b>Rank:</b> {tier}\n"
        f"🌟 <b>Karma:</b> {target_user.karma} pts\n"
        f"💰 <b>Coins:</b> {target_user.coins}\n"
        f"🔥 <b>Daily Streak:</b> {target_user.daily_streak} days\n"
        f"⚠️ <b>Warnings:</b> {warns} / {max_warns}\n"
        f"🎖️ <b>Badges:</b> {target_user.badges}\n"
    )

    await reply_with_ttl(message, text, ttl_type=TTLType.FUN)


@router.message(Command("settitle"))
async def handle_set_title(
    message: Message,
    db_user: Optional[User] = None,
):
    if not db_user:
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await reply_with_ttl(
            message,
            "⚠️ Usage: <code>/settitle [custom flair title]</code>",
            ttl_type=TTLType.FUN,
        )
        return

    new_title = parts[1].strip()[:50]
    db_user.custom_title = new_title
    await reply_with_ttl(
        message,
        f"✨ Your custom title flair has been updated to: <b>{escape_html(new_title)}</b>",
        ttl_type=TTLType.FUN,
    )
