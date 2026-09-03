from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner, User as TgUser

from src.services.report_service import ReportService
from src.utils import permissions


@pytest.mark.asyncio
async def test_get_chat_member_safe_returns_none_on_exception():
    bot = SimpleNamespace(get_chat_member=AsyncMock(side_effect=RuntimeError("boom")))
    member = await permissions.get_chat_member_safe(bot, chat_id=-1001, user_id=10)
    assert member is None


def test_is_super_admin_and_admin_checks(monkeypatch):
    monkeypatch.setattr(permissions.settings, "bot_super_admins", [999])

    user = TgUser(id=1, is_bot=False, first_name="Admin")
    admin_member = ChatMemberAdministrator(
        user=user,
        can_be_edited=False,
        is_anonymous=False,
        can_manage_chat=True,
        can_delete_messages=True,
        can_manage_video_chats=True,
        can_restrict_members=False,
        can_promote_members=False,
        can_change_info=False,
        can_invite_users=True,
        can_post_stories=False,
        can_edit_stories=False,
        can_delete_stories=False,
        can_send_welcome_messages=False,
        can_pin_messages=False,
    )

    assert permissions.is_super_admin(999) is True
    assert permissions.is_admin(admin_member, 1) is True
    assert permissions.is_admin(None, 1) is False
    assert permissions.is_admin(None, 999) is True


def test_owner_and_permission_capability_checks(monkeypatch):
    monkeypatch.setattr(permissions.settings, "bot_super_admins", [])

    user = TgUser(id=7, is_bot=False, first_name="Owner")
    owner = ChatMemberOwner(user=user, is_anonymous=False)

    admin_limited = ChatMemberAdministrator(
        user=TgUser(id=8, is_bot=False, first_name="Limited"),
        can_be_edited=False,
        is_anonymous=False,
        can_manage_chat=True,
        can_delete_messages=False,
        can_manage_video_chats=True,
        can_restrict_members=True,
        can_promote_members=False,
        can_change_info=False,
        can_invite_users=True,
        can_post_stories=False,
        can_edit_stories=False,
        can_delete_stories=False,
        can_send_welcome_messages=False,
        can_pin_messages=False,
    )

    admin_full = ChatMemberAdministrator(
        user=TgUser(id=9, is_bot=False, first_name="Full"),
        can_be_edited=False,
        is_anonymous=False,
        can_manage_chat=True,
        can_delete_messages=True,
        can_manage_video_chats=True,
        can_restrict_members=True,
        can_promote_members=False,
        can_change_info=False,
        can_invite_users=True,
        can_post_stories=False,
        can_edit_stories=False,
        can_delete_stories=False,
        can_send_welcome_messages=False,
        can_pin_messages=True,
    )

    assert permissions.is_owner(owner, 7) is True
    assert permissions.is_owner(admin_limited, 8) is False

    assert permissions.can_restrict(owner, 7) is True
    assert permissions.can_restrict(admin_limited, 8) is True

    assert permissions.can_delete(admin_limited, 8) is False
    assert permissions.can_delete(admin_full, 9) is True

    assert permissions.can_pin(admin_limited, 8) is False
    assert permissions.can_pin(admin_full, 9) is True


def test_report_service_message_link_for_public_chat():
    assert ReportService.get_message_link(-1001234567890, "mygroup", 55) == "https://t.me/mygroup/55"


def test_report_service_message_link_for_private_supergroup():
    # Telegram private supergroup IDs are -100xxxxxxxxxx and use /c/<id_without_100>/
    assert (
        ReportService.get_message_link(-1009876543210, None, 77)
        == "https://t.me/c/9876543210/77"
    )
