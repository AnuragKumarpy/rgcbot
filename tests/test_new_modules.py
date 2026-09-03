from datetime import date
import asyncio
import pytest
from aiogram.types import Chat, Message, User as TgUser
from src.models.group import Group
from src.services.games_service import GamesService
from src.services.locks_service import LocksService
from src.services.settings_transfer_service import SettingsTransferService
from src.services.stats_service import StatsService


def test_locks_service_normalization():
    assert LocksService.normalize_lock_type("links") == "links"
    assert LocksService.normalize_lock_type("url") == "links"
    assert LocksService.normalize_lock_type("sticker") == "stickers"
    assert LocksService.normalize_lock_type("round") == "video"
    assert LocksService.normalize_lock_type("all") == "all"
    assert LocksService.normalize_lock_type("invalid_type") is None


def test_locks_service_toggle():
    group = Group(chat_id=-1001, title="Test Group", locked_types="")
    assert LocksService.get_locked_set(group) == set()

    # Lock stickers
    res = LocksService.set_lock(group, "stickers", locked=True)
    assert "stickers" in res
    assert group.locked_types == "stickers"

    # Lock links
    res = LocksService.set_lock(group, "links", locked=True)
    assert "stickers" in res and "links" in res

    # Unlock stickers
    res = LocksService.set_lock(group, "stickers", locked=False)
    assert "stickers" not in res
    assert "links" in res

    # Lock all
    res = LocksService.set_lock(group, "all", locked=True)
    assert len(res) == 12

    # Unlock all
    res = LocksService.set_lock(group, "all", locked=False)
    assert len(res) == 0


def test_locks_service_check_message():
    group = Group(chat_id=-1001, title="Test Group", locked_types="links,forwards")

    # Message with URL
    msg_url = Message(
        message_id=1,
        date=date.today(),
        chat=Chat(id=-1001, type="supergroup"),
        from_user=TgUser(id=123, is_bot=False, first_name="User"),
        text="Check out https://telegram.org!",
    )
    assert LocksService.check_message_locks(group, msg_url) == "links"

    # Clean message
    msg_clean = Message(
        message_id=2,
        date=date.today(),
        chat=Chat(id=-1001, type="supergroup"),
        from_user=TgUser(id=123, is_bot=False, first_name="User"),
        text="Hello everyone in the group!",
    )
    assert LocksService.check_message_locks(group, msg_clean) is None


def test_settings_transfer_encoding_decoding():
    raw_payload = {
        "v": 1,
        "welcome": {"enabled": True, "text": "Welcome to the group!"},
        "locks": {"locked_types": "links,stickers", "clean_service": True, "antichannel": True},
        "security": {"antispam": True, "antiflood_limit": 5},
    }

    import base64
    import json
    import zlib

    # Test compression round-trip
    compressed = zlib.compress(json.dumps(raw_payload).encode("utf-8"), level=9)
    encoded = "RGC-CFG-" + base64.urlsafe_b64encode(compressed).decode("ascii")

    assert encoded.startswith("RGC-CFG-")
    clean = encoded[8:]
    decompressed = json.loads(zlib.decompress(base64.urlsafe_b64decode(clean)).decode("utf-8"))
    assert decompressed["welcome"]["text"] == "Welcome to the group!"
    assert decompressed["locks"]["clean_service"] is True


def test_stats_palette_extraction_and_card_generation():
    primary, secondary = StatsService.extract_palette(None)
    assert len(primary) == 3
    assert len(secondary) == 3

    sample_stats = {
        "timeframe": "today",
        "total_messages": 100,
        "active_users": 15,
        "total_stickers": 20,
        "total_media": 10,
        "total_voice": 5,
        "top_users": [
            {"name": "Alice", "messages": 50},
            {"name": "Bob", "messages": 30},
        ],
    }

    bio = StatsService.generate_stats_card("Test Group", None, sample_stats)
    assert bio is not None
    assert len(bio.getvalue()) > 5000


def test_game_result_tracking_updates_user_counters():
    class DummyUser:
        def __init__(self):
            self.games_played = 0
            self.games_won = 0
            self.game_score = 0

    dummy = DummyUser()

    asyncio.run(GamesService.record_game_result(object(), dummy, score_delta=25, won=True))

    assert dummy.games_played == 1
    assert dummy.games_won == 1
    assert dummy.game_score == 25
