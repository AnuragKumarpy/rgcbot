from typing import Optional
import redis.asyncio as aioredis
from loguru import logger
from src.config.settings import settings


class RedisManager:
    def __init__(self):
        self.client: Optional[aioredis.Redis] = None

    async def initialize(self):
        logger.info(f"Connecting to Redis at: {settings.redis_url}")
        self.client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        try:
            await self.client.ping()
            logger.info("Successfully connected to Redis.")
        except Exception as e:
            logger.warning(f"Redis ping failed: {e}. Bot will attempt reconnection on requests.")

    async def get_client(self) -> aioredis.Redis:
        if self.client is None:
            await self.initialize()
        assert self.client is not None
        return self.client

    async def close(self):
        if self.client:
            await self.client.aclose()
            logger.info("Redis connection pool closed.")


redis_manager = RedisManager()
