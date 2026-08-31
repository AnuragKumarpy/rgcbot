import asyncio
from typing import Any, Awaitable, Callable, Dict, Optional
from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, TelegramObject
from loguru import logger
from src.config.settings import settings
from src.core.enums import ActionType
from src.models.group import Group
from src.services.audit_service import AuditService
from src.utils.text_formatter import escape_html, mention_html


class CommandLoggerMiddleware(BaseMiddleware):
    """
    Automatically captures and logs every command invocation to the default audit channel.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text and event.text.startswith("/"):
            bot: Optional[Bot] = data.get("bot") or event.bot
            db_group: Optional[Group] = data.get("db_group")
            user = event.from_user

            if bot and user:
                chat_title = event.chat.title or "Private Chat"
                chat_id = event.chat.id
                command_text = event.text

                # Asynchronously forward command log to audit channel without blocking message execution
                asyncio.create_task(
                    self._log_command(
                        bot=bot,
                        chat_id=chat_id,
                        chat_title=chat_title,
                        user_id=user.id,
                        user_name=user.full_name or user.first_name,
                        username=user.username,
                        command_text=command_text,
                        log_channel_id=db_group.log_channel_id if db_group else None,
                    )
                )

        return await handler(event, data)

    async def _log_command(
        self,
        bot: Bot,
        chat_id: int,
        chat_title: str,
        user_id: int,
        user_name: str,
        username: Optional[str],
        command_text: str,
        log_channel_id: Optional[int],
    ):
        try:
            target_channel = log_channel_id or settings.default_log_channel_id
            if not target_channel:
                return

            u_mention = mention_html(user_id, user_name)
            handle = f" (@{username})" if username else ""

            text = (
                f"⚡ <b>COMMAND EXECUTED</b>\n"
                f"<b>Chat:</b> {escape_html(chat_title)} [<code>{chat_id}</code>]\n"
                f"<b>User:</b> {u_mention}{handle} [<code>{user_id}</code>]\n"
                f"<b>Command:</b> <code>{escape_html(command_text)}</code>"
            )
            await bot.send_message(chat_id=target_channel, text=text, parse_mode="HTML")
        except Exception as e:
            logger.debug(f"Command logger could not send log: {e}")
