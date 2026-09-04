import os
import shutil
import time
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
from src.models.member import GroupMember
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
from src.utils.text_formatter import escape_html, format_card

router = Router(name="admin_superadmin")


def is_super_admin(user_id: int) -> bool:
    return user_id in settings.bot_super_admins


# --------------------------------------------------------------------------
# System / EC2 stats — stdlib only, no new dependency (psutil isn't in
# requirements.txt). Reads /proc directly, which only works on Linux
# (fine for an EC2 deployment; falls back gracefully elsewhere).
# --------------------------------------------------------------------------
def _get_system_stats() -> dict:
    stats = {
        "cpu_load": "N/A",
        "mem_used_pct": "N/A",
        "mem_used_mb": 0,
        "mem_total_mb": 0,
        "disk_used_pct": "N/A",
        "disk_used_gb": 0,
        "disk_total_gb": 0,
        "uptime": "N/A",
    }

    # CPU load average (1 / 5 / 15 min)
    try:
        load1, load5, load15 = os.getloadavg()
        stats["cpu_load"] = f"{load1:.2f} / {load5:.2f} / {load15:.2f}"
    except (OSError, AttributeError):
        pass

    # Memory, from /proc/meminfo (Linux only)
    try:
        meminfo = {}
        with open("/proc/meminfo") as f:
            for line in f:
                key, value = line.split(":", 1)
                meminfo[key.strip()] = int(value.strip().split()[0])  # kB
        total_kb = meminfo.get("MemTotal", 0)
        available_kb = meminfo.get("MemAvailable", 0)
        used_kb = max(total_kb - available_kb, 0)
        if total_kb > 0:
            stats["mem_total_mb"] = round(total_kb / 1024)
            stats["mem_used_mb"] = round(used_kb / 1024)
            stats["mem_used_pct"] = f"{(used_kb / total_kb) * 100:.1f}%"
    except (FileNotFoundError, ValueError, KeyError):
        pass

    # Disk usage for the root filesystem
    try:
        total, used, _free = shutil.disk_usage("/")
        stats["disk_total_gb"] = round(total / (1024**3), 1)
        stats["disk_used_gb"] = round(used / (1024**3), 1)
        stats["disk_used_pct"] = f"{(used / total) * 100:.1f}%"
    except OSError:
        pass

    # System uptime, from /proc/uptime
    try:
        with open("/proc/uptime") as f:
            uptime_seconds = float(f.readline().split()[0])
        stats["uptime"] = format_uptime(uptime_seconds)
    except (FileNotFoundError, ValueError):
        pass

    return stats


def format_uptime(seconds: float) -> str:
    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def get_superadmin_keyboard() -> InlineKeyboardMarkup:
    # NOTE: `style` and `icon_custom_emoji_id` were previously passed to
    # InlineKeyboardButton, but neither is a real field on this Telegram
    # Bot API object. aiogram's pydantic models reject unknown fields,
    # so calling this function raised a validation error every time -
    # /adminpanel was completely broken. Removed both.
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Refresh Statistics", callback_data="sa:refresh_stats"),
                InlineKeyboardButton(text="📢 Broadcast Wizard", callback_data="sa:broadcast_wizard"),
            ],
            [
                InlineKeyboardButton(text="🖥 System Health", callback_data="sa:system_health"),
                InlineKeyboardButton(text="👥 All Groups", callback_data="sa:list_groups:0"),
            ],
            [
                InlineKeyboardButton(text="🧹 Sweep Cache & DB", callback_data="sa:sweep_cache"),
                InlineKeyboardButton(text="🔁 Sync BotFather Menus", callback_data="sa:sync_commands"),
            ],
            [
                InlineKeyboardButton(text="👑 Super Admins List", callback_data="sa:admins_list"),
                InlineKeyboardButton(text="❌ Close Panel", callback_data="sa:close"),
            ],
        ]
    )


async def generate_admin_panel_card(session: AsyncSession) -> str:
    # Total Users
    res_users = await session.execute(select(func.count(User.user_id)))
    total_users = res_users.scalar_one()

    # Monthly Active Users (MAU)
    # NOTE: this previously did `max(mau, total_users)`, which always just
    # returns total_users since MAU can never exceed it - the MAU figure
    # displayed was actually always identical to total registered users.
    # Now reports the real MAU count directly.
    res_mau = await session.execute(
        select(func.count(User.user_id)).where(
            User.updated_at >= datetime.utcnow() - timedelta(days=30)
        )
    )
    mau = res_mau.scalar_one()

    # Total Groups & Active Groups
    res_groups = await session.execute(select(func.count(Group.chat_id)))
    total_groups = res_groups.scalar_one()
    res_active = await session.execute(
        select(func.count(Group.chat_id)).where(Group.is_active == True)  # noqa: E712
    )
    active_groups = res_active.scalar_one()

    # Total unique members seen across all groups (distinct user_id in GroupMember)
    res_members = await session.execute(
        select(func.count(func.distinct(GroupMember.user_id)))
    )
    total_unique_members = res_members.scalar_one()

    # Sum of all per-group message counts, as a rough "total group memberships" figure
    res_memberships = await session.execute(select(func.count(GroupMember.user_id)))
    total_memberships = res_memberships.scalar_one()

    return format_card(
        title=f"{E_DIAMOND} GLOBAL SUPER ADMIN PANEL",
        fields=[
            ("Monthly Active Users (MAU)", f"<b>{mau:,}</b>"),
            ("Total Registered Users", f"<b>{total_users:,}</b>"),
            ("Unique Members (all groups)", f"<b>{total_unique_members:,}</b>"),
            ("Total Group Memberships", f"<b>{total_memberships:,}</b>"),
            ("Active Supergroups", f"<b>{active_groups:,} / {total_groups:,}</b>"),
            ("Operating Mode", f"<code>{settings.bot_mode.upper()}</code>"),
            ("Primary Audit Channel", f"<code>{settings.default_log_channel_id}</code>"),
            ("Database Pool Status", f"<code>{settings.db_pool_size} conns</code>"),
        ],
        footer="Select an operation below or broadcast via /broadcast &lt;target&gt; &lt;text&gt;",
    )


def generate_system_health_card() -> str:
    stats = _get_system_stats()
    return format_card(
        title=f"{E_RADAR} SERVER / EC2 SYSTEM HEALTH",
        fields=[
            ("CPU Load (1m / 5m / 15m)", f"<code>{stats['cpu_load']}</code>"),
            (
                "Memory Usage",
                f"<b>{stats['mem_used_pct']}</b> ({stats['mem_used_mb']:,} MB / {stats['mem_total_mb']:,} MB)",
            ),
            (
                "Disk Usage (/)",
                f"<b>{stats['disk_used_pct']}</b> ({stats['disk_used_gb']} GB / {stats['disk_total_gb']} GB)",
            ),
            ("System Uptime", f"<code>{stats['uptime']}</code>"),
        ],
        footer="<i>Stats reflect the host running this container.</i>",
    )


async def _build_groups_list_text(session: AsyncSession, bot, offset: int = 0, page_size: int = 15) -> tuple[str, bool]:
    """Returns (text, has_more)."""
    res = await session.execute(
        select(Group).order_by(Group.title).offset(offset).limit(page_size + 1)
    )
    groups = res.scalars().all()
    has_more = len(groups) > page_size
    groups = groups[:page_size]

    res_total = await session.execute(select(func.count(Group.chat_id)))
    total = res_total.scalar_one()

    if not groups:
        return "<i>No groups recorded yet.</i>", False

    lines = [f"{E_SHIELD} <b>All Groups</b> (showing {offset + 1}-{offset + len(groups)} of {total})\n"]
    for g in groups:
        link = None
        try:
            if g.username:
                link = f"https://t.me/{g.username}"
            else:
                link = await bot.export_chat_invite_link(g.chat_id)
        except Exception:
            link = None
        status = "🟢" if g.is_active else "🔴"
        title = escape_html(g.title or "Untitled Group")
        if link:
            lines.append(f'{status} <a href="{link}">{title}</a> — <code>{g.chat_id}</code>')
        else:
            lines.append(f"{status} {title} — <code>{g.chat_id}</code> <i>(no link available)</i>")

    return "\n".join(lines), has_more


def _groups_list_keyboard(offset: int, has_more: bool, page_size: int = 15) -> InlineKeyboardMarkup:
    nav_row = []
    if offset > 0:
        prev_offset = max(offset - page_size, 0)
        nav_row.append(
            InlineKeyboardButton(text="⬅️ Prev", callback_data=f"sa:list_groups:{prev_offset}")
        )
    if has_more:
        nav_row.append(
            InlineKeyboardButton(text="Next ➡️", callback_data=f"sa:list_groups:{offset + page_size}")
        )
    rows = [nav_row] if nav_row else []
    rows.append([InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="sa:refresh_stats")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
            "• <code>/adminpanel</code> — System, member & server stats\n"
            "• <code>/listgroups</code> — All groups the bot is in, with links\n"
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
    if "@" in cmd_word:
        # NOTE: previously hardcoded to check for "@randomgccorebot", a
        # placeholder that almost certainly didn't match this bot's real
        # username - meaning /adminpanel silently failed whenever someone
        # ran it with an explicit @mention in a group. Now resolves the
        # bot's actual username dynamically instead.
        bot_info = await message.bot.get_me()
        if not cmd_word.lower().endswith(f"@{bot_info.username.lower()}"):
            return
    if not session:
        return
    card = await generate_admin_panel_card(session)
    kb = get_superadmin_keyboard()
    await message.answer(card, reply_markup=kb, parse_mode="HTML")


@router.message(Command("listgroups", "allgroups"))
async def handle_list_groups(
    message: Message,
    session: Optional[AsyncSession] = None,
):
    if not message.from_user or not is_super_admin(message.from_user.id) or not session:
        return
    text, has_more = await _build_groups_list_text(session, message.bot, offset=0)
    kb = _groups_list_keyboard(offset=0, has_more=has_more)
    await message.answer(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)


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


@router.callback_query(F.data == "sa:system_health")
async def handle_sa_system_health(call: CallbackQuery):
    if not call.from_user or not is_super_admin(call.from_user.id):
        await call.answer("Unauthorized", show_alert=True)
        return
    card = generate_system_health_card()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="sa:system_health")],
            [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="sa:refresh_stats")],
        ]
    )
    try:
        await call.message.edit_text(card, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await call.answer("System health refreshed!")


@router.callback_query(F.data.startswith("sa:list_groups:"))
async def handle_sa_list_groups(call: CallbackQuery, session: Optional[AsyncSession] = None):
    if not call.from_user or not is_super_admin(call.from_user.id) or not session:
        await call.answer("Unauthorized", show_alert=True)
        return
    try:
        offset = int(call.data.split(":")[2])
    except (IndexError, ValueError):
        offset = 0
    text, has_more = await _build_groups_list_text(session, call.bot, offset=offset)
    kb = _groups_list_keyboard(offset=offset, has_more=has_more)
    try:
        await call.message.edit_text(
            text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True
        )
    except Exception:
        pass
    await call.answer()


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
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="sa:refresh_stats")]
        ]
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
        await call.answer(
            "✅ BotFather metadata, descriptions, and commands synced successfully!",
            show_alert=True,
        )
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
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="sa:refresh_stats")]
        ]
    )
    await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "sa:close")
async def handle_sa_close(call: CallbackQuery):
    if not call.from_user or not is_super_admin(call.from_user.id):
        return
    if call.message:
        await call.message.delete()


def _extract_broadcast_params(message: Message) -> tuple[str, bool, str]:
    raw_html = message.html_text or message.text or ""
    words = raw_html.split()
    target_type = "all"
    pin = False
    consumed_count = 1  # the command word

    if message.text and message.text.startswith("/gcast"):
        target_type = "groups"

    for w in words[1:]:
        low = w.lower().strip()
        if low in ["-all", "all", "-a"]:
            target_type = "all"
            consumed_count += 1
        elif low in ["-users", "users", "-u", "-user", "user"]:
            target_type = "users"
            consumed_count += 1
        elif low in ["-active", "active", "-verified", "verified"]:
            target_type = "active"
            consumed_count += 1
        elif low in ["-groups", "groups", "-g", "-group", "group", "-chats", "chats", "-c"]:
            target_type = "groups"
            consumed_count += 1
        elif low in ["-pin", "pin", "-p"]:
            pin = True
            consumed_count += 1
        else:
            break

    chunks = raw_html.split(None, consumed_count)
    payload_text = chunks[consumed_count].strip() if len(chunks) > consumed_count else ""
    return target_type, pin, payload_text


@router.message(Command("broadcast", "gcast"))
async def handle_broadcast(
    message: Message,
    session: Optional[AsyncSession] = None,
):
    if not message.from_user or not is_super_admin(message.from_user.id):
        return

    target_type, pin, raw_html_text = _extract_broadcast_params(message)
    source_msg = message.reply_to_message

    if not source_msg and not raw_html_text:
        help_text = (
            "📢 <b>GLOBAL BROADCAST USAGE:</b>\n\n"
            "• <code>/broadcast -users &lt;message text / HTML / links&gt;</code>\n"
            "• <code>/broadcast -groups [pin] &lt;message text&gt;</code>\n"
            "• <code>/broadcast -all [pin] &lt;message text&gt;</code>\n"
            "• <code>/broadcast -active &lt;message text&gt;</code> (Verified DM Users)\n\n"
            "<i>💡 Tip: Reply to ANY Photo, Video, GIF, Document, Voice note, or Post with <code>/broadcast -all</code> to copy/forward rich media with full formatting and links!</i>"
        )
        await message.answer(help_text, parse_mode="HTML")
        return

    media_desc = "YES (Rich Media Copy)" if source_msg else "HTML Rich Text"
    progress_msg = await message.answer(
        f"⚡ <b>Initializing Parallel Broadcast...</b>\n\n"
        f"• <b>Scope:</b> <code>{target_type.upper()}</code>\n"
        f"• <b>Media Attached:</b> <code>{media_desc}</code>\n"
        f"• <b>Status:</b> <i>Spinning up background worker pool...</i>\n\n"
        f"<i>Bot remains 100% active and responsive during dispatch.</i>",
        parse_mode="HTML",
    )

    await BroadcastService.start_background_broadcast(
        bot=message.bot,
        admin_id=message.from_user.id,
        target_type=target_type,
        text=raw_html_text if raw_html_text else None,
        source_message=source_msg,
        pin=pin,
        status_msg=progress_msg,
    )
