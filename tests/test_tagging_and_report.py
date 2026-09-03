import pytest
from src.services.mention_service import MentionService, COOL_EMOJIS
from src.services.report_service import ReportService


def test_mention_service_zero_risk_secret_tagging():
    chunk = [
        {"user_id": 101, "first_name": "Alice"},
        {"user_id": 102, "first_name": "Bob"},
        {"user_id": 103, "first_name": "Charlie"},
        {"user_id": 104, "first_name": "David"},
        {"user_id": 105, "first_name": "Eve"},
    ]

    # All modes must enforce 100% secret emoji masking to prevent TOS breaches
    text_all = MentionService.create_tag_batch_text(
        chunk, custom_text="Important announcement!", mode="all"
    )
    assert "Important announcement!" in text_all
    assert '<a href="tg://user?id=101">' in text_all
    assert "Alice" not in text_all  # Names must never be exposed

    text_secret = MentionService.create_tag_batch_text(
        chunk, custom_text="Secret Tag!", mode="secret"
    )
    assert "Secret Tag!" in text_secret
    assert '<a href="tg://user?id=101">' in text_secret
    assert "Alice" not in text_secret
    assert "Eve" not in text_secret


def test_report_service_message_link():
    # Supergroup with username
    link1 = ReportService.get_message_link(
        chat_id=-1001234567890, chat_username="testgroup", message_id=42
    )
    assert link1 == "https://t.me/testgroup/42"

    # Private supergroup without username
    link2 = ReportService.get_message_link(
        chat_id=-1001234567890, chat_username=None, message_id=42
    )
    assert "https://t.me/c/" in link2
    assert link2.endswith("/42")
