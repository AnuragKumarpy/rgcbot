from datetime import datetime, timedelta
from typing import Optional, Tuple
from aiogram import Bot
from aiogram.types import ChatPermissions
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import ActionType, WarnAction
from src.models.group import Group
from src.models.log import ModerationLog
from src.models.member import GroupMember
from src.models.user import User
from src.services.audit_service import AuditService
from src.utils.permissions import is_super_admin
from src.utils.time_parser import format_duration


class ModerationService:
    @staticmethod
    async def ensure_user(
        session: AsyncSession,
        user_id: int,
        first_name: str = "",
        username: Optional[str] = None,
    ) -> User:
        """Ensures a user record exists in the users table to prevent FK violations."""
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                user_id=user_id,
                username=username,
                first_name=first_name or f"User {user_id}",
            )
            session.add(user)
            await session.flush()
        else:
            # Update names if provided
            if first_name and user.first_name != first_name:
                user.first_name = first_name
            if username and user.username != username:
                user.username = username
        return user

    @staticmethod
    async def ensure_group(
        session: AsyncSession,
        chat_id: int,
        title: str = "Group",
    ) -> Group:
        """Ensures a group record exists in the groups table to prevent FK violations."""
        result = await session.execute(select(Group).where(Group.chat_id == chat_id))
        group = result.scalar_one_or_none()
        if not group:
            group = Group(chat_id=chat_id, title=title, is_active=True)
            session.add(group)
            await session.flush()
        return group

    @classmethod
    async def get_or_create_member(
        cls,
        session: AsyncSession,
        chat_id: int,
        user_id: int,
        first_name: str = "",
        username: Optional[str] = None,
        chat_title: str = "Group",
    ) -> GroupMember:
        # Guarantee parent rows exist
        await cls.ensure_user(session, user_id, first_name=first_name, username=username)
        await cls.ensure_group(session, chat_id, title=chat_title)

        result = await session.execute(
            select(GroupMember).where(
                GroupMember.chat_id == chat_id, GroupMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            member = GroupMember(chat_id=chat_id, user_id=user_id)
            session.add(member)
            await session.flush()
        return member

    @classmethod
    async def ban_user(
        cls,
        bot: Bot,
        session: AsyncSession,
        group: Group,
        target_user: User,
        admin_user: Optional[User],
        reason: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> bool:
        until_date = None
        action_type = ActionType.BAN
        duration_str = None

        if duration_seconds and duration_seconds > 0:
            until_date = datetime.utcnow() + timedelta(seconds=duration_seconds)
            action_type = ActionType.TEMPBAN
            duration_str = format_duration(duration_seconds)

        if is_super_admin(target_user.user_id):
            return False  # Prevent super admin ban

        # Telegram API Call
        await bot.ban_chat_member(
            chat_id=group.chat_id,
            user_id=target_user.user_id,
            until_date=until_date,
            revoke_messages=False,
        )

        # Ensure DB records exist
        await cls.ensure_user(
            session, target_user.user_id, target_user.first_name, target_user.username
        )
        if admin_user:
            await cls.ensure_user(
                session, admin_user.user_id, admin_user.first_name, admin_user.username
            )

        # Update DB Member
        member = await cls.get_or_create_member(
            session,
            group.chat_id,
            target_user.user_id,
            target_user.first_name,
            target_user.username,
            group.title,
        )
        member.is_banned = True

        # Write Log
        log = ModerationLog(
            chat_id=group.chat_id,
            target_user_id=target_user.user_id,
            admin_user_id=admin_user.user_id if admin_user else None,
            action_type=action_type.value,
            reason=reason,
            duration_seconds=duration_seconds,
        )
        session.add(log)

        # Audit Channel
        await AuditService.log_action(
            bot=bot,
            chat_id=group.chat_id,
            chat_title=group.title,
            target_user_id=target_user.user_id,
            target_user_name=target_user.first_name,
            admin_user_id=admin_user.user_id if admin_user else None,
            admin_user_name=admin_user.first_name if admin_user else None,
            action=action_type,
            reason=reason,
            duration_str=duration_str,
            channel_id=group.log_channel_id,
        )
        return True

    @classmethod
    async def unban_user(
        cls,
        bot: Bot,
        session: AsyncSession,
        group: Group,
        target_user: User,
        admin_user: Optional[User],
        reason: Optional[str] = None,
    ) -> bool:
        await bot.unban_chat_member(
            chat_id=group.chat_id,
            user_id=target_user.user_id,
            only_if_banned=True,
        )

        await cls.ensure_user(
            session, target_user.user_id, target_user.first_name, target_user.username
        )
        if admin_user:
            await cls.ensure_user(
                session, admin_user.user_id, admin_user.first_name, admin_user.username
            )

        member = await cls.get_or_create_member(
            session,
            group.chat_id,
            target_user.user_id,
            target_user.first_name,
            target_user.username,
            group.title,
        )
        member.is_banned = False

        log = ModerationLog(
            chat_id=group.chat_id,
            target_user_id=target_user.user_id,
            admin_user_id=admin_user.user_id if admin_user else None,
            action_type=ActionType.UNBAN.value,
            reason=reason,
        )
        session.add(log)

        await AuditService.log_action(
            bot=bot,
            chat_id=group.chat_id,
            chat_title=group.title,
            target_user_id=target_user.user_id,
            target_user_name=target_user.first_name,
            admin_user_id=admin_user.user_id if admin_user else None,
            admin_user_name=admin_user.first_name if admin_user else None,
            action=ActionType.UNBAN,
            reason=reason,
            channel_id=group.log_channel_id,
        )
        return True

    @classmethod
    async def mute_user(
        cls,
        bot: Bot,
        session: AsyncSession,
        group: Group,
        target_user: User,
        admin_user: Optional[User],
        reason: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> bool:
        until_date = None
        action_type = ActionType.MUTE
        duration_str = None

        if duration_seconds and duration_seconds > 0:
            until_date = datetime.utcnow() + timedelta(seconds=duration_seconds)
            action_type = ActionType.TEMPMUTE
            duration_str = format_duration(duration_seconds)

        no_permissions = ChatPermissions(
            can_send_messages=False,
            can_send_audios=False,
            can_send_documents=False,
            can_send_photos=False,
            can_send_videos=False,
            can_send_video_notes=False,
            can_send_voice_notes=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
        )
        
        if is_super_admin(target_user.user_id):
            return False  # Prevent super admin mute

        await bot.restrict_chat_member(
            chat_id=group.chat_id,
            user_id=target_user.user_id,
            permissions=no_permissions,
            until_date=until_date,
        )

        await cls.ensure_user(
            session, target_user.user_id, target_user.first_name, target_user.username
        )
        if admin_user:
            await cls.ensure_user(
                session, admin_user.user_id, admin_user.first_name, admin_user.username
            )

        member = await cls.get_or_create_member(
            session,
            group.chat_id,
            target_user.user_id,
            target_user.first_name,
            target_user.username,
            group.title,
        )
        member.is_muted = True
        member.muted_until = until_date

        log = ModerationLog(
            chat_id=group.chat_id,
            target_user_id=target_user.user_id,
            admin_user_id=admin_user.user_id if admin_user else None,
            action_type=action_type.value,
            reason=reason,
            duration_seconds=duration_seconds,
        )
        session.add(log)

        await AuditService.log_action(
            bot=bot,
            chat_id=group.chat_id,
            chat_title=group.title,
            target_user_id=target_user.user_id,
            target_user_name=target_user.first_name,
            admin_user_id=admin_user.user_id if admin_user else None,
            admin_user_name=admin_user.first_name if admin_user else None,
            action=action_type,
            reason=reason,
            duration_str=duration_str,
            channel_id=group.log_channel_id,
        )
        return True

    @classmethod
    async def unmute_user(
        cls,
        bot: Bot,
        session: AsyncSession,
        group: Group,
        target_user: User,
        admin_user: Optional[User],
        reason: Optional[str] = None,
    ) -> bool:
        # Restore normal default permissions
        default_permissions = ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_invite_users=True,
        )

        await bot.restrict_chat_member(
            chat_id=group.chat_id,
            user_id=target_user.user_id,
            permissions=default_permissions,
        )

        await cls.ensure_user(
            session, target_user.user_id, target_user.first_name, target_user.username
        )
        if admin_user:
            await cls.ensure_user(
                session, admin_user.user_id, admin_user.first_name, admin_user.username
            )

        member = await cls.get_or_create_member(
            session,
            group.chat_id,
            target_user.user_id,
            target_user.first_name,
            target_user.username,
            group.title,
        )
        member.is_muted = False
        member.muted_until = None

        log = ModerationLog(
            chat_id=group.chat_id,
            target_user_id=target_user.user_id,
            admin_user_id=admin_user.user_id if admin_user else None,
            action_type=ActionType.UNMUTE.value,
            reason=reason,
        )
        session.add(log)

        await AuditService.log_action(
            bot=bot,
            chat_id=group.chat_id,
            chat_title=group.title,
            target_user_id=target_user.user_id,
            target_user_name=target_user.first_name,
            admin_user_id=admin_user.user_id if admin_user else None,
            admin_user_name=admin_user.first_name if admin_user else None,
            action=ActionType.UNMUTE,
            reason=reason,
            channel_id=group.log_channel_id,
        )
        return True

    @classmethod
    async def kick_user(
        cls,
        bot: Bot,
        session: AsyncSession,
        group: Group,
        target_user: User,
        admin_user: Optional[User],
        reason: Optional[str] = None,
    ) -> bool:
        if is_super_admin(target_user.user_id):
            return False  # Prevent super admin kick

        # Kick in Telegram is ban followed by immediate unban
        await bot.ban_chat_member(chat_id=group.chat_id, user_id=target_user.user_id)
        await bot.unban_chat_member(chat_id=group.chat_id, user_id=target_user.user_id)

        await cls.ensure_user(
            session, target_user.user_id, target_user.first_name, target_user.username
        )
        if admin_user:
            await cls.ensure_user(
                session, admin_user.user_id, admin_user.first_name, admin_user.username
            )

        log = ModerationLog(
            chat_id=group.chat_id,
            target_user_id=target_user.user_id,
            admin_user_id=admin_user.user_id if admin_user else None,
            action_type=ActionType.KICK.value,
            reason=reason,
        )
        session.add(log)

        await AuditService.log_action(
            bot=bot,
            chat_id=group.chat_id,
            chat_title=group.title,
            target_user_id=target_user.user_id,
            target_user_name=target_user.first_name,
            admin_user_id=admin_user.user_id if admin_user else None,
            admin_user_name=admin_user.first_name if admin_user else None,
            action=ActionType.KICK,
            reason=reason,
            channel_id=group.log_channel_id,
        )
        return True

    @classmethod
    async def warn_user(
        cls,
        bot: Bot,
        session: AsyncSession,
        group: Group,
        target_user: User,
        admin_user: Optional[User],
        reason: Optional[str] = None,
    ) -> Tuple[int, int, Optional[str]]:
        """
        Increments warning count. If max warns reached, executes escalation action.
        Returns: (current_warns, max_warns, escalation_action_taken_or_None)
        """
        if is_super_admin(target_user.user_id):
            return 0, group.max_warns, None  # No action for super admins

        await cls.ensure_user(
            session, target_user.user_id, target_user.first_name, target_user.username
        )
        if admin_user:
            await cls.ensure_user(
                session, admin_user.user_id, admin_user.first_name, admin_user.username
            )

        member = await cls.get_or_create_member(
            session,
            group.chat_id,
            target_user.user_id,
            target_user.first_name,
            target_user.username,
            group.title,
        )

        member.warnings_count += 1
        current_warns = member.warnings_count
        max_warns = group.max_warns

        escalated_action = None

        if current_warns >= max_warns:
            # Trigger escalation
            member.warnings_count = 0  # Reset on punishment
            if group.warn_action == WarnAction.BAN.value:
                escalated_action = "banned"
                await cls.ban_user(
                    bot,
                    session,
                    group,
                    target_user,
                    admin_user,
                    reason=f"Exceeded max warnings ({max_warns}/{max_warns}) - {reason or 'No reason'}",
                )
            elif group.warn_action == WarnAction.KICK.value:
                escalated_action = "kicked"
                await cls.kick_user(
                    bot,
                    session,
                    group,
                    target_user,
                    admin_user,
                    reason=f"Exceeded max warnings ({max_warns}/{max_warns}) - {reason or 'No reason'}",
                )
            else:  # Mute default
                escalated_action = f"muted for {format_duration(group.warn_duration_sec)}"
                await cls.mute_user(
                    bot,
                    session,
                    group,
                    target_user,
                    admin_user,
                    reason=f"Exceeded max warnings ({max_warns}/{max_warns}) - {reason or 'No reason'}",
                    duration_seconds=group.warn_duration_sec,
                )
        else:
            # Record warn log
            log = ModerationLog(
                chat_id=group.chat_id,
                target_user_id=target_user.user_id,
                admin_user_id=admin_user.user_id if admin_user else None,
                action_type=ActionType.WARN.value,
                reason=reason,
            )
            session.add(log)

            await AuditService.log_action(
                bot=bot,
                chat_id=group.chat_id,
                chat_title=group.title,
                target_user_id=target_user.user_id,
                target_user_name=target_user.first_name,
                admin_user_id=admin_user.user_id if admin_user else None,
                admin_user_name=admin_user.first_name if admin_user else None,
                action=ActionType.WARN,
                reason=f"[{current_warns}/{max_warns}] {reason or 'No reason'}",
                channel_id=group.log_channel_id,
            )

        return current_warns, max_warns, escalated_action

    @classmethod
    async def reset_warns(
        cls,
        bot: Bot,
        session: AsyncSession,
        group: Group,
        target_user: User,
        admin_user: Optional[User],
    ) -> bool:
        await cls.ensure_user(
            session, target_user.user_id, target_user.first_name, target_user.username
        )
        if admin_user:
            await cls.ensure_user(
                session, admin_user.user_id, admin_user.first_name, admin_user.username
            )

        member = await cls.get_or_create_member(
            session,
            group.chat_id,
            target_user.user_id,
            target_user.first_name,
            target_user.username,
            group.title,
        )
        member.warnings_count = 0

        log = ModerationLog(
            chat_id=group.chat_id,
            target_user_id=target_user.user_id,
            admin_user_id=admin_user.user_id if admin_user else None,
            action_type=ActionType.RESET_WARNS.value,
            reason="Admin reset warnings",
        )
        session.add(log)

        await AuditService.log_action(
            bot=bot,
            chat_id=group.chat_id,
            chat_title=group.title,
            target_user_id=target_user.user_id,
            target_user_name=target_user.first_name,
            admin_user_id=admin_user.user_id if admin_user else None,
            admin_user_name=admin_user.first_name if admin_user else None,
            action=ActionType.RESET_WARNS,
            reason="Warnings reset to 0",
            channel_id=group.log_channel_id,
        )
        return True