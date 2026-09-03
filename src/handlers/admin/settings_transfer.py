from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import TTLType
from src.middlewares.ttl import reply_with_ttl
from src.models.group import Group
from src.services.settings_transfer_service import SettingsTransferService
from src.utils.emojis import E_ROCKET, E_SHIELD, E_SPARKLES, animate_text

router = Router(name="admin_settings_transfer")


@router.message(Command("exportsettings", "copysettings", "backupcfg"))
async def handle_export_settings(
    message: Message,
    is_admin: bool = False,
    session: Optional[AsyncSession] = None,
):
    if not is_admin:
        await reply_with_ttl(message, "❌ Admin rights required.", ttl_type=TTLType.MODERATION)
        return
    if not session or message.chat.id >= 0:
        return

    try:
        cfg_code = await SettingsTransferService.export_settings(session, message.chat.id)
        text = animate_text(
            f"{E_SPARKLES} <b>Group Configuration Exported!</b>\n\n"
            "This portable code contains your group's complete configuration:\n"
            "• <b>Welcome Gate:</b> Text, media & buttons\n"
            "• <b>Captcha & Anti-Spam:</b> Settings & limits\n"
            "• <b>Content Locks:</b> Media locks, CleanService & Anti-Channel\n"
            "• <b>TTL Timers & Filters:</b> Auto-destruct & regex filters\n\n"
            "📋 <b>Copy & apply to any group using:</b>\n"
            f"<code>/importsettings {cfg_code}</code>\n\n"
            f"<code>{cfg_code}</code>"
        )
        await reply_with_ttl(message, text, ttl_type=TTLType.MODERATION)
    except Exception as e:
        logger.error(f"Failed to export settings: {e}")
        await reply_with_ttl(
            message, f"❌ Failed to export settings: {e}", ttl_type=TTLType.MODERATION
        )


@router.message(Command("importsettings", "applysettings", "restorecfg"))
async def handle_import_settings(
    message: Message,
    is_admin: bool = False,
    session: Optional[AsyncSession] = None,
):
    if not is_admin:
        await reply_with_ttl(message, "❌ Admin rights required.", ttl_type=TTLType.MODERATION)
        return
    if not session or message.chat.id >= 0:
        return

    args = message.text.split()[1:] if message.text else []
    cfg_code = None

    if args:
        cfg_code = args[0]
    elif message.reply_to_message and message.reply_to_message.text:
        lines = message.reply_to_message.text.split()
        for l in lines:
            if "RGC-CFG-" in l:
                cfg_code = l
                break

    if not cfg_code:
        await reply_with_ttl(
            message,
            "<b>Usage:</b> <code>/importsettings &lt;config_code&gt;</code>\n"
            "<i>(You can also reply to a message containing the config code with <code>/importsettings</code>)</i>",
            ttl_type=TTLType.MODERATION,
        )
        return

    try:
        summary = await SettingsTransferService.import_settings(session, message.chat.id, cfg_code)
        text = animate_text(
            f"{E_SHIELD} <b>Settings Successfully Imported & Applied!</b>\n\n"
            f"• <b>Welcome Gate:</b> {'<code>ENABLED</code> 🟢' if summary['welcome_enabled'] else '<code>DISABLED</code> 🔴'}\n"
            f"• <b>Captcha Mode:</b> <code>{summary['captcha_mode']}</code>\n"
            f"• <b>Active Locks:</b> <code>{summary['locked_count']} types</code>\n"
            f"• <b>CleanService:</b> {'<code>ENABLED</code> 🟢' if summary['clean_service'] else '<code>DISABLED</code> 🔴'}\n"
            f"• <b>AntiChannel:</b> {'<code>ENABLED</code> 🟢' if summary['antichannel'] else '<code>DISABLED</code> 🔴'}\n"
            f"• <b>Imported Filters:</b> <code>{summary['filters_count']}</code>\n"
            f"• <b>Imported Blocklist:</b> <code>{summary['blocklist_count']} terms</code>\n\n"
            "✨ <i>All protections and modules are now live in this group.</i>"
        )
        await reply_with_ttl(message, text, ttl_type=TTLType.MODERATION)
    except Exception as e:
        logger.error(f"Failed to import settings: {e}")
        await reply_with_ttl(
            message, f"❌ Failed to import settings: {e}", ttl_type=TTLType.MODERATION
        )
