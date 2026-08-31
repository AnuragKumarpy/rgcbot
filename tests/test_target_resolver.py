from datetime import datetime
import pytest
from aiogram.enums import MessageEntityType
from aiogram.types import Chat, Message, MessageEntity, User as TgUser
from src.models.user import User
from src.utils.target_resolver import resolve_target


@pytest.mark.asyncio
async def test_resolve_target_from_reply():
    reply_user = TgUser(id=111222, is_bot=False, first_name="TargetUser", username="target_u")
    reply_msg = Message(
        message_id=10,
        date=datetime.now(),
        chat=Chat(id=-1001, type="supergroup"),
        from_user=reply_user,
    )
    cmd_msg = Message(
        message_id=11,
        date=datetime.now(),
        chat=Chat(id=-1001, type="supergroup"),
        from_user=TgUser(id=999, is_bot=False, first_name="Admin"),
        reply_to_message=reply_msg,
        text="/ban Rule violation",
    )

    res = await resolve_target(cmd_msg)
    assert res is not None
    assert res.user_id == 111222
    assert res.first_name == "TargetUser"
    assert res.username == "target_u"
    assert res.from_reply is True
    assert res.remaining_args == ["Rule", "violation"]


@pytest.mark.asyncio
async def test_resolve_target_from_numeric_id():
    cmd_msg = Message(
        message_id=12,
        date=datetime.now(),
        chat=Chat(id=-1001, type="supergroup"),
        from_user=TgUser(id=999, is_bot=False, first_name="Admin"),
        text="/mute 8713594643 30m Spamming",
    )

    res = await resolve_target(cmd_msg)
    assert res is not None
    assert res.user_id == 8713594643
    assert res.from_reply is False
    assert res.remaining_args == ["30m", "Spamming"]


@pytest.mark.asyncio
async def test_resolve_target_from_numeric_id_with_prefix():
    cmd_msg = Message(
        message_id=13,
        date=datetime.now(),
        chat=Chat(id=-1001, type="supergroup"),
        from_user=TgUser(id=999, is_bot=False, first_name="Admin"),
        text="/unban id:8713594643",
    )

    res = await resolve_target(cmd_msg)
    assert res is not None
    assert res.user_id == 8713594643
    assert res.remaining_args == []


@pytest.mark.asyncio
async def test_resolve_target_from_text_mention():
    mentioned_tg = TgUser(id=555666, is_bot=False, first_name="MentionedGuy", username=None)
    entity = MessageEntity(
        type=MessageEntityType.TEXT_MENTION,
        offset=6,
        length=12,
        user=mentioned_tg,
    )
    cmd_msg = Message(
        message_id=14,
        date=datetime.now(),
        chat=Chat(id=-1001, type="supergroup"),
        from_user=TgUser(id=999, is_bot=False, first_name="Admin"),
        text="/warn MentionedGuy 2nd warning",
        entities=[entity],
    )

    res = await resolve_target(cmd_msg)
    assert res is not None
    assert res.user_id == 555666
    assert res.first_name == "MentionedGuy"
    assert res.from_reply is False
    assert res.remaining_args == ["2nd", "warning"]
