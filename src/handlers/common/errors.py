from aiogram import Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ErrorEvent
from loguru import logger

router = Router(name="common_errors")


@router.error()
async def global_error_handler(event: ErrorEvent):
    exception = event.exception
    if isinstance(exception, TelegramBadRequest):
        logger.warning(f"TelegramBadRequest: {exception.message}")
    elif isinstance(exception, TelegramForbiddenError):
        logger.warning(f"TelegramForbiddenError: Bot was blocked or lacks admin rights.")
    elif isinstance(exception, TelegramAPIError):
        logger.error(f"TelegramAPIError: {exception}")
    else:
        logger.exception(f"Unhandled exception in update processing: {exception}")
