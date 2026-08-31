from typing import Optional
from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.group import Group
from src.services.antispam_service import AntiSpamService
from src.services.blocklist_service import BlocklistService
from src.services.language_filter import LanguageFilterService

router = Router(name="events_antispam")


@router.message(F.text | F.caption, ~F.text.startswith("/"))
async def handle_antispam_checks(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
):
    # Admins bypass passive spam filters
    if is_admin or not db_group or not session:
        return

    # 1. Telegram Zero-Tolerance TOS Shield Check
    tos_violated = await BlocklistService.check_tos_shield(
        bot=message.bot,
        session=session,
        group=db_group,
        message=message,
    )
    if tos_violated:
        return

    # 2. Custom Group Blocklist Terms Check
    blocklist_matched = await BlocklistService.check_group_blocklist(
        bot=message.bot,
        session=session,
        group=db_group,
        message=message,
    )
    if blocklist_matched:
        return

    # 3. Language Filter Check (English Only)
    lang_violated = await LanguageFilterService.check_language(
        bot=message.bot,
        group=db_group,
        message=message,
    )
    if lang_violated:
        return

    # 4. Anti-Flood Check
    flood_triggered = await AntiSpamService.check_flood(
        bot=message.bot,
        group=db_group,
        message=message,
    )
    if flood_triggered:
        return

    # 5. Anti-Link and Forward Protection Check
    await AntiSpamService.check_links_and_forwards(
        bot=message.bot,
        group=db_group,
        message=message,
    )
