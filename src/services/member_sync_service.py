import os
from datetime import datetime
from typing import Optional

from aiogram import Bot
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.member import GroupMember
from src.models.user import User

API_ID = 28102220
API_HASH = "c9ff5d60c4b80bf5f7de1092082207a5"
SESSION_PATH = "scripts/user_session"


class MemberSyncService:
    @classmethod
    async def sync_group_members_mtproto(cls, session: AsyncSession, chat_id: int) -> int:
        """
        Connects via MTProto client session to fetch all participants of the target group
        and upserts them into PostgreSQL. Returns the count of synced members.
        """
        try:
            from telethon import TelegramClient
        except ImportError:
            logger.warning("Telethon not installed, skipping MTProto member sync.")
            return 0

        session_file = f"{SESSION_PATH}.session"
        if not os.path.exists(session_file):
            logger.warning(f"MTProto session file not found at {session_file}")
            return 0

        client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                logger.warning("MTProto client is not authorized.")
                await client.disconnect()
                return 0

            group = await client.get_entity(chat_id)
            participants = await client.get_participants(group, limit=5000)

            synced_count = 0
            for p in participants:
                if p.bot:
                    continue

                # 1. Upsert User
                u_res = await session.execute(select(User).where(User.user_id == p.id))
                db_u = u_res.scalars().first()
                if not db_u:
                    db_u = User(
                        user_id=p.id,
                        username=p.username,
                        first_name=p.first_name or "",
                        last_name=p.last_name,
                        karma=0,
                        coins=0,
                        daily_streak=0,
                        badges="[]",
                        is_afk=False,
                    )
                    session.add(db_u)
                else:
                    db_u.username = p.username
                    db_u.first_name = p.first_name or ""
                    db_u.last_name = p.last_name

                # 2. Upsert GroupMember
                gm_res = await session.execute(
                    select(GroupMember).where(
                        GroupMember.chat_id == chat_id, GroupMember.user_id == p.id
                    )
                )
                db_gm = gm_res.scalars().first()
                if not db_gm:
                    db_gm = GroupMember(
                        chat_id=chat_id,
                        user_id=p.id,
                        warnings_count=0,
                        is_muted=False,
                        is_banned=False,
                        message_count=0,
                        joined_at=datetime.utcnow(),
                        last_active_at=datetime.utcnow(),
                    )
                    session.add(db_gm)

                synced_count += 1

            await session.commit()
            await client.disconnect()
            return synced_count
        except Exception as e:
            logger.error(f"Failed to sync members via MTProto for chat {chat_id}: {e}")
            try:
                await client.disconnect()
            except Exception:
                pass
            return 0

    @classmethod
    async def sync_admins_fallback(cls, bot: Bot, session: AsyncSession, chat_id: int) -> int:
        """Fallback to sync all chat administrators via Bot API."""
        try:
            admins = await bot.get_chat_administrators(chat_id)
            count = 0
            for adm in admins:
                if adm.user.is_bot:
                    continue
                u = adm.user
                u_res = await session.execute(select(User).where(User.user_id == u.id))
                db_u = u_res.scalars().first()
                if not db_u:
                    db_u = User(
                        user_id=u.id,
                        username=u.username,
                        first_name=u.first_name or "",
                        last_name=u.last_name,
                    )
                    session.add(db_u)

                gm_res = await session.execute(
                    select(GroupMember).where(
                        GroupMember.chat_id == chat_id, GroupMember.user_id == u.id
                    )
                )
                if not gm_res.scalars().first():
                    session.add(
                        GroupMember(
                            chat_id=chat_id,
                            user_id=u.id,
                            warnings_count=0,
                            is_muted=False,
                            is_banned=False,
                            message_count=0,
                            joined_at=datetime.utcnow(),
                            last_active_at=datetime.utcnow(),
                        )
                    )
                count += 1
            await session.commit()
            return count
        except Exception as e:
            logger.error(f"Failed to sync admins for chat {chat_id}: {e}")
            return 0
