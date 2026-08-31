from typing import Any, Awaitable, Callable, Dict, Optional
from aiogram import BaseMiddleware, Bot
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery, ChatJoinRequest, ChatMemberUpdated, Message, TelegramObject, Update
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.settings import settings
from src.models.group import Group
from src.models.member import GroupMember
from src.models.ttl import TTLSettings
from src.models.user import User
from src.utils.permissions import (
    can_delete,
    can_pin,
    can_restrict,
    get_chat_member_safe,
    is_admin,
    is_owner,
    is_super_admin,
)


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Default fallback values for every update
        data.setdefault("db_user", None)
        data.setdefault("db_group", None)
        data.setdefault("is_admin", False)
        data.setdefault("is_owner", False)
        data.setdefault("can_restrict", False)
        data.setdefault("can_delete", False)
        data.setdefault("can_pin", False)

        session: Optional[AsyncSession] = data.get("session")
        bot: Optional[Bot] = data.get("bot")

        user_obj = None
        chat_obj = None

        # Extract user and chat from various TelegramObject types
        if isinstance(event, Message):
            user_obj = event.from_user
            chat_obj = event.chat
        elif isinstance(event, CallbackQuery):
            user_obj = event.from_user
            chat_obj = event.message.chat if event.message else None
        elif isinstance(event, ChatMemberUpdated):
            user_obj = event.from_user
            chat_obj = event.chat
        elif isinstance(event, ChatJoinRequest):
            user_obj = event.from_user
            chat_obj = event.chat
        elif isinstance(event, Update):
            if event.message:
                user_obj = event.message.from_user
                chat_obj = event.message.chat
            elif event.callback_query:
                user_obj = event.callback_query.from_user
                chat_obj = event.callback_query.message.chat if event.callback_query.message else None
            elif event.chat_member:
                user_obj = event.chat_member.from_user
                chat_obj = event.chat_member.chat
            elif event.my_chat_member:
                user_obj = event.my_chat_member.from_user
                chat_obj = event.my_chat_member.chat
            elif event.chat_join_request:
                user_obj = event.chat_join_request.from_user
                chat_obj = event.chat_join_request.chat

        if not session:
            return await handler(event, data)


        db_user = None
        db_group = None

        # 1. Ensure user exists in DB
        if user_obj and not user_obj.is_bot:
            result = await session.execute(select(User).where(User.user_id == user_obj.id))
            db_user = result.scalars().first()

            if not db_user:
                db_user = User(
                    user_id=user_obj.id,
                    username=user_obj.username,
                    first_name=user_obj.first_name or "",
                    last_name=user_obj.last_name,
                )
                session.add(db_user)
                await session.flush()
            else:
                # Update info if changed
                if db_user.username != user_obj.username or db_user.first_name != (user_obj.first_name or ""):
                    db_user.username = user_obj.username
                    db_user.first_name = user_obj.first_name or ""
                    db_user.last_name = user_obj.last_name

            data["db_user"] = db_user

        # Auto-upsert replied-to user if present
        if isinstance(event, Message) and event.reply_to_message and event.reply_to_message.from_user:
            r_user = event.reply_to_message.from_user
            if not r_user.is_bot:
                r_res = await session.execute(select(User).where(User.user_id == r_user.id))
                db_r = r_res.scalars().first()
                if not db_r:
                    session.add(
                        User(
                            user_id=r_user.id,
                            username=r_user.username,
                            first_name=r_user.first_name or "",
                            last_name=r_user.last_name,
                        )
                    )
                    await session.flush()
                else:
                    if db_r.username != r_user.username or db_r.first_name != (r_user.first_name or ""):
                        db_r.username = r_user.username
                        db_r.first_name = r_user.first_name or ""
                        db_r.last_name = r_user.last_name

        # Auto-upsert text_mention users if present
        if isinstance(event, Message) and event.entities:
            for ent in event.entities:
                if ent.type == "text_mention" and ent.user and not ent.user.is_bot:
                    tm_u = ent.user
                    tm_res = await session.execute(select(User).where(User.user_id == tm_u.id))
                    db_tm = tm_res.scalars().first()
                    if not db_tm:
                        session.add(
                            User(
                                user_id=tm_u.id,
                                username=tm_u.username,
                                first_name=tm_u.first_name or "",
                                last_name=tm_u.last_name,
                            )
                        )
                        await session.flush()


        # 2. Ensure group exists in DB if in a supergroup / group
        if chat_obj and chat_obj.type in (ChatType.SUPERGROUP, ChatType.GROUP):
            result = await session.execute(select(Group).where(Group.chat_id == chat_obj.id))
            db_group = result.scalars().first()
            if not db_group:
                db_group = Group(
                    chat_id=chat_obj.id,
                    title=chat_obj.title or "Group",
                    username=chat_obj.username,
                    is_active=True,
                )
                session.add(db_group)
                # Also add default TTL settings
                ttl_cfg = TTLSettings(
                    chat_id=chat_obj.id,
                    mod_ttl=settings.default_mod_ttl,
                    fun_ttl=settings.default_fun_ttl,
                    rules_ttl=settings.default_rules_ttl,
                    warn_ttl=settings.default_warn_ttl,
                    general_ttl=settings.default_general_ttl,
                    delete_command_trigger=True,
                )
                session.add(ttl_cfg)
                await session.flush()
            else:
                if db_group.title != (chat_obj.title or "Group"):
                    db_group.title = chat_obj.title or "Group"
                    db_group.username = chat_obj.username

            data["db_group"] = db_group

            # Check permissions for user in group
            if user_obj and bot:
                if is_super_admin(user_obj.id):
                    data["is_admin"] = True
                    data["is_owner"] = True
                    data["can_restrict"] = True
                    data["can_delete"] = True
                    data["can_pin"] = True
                else:
                    member = await get_chat_member_safe(bot, chat_obj.id, user_obj.id)
                    data["is_admin"] = is_admin(member, user_obj.id)
                    data["is_owner"] = is_owner(member, user_obj.id)
                    data["can_restrict"] = can_restrict(member, user_obj.id)
                    data["can_delete"] = can_delete(member, user_obj.id)
                    data["can_pin"] = can_pin(member, user_obj.id)

            # Processing incoming group messages
            if isinstance(event, Message):
                # 1. Clean Service Messages (Exclude join/leave so event handlers can trigger welcome/captcha)
                if db_group.clean_service_enabled:
                    is_service = bool(
                        event.pinned_message
                        or event.video_chat_started
                        or event.video_chat_ended
                        or event.video_chat_participants_invited
                        or event.new_chat_title
                        or event.new_chat_photo
                        or event.delete_chat_photo
                    )
                    if is_service:
                        try:
                            await event.delete()
                            return None
                        except Exception:
                            pass


                # 2. Anti-Channel Protection
                if db_group.antichannel_enabled and event.sender_chat and event.sender_chat.id != chat_obj.id:
                    try:
                        await event.delete()
                        if db_group.antichannel_mode == "ban" and bot:
                            await bot.ban_chat_sender_chat(chat_id=chat_obj.id, sender_chat_id=event.sender_chat.id)
                        return None
                    except Exception:
                        pass

                # 3. Granular Content Locks Enforcement (Non-Admins only)
                if not data.get("is_admin", False) and db_group.locked_types:
                    from src.services.locks_service import LocksService
                    violation = LocksService.check_message_locks(db_group, event)
                    if violation:
                        try:
                            await event.delete()
                            return None
                        except Exception:
                            pass

                # 4. Federation Ban Auto-Enforcement
                if not data.get("is_admin", False) and user_obj and not user_obj.is_bot:
                    from src.services.federation_service import FederationService
                    fed = await FederationService.get_group_federation(session, chat_obj.id)
                    if fed:
                        f_ban = await FederationService.is_user_fed_banned(session, fed.fed_id, user_obj.id)
                        if f_ban:
                            try:
                                await event.delete()
                            except Exception:
                                pass
                            if bot:
                                try:
                                    await bot.ban_chat_member(chat_id=chat_obj.id, user_id=user_obj.id)
                                except Exception:
                                    pass
                            return None

                # 5. Message caching, activity recording, and GroupMember upserting
                if user_obj and not user_obj.is_bot:

                    from datetime import datetime
                    from src.services.quote_service import QuoteService
                    from src.services.stats_service import StatsService
                    
                    # Upsert GroupMember
                    gm_res = await session.execute(
                        select(GroupMember).where(GroupMember.chat_id == chat_obj.id, GroupMember.user_id == user_obj.id)
                    )
                    db_gm = gm_res.scalars().first()

                    if not db_gm:
                        db_gm = GroupMember(
                            chat_id=chat_obj.id,
                            user_id=user_obj.id,
                            message_count=1,
                            last_active_at=datetime.utcnow(),
                        )
                        session.add(db_gm)
                    else:
                        db_gm.message_count += 1
                        db_gm.last_active_at = datetime.utcnow()

                    await QuoteService.cache_chat_message(chat_obj.id, event)
                    if session:
                        await StatsService.record_activity(session, chat_obj.id, user_obj.id, event)
                        if bot:
                            await QuoteService.check_and_trigger_quote_popup(bot, session, chat_obj.id)

        else:
            # Private chat or channel
            is_super = is_super_admin(user_obj.id) if user_obj else False
            data["is_admin"] = is_super
            data["is_owner"] = is_super
            data["can_restrict"] = is_super
            data["can_delete"] = is_super
            data["can_pin"] = is_super

        return await handler(event, data)

