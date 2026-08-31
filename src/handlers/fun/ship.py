import hashlib
import random
from typing import Optional
from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Message
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import TTLType
from src.middlewares.ttl import reply_with_ttl, schedule_auto_delete
from src.models.group import Group
from src.models.member import GroupMember
from src.models.user import User
from src.services.ship_image_service import ShipImageService
from src.utils.emojis import (
    E_DIAMOND,
    E_FIRE,
    E_HEART,
    E_LIGHTNING,
    E_RADAR,
    E_STAR,
)
from src.utils.text_formatter import escape_html, mention_html

router = Router(name="fun_ship")


def generate_progress_bar(percentage: int) -> str:
    filled = int(percentage / 10)
    empty = 10 - filled
    return f"[{'█' * filled}{'░' * empty}]"


def get_ship_status(percentage: int) -> str:
    if percentage >= 90:
        return f"{E_HEART} Soulmates for life! Match made in heaven! 💍"
    elif percentage >= 75:
        return f"{E_FIRE} Hot couple! Spreading love in the chat! {E_HEART}"
    elif percentage >= 50:
        return f"{E_STAR} Cute duo! There is definitely potential! 💕"
    elif percentage >= 25:
        return f"{E_RADAR} It is complicated... maybe just good friends? ☕"
    else:
        return "💀 Disaster match! Run for your life! 🏃💨"


def get_couple_name(name1: str, name2: str) -> str:
    part1 = name1[: max(2, len(name1) // 2)]
    part2 = name2[max(2, len(name2) // 2) :]
    return (part1 + part2).title()


async def get_active_group_members(
    bot: Bot,
    session: AsyncSession,
    chat_id: int,
    exclude_user_id: int,
    limit: int = 50,
) -> list[tuple[int, str]]:
    """Fetches active chat members who regularly chat in this specific supergroup."""
    stmt = (
        select(GroupMember.user_id, User.first_name)
        .join(User, GroupMember.user_id == User.user_id)
        .where(
            GroupMember.chat_id == chat_id,
            GroupMember.user_id != exclude_user_id,
            GroupMember.is_banned == False,
            GroupMember.is_muted == False,
        )
        .order_by(desc(GroupMember.last_active_at), desc(GroupMember.message_count))
        .limit(limit)
    )
    res = await session.execute(stmt)
    members = res.all()
    if members:
        return [(m[0], m[1]) for m in members]

    # Fallback to chat administrators
    try:
        admins = await bot.get_chat_administrators(chat_id=chat_id)
        valid_admins = []
        for adm in admins:
            if not adm.user.is_bot and adm.user.id != exclude_user_id:
                valid_admins.append((adm.user.id, adm.user.first_name))
        return valid_admins
    except Exception:
        return []


@router.message(Command("ship", "couple"))
async def handle_ship_command(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    db_user: Optional[User] = None,
):
    if not db_group or not session or not message.from_user or not message.bot:
        await message.answer("⚠️ The /ship command can only be used in supergroups.")
        return

    caller_id = message.from_user.id
    caller_name = message.from_user.first_name

    target_user_id = None
    target_user_name = None

    # 1. Check if replied to a message
    if message.reply_to_message and message.reply_to_message.from_user:
        replied = message.reply_to_message.from_user
        if replied.id != caller_id and not replied.is_bot:
            target_user_id = replied.id
            target_user_name = replied.first_name

    # 2. Check if username mentioned in command
    if not target_user_id:
        parts = message.text.split(maxsplit=2)
        if len(parts) > 1 and parts[1].startswith("@"):
            username = parts[1].lstrip("@").lower()
            res_u = await session.execute(select(User).where(User.username == username))
            u_found = res_u.scalar_one_or_none()
            if u_found and u_found.user_id != caller_id:
                target_user_id = u_found.user_id
                target_user_name = u_found.first_name

    # 3. Otherwise, pick a random active member who chats regularly in this group
    if not target_user_id:
        active_members = await get_active_group_members(
            bot=message.bot,
            session=session,
            chat_id=db_group.chat_id,
            exclude_user_id=caller_id,
        )

        if active_members:
            chosen = random.choice(active_members)
            target_user_id = chosen[0]
            target_user_name = chosen[1]

    if not target_user_id or not target_user_name:
        await reply_with_ttl(
            message,
            f"{E_HEART} <i>Not enough active group members found yet to find a match! Keep chatting in the group to build the matchmaking pool.</i>",
            ttl_type=TTLType.FUN,
            custom_ttl=15,
        )
        return

    # Deterministic yet dynamic daily seed + salt calculation
    pair_str = f"{min(caller_id, target_user_id)}:{max(caller_id, target_user_id)}"
    seed = int(hashlib.md5(pair_str.encode()).hexdigest(), 16)
    random.seed(seed + random.randint(1, 999))
    compatibility = random.randint(25, 100)

    couple_tag = get_couple_name(caller_name, target_user_name)
    progress_bar = generate_progress_bar(compatibility)
    status_text = get_ship_status(compatibility)

    mention1 = mention_html(caller_id, caller_name)
    mention2 = mention_html(target_user_id, target_user_name)

    card = (
        f"{E_HEART} <b>MATCHMAKING RADAR</b>\n\n"
        f"💘 <b>Couple:</b> {mention1} <b>+</b> {mention2}\n"
        f"🏷️ <b>Ship Name:</b> <code>#{escape_html(couple_tag)}</code>\n\n"
        f"{E_RADAR} <b>Compatibility:</b> <b>{compatibility}%</b>\n"
        f"<code>{progress_bar}</code>\n\n"
        f"💬 <i>{status_text}</i>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Roll New Ship",
                    callback_data=f"ship:reroll:{caller_id}",
                    style="success",
                    icon_custom_emoji_id="5312138559556164615",
                )
            ]
        ]
    )

    # Generate Landscape Picture with PFPs and Heart Percentage
    try:
        u1_img = await ShipImageService.fetch_user_avatar(message.bot, caller_id)
        u2_img = await ShipImageService.fetch_user_avatar(message.bot, target_user_id)
        photo_buf = ShipImageService.generate_ship_card(
            user1_name=caller_name,
            user2_name=target_user_name,
            user1_img=u1_img,
            user2_img=u2_img,
            percentage=compatibility,
            ship_name=f"#{couple_tag}",
        )
        input_file = BufferedInputFile(photo_buf.getvalue(), filename="ship_match.jpg")
        sent = await message.answer_photo(
            photo=input_file,
            caption=card,
            reply_markup=kb,
            parse_mode="HTML",
        )
        await schedule_auto_delete(message.chat.id, sent.message_id, ttl_seconds=60)
        await schedule_auto_delete(message.chat.id, message.message_id, ttl_seconds=60)
    except Exception:
        await reply_with_ttl(
            message,
            card,
            reply_markup=kb,
            ttl_type=TTLType.FUN,
            custom_ttl=60,
        )


@router.callback_query(F.data.startswith("ship:reroll:"))
async def handle_ship_reroll(call: CallbackQuery, session: Optional[AsyncSession] = None):
    if not call.from_user or not session or not call.message or not call.bot:
        return

    caller_id = int(call.data.split(":")[-1])
    if call.from_user.id != caller_id:
        await call.answer("❌ Only the member who initiated the ship can re-roll!", show_alert=True)
        return

    chat_id = call.message.chat.id
    caller_name = call.from_user.first_name

    active_members = await get_active_group_members(
        bot=call.bot,
        session=session,
        chat_id=chat_id,
        exclude_user_id=caller_id,
    )

    if not active_members:
        await call.answer("Not enough active members to re-roll!", show_alert=True)
        return

    chosen = random.choice(active_members)
    target_user_id = chosen[0]
    target_user_name = chosen[1]

    compatibility = random.randint(25, 100)
    couple_tag = get_couple_name(caller_name, target_user_name)
    progress_bar = generate_progress_bar(compatibility)
    status_text = get_ship_status(compatibility)

    mention1 = mention_html(caller_id, caller_name)
    mention2 = mention_html(target_user_id, target_user_name)

    card = (
        f"{E_HEART} <b>MATCHMAKING RADAR</b>\n\n"
        f"💘 <b>Couple:</b> {mention1} <b>+</b> {mention2}\n"
        f"🏷️ <b>Ship Name:</b> <code>#{escape_html(couple_tag)}</code>\n\n"
        f"{E_RADAR} <b>Compatibility:</b> <b>{compatibility}%</b>\n"
        f"<code>{progress_bar}</code>\n\n"
        f"💬 <i>{status_text}</i>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Roll New Ship",
                    callback_data=f"ship:reroll:{caller_id}",
                    style="success",
                    icon_custom_emoji_id="5312138559556164615",
                )
            ]
        ]
    )

    try:
        u1_img = await ShipImageService.fetch_user_avatar(call.bot, caller_id)
        u2_img = await ShipImageService.fetch_user_avatar(call.bot, target_user_id)
        photo_buf = ShipImageService.generate_ship_card(
            user1_name=caller_name,
            user2_name=target_user_name,
            user1_img=u1_img,
            user2_img=u2_img,
            percentage=compatibility,
            ship_name=f"#{couple_tag}",
        )
        input_file = BufferedInputFile(photo_buf.getvalue(), filename="ship_match.jpg")
        media = InputMediaPhoto(media=input_file, caption=card, parse_mode="HTML")
        await call.message.edit_media(media=media, reply_markup=kb)
    except Exception:
        try:
            await call.message.edit_caption(caption=card, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass
    await call.answer("New ship rolled!")
