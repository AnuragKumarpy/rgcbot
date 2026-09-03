
from aiogram.types import Message


async def resolve_target(message: Message):
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1 and parts[1].startswith("@"):
        try:
            return await message.bot.get_chat(parts[1])
        except Exception:
            return None
    return None


def display_name(entity) -> str:
    if hasattr(entity, "full_name") and entity.full_name:
        return entity.full_name
    first = getattr(entity, "first_name", "") or ""
    last = getattr(entity, "last_name", "") or ""
    return f"{first} {last}".strip() or str(entity.id)
