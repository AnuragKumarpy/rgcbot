from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, User as TgUser
from loguru import logger
from src.middlewares.ttl import schedule_auto_delete
from src.models.group import Group
from src.utils.text_formatter import get_user_mention, mention_html


class WelcomeService:
    @classmethod
    def parse_welcome_buttons(cls, raw_buttons: Optional[str]) -> Optional[InlineKeyboardMarkup]:
        if not raw_buttons:
            return None
        keyboard = []
        for line in raw_buttons.strip().split("\n"):
            row = []
            parts = line.split("|")
            if len(parts) >= 2:
                btn_text = parts[0].strip()
                btn_url = parts[1].strip()
                if btn_text and btn_url:
                    row.append(InlineKeyboardButton(text=btn_text, url=btn_url))
            if row:
                keyboard.append(row)
        return InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None

    @classmethod
    def format_welcome_text(cls, template: str, user: TgUser, group: Group) -> str:
        from src.utils.emojis import animate_text

        mention = get_user_mention(user)
        text = template.replace("{mention}", mention)
        text = text.replace("{name}", user.first_name or "Member")
        text = text.replace("{username}", f"@{user.username}" if user.username else "")
        text = text.replace("{id}", str(user.id))
        text = text.replace("{chat_title}", group.title)
        return animate_text(text)

    @classmethod
    async def send_welcome(
        cls,
        bot: Bot,
        group: Group,
        user: TgUser,
    ) -> Optional[Message]:
        if not group.welcome_enabled:
            return None

        formatted_caption = cls.format_welcome_text(group.welcome_text, user, group)

        # Attach green Check Rules button on downside of welcome message
        bot_info = await bot.get_me()
        rules_url = f"https://t.me/{bot_info.username}?start=rules_{group.chat_id}"
        rules_btn = InlineKeyboardButton(
            text="🟢 Check Rules",
            url=rules_url,
            style="success",
            icon_custom_emoji_id="5237699328843200968",
        )

        custom_kb = cls.parse_welcome_buttons(group.welcome_buttons)
        if custom_kb and custom_kb.inline_keyboard:
            rows = [list(r) for r in custom_kb.inline_keyboard]
            rows.append([rules_btn])
            kb = InlineKeyboardMarkup(inline_keyboard=rows)
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[[rules_btn]])

        sent_msg = None
        try:
            if group.welcome_media_type == "photo" and group.welcome_media_file_id:
                sent_msg = await bot.send_photo(
                    chat_id=group.chat_id,
                    photo=group.welcome_media_file_id,
                    caption=formatted_caption,
                    parse_mode="HTML",
                    reply_markup=kb,
                )
            elif group.welcome_media_type == "video" and group.welcome_media_file_id:
                sent_msg = await bot.send_video(
                    chat_id=group.chat_id,
                    video=group.welcome_media_file_id,
                    caption=formatted_caption,
                    parse_mode="HTML",
                    reply_markup=kb,
                )
            elif group.welcome_media_type == "animation" and group.welcome_media_file_id:
                sent_msg = await bot.send_animation(
                    chat_id=group.chat_id,
                    animation=group.welcome_media_file_id,
                    caption=formatted_caption,
                    parse_mode="HTML",
                    reply_markup=kb,
                )
            else:
                sent_msg = await bot.send_message(
                    chat_id=group.chat_id,
                    text=formatted_caption,
                    parse_mode="HTML",
                    reply_markup=kb,
                )

            if sent_msg:
                # Schedule auto-delete
                ttl_sec = max(15, min(300, group.captcha_timeout_sec))
                await schedule_auto_delete(group.chat_id, sent_msg.message_id, ttl_sec)

        except Exception as e:
            logger.warning(f"Failed to send rich welcome message in {group.chat_id}: {e}")

        return sent_msg
