from PIL import Image, ImageDraw
from datetime import date 
from pathlib import Path 

from image_generator.render import (
    SocialImageRenderer, 
    COLORS, 
    font,
    clean_company_name, 
    format_price
)


class TopCompaniesMoversRenderer(SocialImageRenderer):
    TITLE = "Top Movers"
    SUBTITLE = "Leaders & Laggards based on 1-month price change"

    SECTION_GAP = 15

    def get_background(self):
        # Source asset is 4800x6000 (4x every other template), downscale it (2x)
        image = self._open("Insider trading.png")
        return image.resize((2400, 3000), Image.Resampling.LANCZOS)

    def _format_pct_change(self, pct_change: float) -> str:
        display_value = pct_change * 100
        sign = "+" if display_value >= 0 else ""
        return f"{sign}{display_value:.2f}%"
    
    def _text_y_center(self, draw, text, fnt, center_y: int) -> int:
        bbox = draw.textbbox((0, 0), text, font=fnt)
        text_height = bbox[3] - bbox[1]
        return int(center_y - text_height / 2 - bbox[1])

    def render_title_section(self, draw: ImageDraw.ImageDraw, image_width: int):
        scale = image_width / 1200

        margin = int(60 * scale)
        title_y = int(135 * scale)

        draw.text(
            (margin + int(20 * scale), title_y),
            self.TITLE,
            font=font("Inter-Bold.ttf", int(64 * scale)),
            fill=COLORS["orange_deep"],
        )

        draw.text(
            (margin + int(20 * scale), title_y + int(90 * scale)),
            self.SUBTITLE,
            font=font("Inter-Italic.ttf", int(30 * scale)),
            fill=COLORS["dark"],
        )

    def _ranked_companies(self, data: list[dict], section_key: str) -> list[dict]:
        rows = []

        for company in data:
            section_data = company.get(section_key)

            if not isinstance(section_data, dict):
                continue

            rows.append(company)

        return sorted(
            rows,
            key=lambda company: company[section_key].get("rank", 999),
        )[:10]

    def _render_section_card(
        self,
        draw: ImageDraw.ImageDraw,
        image: Image.Image,
        data: list[dict],
        section_key: str,
        header_label: str,
        header_color: str,
        arrow_char: str,
        start_y: int,
        image_width: int,
    ) -> int:
        scale = image_width / 1200

        margin = int(60 * scale)
        right_x = int(1140 * scale)

        header_h = int(50 * scale)
        row_h = int(42.5 * scale)
        radius = int(16 * scale)

        rows = self._ranked_companies(data, section_key)
        total_h = header_h + len(rows) * row_h

        draw.rounded_rectangle(
            (margin, start_y, right_x, start_y + total_h),
            radius=radius,
            fill=COLORS["off_white"],
        )

        draw.rounded_rectangle(
            (margin, start_y, right_x, start_y + header_h),
            radius=radius,
            fill=header_color,
        )

        draw.rectangle(
            (margin, start_y + header_h - radius, right_x, start_y + header_h),
            fill=header_color,
        )

        header_font = font("Inter-Bold.ttf", int(20 * scale))
        column_font = font("Inter-Bold.ttf", int(14 * scale))
        ticker_font = font("Inter-Bold.ttf", int(20 * scale))
        value_font = font("Inter-Bold.ttf", int(16 * scale))

        pct_right_x = int(815 * scale)
        close_right_x = int(1010 * scale)

        header_center_y = start_y + header_h // 2

        header_text = f"{arrow_char}  {header_label}"

        draw.text(
            (
                margin + int(20 * scale), 
                self._text_y_center(
                    draw, header_text, header_font, header_center_y
                )
            ),
            header_text,
            font=header_font,
            fill="#ffffff",
        )

        pct_header = "1M Change"
        pct_header_w = draw.textbbox((0, 0), pct_header, font=column_font)[2]
        
        draw.text(
            (
                pct_right_x - pct_header_w, 
                self._text_y_center(
                    draw, pct_header, column_font, header_center_y
                )
            ),
            pct_header,
            font=column_font,
            fill="#ffffff",
        )

        close_header = "Close (IDR)"
        close_header_w = draw.textbbox((0, 0), close_header, font=column_font)[2]
        
        draw.text(
            (
                close_right_x - close_header_w, 
                self._text_y_center(
                    draw, close_header, column_font, header_center_y
                )
            ),
            close_header,
            font=column_font,
            fill="#ffffff",
        )

        logo_size = int(36 * scale)
        logo_x = margin + int(20 * scale)

        pct_color = COLORS["green_deep"] if section_key == "one_month_leaders" else COLORS["red_deep"]

        for index, company in enumerate(rows):
            row_top = start_y + header_h + index * row_h
            row_center_y = row_top + row_h // 2

            if index < len(rows) - 1:
                divider_y = row_top + row_h
                
                draw.line(
                    (margin + int(10 * scale), divider_y, right_x - int(10 * scale), divider_y),
                    fill="#dcdfe4",
                    width=max(1, int(1 * scale)),
                )

            symbol = company["symbol"].replace(".JK", "")
            company_name = company["company_name"]
            cleaned_company_name = clean_company_name(company_name)
            section_data = company[section_key]

            self._logo(
                image,
                (logo_x, row_center_y - logo_size // 2),
                symbol,
                size=logo_size,
            )

            ticker_x = logo_x + logo_size + int(12 * scale)
            company_name_font = font("Inter-Regular.ttf", int(18 * scale))

            draw.text(
                (ticker_x, self._text_y_center(draw, symbol, ticker_font, row_center_y)),
                symbol,
                font=ticker_font,
                fill=COLORS["heading"],
            )

            symbol_w = draw.textbbox((0, 0), symbol, font=ticker_font)[2]
            suffix = f" · {cleaned_company_name}"
            draw.text(
                (
                    ticker_x + symbol_w, 
                    self._text_y_center(draw, suffix, company_name_font, row_center_y)
                ),
                suffix,
                font=company_name_font,
                fill=COLORS["heading"],
            )

            pct_text = self._format_pct_change(section_data["pct_change"])
            pct_w = draw.textbbox((0, 0), pct_text, font=value_font)[2]
            
            draw.text(
                (
                    pct_right_x - pct_w, 
                    self._text_y_center(draw, pct_text, value_font, row_center_y)
                ),
                pct_text,
                font=value_font,
                fill=pct_color,
            )

            close_text = format_price(section_data["latest_close"])
            close_w = draw.textbbox((0, 0), close_text, font=value_font)[2]
            
            draw.text(
                (
                    close_right_x - close_w, 
                    self._text_y_center(draw, close_text, value_font, row_center_y)
                ),
                close_text,
                font=value_font,
                fill=COLORS["heading"],
            )

        return start_y + total_h

    def render_leaders(
        self,
        draw: ImageDraw.ImageDraw,
        image: Image.Image,
        data: list[dict],
        start_y: int,
        image_width: int,
    ) -> int:
        return self._render_section_card(
            draw=draw,
            image=image,
            data=data,
            section_key="one_month_leaders",
            header_label="1-Month Leaders",
            header_color=COLORS["green_deep"],
            arrow_char="▲",
            start_y=start_y,
            image_width=image_width,
        )

    def render_laggards(
        self,
        draw: ImageDraw.ImageDraw,
        image: Image.Image,
        data: list[dict],
        start_y: int,
        image_width: int,
    ) -> int:
        self._render_section_card(
            draw=draw,
            image=image,
            data=data,
            section_key="one_month_laggards",
            header_label="1-Month Laggards",
            header_color=COLORS["red_deep"],
            arrow_char="▼",
            start_y=start_y,
            image_width=image_width,
        )

    def render_footer_section(self, draw: ImageDraw.ImageDraw, image_width: int):
        scale = image_width / 1200

        footer_x = int(80 * scale)
        footer_y = int(1305 * scale)

        draw.text(
            (footer_x, footer_y),
            "Data sourced from Sectors · sectors.app",
            font=font("Inter-Bold.ttf", int(20 * scale)),
            fill=COLORS["orange_deep"],
        )

        draw.text(
            (footer_x, footer_y + int(38 * scale)),
            f"Data reflects latest market close on {date.today()}",
            font=font("Inter-Regular.ttf", int(20 * scale)),
            fill=COLORS["dark"],
        )

    def render(self, data: list[dict], filename: str = "companies_mover_2.png") -> Path:
        image = self.get_background()
        draw = ImageDraw.Draw(image)
        image_width, _ = image.size
        scale = image_width / 1200

        self.render_title_section(draw, image_width)

        leaders_start_y = int(325 * scale)

        leaders_bottom_y = self.render_leaders(
            draw=draw,
            image=image,
            data=data,
            start_y=leaders_start_y,
            image_width=image_width,
        )

        laggards_start_y = leaders_bottom_y + int(self.SECTION_GAP * scale)

        self.render_laggards(
            draw=draw,
            image=image,
            data=data,
            start_y=laggards_start_y,
            image_width=image_width,
        )

        self.render_footer_section(draw, image_width)

        return self._save(image, filename)

