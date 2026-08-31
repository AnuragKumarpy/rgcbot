import re
from aiogram import Bot
from aiogram.types import Message
from src.middlewares.ttl import schedule_auto_delete
from src.models.group import Group
from src.utils.text_formatter import mention_html

# Matches non-Latin / non-ASCII non-punctuation alphabets (Arabic, Cyrillic, Chinese, Japanese, Korean, Devanagari, Hebrew, Thai, etc.)
NON_ENGLISH_SCRIPT_REGEX = re.compile(
    r"[\u0400-\u04FF\u0600-\u06FF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF\u0900-\u097F\u0590-\u05FF\u0E00-\u0E7F]"
)


class LanguageFilterService:
    @classmethod
    async def check_language(
        cls,
        bot: Bot,
        group: Group,
        message: Message,
    ) -> bool:
        """
        Checks if the message violates the English-only group policy.
        If violated: deletes the message and sends an ephemeral notice.
        Returns True if deleted.
        """
        if not group.english_only_enabled:
            return False

        text = message.text or message.caption or ""
        if not text:
            return False

        # If foreign non-Latin script detected
        if NON_ENGLISH_SCRIPT_REGEX.search(text):
            try:
                await message.delete()
            except Exception:
                pass

            user_id = message.from_user.id if message.from_user else 0
            user_name = message.from_user.first_name if message.from_user else "Member"
            notice = await message.answer(
                f"🌐 {mention_html(user_id, user_name)}, <b>English only</b> is permitted in this group.",
                parse_mode="HTML",
            )
            await schedule_auto_delete(group.chat_id, notice.message_id, 10)
            return True

        return False
