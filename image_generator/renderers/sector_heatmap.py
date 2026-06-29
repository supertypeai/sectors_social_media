"""Sector Heat Map — weekly sector performance + top mover per sector.

11 IDX sectors ranked by market-cap-weighted weekly return. Each row shows the
sector name, a green/red bar scaled to the worst-case absolute return seen this
week (so the strongest sector reaches the bar's full length), and the
sector's top single-stock mover.
"""
from pathlib import Path

from PIL import ImageDraw

from ..render import (
    SocialImageRenderer,
    COLORS,
    font,
    ellipsize_to_width,
)


class SectorHeatmapRenderer(SocialImageRenderer):
    TITLE = "IDX Sector Heat Map"

    def _fmt_pct(self, val) -> str:
        try:
            v = float(val)
        except Exception:
            return "-"
        sign = "+" if v >= 0 else ""
        return f"{sign}{v * 100:.2f}%"

    def render(self, data: dict, filename: str = "sector_heatmap.png") -> Path:
        sectors = data.get("sectors", [])
        window = data.get("window", ("", ""))

        image = self._open("IDX - News 1.png")
        draw = ImageDraw.Draw(image)
        w, h = image.size
        margin = 60

        # === Title block ===
        y = 290
        draw.text((margin, y), self.TITLE, font=font("Inter-Bold.ttf", 54), fill=COLORS["ink"])
        y += 70

        date_subtitle = f"{window[0]}  to  {window[1]}  WIB"
        draw.text((margin, y), date_subtitle, font=font("Inter-Regular.ttf", 24), fill=COLORS["muted"])
        y += 36

        draw.line((margin, y, w - margin, y), fill=COLORS["line"], width=3)
        y += 30

        # Compute bar scale so the strongest |return| just reaches the bar's max width.
        max_abs = max(
            (abs(s.get("weighted_return", 0)) for s in sectors),
            default=0.01,
        )
        max_abs = max(max_abs, 0.005)  # floor — avoid divide-by-zero on a flat week

        # Layout columns. Three distinct zones with explicit gutters so the
        # % label and the top-mover logo never collide.
        sector_label_x = margin
        sector_label_w = 290           # wider — fits "Transportation & Logistic"
        bar_area_start = margin + 300
        bar_area_end = margin + 300 + 280
        bar_center_x = (bar_area_start + bar_area_end) // 2
        bar_half_w = (bar_area_end - bar_area_start) // 2 - 6
        pct_label_x = bar_area_end + 16       # fixed x — always here, no overflow
        pct_label_w = 100
        topmover_x = pct_label_x + pct_label_w + 18
        right_x = w - margin

        # Center axis line for the bars (subtle, full column)
        # Drawn once, behind all rows.
        rows_start_y = y
        row_h = 108
        n_rows = len(sectors[:11])
        rows_end_y = rows_start_y + n_rows * row_h
        draw.line(
            (bar_center_x, rows_start_y, bar_center_x, rows_end_y),
            fill="#e6e6e6",
            width=1,
        )

        for s in sectors[:11]:
            sector = s.get("sector", "")
            wret = float(s.get("weighted_return", 0) or 0)
            n = int(s.get("n_stocks", 0) or 0)
            color = COLORS["green_deep"] if wret >= 0 else COLORS["red_deep"]

            # --- Sector name + count ---
            name_fnt = font("Inter-Bold.ttf", 22)
            name_text = ellipsize_to_width(draw, sector, name_fnt, sector_label_w)
            draw.text((sector_label_x, y + 22), name_text, font=name_fnt, fill=COLORS["ink"])
            count_text = f"{n} stocks"
            draw.text(
                (sector_label_x, y + 52),
                count_text,
                font=font("Inter-Regular.ttf", 16),
                fill=COLORS["muted"],
            )

            # --- Bar ---
            bar_h = 28
            bar_y = y + 38
            bar_len = int((abs(wret) / max_abs) * bar_half_w)
            if wret >= 0:
                bar_x0, bar_x1 = bar_center_x, bar_center_x + bar_len
            else:
                bar_x0, bar_x1 = bar_center_x - bar_len, bar_center_x
            if bar_len > 0:
                draw.rounded_rectangle(
                    (bar_x0, bar_y, bar_x1, bar_y + bar_h),
                    radius=bar_h // 2,
                    fill=color,
                )

            # % label always at the fixed pct_label_x — no overflow into the
            # top-mover column, no collision with the bar.
            pct_text = self._fmt_pct(wret)
            pct_fnt = font("Inter-Bold.ttf", 22)
            draw.text((pct_label_x, bar_y + 1), pct_text, font=pct_fnt, fill=color)

            # --- Top mover ---
            top_sym = s.get("top_base_symbol", "?") or "?"
            top_ret = float(s.get("top_return", 0) or 0)

            logo_size = 48
            self._logo(image, (topmover_x, y + 28), top_sym, size=logo_size, accent=color)

            tm_text_x = topmover_x + logo_size + 12
            draw.text(
                (tm_text_x, y + 28),
                top_sym,
                font=font("Inter-Bold.ttf", 22),
                fill=COLORS["ink"],
            )

            top_color = COLORS["green_deep"] if top_ret >= 0 else COLORS["red_deep"]
            top_pct_text = self._fmt_pct(top_ret)
            draw.text(
                (tm_text_x, y + 56),
                top_pct_text,
                font=font("Inter-Bold.ttf", 20),
                fill=top_color,
            )

            y += row_h

        return self._save(image, filename)
