import io
import json
import os
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from aiogram import Bot
from aiogram.types import Message
from loguru import logger
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.redis import redis_manager
from src.keyboards.quote_kb import get_quote_reaction_keyboard
from src.models.quote import Quote


@dataclass
class QuoteMessageData:
    message_id: int
    user_id: int
    first_name: str
    username: Optional[str]
    text: str
    date_str: str
    avatar_img: Optional[Image.Image] = None
    reply_user_name: Optional[str] = None
    reply_text: Optional[str] = None


class QuoteColorTheme:
    THEMES = {
        "dark": {
            "bg": (24, 26, 36, 245),
            "border": (70, 80, 110, 200),
            "name": (120, 185, 255),
            "reply_bar": (100, 160, 255),
            "reply_name": (140, 195, 255),
            "reply_bg": (35, 38, 54, 180),
            "text": (245, 247, 250),
            "time": (140, 150, 175),
            "avatar_ring": (120, 185, 255),
        },
        "pink": {
            "bg": (38, 16, 30, 245),
            "border": (190, 60, 130, 200),
            "name": (255, 110, 185),
            "reply_bar": (255, 110, 185),
            "reply_name": (255, 140, 200),
            "reply_bg": (55, 24, 44, 180),
            "text": (255, 240, 248),
            "time": (210, 140, 180),
            "avatar_ring": (255, 110, 185),
        },
        "blue": {
            "bg": (14, 28, 48, 245),
            "border": (35, 145, 245, 200),
            "name": (0, 215, 255),
            "reply_bar": (0, 215, 255),
            "reply_name": (80, 230, 255),
            "reply_bg": (20, 42, 72, 180),
            "text": (235, 248, 255),
            "time": (130, 180, 230),
            "avatar_ring": (0, 215, 255),
        },
        "cyan": {
            "bg": (12, 34, 44, 245),
            "border": (0, 220, 220, 200),
            "name": (0, 245, 230),
            "reply_bar": (0, 245, 230),
            "reply_name": (80, 255, 240),
            "reply_bg": (18, 50, 65, 180),
            "text": (235, 255, 252),
            "time": (120, 195, 190),
            "avatar_ring": (0, 245, 230),
        },
        "red": {
            "bg": (40, 14, 18, 245),
            "border": (210, 45, 65, 200),
            "name": (255, 65, 95),
            "reply_bar": (255, 65, 95),
            "reply_name": (255, 110, 130),
            "reply_bg": (60, 20, 28, 180),
            "text": (255, 238, 242),
            "time": (210, 130, 145),
            "avatar_ring": (255, 65, 95),
        },
        "orange": {
            "bg": (42, 24, 12, 245),
            "border": (230, 125, 30, 200),
            "name": (255, 150, 25),
            "reply_bar": (255, 150, 25),
            "reply_name": (255, 180, 80),
            "reply_bg": (62, 36, 18, 180),
            "text": (255, 246, 238),
            "time": (220, 155, 115),
            "avatar_ring": (255, 150, 25),
        },
        "green": {
            "bg": (12, 36, 24, 245),
            "border": (35, 190, 110, 200),
            "name": (0, 240, 145),
            "reply_bar": (0, 240, 145),
            "reply_name": (80, 255, 180),
            "reply_bg": (18, 54, 36, 180),
            "text": (238, 255, 248),
            "time": (130, 200, 160),
            "avatar_ring": (0, 240, 145),
        },
        "purple": {
            "bg": (32, 14, 48, 245),
            "border": (160, 65, 245, 200),
            "name": (185, 105, 255),
            "reply_bar": (185, 105, 255),
            "reply_name": (210, 145, 255),
            "reply_bg": (48, 22, 72, 180),
            "text": (248, 238, 255),
            "time": (190, 145, 220),
            "avatar_ring": (185, 105, 255),
        },
        "gold": {
            "bg": (38, 30, 10, 245),
            "border": (230, 190, 45, 200),
            "name": (255, 220, 10),
            "reply_bar": (255, 220, 10),
            "reply_name": (255, 235, 90),
            "reply_bg": (58, 46, 16, 180),
            "text": (255, 252, 235),
            "time": (210, 180, 115),
            "avatar_ring": (255, 220, 10),
        },
    }

    @classmethod
    def get_theme(cls, color_key: str) -> Dict[str, Tuple[int, int, int, int] | Tuple[int, int, int]]:
        key = color_key.lower().strip()
        if key in ("yellow",):
            key = "gold"
        elif key in ("violet",):
            key = "purple"
        elif key in ("rose",):
            key = "pink"
        elif key in ("emerald",):
            key = "green"
        elif key in ("amber",):
            key = "orange"
        elif key in ("crimson",):
            key = "red"

        if key in cls.THEMES:
            return cls.THEMES[key]

        # Check for custom hex
        hex_match = re.match(r"^#?([A-Fa-f0-9]{6})$", key)
        if hex_match:
            hex_val = hex_match.group(1)
            r = int(hex_val[0:2], 16)
            g = int(hex_val[2:4], 16)
            b = int(hex_val[4:6], 16)
            bg_r = max(10, int(r * 0.15))
            bg_g = max(10, int(g * 0.15))
            bg_b = max(15, int(b * 0.15))
            return {
                "bg": (bg_r, bg_g, bg_b, 245),
                "border": (r, g, b, 200),
                "name": (r, g, b),
                "reply_bar": (r, g, b),
                "reply_name": (min(255, r + 40), min(255, g + 40), min(255, b + 40)),
                "reply_bg": (max(15, int(r * 0.25)), max(15, int(g * 0.25)), max(20, int(b * 0.25)), 180),
                "text": (245, 247, 250),
                "time": (150, 155, 175),
                "avatar_ring": (r, g, b),
            }

        return cls.THEMES["dark"]


class QuoteService:
    @staticmethod
    def clean_emoji_text(text: str) -> str:
        """
        Strips HTML wrappers, unwraps custom Telegram animated/premium emojis (<tg-emoji>)
        to original fallback Unicode glyphs, and ensures clean text layout.
        """
        if not text:
            return ""
        # 1. Unwrap <tg-emoji emoji-id="...">FALLBACK_EMOJI</tg-emoji>
        unwrapped = re.sub(r"<tg-emoji[^>]*>(.*?)</tg-emoji>", r"\1", text, flags=re.IGNORECASE)
        # 2. Strip any other HTML tags
        clean = re.sub(r"<[^>]+>", "", unwrapped)
        return clean.strip()

    @staticmethod
    def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        font_names = [
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
            "Roboto-Bold.ttf" if bold else "Roboto-Regular.ttf",
            "Arial Bold.ttf" if bold else "Arial.ttf",
            "Helvetica-Bold.ttf" if bold else "Helvetica.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]
        for name in font_names:
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    @staticmethod
    def _get_emoji_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        emoji_paths = [
            "src/assets/fonts/Symbola.ttf",
            "/usr/share/fonts/truetype/ancient-scripts/Symbola_hint.ttf",
            "/usr/share/fonts/truetype/ancient-scripts/Symbola.ttf",
            "/System/Library/Fonts/Apple Color Emoji.ttc",
            "/Library/Fonts/Apple Color Emoji.ttc",
        ]
        for path in emoji_paths:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return QuoteService._get_font(size)

    @staticmethod
    def is_emoji_char(char: str) -> bool:
        if not char:
            return False
        code = ord(char)
        return (
            0x1F300 <= code <= 0x1FAFF or
            0x2600 <= code <= 0x27BF or
            0xFE00 <= code <= 0xFE0F or
            0x1F900 <= code <= 0x1F9FF or
            0x1F600 <= code <= 0x1F64F or
            0x1F680 <= code <= 0x1F6FF or
            0x2300 <= code <= 0x23FF or
            0x2B50 <= code <= 0x2B55 or
            code in (0x200D, 0x2764, 0x2B50, 0x2705, 0x274C, 0x2728, 0x1F44D, 0x1F44E, 0x1F31F, 0x1F48E, 0x1F451, 0x1F525)
        )

    @staticmethod
    def segment_text_emojis(text: str) -> List[Tuple[str, bool]]:
        if not text:
            return []
        segments = []
        curr_text = ""
        curr_is_emoji = QuoteService.is_emoji_char(text[0])
        for ch in text:
            ch_emoji = QuoteService.is_emoji_char(ch)
            if ch_emoji == curr_is_emoji:
                curr_text += ch
            else:
                if curr_text:
                    segments.append((curr_text, curr_is_emoji))
                curr_text = ch
                curr_is_emoji = ch_emoji
        if curr_text:
            segments.append((curr_text, curr_is_emoji))
        return segments

    @staticmethod
    def get_composite_text_bbox(
        draw: ImageDraw.ImageDraw,
        text: str,
        font_text: ImageFont.ImageFont,
        font_emoji: ImageFont.ImageFont,
    ) -> Tuple[int, int]:
        total_w = 0
        max_h = 0
        for seg, is_em in QuoteService.segment_text_emojis(text):
            font = font_emoji if is_em else font_text
            bbox = draw.textbbox((0, 0), seg, font=font)
            total_w += (bbox[2] - bbox[0])
            max_h = max(max_h, bbox[3] - bbox[1])
        return total_w, max_h

    @staticmethod
    def draw_composite_text(
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        text: str,
        font_text: ImageFont.ImageFont,
        font_emoji: ImageFont.ImageFont,
        fill_color: Tuple[int, int, int],
    ) -> int:
        curr_x = x
        for seg, is_em in QuoteService.segment_text_emojis(text):
            font = font_emoji if is_em else font_text
            bbox = draw.textbbox((curr_x, y), seg, font=font)
            draw.text((curr_x, y), seg, fill=fill_color, font=font)
            curr_x += (bbox[2] - bbox[0])
        return curr_x

    @classmethod
    async def fetch_user_avatar(cls, bot: Bot, user_id: int) -> Optional[Image.Image]:
        try:
            photos = await bot.get_user_profile_photos(user_id=user_id, limit=1)
            if photos.total_count > 0 and photos.photos:
                file_id = photos.photos[0][-1].file_id
                file = await bot.get_file(file_id)
                if file.file_path:
                    bio = io.BytesIO()
                    await bot.download_file(file.file_path, bio)
                    bio.seek(0)
                    return Image.open(bio)
        except Exception as e:
            logger.debug(f"Could not fetch avatar for {user_id}: {e}")
        return None

    @staticmethod
    def _create_circular_avatar(
        avatar_img: Optional[Image.Image],
        name: str,
        size: int,
        ring_color: Tuple[int, int, int] = (120, 185, 255),
    ) -> Image.Image:
        scale = 4
        canvas_size = size * scale

        if avatar_img:
            avatar = avatar_img.convert("RGBA").resize((canvas_size, canvas_size), Image.Resampling.LANCZOS)
        else:
            avatar = Image.new("RGBA", (canvas_size, canvas_size), (45, 50, 70, 255))
            d = ImageDraw.Draw(avatar)
            clean_name = QuoteService.clean_emoji_text(name)
            initial = (clean_name[0] if clean_name else "?").upper()
            font = QuoteService._get_font(canvas_size // 2, bold=True)
            font_emoji = QuoteService._get_emoji_font(canvas_size // 2)
            
            w, h = QuoteService.get_composite_text_bbox(d, initial, font, font_emoji)
            QuoteService.draw_composite_text(
                d,
                (canvas_size - w) // 2,
                (canvas_size - h) // 2 - 10,
                initial,
                font,
                font_emoji,
                (255, 255, 255),
            )

        # High-res circular mask
        mask = Image.new("L", (canvas_size, canvas_size), 0)
        d_mask = ImageDraw.Draw(mask)
        d_mask.ellipse((0, 0, canvas_size - 1, canvas_size - 1), fill=255)

        circ = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        circ.paste(avatar, (0, 0), mask=mask)

        # Glowing border ring
        border_w = 4 * scale
        ring = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        d_ring = ImageDraw.Draw(ring)
        d_ring.ellipse(
            (border_w // 2, border_w // 2, canvas_size - border_w // 2 - 1, canvas_size - border_w // 2 - 1),
            outline=(*ring_color, 255),
            width=border_w,
        )
        circ.alpha_composite(ring)

        return circ.resize((size, size), Image.Resampling.LANCZOS)

    @classmethod
    def parse_quote_args(cls, args: List[str]) -> Tuple[str, bool, int]:
        color = "dark"
        include_reply = False
        count = 1

        for arg in args:
            clean = arg.strip().lower()
            if clean in ("r", "reply", "rep"):
                include_reply = True
            elif clean.isdigit() and 1 <= int(clean) <= 5:
                count = int(clean)
            elif clean in QuoteColorTheme.THEMES or re.match(r"^#?[0-9a-fA-F]{6}$", clean) or clean in ("yellow", "violet", "rose", "emerald", "amber", "crimson"):
                color = clean

        return color, include_reply, count

    @classmethod
    async def cache_chat_message(cls, chat_id: int, message: Message):
        if not message or not message.from_user or message.chat.id >= 0:
            return

        raw_text = message.text or message.caption or ""
        clean_text = cls.clean_emoji_text(raw_text)
        if not clean_text and not message.sticker and not message.photo:
            return

        payload = {
            "message_id": message.message_id,
            "user_id": message.from_user.id,
            "first_name": message.from_user.first_name or f"User {message.from_user.id}",
            "username": message.from_user.username,
            "text": clean_text or "[Media]",
            "date_str": datetime.now().strftime("%H:%M"),
        }

        if message.reply_to_message and message.reply_to_message.from_user:
            payload["reply_user_name"] = message.reply_to_message.from_user.first_name or "User"
            r_text = message.reply_to_message.text or message.reply_to_message.caption or "[Media]"
            payload["reply_text"] = cls.clean_emoji_text(r_text)[:50]

        try:
            redis = await redis_manager.get_client()
            key = f"rgcbot:chat_msgs:{chat_id}"
            await redis.zadd(key, {json.dumps(payload): message.message_id})
            await redis.zremrangebyrank(key, 0, -101)
            await redis.expire(key, 86400)
        except Exception as e:
            logger.debug(f"Redis message caching note: {e}")

    @classmethod
    async def get_sequential_messages(cls, chat_id: int, start_msg_id: int, count: int) -> List[QuoteMessageData]:
        messages: List[QuoteMessageData] = []
        try:
            redis = await redis_manager.get_client()
            key = f"rgcbot:chat_msgs:{chat_id}"
            raw_items = await redis.zrangebyscore(key, min=start_msg_id, max="+inf", start=0, num=count)
            for item in raw_items:
                data = json.loads(item)
                messages.append(
                    QuoteMessageData(
                        message_id=data["message_id"],
                        user_id=data["user_id"],
                        first_name=data["first_name"],
                        username=data.get("username"),
                        text=data["text"],
                        date_str=data.get("date_str", ""),
                        reply_user_name=data.get("reply_user_name"),
                        reply_text=data.get("reply_text"),
                    )
                )
        except Exception as e:
            logger.debug(f"Redis get_sequential_messages note: {e}")
        return messages

    @classmethod
    def generate_quote_image(
        cls,
        messages: List[QuoteMessageData],
        color_key: str = "dark",
        include_reply: bool = False,
    ) -> io.BytesIO:
        theme = QuoteColorTheme.get_theme(color_key)

        SCALE = 2
        PAD_X = 24 * SCALE
        PAD_Y = 20 * SCALE
        AVATAR_SIZE = 54 * SCALE
        GAP = 14 * SCALE
        MAX_TEXT_WIDTH = 460 * SCALE
        BUBBLE_RADIUS = 22 * SCALE

        # Fonts with composite emoji support
        font_name = cls._get_font(20 * SCALE, bold=True)
        font_name_emoji = cls._get_emoji_font(20 * SCALE)
        font_text = cls._get_font(19 * SCALE, bold=False)
        font_text_emoji = cls._get_emoji_font(19 * SCALE)
        font_reply_name = cls._get_font(15 * SCALE, bold=True)
        font_reply_name_emoji = cls._get_emoji_font(15 * SCALE)
        font_reply_text = cls._get_font(15 * SCALE, bold=False)
        font_reply_text_emoji = cls._get_emoji_font(15 * SCALE)
        font_time = cls._get_font(13 * SCALE, bold=False)

        dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        dummy_draw = ImageDraw.Draw(dummy_img)

        # Word wrap helper using composite emoji font measuring
        def wrap_text(text: str, max_w: int) -> List[str]:
            lines = []
            for paragraph in text.split("\n"):
                if not paragraph:
                    lines.append("")
                    continue
                words = paragraph.split(" ")
                current_line = words[0]
                for w in words[1:]:
                    test_line = current_line + " " + w
                    w_box, _ = cls.get_composite_text_bbox(dummy_draw, test_line, font_text, font_text_emoji)
                    if w_box <= max_w:
                        current_line = test_line
                    else:
                        lines.append(current_line)
                        current_line = w
                lines.append(current_line)
            return lines

        # Layout calculation
        first_msg = messages[0]
        wrapped_body_lines: List[Tuple[QuoteMessageData, List[str]]] = []
        max_content_w = 0

        for msg in messages:
            clean_body = cls.clean_emoji_text(msg.text or "[Message]")
            lines = wrap_text(clean_body, MAX_TEXT_WIDTH)
            wrapped_body_lines.append((msg, lines))
            for l in lines:
                w_box, _ = cls.get_composite_text_bbox(dummy_draw, l, font_text, font_text_emoji)
                max_content_w = max(max_content_w, w_box)

        # Header width
        clean_first_name = cls.clean_emoji_text(first_msg.first_name)
        name_w, _ = cls.get_composite_text_bbox(dummy_draw, clean_first_name, font_name, font_name_emoji)
        time_bbox = dummy_draw.textbbox((0, 0), first_msg.date_str, font=font_time)
        header_w = name_w + (time_bbox[2] - time_bbox[0]) + 30 * SCALE
        max_content_w = max(max_content_w, header_w)

        # Reply mini-header if applicable
        has_reply_header = include_reply and first_msg.reply_user_name and first_msg.reply_text
        reply_h = 0
        if has_reply_header:
            clean_reply_user = cls.clean_emoji_text(first_msg.reply_user_name or "User")
            clean_reply_snippet = cls.clean_emoji_text(first_msg.reply_text or "")
            r_name_w, _ = cls.get_composite_text_bbox(dummy_draw, clean_reply_user, font_reply_name, font_reply_name_emoji)
            r_text_w, _ = cls.get_composite_text_bbox(dummy_draw, clean_reply_snippet, font_reply_text, font_reply_text_emoji)
            reply_w = max(r_name_w, r_text_w) + 20 * SCALE
            max_content_w = max(max_content_w, reply_w)
            reply_h = 44 * SCALE

        # Total Dimensions
        bubble_inner_w = max(max_content_w + 30 * SCALE, 200 * SCALE)
        bubble_w = bubble_inner_w + PAD_X * 2
        canvas_w = AVATAR_SIZE + GAP + bubble_w + 20 * SCALE

        # Calculate height
        line_height = 26 * SCALE
        total_text_h = sum(len(lines) * line_height + 15 * SCALE for _, lines in wrapped_body_lines)
        bubble_h = PAD_Y * 2 + 28 * SCALE + reply_h + total_text_h + 10 * SCALE
        canvas_h = max(bubble_h + 20 * SCALE, AVATAR_SIZE + 20 * SCALE)

        # Base Image (Transparent RGBA)
        base = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(base)

        # 1. Render Circular Avatar
        avatar = cls._create_circular_avatar(
            first_msg.avatar_img,
            first_msg.first_name,
            AVATAR_SIZE,
            ring_color=theme["avatar_ring"],
        )
        avatar_y = canvas_h - AVATAR_SIZE - 10 * SCALE
        base.paste(avatar, (10 * SCALE, avatar_y), mask=avatar)

        # 2. Render Bubble
        bubble_x = 10 * SCALE + AVATAR_SIZE + GAP
        bubble_y = canvas_h - bubble_h - 10 * SCALE

        draw.rounded_rectangle(
            (bubble_x, bubble_y, bubble_x + bubble_w, bubble_y + bubble_h),
            radius=BUBBLE_RADIUS,
            fill=theme["bg"],
            outline=theme["border"],
            width=2 * SCALE,
        )

        curr_y = bubble_y + PAD_Y

        # 3. Header: User Name & Timestamp
        cls.draw_composite_text(draw, bubble_x + PAD_X, curr_y, clean_first_name, font_name, font_name_emoji, theme["name"])
        time_x = bubble_x + bubble_w - PAD_X - (time_bbox[2] - time_bbox[0])
        draw.text((time_x, curr_y + 4 * SCALE), first_msg.date_str, fill=theme["time"], font=font_time)
        curr_y += 28 * SCALE

        # 4. Reply Bar
        if has_reply_header:
            r_box_y = curr_y + 4 * SCALE
            r_box_h = 36 * SCALE
            r_box_w = bubble_w - PAD_X * 2

            draw.rounded_rectangle(
                (bubble_x + PAD_X, r_box_y, bubble_x + PAD_X + r_box_w, r_box_y + r_box_h),
                radius=6 * SCALE,
                fill=theme["reply_bg"],
            )
            draw.rounded_rectangle(
                (bubble_x + PAD_X, r_box_y, bubble_x + PAD_X + 4 * SCALE, r_box_y + r_box_h),
                radius=2 * SCALE,
                fill=theme["reply_bar"],
            )
            clean_r_name = cls.clean_emoji_text(first_msg.reply_user_name or "User")
            clean_r_snippet = cls.clean_emoji_text((first_msg.reply_text or "")[:45])
            cls.draw_composite_text(
                draw,
                bubble_x + PAD_X + 10 * SCALE,
                r_box_y + 3 * SCALE,
                clean_r_name,
                font_reply_name,
                font_reply_name_emoji,
                theme["reply_name"],
            )
            cls.draw_composite_text(
                draw,
                bubble_x + PAD_X + 10 * SCALE,
                r_box_y + 19 * SCALE,
                clean_r_snippet,
                font_reply_text,
                font_reply_text_emoji,
                theme["text"],
            )
            curr_y += reply_h + 8 * SCALE

        # 5. Render Message Lines
        for msg, lines in wrapped_body_lines:
            for l in lines:
                cls.draw_composite_text(
                    draw,
                    bubble_x + PAD_X,
                    curr_y,
                    l,
                    font_text,
                    font_text_emoji,
                    theme["text"],
                )
                curr_y += line_height
            curr_y += 8 * SCALE

        # 6. Telegram Sticker Constraints (Max 512px on longest side)
        max_dim = max(canvas_w, canvas_h)
        scale_factor = 512.0 / max_dim
        final_w = int(canvas_w * scale_factor)
        final_h = int(canvas_h * scale_factor)

        final_sticker = base.resize((final_w, final_h), Image.Resampling.LANCZOS)

        bio = io.BytesIO()
        final_sticker.save(bio, format="WEBP", lossless=True, quality=95)
        bio.seek(0)
        return bio

    @classmethod
    async def save_quote(
        cls,
        session: AsyncSession,
        chat_id: int,
        message_id: int,
        user_id: int,
        file_id: str,
        text_snippet: Optional[str] = None,
    ) -> Quote:
        quote = Quote(
            chat_id=chat_id,
            message_id=message_id,
            user_id=user_id,
            file_id=file_id,
            text_snippet=text_snippet,
            likes_count=0,
            dislikes_count=0,
        )
        session.add(quote)
        await session.flush()
        return quote

    @classmethod
    async def get_random_quote(cls, session: AsyncSession, chat_id: int) -> Optional[Quote]:
        res = await session.execute(
            select(Quote).where(Quote.chat_id == chat_id).order_by(func.random()).limit(1)
        )
        return res.scalar_one_or_none()

    @classmethod
    async def toggle_reaction(
        cls,
        session: AsyncSession,
        quote_id: int,
        user_id: int,
        action: str,
    ) -> Tuple[int, int, str]:
        redis = await redis_manager.get_client()
        like_key = f"rgcbot:quote:{quote_id}:likes"
        dislike_key = f"rgcbot:quote:{quote_id}:dislikes"

        is_liked = await redis.sismember(like_key, str(user_id))
        is_disliked = await redis.sismember(dislike_key, str(user_id))

        status_msg = ""
        if action == "like":
            if is_liked:
                await redis.srem(like_key, str(user_id))
                status_msg = "Removed like."
            else:
                await redis.sadd(like_key, str(user_id))
                if is_disliked:
                    await redis.srem(dislike_key, str(user_id))
                status_msg = "👍 You liked this quote!"
        elif action == "dislike":
            if is_disliked:
                await redis.srem(dislike_key, str(user_id))
                status_msg = "Removed dislike."
            else:
                await redis.sadd(dislike_key, str(user_id))
                if is_liked:
                    await redis.srem(like_key, str(user_id))
                status_msg = "👎 You disliked this quote."

        likes = await redis.scard(like_key)
        dislikes = await redis.scard(dislike_key)

        try:
            await session.execute(
                update(Quote)
                .where(Quote.id == quote_id)
                .values(likes_count=likes, dislikes_count=dislikes)
            )
            await session.commit()
        except Exception as e:
            logger.debug(f"DB quote reaction update note: {e}")

        return likes, dislikes, status_msg

    @classmethod
    async def get_quote_reactions(cls, quote_id: int) -> Tuple[int, int]:
        try:
            redis = await redis_manager.get_client()
            like_key = f"rgcbot:quote:{quote_id}:likes"
            dislike_key = f"rgcbot:quote:{quote_id}:dislikes"
            likes = await redis.scard(like_key)
            dislikes = await redis.scard(dislike_key)
            return likes, dislikes
        except Exception:
            return 0, 0

    @classmethod
    async def check_and_trigger_quote_popup(
        cls,
        bot: Bot,
        session: AsyncSession,
        chat_id: int,
    ):
        if chat_id >= 0:
            return

        try:
            redis = await redis_manager.get_client()
            cd_key = f"rgcbot:quote_popup_cd:{chat_id}"
            if await redis.exists(cd_key):
                return

            cnt_key = f"rgcbot:quote_popup_cnt:{chat_id}"
            msg_count = await redis.incr(cnt_key)

            if msg_count >= 50 and random.random() < 0.25:
                await redis.delete(cnt_key)
                await redis.setex(cd_key, 1800, "1")

                quote = await cls.get_random_quote(session, chat_id)
                if quote:
                    likes, dislikes = await cls.get_quote_reactions(quote.id)
                    kb = get_quote_reaction_keyboard(quote.id, likes=likes, dislikes=dislikes)
                    await bot.send_sticker(
                        chat_id=chat_id,
                        sticker=quote.file_id,
                        reply_markup=kb,
                    )
        except Exception as e:
            logger.debug(f"Random quote popup note: {e}")
