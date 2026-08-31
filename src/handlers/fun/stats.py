from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, InputMediaPhoto, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import TTLType
from src.keyboards.stats_kb import get_stats_keyboard
from src.middlewares.ttl import reply_photo_with_ttl, reply_with_ttl
from src.models.group import Group
from src.services.quote_service import QuoteService
from src.services.stats_service import StatsService
from src.utils.emojis import (
    E_CALENDAR,
    E_CROWN,
    E_DIAMOND,
    E_FIRE,
    E_MEMBERS,
    E_NEWS,
    E_ROCKET,
    E_SPARKLES,
    E_STAR,
    E_TROPHY,
    animate_text,
)

router = Router(name="fun_stats")


def format_stats_caption(chat_title: str, stats_data: dict) -> str:
    timeframe = stats_data.get("timeframe", "today").upper()
    tot_msg = stats_data.get("total_messages", 0)
    active_users = stats_data.get("active_users", 0)
    tot_stick = stats_data.get("total_stickers", 0)
    tot_med = stats_data.get("total_media", 0)
    tot_voice = stats_data.get("total_voice", 0)

    clean_title = QuoteService.clean_emoji_text(chat_title)

    lines = [
        f"{E_SPARKLES} <b>Activity Metrics — {clean_title}</b>",
        f"<i>Timeframe: {timeframe}</i>\n",
        f"• <b>Total Messages:</b> <code>{tot_msg:,}</code>",
        f"• <b>Active Members:</b> <code>{active_users:,}</code>",
        f"• <b>Stickers Sent:</b> <code>{tot_stick:,}</code>",
        f"• <b>Media & Files:</b> <code>{tot_med:,}</code>",
        f"• <b>Voice & Audio:</b> <code>{tot_voice:,}</code>\n",
        f"{E_CROWN} <b>Top Active Members:</b>",
    ]

    top_users = stats_data.get("top_users", [])[:6]
    medals = ["🥇", "🥈", "🥉", "4.", "5.", "6."]

    if top_users:
        for idx, u in enumerate(top_users):
            medal = medals[idx]
            name = QuoteService.clean_emoji_text(u["name"])[:18]
            count = u["messages"]
            lines.append(f"{medal} <b>{name}</b> — <code>{count:,} msgs</code>")
    else:
        lines.append("<i>No message activity recorded in this period yet!</i>")

    return animate_text("\n".join(lines))


@router.message(Command("stats", "chatstats", "topactive"))
async def handle_chat_stats_cmd(
    message: Message,
    session: Optional[AsyncSession] = None,
):
    if not session or message.chat.id >= 0:
        return

    try:
        timeframe = "today"
        stats_data = await StatsService.get_chat_stats(session, message.chat.id, timeframe=timeframe)
        avatar_img = await StatsService.fetch_chat_avatar(message.bot, message.chat.id)

        card_bio = StatsService.generate_stats_card(
            chat_title=message.chat.title or "Group",
            avatar_img=avatar_img,
            stats_data=stats_data,
        )

        caption = format_stats_caption(message.chat.title or "Group", stats_data)
        kb = get_stats_keyboard(active_timeframe=timeframe)

        await reply_photo_with_ttl(
            message=message,
            photo=BufferedInputFile(card_bio.getvalue(), filename="stats_card.jpg"),
            caption=caption,
            reply_markup=kb,
            ttl_type=TTLType.GENERAL,
        )
    except Exception as e:
        logger.error(f"Error handling stats command: {e}")
        # Fallback to text if image rendering fails
        stats_data = await StatsService.get_chat_stats(session, message.chat.id, timeframe="today")
        caption = format_stats_caption(message.chat.title or "Group", stats_data)
        await reply_with_ttl(
            message=message,
            text=caption,
            reply_markup=get_stats_keyboard(active_timeframe="today"),
            ttl_type=TTLType.GENERAL,
        )


@router.callback_query(F.data.startswith("stats_view:"))
async def handle_stats_timeframe_callback(
    call: CallbackQuery,
    session: Optional[AsyncSession] = None,
):
    if not session or not call.message:
        await call.answer()
        return

    timeframe = call.data.split(":")[1]
    await call.answer(f"Loading {timeframe.replace('_', ' ').title()} stats...")

    try:
        stats_data = await StatsService.get_chat_stats(session, call.message.chat.id, timeframe=timeframe)
        avatar_img = await StatsService.fetch_chat_avatar(call.bot, call.message.chat.id)

        card_bio = StatsService.generate_stats_card(
            chat_title=call.message.chat.title or "Group",
            avatar_img=avatar_img,
            stats_data=stats_data,
        )

        caption = format_stats_caption(call.message.chat.title or "Group", stats_data)
        kb = get_stats_keyboard(active_timeframe=timeframe)

        if call.message.photo:
            new_media = InputMediaPhoto(
                media=BufferedInputFile(card_bio.getvalue(), filename="stats_card.jpg"),
                caption=caption,
                parse_mode="HTML",
            )
            await call.message.edit_media(media=new_media, reply_markup=kb)
        else:
            await call.message.edit_text(caption, reply_markup=kb)
    except Exception as e:
        logger.error(f"Failed to update stats card: {e}")
