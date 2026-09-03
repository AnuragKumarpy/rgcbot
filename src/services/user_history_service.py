from typing import Any, Dict, Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.group import Group
from src.models.log import ModerationLog
from src.models.profile_change import UserProfileChange
from src.models.user import User


class UserHistoryService:
    @classmethod
    async def record_profile_change(
        cls,
        session: AsyncSession,
        user_id: int,
        *,
        chat_id: Optional[int] = None,
        old_username: Optional[str] = None,
        new_username: Optional[str] = None,
        old_first_name: Optional[str] = None,
        new_first_name: Optional[str] = None,
        note: Optional[str] = None,
    ) -> None:
        if (
            old_username == new_username
            and old_first_name == new_first_name
            and not note
        ):
            return

        try:
            session.add(
                UserProfileChange(
                    user_id=user_id,
                    chat_id=chat_id,
                    old_username=old_username,
                    new_username=new_username,
                    old_first_name=old_first_name,
                    new_first_name=new_first_name,
                    note=note,
                )
            )
            await session.flush()
        except Exception as e:
            logger.debug(f"Failed to record profile change for {user_id}: {e}")

    @classmethod
    async def get_group_user_history(
        cls,
        session: AsyncSession,
        chat_id: int,
        user_id: int,
        limit: int = 12,
    ) -> Dict[str, Any]:
        user_res = await session.execute(select(User).where(User.user_id == user_id))
        user = user_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).where(Group.chat_id == chat_id))
        group = group_res.scalar_one_or_none()

        mod_res = await session.execute(
            select(ModerationLog)
            .where(ModerationLog.chat_id == chat_id, ModerationLog.target_user_id == user_id)
            .order_by(ModerationLog.created_at.desc())
            .limit(limit)
        )
        moderation_logs = list(mod_res.scalars().all())

        profile_res = await session.execute(
            select(UserProfileChange)
            .where(
                UserProfileChange.user_id == user_id,
                (UserProfileChange.chat_id == chat_id) | (UserProfileChange.chat_id.is_(None)),
            )
            .order_by(UserProfileChange.changed_at.desc())
            .limit(limit)
        )
        profile_changes = list(profile_res.scalars().all())

        return {
            "user": user,
            "group": group,
            "moderation_logs": moderation_logs,
            "profile_changes": profile_changes,
        }