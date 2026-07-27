"""Foreign-flow leaderboard — a multi-ticker dark carousel.

Where the single-ticker feeds answer "what happened to THIS stock", this post
answers "where did foreign money go across the WHOLE market this week". Two
slides: slide 1 = the stocks foreigners net-bought, slide 2 = the ones they
net-sold. Follows the dark "IDX Filings" visual system in docs/DESIGN.md.
"""
import io
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageOps

from ..render import SocialImageRenderer, font, ellipsize_to_width, format_date_range, LOGO_CACHE_DIR


class ForeignFlowRenderer(SocialImageRenderer):
    BUY = "#A6D94E"   # lime — foreign accumulation
    SELL = "#F46D43"  # ember — foreign distribution
    BLUE = "#3288BD"  # spectral — "total money"
    AMBER = "#FDAE61"

    def _circular_logo(self, symbol, size=46):
        """Circular RGBA logo for chart ticks (local cache → remote fallback)."""
        symbol = str(symbol).upper().split(".")[0]
        path = LOGO_CACHE_DIR / f"{symbol}.webp"
        img = None
        if path.exists():
            try:
                img = Image.open(path).convert("RGBA")
            except Exception:
                img = None
        if img is None:
            try:
                resp = requests.get(
                    f"https://storage.googleapis.com/sectorsapp-sea/logo/{symbol}.webp", timeout=4
                )
                if resp.status_code == 200:
                    img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                    with open(path, "wb") as f:
                        f.write(resp.content)
            except Exception:
                img = None
        if img is None:
            return None
        img = ImageOps.fit(img, (size, size), Image.Resampling.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        out = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        out.paste(img, (0, 0), mask)
        ring = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((0, 0, size - 1, size - 1), outline="#eeeeee", width=1)
        out.alpha_composite(ring)
        return out

    def _story_wrap(self, card, H=1920):
        """Letterbox the finished 1080x1350 (4:5) card into a 1080xH (9:16) story
        with EQUAL top/bottom padding, extending the background gradient into the
        pad bands. The gradient is a vertical ramp, so we simply stretch the card's
        top edge row upward and its bottom edge row downward — seamless, and the
        card (chart, stats, baked footer) is left completely untouched.
        """
        cw, ch = card.size
        top_pad = (H - ch) // 2
        bot_pad = H - ch - top_pad
        story = Image.new("RGBA", (cw, H))
        if top_pad > 0:
            story.paste(card.crop((0, 0, cw, 1)).resize((cw, top_pad),
                                   Image.Resampling.LANCZOS), (0, 0))
        if bot_pad > 0:
            story.paste(card.crop((0, ch - 1, cw, ch)).resize((cw, bot_pad),
                                  Image.Resampling.LANCZOS), (0, top_pad + ch))
        story.paste(card, (0, top_pad))
        return story

    def _flow_bars_chart(self, rows, accent, title, figsize=(11, 6.4), label_color="#c0c0d0"):
        """One horizontal bar per stock, length = |net foreign IDR|, single
        directional colour, with the ticker's circular logo on each y-tick. A
        non-finance viewer reads breadth + magnitude (and *which company*) in one
        glance — no axes to decode.
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.offsetbox import OffsetImage, AnnotationBbox

        rows = [r for r in rows if abs(float(r.get("net_value") or 0)) > 0][:8]
        if not rows:
            return None

        def compact(v):
            v = abs(float(v or 0))
            if v >= 1e12: return f"IDR {v / 1e12:,.2f}T"
            if v >= 1e9:  return f"IDR {v / 1e9:,.1f}B"
            if v >= 1e6:  return f"IDR {v / 1e6:,.0f}M"
            return f"IDR {v / 1e3:,.0f}K"

        labels = [r["base_symbol"] for r in rows]
        values = [abs(float(r["net_value"])) for r in rows]

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_alpha(0.0)
        ax.set_facecolor("none")

        n = len(rows)
        y_pos = list(range(n - 1, -1, -1))  # #1 on top
        max_v = max(values) or 1
        ax.barh(y_pos, values, height=0.46, color=accent, zorder=3)
        for y, v in zip(y_pos, values):
            ax.text(v + max_v * 0.02, y, compact(v), va="center", ha="left",
                    fontsize=13, color="#F0EBE0", fontweight="bold")

        # Ticker text label, with room reserved (pad) for the logo to its right.
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=15, color="#F0EBE0", fontweight="bold")
        ax.set_xlim(0, max_v * 1.28)
        ax.set_ylim(-0.8, n - 0.2)
        ax.tick_params(axis="y", length=0, colors=label_color, pad=46)

        # Circular logo sitting just left of each bar's origin.
        for y, r in zip(y_pos, rows):
            logo = self._circular_logo(r["base_symbol"])
            if logo is None:
                continue
            ab = AnnotationBbox(
                OffsetImage(logo, zoom=0.62), (0, y), xybox=(-10, 0),
                xycoords="data", boxcoords="offset points",
                box_alignment=(1.0, 0.5), frameon=False, pad=0, zorder=5,
            )
            ax.add_artist(ab)

        for spine in ["top", "right", "bottom", "left"]:
            ax.spines[spine].set_visible(False)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", length=0, labelbottom=False)
        ax.grid(axis="x", color="#3a3a4a", linestyle="-", linewidth=1.0, alpha=0.45, zorder=0)
        ax.set_title(title, loc="left", fontsize=11, color=label_color, pad=12)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", transparent=True)
        buf.seek(0)
        chart = Image.open(buf).convert("RGBA")
        plt.close(fig)
        return chart

    def _slide(self, rows, side, window, trading_days, page, filename):
        W, H, M = 1080, 1350, 76   # 4:5 content card (letterboxed into 9:16 at save)
        HX = M + 32
        is_buy = side == "buy"
        accent = self.BUY if is_buy else self.SELL
        verb = "bought" if is_buy else "sold"
        money = self._money_words

        img = self._idx_fillings_bg()
        draw = ImageDraw.Draw(img)
        max_w = W - 2 * HX

        top = rows[0] if rows else {}
        top_base = top.get("base_symbol", "—")
        total_net = sum(abs(float(r["net_value"])) for r in rows)

        # --- header pills + #1 logo ---
        ex, ey = HX, 56
        x2 = self._dark_pill(draw, img, ex, ey, "FOREIGN FLOW", "#F29942")
        self._dark_pill(draw, img, x2 + 16, ey, "NET BUY" if is_buy else "NET SELL",
                        accent, arrow="up" if is_buy else "down")
        # Keep the header clean; the stock-specific logo is shown in the chart instead.

        draw.text((ex, ey + 76), f"IDX · {format_date_range(window)}",
                  font=font("Inter-Bold.ttf", 24), fill=accent)

        # --- headline: "Foreign cash poured into / BBRI this week" ---
        line1 = "Foreign cash poured into" if is_buy else "Foreign cash flowed out of"
        line2_pre, line2_post = f"{top_base}", " this week"
        hsize = 56
        while hsize > 34:
            hf = font("Inter-Bold.ttf", hsize)
            if (draw.textlength(line1, font=hf) <= max_w
                    and draw.textlength(line2_pre + line2_post, font=hf) <= max_w):
                break
            hsize -= 2
        head_start = 188
        line_gap = 10
        draw.text((HX, head_start), line1, font=hf, fill="#FFFFFF")
        ly = head_start + (hf.size + line_gap)
        self._draw_segments(draw, HX, ly, [(line2_pre, accent), (line2_post, "#FFFFFF")], hf)

        hy = head_start + 2 * (hf.size + line_gap)
        verb_n = "into" if is_buy else "out of"
        def money2f(v):
            v = float(v or 0)
            a = abs(v)
            if a >= 1e12: return f"{v / 1e12:,.2f} trillion"
            if a >= 1e9:  return f"{v / 1e9:,.2f} billion"
            if a >= 1e6:  return f"{v / 1e6:,.2f} million"
            return f"{v:,.0f}"
        subhead = f"Net IDR {money2f(total_net)} {verb_n} {len(rows)} big names this week"
        sub_fnt = font("Inter-SemiBold.ttf", 26)
        draw.text((HX, hy + 24), ellipsize_to_width(draw, subhead, sub_fnt, max_w),
                  font=sub_fnt, fill="#C8C8D8")

        # --- chart ---
        sy = 1000
        title = "NET FOREIGN BUYING THIS WEEK (IDR)" if is_buy else "NET FOREIGN SELLING THIS WEEK (IDR)"
        chart = self._flow_bars_chart(rows, accent, title)
        chart_y = hy + 24 + 40 + 26
        self._paste_chart(img, chart, M, chart_y, W - 2 * M, (sy - 32) - chart_y, center_v=True)

        # --- stat trio ---
        gap = 18
        sw = (W - 2 * M - 2 * gap) // 3
        top_net = abs(float(top.get("net_value", 0))) if top else 0
        self._dark_stat_card(img, draw, M, sy, sw, "TOP " + ("BUY" if is_buy else "SELL"),
                             top_base, "most " + verb, accent, value_color=accent)
        self._dark_stat_card(img, draw, M + sw + gap, sy, sw,
                             "TOTAL NET " + ("BUY" if is_buy else "SELL"),
                             f"IDR {self._compact_num(total_net)}", "this week", self.BLUE)
        self._dark_stat_card(img, draw, M + 2 * (sw + gap), sy, sw,
                             "TOP STOCK", f"IDR {self._compact_num(top_net)}",
                             "net on " + top_base, self.AMBER)

        self._dark_page_dots(draw, W, 1180, page, 2, accent)
        return self._save(self._story_wrap(img, 1920), filename)

    def render(self, data: dict, filename_prefix: str = "foreign_flow") -> list[Path]:
        window = data.get("window")
        trading_days = data.get("trading_days", 0)
        paths = []
        paths.append(self._slide(data.get("net_buy", []), "buy", window, trading_days,
                                 0, f"{filename_prefix}_1.png"))
        paths.append(self._slide(data.get("net_sell", []), "sell", window, trading_days,
                                 1, f"{filename_prefix}_2.png"))
        return paths
