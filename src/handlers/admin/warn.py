from typing import Optional
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import TTLType
from src.keyboards.moderation_kb import get_warn_undo_keyboard
from src.middlewares.ttl import reply_with_ttl
from src.models.group import Group
from src.models.user import User
from src.services.moderation_service import ModerationService
from src.utils.emojis import E_ALERT, E_SHIELD, E_WARN
from src.utils.target_resolver import resolve_target
from src.utils.text_formatter import format_card, get_user_mention, mention_html

router = Router(name="admin_warn")


@router.message(Command("warn", "swarn", "dwarn"))
async def handle_warn(
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
            "❌ You do not have permission to warn members.",
            ttl_type=TTLType.WARN,
        )
        return

    target = await resolve_target(message, session=session, bot=message.bot)
    if not target:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> <code>/warn &lt;reply | @username | ID&gt; [reason]</code>\n"
            "<i>Variants: <code>/dwarn</code> (deletes message), <code>/swarn</code> (silent)</i>",
            ttl_type=TTLType.WARN,
        )
        return

    cmd_text = (message.text or "").split()[0].lower()
    if "dwarn" in cmd_text and message.reply_to_message:
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
        current_warns, max_warns, escalated_action = await ModerationService.warn_user(
            bot=message.bot,
            session=session,
            group=db_group,
            target_user=target_user,
            admin_user=db_user,
            reason=reason,
        )

        target_mention = mention_html(target.user_id, target.first_name)
        admin_mention = get_user_mention(message.from_user)

        if escalated_action:
            card = format_card(
                title=f"{E_ALERT} WARNING LIMIT EXCEEDED",
                fields=[
                    ("Target", f"{target_mention} [<code>{target.user_id}</code>]"),
                    ("Warnings", f"<b>{max_warns}/{max_warns}</b>"),
                    ("Escalation", f"User was {escalated_action}"),
                    ("Admin", admin_mention),
                ],
            )
        else:
            card = format_card(
                title=f"{E_WARN} WARNING ISSUED",
                fields=[
                    ("Target", f"{target_mention} [<code>{target.user_id}</code>]"),
                    ("Warnings", f"<b>{current_warns}/{max_warns}</b>"),
                    ("Reason", reason),
                    ("Admin", admin_mention),
                ],
            )

        undo_kb = get_warn_undo_keyboard(db_group.chat_id, target.user_id)
        await reply_with_ttl(
            message, card, ttl_type=TTLType.WARN, reply_markup=undo_kb
        )
    except Exception as e:
        await reply_with_ttl(
            message, f"❌ Failed to warn user: {e}", ttl_type=TTLType.WARN
        )


@router.message(Command("warns"))
async def handle_get_warns(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    target = await resolve_target(message, session=session, bot=message.bot)
    target_user_id = target.user_id if target else (message.from_user.id if message.from_user else 0)
    target_name = target.first_name if target else (message.from_user.first_name if message.from_user else "User")
    target_username = target.username if target else (message.from_user.username if message.from_user else None)

    member = await ModerationService.get_or_create_member(
        session,
        db_group.chat_id,
        target_user_id,
        target_name,
        target_username,
        db_group.title,
    )
    target_mention = mention_html(target_user_id, target_name)
    card = format_card(
        title=f"{E_WARN} WARNING STATUS",
        fields=[
            ("Member", f"{target_mention} [<code>{target_user_id}</code>]"),
            ("Active Warnings", f"<b>{member.warnings_count} / {db_group.max_warns}</b>"),
            ("On Threshold", f"<code>{db_group.warn_action.upper()}</code>"),
        ],
    )
    await reply_with_ttl(message, card, ttl_type=TTLType.WARN)


@router.message(Command("resetwarns", "unwarn"))
async def handle_reset_warns(
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
            "❌ You do not have permission to reset warnings.",
            ttl_type=TTLType.WARN,
        )
        return

    target = await resolve_target(message, session=session, bot=message.bot)
    if not target:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> <code>/unwarn &lt;reply | @username | ID&gt;</code>\n"
            "<i>Alias: <code>/resetwarns</code></i>",
            ttl_type=TTLType.WARN,
        )
        return

    target_user = User(
        user_id=target.user_id,
        username=target.username,
        first_name=target.first_name,
    )
    try:
        await ModerationService.reset_warns(
            bot=message.bot,
            session=session,
            group=db_group,
            target_user=target_user,
            admin_user=db_user,
        )

        await reply_with_ttl(
            message,
            f"{E_SHIELD} Warnings for {mention_html(target.user_id, target.first_name)} have been reset to <b>0/{db_group.max_warns}</b>.",
            ttl_type=TTLType.WARN,
        )
    except Exception as e:
        await reply_with_ttl(
            message, f"❌ Failed to reset warnings: {e}", ttl_type=TTLType.WARN
        )
