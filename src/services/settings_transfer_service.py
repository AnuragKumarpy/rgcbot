import base64
import json
import zlib
from typing import Any, Dict, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.blocklist import BlocklistTerm
from src.models.filter import GroupFilter
from src.models.group import Group
from src.models.ttl import TTLSettings


class SettingsTransferService:
    CONFIG_PREFIX = "RGC-CFG-"

    @classmethod
    async def export_settings(cls, session: AsyncSession, chat_id: int) -> str:
        """
        Exports group settings (welcome, captcha, locks, protections, ttl, filters, blocklist)
        into a compact compressed base64 token.
        """
        # 1. Fetch Group
        g_res = await session.execute(select(Group).where(Group.chat_id == chat_id))
        group = g_res.scalar_one_or_none()
        if not group:
            raise ValueError("Group not found in database.")

        # 2. Fetch TTL
        ttl_res = await session.execute(select(TTLSettings).where(TTLSettings.chat_id == chat_id))
        ttl = ttl_res.scalar_one_or_none()

        # 3. Fetch Filters
        fil_res = await session.execute(select(GroupFilter).where(GroupFilter.chat_id == chat_id))
        filters = [
            {"keyword": f.keyword, "reply_text": f.reply_text, "media_type": f.media_type, "file_id": f.file_id}
            for f in fil_res.scalars().all()
        ]

        # 4. Fetch Blocklist
        blk_res = await session.execute(select(BlocklistTerm).where(BlocklistTerm.chat_id == chat_id))
        blocklist = [b.term for b in blk_res.scalars().all()]

        payload = {
            "v": 1,
            "welcome": {
                "enabled": group.welcome_enabled,
                "text": group.welcome_text,
                "media_type": group.welcome_media_type,
                "file_id": group.welcome_media_file_id,
                "buttons": group.welcome_buttons,
            },
            "captcha": {
                "mode": group.captcha_mode,
                "timeout": group.captcha_timeout_sec,
            },
            "locks": {
                "locked_types": group.locked_types or "",
                "clean_service": group.clean_service_enabled,
                "antichannel": group.antichannel_enabled,
                "antichannel_mode": group.antichannel_mode or "del",
            },
            "security": {
                "antispam": group.antispam_enabled,
                "antiflood_limit": group.antiflood_limit,
                "antiforward": group.antiforward_enabled,
                "antilink": group.antilink_enabled,
                "english_only": group.english_only_enabled,
                "tos_shield": group.tos_shield_enabled,
            },
            "warns": {
                "max": group.max_warns,
                "action": group.warn_action,
                "duration": group.warn_duration_sec,
            },
            "night_mode": {
                "enabled": group.night_mode_enabled,
                "start": group.night_mode_start,
                "end": group.night_mode_end,
            },
            "ttl": {
                "mod": ttl.mod_ttl if ttl else 30,
                "fun": ttl.fun_ttl if ttl else 60,
                "rules": ttl.rules_ttl if ttl else 120,
                "warn": ttl.warn_ttl if ttl else 45,
                "general": ttl.general_ttl if ttl else 60,
                "del_trigger": ttl.delete_command_trigger if ttl else True,
            },
            "filters": filters,
            "blocklist": blocklist,
        }

        raw_json = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        compressed = zlib.compress(raw_json, level=9)
        encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
        return f"{cls.CONFIG_PREFIX}{encoded}"

    @classmethod
    async def import_settings(
        cls,
        session: AsyncSession,
        chat_id: int,
        config_code: str,
    ) -> Dict[str, Any]:
        """
        Parses and applies exported settings to the target group.
        """
        clean_code = config_code.strip()
        if clean_code.startswith(cls.CONFIG_PREFIX):
            clean_code = clean_code[len(cls.CONFIG_PREFIX):]

        try:
            compressed = base64.urlsafe_b64decode(clean_code)
            raw_json = zlib.decompress(compressed).decode("utf-8")
            data = json.loads(raw_json)
        except Exception as e:
            raise ValueError(f"Invalid or corrupted settings code: {e}")

        # 1. Update Group record
        g_res = await session.execute(select(Group).where(Group.chat_id == chat_id))
        group = g_res.scalar_one_or_none()
        if not group:
            group = Group(chat_id=chat_id, is_active=True)
            session.add(group)

        # Welcome
        w = data.get("welcome", {})
        group.welcome_enabled = w.get("enabled", True)
        group.welcome_text = w.get("text", group.welcome_text)
        group.welcome_media_type = w.get("media_type")
        group.welcome_media_file_id = w.get("file_id")
        group.welcome_buttons = w.get("buttons")

        # Captcha
        c = data.get("captcha", {})
        group.captcha_mode = c.get("mode", "button")
        group.captcha_timeout_sec = c.get("timeout", 90)

        # Locks & CleanService & Anti-Channel
        lk = data.get("locks", {})
        group.locked_types = lk.get("locked_types", "")
        group.clean_service_enabled = lk.get("clean_service", False)
        group.antichannel_enabled = lk.get("antichannel", False)
        group.antichannel_mode = lk.get("antichannel_mode", "del")

        # Security
        s = data.get("security", {})
        group.antispam_enabled = s.get("antispam", True)
        group.antiflood_limit = s.get("antiflood_limit", 5)
        group.antiforward_enabled = s.get("antiforward", False)
        group.antilink_enabled = s.get("antilink", False)
        group.english_only_enabled = s.get("english_only", False)
        group.tos_shield_enabled = s.get("tos_shield", True)

        # Warns
        wrn = data.get("warns", {})
        group.max_warns = wrn.get("max", 3)
        group.warn_action = wrn.get("action", "mute")
        group.warn_duration_sec = wrn.get("duration", 3600)

        # Night Mode
        nm = data.get("night_mode", {})
        group.night_mode_enabled = nm.get("enabled", False)
        group.night_mode_start = nm.get("start", "00:00")
        group.night_mode_end = nm.get("end", "06:00")

        # 2. Update TTL Settings
        t_data = data.get("ttl", {})
        ttl_res = await session.execute(select(TTLSettings).where(TTLSettings.chat_id == chat_id))
        ttl = ttl_res.scalar_one_or_none()
        if not ttl:
            ttl = TTLSettings(chat_id=chat_id)
            session.add(ttl)

        ttl.mod_ttl = t_data.get("mod", 30)
        ttl.fun_ttl = t_data.get("fun", 60)
        ttl.rules_ttl = t_data.get("rules", 120)
        ttl.warn_ttl = t_data.get("warn", 45)
        ttl.general_ttl = t_data.get("general", 60)
        ttl.delete_command_trigger = t_data.get("del_trigger", True)

        # 3. Import Filters
        filters_imported = 0
        if "filters" in data and isinstance(data["filters"], list):
            await session.execute(delete(GroupFilter).where(GroupFilter.chat_id == chat_id))
            for f in data["filters"]:
                session.add(GroupFilter(
                    chat_id=chat_id,
                    keyword=f["keyword"],
                    reply_text=f.get("reply_text"),
                    media_type=f.get("media_type"),
                    file_id=f.get("file_id"),
                ))
                filters_imported += 1

        # 4. Import Blocklist
        blocklist_imported = 0
        if "blocklist" in data and isinstance(data["blocklist"], list):
            await session.execute(delete(BlocklistTerm).where(BlocklistTerm.chat_id == chat_id))
            for b in data["blocklist"]:
                session.add(BlocklistTerm(
                    chat_id=chat_id,
                    term=b,
                ))
                blocklist_imported += 1

        await session.commit()

        return {
            "welcome_enabled": group.welcome_enabled,
            "captcha_mode": group.captcha_mode,
            "locked_count": len([x for x in (group.locked_types or "").split(",") if x]),
            "clean_service": group.clean_service_enabled,
            "antichannel": group.antichannel_enabled,
            "filters_count": filters_imported,
            "blocklist_count": blocklist_imported,
        }
