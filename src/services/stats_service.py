import colorsys
import io
import math
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from aiogram import Bot
from aiogram.types import Message
from loguru import logger
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import UserActivity
from src.models.user import User
from src.services.quote_service import QuoteService


class StatsService:
    @staticmethod
    def _get_font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        paths = [
            f"src/assets/fonts/{name}.ttf",
            f"/app/src/assets/fonts/{name}.ttf",
            f"/Users/mac/rgcbot/src/assets/fonts/{name}.ttf",
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            f"DejaVuSans.ttf",
        ]
        for p in paths:
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
        return ImageFont.load_default()

    @classmethod
    async def record_activity(
        cls,
        session: AsyncSession,
        chat_id: int,
        user_id: int,
        message: Message,
    ):
        """Records message activity for the current day in PostgreSQL."""
        if chat_id >= 0 or not user_id:
            return

        today = date.today()
        is_sticker = 1 if message.sticker else 0
        is_media = 1 if (message.photo or message.video or message.document or message.animation) else 0
        is_voice = 1 if (message.voice or message.audio or message.video_note) else 0

        try:
            stmt = pg_insert(UserActivity).values(
                chat_id=chat_id,
                user_id=user_id,
                date=today,
                messages_count=1,
                stickers_count=is_sticker,
                media_count=is_media,
                voice_count=is_voice,
            ).on_conflict_do_update(
                constraint="uq_user_chat_activity_date",
                set_={
                    "messages_count": UserActivity.messages_count + 1,
                    "stickers_count": UserActivity.stickers_count + is_sticker,
                    "media_count": UserActivity.media_count + is_media,
                    "voice_count": UserActivity.voice_count + is_voice,
                },
            )
            await session.execute(stmt)
            await session.commit()
        except Exception as e:
            logger.debug(f"Record activity note: {e}")

    @classmethod
    async def get_chat_stats(
        cls,
        session: AsyncSession,
        chat_id: int,
        timeframe: str = "today",
    ) -> Dict[str, Any]:
        """
        Queries aggregated statistics for the requested timeframe:
        'today', 'weekly', 'monthly', 'all_time'
        """
        today = date.today()
        start_date = None
        if timeframe == "today":
            start_date = today
        elif timeframe == "weekly":
            start_date = today - timedelta(days=7)
        elif timeframe == "monthly":
            start_date = today - timedelta(days=30)

        # 1. Total chat activity query
        summary_stmt = select(
            func.coalesce(func.sum(UserActivity.messages_count), 0),
            func.coalesce(func.sum(UserActivity.stickers_count), 0),
            func.coalesce(func.sum(UserActivity.media_count), 0),
            func.coalesce(func.sum(UserActivity.voice_count), 0),
            func.count(func.distinct(UserActivity.user_id)),
        ).where(UserActivity.chat_id == chat_id)

        if start_date:
            summary_stmt = summary_stmt.where(UserActivity.date >= start_date)

        summary_res = await session.execute(summary_stmt)
        tot_msg, tot_stick, tot_med, tot_voice, active_users = summary_res.one()

        # 2. Top 10 active contributors
        top_stmt = (
            select(
                UserActivity.user_id,
                func.sum(UserActivity.messages_count).label("total_msgs"),
                func.sum(UserActivity.stickers_count).label("total_stickers"),
                func.sum(UserActivity.media_count).label("total_media"),
                func.sum(UserActivity.voice_count).label("total_voice"),
                User.first_name,
                User.username,
            )
            .outerjoin(User, User.user_id == UserActivity.user_id)
            .where(UserActivity.chat_id == chat_id)
            .group_by(UserActivity.user_id, User.first_name, User.username)
            .order_by(func.sum(UserActivity.messages_count).desc())
            .limit(10)
        )

        if start_date:
            top_stmt = top_stmt.where(UserActivity.date >= start_date)

        top_res = await session.execute(top_stmt)
        top_users: List[Dict[str, Any]] = []

        for row in top_res.all():
            top_users.append({
                "user_id": row[0],
                "messages": row[1] or 0,
                "stickers": row[2] or 0,
                "media": row[3] or 0,
                "voice": row[4] or 0,
                "name": row[5] or f"User {row[0]}",
                "username": row[6],
            })

        return {
            "timeframe": timeframe,
            "total_messages": int(tot_msg),
            "total_stickers": int(tot_stick),
            "total_media": int(tot_med),
            "total_voice": int(tot_voice),
            "active_users": int(active_users),
            "top_users": top_users,
        }

    @classmethod
    async def fetch_chat_avatar(cls, bot: Bot, chat_id: int) -> Optional[Image.Image]:
        try:
            chat = await bot.get_chat(chat_id)
            if chat.photo and chat.photo.big_file_id:
                file = await bot.get_file(chat.photo.big_file_id)
                if file.file_path:
                    bio = io.BytesIO()
                    await bot.download_file(file.file_path, bio)
                    bio.seek(0)
                    return Image.open(bio)
        except Exception as e:
            logger.debug(f"Could not fetch chat avatar for {chat_id}: {e}")
        return None

    @classmethod
    def extract_palette(cls, img: Optional[Image.Image]) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        """Dynamically extracts dominant vibrant theme colors from the group avatar."""
        if not img:
            return (0, 215, 255), (160, 80, 255)

        thumb = img.convert("RGB").resize((64, 64))
        pixels = list(thumb.getdata())

        scored = []
        for r, g, b in pixels:
            h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if 0.20 <= s <= 0.99 and 0.25 <= v <= 0.99:
                score = (s ** 1.3) * (v ** 1.1)
                scored.append((score, (r, g, b)))

        if not scored:
            return (0, 215, 255), (160, 80, 255)

        scored.sort(key=lambda x: x[0], reverse=True)
        primary = scored[0][1]

        # Brighten/boost primary if needed
        pr_h, pr_s, pr_v = colorsys.rgb_to_hsv(primary[0] / 255.0, primary[1] / 255.0, primary[2] / 255.0)
        pr_v = max(0.85, pr_v)
        pr_s = min(0.95, max(0.65, pr_s))
        p_rgb = colorsys.hsv_to_rgb(pr_h, pr_s, pr_v)
        primary = (int(p_rgb[0] * 255), int(p_rgb[1] * 255), int(p_rgb[2] * 255))

        # Secondary harmonic color
        secondary = None
        for _, c in scored[8:]:
            c_h, _, _ = colorsys.rgb_to_hsv(c[0] / 255.0, c[1] / 255.0, c[2] / 255.0)
            if abs(pr_h - c_h) > 0.12:
                secondary = c
                break

        if not secondary:
            sec_h = (pr_h + 0.18) % 1.0
            s_rgb = colorsys.hsv_to_rgb(sec_h, 0.85, 0.95)
            secondary = (int(s_rgb[0] * 255), int(s_rgb[1] * 255), int(s_rgb[2] * 255))
        else:
            sec_h, sec_s, sec_v = colorsys.rgb_to_hsv(secondary[0] / 255.0, secondary[1] / 255.0, secondary[2] / 255.0)
            sec_v = max(0.80, sec_v)
            sec_s = min(0.95, max(0.60, sec_s))
            s_rgb = colorsys.hsv_to_rgb(sec_h, sec_s, sec_v)
            secondary = (int(s_rgb[0] * 255), int(s_rgb[1] * 255), int(s_rgb[2] * 255))

        return primary, secondary

    @classmethod
    def generate_stats_card(
        cls,
        chat_title: str,
        avatar_img: Optional[Image.Image],
        stats_data: Dict[str, Any],
    ) -> io.BytesIO:
        """
        Generates a studio-grade landscape visual stats card (1200x680)
        dynamically themed with the group's profile photo palette.
        """
        W, H = 2400, 1360
        scale = 2

        primary, secondary = cls.extract_palette(avatar_img)

        # 1. Base dark background with ambient radial glow
        bg_r = int(10 + primary[0] * 0.03)
        bg_g = int(12 + primary[1] * 0.03)
        bg_b = int(18 + primary[2] * 0.05)
        base = Image.new("RGBA", (W, H), (bg_r, bg_g, bg_b, 255))

        # Ambient Glow Layer
        glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)

        # Top-left ambient glow behind avatar
        glow_draw.ellipse(
            (-200, -200, 950, 950),
            fill=(*primary, 48),
        )
        # Bottom-right ambient glow
        glow_draw.ellipse(
            (W - 850, H - 750, W + 300, H + 300),
            fill=(*secondary, 36),
        )
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(150))
        base.alpha_composite(glow_layer)

        draw = ImageDraw.Draw(base)

        # Subtle grid dots in background
        dot_color = (255, 255, 255, 12)
        for gx in range(40 * scale, W, 40 * scale):
            for gy in range(40 * scale, H, 40 * scale):
                draw.ellipse((gx - 1, gy - 1, gx + 1, gy + 1), fill=dot_color)

        # Fonts
        font_brand = cls._get_font("Outfit", 20 * scale)
        font_title = cls._get_font("Outfit", 36 * scale)
        font_timeframe = cls._get_font("Outfit", 17 * scale)
        font_metric_num = cls._get_font("Outfit", 30 * scale)
        font_metric_lbl = cls._get_font("Inter", 14 * scale)
        font_section = cls._get_font("Outfit", 22 * scale)
        font_user_rank = cls._get_font("Outfit", 20 * scale)
        font_user_name = cls._get_font("Outfit", 24 * scale)
        font_user_stat = cls._get_font("Inter", 18 * scale)

        # 2. Header Container (Glass Panel)
        draw.rounded_rectangle(
            (60 * scale, 45 * scale, (W // scale - 60) * scale, 175 * scale),
            radius=20 * scale,
            fill=(18, 22, 34, 215),
            outline=(*primary, 70),
            width=2 * scale,
        )

        # 3. Avatar: Clean single circular avatar (NO double border)
        AVATAR_D = 96 * scale
        av_x, av_y = 80 * scale, 62 * scale

        if avatar_img:
            av_resized = avatar_img.convert("RGBA").resize((AVATAR_D, AVATAR_D), Image.Resampling.LANCZOS)
        else:
            av_resized = Image.new("RGBA", (AVATAR_D, AVATAR_D), (28, 34, 48, 255))
            d_av = ImageDraw.Draw(av_resized)
            init_letter = (QuoteService.clean_emoji_text(chat_title)[:1] or "G").upper()
            f_init = cls._get_font("Outfit", 44 * scale)
            bbox = d_av.textbbox((0, 0), init_letter, font=f_init)
            d_av.text(
                ((AVATAR_D - (bbox[2] - bbox[0])) // 2, (AVATAR_D - (bbox[3] - bbox[1])) // 2 - 4 * scale),
                init_letter,
                fill=(255, 255, 255, 255),
                font=f_init,
            )

        # Single circle mask
        mask = Image.new("L", (AVATAR_D, AVATAR_D), 0)
        d_m = ImageDraw.Draw(mask)
        d_m.ellipse((0, 0, AVATAR_D - 1, AVATAR_D - 1), fill=255)

        circ_avatar = Image.new("RGBA", (AVATAR_D, AVATAR_D), (0, 0, 0, 0))
        circ_avatar.paste(av_resized, (0, 0), mask=mask)

        # Single sleek accent ring
        d_ring = ImageDraw.Draw(circ_avatar)
        d_ring.ellipse(
            (1 * scale, 1 * scale, AVATAR_D - 2 * scale, AVATAR_D - 2 * scale),
            outline=(*primary, 255),
            width=3 * scale,
        )
        base.paste(circ_avatar, (av_x, av_y), mask=circ_avatar)

        # Group Title & Brand Header
        clean_title = QuoteService.clean_emoji_text(chat_title)[:24]
        draw.text((196 * scale, 64 * scale), "ACTIVITY METRICS", fill=(*primary, 230), font=font_brand)
        draw.text((196 * scale, 88 * scale), clean_title, fill=(255, 255, 255, 255), font=font_title)

        # Timeframe Chip
        timeframe_label = stats_data.get("timeframe", "today").upper()
        timeframe_text = f"• {timeframe_label} •"
        tf_box = draw.textbbox((0, 0), timeframe_text, font=font_timeframe)
        tf_w = tf_box[2] - tf_box[0] + 24 * scale
        tf_x = 196 * scale
        tf_y = 135 * scale
        draw.rounded_rectangle(
            (tf_x, tf_y, tf_x + tf_w, tf_y + 24 * scale),
            radius=8 * scale,
            fill=(14, 18, 28, 240),
            outline=(*primary, 140),
            width=1 * scale,
        )
        draw.text((tf_x + 12 * scale, tf_y + 3 * scale), timeframe_text, fill=(*primary, 255), font=font_timeframe)

        # 4. Top Metrics Cards (Top Right of Header)
        metrics = [
            ("MESSAGES", f"{stats_data.get('total_messages', 0):,}"),
            ("CONTRIBUTORS", f"{stats_data.get('active_users', 0):,}"),
            ("STICKERS", f"{stats_data.get('total_stickers', 0):,}"),
            ("MEDIA", f"{stats_data.get('total_media', 0):,}"),
        ]

        m_card_w = 136 * scale
        m_card_h = 92 * scale
        m_gap = 12 * scale
        m_start_x = (W // scale - 80) * scale - len(metrics) * (m_card_w + m_gap) + m_gap
        m_y = 64 * scale

        for i, (lbl, val) in enumerate(metrics):
            cx = m_start_x + i * (m_card_w + m_gap)
            draw.rounded_rectangle(
                (cx, m_y, cx + m_card_w, m_y + m_card_h),
                radius=14 * scale,
                fill=(24, 28, 42, 230),
                outline=(45, 52, 74, 180),
                width=1 * scale,
            )
            draw.text((cx + 16 * scale, m_y + 12 * scale), val, fill=(255, 255, 255, 255), font=font_metric_num)
            draw.text((cx + 16 * scale, m_y + 54 * scale), lbl, fill=(145, 158, 185, 255), font=font_metric_lbl)

        # 5. Leaderboard Section Header
        lb_y = 196 * scale
        draw.text((65 * scale, lb_y), "TOP ACTIVE CONTRIBUTORS", fill=(255, 255, 255, 255), font=font_section)

        # 6. Leaderboard Rows (Top 6 users)
        top_users = stats_data.get("top_users", [])[:6]
        max_msgs = max([u["messages"] for u in top_users], default=1)
        max_msgs = max(max_msgs, 1)

        row_start_y = 232 * scale
        row_h = 66 * scale
        row_gap = 10 * scale

        medal_labels = ["#1", "#2", "#3", "#4", "#5", "#6"]
        medal_colors = [
            (255, 215, 0),    # Gold #1
            (210, 220, 235),  # Silver #2
            (225, 145, 70),   # Bronze #3
            (145, 155, 175),
            (145, 155, 175),
            (145, 155, 175),
        ]

        for idx, u in enumerate(top_users):
            ry = row_start_y + idx * (row_h + row_gap)
            rw_box = (60 * scale, ry, (W // scale - 60) * scale, ry + row_h)

            # Glass card row
            is_top3 = idx < 3
            bg_alpha = 220 if is_top3 else 165
            border_col = (*primary, 85) if idx == 0 else (42, 48, 68, 160)

            draw.rounded_rectangle(
                rw_box,
                radius=14 * scale,
                fill=(20, 24, 36, bg_alpha),
                outline=border_col,
                width=1 * scale,
            )

            # Rank Badge Pill with Dark Glass & Colored Accent Border
            r_fill = (26, 30, 46, 240)
            r_outline = (*medal_colors[idx], 220) if is_top3 else (55, 62, 85, 180)
            draw.rounded_rectangle(
                (75 * scale, ry + 16 * scale, 120 * scale, ry + 50 * scale),
                radius=8 * scale,
                fill=r_fill,
                outline=r_outline,
                width=1 * scale,
            )
            draw.text((82 * scale, ry + 19 * scale), medal_labels[idx], fill=medal_colors[idx], font=font_user_rank)

            # User Name
            user_name = QuoteService.clean_emoji_text(u["name"])[:20]
            name_color = (255, 255, 255, 255) if is_top3 else (225, 230, 242, 240)
            draw.text((138 * scale, ry + 17 * scale), user_name, fill=name_color, font=font_user_name)

            # Message Count Pill (Right)
            count_str = f"{u['messages']:,} msgs"
            c_box = draw.textbbox((0, 0), count_str, font=font_user_stat)
            c_w = c_box[2] - c_box[0] + 24 * scale
            pill_x = (W // scale - 75) * scale - c_w
            pill_y = ry + 16 * scale

            pill_fill = (16, 20, 30, 240)
            pill_outline = (*primary, 150) if idx == 0 else (55, 64, 88, 180)

            draw.rounded_rectangle(
                (pill_x, pill_y, pill_x + c_w, pill_y + 34 * scale),
                radius=8 * scale,
                fill=pill_fill,
                outline=pill_outline,
                width=1 * scale,
            )
            count_color = (*primary, 255) if idx == 0 else (220, 228, 245, 255)
            draw.text((pill_x + 12 * scale, pill_y + 6 * scale), count_str, fill=count_color, font=font_user_stat)

            # Progress Bar (Between Name and Count Pill)
            bar_x = 520 * scale
            bar_w = pill_x - bar_x - 30 * scale
            bar_y = ry + 27 * scale
            bar_h = 12 * scale

            # Track
            draw.rounded_rectangle(
                (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h),
                radius=6 * scale,
                fill=(32, 38, 54, 255),
            )

            # Themed Progress Bar
            ratio = min(1.0, u["messages"] / max_msgs)
            filled_w = max(10 * scale, int(bar_w * ratio))

            bar_fill = primary if idx == 0 else secondary if idx == 1 else (95, 160, 245) if idx == 2 else (80, 95, 130)
            draw.rounded_rectangle(
                (bar_x, bar_y, bar_x + filled_w, bar_y + bar_h),
                radius=6 * scale,
                fill=bar_fill,
            )

        if not top_users:
            draw.text(
                (W // 2 - 160 * scale, row_start_y + 100 * scale),
                "No message activity recorded in this period yet!",
                fill=(140, 150, 175, 255),
                font=font_user_name,
            )

        # Downscale to 1200x680 with Lanczos for ultra-crisp output
        final_img = base.resize((1200, 680), Image.Resampling.LANCZOS)

        bio = io.BytesIO()
        final_img.convert("RGB").save(bio, format="JPEG", quality=96)
        bio.seek(0)
        return bio
