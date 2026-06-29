"""Week's Winners & Losers — top-mcap weekly return leaderboard.

Two stacked sections on one image: top 10 winners (green) and top 10 losers
(red) based on ~5 trading-day price change, restricted to the top-100 stocks
by market cap so the board isn't dominated by stale-priced small caps.
"""
from pathlib import Path

from PIL import ImageDraw

from ..render import (
    SocialImageRenderer,
    COLORS,
    font,
    ellipsize_to_width,
)


class WinnersLosersRenderer(SocialImageRenderer):
    TITLE = "Week's Winners & Losers"

    def _fmt_pct(self, val) -> str:
        try:
            v = float(val)
        except Exception:
            return "-"
        sign = "+" if v >= 0 else ""
        return f"{sign}{v * 100:.2f}%"

    def render(self, data: dict, filename: str = "weekly_movers.png") -> Path:
        winners = data.get("winners", [])
        losers = data.get("losers", [])
        window = data.get("window", ("", ""))

        image = self._open("IDX - News 1.png")
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = int(w * 0.07)

        # === Title block ===
        y = 290
        draw.text((margin, y), self.TITLE, font=font("Inter-Bold.ttf", 56), fill=COLORS["ink"])
        y += 72

        date_subtitle = f"{window[0]}  to  {window[1]}  WIB"
        draw.text((margin, y), date_subtitle, font=font("Inter-Regular.ttf", 24), fill=COLORS["muted"])
        y += 38

        draw.line((margin, y, w - margin, y), fill=COLORS["line"], width=3)
        y += 28

        # === Winners section ===
        y = self._render_section(
            image, draw, "WINNERS", "Top 10 gainers",
            COLORS["green_deep"], winners, y, margin, w,
        )
        y += 28

        # === Losers section ===
        self._render_section(
            image, draw, "LOSERS", "Top 10 decliners",
            COLORS["red_deep"], losers, y, margin, w,
        )

        return self._save(image, filename)

    def _render_section(self, image, draw, label, sublabel, color, rows, y, margin, w):
        # Section header pill
        header_fnt = font("Inter-Bold.ttf", 26)
        header_w = draw.textlength(label, font=header_fnt)
        pill_h = 40
        draw.rounded_rectangle(
            (margin, y, margin + header_w + 36, y + pill_h),
            radius=pill_h // 2,
            fill=color,
        )
        draw.text((margin + 18, y + 5), label, font=header_fnt, fill=COLORS["white"])

        # Subtitle to the right of chip
        sub_fnt = font("Inter-Regular.ttf", 20)
        draw.text((margin + header_w + 56, y + 10), sublabel, font=sub_fnt, fill=COLORS["muted"])

        y += pill_h + 10

        # Rows — tighter to fit 10 rows + losers section without footer overlap
        row_h = 54
        right_x = w - margin
        for i, row in enumerate(rows[:10], start=1):
            # Rank number
            rank_text = f"{i:02d}"
            rank_fnt = font("Inter-Bold.ttf", 20)
            draw.text((margin, y + 12), rank_text, font=rank_fnt, fill=COLORS["faint"])

            # Logo
            logo_size = 44
            logo_x = margin + 48
            self._logo(image, (logo_x, y + 2), row.get("base_symbol", "?"), size=logo_size, accent=color)

            # Ticker + company name
            text_x = logo_x + logo_size + 12
            ticker_text = row.get("base_symbol", "?")
            draw.text((text_x, y + 0), ticker_text, font=font("Inter-Bold.ttf", 24), fill=COLORS["ink"])

            company_text = ellipsize_to_width(
                draw,
                row.get("company_name", "") or "",
                font("Inter-Regular.ttf", 16),
                w - text_x - 220,
            )
            draw.text((text_x, y + 28), company_text, font=font("Inter-Regular.ttf", 16), fill=COLORS["muted"])

            # % return on right
            pct_text = self._fmt_pct(row.get("weekly_return", 0))
            pct_fnt = font("Inter-Bold.ttf", 28)
            pct_w = draw.textlength(pct_text, font=pct_fnt)
            draw.text((right_x - pct_w, y + 10), pct_text, font=pct_fnt, fill=color)

            y += row_h

        return y
