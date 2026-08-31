from typing import Set
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from src.services.locks_service import ALL_LOCK_TYPES

# Verified Custom Animated Emoji IDs
EMOJI_LOCK = "5296369303661067030"       # 🔒
EMOJI_CHECK = "5237699328843200968"      # ✅
EMOJI_TRASH = "5445267414562389170"      # 🗑
EMOJI_BAN = "5240241223632954241"        # 🚫
EMOJI_RELOAD = "5375338737028841420"     # 🔄
EMOJI_CROSS = "5210952531676504517"      # ❌
EMOJI_GLOBE = "5447410659077661506"      # 🌐
EMOJI_ARROW = "5416117059207572332"      # ➡️
EMOJI_GAME = "5361741454685256344"       # 🎮
EMOJI_MEMBERS = "5386435923204382258"    # 👥
EMOJI_MEDIA = "5434144690511290129"      # 📰
EMOJI_NOTE = "5373251851074415873"       # 📝
EMOJI_LIGHTNING = "5456140674028019486"  # ⚡

LOCK_BUTTON_NAMES = {
    "links": "Links",
    "forwards": "Forwards",
    "stickers": "Stickers",
    "gifs": "Gifs",
    "voice": "Voice",
    "video": "Video",
    "photos": "Photos",
    "documents": "Documents",
    "polls": "Polls",
    "contacts": "Contacts",
    "location": "Location",
    "games": "Games",
}

LOCK_CUSTOM_ICONS = {
    "links": EMOJI_GLOBE,
    "forwards": EMOJI_ARROW,
    "stickers": EMOJI_MEDIA,
    "gifs": EMOJI_MEDIA,
    "voice": EMOJI_NOTE,
    "video": EMOJI_MEDIA,
    "photos": EMOJI_MEDIA,
    "documents": EMOJI_NOTE,
    "polls": EMOJI_LIGHTNING,
    "contacts": EMOJI_MEMBERS,
    "location": EMOJI_GLOBE,
    "games": EMOJI_GAME,
}


def get_locks_keyboard(locked_set: Set[str], cleanservice_enabled: bool, antichannel_enabled: bool) -> InlineKeyboardMarkup:
    """
    Builds a 2-column interactive grid keyboard for toggling group content locks
    featuring Telegram Premium animated custom emoji icons on every button.
    """
    buttons = []
    current_row = []

    for l_type in ALL_LOCK_TYPES:
        is_locked = l_type in locked_set
        icon_emoji = EMOJI_LOCK if is_locked else EMOJI_CHECK
        status_text = "Locked" if is_locked else "Unlocked"
        name = LOCK_BUTTON_NAMES.get(l_type, l_type.capitalize())
        label = f"{name}: {status_text}"
        callback = f"lock_toggle:{l_type}"

        current_row.append(
            InlineKeyboardButton(
                text=label,
                callback_data=callback,
                icon_custom_emoji_id=icon_emoji,
            )
        )
        if len(current_row) == 2:
            buttons.append(current_row)
            current_row = []

    if current_row:
        buttons.append(current_row)

    # Special module toggles
    cs_status = "Enabled" if cleanservice_enabled else "Disabled"
    ac_status = "Enabled" if antichannel_enabled else "Disabled"

    buttons.append([
        InlineKeyboardButton(
            text=f"CleanService: {cs_status}",
            callback_data="lock_toggle:cleanservice",
            icon_custom_emoji_id=EMOJI_TRASH,
        ),
        InlineKeyboardButton(
            text=f"AntiChannel: {ac_status}",
            callback_data="lock_toggle:antichannel",
            icon_custom_emoji_id=EMOJI_BAN,
        ),
    ])

    # Quick Lock / Unlock All row
    buttons.append([
        InlineKeyboardButton(
            text="Lock All",
            callback_data="lock_toggle:lock_all",
            icon_custom_emoji_id=EMOJI_LOCK,
        ),
        InlineKeyboardButton(
            text="Unlock All",
            callback_data="lock_toggle:unlock_all",
            icon_custom_emoji_id=EMOJI_CHECK,
        ),
    ])

    buttons.append([
        InlineKeyboardButton(
            text="Refresh",
            callback_data="lock_toggle:refresh",
            icon_custom_emoji_id=EMOJI_RELOAD,
        ),
        InlineKeyboardButton(
            text="Close",
            callback_data="lock_toggle:close",
            icon_custom_emoji_id=EMOJI_CROSS,
        ),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
