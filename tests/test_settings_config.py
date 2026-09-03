from src.config.settings import Settings


def test_settings_parse_super_admins_from_csv():
    cfg = Settings(_env_file=None, bot_super_admins="101, 202, invalid, 303")
    assert cfg.bot_super_admins == [101, 202, 303]


def test_settings_parse_super_admins_from_iterable():
    cfg = Settings(_env_file=None, bot_super_admins=[1, "2", "bad", 3])
    assert cfg.bot_super_admins == [1, 2, 3]


def test_settings_empty_super_admins_string_becomes_empty_list():
    cfg = Settings(_env_file=None, bot_super_admins="   ")
    assert cfg.bot_super_admins == []


def test_webhook_url_property_normalizes_host_trailing_slash():
    cfg = Settings(_env_file=None, webhook_host="https://example.com/", webhook_path="/hook")
    assert cfg.webhook_url == "https://example.com/hook"
