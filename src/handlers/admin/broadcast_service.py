import asyncio
from typing import Optional, Tuple
from aiogram import Bot
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.broadcast import BroadcastRecord
from src.models.group import Group
from src.models.user import User


class BroadcastService:
    @classmethod
    async def execute_broadcast(
        cls,
        bot: Bot,
        session: AsyncSession,
        admin_id: int,
        target_type: str,  # "users", "groups", "all"
        text: str,
        media_type: Optional[str] = None,
        media_file_id: Optional[str] = None,
        pin: bool = False,
    ) -> Tuple[int, int]:
        """
        Executes a global broadcast to users, groups, or both.
        Returns: (success_count, failed_count)
        """
        target_chat_ids = []

        if target_type in ("users", "all"):
            res_u = await session.execute(select(User.user_id))
            target_chat_ids.extend(res_u.scalars().all())

        if target_type in ("groups", "all"):
            res_g = await session.execute(select(Group.chat_id).where(Group.is_active == True))
            target_chat_ids.extend(res_g.scalars().all())

        # Remove duplicates
        target_chat_ids = list(set(target_chat_ids))
        total_targets = len(target_chat_ids)
        success_count = 0
        failed_count = 0

        # Record entry in DB
        record = BroadcastRecord(
            admin_id=admin_id,
            target_type=target_type,
            content=text,
            media_type=media_type,
            media_file_id=media_file_id,
            total_targets=total_targets,
            is_pinned=pin,
            status="sending",
        )
        session.add(record)
        await session.commit()

        for chat_id in target_chat_ids:
            try:
                sent_msg = None
                if media_type == "photo" and media_file_id:
                    sent_msg = await bot.send_photo(
                        chat_id=chat_id,
                        photo=media_file_id,
                        caption=text,
                        parse_mode="HTML",
                    )
                elif media_type == "video" and media_file_id:
                    sent_msg = await bot.send_video(
                        chat_id=chat_id,
                        video=media_file_id,
                        caption=text,
                        parse_mode="HTML",
                    )
                elif media_type == "animation" and media_file_id:
                    sent_msg = await bot.send_animation(
                        chat_id=chat_id,
                        animation=media_file_id,
                        caption=text,
                        parse_mode="HTML",
                    )
                else:
                    sent_msg = await bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode="HTML",
                    )

                if pin and sent_msg:
                    try:
                        await bot.pin_chat_message(chat_id=chat_id, message_id=sent_msg.message_id)
                    except Exception:
                        pass

                success_count += 1
            except Exception as e:
                failed_count += 1
                logger.debug(f"Broadcast failed for chat {chat_id}: {e}")

            await asyncio.sleep(0.04)  # Safe ~25 msgs/sec to avoid Telegram flood limits

        record.success_count = success_count
        record.failed_count = failed_count
        record.status = "completed"
        await session.commit()

        return success_count, failed_count

    @classmethod
    async def execute_broadcast_copy(
        cls,
        bot: Bot,
        session: AsyncSession,
        admin_id: int,
        target_type: str,
        source_message,
        pin: bool = False,
    ) -> Tuple[int, int]:
        target_chat_ids = []

        if target_type in ("users", "all"):
            res_u = await session.execute(select(User.user_id))
            target_chat_ids.extend(res_u.scalars().all())

        if target_type in ("groups", "all"):
            res_g = await session.execute(select(Group.chat_id).where(Group.is_active == True))
            target_chat_ids.extend(res_g.scalars().all())

        target_chat_ids = list(set(target_chat_ids))
        total_targets = len(target_chat_ids)
        success_count = 0
        failed_count = 0

        record = BroadcastRecord(
            admin_id=admin_id,
            target_type=target_type,
            content=source_message.caption or source_message.text or "Media Broadcast",
            total_targets=total_targets,
            is_pinned=pin,
            status="sending",
        )
        session.add(record)
        await session.commit()

        for chat_id in target_chat_ids:
            try:
                sent_msg = await source_message.copy_to(chat_id=chat_id)
                if pin and sent_msg and hasattr(sent_msg, "message_id"):
                    try:
                        await bot.pin_chat_message(
                            chat_id=chat_id,
                            message_id=sent_msg.message_id,
                            disable_notification=True,
                        )
                    except Exception:
                        pass
                success_count += 1
            except Exception as e:
                failed_count += 1

            await asyncio.sleep(0.04)

        record.success_count = success_count
        record.failed_count = failed_count
        record.status = "completed"
        await session.commit()

        return success_count, failed_count
