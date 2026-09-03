import asyncio
from typing import List, Set, Tuple
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import ActionType
from src.models.group import Group
from src.models.member import GroupMember
from src.models.user import User
from src.services.audit_service import AuditService


class ZombieCleanerService:
    @classmethod
    async def scan_zombies(
        cls,
        bot: Bot,
        session: AsyncSession,
        chat_id: int,
    ) -> List[int]:
        """
        Scans group members and administrators to detect deleted Telegram accounts.
        Returns a deduplicated list of deleted user IDs.
        """
        candidate_ids: Set[int] = set()

        # 1. Scan administrators
        try:
            admins = await bot.get_chat_administrators(chat_id=chat_id)
            for adm in admins:
                if adm.user.first_name == "Deleted Account" or getattr(
                    adm.user, "is_deleted", False
                ):
                    candidate_ids.add(adm.user.id)
                elif not adm.user.is_bot:
                    # Check status
                    pass
        except Exception as e:
            logger.debug(f"Could not fetch admins for zombie scan in {chat_id}: {e}")

        # 2. Scan tracked group members
        try:
            stmt = select(GroupMember.user_id).where(GroupMember.chat_id == chat_id)
            res = await session.execute(stmt)
            for uid in res.scalars().all():
                candidate_ids.add(uid)
        except Exception as e:
            logger.debug(f"Could not fetch DB group members: {e}")

        # 3. Check each candidate
        zombie_ids: List[int] = []
        for uid in candidate_ids:
            try:
                cm = await bot.get_chat_member(chat_id=chat_id, user_id=uid)
                if cm.user.first_name == "Deleted Account" or getattr(cm.user, "is_deleted", False):
                    zombie_ids.append(uid)
                elif cm.status in ("left", "kicked"):
                    # Ghost member in DB, clean DB row
                    await session.execute(
                        delete(GroupMember).where(
                            GroupMember.chat_id == chat_id,
                            GroupMember.user_id == uid,
                        )
                    )
            except (TelegramBadRequest, TelegramForbiddenError) as e:
                err_msg = str(e).lower()
                if (
                    "user not found" in err_msg
                    or "deleted" in err_msg
                    or "participant_id_invalid" in err_msg
                ):
                    zombie_ids.append(uid)
            except Exception as e:
                logger.debug(f"Error checking member {uid}: {e}")

            await asyncio.sleep(0.04)

        await session.commit()
        return list(set(zombie_ids))

    @classmethod
    async def clean_zombies(
        cls,
        bot: Bot,
        session: AsyncSession,
        group: Group,
        admin_user_id: int,
        admin_user_name: str,
    ) -> Tuple[int, int]:
        """
        Scans and kicks all deleted accounts from the supergroup.
        Returns (cleaned_count, total_scanned).
        """
        zombie_ids = await cls.scan_zombies(bot, session, group.chat_id)
        cleaned_count = 0

        for uid in zombie_ids:
            try:
                # Ban and immediate unban to kick from group
                await bot.ban_chat_member(chat_id=group.chat_id, user_id=uid)
                await bot.unban_chat_member(chat_id=group.chat_id, user_id=uid)
                cleaned_count += 1
            except Exception as e:
                logger.debug(f"Could not kick zombie {uid} in {group.chat_id}: {e}")

            # Clean from database
            await session.execute(
                delete(GroupMember).where(
                    GroupMember.chat_id == group.chat_id,
                    GroupMember.user_id == uid,
                )
            )
            await asyncio.sleep(0.05)

        await session.commit()

        # Audit log
        if cleaned_count > 0:
            await AuditService.log_action(
                bot=bot,
                chat_id=group.chat_id,
                chat_title=group.title,
                target_user_id=0,
                target_user_name=f"{cleaned_count} Deleted Accounts",
                admin_user_id=admin_user_id,
                admin_user_name=admin_user_name,
                action=ActionType.ZOMBIE_PURGE,
                reason=f"Zombie Sweeper: successfully purged {cleaned_count} deleted accounts",
                channel_id=group.log_channel_id,
            )

        return cleaned_count, len(zombie_ids)
