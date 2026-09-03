import html
from typing import Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, User as TgUser
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import TTLType
from src.middlewares.ttl import reply_with_ttl
from src.utils.emojis import E_ALERT, E_BAN, E_CHECK, E_CROSS, E_SHIELD, E_SIREN, animate_text


class ReportService:
    @classmethod
    def get_message_link(cls, chat_id: int, chat_username: Optional[str], message_id: int) -> str:
        if chat_username:
            return f"https://t.me/{chat_username}/{message_id}"
        clean_id = abs(chat_id)
        if str(clean_id).startswith("100"):
            clean_id = int(str(clean_id)[3:])
        return f"https://t.me/c/{clean_id}/{message_id}"

    @classmethod
    async def process_report(
        cls,
        bot: Bot,
        session: AsyncSession,
        message: Message,
        reporter: TgUser,
        reason: str = "Unspecified violation",
    ):
        """Dispatches moderation report to all active group administrators via DM and tags in-group."""
        chat = message.chat
        reply_to = message.reply_to_message

        reported_user = reply_to.from_user if reply_to else None
        target_msg_id = reply_to.message_id if reply_to else message.message_id
        msg_link = cls.get_message_link(chat.id, chat.username, target_msg_id)

        # 1. Reply in group with TTL auto-clean
        await reply_with_ttl(
            message,
            animate_text(
                f"{E_SIREN} <b>Report Submitted</b>\n"
                f"• <b>Reason:</b> <code>{html.escape(reason)}</code>\n"
                "<i>Admins have been notified.</i>"
            ),
            ttl_type=TTLType.MODERATION,
        )

        # 2. Format DM Report Card for Admins
        rep_name = html.escape(reporter.full_name)
        rep_user = f"@{reporter.username}" if reporter.username else "No username"

        if reported_user:
            tgt_name = html.escape(reported_user.full_name)
            tgt_user = f"@{reported_user.username}" if reported_user.username else "No username"
            target_info = (
                f'• <b>Reported User:</b> <a href="tg://user?id={reported_user.id}">{tgt_name}</a> ({tgt_user})\n'
                f"• <b>Target ID:</b> <code>{reported_user.id}</code>"
            )
        else:
            target_info = "• <b>Reported Item:</b> General Chat Violation"

        msg_content = ""
        if reply_to:
            snippet = reply_to.text or reply_to.caption or "[Media / Sticker / Attachment]"
            msg_content = f"\n• <b>Message Snippet:</b> <i>{html.escape(snippet[:120])}</i>"

        dm_text = animate_text(
            f"{E_SIREN} <b>MODERATION REPORT ALERT</b>\n\n"
            f"• <b>Group:</b> <b>{html.escape(chat.title or 'Group')}</b>\n"
            f"{target_info}\n"
            f"• <b>Reporter:</b> {rep_name} ({rep_user})\n"
            f"• <b>Reason:</b> <code>{html.escape(reason)}</code>"
            f"{msg_content}\n"
            f'• <b>Direct Link:</b> <a href="{msg_link}">Open Message ↗️</a>'
        )

        # 3. Action Keyboard for Admins in DM
        buttons = []
        if reported_user and not reported_user.is_bot:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="🔨 Ban User",
                        callback_data=f"rep_act:ban:{chat.id}:{reported_user.id}",
                    ),
                    InlineKeyboardButton(
                        text="🔇 Mute 24h",
                        callback_data=f"rep_act:mute:{chat.id}:{reported_user.id}",
                    ),
                ]
            )

        buttons.append(
            [
                InlineKeyboardButton(
                    text="🗑 Delete Message",
                    callback_data=f"rep_act:del:{chat.id}:{target_msg_id}",
                ),
                InlineKeyboardButton(
                    text="🛡 Dismiss",
                    callback_data="rep_act:dismiss",
                ),
            ]
        )
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

        # 4. Dispatch DM to all human administrators
        try:
            admins = await bot.get_chat_administrators(chat.id)
            for adm in admins:
                if adm.user.is_bot:
                    continue
                try:
                    await bot.send_message(
                        chat_id=adm.user.id,
                        text=dm_text,
                        reply_markup=kb,
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                except Exception as e:
                    logger.debug(f"Could not send report DM to admin {adm.user.id}: {e}")
        except Exception as e:
            logger.error(f"Failed to fetch administrators for report in {chat.id}: {e}")
