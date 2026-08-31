from typing import Optional
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import TTLType
from src.middlewares.ttl import reply_with_ttl
from src.models.group import Group
from src.services.zombie_cleaner_service import ZombieCleanerService
from src.utils.emojis import E_SEARCH, E_SHIELD, E_SPARKLES, E_STOP
from src.utils.permissions import can_restrict as check_can_restrict
from src.utils.text_formatter import format_card, get_user_mention

router = Router(name="admin_zombies")


@router.message(Command("zombies", "cleanzombies", "kickdeleted", "cleandeleted"))
async def handle_zombies_command(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    can_restrict: bool = False,
    is_admin: bool = False,
):
    if not db_group or not session or not message.bot:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not is_admin and not can_restrict:
        await reply_with_ttl(
            message,
            "❌ You do not have permission to manage members.",
            ttl_type=TTLType.MODERATION,
        )
        return

    # Check bot permissions
    try:
        bot_member = await message.bot.get_chat_member(chat_id=db_group.chat_id, user_id=message.bot.id)
        if not check_can_restrict(bot_member, message.bot.id):
            await reply_with_ttl(
                message,
                "❌ Bot needs <b>'Ban Users'</b> administrator rights to purge deleted accounts.",
                ttl_type=TTLType.MODERATION,
            )
            return
    except Exception:
        pass

    parts = message.text.split()
    action = parts[1].lower() if len(parts) > 1 else None

    # Immediate clean if "/zombies clean" or "/cleanzombies"
    if action in ("clean", "purge", "kick") or "clean" in parts[0] or "kick" in parts[0]:
        status_msg = await message.answer(f"{E_SEARCH} <b>Scanning and purging deleted accounts...</b>", parse_mode="HTML")
        cleaned, total = await ZombieCleanerService.clean_zombies(
            bot=message.bot,
            session=session,
            group=db_group,
            admin_user_id=message.from_user.id if message.from_user else 0,
            admin_user_name=message.from_user.full_name if message.from_user else "Admin",
        )
        card = format_card(
            title=f"{E_SHIELD} ZOMBIE ACCOUNTS PURGED",
            fields=[
                ("Chat", db_group.title),
                ("Deleted Accounts Removed", f"<b>{cleaned}</b>"),
                ("Admin", get_user_mention(message.from_user)),
            ],
            footer="Group member list is authentic and clean.",
        )
        try:
            await status_msg.delete()
        except Exception:
            pass
        await reply_with_ttl(message, card, ttl_type=TTLType.MODERATION)
        return

    # Dry-run scan
    status_msg = await message.answer(f"{E_SEARCH} <b>Scanning group for deleted accounts...</b>", parse_mode="HTML")
    zombie_ids = await ZombieCleanerService.scan_zombies(
        bot=message.bot,
        session=session,
        chat_id=db_group.chat_id,
    )
    try:
        await status_msg.delete()
    except Exception:
        pass

    count = len(zombie_ids)
    if count == 0:
        await reply_with_ttl(
            message,
            f"{E_SPARKLES} <b>No deleted accounts found!</b> The group member roster is completely clean.",
            ttl_type=TTLType.MODERATION,
        )
        return

    card = format_card(
        title=f"{E_STOP} ZOMBIE ACCOUNTS DETECTED",
        fields=[
            ("Group", db_group.title),
            ("Deleted Accounts", f"<b>{count}</b>"),
        ],
        footer="Click below to remove all deleted accounts from this group.",
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"✅ Yes, Purge {count} Zombies",
                    callback_data=f"zombies:clean:{db_group.chat_id}:{message.from_user.id if message.from_user else 0}",
                    style="danger",
                    icon_custom_emoji_id="5237699328843200968",
                ),
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data=f"cancel:zombies:{message.from_user.id if message.from_user else 0}",
                    style="primary",
                    icon_custom_emoji_id="5260293700088511294",
                ),
            ]
        ]
    )
    await reply_with_ttl(message, card, ttl_type=TTLType.MODERATION, reply_markup=kb)


@router.callback_query(F.data.startswith("zombies:clean:"))
async def handle_zombies_clean_callback(
    call: CallbackQuery,
    session: Optional[AsyncSession] = None,
    can_restrict: bool = False,
    is_admin: bool = False,
):
    if not session or not call.message or not call.from_user or not call.bot:
        return

    parts = call.data.split(":")
    chat_id = int(parts[2])
    admin_id = int(parts[3]) if len(parts) > 3 else 0

    from src.utils.permissions import is_super_admin
    if admin_id and call.from_user.id != admin_id and not is_super_admin(call.from_user.id):
        await call.answer("❌ Only the admin who initiated the scan can confirm.", show_alert=True)
        return

    if not is_admin and not can_restrict and not is_super_admin(call.from_user.id):
        await call.answer("❌ Only administrators can remove members.", show_alert=True)
        return

    res = await session.execute(select(Group).where(Group.chat_id == chat_id))
    group = res.scalar_one_or_none()
    if not group:
        group = Group(chat_id=chat_id, title=call.message.chat.title or "Group")

    await call.message.edit_text(f"{E_SEARCH} <b>Purging deleted accounts...</b>", parse_mode="HTML")
    cleaned, total = await ZombieCleanerService.clean_zombies(
        bot=call.bot,
        session=session,
        group=group,
        admin_user_id=call.from_user.id,
        admin_user_name=call.from_user.full_name or call.from_user.first_name,
    )
    card = format_card(
        title=f"{E_SHIELD} ZOMBIE ACCOUNTS PURGED",
        fields=[
            ("Chat", group.title),
            ("Deleted Accounts Removed", f"<b>{cleaned}</b>"),
            ("Admin", get_user_mention(call.from_user)),
        ],
        footer="Group member list is authentic and clean.",
    )
    await call.message.edit_text(card, parse_mode="HTML")
    await call.answer("✅ Cleanup completed!")


@router.callback_query(F.data.startswith("cancel:zombies:"))
async def handle_zombies_cancel_callback(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    parts = call.data.split(":")
    admin_id = int(parts[-1]) if len(parts) > 2 else 0

    from src.utils.permissions import is_super_admin
    if admin_id and call.from_user.id != admin_id and not is_super_admin(call.from_user.id):
        await call.answer("❌ Only the admin who initiated the scan can cancel.", show_alert=True)
        return

    try:
        await call.message.edit_text("❌ <b>Zombie cleanup cancelled.</b>", parse_mode="HTML")
    except Exception:
        pass
    await call.answer("Cancelled.")

