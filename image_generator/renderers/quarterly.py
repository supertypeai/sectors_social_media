from PIL import Image, ImageDraw
from datetime import date 
from pathlib import Path 

from image_generator.render import (
    SocialImageRenderer, 
    COLORS, 
    font, 
    format_price
)


class QuarterlyRenderer(SocialImageRenderer):
    def get_background(self):
        image = self._open("MSCI Rebalancing.png")
        draw = ImageDraw.Draw(image)

        scale = image.width / 1200

        # Footer Block
        draw.rectangle(
            (
                int(40 * scale),
                int(1080 * scale),
                int(1160 * scale),
                int(1385 * scale),
            ),
            fill="#f7f6f5",
        )

        footer_box = (
            int(60 * scale),
            int(1215 * scale),
            int(1140 * scale),
            int(1365 * scale),
        )
        footer_stroke = max(1, int(2 * scale))

        draw.rounded_rectangle(
            footer_box,
            radius=int(32 * scale),
            fill="#f7f6f6",
            outline="#eeeeee",
            width=footer_stroke,
        )
        draw.rectangle(
            (
                footer_box[0],
                footer_box[3] - footer_stroke,
                footer_box[2],
                footer_box[3] + footer_stroke,
            ),
            fill="#f7f6f5",
        )

        return image

    def render_title_section(
        self, 
        data: list[dict], 
        draw: ImageDraw.ImageDraw, 
        image_width: int
    ):
        if 'low' in data: 
            title_tag = 'Lows'
            subtitle_tag = 'lowest'
        
        else: 
            title_tag = 'Highs'
            subtitle_tag = 'high'

        title = f"Quarterly {title_tag}"
        subtitle = f"Stock that reached their {subtitle_tag} price in the last quarter"

        margin = int(image_width * 0.08)
        title_y = 110

        draw.text(
            (margin + 44, title_y),
            title,
            font=font("Inter-Bold.ttf", 80),
            fill=COLORS["orange_deep"],
        )

        draw.text(
            (margin + 44, title_y + 110),
            subtitle,
            font=font("Inter-Italic.ttf", 30),
            fill=COLORS["dark"],
        )

    def render_main_section(
        self,
        draw: ImageDraw.ImageDraw,
        data: list[dict],
        image_width: int,
        image: Image.Image = None,
    ):
        scale = image_width / 1200

        column_count = 4
        row_count = 4
        max_companies = column_count * row_count

        column_width = int(265 * scale)
        margin = int((1200 * scale - column_width * 4) / 2)
        section_start_y = int(325 * scale)

        row_gap = int(8 * scale)
        cell_height = int(210 * scale)
        cell_side_padding = int(2 * scale)
        cell_top_padding = 0

        logo_size = int(52 * scale)

        label_font_obj = font("Inter-Regular.ttf", int(18 * scale))
        value_font_obj = font("Inter-Bold.ttf", int(18 * scale))
        ticker_font_obj = font("Inter-Bold.ttf", int(23 * scale))

        for index, company in enumerate(data[:max_companies]):
            col = index % column_count
            row = index // column_count

            cell_x = margin + col * column_width
            cell_y = section_start_y + row * (cell_height + row_gap)
            cell_center_x = cell_x + column_width // 2

            card_x1 = cell_x + cell_side_padding
            card_y1 = cell_y + cell_top_padding
            card_x2 = cell_x + column_width - cell_side_padding
            card_y2 = cell_y + cell_height - cell_top_padding

            self._card(
                draw,
                (card_x1, card_y1, card_x2, card_y2),
                radius=int(14 * scale),
                fill=COLORS["off_white"],
                outline="#eeeeee",
                width=max(1, int(1 * scale)),
            )

            symbol = company["symbol"].replace(".JK", "")

            logo_x = int(cell_center_x - logo_size / 2)
            logo_y = int(card_y1 + 16 * scale)

            if image is not None:
                self._logo(image, (logo_x, logo_y), symbol, size=logo_size)

            ticker_bbox = draw.textbbox((0, 0), symbol, font=ticker_font_obj)
            ticker_width = ticker_bbox[2] - ticker_bbox[0]

            ticker_y = int(card_y1 + 76 * scale)

            draw.text(
                (cell_center_x - ticker_width / 2, ticker_y),
                symbol,
                font=ticker_font_obj,
                fill=COLORS["heading"],
            )
            
            quarterly_low = company.get("quarterly_low") or {}

            data_rows = [
                ("Close", format_price(quarterly_low.get("latest_close", 0)), COLORS["heading"]),
                ("52w Low", format_price(quarterly_low.get("52w_low", 0)), COLORS["red_deep"]),
                ("52w High", format_price(quarterly_low.get("52w_high", 0)), COLORS["green_deep"]),
            ]

            data_y = int(card_y1 + 125 * scale)
            inner_x = card_x1 + int(12 * scale)
            inner_right = card_x2 - int(12 * scale)
            line_gap = int(25 * scale)

            for label, value, color in data_rows:
                draw.text(
                    (inner_x, data_y),
                    label,
                    font=label_font_obj,
                    fill=COLORS["heading"],
                )

                value_bbox = draw.textbbox((0, 0), value, font=value_font_obj)
                value_width = value_bbox[2] - value_bbox[0]

                draw.text(
                    (inner_right - value_width, data_y),
                    value,
                    font=value_font_obj,
                    fill=color,
                )

                data_y += line_gap

    def render_footer_section(self, draw, image_width: int):
        scale = image_width / 1200

        footer_x = int(110 * scale)
        footer_y = int(1255 * scale)

        draw.text(
            (footer_x, footer_y),
            "Data sourced from Sectors · sectors.app",
            font=font("Inter-Bold.ttf", int(20 * scale)),
            fill=COLORS["orange_deep"],
        )

        draw.text(
            (footer_x, footer_y + int(38 * scale)),
            f"Prices in IDR · Data reflects latest market close on {date.today()}",
            font=font("Inter-Regular.ttf", int(20 * scale)),
            fill=COLORS["dark"],
        )

    def render(self, data: list[dict], filename: str = "quarterly_low_3.png") -> Path:
        image = self.get_background()
        draw = ImageDraw.Draw(image)
        image_width, _ = image.size

        self.render_title_section(draw, image_width)
        self.render_main_section(draw, data, image_width, image)
        self.render_footer_section(draw, image_width)

        return self._save(image, filename)