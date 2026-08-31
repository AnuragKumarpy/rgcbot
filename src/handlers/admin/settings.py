from typing import Optional
from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import CaptchaMode, TTLType, WarnAction
from src.keyboards.dm_kb import get_group_selection_keyboard, get_group_settings_redirect_keyboard
from src.keyboards.settings_kb import (
    get_settings_main_menu,
    get_ttl_menu,
    get_warn_settings_menu,
)
from src.middlewares.ttl import reply_with_ttl
from src.models.group import Group
from src.models.ttl import TTLSettings
from src.utils.emojis import (
    E_BELL,
    E_BRAIN,
    E_COOL,
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
from src.utils.permissions import is_admin as check_is_admin, is_super_admin
from src.utils.text_formatter import escape_html, format_card

router = Router(name="admin_settings")


async def get_group_and_ttl(
    session: AsyncSession, chat_id: int
) -> tuple[Group, TTLSettings]:
    res_g = await session.execute(select(Group).where(Group.chat_id == chat_id))
    group = res_g.scalar_one_or_none()
    if not group:
        group = Group(chat_id=chat_id, title="Group", is_active=True)
        session.add(group)
        await session.flush()

    res_t = await session.execute(
        select(TTLSettings).where(TTLSettings.chat_id == chat_id)
    )
    ttl = res_t.scalar_one_or_none()
    if not ttl:
        ttl = TTLSettings(chat_id=chat_id)
        session.add(ttl)
        await session.flush()
    return group, ttl


@router.message(Command("settings"))
async def handle_settings_command(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
):
    if not session or not message.from_user or not message.bot:
        return

    # If called in Private DM: Show list of groups managed by user
    if message.chat.type == ChatType.PRIVATE:
        res = await session.execute(select(Group).where(Group.is_active == True))
        all_groups = res.scalars().all()

        admin_groups = []
        user_id = message.from_user.id
        is_super = is_super_admin(user_id)

        for g in all_groups:
            if is_super:
                admin_groups.append(g)
                continue
            try:
                member = await message.bot.get_chat_member(chat_id=g.chat_id, user_id=user_id)
                if member.status in ("creator", "administrator"):
                    admin_groups.append(g)
            except Exception:
                pass

        if not admin_groups:
            bot_info = await message.bot.get_me()
            await message.answer(
                f"{E_SHIELD} <b>No Managed Groups Found</b>\n\n"
                "You are not recognized as an administrator in any groups where RGCBot is installed.\n"
                f"👉 <a href='https://t.me/{bot_info.username}?startgroup=true'>Add RGCBot to your supergroup</a> to configure settings.",
                parse_mode="HTML",
            )
            return

        text = (
            f"{E_SHIELD} <b>Select a Group to Configure:</b>\n\n"
            "Choose a supergroup below to manage its security filters, defense modules, and auto-delete settings directly in this chat."
        )
        kb = get_group_selection_keyboard(admin_groups, action_prefix="dm_cfg:open")
        await message.answer(text=text, reply_markup=kb, parse_mode="HTML")
        return

    # In Supergroup:
    if not db_group:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not is_admin:
        await message.answer("❌ Only administrators can access group settings.")
        return

    bot_info = await message.bot.get_me()
    text = (
        f"{E_SHIELD} <b>Group Settings & Defense Control</b>\n\n"
        f"• <b>Supergroup:</b> {escape_html(db_group.title)}\n"
        f"• <b>Chat ID:</b> <code>{db_group.chat_id}</code>\n\n"
        f"Choose where you would like to open the settings dashboard:"
    )
    kb = get_group_settings_redirect_keyboard(
        bot_username=bot_info.username or "RandomGCCorebot",
        chat_id=db_group.chat_id,
    )
    await message.answer(text=text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("setwelcome"))
async def handle_set_welcome(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not is_admin:
        await message.answer("❌ Only administrators can configure the welcome message.")
        return

    # Check if replied to media
    if message.reply_to_message:
        replied = message.reply_to_message
        caption_text = message.text.split(maxsplit=1)[1] if len(message.text.split(maxsplit=1)) > 1 else (replied.caption or db_group.welcome_text)
        
        if replied.photo:
            db_group.welcome_media_type = "photo"
            db_group.welcome_media_file_id = replied.photo[-1].file_id
            db_group.welcome_text = caption_text
        elif replied.video:
            db_group.welcome_media_type = "video"
            db_group.welcome_media_file_id = replied.video.file_id
            db_group.welcome_text = caption_text
        elif replied.animation:
            db_group.welcome_media_type = "animation"
            db_group.welcome_media_file_id = replied.animation.file_id
            db_group.welcome_text = caption_text
        else:
            db_group.welcome_media_type = None
            db_group.welcome_media_file_id = None
            db_group.welcome_text = replied.text or caption_text

        await session.commit()
        await reply_with_ttl(
            message,
            f"{E_DIAMOND} <b>Welcome media updated!</b> Format: <code>{db_group.welcome_media_type or 'Text'}</code>",
            ttl_type=TTLType.MODERATION,
        )
        return

    # Direct text set
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await reply_with_ttl(
            message,
            "<b>Usage:</b>\n"
            "• <code>/setwelcome &lt;text message&gt;</code>\n"
            "• Or reply to a Photo/Video/GIF with <code>/setwelcome [caption]</code>\n\n"
            "<i>Tags: <code>{mention}</code>, <code>{name}</code>, <code>{username}</code>, <code>{id}</code>, <code>{chat_title}</code></i>",
            ttl_type=TTLType.MODERATION,
        )
        return

    db_group.welcome_media_type = None
    db_group.welcome_media_file_id = None
    db_group.welcome_text = parts[1].strip()
    await session.commit()
    await reply_with_ttl(
        message, f"{E_DIAMOND} <b>Welcome message text updated!</b>", ttl_type=TTLType.MODERATION
    )


@router.message(Command("welcome"))
async def handle_get_welcome(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
):
    if not db_group:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    card = format_card(
        title=f"{E_NEWS} WELCOME CONFIGURATION",
        fields=[
            ("Enabled", "YES" if db_group.welcome_enabled else "NO"),
            ("Media Format", db_group.welcome_media_type or "Plain Text"),
            ("Template", f"<code>{db_group.welcome_text[:120]}...</code>"),
        ],
        footer="Configure via /setwelcome or /settings",
    )
    await reply_with_ttl(message, card, ttl_type=TTLType.MODERATION)


@router.callback_query(F.data.startswith("cfg:"))
async def handle_settings_callback(
    call: CallbackQuery,
    session: Optional[AsyncSession] = None,
    is_admin: bool = False,
):
    if not session:
        return

    # If in private DM or admin in group
    user_id = call.from_user.id if call.from_user else 0
    is_super = is_super_admin(user_id)

    if not is_admin and not is_super and call.message and call.message.chat.type != ChatType.PRIVATE:
        await call.answer("❌ Only group administrators can alter settings.", show_alert=True)
        return

    data_parts = call.data.split(":")
    action = data_parts[1]

    if action == "close":
        if call.message:
            await call.message.delete()
        return

    chat_id = int(data_parts[-1])
    group, ttl = await get_group_and_ttl(session, chat_id)

    if action == "toggle":
        target = data_parts[2]
        if target == "flood":
            group.antispam_enabled = not group.antispam_enabled
        elif target == "link":
            group.antilink_enabled = not group.antilink_enabled
        elif target == "fwd":
            group.antiforward_enabled = not group.antiforward_enabled
        elif target == "welcome":
            group.welcome_enabled = not group.welcome_enabled
        elif target == "trigger":
            ttl.delete_command_trigger = not ttl.delete_command_trigger
        elif target == "tos":
            group.tos_shield_enabled = not group.tos_shield_enabled

        await session.commit()
        if call.message:
            await call.message.edit_reply_markup(reply_markup=get_settings_main_menu(group, ttl))
        await call.answer("Updated!")

        # Audit log
        if call.from_user:
            from src.core.enums import ActionType
            from src.services.audit_service import AuditService
            await AuditService.log_action(
                bot=call.bot,
                chat_id=chat_id,
                chat_title=group.title,
                target_user_id=call.from_user.id,
                target_user_name=call.from_user.full_name or call.from_user.first_name,
                admin_user_id=call.from_user.id,
                admin_user_name=call.from_user.full_name or call.from_user.first_name,
                action=ActionType.SETTINGS_CHANGE,
                reason=f"Toggled setting: {target}",
                channel_id=group.log_channel_id,
            )

    elif action == "cycle":
        target = data_parts[2]
        if target == "captcha":
            modes = [CaptchaMode.BUTTON.value, CaptchaMode.MATH.value, CaptchaMode.OFF.value]
            curr_idx = modes.index(group.captcha_mode) if group.captcha_mode in modes else 0
            group.captcha_mode = modes[(curr_idx + 1) % len(modes)]
            await session.commit()
            if call.message:
                await call.message.edit_reply_markup(reply_markup=get_settings_main_menu(group, ttl))
            await call.answer(f"Captcha mode: {group.captcha_mode.upper()}")
        elif target == "warn_action":
            actions = [WarnAction.MUTE.value, WarnAction.KICK.value, WarnAction.BAN.value]
            curr_idx = actions.index(group.warn_action) if group.warn_action in actions else 0
            group.warn_action = actions[(curr_idx + 1) % len(actions)]
            await session.commit()
            if call.message:
                await call.message.edit_reply_markup(reply_markup=get_warn_settings_menu(group))
            await call.answer(f"Warn action: {group.warn_action.upper()}")

    elif action == "menu":
        submenu = data_parts[2]
        if submenu == "main":
            if call.message:
                text = (
                    f"{E_SHIELD} <b>Group Settings & Defense Dashboard</b>\n\n"
                    f"Chat: <b>{escape_html(group.title)}</b> [<code>{group.chat_id}</code>]\n"
                    f"Use the buttons below to toggle security modules and configure auto-deletion timers."
                )
                await call.message.edit_text(text=text, reply_markup=get_settings_main_menu(group, ttl), parse_mode="HTML")
        elif submenu == "ttl":
            if call.message:
                await call.message.edit_reply_markup(reply_markup=get_ttl_menu(group, ttl))
        elif submenu == "warn":
            if call.message:
                await call.message.edit_reply_markup(reply_markup=get_warn_settings_menu(group))
        await call.answer()

    elif action == "ttl_adjust":
        category = data_parts[2]
        delta = int(data_parts[3])
        if category == "mod":
            ttl.mod_ttl = max(0, min(300, ttl.mod_ttl + delta))
        elif category == "fun":
            ttl.fun_ttl = max(0, min(300, ttl.fun_ttl + delta))
        elif category == "rules":
            ttl.rules_ttl = max(0, min(300, ttl.rules_ttl + delta))

        await session.commit()
        if call.message:
            await call.message.edit_reply_markup(reply_markup=get_ttl_menu(group, ttl))
        await call.answer("Timer adjusted!")

    elif action == "warn_adjust":
        delta = int(data_parts[3])
        group.max_warns = max(1, min(10, group.max_warns + delta))
        await session.commit()
        if call.message:
            await call.message.edit_reply_markup(reply_markup=get_warn_settings_menu(group))
        await call.answer("Warn limit adjusted!")
