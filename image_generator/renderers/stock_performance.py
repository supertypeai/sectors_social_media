from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from image_generator.render import SocialImageRenderer, OUTPUT_DIR

import math
import re


class StockPerformanceRenderer(SocialImageRenderer):
    DESIGN_CANVAS_WIDTH = 1080
    INK_GLASS_FILL = (20, 20, 24, 86)
    HAIRLINE = "#28282e"
    FONT_DIR = Path(__file__).resolve().parents[2] / "font"

    COLORS = {
        "lime": "#A6D94E",
        "ember": "#F46D43",
        "orange": "#F29942",
        "blue": "#3288BD",
        "white": "#FFFFFF",
        "bone": "#F0EBE0",
        "soft": "#C8C8D8",
        "muted": "#9090a8",
        "muted_soft": "#8888a0",
    }

    TOKEN_PALETTE = [
        (218, 54, 53),
        (42, 113, 201),
        (46, 155, 86),
        (235, 138, 38),
        (222, 184, 70),
        (28, 151, 157),
        (135, 78, 168),
        (78, 173, 212),
    ]

    WEIGHT_MAP = {
        "Bold": "Inter-Bold.ttf",
        "SemiBold": "Inter-SemiBold.ttf",
        "Medium": "Inter-Medium.ttf",
        "Regular": "Inter-Regular.ttf",
    }

    def __init__(
        self,
        template_path: Path | None = None,
        output_dir: Path = OUTPUT_DIR,
        render_scale: float = 1.0,
        per_side: int = 10,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        background_dir = Path(__file__).resolve().parents[2] / "background"
        template_path = template_path or background_dir / "volume_spike.png"
        self._template = Image.open(template_path).convert("RGBA")
        self._width, self._height = self._template.size
        self._scale = (self._width / self.DESIGN_CANVAS_WIDTH) * render_scale
        self._per_side = per_side
        self._outer_margin = self._spec(76)
        self._font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}

    def _spec(self, value: float) -> int:
        return round(value * self._scale)

    def _font(self, weight: str, design_size: int) -> ImageFont.FreeTypeFont:
        size = max(1, self._spec(design_size))
        key = (weight, size)

        if key not in self._font_cache:
            path = self.FONT_DIR / self.WEIGHT_MAP.get(weight, "Inter-Regular.ttf")
            if path.exists():
                self._font_cache[key] = ImageFont.truetype(str(path), size)
            else:
                self._font_cache[key] = ImageFont.load_default()

        return self._font_cache[key]

    @staticmethod
    def _clean_company_name(name: str) -> str:
        name = re.sub(r"\bPT\.?\s*", "", str(name), flags=re.IGNORECASE)
        name = re.sub(r",?\s*Tbk\.?\s*$", "", name, flags=re.IGNORECASE)
        name = re.sub(r"\s*\(Persero\)\s*", " ", name, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", name).strip()

    @staticmethod
    def _symbol(record: dict) -> str:
        return str(record.get("symbol", "")).upper().split(".")[0]

    @staticmethod
    def _format_close_price(value) -> str:
        try:
            price = float(value)
        except (TypeError, ValueError):
            return ""

        if not math.isfinite(price):
            return ""

        return f"IDR {price:,.0f}"

    @staticmethod
    def _place_center(canvas: Image.Image, layer: Image.Image, center: tuple[int, int]) -> None:
        canvas.alpha_composite(layer, (round(center[0] - layer.width / 2), round(center[1] - layer.height / 2)))

    @staticmethod
    def _radial_disc(size: int, base_rgb: tuple[int, int, int]) -> Image.Image:
        disc = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        center = (size - 1) / 2
        radius = center
        pixels = disc.load()

        for y in range(size):
            for x in range(size):
                dx = (x - center) / radius
                dy = (y - center) / radius
                distance = math.sqrt(dx * dx + dy * dy)
                if distance > 1:
                    continue

                highlight = max(0, 1 - math.sqrt((dx + 0.3) ** 2 + (dy + 0.48) ** 2))
                shade = 1 - distance * 0.33
                factor = max(0.42, min(1.34, shade + highlight * 0.44))
                pixels[x, y] = tuple(max(0, min(255, round(c * factor))) for c in base_rgb) + (255,)

        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        disc.putalpha(mask)
        return disc

    def _return_color(self, value: float) -> str:
        return self.COLORS["lime"] if value >= 0 else self.COLORS["ember"]

    def _fit_font(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        weight: str,
        start_size: int,
        min_size: int,
        max_width: int,
    ) -> ImageFont.FreeTypeFont:
        for size in range(round(start_size), min_size - 1, -1):
            font = self._font(weight, size)
            if draw.textlength(text, font=font) <= max_width:
                return font

        return self._font(weight, min_size)

    def _draw_centered_text(
        self,
        draw: ImageDraw.ImageDraw,
        center_x: int,
        y: int,
        text: str,
        font: ImageFont.FreeTypeFont,
        fill: str | tuple[int, int, int, int],
    ) -> None:
        draw.text((center_x - draw.textlength(text, font=font) / 2, y), text, font=font, fill=fill)

    def _draw_pill(
        self,
        canvas: Image.Image,
        x: int,
        y: int,
        label: str,
        border: str,
        arrow: str | None = None,
    ) -> int:
        draw = ImageDraw.Draw(canvas)
        font = self._font("Bold", 22)
        height = self._spec(48)
        text_width = round(draw.textlength(label, font=font))
        width = text_width + self._spec(44) + (self._spec(30) if arrow else 0)

        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(overlay).rounded_rectangle(
            (x, y, x + width, y + height), radius=height // 2, fill=self.INK_GLASS_FILL
        )
        canvas.alpha_composite(overlay)

        draw.rounded_rectangle(
            (x, y, x + width, y + height),
            radius=height // 2,
            outline=border,
            width=self._spec(2),
        )

        text_y = y + (height - font.size) // 2 - self._spec(1)
        draw.text((x + self._spec(22), text_y), label, font=font, fill=self.COLORS["white"])

        if arrow:
            ax = x + self._spec(22) + text_width + self._spec(18)
            ay = y + height // 2
            size = self._spec(7)
            if arrow == "up":
                points = [(ax + size, ay - size), (ax, ay + size), (ax + size * 2, ay + size)]
            else:
                points = [(ax, ay - size), (ax + size * 2, ay - size), (ax + size, ay + size)]
            draw.polygon(points, fill=border)

        return x + width

    def _logo_image(self, symbol: str, size: int) -> Image.Image:
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        self._logo(canvas, (0, 0), symbol, size, extension="png")
        return canvas

    def _token_image(
        self,
        symbol: str,
        size: int,
        base_rgb: tuple[int, int, int],
        tilt_degrees: float = 0,
    ) -> Image.Image:
        depth = round(size * 0.15)
        pad = round(size * 0.2)
        token = Image.new("RGBA", (size + pad * 2, size + depth + pad * 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(token)
        left, top = pad, pad
        right, bottom = left + size, top + size

        shadow = Image.new("RGBA", token.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).ellipse(
            (left + size * 0.07, bottom + depth * 0.34, right - size * 0.07, bottom + depth * 1.18),
            fill=(0, 0, 0, 120),
        )
        token.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(round(size * 0.055))))

        for offset in range(depth, 0, -2):
            factor = 0.50 + (offset / depth) * 0.20
            side = tuple(round(c * factor) for c in base_rgb)
            draw.ellipse((left, top + offset, right, bottom + offset), fill=side + (255,))

        top_disc = self._radial_disc(size, base_rgb)
        logo_size = round(size * 0.64)
        logo = self._logo_image(symbol, logo_size)

        logo_shadow = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
        ImageDraw.Draw(logo_shadow).ellipse((3, 5, logo_size - 3, logo_size - 1), fill=(0, 0, 0, 88))
        top_disc.alpha_composite(
            logo_shadow.filter(ImageFilter.GaussianBlur(max(1, round(size * 0.014)))),
            ((size - logo_size) // 2, (size - logo_size) // 2 + round(size * 0.014)),
        )
        top_disc.alpha_composite(logo, ((size - logo_size) // 2, (size - logo_size) // 2))

        rim = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        rim_draw = ImageDraw.Draw(rim)
        rim_draw.ellipse((2, 2, size - 3, size - 3), outline=(255, 255, 255, 125), width=max(2, size // 38))
        rim_draw.ellipse((10, 11, size - 11, size - 9), outline=(0, 0, 0, 48), width=max(2, size // 55))
        top_disc.alpha_composite(rim)
        token.alpha_composite(top_disc, (left, top))

        shine = Image.new("RGBA", token.size, (0, 0, 0, 0))
        shine_draw = ImageDraw.Draw(shine)
        shine_draw.arc(
            (left + size * 0.08, top + size * 0.07, right - size * 0.08, bottom - size * 0.1),
            202, 312,
            fill=(255, 255, 255, 116),
            width=max(3, size // 27),
        )
        token.alpha_composite(shine.filter(ImageFilter.GaussianBlur(0.5)))

        if tilt_degrees:
            token = token.rotate(tilt_degrees, resample=Image.Resampling.BICUBIC, expand=True)

        return token

    def _draw_header(
        self,
        canvas: Image.Image,
        index_name: str,
        period_label: str,
        direction: str,
        index_performance: float | None = None,
        day: int = 7,
    ) -> None:
        accent = self.COLORS["lime"] if direction == "gainers" else self.COLORS["ember"]
        draw = ImageDraw.Draw(canvas)
        x = self._outer_margin

        eyebrow = f"{day}-day return"

        if period_label:
            eyebrow = f"{eyebrow} · {period_label}"
        
        draw.text((x, self._spec(118)), eyebrow, font=self._font("Bold", 24), fill=accent)

        title = "index drivers" if direction == "gainers" else "biggest drops"
        title_font = self._fit_font(draw, title.upper(), "Bold", 62, 42, self._width - x * 2)
        draw.text((x, self._spec(180)), title.upper(), font=title_font, fill=self.COLORS["white"])

        index_title = index_name.upper()
        index_font = self._fit_font(draw, index_title, "Bold", 82, 50, self._width - x * 2)
        draw.text((x, self._spec(248)), index_title, font=index_font, fill=accent)

        # subhead = (
        #     f"Top {self._per_side} · {day}d return"
        #     if direction == "gainers"
        #     else f"Bottom {self._per_side} · {day}d return"
        # )

        # draw.text((x, self._spec(344)), subhead, font=self._font("SemiBold", 27), fill=self.COLORS["soft"])

        if index_performance is not None:
            index_color = self.COLORS["lime"] if index_performance >= 0 else self.COLORS["ember"]
            arrow = "up" if index_performance >= 0 else "down"
            
            self._draw_pill(
                canvas, x, self._spec(385),
                f"INDEX  {index_performance:+.1f}%",
                border=index_color,
                arrow=arrow,
            )

    def _draw_token_grid(
        self, canvas: Image.Image, records: list[dict], return_key: str = "return_7d"
    ) -> None:
        draw = ImageDraw.Draw(canvas)

        grid_top = self._spec(580)
        cols = 5 if len(records) >= 9 else 3 if len(records) > 2 else max(1, len(records))
        side_inset = self._spec(64 if cols >= 5 else 150)
        grid_left = self._outer_margin + side_inset
        grid_right = self._width - self._outer_margin - side_inset

        rows = math.ceil(len(records) / cols) if records else 1
        col_gap = (grid_right - grid_left) / max(1, cols - 1)
        row_gap = self._spec(345 if rows <= 2 else 272)
        token_size = self._spec(128 if cols >= 5 else 170 if rows <= 2 else 146)

        label_font = self._font("Bold", 25 if cols >= 5 else 31 if rows <= 2 else 26)
        pct_font = self._font("Bold", 38 if cols >= 5 else 48 if rows <= 2 else 40)
        close_font = self._font("SemiBold", 18 if cols >= 5 else 22 if rows <= 2 else 19)

        for idx, record in enumerate(records):
            row = idx // cols
            col = idx % cols
            
            center = (
                round(grid_left + col_gap * col),
                round(grid_top + row_gap * row),
            )

            symbol = self._symbol(record)
            base_rgb = self.TOKEN_PALETTE[idx % len(self.TOKEN_PALETTE)]
            tilt = -7 + (idx % cols) * 4 + (row * 1.5)
            token = self._token_image(symbol, token_size, base_rgb, tilt_degrees=tilt)
            self._place_center(canvas, token, center)

            ticker_y = center[1] + self._spec(104 if cols >= 5 else 133 if rows <= 2 else 113)
            self._draw_centered_text(draw, center[0], ticker_y, symbol, label_font, self.COLORS["white"])

            value = float(record.get(return_key, 0) or 0)
            pct_text = f"{value:+.1f}%"
            pct_font_fit = self._fit_font(draw, pct_text, "Bold", pct_font.size / self._scale, 30, self._spec(230))
            
            self._draw_centered_text(
                draw, center[0], ticker_y + self._spec(32 if cols >= 5 else 38),
                pct_text, pct_font_fit, self._return_color(value),
            )

            close_text = self._format_close_price(record.get("latest_close"))
            
            if close_text:
                close_y = ticker_y + self._spec(78 if cols >= 5 else 90)
                
                close_font_fit = self._fit_font(
                    draw, close_text, "SemiBold",
                    close_font.size / self._scale, 14,
                    self._spec(210 if cols >= 5 else 260),
                )

                self._draw_centered_text(draw, center[0], close_y, close_text, close_font_fit, self.COLORS["soft"])

    def _draw_summary_strip(
        self, canvas: Image.Image, records: list[dict], direction: str, return_key: str = "return_7d"
    ) -> None:
        if not records:
            return

        draw = ImageDraw.Draw(canvas)
        accent = self.COLORS["lime"] if direction == "gainers" else self.COLORS["ember"]
        left = self._outer_margin
        right = self._width - self._outer_margin
        top = self._height - self._spec(248)
        height = self._spec(120)
        radius = self._spec(22)

        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(overlay).rounded_rectangle(
            (left, top, right, top + height), radius=radius, fill=self.INK_GLASS_FILL
        )
        canvas.alpha_composite(overlay)
        draw.rounded_rectangle(
            (left, top, right, top + height), radius=radius, outline=self.HAIRLINE, width=self._spec(1)
        )

        best = max(records, key=lambda r: abs(float(r.get(return_key, 0) or 0)))
        values = [float(r.get(return_key, 0) or 0) for r in records]
        avg_value = sum(values) / len(values)

        metrics = [
            ("LEADER", self._symbol(best), accent),
            ("AVG MOVE", f"{avg_value:+.1f}%", self.COLORS["orange"]),
            ("COUNT", f"{len(records)} stocks", self.COLORS["blue"]),
        ]

        col_width = (right - left) / 3
        
        for idx, (label, value, color) in enumerate(metrics):
            cx = round(left + col_width * idx + col_width / 2)
            chip_font = self._font("Bold", 16)
            value_font = self._fit_font(draw, value, "Bold", 38, 25, round(col_width - self._spec(34)))
            chip_w = round(draw.textlength(label, font=chip_font)) + self._spec(28)
            chip_h = self._spec(30)
            chip_x = cx - chip_w // 2
            chip_y = top + self._spec(20)
            
            draw.rounded_rectangle(
                (chip_x, chip_y, chip_x + chip_w, chip_y + chip_h),
                radius=chip_h // 2, outline=color, width=self._spec(1),
            )
            
            self._draw_centered_text(draw, cx, chip_y + self._spec(5), label, chip_font, self.COLORS["white"])
            
            self._draw_centered_text(
                draw, cx, top + self._spec(64), value, value_font,
                self.COLORS["bone"] if idx != 1 else color,
            )

    def render(
        self,
        index_name: str,
        records: list[dict],
        filename: str,
        as_of_date: str = "",
        direction: str = "gainers",
        index_performance: float | None = None,
        day: int = 7,
    ) -> Path:
        if direction not in {"gainers", "losers"}:
            raise ValueError("direction must be 'gainers' or 'losers'")

        return_key = f"return_{day}d"
        ranked = sorted(records, key=lambda r: float(r.get(return_key, 0) or 0), reverse=(direction == "gainers"))
        selected = ranked[: self._per_side]

        canvas = self._template.copy()
        self._draw_header(canvas, index_name, as_of_date, direction, index_performance, day)
        self._draw_token_grid(canvas, selected, return_key)

        return self._save(canvas, filename)
