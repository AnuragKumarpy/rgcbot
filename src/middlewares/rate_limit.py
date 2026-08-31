import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from loguru import logger
from src.config.settings import settings
from src.core.redis import redis_manager


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit_per_second: float = 1.0):
        self.limit_per_second = limit_per_second

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if not user_id or user_id in settings.bot_super_admins:
            return await handler(event, data)

        try:
            redis = await redis_manager.get_client()
            key = f"{settings.redis_rate_limit_prefix}{user_id}"
            current_time = time.time()

            # Set a simple sliding cooldown in Redis
            last_request_time = await redis.get(key)
            if last_request_time:
                elapsed = current_time - float(last_request_time)
                if elapsed < self.limit_per_second:
                    # User is sending commands too fast, drop or warn silently
                    logger.debug(f"User {user_id} throttled (elapsed: {elapsed:.2f}s)")
                    return None

            await redis.set(key, str(current_time), ex=3)
        except Exception as e:
            logger.warning(f"Rate limiting check failed: {e}")

        return await handler(event, data)
