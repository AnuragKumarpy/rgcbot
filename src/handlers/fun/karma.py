from typing import Optional
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import ActionType, TTLType
from src.middlewares.ttl import reply_with_ttl
from src.models.group import Group
from src.models.user import User
from src.services.audit_service import AuditService
from src.services.karma_service import KarmaService
from src.utils.emojis import (
    E_COOL,
    E_DIAMOND,
    E_FIRE,
    E_IDEA,
    E_LIGHTNING,
    E_NEWS,
    E_RADAR,
    E_SHIELD,
    E_STAR,
    E_TOP,
    E_WARN,
)
from src.utils.text_formatter import format_card, get_karma_tier, get_user_mention

router = Router(name="fun_karma")


@router.message(F.text.regexp(r"(?i)^(\+rep|thanks|thank you|\+1|thx)\b"))
async def handle_karma_award(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_user: Optional[User] = None,
    db_group: Optional[Group] = None,
):
    if not session or not db_user or not message.reply_to_message:
        return

    target_tg_user = message.reply_to_message.from_user
    if not target_tg_user or target_tg_user.is_bot:
        return

    res = await session.execute(select(User).where(User.user_id == target_tg_user.id))
    target_user = res.scalar_one_or_none()
    if not target_user:
        target_user = User(
            user_id=target_tg_user.id,
            username=target_tg_user.username,
            first_name=target_tg_user.first_name or "",
        )
        session.add(target_user)
        await session.flush()

    success, message_or_tier, new_karma = await KarmaService.process_reputation(
        session=session,
        giver=db_user,
        receiver=target_user,
    )

    giver_mention = get_user_mention(message.from_user)
    target_mention = get_user_mention(target_tg_user)

    if success:
        text = (
            f"{E_STAR} {giver_mention} gave +1 reputation to {target_mention}!\n"
            f"{E_DIAMOND} Total Karma: <b>{new_karma}</b> <i>({message_or_tier})</i>"
        )
        await reply_with_ttl(message, text, ttl_type=TTLType.FUN)

        if db_group:
            await AuditService.log_action(
                bot=message.bot,
                chat_id=db_group.chat_id,
                chat_title=db_group.title,
                target_user_id=target_user.user_id,
                target_user_name=target_user.first_name,
                admin_user_id=db_user.user_id,
                admin_user_name=db_user.first_name,
                action=ActionType.KARMA_AWARD,
                reason=f"Reputation awarded (+1 pt) — New total: {new_karma} ({message_or_tier})",
                channel_id=db_group.log_channel_id,
            )
    else:
        # Send cooldown or self-rep warning with short TTL
        await reply_with_ttl(
            message,
            f"{E_WARN} {giver_mention}, {message_or_tier}",
            ttl_type=TTLType.FUN,
            custom_ttl=10,
        )


@router.message(Command("karma", "rep"))
async def handle_get_karma(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_user: Optional[User] = None,
):
    if not session or not message.from_user:
        return

    target_user = db_user
    target_tg_user = message.from_user

    if message.reply_to_message and message.reply_to_message.from_user:
        target_tg_user = message.reply_to_message.from_user
        res = await session.execute(select(User).where(User.user_id == target_tg_user.id))
        target_user = res.scalar_one_or_none()
        if not target_user:
            target_user = User(
                user_id=target_tg_user.id,
                username=target_tg_user.username,
                first_name=target_tg_user.first_name or "",
            )
            session.add(target_user)
            await session.flush()

    if not target_user:
        return

    mention = get_user_mention(target_tg_user)
    tier = get_karma_tier(target_user.karma)

    card = format_card(
        title=f"{E_DIAMOND} REPUTATION STATUS",
        fields=[
            ("User", mention),
            ("Karma Points", f"<b>{target_user.karma}</b>"),
            ("Rank Tier", tier),
            ("Coins", f"<b>{target_user.coins}</b>"),
            ("Daily Streak", f"<b>{target_user.daily_streak} days</b>"),
        ],
    )
    await reply_with_ttl(message, card, ttl_type=TTLType.FUN)


@router.message(Command("daily"))
async def handle_daily(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_user: Optional[User] = None,
):
    if not session or not db_user or not message.from_user:
        return

    success, message_text, streak, coins_awarded = await KarmaService.claim_daily(session, db_user)
    mention = get_user_mention(message.from_user)

    if success:
        card = format_card(
            title=f"{E_STAR} DAILY REWARD CLAIMED",
            fields=[
                ("Member", mention),
                ("Coins Earned", f"<b>+{coins_awarded} coins</b>"),
                ("Daily Streak", f"<b>{streak} days</b> {E_FIRE}"),
                ("Total Balance", f"<b>{db_user.coins} coins</b>"),
            ],
            footer="Return tomorrow to keep your streak multiplier active!",
        )
        await reply_with_ttl(message, card, ttl_type=TTLType.FUN)
    else:
        await reply_with_ttl(
            message,
            f"{E_WARN} {mention}, {message_text}",
            ttl_type=TTLType.FUN,
            custom_ttl=15,
        )


@router.message(Command("topkarma", "leaderboard"))
async def handle_top_karma(
    message: Message,
    session: Optional[AsyncSession] = None,
):
    if not session:
        return

    res = await session.execute(select(User).order_by(desc(User.karma)).limit(10))
    top_users = res.scalars().all()

    if not top_users:
        await reply_with_ttl(
            message,
            f"{E_DIAMOND} <i>No reputation leaderboard records yet.</i>",
            ttl_type=TTLType.FUN,
        )
        return

    fields = []
    medals = [E_TOP, E_DIAMOND, E_STAR]
    for idx, u in enumerate(top_users, start=1):
        badge = medals[idx - 1] if idx <= 3 else f"#{idx}"
        name = u.first_name or f"User {u.user_id}"
        fields.append((f"{badge} {name}", f"<b>{u.karma} pts</b> ({u.coins} coins)"))

    card = format_card(
        title=f"{E_TOP} GLOBAL REPUTATION LEADERBOARD",
        fields=fields,
        footer="Earn reputation by helping community members (+rep)",
    )
    await reply_with_ttl(message, card, ttl_type=TTLType.FUN)
