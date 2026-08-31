import asyncio
from typing import Optional
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import ActionType, TTLType
from src.keyboards.games_kb import get_duel_keyboard
from src.middlewares.ttl import reply_with_ttl, schedule_auto_delete
from src.models.group import Group
from src.models.user import User
from src.services.audit_service import AuditService
from src.services.games_service import GamesService
from src.utils.emojis import E_DIAMOND, E_FIRE, E_LIGHTNING, E_SPARKLES, E_STAR, E_TOP
from src.utils.text_formatter import get_user_mention, mention_html

router = Router(name="fun_games")


@router.message(Command("roulette"))
async def handle_russian_roulette(
    message: Message,
    db_group: Optional[Group] = None,
    db_user: Optional[User] = None,
):
    """Russian roulette with 1-in-6 chance of 60s temporary mute."""
    if not db_group or not db_user:
        await message.answer("⚠️ Russian Roulette can only be played in supergroups.")
        return

    survived, result_text = await GamesService.play_russian_roulette(
        bot=message.bot,
        group=db_group,
        user=db_user,
        message=message,
    )
    await reply_with_ttl(
        message,
        result_text,
        ttl_type=TTLType.FUN,
        custom_ttl=25 if survived else 60,
    )

    # Log game result
    user_name = message.from_user.full_name if message.from_user else "User"
    user_id = message.from_user.id if message.from_user else 0
    outcome = "Survived (*click*)" if survived else "BANG! Muted for 60s (+50 coins earned)"
    await AuditService.log_action(
        bot=message.bot,
        chat_id=db_group.chat_id,
        chat_title=db_group.title,
        target_user_id=user_id,
        target_user_name=user_name,
        action=ActionType.GAME_PLAY,
        reason=f"Russian Roulette: {outcome}",
        channel_id=db_group.log_channel_id,
    )


@router.message(Command("dice"))
async def handle_dice(
    message: Message,
    db_group: Optional[Group] = None,
):
    dice_msg = await message.answer_dice(emoji="🎲")
    await schedule_auto_delete(message.chat.id, dice_msg.message_id, ttl_seconds=30)
    await schedule_auto_delete(message.chat.id, message.message_id, ttl_seconds=30)


@router.message(Command("darts", "dart"))
async def handle_darts(
    message: Message,
    db_group: Optional[Group] = None,
):
    dice_msg = await message.answer_dice(emoji="🎯")
    await schedule_auto_delete(message.chat.id, dice_msg.message_id, ttl_seconds=30)
    await schedule_auto_delete(message.chat.id, message.message_id, ttl_seconds=30)


@router.message(Command("slots", "slot"))
async def handle_slots(
    message: Message,
    db_group: Optional[Group] = None,
    db_user: Optional[User] = None,
    session: Optional[AsyncSession] = None,
):
    dice_msg = await message.answer_dice(emoji="🎰")
    value = dice_msg.dice.value
    desc, reward = GamesService.evaluate_dice_score("🎰", value)
    if db_user and reward > 0 and session:
        db_user.coins += reward
        await session.commit()

        # Log jackpot / slot win
        if db_group:
            user_name = message.from_user.full_name if message.from_user else "User"
            await AuditService.log_action(
                bot=message.bot,
                chat_id=db_group.chat_id,
                chat_title=db_group.title,
                target_user_id=db_user.user_id,
                target_user_name=user_name,
                action=ActionType.GAME_PLAY,
                reason=f"Slots Reward: {desc} (+{reward} coins)",
                channel_id=db_group.log_channel_id,
            )

    await schedule_auto_delete(message.chat.id, dice_msg.message_id, ttl_seconds=30)
    await schedule_auto_delete(message.chat.id, message.message_id, ttl_seconds=30)


@router.message(Command("basketball"))
async def handle_basketball(message: Message):
    dice_msg = await message.answer_dice(emoji="🏀")
    await schedule_auto_delete(message.chat.id, dice_msg.message_id, ttl_seconds=30)
    await schedule_auto_delete(message.chat.id, message.message_id, ttl_seconds=30)


@router.message(Command("football"))
async def handle_football(message: Message):
    dice_msg = await message.answer_dice(emoji="⚽")
    await schedule_auto_delete(message.chat.id, dice_msg.message_id, ttl_seconds=30)
    await schedule_auto_delete(message.chat.id, message.message_id, ttl_seconds=30)


@router.message(Command("bowling"))
async def handle_bowling(message: Message):
    dice_msg = await message.answer_dice(emoji="🎳")
    await schedule_auto_delete(message.chat.id, dice_msg.message_id, ttl_seconds=30)
    await schedule_auto_delete(message.chat.id, message.message_id, ttl_seconds=30)


@router.message(Command("duel"))
async def handle_duel(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_user: Optional[User] = None,
):
    if not session or not db_user or not message.from_user:
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await reply_with_ttl(
            message,
            "⚠️ Reply to the user you want to challenge to a dice duel!\nUsage: <code>/duel [bet_amount]</code>",
            ttl_type=TTLType.FUN,
        )
        return

    opponent_tg = message.reply_to_message.from_user
    if opponent_tg.id == message.from_user.id or opponent_tg.is_bot:
        await reply_with_ttl(
            message, "❌ You cannot duel yourself or bots!", ttl_type=TTLType.FUN
        )
        return

    # Parse bet amount
    parts = message.text.split()
    amount = 50
    if len(parts) > 1 and parts[1].isdigit():
        amount = int(parts[1])

    if db_user.coins < amount:
        await reply_with_ttl(
            message,
            f"❌ You do not have enough coins! Balance: {db_user.coins} coins.",
            ttl_type=TTLType.FUN,
        )
        return

    challenger_mention = get_user_mention(message.from_user)
    opponent_mention = get_user_mention(opponent_tg)

    text = (
        f"⚔️ <b>DICE DUEL CHALLENGE</b> ⚔️\n\n"
        f"{challenger_mention} has challenged {opponent_mention} to a duel for <b>{amount} coins</b> {E_FIRE}!\n"
        f"Do you accept the challenge?"
    )

    kb = get_duel_keyboard(
        challenger_id=message.from_user.id,
        opponent_id=opponent_tg.id,
        amount=amount,
    )
    await reply_with_ttl(
        message, text, ttl_type=TTLType.FUN, reply_markup=kb, custom_ttl=60
    )


@router.callback_query(F.data.startswith("duel:"))
async def handle_duel_callback(
    call: CallbackQuery,
    session: Optional[AsyncSession] = None,
):
    if not session or not call.message or not call.from_user:
        return

    parts = call.data.split(":")
    action = parts[1]
    challenger_id = int(parts[2])
    opponent_id = int(parts[3])
    amount = int(parts[4])

    if call.from_user.id != opponent_id:
        await call.answer("❌ This duel challenge is not for you!", show_alert=True)
        return

    if action == "decline":
        await call.message.edit_text(
            f"❌ The duel challenge was declined by {get_user_mention(call.from_user)}."
        )
        return

    # Fetch challenger & opponent users from DB
    res_c = await session.execute(
        select(User).where(User.user_id == challenger_id)
    )
    challenger = res_c.scalar_one_or_none()

    res_o = await session.execute(
        select(User).where(User.user_id == opponent_id)
    )
    opponent = res_o.scalar_one_or_none()

    if not challenger or not opponent:
        await call.answer("Player data not found.")
        return

    if challenger.coins < amount or opponent.coins < amount:
        await call.message.edit_text("❌ One of the players no longer has enough coins.")
        return

    await call.message.edit_text(f"{E_LIGHTNING} <b>Rolling dice for the duel...</b>", parse_mode="HTML")

    # Challenger roll
    c_dice = await call.message.answer_dice(emoji="🎲")
    await asyncio.sleep(2)
    # Opponent roll
    o_dice = await call.message.answer_dice(emoji="🎲")
    await asyncio.sleep(2)

    c_score = c_dice.dice.value
    o_score = o_dice.dice.value

    c_mention = mention_html(challenger.user_id, challenger.first_name)
    o_mention = mention_html(opponent.user_id, opponent.first_name)

    winner_name = None
    if c_score > o_score:
        challenger.coins += amount
        opponent.coins -= amount
        winner_name = challenger.first_name
        res_text = (
            f"{E_TOP} {c_mention} (🎲 {c_score}) defeated {o_mention} (🎲 {o_score})!\n"
            f"{E_DIAMOND} Won <b>+{amount} coins</b>!"
        )
    elif o_score > c_score:
        opponent.coins += amount
        challenger.coins -= amount
        winner_name = opponent.first_name
        res_text = (
            f"{E_TOP} {o_mention} (🎲 {o_score}) defeated {c_mention} (🎲 {c_score})!\n"
            f"{E_DIAMOND} Won <b>+{amount} coins</b>!"
        )
    else:
        res_text = f"🤝 It's a draw! Both rolled 🎲 {c_score}. Coins returned."

    await session.commit()
    sent_res = await call.message.answer(res_text, parse_mode="HTML")

    # Audit log duel
    res_summary = f"{challenger.first_name} ({c_score}) vs {opponent.first_name} ({o_score}) — Winner: {winner_name or 'Draw'} ({amount} coins)"
    await AuditService.log_action(
        bot=call.bot,
        chat_id=call.message.chat.id,
        chat_title=call.message.chat.title or "Group",
        target_user_id=opponent_id,
        target_user_name=opponent.first_name,
        admin_user_id=challenger_id,
        admin_user_name=challenger.first_name,
        action=ActionType.GAME_PLAY,
        reason=f"Dice Duel: {res_summary}",
    )

    await schedule_auto_delete(call.message.chat.id, sent_res.message_id, 30)
    await schedule_auto_delete(call.message.chat.id, c_dice.message_id, 30)
    await schedule_auto_delete(call.message.chat.id, o_dice.message_id, 30)
