from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_quote_reaction_keyboard(quote_id: int, likes: int = 0, dislikes: int = 0) -> InlineKeyboardMarkup:
    """Builds inline keyboard with interactive Like and Dislike buttons for quote stickers."""
    like_text = f"👍 {likes}" if likes > 0 else "👍"
    dislike_text = f"👎 {dislikes}" if dislikes > 0 else "👎"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=like_text,
                    callback_data=f"quote_react:like:{quote_id}",
                ),
                InlineKeyboardButton(
                    text=dislike_text,
                    callback_data=f"quote_react:dislike:{quote_id}",
                ),
            ]
        ]
    )
