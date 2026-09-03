from aiogram import Router
from src.handlers.fun.afk import router as afk_router
from src.handlers.fun.games import router as games_router
from src.handlers.fun.karma import router as karma_router
from src.handlers.fun.profile import router as profile_router
from src.handlers.fun.quote import router as quote_router
from src.handlers.fun.ship import router as ship_router
from src.handlers.fun.stats import router as stats_router


fun_router = Router(name="fun_master")
fun_router.include_router(karma_router)
fun_router.include_router(games_router)
fun_router.include_router(profile_router)
fun_router.include_router(afk_router)
fun_router.include_router(ship_router)
fun_router.include_router(quote_router)
fun_router.include_router(stats_router)

__all__ = ["fun_router"]
