"""
Premium Animated Emojis Module
Provides formatted custom animated emoji tags (<tg-emoji>) with high-fidelity fallback
and auto-replacement for complete animated emoji coverage.
Sourced 100% from clean, official Telegram Packs (Topics, NewsEmoji, BeemEmojiPack).
"""

# Custom Animated Emoji Tags from Verified Clean Active Packs
E_CROWN = '<tg-emoji emoji-id="5217822164362739968">👑</tg-emoji>'
E_DIAMOND = '<tg-emoji emoji-id="5427168083074628963">💎</tg-emoji>'
E_BRAIN = '<tg-emoji emoji-id="5237889595894414384">🧠</tg-emoji>'
E_LOCK = '<tg-emoji emoji-id="5296369303661067030">🔒</tg-emoji>'
E_BELL = '<tg-emoji emoji-id="5458603043203327669">🔔</tg-emoji>'
E_SPARKLES = '<tg-emoji emoji-id="5325547803936572038">✨</tg-emoji>'
E_STAR = '<tg-emoji emoji-id="5438496463044752972">⭐️</tg-emoji>'
E_NEWS = '<tg-emoji emoji-id="5434144690511290129">📰</tg-emoji>'
E_LIGHTNING = '<tg-emoji emoji-id="5456140674028019486">⚡️</tg-emoji>'
E_FIRE = '<tg-emoji emoji-id="5033184522489825051">🔥</tg-emoji>'
E_HEART = '<tg-emoji emoji-id="5312138559556164615">❤️</tg-emoji>'
E_PINK_HEART = '<tg-emoji emoji-id="5310029292527164639">💖</tg-emoji>'
E_TOP = '<tg-emoji emoji-id="5418085807791545980">🔝</tg-emoji>'
E_RADAR = '<tg-emoji emoji-id="5210956306952758910">👀</tg-emoji>'
E_IDEA = '<tg-emoji emoji-id="5312536423851630001">💡</tg-emoji>'
E_STOP = '<tg-emoji emoji-id="5260293700088511294">⛔️</tg-emoji>'
E_BAN = '<tg-emoji emoji-id="5240241223632954241">🚫</tg-emoji>'
E_WARN = '<tg-emoji emoji-id="5440660757194744323">‼️</tg-emoji>'
E_ALERT = '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji>'
E_SIREN = '<tg-emoji emoji-id="5395695537687123235">🚨</tg-emoji>'
E_SHIELD = '<tg-emoji emoji-id="5251203410396458957">🛡️</tg-emoji>'
E_SEARCH = '<tg-emoji emoji-id="5231012545799666522">🔍</tg-emoji>'
E_MEGAPHONE = '<tg-emoji emoji-id="5424818078833715060">📣</tg-emoji>'
E_NOTE = '<tg-emoji emoji-id="5373251851074415873">📝</tg-emoji>'
E_COOL = '<tg-emoji emoji-id="5420216386448270341">🆒</tg-emoji>'
E_ROBOT = '<tg-emoji emoji-id="5309832892262654231">🤖</tg-emoji>'
E_GAME = '<tg-emoji emoji-id="5361741454685256344">🎮</tg-emoji>'
E_HOURGLASS = '<tg-emoji emoji-id="5386367538735104399">⏳</tg-emoji>'
E_COINS = '<tg-emoji emoji-id="5350452584119279096">💰</tg-emoji>'
E_TROPHY = '<tg-emoji emoji-id="5312315739842026755">🏆</tg-emoji>'
E_GLOBE = '<tg-emoji emoji-id="5447410659077661506">🌐</tg-emoji>'
E_MEMBERS = '<tg-emoji emoji-id="5386435923204382258">👥</tg-emoji>'
E_CHECK = '<tg-emoji emoji-id="5237699328843200968">✅</tg-emoji>'
E_CROSS = '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji>'
E_RELOAD = '<tg-emoji emoji-id="5375338737028841420">🔄</tg-emoji>'
E_CALENDAR = '<tg-emoji emoji-id="5413879192267805083">📅</tg-emoji>'
E_ONLINE = '<tg-emoji emoji-id="5416081784641168838">🟢</tg-emoji>'
E_RED = '<tg-emoji emoji-id="5411225014148014586">🔴</tg-emoji>'
E_GEAR = '<tg-emoji emoji-id="5341715473882955310">⚙️</tg-emoji>'
E_TRASH = '<tg-emoji emoji-id="5445267414562389170">🗑</tg-emoji>'
E_MICROSCOPE = '<tg-emoji emoji-id="5377580546748588396">🔬</tg-emoji>'
E_PLUS = '<tg-emoji emoji-id="5397916757333654639">➕</tg-emoji>'
E_ARROW = '<tg-emoji emoji-id="5416117059207572332">➡️</tg-emoji>'
E_NSFW = '<tg-emoji emoji-id="5420331611830886484">🔞</tg-emoji>'
E_ROCKET = '<tg-emoji emoji-id="5188481279963715781">🚀</tg-emoji>'


# Aliases
E_EDIT = E_NOTE
E_CLOCK = E_HOURGLASS
E_MEDIA = E_NEWS

# Direct mapping dictionary for auto-conversion
EMOJI_MAP = {
    "👑": E_CROWN,
    "💎": E_DIAMOND,
    "🧠": E_BRAIN,
    "🔒": E_LOCK,
    "🔔": E_BELL,
    "✨": E_SPARKLES,
    "⭐️": E_STAR,
    "⭐": E_STAR,
    "📰": E_NEWS,
    "⚡️": E_LIGHTNING,
    "⚡": E_LIGHTNING,
    "🔥": E_FIRE,
    "❤️": E_HEART,
    "❤": E_HEART,
    "💖": E_PINK_HEART,
    "💘": E_PINK_HEART,
    "💕": E_PINK_HEART,
    "🔝": E_TOP,
    "👀": E_RADAR,
    "💡": E_IDEA,
    "⛔️": E_STOP,
    "⛔": E_STOP,
    "🚫": E_BAN,
    "‼️": E_WARN,
    "⚠️": E_ALERT,
    "🚨": E_SIREN,
    "🛡️": E_SHIELD,
    "🛡": E_SHIELD,
    "🔍": E_SEARCH,
    "🔎": E_SEARCH,
    "📣": E_MEGAPHONE,
    "📢": E_MEGAPHONE,
    "📝": E_NOTE,
    "✍️": E_NOTE,
    "🆒": E_COOL,
    "🤖": E_ROBOT,
    "🎮": E_GAME,
    "⏳": E_HOURGLASS,
    "⌛": E_HOURGLASS,
    "⏱️": E_HOURGLASS,
    "⏱": E_HOURGLASS,
    "💰": E_COINS,
    "💵": E_COINS,
    "💸": E_COINS,
    "🏆": E_TROPHY,
    "🏅": E_TROPHY,
    "🌐": E_GLOBE,
    "👥": E_MEMBERS,
    "👨‍👩‍👧‍👦": E_MEMBERS,
    "✅": E_CHECK,
    "✔️": E_CHECK,
    "❌": E_CROSS,
    "🔄": E_RELOAD,
    "📅": E_CALENDAR,
    "📆": E_CALENDAR,
    "🗓": E_CALENDAR,
    "🟢": E_ONLINE,
    "🔴": E_RED,
    "⚙️": E_GEAR,
    "⚙": E_GEAR,
    "🗑️": E_TRASH,
    "🗑": E_TRASH,
    "🔬": E_MICROSCOPE,
    "➕": E_PLUS,
    "➡️": E_ARROW,
    "🔞": E_NSFW,
    "🚀": E_ROCKET,
}


def animate_text(text: str) -> str:
    """Replaces standard Unicode emojis in HTML formatted strings with animated custom emoji tags."""
    if not text:
        return text
    # Replace in order of key length to avoid partial collisions
    sorted_emojis = sorted(EMOJI_MAP.keys(), key=len, reverse=True)
    result = text
    for emoji_char in sorted_emojis:
        if emoji_char in result:
            result = result.replace(emoji_char, EMOJI_MAP[emoji_char])
    return result
