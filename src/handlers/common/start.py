from datetime import datetime, timedelta
from typing import Optional

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.core.enums import ActionType, TTLType
from src.keyboards.dm_kb import (
    get_dm_start_keyboard,
    get_group_selection_keyboard,
)
from src.keyboards.help_kb import get_help_back_keyboard, get_help_main_keyboard
from src.keyboards.settings_kb import get_settings_main_menu
from src.middlewares.ttl import reply_with_ttl
from src.models.group import Group
from src.models.ttl import TTLSettings
from src.models.user import User
from src.services.audit_service import AuditService
from src.utils.emojis import (
    E_BELL,
    E_BRAIN,
    E_CHECK,
    E_COOL,
    E_CROWN,
    E_DIAMOND,
    E_FIRE,
    E_HEART,
    E_IDEA,
    E_LIGHTNING,
    E_LOCK,
    E_NEWS,
    E_RADAR,
    E_ROCKET,
    E_SHIELD,
    E_SPARKLES,
    E_STAR,
    E_TOP,
    E_WARN,
    animate_text,
)
from src.utils.permissions import is_super_admin
from src.utils.text_formatter import (
    escape_html,
    format_card,
    get_karma_tier,
    get_user_mention,
    mention_html,
)

router = Router(name="common_start")

POWERED_BY_FOOTER = (
    '⚡ <b>Powered by ELITE Bot</b> <a href="https://t.me/EliteBotsTelegram">@EliteBotsTelegram</a>'
)


async def get_network_metrics(session: AsyncSession):
    res_mau = await session.execute(
        select(func.count(User.user_id)).where(
            User.updated_at >= datetime.utcnow() - timedelta(days=30)
        )
    )
    mau = res_mau.scalar_one()

    res_groups = await session.execute(
        select(func.count(Group.chat_id)).where(Group.is_active == True)
    )
    active_groups = res_groups.scalar_one()

    res_users = await session.execute(select(func.count(User.user_id)))
    total_users = res_users.scalar_one()

    return max(mau, 1), active_groups, total_users


def format_rules_text(group_title: str, rules_content: str, include_footer: bool = False) -> str:
    clean_title = escape_html(group_title)
    clean_rules = rules_content.strip()
    has_branding = ("elitebots" in clean_rules.lower()) or ("powered by" in clean_rules.lower())
    if include_footer and not has_branding:
        return f"{E_DIAMOND} <b>Group Rules for {clean_title}:</b>\n\n{clean_rules}\n\n{POWERED_BY_FOOTER}"
    return f"{E_DIAMOND} <b>Group Rules for {clean_title}:</b>\n\n{clean_rules}"


@router.message(CommandStart())
async def handle_start(
    message: Message,
    command: Optional[CommandObject] = None,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    db_user: Optional[User] = None,
):
    user = message.from_user
    mention = get_user_mention(user) if user else "Friend"
    chat_title = message.chat.title or "Private Chat"
    log_channel = db_group.log_channel_id if db_group else None

    # Deep-link routing (e.g. /start settings_123456)
    if command and command.args:
        args = command.args.strip()
        if args.startswith("settings_"):
            try:
                target_chat_id = int(args.replace("settings_", ""))
                if session:
                    res_g = await session.execute(
                        select(Group).where(Group.chat_id == target_chat_id)
                    )
                    group = res_g.scalars().first()
                    if group:
                        res_t = await session.execute(
                            select(TTLSettings).where(TTLSettings.chat_id == target_chat_id)
                        )
                        ttl = res_t.scalars().first()
                        if not ttl:
                            ttl = TTLSettings(chat_id=target_chat_id)
                            session.add(ttl)
                            await session.flush()

                        text = animate_text(
                            f"{E_SHIELD} <b>Remote Group Settings & Defense Dashboard</b>\n\n"
                            f"Target Group: <b>{escape_html(group.title)}</b> [<code>{group.chat_id}</code>]\n"
                            f"Configure security, TTL auto-deletions, and filters directly from DM.\n\n"
                            f"{POWERED_BY_FOOTER}"
                        )
                        kb = get_settings_main_menu(group, ttl)
                        await message.answer(text=text, reply_markup=kb, parse_mode="HTML")
                        return
            except Exception:
                pass
        elif args.startswith("rules_"):
            try:
                target_chat_id = int(args.replace("rules_", ""))
                if session:
                    res_g = await session.execute(
                        select(Group).where(Group.chat_id == target_chat_id)
                    )
                    group = res_g.scalars().first()
                    if group and group.rules_text:
                        formatted_rules = animate_text(format_rules_text(group.title, group.rules_text, include_footer=True))
                        if group.rules_media_type == "photo" and group.rules_media_file_id:
                            await message.answer_photo(
                                photo=group.rules_media_file_id,
                                caption=formatted_rules,
                                parse_mode="HTML",
                            )
                        elif group.rules_media_type == "video" and group.rules_media_file_id:
                            await message.answer_video(
                                video=group.rules_media_file_id,
                                caption=formatted_rules,
                                parse_mode="HTML",
                            )
                        elif group.rules_media_type == "animation" and group.rules_media_file_id:
                            await message.answer_animation(
                                animation=group.rules_media_file_id,
                                caption=formatted_rules,
                                parse_mode="HTML",
                            )
                        elif group.rules_media_type == "document" and group.rules_media_file_id:
                            await message.answer_document(
                                document=group.rules_media_file_id,
                                caption=formatted_rules,
                                parse_mode="HTML",
                            )
                        else:
                            await message.answer(
                                text=formatted_rules,
                                parse_mode="HTML",
                                disable_web_page_preview=False,
                            )
                        return
                    else:
                        await message.answer(
                            f"{E_NEWS} <i>No custom rules have been configured for this group yet.</i>",
                            parse_mode="HTML",
                        )
                        return
            except Exception:
                pass

    if message.chat.type == ChatType.PRIVATE:
        mau, active_groups, total_users = (1, 0, 1)
        if session:
            mau, active_groups, total_users = await get_network_metrics(session)

        bot_info = await message.bot.get_me()
        is_super = is_super_admin(user.id) if user else False

        text = animate_text(
            f"👑 <b>Welcome, {mention}!</b>\n\n"
            f"I am <b>RGCBot</b> — the premier Telegram Supergroup Management, Security & Federation Defense System {E_DIAMOND}\n\n"
            f"{E_NEWS} <b>Network Infrastructure:</b>\n"
            f"• 👥 <b>Monthly Active Users:</b> <code>{mau:,}</code>\n"
            f"• 🌐 <b>Protected Supergroups:</b> <code>{active_groups:,}</code>\n"
            f"• {E_LIGHTNING} <b>Defense Engines:</b> <code>ZERO-RISK SHIELD • ACTIVE</code>\n\n"
            f"Tap the buttons below to configure your groups, explore commands, or read the User Manual.\n\n"
            f"{POWERED_BY_FOOTER}"
        )

        kb = get_dm_start_keyboard(
            bot_username=bot_info.username or "RandomGCCorebot", is_super_admin=is_super
        )
        await message.answer(text=text, reply_markup=kb, parse_mode="HTML")
    else:
        # Group chat
        await reply_with_ttl(
            message,
            animate_text(
                f"👋 Hi {mention}! RGCBot is active in <b>{escape_html(message.chat.title)}</b> {E_SHIELD}\n"
                f"Type <code>/help</code> or <code>/settings</code> for group management."
            ),
            ttl_type=TTLType.GENERAL,
        )


@router.callback_query(F.data == "dm:menu")
async def handle_dm_main_menu(call: CallbackQuery, session: Optional[AsyncSession] = None):
    if not call.from_user or not call.bot:
        return

    mau, active_groups, total_users = (1, 0, 1)
    if session:
        mau, active_groups, total_users = await get_network_metrics(session)

    bot_info = await call.bot.get_me()
    is_super = is_super_admin(call.from_user.id)
    mention = get_user_mention(call.from_user)

    text = animate_text(
        f"👑 <b>Welcome, {mention}!</b>\n\n"
        f"I am <b>RGCBot</b> — the premier Telegram Supergroup Management, Security & Federation Defense System {E_DIAMOND}\n\n"
        f"{E_NEWS} <b>Network Infrastructure:</b>\n"
        f"• 👥 <b>Monthly Active Users:</b> <code>{mau:,}</code>\n"
        f"• 🌐 <b>Protected Supergroups:</b> <code>{active_groups:,}</code>\n"
        f"• {E_LIGHTNING} <b>Defense Engines:</b> <code>ZERO-RISK SHIELD • ACTIVE</code>\n\n"
        f"Tap the buttons below to configure your groups, explore commands, or read the User Manual.\n\n"
        f"{POWERED_BY_FOOTER}"
    )
    kb = get_dm_start_keyboard(
        bot_username=bot_info.username or "RandomGCCorebot", is_super_admin=is_super
    )
    await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.message(Command("help", "commands"))
@router.callback_query(F.data == "dm:help")
async def handle_help(event: Message | CallbackQuery):
    text = animate_text(
        f"{E_DIAMOND} <b>RGCBot Interactive Command Guide & Help Center</b>\n\n"
        "Select a feature category below to view detailed commands, permissions, and syntax:\n\n"
        f"• 🛡️ <b>Moderation & Defense:</b> Bans, mutes, warnings, panic mode, zombies\n"
        f"• 📊 <b>History & Appeals:</b> Group stats, user stats, appeals, moderation history\n"
        f"• ⚡ <b>Mass Tagging:</b> Zero-risk secret tags (<code>@all</code>, <code>@allactive</code>, <code>@rall</code>)\n"
        f"• 🌐 <b>Federations:</b> Cross-group shared banlists (<code>/fcreate</code>, <code>/fban</code>)\n"
        f"• 🔒 <b>Content Locks:</b> Granular media, link, and forward restrictions\n"
        f"• 💎 <b>Reputation & Economy:</b> Karma, streaks, daily coins, profile\n"
        f"• 🎲 <b>Games & Fun:</b> Roulette, duels, quote card maker, matchmaking\n"
        f"• ⚙️ <b>Settings Transfer:</b> Clone group configurations with one code\n"
        f"• 📖 <b>User Manual:</b> Complete architecture & setup documentation\n\n"
        f"{POWERED_BY_FOOTER}"
    )
    kb = get_help_main_keyboard()

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        if event.chat.type == ChatType.PRIVATE:
            await event.answer(text=text, reply_markup=kb, parse_mode="HTML")
        else:
            await reply_with_ttl(
                event, text, reply_markup=kb, ttl_type=TTLType.RULES, custom_ttl=60
            )


@router.callback_query(F.data == "help:defense")
async def handle_help_defense(call: CallbackQuery):
    text = animate_text(
        f"🛡️ <b>SUPERGROUP DEFENSE & MODERATION MANUAL</b>\n\n"
        f"• <code>/ban &lt;target&gt; [reason]</code> — Ban a user from the supergroup\n"
        f"• <code>/tban &lt;target&gt; &lt;duration&gt; [reason]</code> — Temp-ban (e.g. <code>1d</code>, <code>12h</code>, <code>30m</code>)\n"
        f"• <code>/mute &lt;target&gt; [reason]</code> — Restrict user from sending messages\n"
        f"• <code>/tmute &lt;target&gt; &lt;duration&gt; [reason]</code> — Temp-mute user\n"
        f"• <code>/unban &lt;target&gt;</code>, <code>/unmute &lt;target&gt;</code> — Remove restrictions\n"
        f"• <code>/warn &lt;target&gt; [reason]</code> — Issue a warning with auto-escalation (default: 3 warns = mute)\n"
        f"• <code>/warns &lt;target&gt;</code>, <code>/resetwarns &lt;target&gt;</code> — View/reset warnings\n"
        f"• <code>/history &lt;target&gt;</code> — View bans, mutes, and username changes\n"
        f"• <code>/panic [on|off]</code> — Anti-Raid instant chat lockdown\n"
        f"• <code>/zombies</code> or <code>/cleanzombies</code> — Scan & purge deleted Telegram accounts\n"
        f"• <code>/purge [count]</code>, <code>/del</code> — Bulk delete messages\n"
        f"• <code>/pin [loud]</code>, <code>/unpin</code>, <code>/unpinall</code> — Message pinning utilities\n"
        f"• <code>/blocklist add &lt;term&gt; [action]</code>, <code>/tos on|off</code> — Filter prohibited words and TOS violations\n\n"
        f"{POWERED_BY_FOOTER}"
    )
    await call.message.edit_text(
        text=text, reply_markup=get_help_back_keyboard(), parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "help:tagging")
async def handle_help_tagging(call: CallbackQuery):
    text = animate_text(
        f"⚡ <b>MASS TAGGING & MENTIONS SYSTEM</b>\n\n"
        f"<b>Zero-Risk Secret Emoji Masking:</b>\n"
        "All member display names are replaced with randomized cool emojis (<code>[⚡]</code>, <code>[🔥]</code>, <code>[💎]</code>) to guarantee 100% compliance with Telegram Terms of Service and eliminate text spam.\n\n"
        f"• <code>@all [announcement]</code> or <code>/tagall</code> — Tags all registered group members in 5-user chunks with live ETA status card\n"
        f"• <code>@allactive [text]</code> or <code>/tagactive</code> — Tags active chatters (last 7 days message history) in ultra-fast time (~15–45s)\n"
        f"• <code>@rall [text]</code> or <code>/rtagall</code> — Mentions members directly replying to the target message\n"
        f"• <code>/tagstop</code> or <code>@cancel</code> — Instantly halts any running tagging task\n"
        f"• <code>@admin [reason]</code> or <code>/report</code> — Reports offensive messages to all administrators in private DM with instant jump-link\n\n"
        f"{POWERED_BY_FOOTER}"
    )
    await call.message.edit_text(
        text=text, reply_markup=get_help_back_keyboard(), parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "help:federation")
async def handle_help_federation(call: CallbackQuery):
    text = animate_text(
        f"🌐 <b>CROSS-GROUP SECURITY FEDERATIONS</b>\n\n"
        "A Federation allows multiple supergroups to share a unified banlist. When a scammer or raid bot is banned in the federation, they are banned across <b>every connected chat</b> automatically.\n\n"
        f"• <code>/fcreate &lt;name&gt;</code> — Create a new Security Federation\n"
        f"• <code>/fjoin &lt;fed_id&gt;</code> — Link current supergroup to a federation (Group Owner only)\n"
        f"• <code>/fleave</code> — Unlink current group from federation\n"
        f"• <code>/finfo [fed_id]</code> — View federation details, member chats, and ban stats\n"
        f"• <code>/fban &lt;user&gt; [reason]</code> — Federation-ban a bad actor across all linked chats\n"
        f"• <code>/funban &lt;user&gt;</code> — Remove a federation ban\n"
        f"• <code>/fpromote &lt;user&gt;</code> — Appoint a Federation Admin (Owner only)\n"
        f"• <code>/fdemote &lt;user&gt;</code> — Remove a Federation Admin\n\n"
        f"{POWERED_BY_FOOTER}"
    )
    await call.message.edit_text(
        text=text, reply_markup=get_help_back_keyboard(), parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "help:locks")
async def handle_help_locks(call: CallbackQuery):
    text = animate_text(
        f"🔒 <b>GRANULAR CONTENT LOCKS SYSTEM</b>\n\n"
        "Control exactly what media and message types non-admin members can send:\n\n"
        f"• <code>/locks</code> — Open the interactive visual locks toggle dashboard\n"
        f"• <code>/lock &lt;type&gt;</code> — Lock a specific content type (e.g. <code>/lock stickers</code>)\n"
        f"• <code>/unlock &lt;type&gt;</code> — Unlock a specific content type\n"
        f"• <code>/lockall</code> — Lock all content types (text only allowed)\n"
        f"• <code>/unlockall</code> — Unlock all content types\n\n"
        f"<b>Supported Lock Types:</b>\n"
        f"<code>stickers</code>, <code>animations</code> (GIFs), <code>photos</code>, <code>videos</code>, <code>audios</code>, <code>voice</code>, <code>documents</code>, <code>contacts</code>, <code>locations</code>, <code>polls</code>, <code>links</code>, <code>forwards</code>, <code>inline_bots</code>, <code>games</code>\n\n"
        f"{POWERED_BY_FOOTER}"
    )
    await call.message.edit_text(
        text=text, reply_markup=get_help_back_keyboard(), parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "help:reputation")
async def handle_help_reputation(call: CallbackQuery):
    text = animate_text(
        f"💎 <b>REPUTATION, KARMA & ECONOMY GUIDE</b>\n\n"
        f"• <code>+rep</code> or <code>thanks</code> — Reply to a helpful member to award them +1 Karma\n"
        f"• <code>/daily</code> — Claim your daily coin bonus and maintain your daily login streak\n"
        f"• <code>/profile</code> — View your personal member card with rank tier, coins, and badges\n"
        f"• <code>/karma</code>, <code>/topkarma</code> — View reputation leaderboard\n"
        f"• <code>/afk [reason]</code> — Set AFK status (bot notifies users who tag you)\n\n"
        f"<b>Elite Rank Tiers:</b>\n"
        f"• 🥉 <i>Novice</i> (0 pts)\n"
        f"• 🥈 <i>Apprentice</i> (10 pts)\n"
        f"• 🥇 <i>Veteran</i> (50 pts)\n"
        f"• 💎 <i>Master</i> (150 pts)\n"
        f"• 👑 <i>Grandmaster</i> (500 pts)\n"
        f"• ⚡ <i>Mythic Legend</i> (1,000+ pts)\n\n"
        f"{POWERED_BY_FOOTER}"
    )
    await call.message.edit_text(
        text=text, reply_markup=get_help_back_keyboard(), parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "help:games")
async def handle_help_games(call: CallbackQuery):
    text = animate_text(
        f"🎲 <b>GAMES, FUN & QUOTE MAKER</b>\n\n"
        f"• <code>/ship</code> — Matchmaking compatibility radar between group members with animated graphic card\n"
        f"• <code>/q</code> or <code>/quote</code> — Generate a sleek graphic quote card from any replied message\n"
        f"• <code>/qrand</code> — Generate a random quote card from recent cached messages\n"
        f"• <code>/roulette</code> — Russian Roulette (1-in-6 chance of 60s temporary mute!)\n"
        f"• <code>/duel &lt;amount&gt;</code> — Challenge another member to a coin duel\n"
        f"• <code>/dice</code>, <code>/slots</code>, <code>/darts</code>, <code>/bowling</code> — Interactive Telegram mini-games with coin rewards\n"
        f"• <code>/stats [today|weekly|monthly|all]</code> — Generate aesthetic chat statistics with group profile color palette\n\n"
        f"{POWERED_BY_FOOTER}"
    )
    await call.message.edit_text(
        text=text, reply_markup=get_help_back_keyboard(), parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "help:settings")
async def handle_help_settings(call: CallbackQuery):
    text = animate_text(
        f"⚙️ <b>SETTINGS & INSTANT TRANSFER ENGINE</b>\n\n"
        f"• <code>/settings</code> — Interactive group defense, TTL auto-delete, and CAPTCHA dashboard\n"
        f"• <code>/exportsettings</code> — Export the entire security, locks, and defense configuration into an encrypted code\n"
        f"• <code>/importsettings &lt;code&gt;</code> — Paste the code into another group to clone all settings instantly in 1 second!\n"
        f"• <code>/setrules &lt;text&gt;</code>, <code>/rules</code> — Configure and view group rules\n"
        f"• <code>/setnote &lt;target&gt; &lt;text&gt;</code>, <code>/notes</code> — Internal administrator notes\n"
        f"• <code>/filter &lt;word&gt; &lt;reply&gt;</code>, <code>/filters</code> — Custom keyword auto-responses\n\n"
        f"{POWERED_BY_FOOTER}"
    )
    await call.message.edit_text(
        text=text, reply_markup=get_help_back_keyboard(), parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "help:faq")
@router.message(Command("faq"))
async def handle_help_faq(event: Message | CallbackQuery):
    text = animate_text(
        f"❓ <b>FREQUENTLY ASKED QUESTIONS (FAQ)</b>\n\n"
        f"<b>Q: How do I enable auto-deleting bot messages (TTL)?</b>\n"
        "A: Open <code>/settings</code> ➔ Auto-Delete (TTL). You can set custom lifetimes for moderation, fun, rules, and general responses.\n\n"
        f"<b>Q: Why do tagging commands use emojis instead of names?</b>\n"
        "A: We use 100% Zero-Risk Secret Emoji Masking. This guarantees Telegram TOS compliance and prevents malicious names from displaying while ensuring everyone is tagged.\n\n"
        f"<b>Q: How do I clone group settings to another group?</b>\n"
        "A: In Group A, run <code>/exportsettings</code> to get your code. In Group B, run <code>/importsettings &lt;code&gt;</code>.\n\n"
        f"<b>Q: How do I link my groups into a Federation?</b>\n"
        "A: Run <code>/fcreate &lt;name&gt;</code> to create your fed, then run <code>/fjoin &lt;fed_id&gt;</code> in each of your supergroups.\n\n"
        f"<b>Q: How does Clean Service and Anti-Channel work?</b>\n"
        "A: Open <code>/settings</code> ➔ Defense to auto-delete join/leave messages and block unauthorized channels from posting in your chat.\n\n"
        f"{POWERED_BY_FOOTER}"
    )
    kb = get_help_back_keyboard()
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        if event.chat.type == ChatType.PRIVATE:
            await event.answer(text=text, reply_markup=kb, parse_mode="HTML")
        else:
            await reply_with_ttl(
                event, text, reply_markup=kb, ttl_type=TTLType.RULES, custom_ttl=60
            )


@router.callback_query(F.data == "help:manual")
@router.message(Command("manual"))
async def handle_help_manual(event: Message | CallbackQuery):
    text = animate_text(
        f"📖 <b>COMPLETE RGCBOT USER & ADMIN MANUAL</b>\n\n"
        f"<b>1. Initial Supergroup Installation:</b>\n"
        "1. Add @RandomGCCorebot to your group.\n"
        "2. Promote RGCBot to <b>Administrator</b> with permissions (Delete Messages, Ban Users, Pin Messages).\n"
        "3. RGCBot will automatically initialize security databases and start protecting your chat.\n\n"
        f"<b>2. Security & Anti-Spam Setup:</b>\n"
        "• Type <code>/settings</code> to configure CAPTCHA verification mode (Button or Math).\n"
        "• Configure Anti-Flood to automatically mute raid spammers.\n"
        "• Use <code>/locks</code>, <code>/lock</code>, and <code>/unlock</code> to restrict media types for non-admin members.\n"
        "• Toggle <code>/cleanservice</code>, <code>/antichannel</code>, and <code>/tos</code> for chat hygiene.\n\n"
        f"<b>3. Moderation Actions:</b>\n"
        "• Target users by replying to their message, using @username, or numeric Telegram ID.\n"
        "• Commands: <code>/ban</code>, <code>/tban</code>, <code>/mute</code>, <code>/tmute</code>, <code>/warn</code>, <code>/purge</code>, <code>/history</code>.\n\n"
        f"<b>4. Mass Announcements:</b>\n"
        "• Use <code>@all [text]</code> to notify all members with live progress and ETA.\n"
        "• Use <code>@allactive [text]</code> for ultra-fast active chatter tagging (~15-45s).\n\n"
        f"<b>5. Multi-Group Federation:</b>\n"
        "• Connect all your chats with <code>/fcreate</code> and <code>/fjoin</code> to establish unified ban protection.\n\n"
        f"<b>6. Super Admin Tools:</b>\n"
        "• Use <code>/helpadmin</code>, <code>/adminpanel</code>, and <code>/broadcast</code> for global operations.\n"
        "• Use <code>/syncmembers</code> to refresh the local member cache.\n\n"
        f"{POWERED_BY_FOOTER}"
    )
    kb = get_help_back_keyboard()
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        if event.chat.type == ChatType.PRIVATE:
            await event.answer(text=text, reply_markup=kb, parse_mode="HTML")
        else:
            await reply_with_ttl(
                event, text, reply_markup=kb, ttl_type=TTLType.RULES, custom_ttl=60
            )


@router.callback_query(F.data == "dm:profile")
async def handle_dm_profile_callback(call: CallbackQuery, session: Optional[AsyncSession] = None):
    if not session or not call.from_user:
        return

    res = await session.execute(select(User).where(User.user_id == call.from_user.id))
    db_u = res.scalars().first()
    if not db_u:
        db_u = User(user_id=call.from_user.id, first_name=call.from_user.first_name)

    tier = get_karma_tier(db_u.karma)
    mention = mention_html(call.from_user.id, call.from_user.first_name)

    card = format_card(
        title=f"{E_DIAMOND} PERSONAL MEMBER PROFILE",
        fields=[
            ("Member", mention),
            ("Telegram ID", f"<code>{db_u.user_id}</code>"),
            ("Rank Tier", tier),
            ("Reputation Karma", f"<b>{db_u.karma} pts</b>"),
            ("Coin Balance", f"<b>{db_u.coins:,} coins</b>"),
            ("Daily Streak", f"<b>{db_u.daily_streak} days</b>"),
        ],
        footer=f"Earn coins & karma by being active in supported groups!\n\n{POWERED_BY_FOOTER}",
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 Back to Main Menu",
                    callback_data="dm:menu",
                    style="primary",
                    icon_custom_emoji_id="5434144690511290129",
                )
            ]
        ]
    )
    await call.message.edit_text(text=animate_text(card), reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.in_(("dm:my_groups", "dm:settings_list")))
async def handle_dm_my_groups(call: CallbackQuery, session: Optional[AsyncSession] = None):
    if not session or not call.from_user or not call.bot:
        return

    res = await session.execute(select(Group).where(Group.is_active == True))
    all_groups = res.scalars().all()

    admin_groups = []
    user_id = call.from_user.id
    is_super = is_super_admin(user_id)

    for g in all_groups:
        if is_super:
            admin_groups.append(g)
            continue
        try:
            member = await call.bot.get_chat_member(chat_id=g.chat_id, user_id=user_id)
            if member.status in ("creator", "administrator"):
                admin_groups.append(g)
        except Exception:
            pass

    if not admin_groups:
        text = animate_text(
            f"{E_SHIELD} <b>No Managed Groups Found</b>\n\n"
            "You are not recognized as an administrator in any groups where RGCBot is currently installed.\n\n"
            "👉 Add RGCBot to your group as an administrator to enable remote management.\n\n"
            f"{POWERED_BY_FOOTER}"
        )
        bot_info = await call.bot.get_me()
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Add to Your Group",
                        url=f"https://t.me/{bot_info.username}?startgroup=true&admin=change_info+delete_messages+restrict_members+invite_users+pin_messages",
                        style="success",
                        icon_custom_emoji_id="5427168083074628963",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Back to Main Menu",
                        callback_data="dm:menu",
                        style="primary",
                        icon_custom_emoji_id="5434144690511290129",
                    )
                ],
            ]
        )
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
        await call.answer()
        return

    text = animate_text(
        f"{E_SHIELD} <b>Select a Group to Configure:</b>\n\n"
        "Click any supergroup below to manage its security filters, defense modules, and auto-delete settings directly in this chat.\n\n"
        f"{POWERED_BY_FOOTER}"
    )
    kb = get_group_selection_keyboard(admin_groups, action_prefix="dm_cfg:open")
    await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("dm_cfg:open:"))
async def handle_dm_cfg_open(call: CallbackQuery, session: Optional[AsyncSession] = None):
    if not session or not call.message or not call.from_user:
        return

    chat_id = int(call.data.split(":")[-1])
    res_g = await session.execute(select(Group).where(Group.chat_id == chat_id))
    group = res_g.scalars().first()
    if not group:
        await call.answer("Group not found in database.", show_alert=True)
        return

    res_t = await session.execute(select(TTLSettings).where(TTLSettings.chat_id == chat_id))
    ttl = res_t.scalars().first()
    if not ttl:
        ttl = TTLSettings(chat_id=chat_id)
        session.add(ttl)
        await session.flush()

    text = animate_text(
        f"{E_SHIELD} <b>Remote Group Settings Dashboard</b>\n\n"
        f"Group: <b>{escape_html(group.title)}</b> [<code>{group.chat_id}</code>]\n"
        f"Configure security, TTL auto-deletions, and filters directly in DM.\n\n"
        f"{POWERED_BY_FOOTER}"
    )
    kb = get_settings_main_menu(group, ttl)
    await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.message(Command("rules"))
async def handle_rules(
    message: Message,
    db_group: Optional[Group] = None,
):
    if not db_group:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not db_group.rules_text and not db_group.rules_media_file_id:
        await reply_with_ttl(
            message,
            animate_text(
                f"{E_NEWS} <i>No custom rules configured yet for <b>{escape_html(db_group.title)}</b>.\n"
                f"Admins can configure them with <code>/setrules &lt;text | reply to media/post&gt;</code></i>"
            ),
            ttl_type=TTLType.RULES,
            custom_ttl=45,
        )
        return

    bot_info = await message.bot.get_me()
    check_rules_url = f"https://t.me/{bot_info.username}?start=rules_{db_group.chat_id}"

    # If rules consist of media, redirect to DM with a single clean button
    if db_group.rules_media_type and db_group.rules_media_file_id:
        single_btn_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🟢 Check Rules (View Media)",
                        url=check_rules_url,
                        style="success",
                        icon_custom_emoji_id="5237699328843200968",
                    )
                ]
            ]
        )
        redirect_text = animate_text(
            f"{E_DIAMOND} <b>Group Rules for {escape_html(db_group.title)}</b>\n\n"
            f"📜 <i>The official guidelines for this group contain rich media.\n"
            f"Tap the button below to view the full rules & media in DM:</i>"
        )
        await reply_with_ttl(message, redirect_text, reply_markup=single_btn_kb, ttl_type=TTLType.RULES, custom_ttl=60)
        return

    # If text-only rules, output directly in group chat
    formatted_rules = animate_text(format_rules_text(db_group.title, db_group.rules_text or "No rules specified.", include_footer=False))
    await reply_with_ttl(message, formatted_rules, ttl_type=TTLType.RULES, custom_ttl=60)


@router.message(Command("setrules"))
async def handle_set_rules(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not is_admin:
        await message.answer("❌ Only administrators can configure group rules.")
        return

    media_type = None
    media_file_id = None
    rules_text = None

    if message.reply_to_message:
        replied = message.reply_to_message
        if replied.photo:
            media_type = "photo"
            media_file_id = replied.photo[-1].file_id
            rules_text = replied.caption or ""
        elif replied.video:
            media_type = "video"
            media_file_id = replied.video.file_id
            rules_text = replied.caption or ""
        elif replied.animation:
            media_type = "animation"
            media_file_id = replied.animation.file_id
            rules_text = replied.caption or ""
        elif replied.document:
            media_type = "document"
            media_file_id = replied.document.file_id
            rules_text = replied.caption or ""
        else:
            rules_text = replied.html_text or replied.text or ""

        cmd_html = message.html_text or message.text or ""
        parts = cmd_html.split(maxsplit=1)
        if len(parts) > 1 and parts[1].strip():
            rules_text = parts[1].strip()
    else:
        cmd_html = message.html_text or message.text or ""
        parts = cmd_html.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            help_text = animate_text(
                f"{E_ALERT} <b>How to Configure Group Rules:</b>\n\n"
                f"1. <b>Text/Links:</b> <code>/setrules &lt;your rules text with links/formatting&gt;</code>\n"
                f"2. <b>Rich Media:</b> Reply to any Photo, Video, GIF, Document, or Post with <code>/setrules</code>"
            )
            await reply_with_ttl(message, help_text, ttl_type=TTLType.MODERATION)
            return
        rules_text = parts[1].strip()

    db_group.rules_text = rules_text
    db_group.rules_media_type = media_type
    db_group.rules_media_file_id = media_file_id
    await session.commit()

    if message.from_user:
        await AuditService.log_action(
            bot=message.bot,
            chat_id=db_group.chat_id,
            chat_title=db_group.title,
            target_user_id=message.from_user.id,
            target_user_name=message.from_user.full_name or message.from_user.first_name,
            admin_user_id=message.from_user.id,
            admin_user_name=message.from_user.full_name or message.from_user.first_name,
            action=ActionType.RULES_UPDATE,
            reason="Configured group rules",
            channel_id=db_group.log_channel_id,
        )

    card = format_card(
        title=f"{E_DIAMOND} GROUP RULES CONFIGURED",
        fields=[
            ("Group", f"<b>{escape_html(db_group.title)}</b>"),
            ("Media Attached", f"<code>{media_type.upper() if media_type else 'TEXT ONLY'}</code>"),
            ("Interactive Button", "🟢 Check Rules (Active)"),
            ("Status", "✅ Saved & Operational"),
        ],
        footer="Members can view the rules via /rules",
    )
    await reply_with_ttl(message, animate_text(card), ttl_type=TTLType.MODERATION)


@router.message(Command("clearrules", "resetrules"))
async def handle_clear_rules(
    message: Message,
    session: Optional[AsyncSession] = None,
    db_group: Optional[Group] = None,
    is_admin: bool = False,
):
    if not db_group or not session:
        await message.answer("⚠️ This command can only be used in a supergroup.")
        return

    if not is_admin:
        await message.answer("❌ Only administrators can reset group rules.")
        return

    db_group.rules_text = None
    db_group.rules_media_type = None
    db_group.rules_media_file_id = None
    await session.commit()

    await reply_with_ttl(
        message,
        animate_text(f"{E_CHECK} <b>Group rules have been cleared and reset.</b>"),
        ttl_type=TTLType.MODERATION,
    )


import time


@router.message(Command("ping"))
async def cmd_ping(message: Message):
    t0 = time.time()
    sent = await message.reply("🏓 <i>Pinging...</i>", parse_mode="HTML")
    latency = (time.time() - t0) * 1000
    card = format_card(
        title=f"{E_ROBOT} RGC ENGINE PING",
        fields=[
            ("Roundtrip Latency", f"<code>{latency:.1f} ms</code>"),
            ("Database Engine", "PostgreSQL / Redis"),
            ("Status", "🟢 100% Operational"),
        ],
        footer=POWERED_BY_FOOTER,
    )
    await sent.edit_text(card, parse_mode="HTML")
