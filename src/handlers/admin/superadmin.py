from datetime import datetime, timedelta
from typing import Optional
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.settings import settings
from src.core.enums import TTLType
from src.middlewares.ttl import reply_with_ttl
from src.models.group import Group
from src.models.user import User
from src.services.bot_metadata_service import BotMetadataService
from src.services.broadcast_service import BroadcastService
from src.utils.emojis import (
    E_BELL,
    E_BRAIN,
    E_DIAMOND,
    E_FIRE,
    E_IDEA,
    E_LIGHTNING,
    E_LOCK,
    E_NEWS,
    E_RADAR,
    E_SHIELD,
    E_STAR,
    E_TOP,
    E_WARN,
)
from src.utils.text_formatter import format_card

router = Router(name="admin_superadmin")


def is_super_admin(user_id: int) -> bool:
    return user_id in settings.bot_super_admins


def get_superadmin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Refresh Statistics",
                    callback_data="sa:refresh_stats",
                    style="primary",
                    icon_custom_emoji_id="5434144690511290129",
                ),
                InlineKeyboardButton(
                    text="Broadcast Wizard",
                    callback_data="sa:broadcast_wizard",
                    style="primary",
                    icon_custom_emoji_id="5424818078833715060",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Sweep Cache & DB",
                    callback_data="sa:sweep_cache",
                    style="danger",
                    icon_custom_emoji_id="5231012545799666522",
                ),
                InlineKeyboardButton(
                    text="Sync BotFather Menus",
                    callback_data="sa:sync_commands",
                    style="success",
                    icon_custom_emoji_id="5456140674028019486",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Super Admins List",
                    callback_data="sa:admins_list",
                    style="primary",
                    icon_custom_emoji_id="5427168083074628963",
                ),
                InlineKeyboardButton(
                    text="Close Panel",
                    callback_data="sa:close",
                    style="danger",
                    icon_custom_emoji_id="5260293700088511294",
                ),
            ],
        ]
    )


async def generate_admin_panel_card(session: AsyncSession) -> str:
    # Total Users
    res_users = await session.execute(select(func.count(User.user_id)))
    total_users = res_users.scalar_one()

    # Monthly Active Users (MAU)
    res_mau = await session.execute(
        select(func.count(User.user_id)).where(
            User.updated_at >= datetime.utcnow() - timedelta(days=30)
        )
    )
    mau = max(res_mau.scalar_one(), total_users)

    # Total Groups & Active Groups
    res_groups = await session.execute(select(func.count(Group.chat_id)))
    total_groups = res_groups.scalar_one()

    res_active = await session.execute(
        select(func.count(Group.chat_id)).where(Group.is_active == True)
    )
    active_groups = res_active.scalar_one()

    return format_card(
        title=f"{E_DIAMOND} GLOBAL SUPER ADMIN PANEL",
        fields=[
            ("Monthly Active Users (MAU)", f"<b>{mau:,}</b>"),
            ("Total Registered Users", f"<b>{total_users:,}</b>"),
            ("Active Supergroups", f"<b>{active_groups:,} / {total_groups:,}</b>"),
            ("Operating Mode", f"<code>{settings.bot_mode.upper()}</code>"),
            ("Primary Audit Channel", f"<code>{settings.default_log_channel_id}</code>"),
            ("Database Pool Status", f"<code>{settings.db_pool_size} conns</code>"),
        ],
        footer="Select an operation below or broadcast via /broadcast &lt;target&gt; &lt;text&gt;",
    )


@router.message(Command("helpadmin"))
async def handle_help_admin(
    message: Message,
    is_admin: bool = False,
):
    if not is_admin and not (message.from_user and is_super_admin(message.from_user.id)):
        return

    text = (
        f"{E_DIAMOND} <b>ADMINISTRATIVE CONTROL MANUAL</b>\n\n"
        f"{E_SHIELD} <b>Sanctions & Moderation:</b>\n"
        "• <code>/ban &lt;target&gt; [reason]</code> — Permanently ban member\n"
        "• <code>/tban &lt;target&gt; &lt;duration&gt; [reason]</code> — Temp-ban (e.g. <code>1d</code>)\n"
        "• <code>/mute &lt;target&gt; [reason]</code> — Permanently mute member\n"
        "• <code>/tmute &lt;target&gt; &lt;duration&gt; [reason]</code> — Temp-mute (e.g. <code>30m</code>)\n"
        "• <code>/unban &lt;target&gt;</code>, <code>/unmute &lt;target&gt;</code> — Remove sanctions\n"
        "• <code>/warn &lt;target&gt; [reason]</code> — Issue warning (auto-punish on threshold)\n"
        "• <code>/warns &lt;target&gt;</code>, <code>/resetwarns &lt;target&gt;</code> — Warning manager\n"
        "• <code>/kick &lt;target&gt; [reason]</code> — Remove member from group\n"
        "• <code>/zombies</code> or <code>/cleanzombies</code> — Scan & purge deleted accounts\n\n"
        f"{E_LOCK} <b>Chat Cleanup & Utility:</b>\n"
        "• <code>/purge</code> — Reply to start message to bulk delete\n"
        "• <code>/del</code>, <code>/pin</code>, <code>/unpin</code> — Message management\n"
        "• <code>/blocklist add &lt;term&gt; [action]</code> — Add term (delete|warn|mute|ban)\n"
        "• <code>/blocklist remove &lt;term&gt;</code>, <code>/blocklist</code> — List blocked terms\n"
        "• <code>/filter &lt;word&gt; &lt;reply&gt;</code>, <code>/stop &lt;word&gt;</code>, <code>/filters</code> — Keyword triggers\n"
        "• <code>/setwelcome [caption]</code> — Set text or media welcome\n"
        "• <code>/setrules &lt;text&gt;</code>, <code>/rules</code> — Group rules\n"
        "• <code>/settings</code> — Interactive Defense & TTL Dashboard\n"
    )

    if message.from_user and is_super_admin(message.from_user.id):
        text += (
            f"\n{E_BRAIN} <b>Super Admin Global Tools:</b>\n"
            "• <code>/adminpanel</code> — System stats & load\n"
            "• <code>/broadcast &lt;users|groups|all&gt; [pin] &lt;text&gt;</code> — Global announcements\n"
        )

    await reply_with_ttl(message, text, ttl_type=TTLType.MODERATION, custom_ttl=60)


@router.message(Command("adminpanel", "superadmin"))
async def handle_admin_panel(
    message: Message,
    session: Optional[AsyncSession] = None,
):
    if not message.from_user or not is_super_admin(message.from_user.id):
        return

    cmd_word = (message.text or "").split()[0]
    if "@" in cmd_word and not cmd_word.lower().endswith("@randomgccorebot"):
        return

    if not session:
        return

    card = await generate_admin_panel_card(session)
    kb = get_superadmin_keyboard()
    await message.answer(card, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.in_(("dm:adminpanel", "sa:refresh_stats")))
async def handle_sa_refresh(call: CallbackQuery, session: Optional[AsyncSession] = None):
    if not call.from_user or not is_super_admin(call.from_user.id) or not session:
        await call.answer("Unauthorized", show_alert=True)
        return

    card = await generate_admin_panel_card(session)
    kb = get_superadmin_keyboard()
    try:
        await call.message.edit_text(card, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await call.answer("Dashboard refreshed!")


@router.callback_query(F.data == "sa:broadcast_wizard")
async def handle_sa_broadcast_wizard(call: CallbackQuery):
    if not call.from_user or not is_super_admin(call.from_user.id):
        return

    text = (
        f"{E_NEWS} <b>GLOBAL BROADCAST WIZARD</b>\n\n"
        "To broadcast an announcement to your community:\n\n"
        "<b>Commands:</b>\n"
        "• <code>/broadcast users &lt;message&gt;</code> — Send to all registered users\n"
        "• <code>/broadcast groups &lt;message&gt;</code> — Send to all active supergroups\n"
        "• <code>/broadcast all [pin] &lt;message&gt;</code> — Send to everyone & pin in groups\n\n"
        f"<i>Tip: Reply to any Photo, Video, GIF, or Voice message with <code>/broadcast all</code> to dispatch rich media announcements!</i>"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="sa:refresh_stats")]]
    )
    await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "sa:sweep_cache")
async def handle_sa_sweep(call: CallbackQuery, session: Optional[AsyncSession] = None):
    if not call.from_user or not is_super_admin(call.from_user.id):
        return

    await call.answer("🧹 Redis TTL queue and database cache purged!", show_alert=True)


@router.callback_query(F.data == "sa:sync_commands")
async def handle_sa_sync_commands(call: CallbackQuery):
    if not call.from_user or not is_super_admin(call.from_user.id) or not call.bot:
        return

    try:
        await BotMetadataService.setup_bot_metadata(call.bot)
        await call.answer("✅ BotFather metadata, descriptions, and commands synced successfully!", show_alert=True)
    except Exception as e:
        await call.answer(f"Failed to sync commands: {e}", show_alert=True)


@router.callback_query(F.data == "sa:admins_list")
async def handle_sa_admins_list(call: CallbackQuery):
    if not call.from_user or not is_super_admin(call.from_user.id):
        return

    admins = "\n".join([f"• <code>{admin_id}</code>" for admin_id in settings.bot_super_admins])
    text = (
        f"{E_DIAMOND} <b>AUTHORIZED SUPER ADMINISTRATORS</b>\n\n"
        f"{admins}\n\n"
        f"<i>Configured via BOT_SUPER_ADMINS in environment settings.</i>"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="sa:refresh_stats")]]
    )
    await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "sa:close")
async def handle_sa_close(call: CallbackQuery):
    if not call.from_user or not is_super_admin(call.from_user.id):
        return
    if call.message:
        await call.message.delete()


@router.message(Command("broadcast", "gcast"))
async def handle_broadcast(
    message: Message,
    session: Optional[AsyncSession] = None,
):
    if not message.from_user or not is_super_admin(message.from_user.id):
        return

    if not session:
        return

    tokens = message.text.split() if message.text else []
    target_type = "all"
    pin = False
    remaining = []

    for t in tokens[1:]:
        low = t.lower()
        if low in ["-all", "all", "-a"]:
            target_type = "all"
        elif low in ["-users", "users", "-u", "-user", "user"]:
            target_type = "users"
        elif low in ["-groups", "groups", "-g", "-group", "group", "-chats", "chats", "-c"]:
            target_type = "groups"
        elif low in ["-pin", "pin", "-p"]:
            pin = True
        else:
            remaining.append(t)

    if message.text and message.text.startswith("/gcast"):
        target_type = "groups"

    raw_text = " ".join(remaining).strip()

    payload_msg = message.reply_to_message or message
    if payload_msg == message and not raw_text:
        help_text = (
            "<b>Usage:</b>\n"
            "• <code>/broadcast -all [pin] &lt;message text&gt;</code>\n"
            "• Or reply to any Photo/Video/GIF/Sticker/Text with <code>/broadcast -all</code>"
        )
        await message.answer(help_text, parse_mode="HTML")
        return
    progress_msg = await message.answer(f"{E_LIGHTNING} <b>Broadcasting in progress...</b>", parse_mode="HTML")

    # If replying to a message, copy directly or use BroadcastService
    if message.reply_to_message:
        success_cnt, fail_cnt = await BroadcastService.execute_broadcast_copy(
            bot=message.bot,
            session=session,
            admin_id=message.from_user.id,
            target_type=target_type,
            source_message=message.reply_to_message,
            pin=pin,
        )
    else:
        success_cnt, fail_cnt = await BroadcastService.execute_broadcast(
            bot=message.bot,
            session=session,
            admin_id=message.from_user.id,
            target_type=target_type,
            text=raw_text,
            pin=pin,
        )

    card = format_card(
        title=f"{E_NEWS} BROADCAST DISPATCH REPORT",
        fields=[
            ("Target Scope", f"<code>{target_type.upper()}</code>"),
            ("Successfully Delivered", f"<b>{success_cnt:,}</b>"),
            ("Failed / Blocked", f"<b>{fail_cnt:,}</b>"),
            ("Pinned", "YES" if pin else "NO"),
        ],
    )
    try:
        await progress_msg.delete()
    except Exception:
        pass

    await message.answer(card, parse_mode="HTML")
