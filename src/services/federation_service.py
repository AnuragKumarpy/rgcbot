from datetime import datetime
from typing import Any, Dict, List, Optional

from aiogram import Bot
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.federation import Federation, FederationAdmin, FederationBan, FederationGroup
from src.models.group import Group
from src.models.user import User


class FederationService:
    @classmethod
    async def create_federation(cls, session: AsyncSession, owner_id: int, name: str) -> Federation:
        fed = Federation(name=name, owner_id=owner_id)
        session.add(fed)
        await session.flush()
        # Add owner as admin too
        adm = FederationAdmin(fed_id=fed.fed_id, user_id=owner_id)
        session.add(adm)
        await session.commit()
        return fed

    @classmethod
    async def get_federation(cls, session: AsyncSession, fed_id: str) -> Optional[Federation]:
        res = await session.execute(select(Federation).where(Federation.fed_id == fed_id))
        return res.scalars().first()

    @classmethod
    async def get_group_federation(
        cls, session: AsyncSession, chat_id: int
    ) -> Optional[Federation]:
        stmt = (
            select(Federation)
            .join(FederationGroup, FederationGroup.fed_id == Federation.fed_id)
            .where(FederationGroup.chat_id == chat_id)
        )
        res = await session.execute(stmt)
        return res.scalars().first()

    @classmethod
    async def join_federation(cls, session: AsyncSession, fed_id: str, chat_id: int) -> bool:
        fed = await cls.get_federation(session, fed_id)
        if not fed:
            return False

        # Remove previous fed group link if exists
        res = await session.execute(
            select(FederationGroup).where(FederationGroup.chat_id == chat_id)
        )
        existing = res.scalars().first()
        if existing:
            await session.delete(existing)
            await session.flush()

        fg = FederationGroup(fed_id=fed_id, chat_id=chat_id)
        session.add(fg)
        await session.commit()
        return True

    @classmethod
    async def leave_federation(cls, session: AsyncSession, chat_id: int) -> bool:
        res = await session.execute(
            select(FederationGroup).where(FederationGroup.chat_id == chat_id)
        )
        existing = res.scalars().first()
        if existing:
            await session.delete(existing)
            await session.commit()
            return True
        return False

    @classmethod
    async def is_fed_admin(cls, session: AsyncSession, fed_id: str, user_id: int) -> bool:
        fed = await cls.get_federation(session, fed_id)
        if not fed:
            return False
        if fed.owner_id == user_id:
            return True
        res = await session.execute(
            select(FederationAdmin).where(
                FederationAdmin.fed_id == fed_id, FederationAdmin.user_id == user_id
            )
        )
        return bool(res.scalars().first())

    @classmethod
    async def promote_fed_admin(cls, session: AsyncSession, fed_id: str, user_id: int) -> bool:
        res = await session.execute(
            select(FederationAdmin).where(
                FederationAdmin.fed_id == fed_id, FederationAdmin.user_id == user_id
            )
        )
        if res.scalars().first():
            return True
        adm = FederationAdmin(fed_id=fed_id, user_id=user_id)
        session.add(adm)
        await session.commit()
        return True

    @classmethod
    async def demote_fed_admin(cls, session: AsyncSession, fed_id: str, user_id: int) -> bool:
        res = await session.execute(
            select(FederationAdmin).where(
                FederationAdmin.fed_id == fed_id, FederationAdmin.user_id == user_id
            )
        )
        existing = res.scalars().first()
        if existing:
            await session.delete(existing)
            await session.commit()
            return True
        return False

    @classmethod
    async def is_user_fed_banned(
        cls, session: AsyncSession, fed_id: str, user_id: int
    ) -> Optional[FederationBan]:
        res = await session.execute(
            select(FederationBan).where(
                FederationBan.fed_id == fed_id, FederationBan.user_id == user_id
            )
        )
        return res.scalars().first()

    @classmethod
    async def ban_user(
        cls,
        bot: Bot,
        session: AsyncSession,
        fed_id: str,
        user_id: int,
        reason: Optional[str],
        banned_by_id: int,
    ) -> int:
        """Bans user across all linked federation groups."""
        res = await session.execute(
            select(FederationBan).where(
                FederationBan.fed_id == fed_id, FederationBan.user_id == user_id
            )
        )
        f_ban = res.scalars().first()
        if not f_ban:
            f_ban = FederationBan(
                fed_id=fed_id,
                user_id=user_id,
                reason=reason or "Banned across Federation",
                banned_by_id=banned_by_id,
            )
            session.add(f_ban)
            await session.commit()

        # Ban across all linked group chats
        groups_res = await session.execute(
            select(FederationGroup.chat_id).where(FederationGroup.fed_id == fed_id)
        )
        chat_ids = groups_res.scalars().all()
        banned_chats = 0

        for cid in chat_ids:
            try:
                await bot.ban_chat_member(chat_id=cid, user_id=user_id)
                banned_chats += 1
            except Exception as e:
                logger.debug(f"Could not fed-ban user {user_id} in chat {cid}: {e}")

        return banned_chats

    @classmethod
    async def unban_user(
        cls,
        bot: Bot,
        session: AsyncSession,
        fed_id: str,
        user_id: int,
    ) -> int:
        """Unbans user across all linked federation groups."""
        res = await session.execute(
            select(FederationBan).where(
                FederationBan.fed_id == fed_id, FederationBan.user_id == user_id
            )
        )
        f_ban = res.scalars().first()
        if f_ban:
            await session.delete(f_ban)
            await session.commit()

        groups_res = await session.execute(
            select(FederationGroup.chat_id).where(FederationGroup.fed_id == fed_id)
        )
        chat_ids = groups_res.scalars().all()
        unbanned_chats = 0

        for cid in chat_ids:
            try:
                await bot.unban_chat_member(chat_id=cid, user_id=user_id, only_if_banned=True)
                unbanned_chats += 1
            except Exception as e:
                logger.debug(f"Could not fed-unban user {user_id} in chat {cid}: {e}")

        return unbanned_chats

    @classmethod
    async def get_fed_stats(cls, session: AsyncSession, fed_id: str) -> Dict[str, Any]:
        fed = await cls.get_federation(session, fed_id)
        if not fed:
            return {}

        res_g = await session.execute(
            select(func.count(FederationGroup.id)).where(FederationGroup.fed_id == fed_id)
        )
        group_count = res_g.scalar_one() or 0

        res_b = await session.execute(
            select(func.count(FederationBan.id)).where(FederationBan.fed_id == fed_id)
        )
        ban_count = res_b.scalar_one() or 0

        res_a = await session.execute(
            select(func.count(FederationAdmin.id)).where(FederationAdmin.fed_id == fed_id)
        )
        admin_count = res_a.scalar_one() or 0

        return {
            "fed_id": fed.fed_id,
            "name": fed.name,
            "owner_id": fed.owner_id,
            "groups_count": group_count,
            "bans_count": ban_count,
            "admins_count": admin_count,
            "created_at": fed.created_at,
        }
