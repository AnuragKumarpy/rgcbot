import random
from typing import List, Tuple
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_button_captcha_keyboard(chat_id: int, user_id: int) -> InlineKeyboardMarkup:
    """Returns a simple one-click verification button with Bot API 9.4 success style and custom emoji."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Click here to verify you're human",
                    callback_data=f"captcha:btn:{chat_id}:{user_id}",
                    style="success",
                    icon_custom_emoji_id="5251203410396458957",
                )
            ]
        ]
    )


def get_math_captcha_keyboard(
    chat_id: int, user_id: int, correct_answer: int
) -> Tuple[InlineKeyboardMarkup, str]:
    """
    Generates a math problem (e.g. '12 + 5 = ?') and an inline keyboard with 4 choices.
    Returns: (InlineKeyboardMarkup, question_text)
    """
    a = random.randint(3, 20)
    b = random.randint(2, 15)
    answer = a + b
    question = f"{a} + {b} = ?"

    # Generate 3 distinct wrong answers
    wrong_answers = set()
    while len(wrong_answers) < 3:
        offset = random.choice([-3, -2, -1, 1, 2, 3, 4])
        wrong = answer + offset
        if wrong > 0 and wrong != answer:
            wrong_answers.add(wrong)

    options = list(wrong_answers) + [answer]
    random.shuffle(options)

    buttons = []
    for opt in options:
        is_correct = "1" if opt == answer else "0"
        buttons.append(
            InlineKeyboardButton(
                text=str(opt),
                callback_data=f"captcha:math:{chat_id}:{user_id}:{is_correct}",
                style="primary",
                icon_custom_emoji_id="5237699328843200968",
            )
        )

    # 2 rows of 2 buttons
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [buttons[0], buttons[1]],
            [buttons[2], buttons[3]],
        ]
    )

    return keyboard, question
