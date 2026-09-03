from typing import Optional
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import TTLType
from src.middlewares.ttl import reply_with_ttl
from src.models.blocklist import BlocklistTerm
from src.models.group import Group
from src.utils.emojis import E_BAN, E_NOTE, E_SHIELD, E_STOP, E_WARN
from src.utils.text_formatter import escape_html, format_card

router = Router(name="admin_blocklist")


def get_tos_card_and_keyboard(db_group: Group) -> tuple[str, InlineKeyboardMarkup]:
    status_str = "🟢 ACTIVE (Auto-Delete Message)" if db_group.tos_shield_enabled else "🔴 DISABLED"
    card = format_card(
        title=f"{E_SHIELD} TELEGRAM TOS SHIELD",
        fields=[
            ("Group", db_group.title),
            ("Status", f"<b>{status_str}</b>"),
            ("Protected Against", "Weapons, Narcotics, Carding Dumps, CSAM, Contraband"),
            ("Action on Trigger", "Instant Message Purge + Audit Log (No Bans)"),
        ],
        footer="Toggle using button below or: /tos on / /tos off",
    )

    btn_text = "🔴 Turn OFF TOS Shield" if db_group.tos_shield_enabled else "🟢 Turn ON TOS Shield"
    btn_style = "danger" if db_group.tos_shield_enabled else "success"
    btn_icon = "5260293700088511294" if db_group.tos_shield_enabled else "5237699328843200968"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=btn_text,
                    callback_data=f"tos:toggle:{db_group.chat_id}",
                    style=btn_style,
                    icon_custom_emoji_id=btn_icon,
                )
            ]
        ]
    )
    return card, kb


@router.message(Command("blocklist", "blacklist"))
async def handle_blocklist_command(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not is_admin:
        await message.answer("❌ Only administrators can configure the blocklist.")
        return

    parts = message.text.split(maxsplit=3)
    subcommand = parts[1].lower() if len(parts) > 1 else "list"

    if subcommand == "add" and len(parts) > 2:
        term = parts[2].strip().lower()
        action = parts[3].strip().lower() if len(parts) > 3 else "delete"
        if action not in ("delete", "warn", "mute", "ban"):
            action = "delete"

        # Remove existing if already present
        await session.execute(
            delete(BlocklistTerm).where(
                BlocklistTerm.chat_id == db_group.chat_id,
                BlocklistTerm.term == term,
            )
        )
        new_term = BlocklistTerm(
            chat_id=db_group.chat_id,
            term=term,
            action=action,
        )
        session.add(new_term)
        await session.commit()

        card = format_card(
            title=f"{E_SHIELD} BLOCKLIST TERM ADDED",
            fields=[
                ("Group", db_group.title),
                ("Term", f"<code>{escape_html(term)}</code>"),
                ("Enforcement Action", f"<code>{action.upper()}</code>"),
            ],
            footer="Messages containing this term will be automatically intercepted.",
        )
        await reply_with_ttl(message, card, ttl_type=TTLType.MODERATION)
        return

    elif subcommand in ("remove", "del", "rm") and len(parts) > 2:
        term = parts[2].strip().lower()
        res = await session.execute(
            delete(BlocklistTerm).where(
                BlocklistTerm.chat_id == db_group.chat_id,
                BlocklistTerm.term == term,
            )
        )
        await session.commit()

        if res.rowcount > 0:
            await reply_with_ttl(
                message,
                f"{E_SHIELD} Term <code>{escape_html(term)}</code> was removed from the blocklist.",
                ttl_type=TTLType.MODERATION,
            )
        else:
            await reply_with_ttl(
                message,
                f"❌ Term <code>{escape_html(term)}</code> was not found in the blocklist.",
                ttl_type=TTLType.MODERATION,
            )
        return

    # List terms
    res = await session.execute(
        select(BlocklistTerm).where(BlocklistTerm.chat_id == db_group.chat_id)
    )
    terms = res.scalars().all()

    if not terms:
        await reply_with_ttl(
            message,
            f"{E_NOTE} <b>Group Blocklist:</b> No custom terms configured.\n"
            f"<i>Add terms using: <code>/blocklist add &lt;term&gt; [delete|warn|mute|ban]</code></i>",
            ttl_type=TTLType.MODERATION,
        )
        return

    lines = [f"{E_NOTE} <b>Active Group Blocklist Terms:</b>\n"]
    for t in terms:
        lines.append(
            f"• <code>{escape_html(t.term)}</code> — Action: <code>{t.action.upper()}</code>"
        )

    lines.append(
        "\n<i>Manage via: <code>/blocklist add &lt;term&gt; [action]</code> or <code>/blocklist remove &lt;term&gt;</code></i>"
    )
    await reply_with_ttl(message, "\n".join(lines), ttl_type=TTLType.MODERATION, custom_ttl=45)


@router.message(Command("tos", "tosshield"))
async def handle_tos_command(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not is_admin:
        await message.answer("❌ Only administrators can configure the TOS shield.")
        return

    parts = message.text.split()
    if len(parts) > 1:
        # Check all extra arguments
        full_arg = " ".join(parts[1:]).lower()
        if any(x in full_arg for x in ("on", "enable", "true", "1", "activate")):
            db_group.tos_shield_enabled = True
            await session.commit()
        elif any(x in full_arg for x in ("off", "disable", "false", "0", "deactivate")):
            db_group.tos_shield_enabled = False
            await session.commit()

    card, kb = get_tos_card_and_keyboard(db_group)
    await reply_with_ttl(message, card, reply_markup=kb, ttl_type=TTLType.MODERATION, custom_ttl=60)


@router.callback_query(F.data.startswith("tos:toggle:"))
async def handle_tos_toggle_callback(
    call: CallbackQuery,
    session: Optional[AsyncSession] = None,
    is_admin: bool = False,
):
    if not session or not call.message or not call.from_user:
        return

    chat_id = int(call.data.split(":")[-1])
    res = await session.execute(select(Group).where(Group.chat_id == chat_id))
    group = res.scalar_one_or_none()
    if not group:
        await call.answer("Group data not found.", show_alert=True)
        return

    from src.utils.permissions import is_super_admin

    is_super = is_super_admin(call.from_user.id)
    if not is_admin and not is_super:
        await call.answer("❌ Only administrators can toggle the TOS shield.", show_alert=True)
        return

    group.tos_shield_enabled = not group.tos_shield_enabled
    await session.commit()

    card, kb = get_tos_card_and_keyboard(group)
    try:
        await call.message.edit_text(card, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass

    state_text = "ENABLED (Auto-Delete)" if group.tos_shield_enabled else "DISABLED"
    await call.answer(f"🛡️ TOS Shield is now {state_text}!")
