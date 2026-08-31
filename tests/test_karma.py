import pytest
from datetime import datetime, timedelta
from src.models.user import User
from src.services.karma_service import KarmaService


def test_is_rep_trigger():
    assert KarmaService.is_rep_trigger("+rep") is True
    assert KarmaService.is_rep_trigger("+1") is True
    assert KarmaService.is_rep_trigger("thanks so much!") is True
    assert KarmaService.is_rep_trigger("thank you") is True
    assert KarmaService.is_rep_trigger("thx bro") is True
    assert KarmaService.is_rep_trigger("hello world") is False


@pytest.mark.asyncio
async def test_daily_streak_first_claim():
    user = User(user_id=1001, first_name="Bob", coins=100, daily_streak=0)
    success, msg, streak, coins = await KarmaService.claim_daily(user)
    assert success is True
    assert streak == 1
    assert coins == 125
    assert user.coins == 225


@pytest.mark.asyncio
async def test_daily_streak_cooldown():
    user = User(
        user_id=1002,
        first_name="Alice",
        coins=100,
        daily_streak=1,
        last_daily_at=datetime.utcnow() - timedelta(hours=5),
    )
    success, msg, streak, coins = await KarmaService.claim_daily(user)
    assert success is False
    assert "already claimed" in msg
    assert coins == 0
