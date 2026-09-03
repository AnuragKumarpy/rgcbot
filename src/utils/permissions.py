from typing import Optional
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMember, ChatMemberAdministrator, ChatMemberOwner
from loguru import logger
from src.config.settings import settings


def is_super_admin(user_id: int) -> bool:
    return user_id in settings.bot_super_admins


# Alias to prevent any naming collision (handles both conventions)
is_super_user = is_super_admin


async def get_chat_member_safe(bot: Bot, chat_id: int, user_id: int) -> Optional[ChatMember]:
    try:
        return await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    except Exception as e:
        logger.warning(f"Failed to get chat member {user_id} in {chat_id}: {e}")
        return None


def is_admin(member: Optional[ChatMember], user_id: int) -> bool:
    if is_super_admin(user_id):
        return True
    if member is None:
        return False
    return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)


def is_owner(member: Optional[ChatMember], user_id: int) -> bool:
    if is_super_admin(user_id):
        return True
    if member is None:
        return False
    return member.status == ChatMemberStatus.CREATOR


def can_restrict(member: Optional[ChatMember], user_id: int) -> bool:
    if is_super_admin(user_id):
        return True
    if member is None:
        return False
    if isinstance(member, ChatMemberOwner):
        return True
    if isinstance(member, ChatMemberAdministrator):
        return member.can_restrict_members
    return False


def can_delete(member: Optional[ChatMember], user_id: int) -> bool:
    if is_super_admin(user_id):
        return True
    if member is None:
        return False
    if isinstance(member, ChatMemberOwner):
        return True
    if isinstance(member, ChatMemberAdministrator):
        return member.can_delete_messages
    return False


def can_pin(member: Optional[ChatMember], user_id: int) -> bool:
    if is_super_admin(user_id):
        return True
    if member is None:
        return False
    if isinstance(member, ChatMemberOwner):
        return True
    if isinstance(member, ChatMemberAdministrator):
        return member.can_pin_messages
    return False