from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from src.utils.emojis import E_ALERT, E_CHECK, E_CROSS, E_LOCK, E_SHIELD, E_STOP
from src.utils.text_formatter import format_card, get_user_mention


def get_confirmation_keyboard(
    action_key: str,
    admin_id: int,
    confirm_text: str = "Yes, Proceed",
    cancel_text: str = "Cancel",
    confirm_style: str = "danger",
) -> InlineKeyboardMarkup:
    """
    Returns a standardized Yes / No confirmation inline keyboard with Telegram Bot API 9.4 styles.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"✅ {confirm_text}",
                    callback_data=f"confirm:{action_key}:{admin_id}",
                    style=confirm_style,
                    icon_custom_emoji_id="5237699328843200968",
                ),
                InlineKeyboardButton(
                    text=f"❌ {cancel_text}",
                    callback_data=f"cancel:{action_key}:{admin_id}",
                    style="primary",
                    icon_custom_emoji_id="5260293700088511294",
                ),
            ]
        ]
    )
