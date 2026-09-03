import io
import math
from typing import Optional, Tuple
from aiogram import Bot
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from loguru import logger


class ShipImageService:
    @classmethod
    async def fetch_user_avatar(cls, bot: Bot, user_id: int) -> Optional[Image.Image]:
        """Fetches and decodes the user's latest Telegram profile photo."""
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
        avatar_img: Image.Image, size: int, border_color: Tuple[int, int, int] = (255, 105, 180)
    ) -> Image.Image:
        """Crops an image into a circle with an antialiased glowing border."""
        avatar = avatar_img.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)

        # High-res mask for antialiasing
        scale = 4
        mask_size = (size * scale, size * scale)
        mask = Image.new("L", mask_size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, mask_size[0] - 1, mask_size[1] - 1), fill=255)
        mask = mask.resize((size, size), Image.Resampling.LANCZOS)

        circular_avatar = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        circular_avatar.paste(avatar, (0, 0), mask=mask)

        # Border ring
        border_thickness = 4
        ring = Image.new(
            "RGBA", (size + border_thickness * 2, size + border_thickness * 2), (0, 0, 0, 0)
        )
        ring_draw = ImageDraw.Draw(ring)
        ring_draw.ellipse(
            (0, 0, size + border_thickness * 2 - 1, size + border_thickness * 2 - 1),
            outline=(*border_color, 255),
            width=border_thickness,
        )

        # Compose
        res = Image.new(
            "RGBA", (size + border_thickness * 2, size + border_thickness * 2), (0, 0, 0, 0)
        )
        res.paste(circular_avatar, (border_thickness, border_thickness), mask=mask)
        res.alpha_composite(ring)
        return res

    @staticmethod
    def _create_fallback_avatar(
        name: str, size: int, bg_color: Tuple[int, int, int] = (180, 40, 100)
    ) -> Image.Image:
        """Generates a stylish initial-based avatar if user has no PFP."""
        img = Image.new("RGB", (size, size), bg_color)
        draw = ImageDraw.Draw(img)
        initial = (name[0] if name else "?").upper()

        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", size // 2)
        except Exception:
            try:
                font = ImageFont.truetype("arial.ttf", size // 2)
            except Exception:
                font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), initial, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text(((size - w) // 2, (size - h) // 2 - 5), initial, fill=(255, 255, 255), font=font)
        return img

    @classmethod
    def generate_ship_card(
        cls,
        user1_name: str,
        user2_name: str,
        user1_img: Optional[Image.Image],
        user2_img: Optional[Image.Image],
        percentage: int,
        ship_name: str,
    ) -> io.BytesIO:
        """
        Generates a premium landscape romance card (1000x520) with avatars,
        glowing heart with compatibility percentage, vignette effect, and sleek framing.
        """
        W, H = 1000, 520
        # 1. Base Gradient Canvas (Deep midnight purple to vivid romantic magenta)
        base = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        draw = ImageDraw.Draw(base)

        for y in range(H):
            ratio = y / H
            # Smooth vertical gradient: Top (#1C081F) to Center (#4A0E38) to Bottom (#1C081F)
            center_dist = 1.0 - abs(ratio - 0.5) * 2
            r = int(28 + center_dist * 55)
            g = int(8 + center_dist * 18)
            b = int(35 + center_dist * 40)
            draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

        # 2. Radial Pink Glow in Center
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        center_x, center_y = W // 2, H // 2 + 10
        glow_radius = 220
        for i in range(glow_radius, 0, -10):
            alpha = int(40 * (1 - i / glow_radius))
            glow_draw.ellipse(
                (center_x - i, center_y - i, center_x + i, center_y + i),
                fill=(255, 70, 140, alpha),
            )
        base = Image.alpha_composite(base, glow)

        # 3. Vignette Shadow around borders
        vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        v_draw = ImageDraw.Draw(vignette)
        margin = 60
        for m in range(margin, 0, -5):
            alpha = int(120 * (1 - m / margin))
            v_draw.rectangle((0, 0, W, m), fill=(0, 0, 0, alpha))
            v_draw.rectangle((0, H - m, W, H), fill=(0, 0, 0, alpha))
            v_draw.rectangle((0, 0, m, H), fill=(0, 0, 0, alpha))
            v_draw.rectangle((W - m, 0, W, H), fill=(0, 0, 0, alpha))
        base = Image.alpha_composite(base, vignette)

        # 4. Fine Rose-Gold Inset Border
        border_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        b_draw = ImageDraw.Draw(border_layer)
        inset = 18
        b_draw.rounded_rectangle(
            (inset, inset, W - inset, H - inset),
            radius=16,
            outline=(255, 140, 190, 160),
            width=2,
        )
        base = Image.alpha_composite(base, border_layer)

        # 5. Prepare Avatars
        av_size = 170
        pfp1 = (
            user1_img
            if user1_img
            else cls._create_fallback_avatar(user1_name, av_size, (190, 45, 110))
        )
        pfp2 = (
            user2_img
            if user2_img
            else cls._create_fallback_avatar(user2_name, av_size, (140, 35, 160))
        )

        av1_circ = cls._create_circular_avatar(pfp1, av_size, (255, 105, 180))
        av2_circ = cls._create_circular_avatar(pfp2, av_size, (255, 105, 180))

        av1_x, av1_y = 120, 145
        av2_x, av2_y = W - 120 - av2_circ.width, 145

        # Drop shadow for avatars
        shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow_layer)
        s_offset = 6
        s_draw.ellipse(
            (
                av1_x + s_offset,
                av1_y + s_offset,
                av1_x + av1_circ.width + s_offset,
                av1_y + av1_circ.height + s_offset,
            ),
            fill=(0, 0, 0, 110),
        )
        s_draw.ellipse(
            (
                av2_x + s_offset,
                av2_y + s_offset,
                av2_x + av2_circ.width + s_offset,
                av2_y + av2_circ.height + s_offset,
            ),
            fill=(0, 0, 0, 110),
        )
        base = Image.alpha_composite(base, shadow_layer)

        base.alpha_composite(av1_circ, (av1_x, av1_y))
        base.alpha_composite(av2_circ, (av2_x, av2_y))

        # 6. Draw Center Glowing Heart Badge with Percentage
        heart_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        h_draw = ImageDraw.Draw(heart_layer)

        # Draw smooth polygon heart in center
        hx, hy = W // 2, 225
        h_size = 75

        # High quality heart curve points
        points = []
        for t in [i * 0.05 for i in range(0, 126)]:
            x = 16 * (math.sin(t) ** 3)
            y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            points.append((hx + x * (h_size / 16), hy + y * (h_size / 16)))

        # Outer heart glow
        h_draw.polygon(points, fill=(255, 45, 115, 235), outline=(255, 180, 220, 255))
        base = Image.alpha_composite(base, heart_layer)

        # 7. Typography (Header, Names, Percentage, Ship Name)
        text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        t_draw = ImageDraw.Draw(text_layer)

        try:
            font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
            font_pct = ImageFont.truetype("DejaVuSans-Bold.ttf", 44)
            font_names = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
            font_ship = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
            font_sub = ImageFont.truetype("DejaVuSans.ttf", 16)
        except Exception:
            try:
                font_title = ImageFont.truetype("arial.ttf", 22)
                font_pct = ImageFont.truetype("arial.ttf", 44)
                font_names = ImageFont.truetype("arial.ttf", 24)
                font_ship = ImageFont.truetype("arial.ttf", 26)
                font_sub = ImageFont.truetype("arial.ttf", 16)
            except Exception:
                font_title = ImageFont.load_default()
                font_pct = ImageFont.load_default()
                font_names = ImageFont.load_default()
                font_ship = ImageFont.load_default()
                font_sub = ImageFont.load_default()

        # Title at Top
        title_text = "✦ MATCHMAKING RADAR ✦"
        t_box = t_draw.textbbox((0, 0), title_text, font=font_title)
        t_draw.text(
            ((W - (t_box[2] - t_box[0])) // 2, 45),
            title_text,
            fill=(255, 200, 225, 240),
            font=font_title,
        )

        # Percentage Text inside Heart
        pct_text = f"{percentage}%"
        p_box = t_draw.textbbox((0, 0), pct_text, font=font_pct)
        pw = p_box[2] - p_box[0]
        ph = p_box[3] - p_box[1]
        t_draw.text(
            ((W - pw) // 2 + 2, hy - (ph // 2) - 8 + 2),
            pct_text,
            fill=(80, 0, 30, 200),
            font=font_pct,
        )
        t_draw.text(
            ((W - pw) // 2, hy - (ph // 2) - 8), pct_text, fill=(255, 255, 255, 255), font=font_pct
        )

        # User 1 Name below left avatar
        u1_name = user1_name[:14]
        u1_box = t_draw.textbbox((0, 0), u1_name, font=font_names)
        u1_w = u1_box[2] - u1_box[0]
        u1_center = av1_x + (av1_circ.width // 2)
        t_draw.text(
            (u1_center - (u1_w // 2), av1_y + av1_circ.height + 15),
            u1_name,
            fill=(255, 240, 250, 255),
            font=font_names,
        )

        # User 2 Name below right avatar
        u2_name = user2_name[:14]
        u2_box = t_draw.textbbox((0, 0), u2_name, font=font_names)
        u2_w = u2_box[2] - u2_box[0]
        u2_center = av2_x + (av2_circ.width // 2)
        t_draw.text(
            (u2_center - (u2_w // 2), av2_y + av2_circ.height + 15),
            u2_name,
            fill=(255, 240, 250, 255),
            font=font_names,
        )

        # Ship Tag & Progress Bar at bottom
        ship_tag = f"💖 {ship_name}"
        s_box = t_draw.textbbox((0, 0), ship_tag, font=font_ship)
        s_w = s_box[2] - s_box[0]
        t_draw.text(((W - s_w) // 2, H - 90), ship_tag, fill=(255, 150, 200, 255), font=font_ship)

        # Subtitle Status
        if percentage >= 85:
            verdict = "Perfect Soulmates • Match Made in Heaven"
        elif percentage >= 60:
            verdict = "Strong Chemistry • High Potential Duo"
        elif percentage >= 40:
            verdict = "Sweet Spark • Growing Friendship"
        else:
            verdict = "Complex Dynamic • Opposites Attract"

        v_box = t_draw.textbbox((0, 0), verdict, font=font_sub)
        v_w = v_box[2] - v_box[0]
        t_draw.text(((W - v_w) // 2, H - 55), verdict, fill=(240, 190, 220, 200), font=font_sub)

        base = Image.alpha_composite(base, text_layer)

        # Convert to RGB JPEG in memory
        output = io.BytesIO()
        base.convert("RGB").save(output, format="JPEG", quality=95)
        output.seek(0)
        return output
