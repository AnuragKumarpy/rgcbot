import asyncio
import os
from typing import Optional, Tuple
from loguru import logger
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.getenv("TELEGRAM_API_ID", "28102220"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "c9ff5d60c4b80bf5f7de1092082207a5")
SESSION_STRING = os.getenv("USER_SESSION_STRING", "1BVtsOHoBu3Qm0HDjjhqTXms7P6E5BD-WOvPAHCCqbmk8-kBVCIxc4KwqWfJRwWYQw6B_DpISsylq4t32UbWb5ADOp3xXiF2hxK8Gw8V-yGPcmDvilmZFUtLUPYCimKuNs-Ym2_iTAa9CWfDQG0DHRJTFfYgLxYwsznGXMKNEC70gMI2CphjSp-Itu2l0QiWRvzOey9Hq7tZxOytSC8tlJ_2SXK0fPR3LFIA1CS-gGwDTJ6m6Fxp-d5iPhNbbOQ4FV9veNPHo4QbJO8vEcbIF5Nr2A5RBe3_29m6I7j5gkcHkEkrgMb5_sexonlcRSgW9V4rkEfQCWXM9M95TTqXMfwVaeLZJFAo=")


class MTProtoResolver:
    _client: Optional[TelegramClient] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_client(cls) -> Optional[TelegramClient]:
        async with cls._lock:
            if cls._client is not None:
                if cls._client.is_connected():
                    return cls._client
                else:
                    try:
                        await cls._client.connect()
                        if await cls._client.is_user_authorized():
                            return cls._client
                    except Exception as conn_err:
                        logger.warning(f"[MTProtoResolver] Reconnect failed: {conn_err}")

            try:
                cls._client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
                await cls._client.connect()
                if not await cls._client.is_user_authorized():
                    logger.warning("[MTProtoResolver] User session is not authorized.")
                    return None
                
                logger.info("[MTProtoResolver] Palantir MTProto user session connected successfully.")
                return cls._client
            except Exception as e:
                logger.warning(f"[MTProtoResolver] Could not initialize MTProto client: {e}")
                return None

    @classmethod
    async def resolve_username(cls, username: str) -> Optional[Tuple[int, str, str]]:
        """
        Resolves any Telegram username globally using Palantir MTProto user session.
        Returns (user_id, first_name, username) or None.
        """
        if not username:
            return None

        clean_uname = username.lstrip("@").strip()
        if not clean_uname:
            return None

        client = await cls.get_client()
        if not client:
            return None

        try:
            entity = await client.get_entity(clean_uname)
            if entity and hasattr(entity, "id"):
                user_id = int(entity.id)
                first_name = getattr(entity, "first_name", None) or getattr(entity, "title", f"User {user_id}")
                uname = getattr(entity, "username", clean_uname) or clean_uname
                logger.info(f"[MTProtoResolver] Resolved @{clean_uname} -> ID {user_id} ({first_name})")
                return (user_id, str(first_name), str(uname))
        except Exception as e:
            logger.warning(f"[MTProtoResolver] Could not resolve @{clean_uname} via MTProto: {e}")

        return None
