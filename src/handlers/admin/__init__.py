from aiogram import Router
from src.handlers.admin.ban_mute import router as ban_mute_router
from src.handlers.admin.blocklist import router as blocklist_router
from src.handlers.admin.federation import router as federation_router
from src.handlers.admin.locks import router as locks_router
from src.handlers.admin.notes import router as notes_router
from src.handlers.admin.purge import router as purge_router
from src.handlers.admin.settings import router as settings_router
from src.handlers.admin.settings_transfer import router as settings_transfer_router
from src.handlers.admin.superadmin import router as superadmin_router
from src.handlers.admin.tagging import router as tagging_router
from src.handlers.admin.warn import router as warn_router
from src.handlers.admin.zombies import router as zombies_router

admin_router = Router(name="admin_master")
admin_router.include_router(ban_mute_router)
admin_router.include_router(warn_router)
admin_router.include_router(purge_router)
admin_router.include_router(locks_router)
admin_router.include_router(settings_router)
admin_router.include_router(settings_transfer_router)
admin_router.include_router(tagging_router)
admin_router.include_router(federation_router)
admin_router.include_router(zombies_router)
admin_router.include_router(blocklist_router)
admin_router.include_router(notes_router)
admin_router.include_router(superadmin_router)




__all__ = ["admin_router"]
