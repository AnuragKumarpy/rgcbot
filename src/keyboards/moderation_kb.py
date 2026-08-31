from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_mute_undo_keyboard(chat_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Unmute",
                    callback_data=f"undo:unmute:{chat_id}:{user_id}",
                    style="success",
                    icon_custom_emoji_id="5458603043203327669",
                )
            ]
        ]
    )


def get_ban_undo_keyboard(chat_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Unban",
                    callback_data=f"undo:unban:{chat_id}:{user_id}",
                    style="success",
                    icon_custom_emoji_id="5251203410396458957",
                )
            ]
        ]
    )


def get_warn_undo_keyboard(chat_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Undo Warn",
                    callback_data=f"undo:unwarn:{chat_id}:{user_id}",
                    style="primary",
                    icon_custom_emoji_id="5237699328843200968",
                )
            ]
        ]
    )
