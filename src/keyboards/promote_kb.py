from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

PROMOTE_PERMISSIONS = [
    ("can_manage_chat", "🛠 Manage Chat"),
    ("can_delete_messages", "🗑 Delete Messages"),
    ("can_manage_video_chats", "📹 Manage Video Chats"),
    ("can_restrict_members", "🚫 Restrict Members"),
    ("can_promote_members", "⭐ Promote Members"),
    ("can_change_info", "ℹ️ Change Info"),
    ("can_invite_users", "🔗 Invite Users"),
    ("can_pin_messages", "📌 Pin Messages"),
    ("can_manage_topics", "🧵 Manage Topics"),
]

PROMOTE_PRESETS = {
    "full": {key: True for key, _ in PROMOTE_PERMISSIONS},
    "mod": {
        "can_manage_chat": False,
        "can_delete_messages": True,
        "can_manage_video_chats": False,
        "can_restrict_members": True,
        "can_promote_members": False,
        "can_change_info": False,
        "can_invite_users": True,
        "can_pin_messages": True,
        "can_manage_topics": False,
    },
    "none": {key: False for key, _ in PROMOTE_PERMISSIONS},
}


def build_promote_keyboard(perms: dict) -> InlineKeyboardMarkup:
    rows = []
    for key, label in PROMOTE_PERMISSIONS:
        icon = "✅" if perms.get(key) else "❌"
        rows.append([InlineKeyboardButton(text=f"{icon} {label}", callback_data=f"promote_perm:{key}")])
    rows.append(
        [
            InlineKeyboardButton(text="👑 Full Admin", callback_data="promote_preset:full"),
            InlineKeyboardButton(text="🛡 Mod Preset", callback_data="promote_preset:mod"),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(text="✅ Confirm", callback_data="promote_confirm"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="promote_cancel"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
