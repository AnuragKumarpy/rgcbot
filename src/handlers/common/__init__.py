from aiogram import Router
from src.handlers.common.errors import router as errors_router
from src.handlers.common.report import router as report_router
from src.handlers.common.start import router as start_router


common_router = Router(name="common_master")
common_router.include_router(start_router)
common_router.include_router(errors_router)
common_router.include_router(report_router)

__all__ = ["common_router"]

