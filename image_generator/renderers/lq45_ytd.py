"""LQ45 worst-YTD leaderboard — vertical list, sarcastic-editorial tone.

15 rows, each: rank + logo + ticker + % YTD. Inspired by the "Saham Konglo"
leaderboard format. Default direction is "worst" (the meaner story); the
fetcher also supports "best" for a positive sibling post.
"""
from pathlib import Path

from PIL import ImageDraw

from ..render import (
    SocialImageRenderer,
    COLORS,
    font,
    ellipsize_to_width,
)


class LQ45YTDRenderer(SocialImageRenderer):
    TITLE_WORST = "LQ45's Worst YTD Performers"
    TITLE_BEST = "LQ45's Best YTD Performers"

    def _fmt_pct(self, val) -> str:
        try:
            v = float(val)
        except Exception:
            return "-"
        sign = "+" if v >= 0 else ""
        return f"{sign}{v * 100:.2f}%"

    def render(self, data: dict, filename: str = "lq45_ytd.png") -> Path:
        rows = data.get("rows", [])
        direction = data.get("direction", "worst")
        end_date = data.get("end_date", "")

        image = self._open("IDX - News 1.png")
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = int(w * 0.07)

        # === Title block ===
        y = 290
        title = self.TITLE_WORST if direction == "worst" else self.TITLE_BEST
        draw.text((margin, y), title, font=font("Inter-Bold.ttf", 52), fill=COLORS["ink"])
        y += 70

        sub_text = f"YTD price performance as of {end_date}"
        draw.text((margin, y), sub_text, font=font("Inter-Regular.ttf", 24), fill=COLORS["muted"])
        y += 40

        draw.line((margin, y, w - margin, y), fill=COLORS["line"], width=3)
        y += 30

        # === Rows ===
        color = COLORS["red_deep"] if direction == "worst" else COLORS["green_deep"]
        row_h = 80
        logo_size = 52
        right_x = w - margin
        pct_fnt = font("Inter-Bold.ttf", 30)
        ticker_fnt = font("Inter-Bold.ttf", 26)
        company_fnt = font("Inter-Regular.ttf", 16)
        rank_fnt = font("Inter-Bold.ttf", 22)

        for i, row in enumerate(rows[:15], start=1):
            # Rank
            rank_text = f"{i:02d}"
            draw.text((margin, y + 22), rank_text, font=rank_fnt, fill=COLORS["faint"])

            # Logo
            logo_x = margin + 56
            self._logo(image, (logo_x, y + 6), row.get("base_symbol", "?"), size=logo_size, accent=color)

            # Ticker + company
            text_x = logo_x + logo_size + 14
            ticker_text = row.get("base_symbol", "?")
            draw.text((text_x, y + 4), ticker_text, font=ticker_fnt, fill=COLORS["ink"])

            company_text = ellipsize_to_width(
                draw,
                row.get("company_name", "") or "",
                company_fnt,
                w - text_x - 230,
            )
            draw.text((text_x, y + 38), company_text, font=company_fnt, fill=COLORS["muted"])

            # % return on right
            pct_text = self._fmt_pct(row.get("ytd_return", 0))
            pct_w = draw.textlength(pct_text, font=pct_fnt)
            draw.text((right_x - pct_w, y + 18), pct_text, font=pct_fnt, fill=color)

            y += row_h

        return self._save(image, filename)
