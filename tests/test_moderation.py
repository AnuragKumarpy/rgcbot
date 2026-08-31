import pytest
from unittest.mock import AsyncMock, MagicMock
from src.core.enums import ActionType
from src.keyboards.moderation_kb import (
    get_ban_undo_keyboard,
    get_mute_undo_keyboard,
    get_warn_undo_keyboard,
)
from src.models.group import Group
from src.models.user import User
from src.services.moderation_service import ModerationService


def test_moderation_keyboards():
    mute_kb = get_mute_undo_keyboard(-100123456, 999888)
    assert mute_kb.inline_keyboard[0][0].callback_data == "undo:unmute:-100123456:999888"
    assert mute_kb.inline_keyboard[0][0].text == "Unmute"
    assert getattr(mute_kb.inline_keyboard[0][0], "style", None) == "success"

    ban_kb = get_ban_undo_keyboard(-100123456, 999888)
    assert ban_kb.inline_keyboard[0][0].callback_data == "undo:unban:-100123456:999888"
    assert ban_kb.inline_keyboard[0][0].text == "Unban"
    assert getattr(ban_kb.inline_keyboard[0][0], "style", None) == "success"

    warn_kb = get_warn_undo_keyboard(-100123456, 999888)
    assert warn_kb.inline_keyboard[0][0].callback_data == "undo:unwarn:-100123456:999888"
    assert warn_kb.inline_keyboard[0][0].text == "Undo Warn"
    assert getattr(warn_kb.inline_keyboard[0][0], "style", None) == "primary"
