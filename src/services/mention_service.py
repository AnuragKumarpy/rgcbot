import asyncio
import html
import random
from typing import Any, Dict, List, Optional, Set

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import UserActivity
from src.models.member import GroupMember
from src.models.user import User
from src.utils.emojis import E_CHECK, E_FIRE, E_ROCKET, E_SPARKLES, E_STAR, animate_text

# Cool random emojis for 100% zero-risk secret tagging
COOL_EMOJIS = [
    "⚡",
    "🔥",
    "💎",
    "👑",
    "🚀",
    "✨",
    "🌸",
    "❤️",
    "🌟",
    "💫",
    "🎯",
    "🏆",
    "🔮",
    "🦄",
    "🛡️",
    "🪐",
    "🍀",
    "☄️",
    "🪄",
    "🛸",
    "🦁",
    "🦅",
    "🐺",
    "🐅",
    "🌊",
    "🌙",
    "☀️",
    "🌪️",
    "💥",
    "🍾",
]

# Track active tagging tasks per chat: {chat_id: asyncio.Task}
ACTIVE_TAG_TASKS: Dict[int, asyncio.Task] = {}


class MentionService:
    @classmethod
    def is_tagging_active(cls, chat_id: int) -> bool:
        task = ACTIVE_TAG_TASKS.get(chat_id)
        return bool(task and not task.done() and not task.cancelled())

    @classmethod
    def stop_tagging(cls, chat_id: int) -> bool:
        task = ACTIVE_TAG_TASKS.pop(chat_id, None)
        if task and not task.done():
            task.cancel()
            return True
        return False

    @classmethod
    async def get_target_members(
        cls,
        bot: Bot,
        session: AsyncSession,
        chat_id: int,
        active_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Queries group members from PostgreSQL.
        - active_only=True (@allactive): Targets users who actively chat (message_count > 0) + Admins.
        - active_only=False (@all): Targets all registered group members in the roster.
        """
        seen_ids: Set[int] = set()
        members: List[Dict[str, Any]] = []

        if active_only:
            # 1. Active users from UserActivity table
            stmt_act = (
                select(
                    distinct(UserActivity.user_id),
                    User.first_name,
                    User.username,
                )
                .outerjoin(User, User.user_id == UserActivity.user_id)
                .where(
                    UserActivity.chat_id == chat_id,
                    UserActivity.messages_count > 0,
                )
            )
            res_act = await session.execute(stmt_act)
            for r in res_act.all():
                if r[0] not in seen_ids:
                    seen_ids.add(r[0])
                    members.append(
                        {
                            "user_id": r[0],
                            "first_name": r[1] or f"User {r[0]}",
                            "username": r[2],
                        }
                    )

            # 2. Active users from GroupMember table with message_count > 0
            stmt_gm = (
                select(
                    GroupMember.user_id,
                    User.first_name,
                    User.username,
                )
                .outerjoin(User, User.user_id == GroupMember.user_id)
                .where(
                    GroupMember.chat_id == chat_id,
                    GroupMember.is_banned == False,
                    GroupMember.message_count > 0,
                )
            )
            res_gm = await session.execute(stmt_gm)
            for r in res_gm.all():
                if r[0] not in seen_ids:
                    seen_ids.add(r[0])
                    members.append(
                        {
                            "user_id": r[0],
                            "first_name": r[1] or f"User {r[0]}",
                            "username": r[2],
                        }
                    )

            # 3. Always include chat administrators in active list
            try:
                admins = await bot.get_chat_administrators(chat_id)
                for adm in admins:
                    if adm.user.is_bot:
                        continue
                    if adm.user.id not in seen_ids:
                        seen_ids.add(adm.user.id)
                        members.append(
                            {
                                "user_id": adm.user.id,
                                "first_name": adm.user.first_name or f"User {adm.user.id}",
                                "username": adm.user.username,
                            }
                        )
            except Exception as e:
                logger.debug(f"Could not fetch chat administrators for mention list: {e}")

        else:
            # 1. Query GroupMember table (All members)
            gm_stmt = (
                select(
                    GroupMember.user_id,
                    User.first_name,
                    User.username,
                )
                .outerjoin(User, User.user_id == GroupMember.user_id)
                .where(GroupMember.chat_id == chat_id, GroupMember.is_banned == False)
            )
            gm_res = await session.execute(gm_stmt)
            for r in gm_res.all():
                if r[0] not in seen_ids:
                    seen_ids.add(r[0])
                    members.append(
                        {
                            "user_id": r[0],
                            "first_name": r[1] or f"User {r[0]}",
                            "username": r[2],
                        }
                    )

            # 2. Query UserActivity table
            act_stmt = (
                select(
                    distinct(UserActivity.user_id),
                    User.first_name,
                    User.username,
                )
                .outerjoin(User, User.user_id == UserActivity.user_id)
                .where(UserActivity.chat_id == chat_id)
            )
            act_res = await session.execute(act_stmt)
            for r in act_res.all():
                if r[0] not in seen_ids:
                    seen_ids.add(r[0])
                    members.append(
                        {
                            "user_id": r[0],
                            "first_name": r[1] or f"User {r[0]}",
                            "username": r[2],
                        }
                    )

            # 3. Query Chat Administrators
            try:
                admins = await bot.get_chat_administrators(chat_id)
                for adm in admins:
                    if adm.user.is_bot:
                        continue
                    if adm.user.id not in seen_ids:
                        seen_ids.add(adm.user.id)
                        members.append(
                            {
                                "user_id": adm.user.id,
                                "first_name": adm.user.first_name or f"User {adm.user.id}",
                                "username": adm.user.username,
                            }
                        )
            except Exception as e:
                logger.debug(f"Could not fetch chat administrators for mention list: {e}")

        return members

    @classmethod
    def create_tag_batch_text(
        cls,
        chunk: List[Dict[str, Any]],
        custom_text: str,
        mode: str = "secret",
    ) -> str:
        """
        Creates a 5-member mention message string.
        ALL tagging is 100% secret emoji tagging (zero-risk TOS safety).
        User names and usernames are never printed, only random cool emojis.
        """
        mentions = []
        for u in chunk:
            u_id = u["user_id"]
            emoji_icon = random.choice(COOL_EMOJIS)
            mentions.append(f'<a href="tg://user?id={u_id}">{emoji_icon}</a>')

        mention_str = " ".join(mentions)
        if custom_text:
            return f"{custom_text}\n\n{mention_str}"
        return mention_str

    @classmethod
    async def run_tagging_loop(
        cls,
        bot: Bot,
        chat_id: int,
        members: List[Dict[str, Any]],
        custom_text: str,
        mode: str = "secret",
        reply_to_message_id: Optional[int] = None,
    ):
        """
        Shows ETA / Auto-sync status card, then starts streaming mentions in 5-member chunks.
        NO TTL deletion is applied to tagging messages so mention notifications persist.
        """
        chunk_size = 5
        chunks = [members[i : i + chunk_size] for i in range(0, len(members), chunk_size)]
        total_chunks = len(chunks)
        delay_per_chunk = 1.5  # Optimized maximum safe speed (1.5s per chunk)
        eta_sec = total_chunks * delay_per_chunk
        eta_str = (
            f"{int(eta_sec)}s" if eta_sec < 60 else f"{int(eta_sec // 60)}m {int(eta_sec % 60)}s"
        )

        logger.info(
            f"Starting mention loop in chat {chat_id}: {len(members)} users in {total_chunks} batches (ETA: ~{eta_str})"
        )

        # 1. Dispatch ETA & Live Tagging Status Header
        stop_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⏹️ Stop Tagging", callback_data=f"tag_stop:{chat_id}")]
            ]
        )
        status_text = animate_text(
            f"{E_ROCKET} <b>Auto-Syncing & Preparing Mention Queue...</b>\n\n"
            f"• <b>Total Members:</b> <code>{len(members):,}</code>\n"
            f"• <b>Batches:</b> <code>{total_chunks:,}</code> (5 per chunk)\n"
            f"• <b>Estimated Duration:</b> <code>~{eta_str}</code>\n\n"
            "<i>Mentioning members in chunks below:</i>"
        )
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=status_text,
                reply_to_message_id=reply_to_message_id,
                reply_markup=stop_kb,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.debug(f"Status header send notice: {e}")

        # 2. Stream Mentions in Chunks
        try:
            for idx, chunk in enumerate(chunks, 1):
                if asyncio.current_task().cancelled():
                    break

                batch_text = cls.create_tag_batch_text(chunk, custom_text, mode="secret")

                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=batch_text,
                        reply_to_message_id=reply_to_message_id,
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                except Exception as e:
                    logger.debug(f"Tag chunk send note in {chat_id}: {e}")

                # 1.5s delay between chunks (maximum speed within Telegram limits)
                if idx < total_chunks:
                    await asyncio.sleep(delay_per_chunk)

        except asyncio.CancelledError:
            logger.info(f"Tagging loop cancelled for chat {chat_id}")
            raise
        finally:
            ACTIVE_TAG_TASKS.pop(chat_id, None)

    @classmethod
    def start_tagging_task(
        cls,
        bot: Bot,
        chat_id: int,
        members: List[Dict[str, Any]],
        custom_text: str,
        mode: str = "secret",
        reply_to_message_id: Optional[int] = None,
    ) -> bool:
        """Launches a zero-risk background tagging task."""
        if cls.is_tagging_active(chat_id):
            cls.stop_tagging(chat_id)

        task = asyncio.create_task(
            cls.run_tagging_loop(
                bot=bot,
                chat_id=chat_id,
                members=members,
                custom_text=custom_text,
                mode="secret",
                reply_to_message_id=reply_to_message_id,
            )
        )
        ACTIVE_TAG_TASKS[chat_id] = task
        return True
