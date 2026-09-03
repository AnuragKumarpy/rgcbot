from src.models.group import Group
from src.models.user import User
from src.models.ttl import TTLSettings
from src.models.member import GroupMember


def test_model_instantiation():
    group = Group(
        chat_id=-100123456789,
        title="Test Group",
        is_active=True,
        welcome_enabled=True,
        captcha_mode="button",
    )
    assert group.chat_id == -100123456789
    assert group.welcome_enabled is True
    assert group.captcha_mode == "button"

    ttl = TTLSettings(chat_id=-100123456789, mod_ttl=15, fun_ttl=30, delete_command_trigger=True)
    assert ttl.mod_ttl == 15
    assert ttl.delete_command_trigger is True

    user = User(user_id=98765, first_name="Charlie", karma=10, coins=200)
    assert user.user_id == 98765
    assert user.coins == 200

    member = GroupMember(chat_id=group.chat_id, user_id=user.user_id, warnings_count=2)
    assert member.warnings_count == 2
