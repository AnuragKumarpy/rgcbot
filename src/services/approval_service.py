from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.approved_user import ApprovedUser


class ApprovalService:
    @staticmethod
    async def is_approved(session: AsyncSession, chat_id: int, user_id: int) -> bool:
        res = await session.execute(
            select(ApprovedUser).where(
                ApprovedUser.chat_id == chat_id, ApprovedUser.user_id == user_id
            )
        )
        return res.scalar_one_or_none() is not None

    @staticmethod
    async def approve(
        session: AsyncSession, chat_id: int, user_id: int, approved_by: int, reason: str | None = None
    ) -> bool:
        if await ApprovalService.is_approved(session, chat_id, user_id):
            return False
        session.add(ApprovedUser(chat_id=chat_id, user_id=user_id, approved_by=approved_by, reason=reason))
        await session.commit()
        return True

    @staticmethod
    async def unapprove(session: AsyncSession, chat_id: int, user_id: int) -> bool:
        res = await session.execute(
            delete(ApprovedUser).where(
                ApprovedUser.chat_id == chat_id, ApprovedUser.user_id == user_id
            )
        )
        await session.commit()
        return res.rowcount > 0

    @staticmethod
    async def list_approved(session: AsyncSession, chat_id: int) -> list[ApprovedUser]:
        res = await session.execute(select(ApprovedUser).where(ApprovedUser.chat_id == chat_id))
        return list(res.scalars().all())
