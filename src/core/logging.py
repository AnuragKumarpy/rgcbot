import sys
from loguru import logger
from src.config.settings import settings


def setup_logging():
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level.upper(),
        colorize=True,
    )
    logger.info(f"Logging initialized with level {settings.log_level.upper()}")
    return logger
