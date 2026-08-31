from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_help_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛡️ Moderation & Defense",
                    callback_data="help:defense",
                    style="primary",
                    icon_custom_emoji_id="5251203410396458957",
                ),
                InlineKeyboardButton(
                    text="⚡ Mass Tagging & Reports",
                    callback_data="help:tagging",
                    style="primary",
                    icon_custom_emoji_id="5456140674028019486",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🌐 Security Federations",
                    callback_data="help:federation",
                    style="primary",
                    icon_custom_emoji_id="5447410659077661506",
                ),
                InlineKeyboardButton(
                    text="🔒 Content Locks",
                    callback_data="help:locks",
                    style="primary",
                    icon_custom_emoji_id="5296369303661067030",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💎 Reputation & Economy",
                    callback_data="help:reputation",
                    style="primary",
                    icon_custom_emoji_id="5427168083074628963",
                ),
                InlineKeyboardButton(
                    text="🎲 Games & Fun Radar",
                    callback_data="help:games",
                    style="primary",
                    icon_custom_emoji_id="5361741454685256344",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ Settings & Transfer",
                    callback_data="help:settings",
                    style="primary",
                    icon_custom_emoji_id="5341715473882955310",
                ),
                InlineKeyboardButton(
                    text="❓ FAQ & Troubleshooting",
                    callback_data="help:faq",
                    style="primary",
                    icon_custom_emoji_id="5312536423851630001",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📖 Complete User Manual",
                    callback_data="help:manual",
                    style="success",
                    icon_custom_emoji_id="5373251851074415873",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Back to Main Menu",
                    callback_data="dm:menu",
                    style="danger",
                    icon_custom_emoji_id="5434144690511290129",
                ),
            ],
        ]
    )


def get_help_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 Help Categories",
                    callback_data="dm:help",
                    style="primary",
                    icon_custom_emoji_id="5434144690511290129",
                ),
                InlineKeyboardButton(
                    text="🏠 Main Menu",
                    callback_data="dm:menu",
                    style="primary",
                    icon_custom_emoji_id="5237889595894414384",
                ),
            ]
        ]
    )
