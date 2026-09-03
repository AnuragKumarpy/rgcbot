from typing import Optional
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ChatPermissions, Message
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import ActionType, TTLType
from src.keyboards.confirmation_kb import get_confirmation_keyboard
from src.middlewares.ttl import reply_with_ttl, schedule_auto_delete
from src.models.group import Group
from src.models.note import AdminNote
from src.services.audit_service import AuditService
from src.utils.emojis import E_ALERT, E_BRAIN, E_LOCK, E_NOTE, E_SHIELD, E_STOP
from src.utils.permissions import is_super_admin
from src.utils.target_resolver import resolve_target
from src.utils.text_formatter import escape_html, format_card, get_user_mention, mention_html

router = Router(name="admin_notes")


@router.message(Command("panic", "lockdown", "antiraid"))
async def handle_panic_command(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
):
    if not db_group or not session or not message.bot or not message.from_user:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not is_admin and not is_super_admin(message.from_user.id):
        await message.answer("❌ Only administrators can toggle Anti-Raid Panic Mode.")
        return

    parts = message.text.split()
    mode = parts[1].lower() if len(parts) > 1 else "toggle"

    # Determine desired action
    is_currently_locked = getattr(db_group, "_is_locked", False)
    if mode in ("on", "enable", "lock") or (mode == "toggle" and not is_currently_locked):
        action_mode = "on"
        action_desc = "LOCK GROUP (Regular members will be muted from sending messages)"
        confirm_text = "Yes, Lock Chat"
        confirm_style = "danger"
    else:
        action_mode = "off"
        action_desc = "RESTORE CHAT (Lift lockdown and allow members to send messages)"
        confirm_text = "Yes, Unlock Chat"
        confirm_style = "success"

    admin_mention = get_user_mention(message.from_user)
    card = format_card(
        title=f"{E_ALERT} CONFIRM ANTI-RAID ACTION",
        fields=[
            ("Group", db_group.title),
            ("Proposed Action", f"<b>{action_desc}</b>"),
            ("Initiated By", admin_mention),
        ],
        footer="Please confirm your decision below to execute or cancel.",
    )

    kb = get_confirmation_keyboard(
        action_key=f"panic:{action_mode}:{db_group.chat_id}",
        admin_id=message.from_user.id,
        confirm_text=confirm_text,
        cancel_text="Cancel",
        confirm_style=confirm_style,
    )
    await reply_with_ttl(message, card, reply_markup=kb, ttl_type=TTLType.MODERATION, custom_ttl=60)


@router.callback_query(F.data.startswith("confirm:panic:"))
async def handle_confirm_panic_callback(
    call: CallbackQuery,
    session: Optional[AsyncSession] = None,
    is_admin: bool = False,
):
    if not call.from_user or not call.bot or not call.message:
        return

    # confirm:panic:{action_mode}:{chat_id}:{admin_id}
    parts = call.data.split(":")
    if len(parts) < 5:
        return

    action_mode = parts[2]
    chat_id = int(parts[3])
    admin_id = int(parts[4])

    if call.from_user.id != admin_id and not is_super_admin(call.from_user.id):
        await call.answer(
            "❌ Only the admin who initiated the command can confirm.", show_alert=True
        )
        return

    res = await session.execute(select(Group).where(Group.chat_id == chat_id)) if session else None
    db_group = res.scalar_one_or_none() if res else None
    chat_title = db_group.title if db_group else (call.message.chat.title or "Group")

    admin_mention = get_user_mention(call.from_user)

    if action_mode == "on":
        try:
            await call.bot.set_chat_permissions(
                chat_id=chat_id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False,
                ),
            )
            if db_group:
                setattr(db_group, "_is_locked", True)

            card = format_card(
                title=f"{E_ALERT} ANTI-RAID PANIC MODE ACTIVATED",
                fields=[
                    ("Group", chat_title),
                    ("Chat Status", "LOCKED (Non-admins cannot send messages)"),
                    ("Authorized By", admin_mention),
                ],
                footer="Unlock chat anytime using: /panic off",
            )
            await call.message.edit_text(card, parse_mode="HTML")
            await call.answer("🚨 Anti-Raid Panic Mode Activated!", show_alert=True)

            await AuditService.log_action(
                bot=call.bot,
                chat_id=chat_id,
                chat_title=chat_title,
                target_user_id=0,
                target_user_name="Supergroup",
                admin_user_id=call.from_user.id,
                admin_user_name=call.from_user.full_name or "Admin",
                action=ActionType.PANIC_MODE,
                reason="Confirmed Anti-Raid Lockdown (Permissions Muted)",
                channel_id=db_group.log_channel_id if db_group else None,
            )
        except Exception as e:
            await call.answer(f"Failed to lock chat: {e}", show_alert=True)

    else:
        try:
            await call.bot.set_chat_permissions(
                chat_id=chat_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_send_polls=True,
                ),
            )
            if db_group:
                setattr(db_group, "_is_locked", False)

            card = format_card(
                title=f"{E_SHIELD} CHAT LOCKDOWN LIFTED",
                fields=[
                    ("Group", chat_title),
                    ("Chat Status", "RESTORED (Members can send messages)"),
                    ("Authorized By", admin_mention),
                ],
            )
            await call.message.edit_text(card, parse_mode="HTML")
            await call.answer("✅ Chat Lockdown Lifted! Permissions Restored.", show_alert=True)

            await AuditService.log_action(
                bot=call.bot,
                chat_id=chat_id,
                chat_title=chat_title,
                target_user_id=0,
                target_user_name="Supergroup",
                admin_user_id=call.from_user.id,
                admin_user_name=call.from_user.full_name or "Admin",
                action=ActionType.PANIC_MODE,
                reason="Confirmed Anti-Raid Lockdown Lift (Permissions Restored)",
                channel_id=db_group.log_channel_id if db_group else None,
            )
        except Exception as e:
            await call.answer(f"Failed to unlock chat: {e}", show_alert=True)


@router.callback_query(F.data.startswith("cancel:panic:"))
async def handle_cancel_panic_callback(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    # cancel:panic:{action_mode}:{chat_id}:{admin_id}
    parts = call.data.split(":")
    admin_id = int(parts[-1]) if len(parts) >= 5 else 0

    if admin_id and call.from_user.id != admin_id and not is_super_admin(call.from_user.id):
        await call.answer(
            "❌ Only the admin who initiated the command can cancel.", show_alert=True
        )
        return

    admin_mention = get_user_mention(call.from_user)
    try:
        await call.message.edit_text(
            f"❌ <b>Anti-Raid action cancelled by {admin_mention}.</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await call.answer("Action Cancelled.")
    await schedule_auto_delete(call.message.chat.id, call.message.message_id, ttl_seconds=10)


@router.message(Command("setnote", "addnote"))
async def handle_set_note(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not is_admin:
        await message.answer("❌ Only administrators can add internal notes.")
        return

    target = await resolve_target(message, session=session, bot=message.bot)
    if not target or not target.remaining_args:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> <code>/setnote &lt;reply | @username | ID&gt; &lt;note text&gt;</code>",
            ttl_type=TTLType.MODERATION,
        )
        return

    note_text = " ".join(target.remaining_args)
    admin_id = message.from_user.id if message.from_user else 0

    note = AdminNote(
        chat_id=db_group.chat_id,
        user_id=target.user_id,
        admin_id=admin_id,
        note_text=note_text,
    )
    session.add(note)
    await session.commit()

    card = format_card(
        title=f"{E_NOTE} ADMIN NOTE ATTACHED",
        fields=[
            (
                "Target",
                f"{mention_html(target.user_id, target.first_name)} [<code>{target.user_id}</code>]",
            ),
            ("Note", escape_html(note_text)),
            ("Author", get_user_mention(message.from_user)),
        ],
        footer="Internal note saved. View notes via /notes <target>",
    )
    await reply_with_ttl(message, card, ttl_type=TTLType.MODERATION)


@router.message(Command("notes", "getnote", "getnotes"))
async def handle_get_notes(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not is_admin:
        await message.answer("❌ Only administrators can view internal notes.")
        return

    target = await resolve_target(message, session=session, bot=message.bot)
    if not target:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> <code>/notes &lt;reply | @username | ID&gt;</code>",
            ttl_type=TTLType.MODERATION,
        )
        return

    stmt = (
        select(AdminNote)
        .where(
            AdminNote.chat_id == db_group.chat_id,
            AdminNote.user_id == target.user_id,
        )
        .order_by(AdminNote.created_at.desc())
    )
    res = await session.execute(stmt)
    notes = res.scalars().all()

    if not notes:
        await reply_with_ttl(
            message,
            f"{E_NOTE} No notes found for {mention_html(target.user_id, target.first_name)}.",
            ttl_type=TTLType.MODERATION,
        )
        return

    lines = [
        f"{E_NOTE} <b>Internal Notes for {mention_html(target.user_id, target.first_name)}:</b>\n"
    ]
    for n in notes:
        lines.append(f"• <i>{n.created_at.strftime('%Y-%m-%d')}</i>: {escape_html(n.note_text)}")

    lines.append(
        f"\n<i>Total notes: {len(notes)} | Clear using: <code>/delnotes {target.user_id}</code></i>"
    )
    await reply_with_ttl(message, "\n".join(lines), ttl_type=TTLType.MODERATION, custom_ttl=45)


@router.message(Command("delnotes", "clearnotes"))
async def handle_del_notes(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not is_admin:
        await message.answer("❌ Only administrators can delete internal notes.")
        return

    target = await resolve_target(message, session=session, bot=message.bot)
    if not target:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> <code>/delnotes &lt;reply | @username | ID&gt;</code>",
            ttl_type=TTLType.MODERATION,
        )
        return

    res = await session.execute(
        delete(AdminNote).where(
            AdminNote.chat_id == db_group.chat_id,
            AdminNote.user_id == target.user_id,
        )
    )
    await session.commit()
    await reply_with_ttl(
        message,
        f"{E_SHIELD} Cleared {res.rowcount} notes for {mention_html(target.user_id, target.first_name)}.",
        ttl_type=TTLType.MODERATION,
    )
