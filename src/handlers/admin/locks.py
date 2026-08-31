from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import TTLType
from src.keyboards.locks_kb import get_locks_keyboard
from src.middlewares.ttl import reply_with_ttl
from src.models.group import Group
from src.services.locks_service import ALL_LOCK_TYPES, LocksService
from src.utils.emojis import E_BAN, E_CHECK, E_CROSS, E_LOCK, E_SHIELD, E_SPARKLES, animate_text

router = Router(name="admin_locks")


@router.message(Command("locks"))
async def handle_locks_dashboard(
    message: Message,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
):
    if not is_admin:
        await reply_with_ttl(message, "❌ Admin rights required.", ttl_type=TTLType.MODERATION)
        return

    if not db_group:
        return

    locked_set = LocksService.get_locked_set(db_group)
    kb = get_locks_keyboard(
        locked_set=locked_set,
        cleanservice_enabled=db_group.clean_service_enabled,
        antichannel_enabled=db_group.antichannel_enabled,
    )

    locked_count = len(locked_set)
    text = animate_text(
        f"{E_SHIELD} <b>Group Content & Media Locks</b>\n"
        f"• <b>Active Locks:</b> <code>{locked_count}/{len(ALL_LOCK_TYPES)}</code>\n"
        f"• <b>CleanService:</b> {'<code>ENABLED</code> 🟢' if db_group.clean_service_enabled else '<code>DISABLED</code> 🔴'}\n"
        f"• <b>AntiChannel:</b> {'<code>ENABLED (' + (db_group.antichannel_mode or 'del') + ')</code> 🟢' if db_group.antichannel_enabled else '<code>DISABLED</code> 🔴'}\n\n"
        "<i>Click any button below to instantly toggle permissions for regular members:</i>"
    )

    await reply_with_ttl(message, text, reply_markup=kb, ttl_type=TTLType.MODERATION)


@router.message(Command("lock"))
async def handle_lock_cmd(
    message: Message,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
    session: Optional[AsyncSession] = None,
):
    if not is_admin:
        await reply_with_ttl(message, "❌ Admin rights required.", ttl_type=TTLType.MODERATION)
        return
    if not db_group or not session:
        return

    args = message.text.split()[1:] if message.text else []
    if not args:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> <code>/lock [type]</code>\n"
            f"<b>Available types:</b> <code>{', '.join(ALL_LOCK_TYPES)}</code>, <code>all</code>",
            ttl_type=TTLType.MODERATION,
        )
        return

    target_type = args[0].lower()
    norm = LocksService.normalize_lock_type(target_type)
    if not norm:
        await reply_with_ttl(
            message, f"❌ Invalid lock type: <code>{target_type}</code>", ttl_type=TTLType.MODERATION
        )
        return

    LocksService.set_lock(db_group, norm, locked=True)
    await session.commit()

    label = "ALL media/content" if norm == "all" else norm.capitalize()
    await reply_with_ttl(
        message,
        animate_text(f"{E_LOCK} <b>Locked:</b> <code>{label}</code> is now restricted for regular members."),
        ttl_type=TTLType.MODERATION,
    )


@router.message(Command("unlock"))
async def handle_unlock_cmd(
    message: Message,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
    session: Optional[AsyncSession] = None,
):
    if not is_admin:
        await reply_with_ttl(message, "❌ Admin rights required.", ttl_type=TTLType.MODERATION)
        return
    if not db_group or not session:
        return

    args = message.text.split()[1:] if message.text else []
    if not args:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> <code>/unlock [type]</code>\n"
            f"<b>Available types:</b> <code>{', '.join(ALL_LOCK_TYPES)}</code>, <code>all</code>",
            ttl_type=TTLType.MODERATION,
        )
        return

    target_type = args[0].lower()
    norm = LocksService.normalize_lock_type(target_type)
    if not norm:
        await reply_with_ttl(
            message, f"❌ Invalid lock type: <code>{target_type}</code>", ttl_type=TTLType.MODERATION
        )
        return

    LocksService.set_lock(db_group, norm, locked=False)
    await session.commit()

    label = "ALL media/content" if norm == "all" else norm.capitalize()
    await reply_with_ttl(
        message,
        animate_text(f"{E_CHECK} <b>Unlocked:</b> <code>{label}</code> is now allowed for regular members."),
        ttl_type=TTLType.MODERATION,
    )


@router.message(Command("cleanservice"))
async def handle_cleanservice_cmd(
    message: Message,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
    session: Optional[AsyncSession] = None,
):
    if not is_admin:
        await reply_with_ttl(message, "❌ Admin rights required.", ttl_type=TTLType.MODERATION)
        return
    if not db_group or not session:
        return

    args = message.text.split()[1:] if message.text else []
    if args:
        sub = args[0].lower()
        if sub in ("on", "enable", "yes", "true", "1"):
            db_group.clean_service_enabled = True
        elif sub in ("off", "disable", "no", "false", "0"):
            db_group.clean_service_enabled = False
    else:
        db_group.clean_service_enabled = not db_group.clean_service_enabled

    await session.commit()
    status = "ENABLED 🟢" if db_group.clean_service_enabled else "DISABLED 🔴"
    await reply_with_ttl(
        message,
        animate_text(
            f"🧹 <b>Clean Service Messages:</b> <code>{status}</code>\n"
            "<i>(System joins, leaves, pins, and video chat notices will be auto-deleted.)</i>"
        ),
        ttl_type=TTLType.MODERATION,
    )


@router.message(Command("antichannel"))
async def handle_antichannel_cmd(
    message: Message,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
    session: Optional[AsyncSession] = None,
):
    if not is_admin:
        await reply_with_ttl(message, "❌ Admin rights required.", ttl_type=TTLType.MODERATION)
        return
    if not db_group or not session:
        return

    args = message.text.split()[1:] if message.text else []
    if args:
        sub = args[0].lower()
        if sub in ("on", "enable", "yes", "true"):
            db_group.antichannel_enabled = True
            if len(args) > 1 and args[1].lower() in ("ban", "del"):
                db_group.antichannel_mode = args[1].lower()
        elif sub in ("off", "disable", "no", "false"):
            db_group.antichannel_enabled = False
        elif sub in ("ban", "del"):
            db_group.antichannel_enabled = True
            db_group.antichannel_mode = sub
    else:
        db_group.antichannel_enabled = not db_group.antichannel_enabled

    await session.commit()
    status = f"ENABLED ({db_group.antichannel_mode or 'del'}) 🟢" if db_group.antichannel_enabled else "DISABLED 🔴"
    await reply_with_ttl(
        message,
        animate_text(
            f"{E_BAN} <b>Anti-Channel Shield:</b> <code>{status}</code>\n"
            "<i>(Prevents users from sending messages as channels.)</i>"
        ),
        ttl_type=TTLType.MODERATION,
    )


@router.callback_query(F.data.startswith("lock_toggle:"))
async def handle_lock_callback(
    call: CallbackQuery,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
    session: Optional[AsyncSession] = None,
):
    if not is_admin:
        await call.answer("❌ Admin permissions required.", show_alert=True)
        return
    if not db_group or not session:
        await call.answer()
        return

    action = call.data.split(":")[1]

    if action == "close":
        if call.message:
            await call.message.delete()
        await call.answer()
        return

    if action == "refresh":
        pass
    elif action == "lock_all":
        LocksService.set_lock(db_group, "all", locked=True)
    elif action == "unlock_all":
        LocksService.set_lock(db_group, "all", locked=False)
    elif action == "cleanservice":
        db_group.clean_service_enabled = not db_group.clean_service_enabled
    elif action == "antichannel":
        db_group.antichannel_enabled = not db_group.antichannel_enabled
    else:
        locked_set = LocksService.get_locked_set(db_group)
        is_currently_locked = action in locked_set
        LocksService.set_lock(db_group, action, locked=not is_currently_locked)

    await session.commit()

    locked_set = LocksService.get_locked_set(db_group)
    kb = get_locks_keyboard(
        locked_set=locked_set,
        cleanservice_enabled=db_group.clean_service_enabled,
        antichannel_enabled=db_group.antichannel_enabled,
    )

    locked_count = len(locked_set)
    text = animate_text(
        f"{E_SHIELD} <b>Group Content & Media Locks</b>\n"
        f"• <b>Active Locks:</b> <code>{locked_count}/{len(ALL_LOCK_TYPES)}</code>\n"
        f"• <b>CleanService:</b> {'<code>ENABLED</code> 🟢' if db_group.clean_service_enabled else '<code>DISABLED</code> 🔴'}\n"
        f"• <b>AntiChannel:</b> {'<code>ENABLED (' + (db_group.antichannel_mode or 'del') + ')</code> 🟢' if db_group.antichannel_enabled else '<code>DISABLED</code> 🔴'}\n\n"
        "<i>Click any button below to instantly toggle permissions for regular members:</i>"
    )

    try:
        if call.message:
            await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        pass

    await call.answer("Updated locks configuration!")
