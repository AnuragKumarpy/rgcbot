from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import TTLType
from src.middlewares.ttl import reply_with_ttl
from src.services.federation_service import FederationService
from src.utils.emojis import (
    E_CHECK,
    E_CROWN,
    E_DIAMOND,
    E_FIRE,
    E_ROCKET,
    E_SHIELD,
    E_WARN,
    animate_text,
)
from src.utils.permissions import is_owner, is_super_admin
from src.utils.target_resolver import resolve_target
from src.utils.text_formatter import escape_html, format_card, mention_html

router = Router(name="admin_federation")

POWERED_BY_FOOTER = (
    '⚡ <b>Powered by ELITE Bot</b> <a href="https://t.me/EliteBotsTelegram">@EliteBotsTelegram</a>'
)


@router.message(Command("fcreate", "newfed"))
async def handle_fcreate(message: Message, session: Optional[AsyncSession] = None):
    if not message.from_user or not session:
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2 or not parts[1].strip():
        await reply_with_ttl(
            message,
            f"{E_WARN} <b>Usage:</b> <code>/fcreate &lt;Federation Name&gt;</code>\n"
            "<i>Creates a new shared security federation for your supergroup network.</i>\n\n"
            f"",
            ttl_type=TTLType.MODERATION,
        )
        return
    fed_name = parts[1].strip()
    fed = await FederationService.create_federation(
        session, owner_id=message.from_user.id, name=fed_name
    )
    card = format_card(
        title=f"{E_SHIELD} FEDERATION CREATED SUCCESSFULLY",
        fields=[
            ("Federation Name", f"<b>{escape_html(fed.name)}</b>"),
            ("Federation ID", f"<code>{fed.fed_id}</code>"),
            ("Owner", mention_html(message.from_user.id, message.from_user.first_name)),
            ("Status", "<b>ACTIVE & SECURE</b>"),
        ],
        footer=f"Use <code>/fjoin {fed.fed_id}</code> in your groups to link them.\n\n{POWERED_BY_FOOTER}",
    )
    await reply_with_ttl(message, animate_text(card), ttl_type=TTLType.MODERATION, custom_ttl=60)


@router.message(Command("fjoin", "joinfed"))
async def handle_fjoin(
    message: Message,
    # NOTE: this parameter name previously was `is_owner_user`, but
    # AuthMiddleware populates the dict key "is_owner" - aiogram injects
    # handler params by matching them to that dict, so the mismatched name
    # meant this value was ALWAYS False regardless of the actual sender's
    # role. Real group owners could never /fjoin; only super admins could
    # (since is_super_admin() is checked separately below). Fixed to match.
    is_owner: bool = False,
    session: Optional[AsyncSession] = None,
):
    if not message.from_user or not session or message.chat.id >= 0:
        return
    user_id = message.from_user.id
    if not (is_super_admin(user_id) or is_owner):
        await reply_with_ttl(
            message,
            "❌ <b>Permission Denied:</b> Only the supergroup creator/owner can link a federation.",
            ttl_type=TTLType.MODERATION,
        )
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2 or not parts[1].strip():
        await reply_with_ttl(
            message,
            f"{E_WARN} <b>Usage:</b> <code>/fjoin &lt;fed_id&gt;</code>",
            ttl_type=TTLType.MODERATION,
        )
        return
    fed_id = parts[1].strip()
    success = await FederationService.join_federation(
        session, fed_id=fed_id, chat_id=message.chat.id
    )
    if not success:
        await reply_with_ttl(
            message,
            f"❌ <b>Error:</b> Federation ID <code>{escape_html(fed_id)}</code> does not exist.",
            ttl_type=TTLType.MODERATION,
        )
        return
    fed = await FederationService.get_federation(session, fed_id)
    await reply_with_ttl(
        message,
        animate_text(
            f"{E_CHECK} <b>Group Linked to Federation!</b>\n\n"
            f"• <b>Federation:</b> <b>{escape_html(fed.name)}</b> [<code>{fed.fed_id}</code>]\n"
            f"• <b>Shared Protection:</b> Any <code>/fban</code> will instantly sync to this group.\n\n"
            f""
        ),
        ttl_type=TTLType.MODERATION,
        custom_ttl=45,
    )


@router.message(Command("fleave", "leavefed"))
async def handle_fleave(
    message: Message,
    # Same fix as handle_fjoin above - matches AuthMiddleware's "is_owner" key.
    is_owner: bool = False,
    session: Optional[AsyncSession] = None,
):
    if not message.from_user or not session or message.chat.id >= 0:
        return
    if not (is_super_admin(message.from_user.id) or is_owner):
        await reply_with_ttl(
            message,
            "❌ <b>Permission Denied:</b> Only the supergroup creator/owner can unlink from a federation.",
            ttl_type=TTLType.MODERATION,
        )
        return
    left = await FederationService.leave_federation(session, chat_id=message.chat.id)
    if left:
        await reply_with_ttl(
            message,
            f"{E_CHECK} <b>Group unlinked from federation successfully.</b>",
            ttl_type=TTLType.MODERATION,
        )
    else:
        await reply_with_ttl(
            message,
            "<i>This group is not currently linked to any federation.</i>",
            ttl_type=TTLType.MODERATION,
        )


@router.message(Command("finfo", "fedinfo"))
async def handle_finfo(message: Message, session: Optional[AsyncSession] = None):
    if not session:
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    target_fed_id = parts[1].strip() if len(parts) > 1 else None
    if target_fed_id:
        stats = await FederationService.get_fed_stats(session, target_fed_id)
    else:
        if message.chat.id < 0:
            fed = await FederationService.get_group_federation(session, message.chat.id)
            if not fed:
                await reply_with_ttl(
                    message,
                    f"<i>This group is not linked to any federation. Link with <code>/fjoin &lt;fed_id&gt;</code></i>",
                    ttl_type=TTLType.MODERATION,
                )
                return
            stats = await FederationService.get_fed_stats(session, fed.fed_id)
        else:
            await reply_with_ttl(
                message,
                f"{E_WARN} <b>Usage:</b> <code>/finfo &lt;fed_id&gt;</code>",
                ttl_type=TTLType.MODERATION,
            )
            return
    if not stats:
        await reply_with_ttl(
            message, "❌ <b>Federation not found.</b>", ttl_type=TTLType.MODERATION
        )
        return
    card = format_card(
        title=f"{E_SHIELD} FEDERATION INTELLIGENCE REPORT",
        fields=[
            ("Federation Name", f"<b>{escape_html(stats['name'])}</b>"),
            ("Federation ID", f"<code>{stats['fed_id']}</code>"),
            ("Owner ID", f"<code>{stats['owner_id']}</code>"),
            ("Connected Supergroups", f"<b>{stats['groups_count']} chats</b>"),
            ("Global Fed Bans", f"<b>{stats['bans_count']} bad actors</b>"),
            ("Appointed Fed Admins", f"<b>{stats['admins_count']} moderators</b>"),
        ],
        footer=POWERED_BY_FOOTER,
    )
    await reply_with_ttl(message, animate_text(card), ttl_type=TTLType.MODERATION, custom_ttl=60)


@router.message(Command("fban", "fedban"))
async def handle_fban(
    message: Message,
    session: Optional[AsyncSession] = None,
):
    if not message.from_user or not session or message.chat.id >= 0:
        return
    fed = await FederationService.get_group_federation(session, message.chat.id)
    if not fed:
        await reply_with_ttl(
            message,
            f"❌ <b>This group is not linked to any federation.</b>\nLink with <code>/fjoin &lt;fed_id&gt;</code>",
            ttl_type=TTLType.MODERATION,
        )
        return
    # Check fed admin permissions
    is_fed_adm = await FederationService.is_fed_admin(session, fed.fed_id, message.from_user.id)
    if not (is_super_admin(message.from_user.id) or is_fed_adm):
        await reply_with_ttl(
            message,
            "❌ <b>Permission Denied:</b> You are not an administrator of this federation.",
            ttl_type=TTLType.MODERATION,
        )
        return
    target = await resolve_target(message, session=session)
    if not target or not target.user_id:
        await reply_with_ttl(
            message,
            f"{E_WARN} <b>Usage:</b> <code>/fban &lt;user&gt; [reason]</code>",
            ttl_type=TTLType.MODERATION,
        )
        return
    if is_super_admin(target.user_id):
        await reply_with_ttl(
            message,
            f"{E_SHIELD} This user is a <b>Super Admin</b> and is immune to federation bans.",
            ttl_type=TTLType.MODERATION,
        )
        return
    reason = target.reason or "Violated Federation Security Policy"
    banned_chats = await FederationService.ban_user(
        bot=message.bot,
        session=session,
        fed_id=fed.fed_id,
        user_id=target.user_id,
        reason=reason,
        banned_by_id=message.from_user.id,
    )
    card = format_card(
        title=f"⛔ FEDERATION BAN EXECUTED",
        fields=[
            ("Target User", mention_html(target.user_id, target.first_name)),
            ("User ID", f"<code>{target.user_id}</code>"),
            ("Federation", f"<b>{escape_html(fed.name)}</b> [<code>{fed.fed_id}</code>]"),
            ("Enforcement Scope", f"<b>Banned across {banned_chats} linked groups</b>"),
            ("Reason", f"<i>{escape_html(reason)}</i>"),
            ("Enforcer", mention_html(message.from_user.id, message.from_user.first_name)),
        ],
        footer=POWERED_BY_FOOTER,
    )
    await reply_with_ttl(message, animate_text(card), ttl_type=TTLType.MODERATION, custom_ttl=60)


@router.message(Command("funban", "fedunban"))
async def handle_funban(
    message: Message,
    session: Optional[AsyncSession] = None,
):
    if not message.from_user or not session or message.chat.id >= 0:
        return
    fed = await FederationService.get_group_federation(session, message.chat.id)
    if not fed:
        await reply_with_ttl(
            message,
            f"❌ <b>This group is not linked to any federation.</b>",
            ttl_type=TTLType.MODERATION,
        )
        return
    is_fed_adm = await FederationService.is_fed_admin(session, fed.fed_id, message.from_user.id)
    if not (is_super_admin(message.from_user.id) or is_fed_adm):
        await reply_with_ttl(
            message,
            "❌ <b>Permission Denied:</b> You are not an administrator of this federation.",
            ttl_type=TTLType.MODERATION,
        )
        return
    target = await resolve_target(message, session=session)
    if not target or not target.user_id:
        await reply_with_ttl(
            message,
            f"{E_WARN} <b>Usage:</b> <code>/funban &lt;user&gt;</code>",
            ttl_type=TTLType.MODERATION,
        )
        return
    unbanned_chats = await FederationService.unban_user(
        bot=message.bot,
        session=session,
        fed_id=fed.fed_id,
        user_id=target.user_id,
    )
    await reply_with_ttl(
        message,
        animate_text(
            f"{E_CHECK} <b>Federation Unban Executed!</b>\n\n"
            f"• <b>User:</b> {mention_html(target.user_id, target.first_name)} (<code>{target.user_id}</code>)\n"
            f"• <b>Federation:</b> <b>{escape_html(fed.name)}</b>\n"
            f"• <b>Unbanned across:</b> {unbanned_chats} linked supergroups\n\n"
            f""
        ),
        ttl_type=TTLType.MODERATION,
        custom_ttl=45,
    )


@router.message(Command("fpromote", "fedpromote"))
async def handle_fpromote(message: Message, session: Optional[AsyncSession] = None):
    if not message.from_user or not session or message.chat.id >= 0:
        return
    fed = await FederationService.get_group_federation(session, message.chat.id)
    if not fed:
        await reply_with_ttl(
            message,
            f"❌ <b>This group is not linked to any federation.</b>",
            ttl_type=TTLType.MODERATION,
        )
        return
    if not (is_super_admin(message.from_user.id) or fed.owner_id == message.from_user.id):
        await reply_with_ttl(
            message,
            "❌ <b>Permission Denied:</b> Only the Federation Owner can promote Fed Admins.",
            ttl_type=TTLType.MODERATION,
        )
        return
    target = await resolve_target(message, session=session)
    if not target or not target.user_id:
        await reply_with_ttl(
            message,
            f"{E_WARN} <b>Usage:</b> <code>/fpromote &lt;user&gt;</code>",
            ttl_type=TTLType.MODERATION,
        )
        return
    await FederationService.promote_fed_admin(session, fed_id=fed.fed_id, user_id=target.user_id)
    await reply_with_ttl(
        message,
        animate_text(
            f"{E_CROWN} <b>Promoted to Federation Admin!</b>\n\n"
            f"• <b>User:</b> {mention_html(target.user_id, target.first_name)} [<code>{target.user_id}</code>]\n"
            f"• <b>Federation:</b> <b>{escape_html(fed.name)}</b> [<code>{fed.fed_id}</code>]\n"
            f"• <b>Permissions:</b> Authorized to execute global <code>/fban</code> and <code>/funban</code>.\n\n"
            f""
        ),
        ttl_type=TTLType.MODERATION,
        custom_ttl=60,
    )


@router.message(Command("fdemote", "feddemote"))
async def handle_fdemote(message: Message, session: Optional[AsyncSession] = None):
    if not message.from_user or not session or message.chat.id >= 0:
        return
    fed = await FederationService.get_group_federation(session, message.chat.id)
    if not fed:
        await reply_with_ttl(
            message,
            f"❌ <b>This group is not linked to any federation.</b>",
            ttl_type=TTLType.MODERATION,
        )
        return
    if not (is_super_admin(message.from_user.id) or fed.owner_id == message.from_user.id):
        await reply_with_ttl(
            message,
            "❌ <b>Permission Denied:</b> Only the Federation Owner can demote Fed Admins.",
            ttl_type=TTLType.MODERATION,
        )
        return
    target = await resolve_target(message, session=session)
    if not target or not target.user_id:
        await reply_with_ttl(
            message,
            f"{E_WARN} <b>Usage:</b> <code>/fdemote &lt;user&gt;</code>",
            ttl_type=TTLType.MODERATION,
        )
        return
    await FederationService.demote_fed_admin(session, fed_id=fed.fed_id, user_id=target.user_id)
    await reply_with_ttl(
        message,
        f"{E_CHECK} <b>Demoted from Federation Admin:</b> {mention_html(target.user_id, target.first_name)}",
        ttl_type=TTLType.MODERATION,
    )
