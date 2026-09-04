import asyncio
import time
from typing import Optional, Tuple
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.types import Message
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.broadcast import BroadcastRecord
from src.models.group import Group
from src.models.user import User

POWERED_BY_FOOTER = '⚡ <b>Powered by ELITE Bot</b> <a href="https://t.me/EliteBotsTelegram">@EliteBotsTelegram</a>'


def generate_progress_bar(current: int, total: int, length: int = 10) -> str:
    if total <= 0:
        return "[░░░░░░░░░░] 0%"
    pct = min(1.0, current / total)
    filled = int(round(length * pct))
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {pct * 100:.1f}%"


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
        status_msg: Optional[Message] = None,
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
            content=text,
            media_type=media_type,
            media_file_id=media_file_id,
            total_targets=total_targets,
            is_pinned=pin,
            status="sending",
        )
        session.add(record)
        await session.commit()

        start_time = time.time()
        last_edit_time = start_time

        for idx, chat_id in enumerate(target_chat_ids, start=1):
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
                        await bot.pin_chat_message(chat_id=chat_id, message_id=sent_msg.message_id, disable_notification=True)
                    except Exception:
                        pass

                success_count += 1
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                try:
                    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
                    success_count += 1
                except Exception:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                logger.debug(f"Broadcast failed for chat {chat_id}: {e}")

            # Update live stats card every 2.5s or on completion
            now = time.time()
            if status_msg and (now - last_edit_time >= 2.5 or idx == total_targets):
                last_edit_time = now
                elapsed = max(0.1, now - start_time)
                speed = idx / elapsed
                remaining = max(0, total_targets - idx)
                eta_sec = int(remaining / speed) if speed > 0 else 0
                eta_str = f"{eta_sec // 60}m {eta_sec % 60}s" if eta_sec >= 60 else f"{eta_sec}s"
                progress_bar = generate_progress_bar(idx, total_targets)

                live_text = (
                    f"📢 <b>LIVE BROADCAST DISPATCHER</b>\n\n"
                    f"• <b>Target Scope:</b> <code>{target_type.upper()}</code>\n"
                    f"• <b>Progress:</b> <code>{progress_bar}</code> ({idx:,}/{total_targets:,})\n"
                    f"• <b>Delivered:</b> <b>{success_count:,}</b> ✅\n"
                    f"• <b>Blocked/Failed:</b> <b>{failed_count:,}</b> ❌\n"
                    f"• <b>Throughput Speed:</b> <code>{speed:.1f} msg/s</code>\n"
                    f"• <b>Estimated ETA:</b> <code>{eta_str}</code>\n\n"
                    f"{POWERED_BY_FOOTER}"
                )
                try:
                    await status_msg.edit_text(live_text, parse_mode="HTML")
                except Exception:
                    pass

            await asyncio.sleep(0.04)

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
        status_msg: Optional[Message] = None,
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

        start_time = time.time()
        last_edit_time = start_time

        for idx, chat_id in enumerate(target_chat_ids, start=1):
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
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                try:
                    await source_message.copy_to(chat_id=chat_id)
                    success_count += 1
                except Exception:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                logger.debug(f"Broadcast copy failed for chat {chat_id}: {e}")

            now = time.time()
            if status_msg and (now - last_edit_time >= 2.5 or idx == total_targets):
                last_edit_time = now
                elapsed = max(0.1, now - start_time)
                speed = idx / elapsed
                remaining = max(0, total_targets - idx)
                eta_sec = int(remaining / speed) if speed > 0 else 0
                eta_str = f"{eta_sec // 60}m {eta_sec % 60}s" if eta_sec >= 60 else f"{eta_sec}s"
                progress_bar = generate_progress_bar(idx, total_targets)

                live_text = (
                    f"📢 <b>LIVE MEDIA BROADCAST DISPATCHER</b>\n\n"
                    f"• <b>Target Scope:</b> <code>{target_type.upper()}</code>\n"
                    f"• <b>Progress:</b> <code>{progress_bar}</code> ({idx:,}/{total_targets:,})\n"
                    f"• <b>Delivered:</b> <b>{success_count:,}</b> ✅\n"
                    f"• <b>Blocked/Failed:</b> <b>{failed_count:,}</b> ❌\n"
                    f"• <b>Throughput Speed:</b> <code>{speed:.1f} msg/s</code>\n"
                    f"• <b>Estimated ETA:</b> <code>{eta_str}</code>\n\n"
                    f"{POWERED_BY_FOOTER}"
                )
                try:
                    await status_msg.edit_text(live_text, parse_mode="HTML")
                except Exception:
                    pass

            await asyncio.sleep(0.04)

        record.success_count = success_count
        record.failed_count = failed_count
        record.status = "completed"
        await session.commit()

        return success_count, failed_count
