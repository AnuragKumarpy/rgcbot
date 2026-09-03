import re
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.redis import redis_manager
from src.models.user import User
from src.utils.text_formatter import get_karma_tier, mention_html

REP_TRIGGERS_REGEX = re.compile(
    r"^(\+\+|\+1|\+rep|(thanks|thank you|thank u|ty|thx|tq|tysm|thnx|respect|helpful|great job|legend|pro)\b)",
    re.IGNORECASE,
)


class KarmaService:
    @staticmethod
    def is_rep_trigger(text: Optional[str]) -> bool:
        if not text:
            return False
        clean = text.strip().lower()
        if clean in ("++", "+1", "+rep"):
            return True
        return bool(REP_TRIGGERS_REGEX.search(clean))

    @classmethod
    async def process_reputation(
        cls,
        session: AsyncSession,
        giver: User,
        receiver: User,
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Awards 1 karma point from giver to receiver.
        Returns: (success, reason_or_message, new_karma)
        """
        if giver.user_id == receiver.user_id:
            return False, "You cannot award reputation to yourself!", None

        # Check pair cooldown in Redis (60 seconds)
        redis = await redis_manager.get_client()
        cooldown_key = f"rgcbot:rep_cd:{giver.user_id}:{receiver.user_id}"
        is_on_cooldown = await redis.get(cooldown_key)
        if is_on_cooldown:
            return (
                False,
                "⏳ You already awarded reputation to this member recently. Please wait a moment!",
                None,
            )

        # Increment receiver karma
        receiver.karma += 1
        # Set cooldown for 60 seconds
        await redis.set(cooldown_key, "1", ex=60)

        tier = get_karma_tier(receiver.karma)
        return True, tier, receiver.karma

    @classmethod
    async def claim_daily(cls, user: User) -> Tuple[bool, str, int, int]:
        """
        Claims daily streak reward.
        Returns: (success, message, streak, coins_earned)
        """
        now = datetime.utcnow()
        if user.last_daily_at:
            elapsed = now - user.last_daily_at
            if elapsed < timedelta(hours=20):
                remaining = timedelta(hours=20) - elapsed
                hours, rem = divmod(int(remaining.total_seconds()), 3600)
                mins, _ = divmod(rem, 60)
                return (
                    False,
                    f"⏳ You have already claimed your daily reward today! Come back in <b>{hours}h {mins}m</b>.",
                    user.daily_streak,
                    0,
                )

            # Check if streak broken (more than 48 hours)
            if elapsed > timedelta(hours=48):
                user.daily_streak = 1
            else:
                user.daily_streak += 1
        else:
            user.daily_streak = 1

        user.last_daily_at = now

        # Bonus formula
        base_coins = 100
        streak_bonus = min(user.daily_streak * 25, 500)
        total_coins = base_coins + streak_bonus
        user.coins += total_coins

        return True, "Success", user.daily_streak, total_coins

    @classmethod
    async def get_top_karma(cls, session: AsyncSession, limit: int = 10) -> List[User]:
        result = await session.execute(select(User).order_by(desc(User.karma)).limit(limit))
        return list(result.scalars().all())

    @classmethod
    def format_leaderboard(cls, top_users: List[User]) -> str:
        if not top_users:
            return "<b>REPUTATION LEADERBOARD</b>\n\n<i>No members have earned reputation yet.</i>"

        lines = ["<b>TOP REPUTATION CONTRIBUTORS</b>\n"]
        rank_markers = ["✦", "◆", "▲", "■", "▫", "▪", "•", "•", "•", "•"]

        for i, user in enumerate(top_users):
            marker = rank_markers[i] if i < len(rank_markers) else "•"
            name = user.first_name or f"User {user.user_id}"
            mention = mention_html(user.user_id, name)
            tier = get_karma_tier(user.karma)
            lines.append(f"{marker} #{i + 1} {mention} — <b>{user.karma} pts</b> <i>({tier})</i>")

        return "\n".join(lines)
