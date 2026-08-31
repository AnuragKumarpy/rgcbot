from typing import Optional
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import TTLType
from src.keyboards.moderation_kb import get_ban_undo_keyboard, get_mute_undo_keyboard
from src.middlewares.ttl import reply_with_ttl
from src.models.group import Group
from src.models.user import User
from src.services.moderation_service import ModerationService
from src.utils.emojis import E_ALERT, E_BAN, E_BELL, E_LOCK, E_SHIELD, E_STOP, E_WARN
from src.utils.target_resolver import resolve_target
from src.utils.text_formatter import format_card, get_user_mention, mention_html
from src.utils.time_parser import format_duration, parse_time_string

router = Router(name="admin_ban_mute")


@router.message(Command("ban", "sban", "dban"))
async def handle_ban(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    db_user: Optional[User] = None,
    can_restrict: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not can_restrict:
        await reply_with_ttl(
            message,
            "❌ You do not have permission to ban members.",
            ttl_type=TTLType.MODERATION,
        )
        return

    target = await resolve_target(message, session=session, bot=message.bot)
    if not target:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> <code>/ban &lt;reply | @username | ID&gt; [reason]</code>\n"
            "<i>Variants: <code>/dban</code> (deletes message), <code>/sban</code> (silent)</i>",
            ttl_type=TTLType.MODERATION,
        )
        return

    # If /dban, delete the replied-to message
    cmd_text = (message.text or "").split()[0].lower()
    if "dban" in cmd_text and message.reply_to_message:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id, message_id=message.reply_to_message.message_id
            )
        except Exception:
            pass

    reason = " ".join(target.remaining_args) if target.remaining_args else "No reason specified"
    target_user = User(
        user_id=target.user_id,
        username=target.username,
        first_name=target.first_name,
    )

    try:
        await ModerationService.ban_user(
            bot=message.bot,
            session=session,
            group=db_group,
            target_user=target_user,
            admin_user=db_user,
            reason=reason,
        )
        target_mention = mention_html(target.user_id, target.first_name)
        admin_mention = get_user_mention(message.from_user)

        card = format_card(
            title=f"{E_BAN} SANCTION: PERMANENT BAN",
            fields=[
                ("Target", f"{target_mention} [<code>{target.user_id}</code>]"),
                ("Action", "Permanently Banned"),
                ("Reason", reason),
                ("Admin", admin_mention),
            ],
        )
        undo_kb = get_ban_undo_keyboard(db_group.chat_id, target.user_id)
        await reply_with_ttl(
            message, card, ttl_type=TTLType.MODERATION, reply_markup=undo_kb
        )
    except Exception as e:
        await reply_with_ttl(
            message, f"❌ Failed to ban user: {e}", ttl_type=TTLType.MODERATION
        )


@router.message(Command("tban"))
async def handle_tban(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    db_user: Optional[User] = None,
    can_restrict: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not can_restrict:
        await reply_with_ttl(
            message,
            "❌ You do not have permission to restrict members.",
            ttl_type=TTLType.MODERATION,
        )
        return

    target = await resolve_target(message, session=session, bot=message.bot)
    if not target or not target.remaining_args:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> <code>/tban &lt;reply | @username | ID&gt; &lt;duration&gt; [reason]</code>\n"
            "<i>Examples: <code>/tban 1d Spam</code> or <code>/tban @user 2h Flood</code></i>",
            ttl_type=TTLType.MODERATION,
        )
        return

    # Find duration in remaining args
    duration_sec: Optional[int] = None
    duration_idx = -1
    for idx, arg in enumerate(target.remaining_args):
        sec = parse_time_string(arg)
        if sec:
            duration_sec = sec
            duration_idx = idx
            break

    if not duration_sec or duration_idx == -1:
        await reply_with_ttl(
            message,
            "❌ Invalid duration format! Examples: <code>30m</code>, <code>2h</code>, <code>1d</code>, <code>1w</code>",
            ttl_type=TTLType.MODERATION,
        )
        return

    reason_parts = [
        arg for i, arg in enumerate(target.remaining_args) if i != duration_idx
    ]
    reason = " ".join(reason_parts) if reason_parts else "No reason specified"

    target_user = User(
        user_id=target.user_id,
        username=target.username,
        first_name=target.first_name,
    )

    try:
        await ModerationService.ban_user(
            bot=message.bot,
            session=session,
            group=db_group,
            target_user=target_user,
            admin_user=db_user,
            reason=reason,
            duration_seconds=duration_sec,
        )
        target_mention = mention_html(target.user_id, target.first_name)
        admin_mention = get_user_mention(message.from_user)

        card = format_card(
            title=f"{E_STOP} SANCTION: TEMPORARY BAN",
            fields=[
                ("Target", f"{target_mention} [<code>{target.user_id}</code>]"),
                ("Action", f"Banned for {format_duration(duration_sec)}"),
                ("Reason", reason),
                ("Admin", admin_mention),
            ],
        )
        undo_kb = get_ban_undo_keyboard(db_group.chat_id, target.user_id)
        await reply_with_ttl(
            message, card, ttl_type=TTLType.MODERATION, reply_markup=undo_kb
        )
    except Exception as e:
        await reply_with_ttl(
            message, f"❌ Failed to temp-ban user: {e}", ttl_type=TTLType.MODERATION
        )


@router.message(Command("mute", "smute", "dmute"))
async def handle_mute(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    db_user: Optional[User] = None,
    can_restrict: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not can_restrict:
        await reply_with_ttl(
            message,
            "❌ You do not have permission to mute members.",
            ttl_type=TTLType.MODERATION,
        )
        return

    target = await resolve_target(message, session=session, bot=message.bot)
    if not target:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> <code>/mute &lt;reply | @username | ID&gt; [reason]</code>\n"
            "<i>Variants: <code>/dmute</code> (deletes message), <code>/smute</code> (silent)</i>",
            ttl_type=TTLType.MODERATION,
        )
        return

    cmd_text = (message.text or "").split()[0].lower()
    if "dmute" in cmd_text and message.reply_to_message:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id, message_id=message.reply_to_message.message_id
            )
        except Exception:
            pass

    reason = " ".join(target.remaining_args) if target.remaining_args else "No reason specified"
    target_user = User(
        user_id=target.user_id,
        username=target.username,
        first_name=target.first_name,
    )

    try:
        await ModerationService.mute_user(
            bot=message.bot,
            session=session,
            group=db_group,
            target_user=target_user,
            admin_user=db_user,
            reason=reason,
        )
        target_mention = mention_html(target.user_id, target.first_name)
        admin_mention = get_user_mention(message.from_user)

        card = format_card(
            title=f"{E_LOCK} SANCTION: PERMANENT MUTE",
            fields=[
                ("Target", f"{target_mention} [<code>{target.user_id}</code>]"),
                ("Action", "Muted indefinitely"),
                ("Reason", reason),
                ("Admin", admin_mention),
            ],
        )
        undo_kb = get_mute_undo_keyboard(db_group.chat_id, target.user_id)
        await reply_with_ttl(
            message, card, ttl_type=TTLType.MODERATION, reply_markup=undo_kb
        )
    except Exception as e:
        await reply_with_ttl(
            message, f"❌ Failed to mute user: {e}", ttl_type=TTLType.MODERATION
        )


@router.message(Command("tmute"))
async def handle_tmute(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    db_user: Optional[User] = None,
    can_restrict: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not can_restrict:
        await reply_with_ttl(
            message,
            "❌ You do not have permission to mute members.",
            ttl_type=TTLType.MODERATION,
        )
        return

    target = await resolve_target(message, session=session, bot=message.bot)
    if not target or not target.remaining_args:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> <code>/tmute &lt;reply | @username | ID&gt; &lt;duration&gt; [reason]</code>\n"
            "<i>Examples: <code>/tmute 30m Flood</code> or <code>/tmute @user 2h Toxic</code></i>",
            ttl_type=TTLType.MODERATION,
        )
        return

    duration_sec: Optional[int] = None
    duration_idx = -1
    for idx, arg in enumerate(target.remaining_args):
        sec = parse_time_string(arg)
        if sec:
            duration_sec = sec
            duration_idx = idx
            break

    if not duration_sec or duration_idx == -1:
        await reply_with_ttl(
            message,
            "❌ Invalid duration format! Examples: <code>15m</code>, <code>2h</code>, <code>1d</code>",
            ttl_type=TTLType.MODERATION,
        )
        return

    reason_parts = [
        arg for i, arg in enumerate(target.remaining_args) if i != duration_idx
    ]
    reason = " ".join(reason_parts) if reason_parts else "No reason specified"

    target_user = User(
        user_id=target.user_id,
        username=target.username,
        first_name=target.first_name,
    )

    try:
        await ModerationService.mute_user(
            bot=message.bot,
            session=session,
            group=db_group,
            target_user=target_user,
            admin_user=db_user,
            reason=reason,
            duration_seconds=duration_sec,
        )
        target_mention = mention_html(target.user_id, target.first_name)
        admin_mention = get_user_mention(message.from_user)

        card = format_card(
            title=f"{E_LOCK} SANCTION: TEMPORARY MUTE",
            fields=[
                ("Target", f"{target_mention} [<code>{target.user_id}</code>]"),
                ("Action", f"Muted for {format_duration(duration_sec)}"),
                ("Reason", reason),
                ("Admin", admin_mention),
            ],
        )
        undo_kb = get_mute_undo_keyboard(db_group.chat_id, target.user_id)
        await reply_with_ttl(
            message, card, ttl_type=TTLType.MODERATION, reply_markup=undo_kb
        )
    except Exception as e:
        await reply_with_ttl(
            message, f"❌ Failed to temp-mute user: {e}", ttl_type=TTLType.MODERATION
        )


@router.message(Command("unban"))
async def handle_unban(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    db_user: Optional[User] = None,
    can_restrict: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not can_restrict:
        await reply_with_ttl(
            message,
            "❌ You do not have permission to unban members.",
            ttl_type=TTLType.MODERATION,
        )
        return

    target = await resolve_target(message, session=session, bot=message.bot)
    if not target:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> <code>/unban &lt;reply | @username | ID&gt;</code>",
            ttl_type=TTLType.MODERATION,
        )
        return

    target_user = User(
        user_id=target.user_id,
        username=target.username,
        first_name=target.first_name,
    )
    try:
        await ModerationService.unban_user(
            bot=message.bot,
            session=session,
            group=db_group,
            target_user=target_user,
            admin_user=db_user,
        )
        await reply_with_ttl(
            message,
            f"{E_SHIELD} <b>Restriction Lifted:</b> {mention_html(target.user_id, target.first_name)} has been <b>unbanned</b>.",
            ttl_type=TTLType.MODERATION,
        )
    except Exception as e:
        await reply_with_ttl(
            message, f"❌ Failed to unban user: {e}", ttl_type=TTLType.MODERATION
        )


@router.message(Command("unmute"))
async def handle_unmute(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    db_user: Optional[User] = None,
    can_restrict: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not can_restrict:
        await reply_with_ttl(
            message,
            "❌ You do not have permission to unmute members.",
            ttl_type=TTLType.MODERATION,
        )
        return

    target = await resolve_target(message, session=session, bot=message.bot)
    if not target:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> <code>/unmute &lt;reply | @username | ID&gt;</code>",
            ttl_type=TTLType.MODERATION,
        )
        return

    target_user = User(
        user_id=target.user_id,
        username=target.username,
        first_name=target.first_name,
    )
    try:
        await ModerationService.unmute_user(
            bot=message.bot,
            session=session,
            group=db_group,
            target_user=target_user,
            admin_user=db_user,
        )
        await reply_with_ttl(
            message,
            f"{E_BELL} <b>Restriction Lifted:</b> {mention_html(target.user_id, target.first_name)} has been <b>unmuted</b>.",
            ttl_type=TTLType.MODERATION,
        )
    except Exception as e:
        await reply_with_ttl(
            message, f"❌ Failed to unmute user: {e}", ttl_type=TTLType.MODERATION
        )


@router.message(Command("kick", "skick", "dkick"))
async def handle_kick(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    db_user: Optional[User] = None,
    can_restrict: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not can_restrict:
        await reply_with_ttl(
            message,
            "❌ You do not have permission to kick members.",
            ttl_type=TTLType.MODERATION,
        )
        return

    target = await resolve_target(message, session=session, bot=message.bot)
    if not target:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> <code>/kick &lt;reply | @username | ID&gt; [reason]</code>\n"
            "<i>Variants: <code>/dkick</code> (deletes message), <code>/skick</code> (silent)</i>",
            ttl_type=TTLType.MODERATION,
        )
        return

    cmd_text = (message.text or "").split()[0].lower()
    if "dkick" in cmd_text and message.reply_to_message:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id, message_id=message.reply_to_message.message_id
            )
        except Exception:
            pass

    reason = " ".join(target.remaining_args) if target.remaining_args else "No reason specified"
    target_user = User(
        user_id=target.user_id,
        username=target.username,
        first_name=target.first_name,
    )

    try:
        await ModerationService.kick_user(
            bot=message.bot,
            session=session,
            group=db_group,
            target_user=target_user,
            admin_user=db_user,
            reason=reason,
        )
        target_mention = mention_html(target.user_id, target.first_name)
        admin_mention = get_user_mention(message.from_user)

        card = format_card(
            title=f"{E_STOP} MEMBER REMOVED",
            fields=[
                ("Target", f"{target_mention} [<code>{target.user_id}</code>]"),
                ("Action", "Kicked from group"),
                ("Reason", reason),
                ("Admin", admin_mention),
            ],
        )
        await reply_with_ttl(message, card, ttl_type=TTLType.MODERATION)
    except Exception as e:
        await reply_with_ttl(
            message, f"❌ Failed to kick user: {e}", ttl_type=TTLType.MODERATION
        )


# Interactive Inline Undo Handler
@router.callback_query(F.data.startswith("undo:"))
async def handle_undo_callback(
    call: CallbackQuery,
    session: Optional[AsyncSession] = None,
    can_restrict: bool = False,
):
    if not session or not call.message or not call.from_user:
        return

    if not can_restrict:
        await call.answer("❌ Only administrators can undo moderation actions.", show_alert=True)
        return

    parts = call.data.split(":")
    action = parts[1]
    chat_id = int(parts[2])
    target_user_id = int(parts[3])

    group = await ModerationService.ensure_group(session, chat_id, title=call.message.chat.title or "Group")
    admin_user = await ModerationService.ensure_user(
        session, call.from_user.id, call.from_user.first_name, call.from_user.username
    )
    target_user = await ModerationService.ensure_user(
        session, target_user_id, f"User {target_user_id}", None
    )

    if action == "unmute":
        await ModerationService.unmute_user(
            bot=call.bot,
            session=session,
            group=group,
            target_user=target_user,
            admin_user=admin_user,
            reason="Admin clicked Undo Unmute",
        )
        admin_mention = get_user_mention(call.from_user)
        target_mention = get_user_mention(target_user)
        await call.message.edit_text(
            f"🔊 <b>Action Undone:</b> {target_mention} was <b>unmuted</b> by {admin_mention}.",
            parse_mode="HTML",
        )
        await call.answer("✅ User unmuted!")

    elif action == "unban":
        await ModerationService.unban_user(
            bot=call.bot,
            session=session,
            group=group,
            target_user=target_user,
            admin_user=admin_user,
            reason="Admin clicked Undo Unban",
        )
        admin_mention = get_user_mention(call.from_user)
        target_mention = get_user_mention(target_user)
        await call.message.edit_text(
            f"🔓 <b>Action Undone:</b> {target_mention} was <b>unbanned</b> by {admin_mention}.",
            parse_mode="HTML",
        )
        await call.answer("✅ User unbanned!")

    elif action == "unwarn":
        await ModerationService.reset_warns(
            bot=call.bot,
            session=session,
            group=group,
            target_user=target_user,
            admin_user=admin_user,
        )
        admin_mention = get_user_mention(call.from_user)
        target_mention = get_user_mention(target_user)
        await call.message.edit_text(
            f"🔄 <b>Action Undone:</b> Warnings for {target_mention} were reset by {admin_mention}.",
            parse_mode="HTML",
        )
        await call.answer("✅ Warnings reset!")
