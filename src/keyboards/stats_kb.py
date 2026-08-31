from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

EMOJI_CALENDAR = "5413879192267805083"   # 📅
EMOJI_TOP = "5418085807791545980"        # 🔝
EMOJI_MONTH = "5251537301154062376"      # 📆
EMOJI_CROWN = "5217822164362739968"      # 👑


def get_stats_keyboard(active_timeframe: str = "today") -> InlineKeyboardMarkup:
    """Builds interactive buttons with Telegram Premium animated custom emoji icons."""
    def mark(key: str, label: str) -> str:
        return f"• {label} •" if key == active_timeframe else label

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=mark("today", "Today"),
                    callback_data="stats_view:today",
                    icon_custom_emoji_id=EMOJI_CALENDAR,
                ),
                InlineKeyboardButton(
                    text=mark("weekly", "Weekly"),
                    callback_data="stats_view:weekly",
                    icon_custom_emoji_id=EMOJI_TOP,
                ),
            ],
            [
                InlineKeyboardButton(
                    text=mark("monthly", "Monthly"),
                    callback_data="stats_view:monthly",
                    icon_custom_emoji_id=EMOJI_MONTH,
                ),
                InlineKeyboardButton(
                    text=mark("all_time", "All-Time"),
                    callback_data="stats_view:all_time",
                    icon_custom_emoji_id=EMOJI_CROWN,
                ),
            ],
        ]
    )
