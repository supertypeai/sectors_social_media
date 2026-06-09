from PIL import Image, ImageDraw
from pathlib import Path

from datetime import date

from image_generator.render import (
    SocialImageRenderer,
    COLORS,
    font,
    clean_company_name,
    clean_text,
    fit_font,
    format_price,
)


class DividendRenderer(SocialImageRenderer):
    TITLE = "DIVIDEND YIELD GROWTH"
    SUBTITLE = "YoY"

    def get_background(self):
        return self._open("Insider trading.png")

    def _clean_symbol(self, symbol: str) -> str:
        return str(symbol or "").upper().replace(".JK", "")

    def _text_y_center(self, draw: ImageDraw.ImageDraw, text: str, fnt, center_y: int) -> int:
        bbox = draw.textbbox((0, 0), text, font=fnt)
        text_height = bbox[3] - bbox[1]
        return int(center_y - text_height / 2 - bbox[1])

    def _format_growth(self, value: object) -> str:
        try:
            pct = float(value) * 100

        except (TypeError, ValueError):
            return "-"
        
        sign = "+" if pct >= 0 else ""
        return f"{sign}{pct:.1f}%"

    def _format_dividend(self, value: object) -> str:
        try:
            return f"Rp {format_price(float(value))}"
        
        except (TypeError, ValueError):
            return "-"

    def _format_date(self, value: object) -> str:
        raw = clean_text(value, "")

        try:
            parsed = date.fromisoformat(raw[:10])
            return f"{parsed.strftime('%b')} {parsed.day}, {parsed.year}"
        
        except (ValueError, TypeError):
            return raw or "-"

    def _format_yield(self, value: object) -> str:
        try:
            return f"{float(value) * 100:.1f}%"
        
        except (TypeError, ValueError):
            return "-"

    def _format_number(self, value: object) -> str:
        if value is None:
            return "-"
        
        if float(value).is_integer():
            return f"{int(value)}"
        
        return f"{value:.1f}"
    
    def _extract_dividend_value(self, item: object) -> float | None:
        if isinstance(item, dict):
            for key in (
                "total_dividend",
                "total_dividend_amount",
                "dividend_amount",
                "cash_dividend",
                "dividend",
                "amount",
            ):
                if item.get(key) is not None:
                    try:
                        return float(item.get(key))
                    
                    except (TypeError, ValueError):
                        pass
        else:
            try:
                return float(item)
            
            except (TypeError, ValueError):
                pass

        return None

    def _draw_coin_icon(
        self,
        draw: ImageDraw.ImageDraw,
        cx: int,
        cy: int,
        scale: float,
    ):
        coin_radius = int(15 * scale)
        stack_x = cx + int(20 * scale)
        icon_text_font = font("Inter-Bold.ttf", int(9 * scale))

        for offset in (10, 5, 0):
            current_y = cy - int(offset * scale)

            draw.ellipse(
                (
                    stack_x - coin_radius,
                    current_y - coin_radius,
                    stack_x + coin_radius,
                    current_y + coin_radius,
                ),
                fill="#F59E0B",
                outline="#E67E22",
                width=max(1, int(2 * scale)),
            )

        front_coin_radius = int(18 * scale)

        draw.ellipse(
            (
                cx - front_coin_radius,
                cy - front_coin_radius,
                cx + front_coin_radius,
                cy + front_coin_radius,
            ),
            fill="#FFF3D6",
            outline="#F59E0B",
            width=max(1, int(3 * scale)),
        )

        draw.text(
            (
                cx - int(10 * scale),
                self._text_y_center(draw, "Rp", icon_text_font, cy),
            ),
            "Rp",
            font=icon_text_font,
            fill="#F59E0B",
        )

    def _draw_calendar_icon(
        self,
        draw: ImageDraw.ImageDraw,
        cx: int,
        cy: int,
        scale: float,
    ):
        orange = "#f47a2a"

        w = int(44 * scale)
        h = int(48 * scale)
        x = cx - w // 2
        y = cy - h // 2

        draw.rounded_rectangle(
            (x, y, x + w, y + h),
            radius=int(5 * scale),
            outline=orange,
            width=max(1, int(3 * scale)),
        )

        draw.line(
            (x, y + int(15 * scale), x + w, y + int(15 * scale)),
            fill=orange,
            width=max(1, int(3 * scale)),
        )

        for ring_x in (x + int(12 * scale), x + w - int(12 * scale)):
            draw.line(
                (ring_x, y - int(6 * scale), ring_x, y + int(7 * scale)),
                fill=orange,
                width=max(1, int(4 * scale)),
            )

        dot_r = max(1, int(2 * scale))

        for row_y in (y + int(27 * scale), y + int(38 * scale)):
            for dot_x in (x + int(13 * scale), x + int(23 * scale), x + int(33 * scale)):
                draw.ellipse(
                    (dot_x - dot_r, row_y - dot_r, dot_x + dot_r, row_y + dot_r),
                    fill=orange,
                )

    def _draw_pie_icon(
        self,
        draw: ImageDraw.ImageDraw,
        cx: int,
        cy: int,
        scale: float,
    ):
        orange = "#f47a2a"

        r = int(28 * scale)
        bounds = (cx - r, cy - r, cx + r, cy + r)

        draw.ellipse(bounds, fill=orange)
        draw.pieslice(bounds, start=270, end=360, fill="#f9a15a")
        draw.pieslice(bounds, start=20, end=70, fill="#df4e24")

        line_w = max(1, int(2 * scale))
        draw.line((cx, cy, cx, cy - r), fill=COLORS["white"], width=line_w)
        draw.line((cx, cy, cx + r, cy), fill=COLORS["white"], width=line_w)
        draw.line(
            (cx, cy, cx + int(18 * scale), cy + int(22 * scale)),
            fill=COLORS["white"],
            width=line_w,
        )

    def _hex_to_rgb(self, value: str) -> tuple[int, int, int]:
        value = value.lstrip("#")
        return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))

    def _draw_gradient_bar(
        self,
        image: Image.Image,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        radius: int,
        start_color: str,
        end_color: str,
    ) -> None:
        bar_w_px = max(1, x2 - x1)
        bar_h_px = max(1, y2 - y1)

        gradient = Image.new("RGBA", (bar_w_px, bar_h_px), (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient)

        start = self._hex_to_rgb(start_color)
        end = self._hex_to_rgb(end_color)

        for yy in range(bar_h_px):
            ratio = yy / max(1, bar_h_px - 1)
            color = tuple(
                int(start[index] * (1 - ratio) + end[index] * ratio)
                for index in range(3)
            )
            gradient_draw.line((0, yy, bar_w_px, yy), fill=color + (255,))

        mask = Image.new("L", (bar_w_px, bar_h_px), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            (0, 0, bar_w_px, bar_h_px + radius),
            radius=radius,
            fill=255,
        )

        image.paste(gradient, (x1, y1), mask)
        
    def render_title_section(
        self,
        draw: ImageDraw.ImageDraw,
        image: Image.Image,
        record: dict,
        image_width: int,
    ):
        scale = image_width / 1200

        margin = int(95 * scale)
        logo_size = int(118 * scale)
        top_y = int(155 * scale)

        symbol = self._clean_symbol(record.get("symbol"))
        company_name = clean_company_name(str(record.get("company_name") or ""))

        self._logo(
            image,
            (margin, top_y),
            symbol,
            size=logo_size,
            accent=COLORS["orange_deep"],
        )

        text_x = margin + logo_size + int(34 * scale)
        symbol_font = fit_font(
            draw,
            symbol,
            max_width=int(455 * scale),
            start_size=int(68 * scale),
            min_size=int(48 * scale),
            bold=True,
        )

        draw.text(
            (text_x, top_y - int(4 * scale)),
            symbol,
            font=symbol_font,
            fill=COLORS["heading"],
        )

        name_font = fit_font(
            draw,
            company_name,
            max_width=int(600 * scale),
            start_size=int(31 * scale),
            min_size=int(22 * scale),
            bold=False,
        )

        draw.text(
            (text_x, top_y + int(72 * scale)),
            company_name,
            font=name_font,
            fill=COLORS["dark"],
        )

        sector = clean_text(record.get("sector"), "")

        sector_font = font("Inter-Bold.ttf", int(24 * scale))
        sector_padding_x = int(26 * scale)
        sector_h = int(52 * scale)

        sector_bbox = draw.textbbox((0, 0), sector, font=sector_font)
        sector_w = (sector_bbox[2] - sector_bbox[0]) + (sector_padding_x * 2)

        sector_x = image_width - margin - sector_w
        sector_y = top_y + int(28 * scale)

        draw.rounded_rectangle(
            (sector_x, sector_y, sector_x + sector_w, sector_y + sector_h),
            radius=int(14 * scale),
            fill="#fde8d3",
        )

        draw.text(
            (
                sector_x + sector_padding_x,
                self._text_y_center(draw, sector, sector_font, sector_y + sector_h // 2),
            ),
            sector,
            font=sector_font,
            fill=COLORS["orange_deep"],
        )
    
    def render_main_section(
        self,
        draw: ImageDraw.ImageDraw,
        record: dict,
        image_width: int,
    ):
        scale = image_width / 1200
        margin = int(95 * scale)

        # Divider under the title row.
        divider_y = int(305 * scale)
        draw.line(
            (margin, divider_y, image_width - margin, divider_y),
            fill="#e2cdbb",
            width=max(1, int(1.5 * scale)),
        )

        # "DIVIDEND YIELD GROWTH" heading + "YoY" sub-label.
        headline_y = int(340 * scale)
        draw.text(
            (margin, headline_y),
            self.TITLE,
            font=font("Inter-Bold.ttf", int(34 * scale)),
            fill=COLORS["ink"],
        )
        draw.text(
            (margin, headline_y + int(44 * scale)),
            self.SUBTITLE,
            font=font("Inter-Bold.ttf", int(26 * scale)),
            fill=COLORS["muted"],
        )

        # Big growth number, e.g. "+36.4%".
        growth_text = self._format_growth(record.get("yield_growth"))

        growth_font = fit_font(
            draw,
            growth_text,
            max_width=int(600 * scale),
            start_size=int(124 * scale),
            min_size=int(82 * scale),
            bold=True,
        )
        growth_color = (
            COLORS["orange_deep"]
            if not growth_text.startswith("-")
            else COLORS["red_deep"]
        )
        draw.text(
            (margin, headline_y + int(84 * scale)),
            growth_text,
            font=growth_font,
            fill=growth_color,
        )

        # Year-range pill, e.g. "FY2024  →  FY2025".
        cum_date = clean_text(record.get("cum_date"), "")

        if cum_date[:4].isdigit():
            current_year = int(cum_date[:4])

            first_year_text = f"FY{current_year - 1}"
            arrow_text = "->"
            second_year_text = f"FY{current_year}"

            pill_font = font("Inter-Bold.ttf", int(24 * scale))
            arrow_font = font("Inter-Bold.ttf", int(24 * scale))

            pill_x = margin
            pill_y = headline_y + int(242 * scale)
            pill_h = int(50 * scale)
            pill_w = int(240 * scale)

            draw.rounded_rectangle(
                (pill_x, pill_y, pill_x + pill_w, pill_y + pill_h),
                radius=int(9 * scale),
                fill="#fdf9f2",
            )

            first_w = draw.textbbox((0, 0), first_year_text, font=pill_font)[2]
            arrow_w = draw.textbbox((0, 0), arrow_text, font=arrow_font)[2]
            second_w = draw.textbbox((0, 0), second_year_text, font=pill_font)[2]

            gap = int(10 * scale)
            total_w = first_w + arrow_w + second_w + (gap * 2)
            text_x = pill_x + (pill_w - total_w) // 2
            text_center_y = pill_y + pill_h // 2

            draw.text(
                (
                    text_x,
                    self._text_y_center(draw, first_year_text, pill_font, text_center_y),
                ),
                first_year_text,
                font=pill_font,
                fill=COLORS["heading"],
            )

            arrow_x = text_x + first_w + gap
            draw.text(
                (
                    arrow_x,
                    self._text_y_center(draw, arrow_text, arrow_font, text_center_y),
                ),
                arrow_text,
                font=arrow_font,
                fill=COLORS["orange_deep"],
            )

            second_x = arrow_x + arrow_w + gap
            draw.text(
                (
                    second_x,
                    self._text_y_center(draw, second_year_text, pill_font, text_center_y),
                ),
                second_year_text,
                font=pill_font,
                fill=COLORS["heading"],
            )

        # Caption under the pill.
        draw.text(
            (margin, headline_y + int(298 * scale)),
            "Annual dividend basis",
            font=font("Inter-Regular.ttf", int(26 * scale)),
            fill=COLORS["muted"],
        )

    def render_stat_boxes(
        self,
        draw: ImageDraw.ImageDraw,
        record: dict,
        image_width: int,
    ):
        scale = image_width / 1200
        margin = int(95 * scale)

        box_x = margin
        box_y = int(690 * scale)
        box_w = image_width - (2 * margin)
        box_h = int(118 * scale)

        border = "#f3bd8d"
        divider = "#efc7a6"
        label_color = "#60636b"
        value_color = COLORS["heading"]

        label_font = font("Inter-Bold.ttf", int(18 * scale))
    
        stats = [
            ("DIVIDEND", self._format_dividend(record.get("dividend_amount")), "coins"),
            ("CUM-DATE", self._format_date(record.get("cum_date")), "calendar"),
            ("YIELD TTM", self._format_yield(record.get("yield_ttm")), "pie"),
        ]

        draw.rounded_rectangle(
            (box_x, box_y, box_x + box_w, box_y + box_h),
            radius=int(16 * scale),
            fill="#fffaf4",
            outline=border,
            width=max(1, int(1.3 * scale)),
        )

        cell_w = box_w / 3

        for index in range(1, 3):
            sep_x = int(box_x + cell_w * index)
            draw.line(
                (
                    sep_x,
                    box_y + int(18 * scale),
                    sep_x,
                    box_y + box_h - int(18 * scale),
                ),
                fill=divider,
                width=max(1, int(1 * scale)),
            )

        for index, (label, value, icon) in enumerate(stats):
            cell_x = int(box_x + cell_w * index)
            icon_x = cell_x + int(62 * scale)
            icon_y = box_y + box_h // 2

            if icon == "coins":
                self._draw_coin_icon(draw, icon_x, icon_y - int(5 * scale), scale)
            
            elif icon == "calendar":
                self._draw_calendar_icon(draw, icon_x, icon_y, scale)
            
            elif icon == "pie":
                self._draw_pie_icon(draw, icon_x, icon_y, scale)

            text_x = cell_x + int(122 * scale)
            label_y = box_y + int(36 * scale)
            value_y = box_y + int(64 * scale)

            draw.text(
                (text_x, label_y),
                label,
                font=label_font,
                fill=label_color,
            )

            fitted_value_font = fit_font(
                draw,
                value,
                max_width=int(cell_w - int(150 * scale)),
                start_size=int(30 * scale),
                min_size=int(22 * scale),
                bold=True,
            )

            draw.text(
                (text_x, value_y),
                value,
                font=fitted_value_font,
                fill=value_color,
            )

    def render_historical_data(
        self,
        draw: ImageDraw.ImageDraw,
        image: Image.Image,
        record: dict,
        image_width: int,
    ):
        scale = image_width / 1200
        margin = int(95 * scale)

        title_y = int(850 * scale)
        chart_top = int(920 * scale)
        chart_bottom = int(1130 * scale)
        chart_left = margin 
        chart_right = image_width - margin - int(10 * scale)
        chart_h = chart_bottom - chart_top

        orange = "#f47a2a"
        orange_deep = "#e93d19"
        grid = "#ead8c6"
        axis = "#cbbfb3"
        text = COLORS["ink"]

        title_font = font("Inter-Bold.ttf", int(22 * scale))
        value_font = font("Inter-Bold.ttf", int(22 * scale))
        year_font = font("Inter-Regular.ttf", int(20 * scale))
        year_bold_font = font("Inter-Bold.ttf", int(20 * scale))

        historical = record.get("historical_dividends") or {}
        rows = []

        cum_date = clean_text(record.get("cum_date"), "")
        current_year = None
        if cum_date[:4].isdigit():
            current_year = int(cum_date[:4])

        for year, payload in historical.items():
            try:
                year_int = int(year)
                
            except (TypeError, ValueError):
                continue

            value = self._extract_dividend_value(payload)
            if value is None:
                continue

            if current_year is None or year_int < current_year:
                rows.append((year_int, value))

        rows = sorted(rows, key=lambda item: item[0])[-3:]

        current_value = self._extract_dividend_value(record.get("dividend_amount"))
        
        if current_year is not None and current_value is not None:
            rows.append((current_year, current_value))

        rows = rows[-4:]

        if not rows:
            return

        max_value = max(value for _, value in rows)
        axis_max = max(200, int(((max_value + 49) // 50) * 50))
        tick_values = [0, 50, 100, 150, 200]

        if axis_max > 200:
            tick_values = list(range(0, axis_max + 1, 50))

        draw.text(
            (margin, title_y),
            "HISTORICAL DIVIDEND (RP)",
            font=title_font,
            fill=text,
        )

        for tick in tick_values:
            y = chart_bottom - int((tick / axis_max) * chart_h)

            if tick > 0:
                draw.line(
                    (chart_left, y, chart_right, y),
                    fill=grid,
                    width=max(1, int(1 * scale)),
                )

        draw.line(
            (chart_left, chart_bottom, chart_right, chart_bottom),
            fill=axis,
            width=max(1, int(1 * scale)),
        )

        slot_w = (chart_right - chart_left) / len(rows)
        bar_w = min(int(115 * scale), int(slot_w * 0.58))
        bar_radius = int(7 * scale)

        for index, (year, value) in enumerate(rows):
            is_latest = index == len(rows) - 1

            center_x = int(chart_left + slot_w * index + slot_w / 2)
            bar_h = int((value / axis_max) * chart_h)
            bar_x1 = center_x - bar_w // 2
            bar_x2 = center_x + bar_w // 2
            bar_y1 = chart_bottom - bar_h
            bar_y2 = chart_bottom

            if is_latest:
                self._draw_gradient_bar(
                    image=image,
                    x1=bar_x1,
                    y1=bar_y1,
                    x2=bar_x2,
                    y2=bar_y2,
                    radius=bar_radius,
                    start_color="#ff7b3a",
                    end_color=orange_deep,
                )

                label_color = orange_deep
                label_font = value_font
                year_color = orange_deep
                year_fnt = year_bold_font
            
            else:
                self._draw_gradient_bar(
                    image=image,
                    x1=bar_x1,
                    y1=bar_y1,
                    x2=bar_x2,
                    y2=bar_y2,
                    radius=bar_radius,
                    start_color="#ffb15d",
                    end_color=orange,
                )
                
                label_color = text
                label_font = value_font
                year_color = text
                year_fnt = year_font

            value_text = self._format_number(value)
            value_bbox = draw.textbbox((0, 0), value_text, font=label_font)
            draw.text(
                (
                    center_x - (value_bbox[2] - value_bbox[0]) / 2,
                    bar_y1 - int(34 * scale),
                ),
                value_text,
                font=label_font,
                fill=label_color,
            )

            year_text = str(year)
            year_bbox = draw.textbbox((0, 0), year_text, font=year_fnt)
            draw.text(
                (
                    center_x - (year_bbox[2] - year_bbox[0]) / 2,
                    chart_bottom + int(14 * scale),
                ),
                year_text,
                font=year_fnt,
                fill=year_color,
            )

    def render_footer(
        self,
        draw: ImageDraw.ImageDraw,
        record: dict,
        image_width: int,
    ):
        scale = image_width / 1200
        margin = int(95 * scale)

        card_x = margin
        card_y = int(1200 * scale)
        card_w = image_width - (2 * margin)
        card_h = int(132 * scale)

        orange_deep = "#e93d19"
        card_fill = "#fdf5eb"
        divider = "#efc7a6"
        text = COLORS["ink"]

        title_font = font("Inter-Bold.ttf", int(22 * scale))
        body_font = font("Inter-Regular.ttf", int(20 * scale))
        body_bold_font = font("Inter-Bold.ttf", int(20 * scale))

        growth_text = self._format_growth(record.get("yield_growth"))
        yield_text = self._format_yield(record.get("yield_ttm"))

        historical = record.get("historical_dividends") or {}
        cum_date = clean_text(record.get("cum_date"), "")
        current_year = int(cum_date[:4]) if cum_date[:4].isdigit() else None
        current_dividend = self._extract_dividend_value(record.get("dividend_amount"))

        historical_rows = []

        for year, payload in historical.items():
            try:
                year_int = int(year)

            except (TypeError, ValueError):
                continue

            historical_value = self._extract_dividend_value(payload)

            if historical_value is not None:
                if current_year is None or year_int < current_year:
                    historical_rows.append((year_int, historical_value))

        historical_rows = sorted(historical_rows, key=lambda item: item[0])[-3:]
        historical_values = [value for _, value in historical_rows]
        highest_historical = max(historical_values) if historical_values else None
        year_count = len(historical_values) + (1 if current_dividend is not None else 0)
        
        is_highest_dividend = (
            current_dividend is not None
            and (
                highest_historical is None
                or current_dividend >= highest_historical
            )
        )

        if is_highest_dividend:
            second_title = "Highest dividend yield"
            second_prefix = "in the "
            second_bold = f"last {year_count} years"

        else:
            second_title = "Dividend yield still below"
            second_prefix = "historical peak"
            second_bold = ""
            
        draw.rounded_rectangle(
            (card_x, card_y, card_x + card_w, card_y + card_h),
            radius=int(16 * scale),
            fill=card_fill,
        )

        icon_cx = card_x + int(72 * scale)
        icon_cy = card_y + card_h // 2
        icon_r = int(38 * scale)

        draw.ellipse(
            (icon_cx - icon_r, icon_cy - icon_r, icon_cx + icon_r, icon_cy + icon_r),
            fill=orange_deep,
        )

        star_points = [
            (icon_cx, icon_cy - int(25 * scale)),
            (icon_cx + int(8 * scale), icon_cy - int(8 * scale)),
            (icon_cx + int(26 * scale), icon_cy - int(7 * scale)),
            (icon_cx + int(12 * scale), icon_cy + int(5 * scale)),
            (icon_cx + int(17 * scale), icon_cy + int(24 * scale)),
            (icon_cx, icon_cy + int(14 * scale)),
            (icon_cx - int(17 * scale), icon_cy + int(24 * scale)),
            (icon_cx - int(12 * scale), icon_cy + int(5 * scale)),
            (icon_cx - int(26 * scale), icon_cy - int(7 * scale)),
            (icon_cx - int(8 * scale), icon_cy - int(8 * scale)),
        ]
        draw.line(
            star_points + [star_points[0]],
            fill=COLORS["white"],
            width=max(1, int(4 * scale)),
            joint="curve",
        )

        title_x = card_x + int(132 * scale)
        title_y = card_y + int(28 * scale)

        draw.text(
            (title_x, title_y),
            "KEY INSIGHT",
            font=title_font,
            fill=orange_deep,
        )

        column_1_x = title_x
        column_2_x = card_x + int(425 * scale)
        column_3_x = card_x + int(745 * scale)
        body_y = card_y + int(64 * scale)

        for divider_x in (card_x + int(390 * scale), card_x + int(690 * scale)):
            draw.line(
                (
                    divider_x,
                    card_y + int(42 * scale),
                    divider_x,
                    card_y + card_h - int(30 * scale),
                ),
                fill=divider,
                width=max(1, int(1 * scale)),
            )

        bullet_r = int(5 * scale)

        draw.ellipse(
            (
                column_1_x,
                body_y + int(8 * scale),
                column_1_x + bullet_r * 2,
                body_y + int(8 * scale) + bullet_r * 2,
            ),
            fill=orange_deep,
        )
        draw.text(
            (column_1_x + int(24 * scale), body_y),
            "Dividend yield growth",
            font=body_font,
            fill=text,
        )
        draw.text(
            (column_1_x + int(24 * scale), body_y + int(27 * scale)),
            f"{growth_text} YoY",
            font=body_bold_font,
            fill=text,
        )

        draw.ellipse(
            (
                column_2_x,
                body_y + int(8 * scale),
                column_2_x + bullet_r * 2,
                body_y + int(8 * scale) + bullet_r * 2,
            ),
            fill=orange_deep,
        )

        draw.text(
            (column_2_x + int(24 * scale), body_y),
            second_title,
            font=body_font,
            fill=text,
        )

        second_line_x = column_2_x + int(24 * scale)
        second_line_y = body_y + int(27 * scale)

        draw.text(
            (second_line_x, second_line_y),
            second_prefix,
            font=body_font,
            fill=text,
        )

        if second_bold:
            second_prefix_w = draw.textbbox((0, 0), second_prefix, font=body_font)[2]
            draw.text(
                (second_line_x + second_prefix_w, second_line_y),
                second_bold,
                font=body_bold_font,
                fill=text,
            )

        draw.ellipse(
            (
                column_3_x,
                body_y + int(8 * scale),
                column_3_x + bullet_r * 2,
                body_y + int(8 * scale) + bullet_r * 2,
            ),
            fill=orange_deep,
        )
        draw.text(
            (column_3_x + int(24 * scale), body_y),
            "Attractive yield",
            font=body_font,
            fill=text,
        )

        third_line_x = column_3_x + int(24 * scale)
        third_line_y = body_y + int(27 * scale)
        third_prefix = "reaching "
        third_prefix_w = draw.textbbox((0, 0), third_prefix, font=body_font)[2]

        draw.text(
            (third_line_x, third_line_y),
            third_prefix,
            font=body_font,
            fill=text,
        )
        draw.text(
            (third_line_x + third_prefix_w, third_line_y),
            yield_text,
            font=body_bold_font,
            fill=text,
        )

    def render(
        self,
        data: dict,
        filename: str = "upcoming_dividend.png",
    ) -> Path:
        image = self.get_background()
        draw = ImageDraw.Draw(image)
        image_width, _ = image.size

        self.render_title_section(
            draw=draw,
            image=image,
            record=data,
            image_width=image_width,
        )

        self.render_main_section(
            draw=draw,
            record=data,
            image_width=image_width,
        )

        self.render_stat_boxes(
            draw=draw,
            record=data,
            image_width=image_width,
        )

        self.render_historical_data(
            draw=draw,
            image=image,
            record=data,
            image_width=image_width,
        )

        self.render_footer(
            draw=draw,
            record=data,
            image_width=image_width,
        )

        return self._save(image, filename)
