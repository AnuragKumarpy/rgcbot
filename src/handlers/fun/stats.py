from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Message
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.exceptions import TelegramBadRequest

from src.core.enums import TTLType
from src.keyboards.stats_kb import get_stats_keyboard, get_user_stats_keyboard
from src.middlewares.ttl import reply_photo_with_ttl, reply_with_ttl
from src.models.group import Group
from src.models.log import ModerationLog
from src.models.user import User
from src.services.moderation_service import ModerationService
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
    E_CHECK,
    E_SHIELD,
    E_SIREN,
    E_WARN,
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


def format_user_stats_caption(target_name: str, stats_data: dict) -> str:
    timeframe = stats_data.get("timeframe", "all_time").replace("_", " ").title()
    tot_msg = stats_data.get("total_messages", 0)
    active_chats = stats_data.get("active_chats", 0)
    tot_stick = stats_data.get("total_stickers", 0)
    tot_med = stats_data.get("total_media", 0)
    tot_voice = stats_data.get("total_voice", 0)
    karma = stats_data.get("karma", 0)
    coins = stats_data.get("coins", 0)
    daily_streak = stats_data.get("daily_streak", 0)
    games_played = stats_data.get("games_played", 0)
    games_won = stats_data.get("games_won", 0)
    game_score = stats_data.get("game_score", 0)

    clean_name = QuoteService.clean_emoji_text(target_name)
    lines = [
        f"{E_SPARKLES} <b>User Activity Metrics — {clean_name}</b>",
        f"<i>Timeframe: {timeframe}</i>\n",
        f"• <b>Total Messages:</b> <code>{tot_msg:,}</code>",
        f"• <b>Active Chats:</b> <code>{active_chats:,}</code>",
        f"• <b>Stickers Sent:</b> <code>{tot_stick:,}</code>",
        f"• <b>Media & Files:</b> <code>{tot_med:,}</code>",
        f"• <b>Voice & Audio:</b> <code>{tot_voice:,}</code>",
        f"• <b>Karma / Coins:</b> <code>{karma:,}</code> / <code>{coins:,}</code>",
        f"• <b>Daily Streak:</b> <code>{daily_streak} days</code>\n",
        f"{E_CROWN} <b>Gaming Stats:</b>",
        f"• <b>Games Played:</b> <code>{games_played:,}</code>",
        f"• <b>Games Won:</b> <code>{games_won:,}</code>",
        f"• <b>Game Score:</b> <code>{game_score:,}</code>",
    ]

    top_chats = stats_data.get("top_chats", [])[:5]
    if top_chats:
        lines.append(f"\n{E_TROPHY} <b>Top Chats:</b>")
        for idx, chat in enumerate(top_chats, start=1):
            lines.append(
                f"{idx}. <b>{QuoteService.clean_emoji_text(chat['title'])[:24]}</b> — <code>{chat['messages']:,} msgs</code>"
            )

    banned_groups = stats_data.get("banned_groups", [])
    muted_groups = stats_data.get("muted_groups", [])
    fed_bans = stats_data.get("federation_bans", [])
    if banned_groups or muted_groups:
        lines.append(f"\n{E_WARN} <b>Appealable Group Restrictions:</b>")
        for group in banned_groups[:5]:
            lines.append(f"• <b>Banned:</b> {QuoteService.clean_emoji_text(group['title'])[:28]}")
        for group in muted_groups[:5]:
            lines.append(f"• <b>Muted:</b> {QuoteService.clean_emoji_text(group['title'])[:28]}")
    if fed_bans:
        lines.append(f"\n{E_SHIELD} <b>Federation Bans:</b>")
        for fed in fed_bans[:5]:
            lines.append(f"• <b>{QuoteService.clean_emoji_text(fed['name'])[:28]}</b>")

    if not banned_groups and not muted_groups and not fed_bans:
        lines.append("\n<i>No active bans recorded for this user.</i>")

    return animate_text("\n".join(lines))


def format_global_stats_caption(stats_data: dict) -> str:
    lines = [
        f"{E_TROPHY} <b>Global Messaging & Game Leaderboards</b>",
        "<i>Top scorers across chats, groups, and games.</i>\n",
        f"{E_CROWN} <b>Top Messaging Users:</b>",
    ]

    top_message_users = stats_data.get("top_message_users", [])[:5]
    if top_message_users:
        for idx, user in enumerate(top_message_users, start=1):
            lines.append(
                f"{idx}. <b>{QuoteService.clean_emoji_text(user['name'])[:22]}</b> — <code>{user['messages']:,} msgs</code>"
            )
    else:
        lines.append("<i>No messaging data yet.</i>")

    top_message_groups = stats_data.get("top_message_groups", [])[:5]
    lines.append(f"\n{E_NEWS} <b>Top Messaging Groups:</b>")
    if top_message_groups:
        for idx, group in enumerate(top_message_groups, start=1):
            lines.append(
                f"{idx}. <b>{QuoteService.clean_emoji_text(group['title'])[:24]}</b> — <code>{group['messages']:,} msgs</code>"
            )
    else:
        lines.append("<i>No group activity data yet.</i>")

    top_game_players = stats_data.get("top_game_players", [])[:5]
    lines.append(f"\n{E_FIRE} <b>Top Game Scorers:</b>")
    if top_game_players:
        for idx, player in enumerate(top_game_players, start=1):
            lines.append(
                f"{idx}. <b>{QuoteService.clean_emoji_text(player['name'])[:22]}</b> — <code>{player['game_score']:,} pts</code>"
            )
    else:
        lines.append("<i>No game scores recorded yet.</i>")

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
        stats_data = await StatsService.get_chat_stats(
            session, message.chat.id, timeframe=timeframe
        )
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
        stats_data = await StatsService.get_chat_stats(
            session, call.message.chat.id, timeframe=timeframe
        )
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
    except TelegramBadRequest as e:
        err_msg = str(e).lower()
        if "message is not modified" in err_msg or "canceled by new edit message request" in err_msg:
            # Safe to ignore user spam clicking or identical states
            pass
        else:
            logger.error(f"Failed to update stats card: {e}")
    except Exception as e:
        logger.error(f"Failed to update stats card: {e}")

@router.message(Command("ustats", "mystats"))
async def handle_user_stats_cmd(
    message: Message,
    session: Optional[AsyncSession] = None,
):
    if not session or not message.from_user:
        return

    target_tg_user = message.from_user
    if message.reply_to_message and message.reply_to_message.from_user:
        target_tg_user = message.reply_to_message.from_user

    stats_data = await StatsService.get_user_stats(session, target_tg_user.id, timeframe="all_time")
    caption = format_user_stats_caption(target_tg_user.full_name or "Member", stats_data)
    appeal_targets = [
        {**group, "status": "banned"} for group in stats_data.get("banned_groups", [])
    ] + [
        {**group, "status": "muted"} for group in stats_data.get("muted_groups", [])
    ]
    kb = get_user_stats_keyboard(appeal_targets, target_tg_user.id)

    await reply_with_ttl(
        message=message,
        text=caption,
        reply_markup=kb,
        ttl_type=TTLType.GENERAL,
    )


@router.message(Command("appeal"))
async def handle_appeal_cmd(
    message: Message,
    session: Optional[AsyncSession] = None,
):
    if not session or not message.from_user:
        return

    stats_data = await StatsService.get_user_stats(session, message.from_user.id, timeframe="all_time")
    appeal_targets = [
        {**group, "status": "banned"} for group in stats_data.get("banned_groups", [])
    ] + [
        {**group, "status": "muted"} for group in stats_data.get("muted_groups", [])
    ]
    if not appeal_targets:
        await reply_with_ttl(
            message,
            f"{E_CHECK} You do not have any active group restrictions recorded by the bot.",
            ttl_type=TTLType.GENERAL,
        )
        return

    await reply_with_ttl(
        message,
        format_user_stats_caption(message.from_user.full_name, stats_data),
        reply_markup=get_user_stats_keyboard(appeal_targets, message.from_user.id),
        ttl_type=TTLType.GENERAL,
    )


@router.message(Command("topstats", "tops"))
async def handle_top_stats_cmd(
    message: Message,
    session: Optional[AsyncSession] = None,
):
    if not session:
        return

    stats_data = await StatsService.get_global_leaderboards(session, limit=10)
    await reply_with_ttl(message, format_global_stats_caption(stats_data), ttl_type=TTLType.GENERAL)


@router.callback_query(F.data.startswith("appeal_req:"))
async def handle_appeal_request_callback(
    call: CallbackQuery,
    session: Optional[AsyncSession] = None,
):
    if not session or not call.message:
        await call.answer()
        return

    parts = call.data.split(":")
    status = parts[1]
    chat_id = int(parts[2])
    target_user_id = int(parts[3])

    if call.from_user.id != target_user_id:
        await call.answer("This appeal request is not for you.", show_alert=True)
        return

    group_res = await session.execute(select(Group).where(Group.chat_id == chat_id))
    group = group_res.scalar_one_or_none()
    user_res = await session.execute(select(User).where(User.user_id == target_user_id))
    target_user = user_res.scalar_one_or_none()

    if not group or not target_user:
        await call.answer("Appeal target not found.", show_alert=True)
        return

    action_filter = ("ban", "tempban") if status == "banned" else ("mute", "tempmute")
    latest_action_res = await session.execute(
        select(ModerationLog)
        .where(
            ModerationLog.chat_id == chat_id,
            ModerationLog.target_user_id == target_user_id,
            ModerationLog.action_type.in_(action_filter),
        )
        .order_by(ModerationLog.created_at.desc())
        .limit(1)
    )
    latest_action = latest_action_res.scalar_one_or_none()

    action_title = "BAN" if status == "banned" else "MUTE"
    action_reply = "unban" if status == "banned" else "unmute"
    action_button = "🔓 Approve Unban" if status == "banned" else "🔊 Approve Unmute"
    action_result = "unbanned" if status == "banned" else "unmuted"

    appeal_text = animate_text(
        f"{E_SIREN} <b>{action_title} APPEAL REQUEST</b>\n\n"
        f"• <b>Group:</b> {QuoteService.clean_emoji_text(group.title)}\n"
        f"• <b>Appealing User:</b> {QuoteService.clean_emoji_text(target_user.first_name)} (<code>{target_user.user_id}</code>)\n"
        f"• <b>Reason:</b> {QuoteService.clean_emoji_text(latest_action.reason) if latest_action and latest_action.reason else 'No reason recorded'}\n\n"
        f"A moderator can review and {action_reply} directly from this message."
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=action_button,
                    callback_data=f"appeal_act:{action_reply}:{chat_id}:{target_user_id}",
                ),
                InlineKeyboardButton(
                    text="🛡 Dismiss",
                    callback_data="appeal_act:dismiss",
                ),
            ]
        ]
    )

    try:
        admins = await call.bot.get_chat_administrators(chat_id)
        for adm in admins:
            if adm.user.is_bot:
                continue
            try:
                await call.bot.send_message(
                    chat_id=adm.user.id,
                    text=appeal_text,
                    reply_markup=kb,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            except Exception as e:
                logger.debug(f"Could not send appeal DM to admin {adm.user.id}: {e}")
    except Exception as e:
        logger.error(f"Failed to fetch administrators for appeal in {chat_id}: {e}")

    await call.answer("Appeal sent to group admins.")


@router.callback_query(F.data.startswith("appeal_act:"))
async def handle_appeal_action_callback(
    call: CallbackQuery,
    session: Optional[AsyncSession] = None,
):
    if not session:
        await call.answer()
        return

    parts = call.data.split(":")
    action = parts[1]

    if action == "dismiss":
        await call.answer("Appeal dismissed.", show_alert=False)
        try:
            if call.message:
                await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return

    chat_id = int(parts[2])
    target_user_id = int(parts[3])

    group_res = await session.execute(select(Group).where(Group.chat_id == chat_id))
    group = group_res.scalar_one_or_none()
    user_res = await session.execute(select(User).where(User.user_id == target_user_id))
    target_user = user_res.scalar_one_or_none()

    if not group or not target_user:
        await call.answer("Appeal target not found.", show_alert=True)
        return

    if action == "unban":
        admin_user = User(
            user_id=call.from_user.id,
            first_name=call.from_user.first_name or "Moderator",
            username=call.from_user.username,
        )
        await ModerationService.unban_user(
            bot=call.bot,
            session=session,
            group=group,
            target_user=target_user,
            admin_user=admin_user,
            reason="Appeal approved via bot",
        )
        await session.commit()
        await call.answer("✅ User unbanned!")
        if call.message:
            await call.message.edit_text(
                f"{E_CHECK} Appeal approved and {QuoteService.clean_emoji_text(target_user.first_name)} was unbanned from {QuoteService.clean_emoji_text(group.title)}.",
                parse_mode="HTML",
            )
    elif action == "unmute":
        admin_user = User(
            user_id=call.from_user.id,
            first_name=call.from_user.first_name or "Moderator",
            username=call.from_user.username,
        )
        await ModerationService.unmute_user(
            bot=call.bot,
            session=session,
            group=group,
            target_user=target_user,
            admin_user=admin_user,
            reason="Appeal approved via bot",
        )
        await session.commit()
        await call.answer("✅ User unmuted!")
        if call.message:
            await call.message.edit_text(
                f"{E_CHECK} Appeal approved and {QuoteService.clean_emoji_text(target_user.first_name)} was unmuted from {QuoteService.clean_emoji_text(group.title)}.",
                parse_mode="HTML",
            )
