from typing import Optional
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import TTLType
from src.middlewares.ttl import reply_with_ttl
from src.models.filter import GroupFilter
from src.models.group import Group
from src.utils.text_formatter import escape_html

router = Router(name="events_filters")


@router.message(Command("filter"))
async def handle_add_filter(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not is_admin:
        await message.answer("❌ Only administrators can configure filters.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await reply_with_ttl(
            message,
            "⚠️ Usage: <code>/filter &lt;keyword&gt; &lt;reply_text&gt;</code>",
            ttl_type=TTLType.MODERATION,
        )
        return

    keyword = parts[1].strip().lower()
    response_text = parts[2].strip()

    # Remove existing filter with same keyword if exists
    await session.execute(
        delete(GroupFilter).where(
            GroupFilter.chat_id == db_group.chat_id,
            GroupFilter.keyword == keyword,
        )
    )

    new_filter = GroupFilter(
        chat_id=db_group.chat_id,
        keyword=keyword,
        response_text=response_text,
    )
    session.add(new_filter)
    await reply_with_ttl(
        message,
        f"✅ Filter added! When someone says <code>{escape_html(keyword)}</code>, I will reply with your custom response.",
        ttl_type=TTLType.MODERATION,
    )


@router.message(Command("stop"))
async def handle_remove_filter(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not is_admin:
        await message.answer("❌ Only administrators can configure filters.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await reply_with_ttl(
            message,
            "⚠️ Usage: <code>/stop &lt;keyword&gt;</code>",
            ttl_type=TTLType.MODERATION,
        )
        return

    keyword = parts[1].strip().lower()
    result = await session.execute(
        delete(GroupFilter).where(
            GroupFilter.chat_id == db_group.chat_id,
            GroupFilter.keyword == keyword,
        )
    )
    if result.rowcount > 0:
        await reply_with_ttl(
            message,
            f"🗑️ Filter for <code>{escape_html(keyword)}</code> has been deleted.",
            ttl_type=TTLType.MODERATION,
        )
    else:
        await reply_with_ttl(
            message,
            f"❌ No active filter found for <code>{escape_html(keyword)}</code>.",
            ttl_type=TTLType.MODERATION,
        )


@router.message(Command("filters"))
async def handle_list_filters(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    res = await session.execute(
        select(GroupFilter).where(GroupFilter.chat_id == db_group.chat_id)
    )
    filters = res.scalars().all()
    if not filters:
        await reply_with_ttl(
            message,
            "📋 <b>Active Filters:</b> None configured.",
            ttl_type=TTLType.RULES,
        )
        return

    lines = ["📋 <b>Active Group Filters:</b>\n"]
    for f in filters:
        lines.append(f"• <code>{escape_html(f.keyword)}</code>")

    await reply_with_ttl(
        message, "\n".join(lines), ttl_type=TTLType.RULES, custom_ttl=45
    )


# Passive keyword filter matcher
@router.message(F.text, ~F.text.startswith("/"))
async def handle_filter_trigger(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
):
    if not message.text or not db_group or not session:
        return

    text_lower = message.text.lower()
    res = await session.execute(
        select(GroupFilter).where(GroupFilter.chat_id == db_group.chat_id)
    )
    filters = res.scalars().all()

    for flt in filters:
        if flt.keyword in text_lower:
            await reply_with_ttl(
                message,
                flt.response_text or "",
                ttl_type=TTLType.GENERAL,
                custom_ttl=flt.custom_ttl,
                delete_trigger=False,
            )
            break
