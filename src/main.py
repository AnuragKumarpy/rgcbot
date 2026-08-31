import asyncio
import signal
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from loguru import logger

from src.config.settings import settings
from src.core.bot import create_bot, create_dispatcher
from src.core.database import db
from src.core.logging import setup_logging
from src.core.redis import redis_manager
from src.handlers import admin_router, common_router, events_router, fun_router
from src.middlewares.auth import AuthMiddleware
from src.middlewares.command_logger import CommandLoggerMiddleware
from src.middlewares.database import DatabaseMiddleware
from src.middlewares.rate_limit import RateLimitMiddleware
from src.services.bot_metadata_service import setup_bot_metadata
from src.services.ttl_cleaner import TTLSweeperWorker


async def on_startup(bot: Bot, sweeper: TTLSweeperWorker):
    logger.info("Starting up RGCBot services...")
    # Initialize DB & Redis
    db.initialize()
    await db.create_tables()
    await redis_manager.initialize()

    # Start TTL Sweeper Worker
    await sweeper.start()

    # Register Bot commands, scopes, and descriptions with Telegram Bot API
    await setup_bot_metadata(bot)

    # Set webhook if in webhook mode
    if settings.bot_mode == "webhook":
        logger.info(f"Setting webhook to: {settings.webhook_url}")
        await bot.set_webhook(
            url=settings.webhook_url,
            secret_token=settings.webhook_secret,
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
    else:
        # Drop pending updates for polling
        await bot.delete_webhook(drop_pending_updates=True)

    bot_info = await bot.get_me()
    logger.info(f"RGCBot started as @{bot_info.username} (ID: {bot_info.id})")


async def on_shutdown(bot: Bot, sweeper: TTLSweeperWorker):
    logger.info("Shutting down RGCBot services...")
    await sweeper.stop()
    await redis_manager.close()
    await db.close()
    await bot.session.close()
    logger.info("All connections closed. Goodbye!")


def setup_dispatcher(dp: Dispatcher) -> Dispatcher:
    # 1. Register Outer Middlewares on update level
    dp.update.outer_middleware(DatabaseMiddleware())
    dp.update.outer_middleware(AuthMiddleware())

    # 2. Command Logger Middleware
    dp.message.outer_middleware(CommandLoggerMiddleware())

    # 3. Register Inner Middlewares on message / callback level
    dp.message.middleware(RateLimitMiddleware(limit_per_second=0.7))
    dp.callback_query.middleware(RateLimitMiddleware(limit_per_second=0.5))

    # 4. Register Routers (order matters)
    dp.include_router(common_router)
    dp.include_router(admin_router)
    dp.include_router(fun_router)
    dp.include_router(events_router)

    return dp


async def run_polling(bot: Bot, dp: Dispatcher, sweeper: TTLSweeperWorker):
    await on_startup(bot, sweeper)
    try:
        await dp.start_polling(
            bot,
            allowed_updates=[
                "message",
                "edited_message",
                "callback_query",
                "chat_member",
                "my_chat_member",
                "chat_join_request",
            ],
        )
    finally:
        await on_shutdown(bot, sweeper)


def run_webhook(bot: Bot, dp: Dispatcher, sweeper: TTLSweeperWorker):
    app = web.Application()

    # Health check endpoint for AWS ALB / Target Group
    async def health_check(request):
        return web.Response(text="OK", status=200)

    app.router.add_get("/health", health_check)
    app.router.add_get("/", health_check)

    # Webhook handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.webhook_secret,
    )
    webhook_requests_handler.register(app, path=settings.webhook_path)
    setup_application(app, dp, bot=bot)

    async def on_app_startup(app):
        await on_startup(bot, sweeper)

    async def on_app_cleanup(app):
        await on_shutdown(bot, sweeper)

    app.on_startup.append(on_app_startup)
    app.on_cleanup.append(on_app_cleanup)

    web.run_app(app, host=settings.server_host, port=settings.server_port)


def main():
    setup_logging()
    logger.info("Initializing RGCBot Application...")

    bot = create_bot()
    dp = create_dispatcher()
    setup_dispatcher(dp)

    sweeper = TTLSweeperWorker(bot=bot)

    if settings.bot_mode == "webhook":
        run_webhook(bot, dp, sweeper)
    else:
        asyncio.run(run_polling(bot, dp, sweeper))


if __name__ == "__main__":
    main()
