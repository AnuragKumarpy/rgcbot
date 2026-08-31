import asyncio
import time
from collections import defaultdict
from typing import List
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from loguru import logger
from src.config.settings import settings
from src.core.redis import redis_manager


class TTLSweeperWorker:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        self.is_running = True
        self._task = asyncio.create_task(self._sweep_loop())
        logger.info("TTL Sweeper Worker background loop started.")

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("TTL Sweeper Worker stopped.")

    async def _sweep_loop(self):
        while self.is_running:
            try:
                await self._process_expired_messages()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in TTL sweeper loop: {e}")

            await asyncio.sleep(settings.sweeper_interval_seconds)

    async def _process_expired_messages(self):
        redis = await redis_manager.get_client()
        current_time = time.time()

        # Fetch expired items with score <= current_time
        expired_entries: List[str] = await redis.zrangebyscore(
            settings.redis_ttl_queue_key,
            min=0,
            max=current_time,
            start=0,
            num=settings.sweeper_batch_size,
        )

        if not expired_entries:
            return

        logger.debug(f"TTL Sweeper found {len(expired_entries)} expired messages to delete.")

        # Group by chat_id: chat_id -> list of (message_id, raw_entry)
        chat_grouped = defaultdict(list)
        for entry in expired_entries:
            try:
                chat_id_str, msg_id_str = entry.split(":", 1)
                chat_id = int(chat_id_str)
                msg_id = int(msg_id_str)
                chat_grouped[chat_id].append((msg_id, entry))
            except Exception as e:
                logger.warning(f"Malformed entry in TTL queue '{entry}': {e}")
                # Remove malformed entry
                await redis.zrem(settings.redis_ttl_queue_key, entry)

        # Process deletions per chat
        for chat_id, msg_list in chat_grouped.items():
            msg_ids = [m[0] for m in msg_list]
            entries_to_remove = [m[1] for m in msg_list]

            # Try batch deletion first (supported in Bot API 7.0+)
            try:
                # Telegram delete_messages accepts up to 100 message IDs
                for i in range(0, len(msg_ids), 100):
                    chunk = msg_ids[i : i + 100]
                    try:
                        await self.bot.delete_messages(chat_id=chat_id, message_ids=chunk)
                    except (TelegramBadRequest, TelegramForbiddenError):
                        # Batch deletion may fail if some messages were already deleted or bot lacks permission
                        # Fallback to single message deletion
                        for msg_id in chunk:
                            try:
                                await self.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                            except (TelegramBadRequest, TelegramForbiddenError):
                                pass
                            except TelegramRetryAfter as e:
                                await asyncio.sleep(e.retry_after)
                    except TelegramRetryAfter as e:
                        logger.warning(f"Rate limited during batch delete: retry after {e.retry_after}s")
                        await asyncio.sleep(e.retry_after)

            except Exception as e:
                logger.debug(f"Error during TTL cleanup for chat {chat_id}: {e}")
            finally:
                # Always remove processed messages from Redis queue
                if entries_to_remove:
                    await redis.zrem(settings.redis_ttl_queue_key, *entries_to_remove)
