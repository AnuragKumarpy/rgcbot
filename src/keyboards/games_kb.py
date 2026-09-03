from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_duel_keyboard(challenger_id: int, opponent_id: int, amount: int) -> InlineKeyboardMarkup:
    """Inline keyboard for accepting or declining a dice duel challenge with Bot API 9.4 styles."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Accept Duel",
                    callback_data=f"duel:accept:{challenger_id}:{opponent_id}:{amount}",
                    style="success",
                    icon_custom_emoji_id="5456140674028019486",
                ),
                InlineKeyboardButton(
                    text="Decline",
                    callback_data=f"duel:decline:{challenger_id}:{opponent_id}:{amount}",
                    style="danger",
                    icon_custom_emoji_id="5240241223632954241",
                ),
            ]
        ]
    )
