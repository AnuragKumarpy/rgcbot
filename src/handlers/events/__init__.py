from aiogram import Router
from src.handlers.events.antispam import router as antispam_router
from src.handlers.events.chat_member import router as chat_member_router
from src.handlers.events.filters import router as filters_router
from src.handlers.events.join_request import router as join_request_router

events_router = Router(name="events_master")
events_router.include_router(chat_member_router)
events_router.include_router(antispam_router)
events_router.include_router(filters_router)
events_router.include_router(join_request_router)

__all__ = ["events_router"]
