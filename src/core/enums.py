from enum import Enum


class ActionType(str, Enum):
    BAN = "ban"
    TEMPBAN = "tempban"
    MUTE = "mute"
    TEMPMUTE = "tempmute"
    KICK = "kick"
    WARN = "warn"
    UNBAN = "unban"
    UNMUTE = "unmute"
    RESET_WARNS = "reset_warns"
    PURGE = "purge"
    ANTISPAM_TRIGGER = "antispam_trigger"
    CAPTCHA_FAIL = "captcha_fail"
    CAPTCHA_PASS = "captcha_pass"
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    BOT_START = "bot_start"
    RULES_UPDATE = "rules_update"
    SETTINGS_CHANGE = "settings_change"
    GAME_PLAY = "game_play"
    COMMAND_USE = "command_use"
    KARMA_AWARD = "karma_award"
    DAILY_CLAIM = "daily_claim"
    BLOCKLIST_TRIGGER = "blocklist_trigger"
    TOS_TRIGGER = "tos_trigger"
    LANGUAGE_VIOLATION = "language_violation"
    ZOMBIE_PURGE = "zombie_purge"
    PANIC_MODE = "panic_mode"


class CaptchaMode(str, Enum):
    BUTTON = "button"
    MATH = "math"
    OFF = "off"


class WarnAction(str, Enum):
    MUTE = "mute"
    KICK = "kick"
    BAN = "ban"


class TTLType(str, Enum):
    MODERATION = "mod"
    FUN = "fun"
    RULES = "rules"
    WARN = "warn"
    GENERAL = "general"
    NONE = "none"


class GameType(str, Enum):
    DICE = "dice"
    DARTS = "darts"
    BASKETBALL = "basketball"
    FOOTBALL = "football"
    SLOTS = "slots"
    BOWLING = "bowling"
    ROULETTE = "roulette"
