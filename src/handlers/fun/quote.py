from datetime import datetime
from typing import List, Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import TTLType
from src.keyboards.quote_kb import get_quote_reaction_keyboard
from src.middlewares.ttl import reply_with_ttl
from src.services.quote_service import QuoteMessageData, QuoteService
from src.utils.emojis import E_SPARKLES, E_STAR

router = Router(name="fun_quote")


@router.message(Command("q", "quote"))
async def handle_quote(
    message: Message,
    session: Optional[AsyncSession] = None,
):
    if not message.reply_to_message:
        await reply_with_ttl(
            message,
            f"{E_SPARKLES} <b>Quote Sticker Engine</b>\n"
            "<b>Usage:</b> Reply to a message with <code>/q [r] [color] [1-5]</code>\n"
            "• <b>Colors:</b> <code>pink</code>, <code>blue</code>, <code>cyan</code>, <code>red</code>, <code>orange</code>, <code>green</code>, <code>purple</code>, <code>gold</code>, <code>dark</code>\n"
            "• <b>Reply Context:</b> <code>/q r</code>\n"
            "• <b>Multi-Message:</b> <code>/q 2</code> to <code>/q 5</code>\n"
            "• <b>Random Quote:</b> <code>/qrand</code>",
            ttl_type=TTLType.FUN,
        )
        return

    raw_args = message.text.split()[1:] if message.text else []
    color_key, include_reply, count = QuoteService.parse_quote_args(raw_args)

    target_msg = message.reply_to_message
    if not target_msg.from_user:
        await reply_with_ttl(
            message, "❌ Cannot quote anonymous/channel messages.", ttl_type=TTLType.FUN
        )
        return

    # Prepare message list
    quote_messages: List[QuoteMessageData] = []

    # Fetch avatar for primary user
    avatar_img = await QuoteService.fetch_user_avatar(
        message.bot, target_msg.from_user.id
    )

    primary_text = target_msg.text or target_msg.caption or "[Media / Sticker]"
    reply_author = None
    reply_snippet = None

    if include_reply and target_msg.reply_to_message and target_msg.reply_to_message.from_user:
        reply_author = (
            target_msg.reply_to_message.from_user.first_name
            or f"User {target_msg.reply_to_message.from_user.id}"
        )
        reply_snippet = (
            target_msg.reply_to_message.text
            or target_msg.reply_to_message.caption
            or "[Media]"
        )[:50]

    primary_data = QuoteMessageData(
        message_id=target_msg.message_id,
        user_id=target_msg.from_user.id,
        first_name=target_msg.from_user.first_name or f"User {target_msg.from_user.id}",
        username=target_msg.from_user.username,
        text=primary_text,
        date_str=(target_msg.date or datetime.now()).strftime("%H:%M"),
        avatar_img=avatar_img,
        reply_user_name=reply_author,
        reply_text=reply_snippet,
    )
    quote_messages.append(primary_data)

    # Multi-message lookup if count > 1
    if count > 1:
        cached_msgs = await QuoteService.get_sequential_messages(
            chat_id=message.chat.id,
            start_msg_id=target_msg.message_id,
            count=count,
        )
        if len(cached_msgs) > 1:
            cached_msgs[0].avatar_img = avatar_img
            quote_messages = cached_msgs

    try:
        sticker_bio = QuoteService.generate_quote_image(
            messages=quote_messages,
            color_key=color_key,
            include_reply=include_reply,
        )

        # 1. Send sticker first to obtain file_id
        sent_sticker = await message.bot.send_sticker(
            chat_id=message.chat.id,
            sticker=BufferedInputFile(sticker_bio.getvalue(), filename="quote.webp"),
            reply_to_message_id=target_msg.message_id,
        )

        # 2. Save quote sticker in database
        quote_id = None
        if session and sent_sticker.sticker:
            saved_quote = await QuoteService.save_quote(
                session=session,
                chat_id=message.chat.id,
                message_id=target_msg.message_id,
                user_id=target_msg.from_user.id,
                file_id=sent_sticker.sticker.file_id,
                text_snippet=primary_text[:100],
            )
            await session.commit()
            quote_id = saved_quote.id

        # 3. Attach Like/Dislike reaction keyboard to the sticker
        if quote_id:
            try:
                kb = get_quote_reaction_keyboard(quote_id, likes=0, dislikes=0)
                await message.bot.edit_message_reply_markup(
                    chat_id=message.chat.id,
                    message_id=sent_sticker.message_id,
                    reply_markup=kb,
                )
            except Exception as e:
                logger.debug(f"Sticker reply markup edit note: {e}")

        # Delete trigger command message
        try:
            await message.delete()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Failed to generate quote sticker: {e}")
        await reply_with_ttl(
            message,
            f"❌ Failed to generate quote sticker: {e}",
            ttl_type=TTLType.FUN,
        )


@router.message(Command("qrand", "quoterand"))
async def handle_quote_rand(
    message: Message,
    session: Optional[AsyncSession] = None,
):
    if not session:
        return

    quote = await QuoteService.get_random_quote(session, chat_id=message.chat.id)
    if not quote:
        await reply_with_ttl(
            message,
            f"{E_STAR} <b>No quotes found for this group!</b>\n"
            "Use <code>/q</code> on any message to generate and save quote stickers to the group archive.",
            ttl_type=TTLType.FUN,
        )
        return

    try:
        likes, dislikes = await QuoteService.get_quote_reactions(quote.id)
        kb = get_quote_reaction_keyboard(quote.id, likes=likes, dislikes=dislikes)
        await message.bot.send_sticker(
            chat_id=message.chat.id,
            sticker=quote.file_id,
            reply_markup=kb,
        )
    except Exception as e:
        logger.error(f"Failed to send random quote: {e}")
        await reply_with_ttl(
            message, "❌ Failed to retrieve random quote sticker.", ttl_type=TTLType.FUN
        )


@router.callback_query(F.data.startswith("quote_react:"))
async def handle_quote_reaction(
    call: CallbackQuery,
    session: Optional[AsyncSession] = None,
):
    if not session or not call.data:
        await call.answer()
        return

    parts = call.data.split(":")
    if len(parts) != 3:
        await call.answer()
        return

    action = parts[1]  # "like" or "dislike"
    try:
        quote_id = int(parts[2])
    except ValueError:
        await call.answer()
        return

    likes, dislikes, status_msg = await QuoteService.toggle_reaction(
        session=session,
        quote_id=quote_id,
        user_id=call.from_user.id,
        action=action,
    )

    try:
        new_kb = get_quote_reaction_keyboard(quote_id, likes=likes, dislikes=dislikes)
        if call.message:
            await call.bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=new_kb,
            )
    except Exception as e:
        logger.debug(f"Reaction edit markup note: {e}")

    await call.answer(status_msg)
