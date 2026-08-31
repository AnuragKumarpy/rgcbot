import re
from typing import List, Optional, Set
from aiogram.enums import MessageEntityType
from aiogram.types import Message
from src.models.group import Group

URL_REGEX = re.compile(
    r"(?:https?://|www\.|t\.me/|telegram\.me/)[^\s]+",
    re.IGNORECASE,
)

ALL_LOCK_TYPES = [
    "links",
    "forwards",
    "stickers",
    "gifs",
    "voice",
    "video",
    "photos",
    "documents",
    "polls",
    "contacts",
    "location",
    "games",
]

LOCK_ALIASES = {
    "link": "links",
    "url": "links",
    "urls": "links",
    "forward": "forwards",
    "fwd": "forwards",
    "sticker": "stickers",
    "stick": "stickers",
    "gif": "gifs",
    "animation": "gifs",
    "animations": "gifs",
    "audio": "voice",
    "voice": "voice",
    "videonote": "video",
    "round": "video",
    "videos": "video",
    "video": "video",
    "photo": "photos",
    "image": "photos",
    "images": "photos",
    "photos": "photos",
    "document": "documents",
    "doc": "documents",
    "docs": "documents",
    "file": "documents",
    "files": "documents",
    "documents": "documents",
    "poll": "polls",
    "polls": "polls",
    "contact": "contacts",
    "contacts": "contacts",
    "location": "location",
    "loc": "location",
    "game": "games",
    "games": "games",
}


class LocksService:
    @staticmethod
    def normalize_lock_type(lock_input: str) -> Optional[str]:
        clean = lock_input.lower().strip()
        if clean in ("all", "*"):
            return "all"
        if clean in ALL_LOCK_TYPES:
            return clean
        return LOCK_ALIASES.get(clean)

    @staticmethod
    def get_locked_set(group: Optional[Group]) -> Set[str]:
        if not group or not group.locked_types:
            return set()
        return {item.strip() for item in group.locked_types.split(",") if item.strip()}

    @classmethod
    def set_lock(cls, group: Group, lock_type: str, locked: bool) -> Set[str]:
        current = cls.get_locked_set(group)
        norm = cls.normalize_lock_type(lock_type)
        if not norm:
            return current

        if norm == "all":
            if locked:
                current = set(ALL_LOCK_TYPES)
            else:
                current = set()
        else:
            if locked:
                current.add(norm)
            else:
                current.discard(norm)

        group.locked_types = ",".join(sorted(current))
        return current

    @classmethod
    def check_message_locks(cls, group: Optional[Group], message: Message) -> Optional[str]:
        """
        Evaluates whether a message violates any active locks for this group.
        Returns the violated lock type name (e.g. 'links', 'stickers') or None.
        """
        if not group or not group.locked_types:
            return None

        locked = cls.get_locked_set(group)
        if not locked:
            return None

        # 1. Forwards
        if "forwards" in locked:
            if getattr(message, "forward_date", None) or getattr(message, "forward_origin", None):
                return "forwards"

        # 2. Stickers
        if "stickers" in locked and message.sticker:
            return "stickers"

        # 3. Gifs / Animations
        if "gifs" in locked and message.animation:
            return "gifs"

        # 4. Voice / Audio
        if "voice" in locked and (message.voice or message.audio):
            return "voice"

        # 5. Video & Video Notes (round videos)
        if "video" in locked and (message.video or message.video_note):
            return "video"

        # 6. Photos (excluding animations)
        if "photos" in locked and message.photo and not message.animation:
            return "photos"

        # 7. Documents (excluding animations)
        if "documents" in locked and message.document and not message.animation:
            return "documents"

        # 8. Polls
        if "polls" in locked and message.poll:
            return "polls"

        # 9. Contacts
        if "contacts" in locked and message.contact:
            return "contacts"

        # 10. Location
        if "location" in locked and (message.location or message.venue):
            return "location"

        # 11. Games
        if "games" in locked and message.game:
            return "games"

        # 12. Links
        if "links" in locked:
            text = message.text or message.caption or ""
            if text and URL_REGEX.search(text):
                return "links"
            if message.entities:
                for ent in message.entities:
                    if ent.type in (MessageEntityType.URL, MessageEntityType.TEXT_LINK):
                        return "links"
            if message.caption_entities:
                for ent in message.caption_entities:
                    if ent.type in (MessageEntityType.URL, MessageEntityType.TEXT_LINK):
                        return "links"

        return None
