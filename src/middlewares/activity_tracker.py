
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.stats_service import StatsService


class ActivityTrackerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        session: AsyncSession | None = data.get("session")
        if (
            session
            and event.chat.id < 0
            and event.from_user
            and not event.from_user.is_bot
        ):
            await StatsService.record_activity(session, event.chat.id, event.from_user.id, event)
        return await handler(event, data)
