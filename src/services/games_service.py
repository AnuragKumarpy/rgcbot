import asyncio
import random
from typing import Optional, Tuple
from aiogram import Bot
from aiogram.types import ChatPermissions, Message
from src.core.enums import ActionType
from src.core.redis import redis_manager
from src.models.group import Group
from src.models.user import User
from src.services.audit_service import AuditService
from src.services.moderation_service import ModerationService
from src.utils.text_formatter import get_user_mention, mention_html


class GamesService:
    @classmethod
    async def record_game_result(
        cls,
        session,
        user: Optional[User],
        score_delta: int = 0,
        won: bool = False,
    ) -> None:
        if not session or not user:
            return

        user.games_played += 1
        if won:
            user.games_won += 1
        if score_delta > 0:
            user.game_score += score_delta

    @classmethod
    async def play_russian_roulette(
        cls,
        bot: Bot,
        group: Group,
        user: User,
        message: Message,
    ) -> Tuple[bool, str]:
        """
        Russian roulette with 1-in-6 chance of 60s temporary mute.
        Returns: (survived: bool, result_text: str)
        """
        chamber = random.randint(1, 6)
        user_mention = get_user_mention(message.from_user)
        user.games_played += 1

        if chamber == 1:
            # Bang! Muted for 60 seconds
            mute_duration = 60
            from src.core.database import db

            async for session in db.get_session():
                await ModerationService.mute_user(
                    bot=bot,
                    session=session,
                    group=group,
                    target_user=user,
                    admin_user=None,
                    reason="Lost Russian Roulette 💥",
                    duration_seconds=mute_duration,
                )

            text = (
                f"💥 <b>*BANG!*</b>\n\n"
                f"{user_mention} pulled the trigger and the chamber wasn't empty!\n"
                f"💀 You have been muted for <b>60 seconds</b> to recover."
            )
            return False, text
        else:
            # Safe!
            user.coins += 10
            user.games_won += 1
            user.game_score += 10
            text = (
                f"🔫 <i>*Click*</i>\n\n"
                f"{user_mention} pulls the trigger... and nothing happens!\n"
                f"🍀 <b>You survived!</b> (+10 coins awarded)"
            )
            return True, text

    @classmethod
    def evaluate_dice_score(cls, emoji: str, value: int) -> Tuple[str, int]:
        """
        Evaluates Telegram native dice animation values into human feedback and reward points.
        """
        if emoji == "🎰":
            # Slot Machine: 64 is 777 (Jackpot), 1 is bar/bar/bar, 22 is berry/berry/berry, 43 is lemon/lemon/lemon
            if value == 64:
                return "🎰 <b>JACKPOT! 777!</b> 🔥 (+100 coins)", 100
            elif value in (1, 22, 43):
                return "🎉 <b>Three of a kind!</b> (+30 coins)", 30
            else:
                return "Better luck next spin!", 0
        elif emoji == "🎯":
            if value == 6:
                return "🎯 <b>BULLSEYE! Direct hit!</b> (+25 coins)", 25
            elif value >= 4:
                return "🎯 Great shot!", 5
            else:
                return "Missed the center!", 0
        elif emoji == "🏀":
            if value in (4, 5):
                return "🏀 <b>SWISH! Perfect basket!</b> (+15 coins)", 15
            else:
                return "Missed the hoop!", 0
        elif emoji == "⚽":
            if value in (3, 4, 5):
                return "⚽ <b>GOAAAL! What a strike!</b> (+15 coins)", 15
            else:
                return "Saved by the keeper!", 0
        elif emoji == "🎳":
            if value == 6:
                return "🎳 <b>STRIKE! All pins down!</b> (+30 coins)", 30
            else:
                return f"Knocked down {value} pins.", 0
        else:  # Standard 🎲
            if value == 6:
                return "🎲 <b>Rolled a 6! Maximum roll!</b> (+10 coins)", 10
            else:
                return f"🎲 You rolled a {value}.", 0
