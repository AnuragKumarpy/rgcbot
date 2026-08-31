from typing import List, Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from src.models.group import Group


def get_dm_start_keyboard(
    bot_username: str,
    is_super_admin: bool = False,
) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="Add RGCBot to Group",
                url=f"https://t.me/{bot_username}?startgroup=true&admin=change_info+delete_messages+restrict_members+invite_users+pin_messages",
                style="success",
                icon_custom_emoji_id="5427168083074628963",
            )
        ],
        [
            InlineKeyboardButton(
                text="My Admin Groups",
                callback_data="dm:my_groups",
                style="primary",
                icon_custom_emoji_id="5251203410396458957",
            ),
            InlineKeyboardButton(
                text="Command Guide",
                callback_data="dm:help",
                style="primary",
                icon_custom_emoji_id="5434144690511290129",
            ),
        ],
        [
            InlineKeyboardButton(
                text="Group Settings",
                callback_data="dm:settings_list",
                style="primary",
                icon_custom_emoji_id="5237889595894414384",
            ),
            InlineKeyboardButton(
                text="My Profile",
                callback_data="dm:profile",
                style="primary",
                icon_custom_emoji_id="5237699328843200968",
            ),
        ],
    ]

    if is_super_admin:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="Super Admin Panel",
                    callback_data="dm:adminpanel",
                    style="danger",
                    icon_custom_emoji_id="5427168083074628963",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_group_selection_keyboard(
    groups: List[Group],
    action_prefix: str = "dm_cfg:open",
) -> InlineKeyboardMarkup:
    buttons = []
    for g in groups:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{g.title[:28]}",
                    callback_data=f"{action_prefix}:{g.chat_id}",
                    style="primary",
                    icon_custom_emoji_id="5251203410396458957",
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text="Back to Main Menu",
                callback_data="dm:menu",
                style="primary",
                icon_custom_emoji_id="5434144690511290129",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_group_settings_redirect_keyboard(
    bot_username: str,
    chat_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open Settings in Chat",
                    callback_data=f"cfg:menu:main:{chat_id}",
                    style="primary",
                    icon_custom_emoji_id="5237889595894414384",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Open in Private DM",
                    url=f"https://t.me/{bot_username}?start=settings_{chat_id}",
                    style="success",
                    icon_custom_emoji_id="5427168083074628963",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Close",
                    callback_data=f"cfg:close:{chat_id}",
                    style="danger",
                    icon_custom_emoji_id="5260293700088511294",
                )
            ],
        ]
    )
