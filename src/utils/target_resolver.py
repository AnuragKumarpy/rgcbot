import re
from typing import List, Optional
from aiogram import Bot
from aiogram.enums import MessageEntityType
from aiogram.types import Message, User as TgUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User


class TargetResult:
    def __init__(
        self,
        user_id: int,
        first_name: str,
        username: Optional[str] = None,
        remaining_args: Optional[List[str]] = None,
        from_reply: bool = False,
    ):
        self.user_id = user_id
        self.first_name = first_name
        self.username = username
        self.remaining_args = remaining_args or []
        self.from_reply = from_reply

    def __repr__(self) -> str:
        return f"<TargetResult id={self.user_id} name={self.first_name} username={self.username} args={self.remaining_args}>"


def _is_duration_token(token: str) -> bool:
    """Checks if a string is a valid time duration token (e.g. 10m, 2h, 1d, 3w, 30s)."""
    return bool(re.match(r"^\d+[smhdw]$", token.lower().strip()))


async def resolve_target(
    message: Message,
    session: Optional[AsyncSession] = None,
    bot: Optional[Bot] = None,
) -> Optional[TargetResult]:
    """
    Resolves target user from:
    1. Reply to message
    2. Message entities (TEXT_MENTION with attached TgUser object)
    3. Direct numeric Telegram ID (e.g. 8713594643 or id:8713594643)
    4. Username mention (@username or username)
    5. Flexible position parsing (supports duration before or after target)
    """
    if not message:
        return None

    raw_text = message.text or message.caption or ""
    parts = raw_text.split()[1:] if raw_text else []

    # 1. Reply to Message
    if message.reply_to_message and message.reply_to_message.from_user:
        target_tg = message.reply_to_message.from_user
        # Auto-upsert into DB if session provided
        if session:
            try:
                res = await session.execute(select(User).where(User.user_id == target_tg.id))
                db_u = res.scalar_one_or_none()
                if not db_u:
                    session.add(
                        User(
                            user_id=target_tg.id,
                            username=target_tg.username,
                            first_name=target_tg.first_name or f"User {target_tg.id}",
                            last_name=target_tg.last_name,
                        )
                    )
                    await session.flush()
            except Exception:
                pass

        remaining = list(parts)
        # If the first token in parts is the user's ID or @username, strip it from remaining so it doesn't pollute the reason
        if parts:
            first_tok = parts[0].strip()
            num_match = re.match(r"^(?:id:)?(-?\d{5,15})$", first_tok, re.IGNORECASE)
            if num_match or first_tok.startswith("@"):
                remaining = parts[1:]
            elif target_tg.username and first_tok.lower() == target_tg.username.lower():
                remaining = parts[1:]

        return TargetResult(
            user_id=target_tg.id,
            first_name=target_tg.first_name or f"User {target_tg.id}",
            username=target_tg.username,
            remaining_args=remaining,
            from_reply=True,
        )

    # 2. Text Mention Entity (Telegram links containing full TgUser object)
    entities = message.entities or message.caption_entities or []
    for ent in entities:
        if ent.type == MessageEntityType.TEXT_MENTION and ent.user:
            u = ent.user
            mention_text = raw_text[ent.offset : ent.offset + ent.length]
            remaining = [p for p in parts if p != mention_text]

            if session:
                try:
                    res = await session.execute(select(User).where(User.user_id == u.id))
                    db_u = res.scalar_one_or_none()
                    if not db_u:
                        session.add(
                            User(
                                user_id=u.id,
                                username=u.username,
                                first_name=u.first_name or f"User {u.id}",
                                last_name=u.last_name,
                            )
                        )
                        await session.flush()
                except Exception:
                    pass

            return TargetResult(
                user_id=u.id,
                first_name=u.first_name or f"User {u.id}",
                username=u.username,
                remaining_args=remaining,
                from_reply=False,
            )

    if not parts:
        return None

    # Determine which part is the target and which parts are duration/reason
    target_idx = -1
    target_id: Optional[int] = None
    target_name: Optional[str] = None
    target_username: Optional[str] = None

    # Check first and second tokens
    for idx, token in enumerate(parts[:2]):
        clean_tok = token.strip()

        # A. Numerical User ID (e.g. "8713594643" or "id:8713594643")
        num_match = re.match(r"^(?:id:)?(-?\d{5,15})$", clean_tok, re.IGNORECASE)
        if num_match:
            target_idx = idx
            target_id = int(num_match.group(1))
            target_name = f"User {target_id}"
            break

        # B. Username with '@' (e.g. "@blucop")
        if clean_tok.startswith("@") and len(clean_tok) > 1:
            uname = clean_tok[1:].lower()
            target_idx = idx
            target_username = uname
            break

    # If first token was a duration and second token was a plain username without '@'
    if target_idx == -1 and len(parts) > 0:
        first_tok = parts[0].strip()
        if not _is_duration_token(first_tok):
            # Check if first token could be a known username in DB without '@'
            clean_uname = first_tok.lstrip("@").lower()
            if session:
                res = await session.execute(select(User).where(User.username.ilike(clean_uname)))
                db_u = res.scalar_one_or_none()
                if db_u:
                    target_idx = 0
                    target_id = db_u.user_id
                    target_name = db_u.first_name
                    target_username = db_u.username

    # If target is by username, resolve from DB first, then fallback to Palantir MTProto
    if target_username and target_id is None:
        if session:
            res = await session.execute(select(User).where(User.username.ilike(target_username)))
            db_u = res.scalar_one_or_none()
            if db_u:
                target_id = db_u.user_id
                target_name = db_u.first_name
                target_username = db_u.username

        # Fallback to MTProto Resolver for external users / users not in DB
        if target_id is None:
            try:
                from src.services.mtproto_resolver import MTProtoResolver

                mt_res = await MTProtoResolver.resolve_username(target_username)
                if mt_res:
                    target_id, target_name, target_username = mt_res
                    if session:
                        try:
                            res = await session.execute(
                                select(User).where(User.user_id == target_id)
                            )
                            db_u = res.scalar_one_or_none()
                            if not db_u:
                                session.add(
                                    User(
                                        user_id=target_id,
                                        username=target_username,
                                        first_name=target_name,
                                    )
                                )
                                await session.flush()
                            elif db_u.username != target_username:
                                db_u.username = target_username
                                await session.flush()
                        except Exception:
                            pass
            except Exception:
                pass

        if target_id is None:
            return None

    # If target is by numerical ID, check DB for rich name/username
    if target_id is not None:
        if session and (not target_name or target_name.startswith("User ")):
            res = await session.execute(select(User).where(User.user_id == target_id))
            db_u = res.scalar_one_or_none()
            if db_u:
                target_name = db_u.first_name or f"User {target_id}"
                target_username = db_u.username or target_username

        # Build remaining args excluding the target token
        remaining = [p for i, p in enumerate(parts) if i != target_idx]
        return TargetResult(
            user_id=target_id,
            first_name=target_name or f"User {target_id}",
            username=target_username,
            remaining_args=remaining,
            from_reply=False,
        )

    return None
