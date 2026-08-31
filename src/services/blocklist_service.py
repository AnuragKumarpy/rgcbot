import re
from typing import Optional, Tuple
from aiogram import Bot
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import ActionType
from src.middlewares.ttl import schedule_auto_delete
from src.models.blocklist import BlocklistTerm
from src.models.group import Group
from src.models.user import User
from src.services.audit_service import AuditService
from src.services.moderation_service import ModerationService
from src.utils.text_formatter import format_card, mention_html

# Zero-tolerance Telegram TOS forbidden patterns
TOS_PROHIBITED_REGEX = re.compile(
    r"\b(child\s*porn|cp\s*links?|sell(ing)?\s*cp|selling\s*weapons?|sell(ing)?\s*meth|buy\s*meth|crystal\s*meth|selling\s*heroin|carding\s*dumps|cvv\s*leak|ssn\s*leak|selling\s*firearms?|buy\s*glock|buy\s*cocaine)\b",
    re.IGNORECASE,
)


class BlocklistService:
    @classmethod
    async def check_tos_shield(
        cls,
        bot: Bot,
        session: AsyncSession,
        group: Group,
        message: Message,
    ) -> bool:
        """
        Scans message for severe Telegram TOS violations.
        If found: instantly bans user, deletes message, and alerts audit channel.
        Returns True if a violation was found and handled.
        """
        if not group.tos_shield_enabled:
            return False

        text = message.text or message.caption or ""
        if not text:
            return False

        match = TOS_PROHIBITED_REGEX.search(text)
        if match:
            term = match.group(0)
            user_id = message.from_user.id if message.from_user else 0
            user_name = message.from_user.full_name if message.from_user else "User"

            # 1. Delete offending message immediately
            try:
                await message.delete()
            except Exception:
                pass

            # 2. Log to audit channel
            await AuditService.log_action(
                bot=bot,
                chat_id=group.chat_id,
                chat_title=group.title,
                target_user_id=user_id,
                target_user_name=user_name,
                action=ActionType.TOS_TRIGGER,
                reason=f"Telegram TOS Violation (Message Deleted): {term}",
                channel_id=group.log_channel_id,
            )

            # 3. Post temporary notification in chat
            notice = await message.answer(
                f"🚨 <b>Security Shield:</b> A message from {mention_html(user_id, user_name)} was <b>deleted</b> for containing prohibited content.",
                parse_mode="HTML",
            )
            await schedule_auto_delete(group.chat_id, notice.message_id, 20)
            return True

        return False

    @classmethod
    async def check_group_blocklist(
        cls,
        bot: Bot,
        session: AsyncSession,
        group: Group,
        message: Message,
    ) -> bool:
        """
        Scans message for custom group blocklist terms.
        Executes action: delete, warn, mute, or ban.
        Returns True if a term matched.
        """
        text = (message.text or message.caption or "").lower()
        if not text:
            return False

        stmt = select(BlocklistTerm).where(BlocklistTerm.chat_id == group.chat_id)
        res = await session.execute(stmt)
        terms = res.scalars().all()

        for bt in terms:
            if bt.term.lower() in text:
                user_id = message.from_user.id if message.from_user else 0
                user_name = message.from_user.full_name if message.from_user else "User"
                user_mention = mention_html(user_id, user_name)

                # Delete message
                try:
                    await message.delete()
                except Exception:
                    pass

                target_user = User(user_id=user_id, first_name=user_name)

                if bt.action == "ban":
                    await ModerationService.ban_user(
                        bot=bot,
                        session=session,
                        group=group,
                        target_user=target_user,
                        admin_user=None,
                        reason=f"Blocklist violation: '{bt.term}'",
                    )
                    notice = await message.answer(
                        f"🛡️ <b>Security Alert:</b> {user_mention} was <b>banned</b> for using prohibited terms.",
                        parse_mode="HTML",
                    )
                    await schedule_auto_delete(group.chat_id, notice.message_id, 20)

                elif bt.action == "mute":
                    await ModerationService.mute_user(
                        bot=bot,
                        session=session,
                        group=group,
                        target_user=target_user,
                        admin_user=None,
                        reason=f"Blocklist violation: '{bt.term}'",
                        duration_seconds=3600,
                    )
                    notice = await message.answer(
                        f"🔇 {user_mention} was <b>muted for 1h</b> for using prohibited terms.",
                        parse_mode="HTML",
                    )
                    await schedule_auto_delete(group.chat_id, notice.message_id, 20)

                elif bt.action == "warn":
                    curr, mx, escalated = await ModerationService.warn_user(
                        bot=bot,
                        session=session,
                        group=group,
                        target_user=target_user,
                        admin_user=None,
                        reason=f"Blocklist violation: '{bt.term}'",
                    )
                    if escalated:
                        text_msg = f"🚨 {user_mention} exceeded warning threshold and was <b>{escalated}</b>."
                    else:
                        text_msg = f"⚠️ {user_mention} received a warning ({curr}/{mx}) for using prohibited terms."
                    notice = await message.answer(text_msg, parse_mode="HTML")
                    await schedule_auto_delete(group.chat_id, notice.message_id, 20)

                else:  # "delete"
                    notice = await message.answer(
                        f"⚠️ {user_mention}, your message contained blocked words and was removed.",
                        parse_mode="HTML",
                    )
                    await schedule_auto_delete(group.chat_id, notice.message_id, 10)

                return True

        return False
