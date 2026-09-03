from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from src.models.group import Group
from src.models.ttl import TTLSettings


def get_settings_main_menu(group: Group, ttl: TTLSettings) -> InlineKeyboardMarkup:
    """Main Settings Dashboard Menu with Bot API 9.4 styles and custom emoji icons."""
    antiflood_style = "success" if group.antispam_enabled else "danger"
    antiflood_emoji = "5237699328843200968" if group.antispam_enabled else "5260293700088511294"
    antiflood_text = "Flood: ON" if group.antispam_enabled else "Flood: OFF"

    antilink_style = "success" if group.antilink_enabled else "danger"
    antilink_emoji = "5237699328843200968" if group.antilink_enabled else "5260293700088511294"
    antilink_text = "Link: ON" if group.antilink_enabled else "Link: OFF"

    antifwd_style = "success" if group.antiforward_enabled else "danger"
    antifwd_emoji = "5237699328843200968" if group.antiforward_enabled else "5260293700088511294"
    antifwd_text = "Fwd: ON" if group.antiforward_enabled else "Fwd: OFF"

    welcome_style = "success" if group.welcome_enabled else "danger"
    welcome_emoji = "5237699328843200968" if group.welcome_enabled else "5260293700088511294"
    welcome_text = "Welcome: ON" if group.welcome_enabled else "Welcome: OFF"

    trigger_text = "Trigger: ON" if (ttl and ttl.delete_command_trigger) else "Trigger: OFF"
    trigger_style = "success" if (ttl and ttl.delete_command_trigger) else "danger"
    trigger_emoji = (
        "5237699328843200968" if (ttl and ttl.delete_command_trigger) else "5260293700088511294"
    )
    if group.captcha_mode == "button":
        captcha_style = "success"
        captcha_text = "Captcha: BUTTON"
        captcha_emoji = "5237699328843200968"
    elif group.captcha_mode == "math":
        captcha_style = "primary"
        captcha_text = "Captcha: MATH"
        captcha_emoji = "5237889595894414384"
    else:
        captcha_style = "danger"
        captcha_text = "Captcha: OFF"
        captcha_emoji = "5260293700088511294"

    keyboard = [
        [
            InlineKeyboardButton(
                text=antiflood_text,
                callback_data=f"cfg:toggle:flood:{group.chat_id}",
                style=antiflood_style,
                icon_custom_emoji_id=antiflood_emoji,
            ),
            InlineKeyboardButton(
                text=antilink_text,
                callback_data=f"cfg:toggle:link:{group.chat_id}",
                style=antilink_style,
                icon_custom_emoji_id=antilink_emoji,
            ),
        ],
        [
            InlineKeyboardButton(
                text=antifwd_text,
                callback_data=f"cfg:toggle:fwd:{group.chat_id}",
                style=antifwd_style,
                icon_custom_emoji_id=antifwd_emoji,
            ),
            InlineKeyboardButton(
                text=welcome_text,
                callback_data=f"cfg:toggle:welcome:{group.chat_id}",
                style=welcome_style,
                icon_custom_emoji_id=welcome_emoji,
            ),
        ],
        [
            InlineKeyboardButton(
                text=captcha_text,
                callback_data=f"cfg:cycle:captcha:{group.chat_id}",
                style=captcha_style,
                icon_custom_emoji_id=captcha_emoji,
            ),
            InlineKeyboardButton(
                text=trigger_text,
                callback_data=f"cfg:toggle:trigger:{group.chat_id}",
                style=trigger_style,
                icon_custom_emoji_id=trigger_emoji,
            ),
        ],
        [
            InlineKeyboardButton(
                text="Configure TTL Timers",
                callback_data=f"cfg:menu:ttl:{group.chat_id}",
                style="primary",
                icon_custom_emoji_id="5386367538735104399",
            ),
            InlineKeyboardButton(
                text="Warn Escalation",
                callback_data=f"cfg:menu:warn:{group.chat_id}",
                style="danger",
                icon_custom_emoji_id="5447644880824181073",
            ),
        ],
        [
            InlineKeyboardButton(
                text="Close Dashboard",
                callback_data=f"cfg:close:{group.chat_id}",
                style="danger",
                icon_custom_emoji_id="5260293700088511294",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_ttl_menu(group: Group, ttl: TTLSettings) -> InlineKeyboardMarkup:
    """TTL Timers Configuration Sub-menu."""
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"Mod: {ttl.mod_ttl}s",
                callback_data=f"cfg:ttl:mod:{group.chat_id}",
                style="primary",
                icon_custom_emoji_id="5251203410396458957",
            ),
            InlineKeyboardButton(
                text="+5s",
                callback_data=f"cfg:ttl_adjust:mod:+5:{group.chat_id}",
                style="success",
                icon_custom_emoji_id="5237699328843200968",
            ),
            InlineKeyboardButton(
                text="-5s",
                callback_data=f"cfg:ttl_adjust:mod:-5:{group.chat_id}",
                style="danger",
                icon_custom_emoji_id="5260293700088511294",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Fun: {ttl.fun_ttl}s",
                callback_data=f"cfg:ttl:fun:{group.chat_id}",
                style="primary",
                icon_custom_emoji_id="5361741454685256344",
            ),
            InlineKeyboardButton(
                text="+5s",
                callback_data=f"cfg:ttl_adjust:fun:+5:{group.chat_id}",
                style="success",
                icon_custom_emoji_id="5237699328843200968",
            ),
            InlineKeyboardButton(
                text="-5s",
                callback_data=f"cfg:ttl_adjust:fun:-5:{group.chat_id}",
                style="danger",
                icon_custom_emoji_id="5260293700088511294",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Rules: {ttl.rules_ttl}s",
                callback_data=f"cfg:ttl:rules:{group.chat_id}",
                style="primary",
                icon_custom_emoji_id="5434144690511290129",
            ),
            InlineKeyboardButton(
                text="+5s",
                callback_data=f"cfg:ttl_adjust:rules:+5:{group.chat_id}",
                style="success",
                icon_custom_emoji_id="5237699328843200968",
            ),
            InlineKeyboardButton(
                text="-5s",
                callback_data=f"cfg:ttl_adjust:rules:-5:{group.chat_id}",
                style="danger",
                icon_custom_emoji_id="5260293700088511294",
            ),
        ],
        [
            InlineKeyboardButton(
                text="Back to Main Menu",
                callback_data=f"cfg:menu:main:{group.chat_id}",
                style="primary",
                icon_custom_emoji_id="5434144690511290129",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_warn_settings_menu(group: Group) -> InlineKeyboardMarkup:
    """Warn Escalation Sub-menu."""
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"Max: {group.max_warns}",
                callback_data="noop",
                style="primary",
                icon_custom_emoji_id="5447644880824181073",
            ),
            InlineKeyboardButton(
                text="+1",
                callback_data=f"cfg:warn_adjust:max:+1:{group.chat_id}",
                style="success",
                icon_custom_emoji_id="5237699328843200968",
            ),
            InlineKeyboardButton(
                text="-1",
                callback_data=f"cfg:warn_adjust:max:-1:{group.chat_id}",
                style="danger",
                icon_custom_emoji_id="5260293700088511294",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Action: {group.warn_action.upper()}",
                callback_data=f"cfg:cycle:warn_action:{group.chat_id}",
                style="danger",
                icon_custom_emoji_id="5240241223632954241",
            )
        ],
        [
            InlineKeyboardButton(
                text="Back to Main Menu",
                callback_data=f"cfg:menu:main:{group.chat_id}",
                style="primary",
                icon_custom_emoji_id="5434144690511290129",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
