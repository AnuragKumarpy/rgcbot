from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeDefault, BotCommandScopeChat,
)
from loguru import logger


async def setup_bot_metadata(bot: Bot):
    """
    Configures Bot description, short description, and command menus for all scopes.
    """
    try:
        # 1. Set Bot Name
        await bot.set_my_name(name="RGCBot")
        logger.info("Bot name set to 'RGCBot'")
    except Exception as e:
        logger.warning(f"Could not set bot name: {e}")

    try:
        # 2. Set Bot Short Description (shown on profile & share)
        await bot.set_my_short_description(
            short_description="🛡️ Elite Supergroup Defense & Security Federation Bot. Powered by ELITE Bot @EliteBotsTelegram."
        )
        logger.info("Bot short description updated.")
    except Exception as e:
        logger.warning(f"Could not set short description: {e}")

    try:
        # 3. Set Bot Full Description (shown on empty chat before /start, max 512 chars)
        description = (
            "👑 Welcome to RGCBot — The Elite Telegram Supergroup Management & Defense System.\n\n"
            "✦ Features:\n"
            "• 🛡️ Advanced Defense (Bans, Mutes, Warns, Panic Anti-Raid & Zombies)\n"
            "• 🌐 Security Federations (Unified cross-group banlists)\n"
            "• 🔒 Content Locks (Granular media & message filtering)\n"
            "• ⚡ Zero-Risk Secret Tagging (@all, @allactive, @rall)\n"
            "• ⚙️ Instant Settings Transfer (Export/Import setup code)\n"
            "• 💎 Reputation & Economy (+rep karma, coins, profile)\n\n"
            "⚡ Powered by ELITE Bot @EliteBotsTelegram"
        )
        await bot.set_my_description(description=description)
        logger.info("Bot full description updated.")
    except Exception as e:
        logger.warning(f"Could not set full description: {e}")

    try:
        # 4. Default Scope Commands (Private / Generic)
        default_commands = [
            BotCommand(command="start", description="Start bot & overview dashboard"),
            BotCommand(command="help", description="Categorized command manual"),
            BotCommand(command="faq", description="Frequently Asked Questions"),
            BotCommand(command="manual", description="Complete User & Admin Guide"),
            BotCommand(command="profile", description="Member profile & reputation"),
            BotCommand(command="daily", description="Claim daily coins & streak"),
            BotCommand(command="karma", description="Reputation stats & rank"),
            BotCommand(command="topkarma", description="Reputation leaderboard"),
            BotCommand(command="stats", description="Group activity history cards"),
            BotCommand(command="ustats", description="Personal messaging & game stats"),
            BotCommand(command="topstats", description="Messaging & game leaderboards"),
            BotCommand(command="appeal", description="Request review for active bans"),
            BotCommand(command="history", description="Inspect member moderation history"),
            BotCommand(command="afk", description="Set AFK status [reason]"),
            BotCommand(command="rules", description="View group rules"),
            BotCommand(command="ping", description="Show bot latency and status"),
        ]
        await bot.set_my_commands(
            commands=default_commands,
            scope=BotCommandScopeDefault(),
        )
        logger.info("Default bot commands registered.")

        # 5. Group Chats Scope Commands (For all group members)
        group_commands = [
            BotCommand(command="help", description="Interactive command guide"),
            BotCommand(command="faq", description="Frequently Asked Questions"),
            BotCommand(command="manual", description="User manual & guide"),
            BotCommand(command="profile", description="View profile card & karma"),
            BotCommand(command="daily", description="Claim daily bonus coins"),
            BotCommand(command="karma", description="Check reputation points"),
            BotCommand(command="topkarma", description="Chat reputation leaderboard"),
            BotCommand(command="stats", description="Generate chat activity infographic"),
            BotCommand(command="ustats", description="View personal messaging & game stats"),
            BotCommand(command="topstats", description="Top chat, message & game scorers"),
            BotCommand(command="history", description="Inspect member moderation history"),
            BotCommand(command="appeal", description="Request review for restrictions"),
            BotCommand(command="q", description="Generate graphic quote from message"),
            BotCommand(command="quote", description="Generate graphic quote from message"),
            BotCommand(command="qrand", description="Generate a random quote card"),
            BotCommand(command="ship", description="Member matchmaking radar"),
            BotCommand(command="roulette", description="Russian roulette mini-game"),
            BotCommand(command="duel", description="Challenge member to dice duel"),
            BotCommand(command="dice", description="Roll animated dice"),
            BotCommand(command="slots", description="Spin the slot machine"),
            BotCommand(command="darts", description="Throw darts"),
            BotCommand(command="basketball", description="Play basketball"),
            BotCommand(command="football", description="Play football"),
            BotCommand(command="bowling", description="Play bowling"),
            BotCommand(command="afk", description="Set AFK status [reason]"),
            BotCommand(command="rules", description="View group rules"),
            BotCommand(command="report", description="Report offensive message to admins"),
        ]
        await bot.set_my_commands(
            commands=group_commands,
            scope=BotCommandScopeAllGroupChats(),
        )
        logger.info("Group chat bot commands registered.")

        # 6. Admin Scope Commands (Exclusive to Group Administrators)
        admin_commands = [
            BotCommand(command="settings", description="Defense, TTL & CAPTCHA Dashboard"),
            BotCommand(command="locks", description="Visual Content Locks Manager"),
            BotCommand(command="lock", description="Lock a content type"),
            BotCommand(command="unlock", description="Unlock a content type"),
            BotCommand(command="cleanservice", description="Toggle service message cleanup"),
            BotCommand(command="antichannel", description="Toggle anti-channel protection"),
            BotCommand(command="exportsettings", description="Export configuration code"),
            BotCommand(command="importsettings", description="Clone settings from code"),
            BotCommand(command="blocklist", description="Manage prohibited terms"),
            BotCommand(command="tos", description="Toggle TOS shield"),
            BotCommand(command="tagall", description="Mention all members (zero-risk emojis)"),
            BotCommand(command="tagactive", description="Mention active chatters (~15-45s)"),
            BotCommand(command="tagstop", description="Cancel active tagging loop"),
            BotCommand(command="fcreate", description="Create new Security Federation"),
            BotCommand(command="fjoin", description="Link group to Federation"),
            BotCommand(command="fleave", description="Unlink group from Federation"),
            BotCommand(command="finfo", description="View Federation details & ban stats"),
            BotCommand(command="fban", description="Federation-ban user across all chats"),
            BotCommand(command="funban", description="Remove Federation ban"),
            BotCommand(command="fpromote", description="Appoint Federation Admin"),
            BotCommand(command="fdemote", description="Remove Federation Admin"),
            BotCommand(command="ban", description="Ban member (reply, @user, or ID)"),
            BotCommand(command="tban", description="Temp-ban member (e.g. /tban 1d)"),
            BotCommand(command="unban", description="Unban member"),
            BotCommand(command="mute", description="Mute member"),
            BotCommand(command="tmute", description="Temp-mute member (e.g. /tmute 30m)"),
            BotCommand(command="unmute", description="Unmute member"),
            BotCommand(command="warn", description="Warn member with auto-escalation"),
            BotCommand(command="warns", description="Check member active warnings"),
            BotCommand(command="resetwarns", description="Reset member warnings to 0"),
            BotCommand(command="history", description="Inspect member moderation history"),
            BotCommand(command="purge", description="Bulk delete messages"),
            BotCommand(command="del", description="Delete replied message"),
            BotCommand(command="pin", description="Pin replied message"),
            BotCommand(command="unpin", description="Unpin message"),
            BotCommand(command="unpinall", description="Unpin all messages"),
            BotCommand(command="appeal", description="Review ban appeal requests"),
            BotCommand(command="panic", description="Anti-Raid Lockdown (/panic on/off)"),
            BotCommand(command="zombies", description="Scan & purge deleted accounts"),
            BotCommand(command="syncmembers", description="Sync group members"),
            BotCommand(command="blocklist", description="Manage custom prohibited terms"),
            BotCommand(command="setwelcome", description="Configure welcome message"),
            BotCommand(command="welcome", description="View welcome message"),
            BotCommand(command="setrules", description="Configure group rules"),
            BotCommand(command="rules", description="View group rules"),
            BotCommand(command="setnote", description="Add internal admin note"),
            BotCommand(command="notes", description="View internal admin notes"),
            BotCommand(command="delnotes", description="Delete internal admin notes"),
            BotCommand(command="filter", description="Add keyword auto-reply trigger"),
            BotCommand(command="filters", description="List active group filters"),
            BotCommand(command="helpadmin", description="Admin control manual"),

        ]
        await bot.set_my_commands(
            commands=admin_commands,
            scope=BotCommandScopeAllChatAdministrators(),
        )
        logger.info("Administrator bot commands registered.")

        # 7. Super Admin Commands (Exclusive to configured Super Admins)
        super_commands = admin_commands + [
            BotCommand(command="adminpanel", description="👑 Super Admin Master Dashboard"),
            BotCommand(command="broadcast", description="📢 Global Broadcast Engine"),
            BotCommand(command="gcast", description="📢 Fast Group Broadcast"),
        ]
        for sa_id in settings.bot_super_admins:
            try:
                await bot.set_my_commands(
                    commands=super_commands,
                    scope=BotCommandScopeChat(chat_id=sa_id),
                )
            except Exception as e:
                logger.warning(f"Could not set superadmin scope for {sa_id}: {e}")


    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")


class BotMetadataService:
    setup_bot_metadata = staticmethod(setup_bot_metadata)
