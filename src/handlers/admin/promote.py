from typing import Optional
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import TTLType
from src.fsm.promote_states import PromoteStates
from src.keyboards.promote_kb import PROMOTE_PERMISSIONS, PROMOTE_PRESETS, build_promote_keyboard
from src.middlewares.ttl import reply_with_ttl
from src.utils.emojis import E_CHECK, E_CROWN, E_WARN

router = Router(name="admin_promote")


@router.message(Command("promote"))
async def handle_promote_cmd(message: Message, state: FSMContext, session: Optional[AsyncSession] = None):
    if not session or message.chat.id >= 0:
        return
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await reply_with_ttl(
            message, f"{E_WARN} Reply to a user's message to promote them.", ttl_type=TTLType.MODERATION
        )
        return
    target = message.reply_to_message.from_user
    if target.is_bot:
        await reply_with_ttl(message, f"{E_WARN} Cannot promote bots this way.", ttl_type=TTLType.MODERATION)
        return

    perms = {key: False for key, _ in PROMOTE_PERMISSIONS}
    await state.update_data(target_user_id=target.id, target_name=target.full_name, perms=perms)
    await state.set_state(PromoteStates.choosing_permissions)

    await message.reply(
        f"{E_CROWN} Choose permissions to grant <b>{target.full_name}</b>:",
        reply_markup=build_promote_keyboard(perms),
        parse_mode="HTML",
    )


@router.callback_query(PromoteStates.choosing_permissions, F.data.startswith("promote_perm:"))
async def handle_toggle_permission(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":", 1)[1]
    data = await state.get_data()
    perms = data.get("perms", {})
    perms[key] = not perms.get(key, False)
    await state.update_data(perms=perms)
    await call.message.edit_reply_markup(reply_markup=build_promote_keyboard(perms))
    await call.answer()


@router.callback_query(PromoteStates.choosing_permissions, F.data.startswith("promote_preset:"))
async def handle_apply_preset(call: CallbackQuery, state: FSMContext):
    preset_name = call.data.split(":", 1)[1]
    perms = PROMOTE_PRESETS[preset_name].copy()
    await state.update_data(perms=perms)
    await call.message.edit_reply_markup(reply_markup=build_promote_keyboard(perms))
    await call.answer(f"Applied {preset_name.title()} preset")


@router.callback_query(PromoteStates.choosing_permissions, F.data == "promote_cancel")
async def handle_promote_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Promotion cancelled.")
    await call.answer()


@router.callback_query(PromoteStates.choosing_permissions, F.data == "promote_confirm")
async def handle_promote_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    perms = data.get("perms", {})
    target_user_id = data.get("target_user_id")
    target_name = data.get("target_name", "Member")
    await state.clear()

    if not any(perms.values()):
        await call.answer("Select at least one permission first.", show_alert=True)
        return

    try:
        await call.bot.promote_chat_member(
            chat_id=call.message.chat.id,
            user_id=target_user_id,
            is_anonymous=False,
            **perms,
        )
    except TelegramBadRequest as e:
        await call.message.edit_text(f"{E_WARN} Failed to promote: {e}")
        await call.answer()
        return

    granted = ", ".join(label for key, label in PROMOTE_PERMISSIONS if perms.get(key))
    await call.message.edit_text(
        f"{E_CROWN} <b>{target_name}</b> promoted with: {granted}",
        parse_mode="HTML",
    )
    await call.answer("Promoted!")


@router.message(Command("demote"))
async def handle_demote_cmd(message: Message, session: Optional[AsyncSession] = None):
    if not session or message.chat.id >= 0:
        return
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await reply_with_ttl(
            message, f"{E_WARN} Reply to a user's message to demote them.", ttl_type=TTLType.MODERATION
        )
        return
    target = message.reply_to_message.from_user
    try:
        await message.bot.promote_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            is_anonymous=False,
            **{key: False for key, _ in PROMOTE_PERMISSIONS},
        )
        await reply_with_ttl(message, f"{E_CHECK} <b>{target.full_name}</b> has been demoted.", ttl_type=TTLType.MODERATION)
    except TelegramBadRequest as e:
        await reply_with_ttl(message, f"{E_WARN} Failed to demote: {e}", ttl_type=TTLType.MODERATION)
