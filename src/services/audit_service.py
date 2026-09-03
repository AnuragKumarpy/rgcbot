from datetime import datetime
from typing import Optional
from aiogram import Bot
from loguru import logger
from src.config.settings import settings
from src.core.enums import ActionType
from src.utils.text_formatter import escape_html, mention_html


class AuditService:
    @staticmethod
    async def log_action(
        bot: Bot,
        chat_id: int,
        chat_title: str,
        target_user_id: int,
        target_user_name: str,
        admin_user_id: Optional[int] = None,
        admin_user_name: Optional[str] = None,
        action: ActionType = ActionType.WARN,
        reason: Optional[str] = None,
        duration_str: Optional[str] = None,
        channel_id: Optional[int] = None,
    ):
        target_channel = channel_id or settings.default_log_channel_id
        if not target_channel:
            return

        action_icons = {
            ActionType.BAN: "🔨 <b>USER BANNED</b>",
            ActionType.TEMPBAN: "⏳ <b>USER TEMP BANNED</b>",
            ActionType.MUTE: "🔇 <b>USER MUTED</b>",
            ActionType.TEMPMUTE: "⏳ <b>USER TEMP MUTED</b>",
            ActionType.KICK: "👢 <b>USER KICKED</b>",
            ActionType.WARN: "⚠️ <b>USER WARNED</b>",
            ActionType.UNBAN: "🔓 <b>USER UNBANNED</b>",
            ActionType.UNMUTE: "🔊 <b>USER UNMUTED</b>",
            ActionType.RESET_WARNS: "🔄 <b>WARNS RESET</b>",
            ActionType.PURGE: "🧹 <b>MESSAGES PURGED</b>",
            ActionType.ANTISPAM_TRIGGER: "🛡️ <b>ANTI-SPAM TRIGGER</b>",
            ActionType.CAPTCHA_FAIL: "🤖 <b>CAPTCHA TIMEOUT (KICKED)</b>",
            ActionType.CAPTCHA_PASS: "✅ <b>CAPTCHA VERIFIED</b>",
            ActionType.USER_JOIN: "👋 <b>MEMBER JOINED</b>",
            ActionType.USER_LEAVE: "🚪 <b>MEMBER LEFT</b>",
            ActionType.BOT_START: "🚀 <b>BOT STARTED</b>",
            ActionType.RULES_UPDATE: "📜 <b>RULES UPDATED</b>",
            ActionType.SETTINGS_CHANGE: "⚙️ <b>SETTINGS CHANGED</b>",
            ActionType.GAME_PLAY: "🎮 <b>GAME OUTCOME</b>",
            ActionType.COMMAND_USE: "⚡ <b>COMMAND EXECUTED</b>",
            ActionType.KARMA_AWARD: "🌟 <b>REPUTATION AWARDED</b>",
            ActionType.DAILY_CLAIM: "💰 <b>DAILY REWARD CLAIMED</b>",
            ActionType.BLOCKLIST_TRIGGER: "🚫 <b>BLOCKLIST INTERCEPTED</b>",
            ActionType.TOS_TRIGGER: "🚨 <b>TOS ZERO-TOLERANCE SHIELD</b>",
            ActionType.LANGUAGE_VIOLATION: "🌐 <b>LANGUAGE POLICY ENFORCED</b>",
            ActionType.ZOMBIE_PURGE: "🧟 <b>ZOMBIE ACCOUNTS PURGED</b>",
            ActionType.PANIC_MODE: "🚨 <b>ANTI-RAID PANIC TOGGLED</b>",
        }

        header = action_icons.get(action, f"📋 <b>{action.value.upper()}</b>")
        target_mention = (
            mention_html(target_user_id, target_user_name)
            if target_user_id != 0
            else f"<b>{escape_html(target_user_name)}</b>"
        )
        admin_mention = (
            mention_html(admin_user_id, admin_user_name)
            if admin_user_id
            else "<i>🤖 Automated System</i>"
        )

        lines = [
            f"{header}",
            f"<b>Chat:</b> {escape_html(chat_title)} [<code>{chat_id}</code>]",
            f"<b>Subject:</b> {target_mention} [<code>{target_user_id}</code>]",
            f"<b>Executor:</b> {admin_mention}",
        ]

        if duration_str:
            lines.append(f"<b>Duration:</b> {duration_str}")
        if reason:
            lines.append(f"<b>Details:</b> {escape_html(reason)}")

        lines.append(f"<b>Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

        from src.utils.emojis import animate_text

        text = animate_text("\n".join(lines))

        try:
            await bot.send_message(chat_id=target_channel, text=text, parse_mode="HTML")
            logger.info(f"Audit log sent to {target_channel} [{action.value}]")
        except Exception as e:
            logger.warning(
                f"Failed to send log to channel {target_channel}: {e}. Ensure bot is an Admin in the log channel."
            )
