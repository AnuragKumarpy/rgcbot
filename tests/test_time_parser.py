import pytest
from src.utils.time_parser import format_duration, parse_time_string


def test_parse_time_string_seconds():
    assert parse_time_string("45s") == 45
    assert parse_time_string("30 sec") == 30
    assert parse_time_string("100") == 100


def test_parse_time_string_minutes():
    assert parse_time_string("5m") == 300
    assert parse_time_string("10 min") == 600


def test_parse_time_string_hours():
    assert parse_time_string("2h") == 7200
    assert parse_time_string("1 hour") == 3600


def test_parse_time_string_days_and_weeks():
    assert parse_time_string("1d") == 86400
    assert parse_time_string("1w") == 604800
    assert parse_time_string("1 week") == 604800


def test_parse_time_string_combined():
    assert parse_time_string("1d 2h 30m") == 86400 + 7200 + 1800


def test_parse_time_string_invalid():
    assert parse_time_string("") is None
    assert parse_time_string("invalid_time") is None


def test_format_duration():
    assert format_duration(45) == "45s"
    assert format_duration(3600) == "1h"
    assert format_duration(86400) == "1d"
    assert format_duration(90000) == "1d 1h"
