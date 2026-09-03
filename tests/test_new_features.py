import pytest
from src.core.enums import ActionType
from src.models.note import AdminNote
from src.models.broadcast import BroadcastRecord
from src.services.blocklist_service import TOS_PROHIBITED_REGEX
from src.services.karma_service import KarmaService
from src.services.language_filter import NON_ENGLISH_SCRIPT_REGEX
from src.utils.text_formatter import format_card, get_karma_tier


def test_expanded_karma_triggers():
    assert KarmaService.is_rep_trigger("+rep")
    assert KarmaService.is_rep_trigger("++")
    assert KarmaService.is_rep_trigger("+1")
    assert KarmaService.is_rep_trigger("thanks so much!")
    assert KarmaService.is_rep_trigger("thank you for helping")
    assert KarmaService.is_rep_trigger("ty")
    assert KarmaService.is_rep_trigger("thx bro")
    assert KarmaService.is_rep_trigger("tysm")
    assert KarmaService.is_rep_trigger("respect")
    assert KarmaService.is_rep_trigger("helpful guide")

    assert not KarmaService.is_rep_trigger("hello how are you")
    assert not KarmaService.is_rep_trigger("random text")


def test_tos_prohibited_regex():
    assert TOS_PROHIBITED_REGEX.search("selling weapons here dm me")
    assert TOS_PROHIBITED_REGEX.search("buy meth online")
    assert TOS_PROHIBITED_REGEX.search("selling firearms cheap")
    assert TOS_PROHIBITED_REGEX.search("carding dumps leak")

    assert not TOS_PROHIBITED_REGEX.search("hello welcome to our coding group")
    assert not TOS_PROHIBITED_REGEX.search("let's play a game of roulette")


def test_language_filter_regex():
    # Foreign scripts
    assert NON_ENGLISH_SCRIPT_REGEX.search("Привет как дела")  # Cyrillic
    assert NON_ENGLISH_SCRIPT_REGEX.search("مرحبا كيف حالك")  # Arabic
    assert NON_ENGLISH_SCRIPT_REGEX.search("你好世界")  # Chinese
    assert NON_ENGLISH_SCRIPT_REGEX.search("नमस्ते")  # Devanagari

    # Latin English
    assert not NON_ENGLISH_SCRIPT_REGEX.search("Hello world, how are you doing?")
    assert not NON_ENGLISH_SCRIPT_REGEX.search(
        "This is a clean English message with numbers 12345!"
    )


def test_elite_rank_tiers():
    assert "Grandmaster" in get_karma_tier(6000)
    assert "Ascendant" in get_karma_tier(3000)
    assert "Vanguard" in get_karma_tier(1500)
    assert "Master" in get_karma_tier(600)
    assert "Specialist" in get_karma_tier(250)
    assert "Contributor" in get_karma_tier(80)
    assert "Active" in get_karma_tier(20)
    assert "Initiate" in get_karma_tier(5)


def test_format_card():
    card = format_card(
        title="TEST TITLE",
        fields=[("Field 1", "Value 1"), ("Field 2", "Value 2")],
        footer="Test Footer",
    )
    assert "<b>TEST TITLE</b>" in card
    assert "Field 1" in card
    assert "Value 1" in card
    assert "<i>Test Footer</i>" in card


def test_models_and_enums():
    assert ActionType.GAME_PLAY == "game_play"
    assert ActionType.COMMAND_USE == "command_use"
    assert ActionType.PANIC_MODE == "panic_mode"
    assert ActionType.ZOMBIE_PURGE == "zombie_purge"

    note = AdminNote(chat_id=123, user_id=456, admin_id=789, note_text="Test Note")
    assert note.chat_id == 123
    assert note.note_text == "Test Note"

    b_rec = BroadcastRecord(admin_id=789, target_type="all", content="Hello everyone")
    assert b_rec.target_type == "all"
