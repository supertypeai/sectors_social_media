from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont

from image_generator.render import SocialImageRenderer, OUTPUT_DIR


class MacroNewsRenderer(SocialImageRenderer):
    FONT_DIR = Path(__file__).resolve().parents[2] / "font"

    FONT_FILES = {
        "bold": "Inter-Bold.ttf",
        "semibold": "Inter-SemiBold.ttf",
        "medium": "Inter-Medium.ttf",
        "regular": "Inter-Regular.ttf",
    }

    CANVAS_WIDTH = 1088
    CANVAS_HEIGHT = 1928
    LEFT_INSET = 113
    RIGHT_INSET = 113
    CONTENT_TOP = 195
    CONTENT_BOTTOM = 1680

    SCALE = CANVAS_WIDTH / 1080

    INK = (26, 26, 32)
    INK_SOFT = (58, 58, 70)
    INK_SECONDARY = (74, 74, 85)
    MUTED = (122, 122, 136)
    HAIRLINE = (226, 226, 234)
    HERO_BORDER = (166, 202, 226)
    HERO_DIVIDER = (190, 203, 216)

    ACCENT_BLUE = (37, 101, 145)
    CATEGORY_ORANGE = (242, 153, 66)
    UP_GREEN = (46, 158, 91)
    DOWN_EMBER = (224, 85, 46)

    CARD_FILL = (255, 255, 255, 200)

    TYPE_LABEL = 22
    TYPE_BODY = 30
    TYPE_HEADLINE = 58
    TYPE_HEADLINE_MIN = 38
    TYPE_HERO_VALUE = 72
    TYPE_HERO_MIN = 52
    TYPE_HERO_TEXT = 44
    TYPE_HERO_SUB = 26
    TYPE_BODY_MIN = 22

    def __init__(
        self,
        template_path: str,
        period_label: str,
        output_dir=OUTPUT_DIR,
        render_scale: float = 1.0,
    ):
        render_scale = max(render_scale, 1.0)
        self.CANVAS_WIDTH = round(type(self).CANVAS_WIDTH * render_scale)
        self.CANVAS_HEIGHT = round(type(self).CANVAS_HEIGHT * render_scale)
        self.LEFT_INSET = round(type(self).LEFT_INSET * render_scale)
        self.RIGHT_INSET = round(type(self).RIGHT_INSET * render_scale)
        self.CONTENT_TOP = round(type(self).CONTENT_TOP * render_scale)
        self.CONTENT_BOTTOM = round(type(self).CONTENT_BOTTOM * render_scale)
        self.SCALE = self.CANVAS_WIDTH / 1080

        template = Image.open(template_path).convert("RGBA")
        
        if template.size != (self.CANVAS_WIDTH, self.CANVAS_HEIGHT):
            template = template.resize(
                (self.CANVAS_WIDTH, self.CANVAS_HEIGHT),
                Image.Resampling.LANCZOS,
            )

        self._template = template
        self._period_label = period_label
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}

    def _scaled(self, value: float) -> int:
        return round(value * self.SCALE)

    @property
    def _content_width(self) -> int:
        return self.CANVAS_WIDTH - self.LEFT_INSET - self.RIGHT_INSET

    def _font(self, weight: str, size: int) -> ImageFont.FreeTypeFont:
        key = (weight, size)

        if key not in self._font_cache:
            path = self.FONT_DIR / self.FONT_FILES[weight]
            self._font_cache[key] = ImageFont.truetype(str(path), size)

        return self._font_cache[key]

    @staticmethod
    def _text_width(
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
    ) -> int:
        left, _, right, _ = draw.textbbox((0, 0), text, font=font)
        return right - left

    @staticmethod
    def _glyph_height(font: ImageFont.FreeTypeFont, text: str) -> int:
        _, top, _, bottom = font.getbbox(text)
        return bottom - top

    def _wrap_lines(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
    ) -> list[str]:
        words = text.split()
        lines = []
        current = ""

        for word in words:
            candidate = word if not current else f"{current} {word}"

            if self._text_width(draw, candidate, font) <= max_width:
                current = candidate

            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        return lines

    def _wrap_sentence_blocks(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
    ) -> list[list[str]]:
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", text.strip())
            if sentence.strip()
        ]

        if not sentences:
            return []

        return [
            self._wrap_lines(draw, sentence, font, max_width)
            for sentence in sentences
        ]

    def _fit_single_line(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        weight: str,
        max_size: int,
        min_size: int,
        max_width: int,
    ) -> ImageFont.FreeTypeFont:
        for size in range(max_size, min_size - 1, -1):
            font = self._font(weight, size)

            if self._text_width(draw, text, font) <= max_width:
                return font

        return self._font(weight, min_size)

    def _direction_color(self, direction: str | None) -> tuple[int, int, int]:
        if direction in ("up", "BULLISH"):
            return self.UP_GREEN

        if direction in ("down", "BEARISH"):
            return self.DOWN_EMBER

        return self.ACCENT_BLUE

    @staticmethod
    def _is_long_text_hero(value: str) -> bool:
        return any(character.isalpha() for character in value)
    
    def _draw_pill(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        label: str,
        border_color: tuple[int, int, int],
        arrow: str | None = None,
    ) -> int:
        height = self._scaled(50)
        font = self._font("bold", self._scaled(self.TYPE_LABEL))
        inset = self._scaled(24)
        arrow_gap = self._scaled(16) if arrow else 0
        arrow_size = self._scaled(8) if arrow else 0

        label_width = self._text_width(draw, label, font)
        pill_width = inset * 2 + label_width + arrow_gap + arrow_size
        radius = height // 2

        draw.rounded_rectangle(
            [x, y, x + pill_width, y + height],
            radius=radius,
            outline=border_color,
            width=self._scaled(2),
        )

        label_top = font.getbbox(label)[1]
        text_y = y + (height - self._glyph_height(font, label)) // 2 - label_top
        draw.text((x + inset, text_y), label, font=font, fill=border_color)

        if arrow:
            ax = x + inset + label_width + arrow_gap
            ay = y + height // 2
            half = arrow_size

            if arrow == "down":
                points = [
                    (ax, ay - half),
                    (ax + half*2, ay - half),
                    (ax + half, ay + half),
                ]
            else:
                points = [
                    (ax + half, ay - half),
                    (ax, ay + half),
                    (ax + half*2, ay + half),
                ]

            draw.polygon(points, fill=border_color)

        return x + pill_width

    def _draw_tracked_label(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        text: str,
        font: ImageFont.FreeTypeFont,
        fill: tuple[int, int, int],
        tracking: int,
    ) -> None:
        cursor_x = x

        for character in text:
            draw.text((cursor_x, y), character, font=font, fill=fill)
            cursor_x += self._text_width(draw, character, font) + tracking

    def _draw_inline_arrow(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        center_y: int,
        color: tuple[int, int, int],
        direction: str | None,
    ) -> int:
        size = self._scaled(8)
        arrow = "down" if direction in ("down", "BEARISH") else "up"

        if direction is None:
            arrow = "down"

        if arrow == "down":
            points = [
                (x, center_y - size),
                (x + size * 2, center_y - size),
                (x + size, center_y + size),
            ]
        else:
            points = [
                (x + size, center_y - size),
                (x, center_y + size),
                (x + size * 2, center_y + size),
            ]

        draw.polygon(points, fill=color)
        return x + size * 2

    def render_top_block(
        self,
        draw: ImageDraw.ImageDraw,
        data: dict,
        left: int,
        top_start: int,
        headline_lines: list[str],
        headline_font: ImageFont.FreeTypeFont,
        headline_line_height: int,
        eyebrow_offset: int,
        headline_offset: int,
        direction_color: tuple[int, int, int],
    ) -> None:
        category_pill = data.get("category_pill", "")
        direction = data.get("direction")

        category_right = self._draw_pill(
            draw, left, top_start,
            category_pill.upper(), self.CATEGORY_ORANGE,
        )

        next_pill_x = category_right + self._scaled(16)

        source = data.get("source")
        if source:
            next_pill_x = self._draw_pill(
                draw, next_pill_x, top_start,
                source.upper(), self.MUTED,
            ) + self._scaled(16)

        if direction:
            arrow = "down" if direction in ("down", "BEARISH") else "up"

            self._draw_pill(
                draw,
                next_pill_x,
                top_start,
                direction.upper(),
                direction_color,
                arrow=arrow,
            )

        eyebrow_font = self._font("medium", self._scaled(self.TYPE_LABEL))

        draw.text(
            (left, top_start + eyebrow_offset),
            self._period_label,
            font=eyebrow_font,
            fill=self.ACCENT_BLUE,
        )

        for i, line in enumerate(headline_lines):
            draw.text(
                (left, top_start + headline_offset + i * headline_line_height),
                line,
                font=headline_font,
                fill=self.INK,
            )

    def render_middle_block(
        self,
        draw: ImageDraw.ImageDraw,
        data: dict,
        left: int,
        middle_start: int,
        hero_value_font: ImageFont.FreeTypeFont,
        hero_label_font: ImageFont.FreeTypeFont,
        hero_block_height: int,
        label_to_box: int,
        hero_box_height: int,
        body_blocks: list[list[str]],
        body_font: ImageFont.FreeTypeFont,
        body_line_height: int,
        body_sentence_gap: int,
        hero_to_body_gap: int,
        direction_color: tuple[int, int, int],
    ) -> None:
        hero_label = data.get("hero_label", "")
        hero_value = data.get("hero_value", "")
        hero_sub = data.get("hero_sub")
        direction = data.get("direction")

        self._draw_tracked_label(
            draw, left, middle_start,
            hero_label.upper(), hero_label_font,
            self.MUTED, self._scaled(2),
        )

        hero_box_top = middle_start + label_to_box
        hero_box_bottom = hero_box_top + hero_box_height
        hero_box_radius = self._scaled(14)
        hero_box_pad_x = self._scaled(42)
        hero_box_right_pad = self._scaled(30)

        hero_sub_font = self._font("regular", self._scaled(self.TYPE_HERO_SUB))
        sub_area_min_width = self._scaled(300) if hero_sub else 0
        value_width = self._text_width(draw, hero_value, hero_value_font)
        value_area_width = min(
            max(value_width + hero_box_pad_x * 2, self._scaled(405)),
            self._content_width - sub_area_min_width,
        )
        divider_x = left + value_area_width
        right_edge = left + self._content_width

        draw.rounded_rectangle(
            [left, hero_box_top, right_edge, hero_box_bottom],
            radius=hero_box_radius,
            fill=(255, 255, 255, 76),
            outline=self.HERO_BORDER,
            width=self._scaled(1),
        )

        value_top = hero_value_font.getbbox(hero_value)[1]
        value_y = (
            hero_box_top
            + (hero_box_height - self._glyph_height(hero_value_font, hero_value)) // 2
            - value_top
        )

        value_x = left + (value_area_width - value_width) // 2
        draw.text(
            (value_x, value_y),
            hero_value,
            font=hero_value_font,
            fill=direction_color,
        )

        if hero_sub:
            draw.line(
                [
                    (divider_x, hero_box_top + self._scaled(26)),
                    (divider_x, hero_box_bottom - self._scaled(26)),
                ],
                fill=self.HERO_DIVIDER,
                width=self._scaled(1),
            )

            sub_left = divider_x + self._scaled(54)
            arrow_x = divider_x + self._scaled(28)
            arrow_reserved_right = arrow_x + self._scaled(16)
            sub_left = max(sub_left, arrow_reserved_right + self._scaled(16))
            
            sub_width = min(
                right_edge - sub_left - hero_box_right_pad,
                self._scaled(292),
            )

            sub_lines = self._wrap_lines(
                draw,
                hero_sub,
                hero_sub_font,
                sub_width,
            )

            sub_line_height = self._scaled(self.TYPE_HERO_SUB) + self._scaled(8)
            sub_total_height = len(sub_lines) * sub_line_height
            sub_y = hero_box_top + (hero_box_height - sub_total_height) // 2
            
            self._draw_inline_arrow(
                draw,
                arrow_x,
                sub_y + sub_line_height // 2,
                direction_color,
                direction,
            )

            for line in sub_lines:
                draw.text(
                    (sub_left, sub_y),
                    line,
                    font=hero_sub_font,
                    fill=self.INK_SECONDARY,
                )

                sub_y += sub_line_height

        body_y = middle_start + hero_block_height + hero_to_body_gap

        for block_index, block_lines in enumerate(body_blocks):
            for line in block_lines:
                draw.text((left, body_y), line, font=body_font, fill=self.INK_SOFT)
                body_y += body_line_height

            if block_index < len(body_blocks) - 1:
                body_y += body_sentence_gap

    def render_insight_card(
        self,
        overlay: Image.Image,
        left: int,
        right_edge: int,
        card_top: int,
        card_bottom: int,
        card_padding: int,
        insight_blocks: list[list[str]],
        card_header_font: ImageFont.FreeTypeFont,
        card_value_font: ImageFont.FreeTypeFont,
        card_header_block: int,
        card_value_line_height: int,
        card_value_sentence_gap: int,
    ) -> None:
        card_layer = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
        card_draw = ImageDraw.Draw(card_layer)

        card_draw.rounded_rectangle(
            [left, card_top, right_edge, card_bottom],
            radius=self._scaled(22),
            fill=self.CARD_FILL,
            outline=self.HAIRLINE,
            width=self._scaled(1),
        )

        overlay.alpha_composite(card_layer)
        draw = ImageDraw.Draw(overlay)

        card_text_x = left + card_padding
        card_text_y = card_top + card_padding

        self._draw_tracked_label(
            draw, card_text_x, card_text_y,
            "WHY IT MATTERS", card_header_font,
            self.MUTED, self._scaled(2),
        )

        underline_y = card_text_y + self._scaled(self.TYPE_LABEL) + self._scaled(20)
        draw.line(
            [
                (card_text_x, underline_y),
                (card_text_x + self._scaled(72), underline_y),
            ],
            fill=self.INK,
            width=self._scaled(4),
        )

        card_text_y += card_header_block

        for block_index, block_lines in enumerate(insight_blocks):
            for line in block_lines:
                draw.text(
                    (card_text_x, card_text_y),
                    line,
                    font=card_value_font,
                    fill=self.INK_SOFT,
                )

                card_text_y += card_value_line_height

            if block_index < len(insight_blocks) - 1:
                card_text_y += card_value_sentence_gap

    def render(
        self,
        data: dict,
        filename: str,
    ) -> Path:
        base = self._template.copy()
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        left = self.LEFT_INSET
        right_edge = self.CANVAS_WIDTH - self.RIGHT_INSET
        content_width = self._content_width

        direction = data.get("direction")
        direction_color = self._direction_color(direction)

        # Headline (auto-shrink to <= 3 lines)
        headline_text = " ".join(data.get("headline_lines", []))
        headline_size = self._scaled(self.TYPE_HEADLINE)
        min_headline_size = self._scaled(self.TYPE_HEADLINE_MIN)
        headline_font = self._font("bold", headline_size)
        headline_lines = self._wrap_lines(draw, headline_text, headline_font, content_width)

        while len(headline_lines) > 3 and headline_size > min_headline_size:
            headline_size -= 2
            headline_font = self._font("bold", headline_size)
            headline_lines = self._wrap_lines(draw, headline_text, headline_font, content_width)

        headline_line_height = headline_size + self._scaled(12)

        # Top-block geometry
        pill_height = self._scaled(50)
        eyebrow_offset = pill_height + self._scaled(42)
        headline_offset = eyebrow_offset + self._scaled(48)
        top_height = headline_offset + len(headline_lines) * headline_line_height

        # Hero metrics
        hero_value = data.get("hero_value", "")
        hero_label_font = self._font("medium", self._scaled(self.TYPE_LABEL))
        hero_value_font = self._fit_single_line(
            draw, hero_value, "semibold",
            max_size=self._scaled(self.TYPE_HERO_TEXT),
            min_size=self._scaled(self.TYPE_HERO_TEXT),
            max_width=round(content_width * 0.46),
        )

        label_to_box = self._scaled(38)
        hero_box_height = self._scaled(124)
        hero_block_height = label_to_box + hero_box_height

        # Body metrics
        hero_to_body_gap = self._scaled(48)
        body_font = self._font("regular", self._scaled(self.TYPE_BODY))
        body_line_height = self._scaled(self.TYPE_BODY) + self._scaled(22)
        body_sentence_gap = self._scaled(14)
        
        body_blocks = self._wrap_sentence_blocks(
            draw, data.get("body", ""), body_font, content_width,
        )

        body_text_height = (
            sum(len(block) for block in body_blocks) * body_line_height
            + max(len(body_blocks) - 1, 0) * body_sentence_gap
        )

        middle_height = hero_block_height + hero_to_body_gap + body_text_height

        # Insight card metrics
        card_padding = self._scaled(34)
        card_header_font = self._font("medium", self._scaled(self.TYPE_LABEL))
        card_value_font = body_font
        card_inner_width = content_width - card_padding * 2
        
        insight_blocks = self._wrap_sentence_blocks(
            draw, data.get("insight", ""), card_value_font, card_inner_width,
        )

        card_value_line_height = body_line_height
        card_value_sentence_gap = body_sentence_gap
        card_header_block = self._scaled(self.TYPE_LABEL) + self._scaled(52)
        
        card_height = (
            card_padding * 2
            + card_header_block
            + sum(len(block) for block in insight_blocks) * card_value_line_height
            + max(len(insight_blocks) - 1, 0) * card_value_sentence_gap
        )

        # Vertical distribution
        band = self.CONTENT_BOTTOM - self.CONTENT_TOP
        free = band - (top_height + middle_height + card_height)

        min_gap = self._scaled(48)

        while free < (3 * min_gap) and body_font.size > self._scaled(self.TYPE_BODY_MIN):
            body_font = self._font("regular", body_font.size - 1)
            body_line_height = body_font.size + self._scaled(22)
            
            body_blocks = self._wrap_sentence_blocks(
                draw, data.get("body", ""), body_font, content_width,
            )

            body_text_height = (
                sum(len(block) for block in body_blocks) * body_line_height
                + max(len(body_blocks) - 1, 0) * body_sentence_gap
            )
            
            middle_height = hero_block_height + hero_to_body_gap + body_text_height
            card_value_font = body_font
            
            insight_blocks = self._wrap_sentence_blocks(
                draw, data.get("insight", ""), card_value_font, card_inner_width,
            )

            card_value_line_height = body_line_height
            card_height = (
                card_padding * 2
                + card_header_block
                + sum(len(block) for block in insight_blocks) * card_value_line_height
                + max(len(insight_blocks) - 1, 0) * card_value_sentence_gap
            )

            free = band - (top_height + middle_height + card_height)

        free = max(free, 0)
        header_gap = min(self._scaled(48), free // 4)
        internal_gap = min(self._scaled(75), (free - header_gap) // 2)

        top_nudge = self._scaled(30)
        content_nudge = self._scaled(25)

        top_start = self.CONTENT_TOP + header_gap + top_nudge
        middle_start = self.CONTENT_TOP + header_gap + top_height + internal_gap + content_nudge

        card_nudge = self._scaled(24)
        desired_card_gap = self._scaled(64)
        max_card_top = self.CONTENT_BOTTOM - card_height - self._scaled(8)
        pinned_card_top = self.CONTENT_BOTTOM - card_height - card_nudge
        content_card_top = middle_start + middle_height + desired_card_gap

        card_top = min(max_card_top, max(pinned_card_top, content_card_top))
        card_bottom = card_top + card_height

        self.render_top_block(
            draw=draw,
            data=data,
            left=left,
            top_start=top_start,
            headline_lines=headline_lines,
            headline_font=headline_font,
            headline_line_height=headline_line_height,
            eyebrow_offset=eyebrow_offset,
            headline_offset=headline_offset,
            direction_color=direction_color,
        )

        self.render_middle_block(
            draw=draw,
            data=data,
            left=left,
            middle_start=middle_start,
            hero_value_font=hero_value_font,
            hero_label_font=hero_label_font,
            hero_block_height=hero_block_height,
            label_to_box=label_to_box,
            hero_box_height=hero_box_height,
            body_blocks=body_blocks,
            body_font=body_font,
            body_line_height=body_line_height,
            body_sentence_gap=body_sentence_gap,
            hero_to_body_gap=hero_to_body_gap,
            direction_color=direction_color,
        )

        self.render_insight_card(
            overlay=overlay,
            left=left,
            right_edge=right_edge,
            card_top=card_top,
            card_bottom=card_bottom,
            card_padding=card_padding,
            insight_blocks=insight_blocks,
            card_header_font=card_header_font,
            card_value_font=card_value_font,
            card_header_block=card_header_block,
            card_value_line_height=card_value_line_height,
            card_value_sentence_gap=card_value_sentence_gap,
        )

        result = Image.alpha_composite(base, overlay).convert("RGB")

        return self._save(result, filename)
