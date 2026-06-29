"""Insider Action Roundup — weekly aggregate of insider filings.

Two stacked sections on one image: top 5 stocks insiders bought (green) and
top 5 stocks insiders sold (red), summed by transaction_value over the
trailing 7 days. Different angle from the per-event insider posts.
"""
from pathlib import Path

from PIL import ImageDraw

from ..render import (
    SocialImageRenderer,
    COLORS,
    font,
    currency_idr,
    ellipsize_to_width,
)


class InsiderRoundupRenderer(SocialImageRenderer):
    TITLE = "Insider Action This Week"

    def render(self, data: dict, filename: str = "insider_roundup.png") -> Path:
        buys = data.get("buys", [])
        sells = data.get("sells", [])
        window = data.get("window", ("", ""))
        n_filings = int(data.get("n_filings", 0))

        image = self._open("IDX - News 1.png")
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = int(w * 0.07)

        # === Title block ===
        y = 290
        draw.text((margin, y), self.TITLE, font=font("Inter-Bold.ttf", 56), fill=COLORS["ink"])
        y += 72

        sub_text = f"{window[0]}  to  {window[1]}  ·  {n_filings} insider filings"
        draw.text((margin, y), sub_text, font=font("Inter-Regular.ttf", 22), fill=COLORS["muted"])
        y += 36

        draw.line((margin, y, w - margin, y), fill=COLORS["line"], width=3)
        y += 28

        # === Buys section ===
        y = self._render_section(
            image, draw, "INSIDER BUYS", "Top 5 by IDR value",
            COLORS["green_deep"], buys, y, margin, w,
        )
        y += 36

        # === Sells section ===
        self._render_section(
            image, draw, "INSIDER SELLS", "Top 5 by IDR value",
            COLORS["red_deep"], sells, y, margin, w,
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

        # Subtitle
        sub_fnt = font("Inter-Regular.ttf", 20)
        draw.text((margin + header_w + 56, y + 10), sublabel, font=sub_fnt, fill=COLORS["muted"])

        y += pill_h + 16

        # Rows
        row_h = 96
        right_x = w - margin
        for i, row in enumerate(rows[:5], start=1):
            # Rank
            rank_text = f"{i:02d}"
            draw.text((margin, y + 28), rank_text, font=font("Inter-Bold.ttf", 22), fill=COLORS["faint"])

            # Logo
            logo_size = 56
            logo_x = margin + 56
            self._logo(image, (logo_x, y + 12), row.get("base_symbol", "?"), size=logo_size, accent=color)

            # Ticker + company name + top holder
            text_x = logo_x + logo_size + 14
            draw.text((text_x, y + 8), row.get("base_symbol", "?"),
                      font=font("Inter-Bold.ttf", 26), fill=COLORS["ink"])

            company_text = ellipsize_to_width(
                draw,
                row.get("company_name", "") or "",
                font("Inter-Regular.ttf", 17),
                w - text_x - 320,
            )
            draw.text((text_x, y + 40), company_text,
                      font=font("Inter-Regular.ttf", 17), fill=COLORS["muted"])

            n_str = f"{int(row.get('n_filings', 0))} filings"
            holder_text = ellipsize_to_width(
                draw,
                f"top: {row.get('top_holder', '') or '-'}",
                font("Inter-Regular.ttf", 15),
                w - text_x - 320,
            )
            draw.text((text_x, y + 64), f"{n_str}  ·  {holder_text}",
                      font=font("Inter-Regular.ttf", 15), fill=COLORS["faint"])

            # Total value on right
            value_text = currency_idr(row.get("total_value", 0))
            value_fnt = font("Inter-Bold.ttf", 28)
            value_w = draw.textlength(value_text, font=value_fnt)
            draw.text((right_x - value_w, y + 28), value_text, font=value_fnt, fill=color)

            y += row_h

        return y
