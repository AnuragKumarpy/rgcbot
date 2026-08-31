import io
import pytest
from PIL import Image
from src.keyboards.quote_kb import get_quote_reaction_keyboard
from src.models.quote import Quote
from src.services.quote_service import QuoteColorTheme, QuoteMessageData, QuoteService


def test_quote_args_parsing():
    # Test color + reply + count combinations
    color, rep, count = QuoteService.parse_quote_args(["r", "pink", "3"])
    assert color == "pink"
    assert rep is True
    assert count == 3

    color, rep, count = QuoteService.parse_quote_args(["blue", "2"])
    assert color == "blue"
    assert rep is False
    assert count == 2

    color, rep, count = QuoteService.parse_quote_args(["reply", "#FF007F"])
    assert color == "#ff007f"
    assert rep is True
    assert count == 1

    color, rep, count = QuoteService.parse_quote_args(["gold"])
    assert color == "gold"
    assert rep is False
    assert count == 1


def test_quote_theme_resolution():
    theme_dark = QuoteColorTheme.get_theme("dark")
    assert "bg" in theme_dark
    assert "name" in theme_dark

    theme_pink = QuoteColorTheme.get_theme("pink")
    assert theme_pink["name"] == (255, 110, 185)

    theme_hex = QuoteColorTheme.get_theme("#00FF88")
    assert theme_hex["name"] == (0, 255, 136)


def test_clean_emoji_text():
    # Standard text with unicode emojis
    text = "Hello world 🔥 💎 👑"
    assert QuoteService.clean_emoji_text(text) == "Hello world 🔥 💎 👑"

    # Custom / Premium Telegram emoji tags
    premium_text = 'Check this out <tg-emoji emoji-id="5368324170671202286">🔥</tg-emoji> and <tg-emoji emoji-id="12345">💎</tg-emoji>!'
    assert QuoteService.clean_emoji_text(premium_text) == "Check this out 🔥 and 💎!"

    # HTML tags stripping
    html_text = "<b>Bold text</b> with <i>italics</i>"
    assert QuoteService.clean_emoji_text(html_text) == "Bold text with italics"


def test_quote_reaction_keyboard():
    kb = get_quote_reaction_keyboard(quote_id=42, likes=5, dislikes=2)
    assert len(kb.inline_keyboard) == 1
    assert len(kb.inline_keyboard[0]) == 2
    assert kb.inline_keyboard[0][0].text == "👍 5"
    assert kb.inline_keyboard[0][0].callback_data == "quote_react:like:42"
    assert kb.inline_keyboard[0][1].text == "👎 2"
    assert kb.inline_keyboard[0][1].callback_data == "quote_react:dislike:42"

    kb_zero = get_quote_reaction_keyboard(quote_id=42, likes=0, dislikes=0)
    assert kb_zero.inline_keyboard[0][0].text == "👍"
    assert kb_zero.inline_keyboard[0][1].text == "👎"


def test_generate_single_quote_image():
    msg = QuoteMessageData(
        message_id=100,
        user_id=12345,
        first_name="Alice 🔥",
        username="alice",
        text="Hello, this is a test quote sticker with emojis! 💎 👑 ❤️",
        date_str="14:30",
        avatar_img=None,
        reply_user_name=None,
        reply_text=None,
    )

    bio = QuoteService.generate_quote_image([msg], color_key="pink", include_reply=False)
    assert isinstance(bio, io.BytesIO)
    bio.seek(0)

    img = Image.open(bio)
    assert img.format == "WEBP"
    assert max(img.width, img.height) == 512
    assert min(img.width, img.height) <= 512


def test_generate_quote_image_with_reply():
    msg = QuoteMessageData(
        message_id=101,
        user_id=12345,
        first_name="Bob",
        username="bob",
        text="I totally agree with what you said earlier. 🚀",
        date_str="15:45",
        avatar_img=None,
        reply_user_name="Alice 🔥",
        reply_text="Should we launch the new feature today? 💎",
    )

    bio = QuoteService.generate_quote_image([msg], color_key="blue", include_reply=True)
    bio.seek(0)
    img = Image.open(bio)
    assert img.format == "WEBP"
    assert max(img.width, img.height) == 512


def test_generate_multi_message_quote_image():
    msgs = [
        QuoteMessageData(
            message_id=102,
            user_id=12345,
            first_name="Charlie",
            username="charlie",
            text="Message part 1: Introduction to the plan. 🌟",
            date_str="16:00",
        ),
        QuoteMessageData(
            message_id=103,
            user_id=12345,
            first_name="Charlie",
            username="charlie",
            text="Message part 2: Detailed architecture and steps. ⚡",
            date_str="16:01",
        ),
    ]

    bio = QuoteService.generate_quote_image(msgs, color_key="gold", include_reply=False)
    bio.seek(0)
    img = Image.open(bio)
    assert img.format == "WEBP"
    assert max(img.width, img.height) == 512
