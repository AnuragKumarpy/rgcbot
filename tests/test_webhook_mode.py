import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from src import main as app_main


class DummySweeper:
    def __init__(self):
        self.start = AsyncMock()
        self.stop = AsyncMock()


def _patch_common_startup_dependencies(monkeypatch):
    monkeypatch.setattr(app_main.db, "initialize", MagicMock())
    monkeypatch.setattr(app_main.db, "create_tables", AsyncMock())
    monkeypatch.setattr(app_main.redis_manager, "initialize", AsyncMock())
    monkeypatch.setattr(app_main, "setup_bot_metadata", AsyncMock())


def test_on_startup_sets_webhook_when_in_webhook_mode(monkeypatch):
    _patch_common_startup_dependencies(monkeypatch)

    monkeypatch.setattr(app_main.settings, "bot_mode", "webhook")
    monkeypatch.setattr(app_main.settings, "webhook_secret", "secret-123")
    monkeypatch.setattr(app_main.settings, "webhook_host", "https://example.com")
    monkeypatch.setattr(app_main.settings, "webhook_path", "/webhook")

    bot = SimpleNamespace(
        set_webhook=AsyncMock(),
        delete_webhook=AsyncMock(),
        get_me=AsyncMock(return_value=SimpleNamespace(username="rgcbot", id=1)),
    )
    sweeper = DummySweeper()

    asyncio.run(app_main.on_startup(bot, sweeper))

    bot.set_webhook.assert_awaited_once_with(
        url="https://example.com/webhook",
        secret_token="secret-123",
        drop_pending_updates=True,
        allowed_updates=[
            "message",
            "edited_message",
            "callback_query",
            "chat_member",
            "my_chat_member",
            "chat_join_request",
        ],
    )
    bot.delete_webhook.assert_not_awaited()


def test_on_startup_deletes_webhook_when_in_polling_mode(monkeypatch):
    _patch_common_startup_dependencies(monkeypatch)

    monkeypatch.setattr(app_main.settings, "bot_mode", "polling")

    bot = SimpleNamespace(
        set_webhook=AsyncMock(),
        delete_webhook=AsyncMock(),
        get_me=AsyncMock(return_value=SimpleNamespace(username="rgcbot", id=1)),
    )
    sweeper = DummySweeper()

    asyncio.run(app_main.on_startup(bot, sweeper))

    bot.set_webhook.assert_not_awaited()
    bot.delete_webhook.assert_awaited_once_with(drop_pending_updates=True)


def test_main_routes_to_webhook_runner(monkeypatch):
    fake_bot = object()
    fake_dp = object()
    fake_sweeper = object()

    monkeypatch.setattr(app_main, "setup_logging", MagicMock())
    monkeypatch.setattr(app_main, "create_bot", MagicMock(return_value=fake_bot))
    monkeypatch.setattr(app_main, "create_dispatcher", MagicMock(return_value=fake_dp))
    monkeypatch.setattr(app_main, "setup_dispatcher", MagicMock(return_value=fake_dp))
    monkeypatch.setattr(app_main, "TTLSweeperWorker", MagicMock(return_value=fake_sweeper))

    run_webhook_mock = MagicMock()
    monkeypatch.setattr(app_main, "run_webhook", run_webhook_mock)
    monkeypatch.setattr(app_main, "run_polling", AsyncMock())
    monkeypatch.setattr(app_main.asyncio, "run", MagicMock())

    monkeypatch.setattr(app_main.settings, "bot_mode", "webhook")

    app_main.main()

    run_webhook_mock.assert_called_once_with(fake_bot, fake_dp, fake_sweeper)
    app_main.asyncio.run.assert_not_called()


def test_main_routes_to_polling_runner(monkeypatch):
    fake_bot = object()
    fake_dp = object()
    fake_sweeper = object()

    monkeypatch.setattr(app_main, "setup_logging", MagicMock())
    monkeypatch.setattr(app_main, "create_bot", MagicMock(return_value=fake_bot))
    monkeypatch.setattr(app_main, "create_dispatcher", MagicMock(return_value=fake_dp))
    monkeypatch.setattr(app_main, "setup_dispatcher", MagicMock(return_value=fake_dp))
    monkeypatch.setattr(app_main, "TTLSweeperWorker", MagicMock(return_value=fake_sweeper))

    monkeypatch.setattr(app_main, "run_webhook", MagicMock())
    polling_coro = AsyncMock()
    monkeypatch.setattr(app_main, "run_polling", polling_coro)
    asyncio_run_mock = MagicMock()
    monkeypatch.setattr(app_main.asyncio, "run", asyncio_run_mock)

    monkeypatch.setattr(app_main.settings, "bot_mode", "polling")

    app_main.main()

    app_main.run_webhook.assert_not_called()
    asyncio_run_mock.assert_called_once()
    polling_coro.assert_called_once_with(fake_bot, fake_dp, fake_sweeper)
    called_coro = asyncio_run_mock.call_args.args[0]
    assert asyncio.iscoroutine(called_coro)
    called_coro.close()
