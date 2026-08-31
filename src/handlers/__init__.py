from src.handlers.admin import admin_router
from src.handlers.fun import fun_router
from src.handlers.events import events_router
from src.handlers.common import common_router

__all__ = [
    "admin_router",
    "fun_router",
    "events_router",
    "common_router",
]
