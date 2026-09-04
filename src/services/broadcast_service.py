import asyncio
import time
from typing import Optional, List
from aiogram import Bot
from aiogram.exceptions import (
    TelegramForbiddenError,
    TelegramBadRequest,
    TelegramRetryAfter,
    TelegramAPIError,
)
from aiogram.types import Message
from loguru import logger
from sqlalchemy import select
from src.core.database import db
from src.models.broadcast import BroadcastRecord
from src.models.group import Group
from src.models.user import User
from src.utils.text_formatter import format_card

POWERED_BY_FOOTER = '⚡ <b>Powered by ELITE Bot</b> <a href="https://t.me/EliteBotsTelegram">@EliteBotsTelegram</a>'


def generate_progress_bar(current: int, total: int, length: int = 10) -> str:
    if total <= 0:
        return "[░░░░░░░░░░] 0.0%"
    pct = min(1.0, max(0.0, current / total))
    filled = int(round(length * pct))
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {pct * 100:.1f}%"


class BroadcastService:
    @classmethod
    async def start_background_broadcast(
        cls,
        bot: Bot,
        admin_id: int,
        target_type: str,
        text: Optional[str] = None,
        source_message: Optional[Message] = None,
        pin: bool = False,
        status_msg: Optional[Message] = None,
    ):
        """
        Dispatches a high-speed parallel broadcast in a non-blocking background task.
        The bot remains 100% active and responsive for all other chats/commands.
        """
        asyncio.create_task(
            cls._broadcast_pipeline(
                bot=bot,
                admin_id=admin_id,
                target_type=target_type,
                text=text,
                source_message=source_message,
                pin=pin,
                status_msg=status_msg,
            )
        )

    @classmethod
    async def _broadcast_pipeline(
        cls,
        bot: Bot,
        admin_id: int,
        target_type: str,
        text: Optional[str] = None,
        source_message: Optional[Message] = None,
        pin: bool = False,
        status_msg: Optional[Message] = None,
    ):
        target_chat_ids: List[int] = []

        # 1. Fetch Target Chat IDs safely with dedicated DB session
        try:
            async for session in db.get_session():
                if target_type in ("users", "all"):
                    res_u = await session.execute(select(User.user_id))
                    target_chat_ids.extend(res_u.scalars().all())

                if target_type in ("groups", "all"):
                    res_g = await session.execute(select(Group.chat_id).where(Group.is_active == True))
                    target_chat_ids.extend(res_g.scalars().all())

                # Remove duplicates while preserving order
                target_chat_ids = list(dict.fromkeys(target_chat_ids))
                total_targets = len(target_chat_ids)

                record = BroadcastRecord(
                    admin_id=admin_id,
                    target_type=target_type,
                    content=(
                        source_message.caption
                        or source_message.text
                        or text
                        or "Media Broadcast"
                    )
                    if source_message
                    else (text or "Broadcast"),
                    total_targets=total_targets,
                    is_pinned=pin,
                    status="sending",
                )
                session.add(record)
                await session.commit()
                record_id = record.id
                break
        except Exception as e:
            logger.error(f"Failed to initialize broadcast record in DB: {e}")
            if status_msg:
                try:
                    await status_msg.edit_text(f"❌ <b>Database Error:</b> Failed to initialize broadcast: {e}", parse_mode="HTML")
                except Exception:
                    pass
            return

        if not target_chat_ids:
            if status_msg:
                try:
                    await status_msg.edit_text("⚠️ <b>No recipients found for this broadcast scope.</b>", parse_mode="HTML")
                except Exception:
                    pass
            return

        logger.info(f"Starting parallel broadcast to {total_targets} targets (scope: {target_type}) by admin {admin_id}")

        # 2. Concurrency & Queue Setup
        # Use a worker pool pattern with 20 parallel workers
        NUM_WORKERS = 20
        queue = asyncio.Queue()
        for cid in target_chat_ids:
            queue.put_nowait(cid)

        success_count = 0
        failed_count = 0
        processed_count = 0
        lock = asyncio.Lock()
        start_time = time.time()
        is_running = True

        # 3. Live UI Background Status Updater Loop
        async def ui_updater_task():
            while is_running:
                await asyncio.sleep(2.5)
                if not status_msg:
                    continue
                async with lock:
                    current_done = processed_count
                    cur_success = success_count
                    cur_failed = failed_count

                now = time.time()
                elapsed = max(0.1, now - start_time)
                speed = current_done / elapsed
                remaining = max(0, total_targets - current_done)
                eta_sec = int(remaining / speed) if speed > 0 else 0
                eta_str = f"{eta_sec // 60}m {eta_sec % 60:02d}s" if eta_sec >= 60 else f"{eta_sec}s"
                progress_bar = generate_progress_bar(current_done, total_targets)

                live_text = (
                    f"📢 <b>PARALLEL BROADCAST IN PROGRESS</b> 🚀\n\n"
                    f"• <b>Scope:</b> <code>{target_type.upper()}</code>\n"
                    f"• <b>Progress:</b> <code>{progress_bar}</code> ({current_done:,}/{total_targets:,})\n"
                    f"• <b>Delivered:</b> <b>{cur_success:,}</b> ✅\n"
                    f"• <b>Blocked / Failed:</b> <b>{cur_failed:,}</b> ❌\n"
                    f"• <b>Live Speed:</b> <code>{speed:.1f} msg/s</code>\n"
                    f"• <b>ETA:</b> <code>{eta_str}</code>\n\n"
                    f"<i>Bot remains 100% active and responsive during broadcast.</i>\n\n"
                    f"{POWERED_BY_FOOTER}"
                )
                try:
                    await status_msg.edit_text(live_text, parse_mode="HTML")
                except TelegramRetryAfter as e:
                    await asyncio.sleep(e.retry_after)
                except Exception:
                    pass

        ui_task = asyncio.create_task(ui_updater_task())

        # 4. Worker Routine
        async def worker():
            nonlocal success_count, failed_count, processed_count
            while is_running:
                try:
                    chat_id = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                delivered = False
                try:
                    sent_msg = None
                    if source_message:
                        sent_msg = await bot.copy_message(
                            chat_id=chat_id,
                            from_chat_id=source_message.chat.id,
                            message_id=source_message.message_id,
                            reply_markup=source_message.reply_markup,
                        )
                    else:
                        sent_msg = await bot.send_message(
                            chat_id=chat_id,
                            text=text,
                            parse_mode="HTML",
                            disable_web_page_preview=False,
                        )

                    if pin and sent_msg and hasattr(sent_msg, "message_id") and chat_id < 0:
                        try:
                            await bot.pin_chat_message(
                                chat_id=chat_id,
                                message_id=sent_msg.message_id,
                                disable_notification=True,
                            )
                        except Exception:
                            pass
                    delivered = True
                except TelegramRetryAfter as e:
                    await asyncio.sleep(e.retry_after + 0.5)
                    try:
                        if source_message:
                            await bot.copy_message(
                                chat_id=chat_id,
                                from_chat_id=source_message.chat.id,
                                message_id=source_message.message_id,
                                reply_markup=source_message.reply_markup,
                            )
                        else:
                            await bot.send_message(
                                chat_id=chat_id,
                                text=text,
                                parse_mode="HTML",
                            )
                        delivered = True
                    except Exception:
                        delivered = False
                except (TelegramForbiddenError, TelegramBadRequest) as e:
                    delivered = False
                    logger.debug(f"Target {chat_id} inaccessible: {e}")
                except TelegramAPIError as e:
                    delivered = False
                    logger.debug(f"Telegram API Notice for {chat_id}: {e}")
                except Exception as e:
                    delivered = False
                    logger.debug(f"Broadcast generic failure for {chat_id}: {e}")
                finally:
                    queue.task_done()

                async with lock:
                    if delivered:
                        success_count += 1
                    else:
                        failed_count += 1
                    processed_count += 1

                # Micro-sleep to keep aggregate rate steady (~20-25 msg/s across 20 workers)
                await asyncio.sleep(0.04)

        # 5. Run Worker Pool
        workers = [asyncio.create_task(worker()) for _ in range(NUM_WORKERS)]
        await asyncio.gather(*workers, return_exceptions=True)

        is_running = False
        ui_task.cancel()

        # 6. Update Database Record
        total_time = max(0.1, time.time() - start_time)
        avg_speed = total_targets / total_time
        try:
            async for session in db.get_session():
                res_r = await session.execute(select(BroadcastRecord).where(BroadcastRecord.id == record_id))
                rec = res_r.scalars().first()
                if rec:
                    rec.success_count = success_count
                    rec.failed_count = failed_count
                    rec.status = "completed"
                    await session.commit()
                break
        except Exception as e:
            logger.error(f"Failed to update broadcast record completion: {e}")

        # 7. Final Comprehensive Dispatch Card
        success_pct = (success_count / max(1, total_targets)) * 100
        mins = int(total_time // 60)
        secs = int(total_time % 60)
        duration_str = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"

        final_card = format_card(
            title="📢 BROADCAST DISPATCH COMPLETED",
            fields=[
                ("Target Scope", f"<code>{target_type.upper()}</code>"),
                ("Total Targets", f"<b>{total_targets:,}</b>"),
                ("Successfully Delivered", f"<b>{success_count:,}</b> ✅"),
                ("Failed / Blocked", f"<b>{failed_count:,}</b> ❌"),
                ("Delivery Success Rate", f"<b>{success_pct:.1f}%</b>"),
                ("Total Time Taken", f"<code>{duration_str}</code> (<code>{avg_speed:.1f} msg/s</code>)"),
                ("Pinned in Groups", "YES 📌" if pin else "NO"),
            ],
            footer=POWERED_BY_FOOTER,
        )

        if status_msg:
            try:
                await status_msg.edit_text(final_card, parse_mode="HTML")
            except Exception:
                try:
                    await bot.send_message(chat_id=admin_id, text=final_card, parse_mode="HTML")
                except Exception:
                    pass
        else:
            try:
                await bot.send_message(chat_id=admin_id, text=final_card, parse_mode="HTML")
            except Exception:
                pass
