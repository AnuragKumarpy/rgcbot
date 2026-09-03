from unittest.mock import AsyncMock, MagicMock
import pytest
from src.keyboards.help_kb import get_help_back_keyboard, get_help_main_keyboard
from src.models.federation import (
    Federation,
    FederationAdmin,
    FederationBan,
    FederationGroup,
    generate_fed_id,
)
from src.services.federation_service import FederationService


def test_federation_models():
    fed_id = generate_fed_id()
    assert len(fed_id) == 12

    fed = Federation(fed_id=fed_id, name="Elite Federation", owner_id=123456)
    assert fed.fed_id == fed_id
    assert fed.name == "Elite Federation"
    assert fed.owner_id == 123456

    fed_admin = FederationAdmin(fed_id=fed_id, user_id=999888)
    assert fed_admin.fed_id == fed_id
    assert fed_admin.user_id == 999888

    fed_grp = FederationGroup(fed_id=fed_id, chat_id=-1001928374)
    assert fed_grp.fed_id == fed_id
    assert fed_grp.chat_id == -1001928374

    fed_ban = FederationBan(fed_id=fed_id, user_id=777666, reason="Spam raid", banned_by_id=123456)
    assert fed_ban.fed_id == fed_id
    assert fed_ban.user_id == 777666
    assert fed_ban.reason == "Spam raid"


def test_help_keyboards():
    main_kb = get_help_main_keyboard()
    assert main_kb is not None
    assert len(main_kb.inline_keyboard) >= 5

    # Check categories exist
    callbacks = [b.callback_data for row in main_kb.inline_keyboard for b in row]
    assert "help:defense" in callbacks
    assert "help:tagging" in callbacks
    assert "help:federation" in callbacks
    assert "help:locks" in callbacks
    assert "help:reputation" in callbacks
    assert "help:games" in callbacks
    assert "help:settings" in callbacks
    assert "help:faq" in callbacks
    assert "help:manual" in callbacks

    back_kb = get_help_back_keyboard()
    assert back_kb is not None
    back_callbacks = [b.callback_data for row in back_kb.inline_keyboard for b in row]
    assert "dm:help" in back_callbacks
    assert "dm:menu" in back_callbacks


@pytest.mark.asyncio
async def test_federation_service_mocked():
    session = AsyncMock()

    # Test create federation
    fed = await FederationService.create_federation(session, owner_id=1001, name="Test Fed")
    assert fed.name == "Test Fed"
    assert fed.owner_id == 1001
    assert session.add.called
    assert session.commit.called
