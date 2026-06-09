"""Insider / becoming-insider / earnings card renderers.

Extracted from render.py into a mixin so the heavy insider-feature surface
lives in its own module (keeps render.py's diff small + conflict-free on merge).
SocialImageRenderer inherits this mixin, so every method keeps `self` semantics
and freely calls the base renderer's helpers and vice-versa.
"""
import io
import os
import math
from io import BytesIO
from datetime import datetime, timedelta
from collections import defaultdict

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

from ..render import (
    COLORS,
    font,
    wrap_text,
    ellipsize_to_width,
    currency_idr,
    format_shares,
    clean_slug,
)
from ..insider_patterns import parse_price_transactions


class InsiderEarningsRendererMixin:
    def _trend_arrow(self, draw, xy, up=True, size=18, fill=COLORS["green"], weight=4):
        """Draw a diagonal trend arrow: up-right for buy, down-right for sell."""
        x, y = xy
        if up:
            tail = (x, y + size)
            head = (x + size, y)
            barb1 = (x + size - size * 0.5, y)
            barb2 = (x + size, y + size * 0.5)
        else:
            tail = (x, y)
            head = (x + size, y + size)
            barb1 = (x + size, y + size - size * 0.5)
            barb2 = (x + size - size * 0.5, y + size)
        draw.line([tail, head], fill=fill, width=weight)
        draw.line([head, barb1], fill=fill, width=weight)
        draw.line([head, barb2], fill=fill, width=weight)

    def _cluster_chart(self, symbol, transactions):
        """Render a price line + buy/sell markers for a cluster as a transparent RGBA image.

        Returns None if no transaction dates or no price data are available.
        """
        import io
        from datetime import datetime, timedelta
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        from ..data import fetch_daily_prices

        # Collect every individual transaction (date, type, price) across the cluster.
        markers = []
        for txn in transactions:
            for entry in parse_price_transactions(txn.get("price_transaction")):
                date_str = str(entry.get("date") or "")[:10]
                if not date_str:
                    continue
                txn_type = str(entry.get("type") or "").lower()
                markers.append((date_str, txn_type, entry.get("price")))

        if not markers:
            return None

        marker_dates = sorted({d for d, _, _ in markers})
        try:
            since = (datetime.strptime(marker_dates[0], "%Y-%m-%d") - timedelta(days=10)).strftime("%Y-%m-%d")
            until = (datetime.strptime(marker_dates[-1], "%Y-%m-%d") + timedelta(days=10)).strftime("%Y-%m-%d")
        except ValueError:
            return None

        try:
            df = fetch_daily_prices(symbol, since=since, until=until)
        except Exception as e:
            print(f"Cluster chart price fetch failed for {symbol}: {e}")
            return None
        if df is None or df.empty:
            return None

        df = df.dropna(subset=["close"]).sort_values("date")
        line_dates = [datetime.strptime(str(d)[:10], "%Y-%m-%d") for d in df["date"]]
        line_closes = [float(c) for c in df["close"]]
        if not line_dates:
            return None
        close_by_date = {str(d)[:10]: float(c) for d, c in zip(df["date"], df["close"])}

        GREEN, RED = "#1f9d6a", "#d64a4a"

        fig, ax = plt.subplots(figsize=(10, 4))
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)
        ax.plot(line_dates, line_closes, linewidth=2.5, color="#8a8d99", zorder=2)

        seen_labels = set()
        for date_str, txn_type, price in markers:
            close = close_by_date.get(date_str)
            if close is None:
                try:
                    close = float(price)
                except (TypeError, ValueError):
                    continue
            try:
                xdate = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue
            is_buy = "buy" in txn_type or "bought" in txn_type
            color = GREEN if is_buy else RED
            label = "Buy" if is_buy else "Sell"
            ax.scatter(
                [xdate], [close], s=130, color=color, zorder=4,
                edgecolors="white", linewidths=2,
                label=label if label not in seen_labels else None,
            )
            seen_labels.add(label)

        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f"{int(v):,}"))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), ha="right")

        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color("#999")
            ax.spines[spine].set_linewidth(1.5)
        ax.tick_params(colors="#666", which="both", labelsize=11)
        ax.grid(True, alpha=0.2, linestyle="--", color="#999")
        if seen_labels:
            ax.legend(loc="best", frameon=False, fontsize=12)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=120, bbox_inches="tight", transparent=True)
        buf.seek(0)
        chart = Image.open(buf).convert("RGBA")
        plt.close(fig)
        return chart

    def _fmt_date(self, date_str):
        from datetime import datetime
        try:
            return datetime.strptime(str(date_str)[:10], "%Y-%m-%d").strftime("%b %d, %Y")
        except ValueError:
            return str(date_str)

    def _fmt_pct(self, value):
        try:
            v = float(value)
        except (TypeError, ValueError):
            return "-"
        if v != 0 and abs(v) < 0.1:
            return f"{v:.3f}%"
        return f"{v:.2f}%"

    def _stat_card(self, draw, x, y, width, label, value, sub, accent, value_color=None):
        h = 146
        self._card(draw, (x, y, x + width, y + h), radius=22, fill="#ffffff", outline="#eeeeee", width=2)
        lab_fnt = font("Inter-Bold.ttf", 18)
        lw = draw.textlength(label, font=lab_fnt)
        draw.rounded_rectangle((x + 20, y + 20, x + 20 + lw + 26, y + 20 + 34), radius=10, fill=accent)
        draw.text((x + 33, y + 26), label, font=lab_fnt, fill="#ffffff")
        draw.text((x + 20, y + 66), value, font=font("Inter-Bold.ttf", 36), fill=value_color or COLORS["ink"])
        if sub:
            draw.text((x + 20, y + 112), sub, font=font("Inter-Regular.ttf", 18), fill=COLORS["muted"])

    def _dark_page_dots(self, draw, w, y, page, total, accent):
        dot, gap = 14, 12
        x = (w - (total * dot + (total - 1) * gap)) // 2
        for i in range(total):
            draw.ellipse((x, y, x + dot, y + dot), fill=accent if i == page else "#44445a")
            x += dot + gap

    def _alpha_line(self, image, xy, hex_color, alpha=90, width=1):
        """Draw a semi-transparent line onto an RGBA image via alpha composite."""
        h = hex_color.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        lo = Image.new("RGBA", image.size, (0, 0, 0, 0))
        ImageDraw.Draw(lo).line(xy, fill=(r, g, b, alpha), width=width)
        image.alpha_composite(lo)

    def _dark_stat_card(self, image, draw, x, y, width, label, value, sub, accent, value_color=None):
        """Stat card for dark backgrounds — centered layout: chip top, big value middle, sub bottom."""
        h = 164
        # Near-black card body
        card_ov = Image.new("RGBA", image.size, (0, 0, 0, 0))
        ImageDraw.Draw(card_ov).rounded_rectangle((x, y, x + width, y + h), radius=22, fill=self.IDX_DARK_CARD_FILL)
        image.alpha_composite(card_ov)
        draw.rounded_rectangle((x, y, x + width, y + h), radius=22, outline=self.IDX_DARK_BORDER, width=2)

        # Centered outlined chip at the top
        lab_fnt = font("Inter-Bold.ttf", 17)
        lw = int(draw.textlength(label, font=lab_fnt))
        chip_w, chip_h = lw + 28, 30
        chip_x = x + (width - chip_w) // 2
        chip_y = y + 22
        draw.rounded_rectangle((chip_x, chip_y, chip_x + chip_w, chip_y + chip_h),
                               radius=chip_h // 2, outline=accent, width=1)
        draw.text((chip_x + 14, chip_y + 5), label, font=lab_fnt, fill="#ffffff")

        # Large centered value — extra gap below chip
        val_size = 40
        val_fnt = font("Inter-Bold.ttf", val_size)
        while draw.textlength(value, font=val_fnt) > width - 24 and val_size > 26:
            val_size -= 2
            val_fnt = font("Inter-Bold.ttf", val_size)
        vw = draw.textlength(value, font=val_fnt)
        draw.text((x + (width - vw) // 2, y + 70), value, font=val_fnt, fill=value_color or "#F0EBE0")

        # Centered sub label — title-cased, with extra breathing room at bottom
        if sub:
            sub_fnt = font("Inter-Regular.ttf", 17)
            sub_text = sub.title()
            sw = draw.textlength(sub_text, font=sub_fnt)
            draw.text((x + (width - sw) // 2, y + 126), sub_text, font=sub_fnt, fill="#8888a0")

    def _dark_signal_card(self, draw, image, x, y, width, modules, accent, header="PAST INSIGHTS"):
        """Dark-themed signal strip for the IDX Fillings background."""
        if not modules:
            return y
        pad, row_h = 28, 64
        card_h = pad + 40 + len(modules) * row_h + pad - 12
        card_ov = Image.new("RGBA", image.size, (0, 0, 0, 0))
        ImageDraw.Draw(card_ov).rounded_rectangle((x, y, x + width, y + card_h), radius=22, fill=self.IDX_DARK_CARD_FILL)
        image.alpha_composite(card_ov)
        draw.rounded_rectangle((x, y, x + width, y + card_h), radius=22, outline=self.IDX_DARK_BORDER, width=1)
        cx, cy = x + pad, y + pad
        draw.text((cx, cy), header, font=font("Inter-Bold.ttf", 18), fill="#9090a8")
        cy += 44
        lab_fnt = font("Inter-Bold.ttf", 18)
        val_fnt = font("Inter-SemiBold.ttf", 26)
        for label, text, color in modules:
            lw = draw.textlength(label, font=lab_fnt)
            chip_ov = Image.new("RGBA", image.size, (0, 0, 0, 0))
            ImageDraw.Draw(chip_ov).rounded_rectangle(
                (cx, cy + 4, cx + lw + 26, cy + 4 + 34), radius=10, fill=self.IDX_DARK_CARD_FILL
            )
            image.alpha_composite(chip_ov)
            draw.rounded_rectangle((cx, cy + 4, cx + lw + 26, cy + 4 + 34), radius=10, outline=color, width=1)
            draw.text((cx + 13, cy + 10), label, font=lab_fnt, fill=color)
            draw.text((cx + lw + 26 + 18, cy + 6), ellipsize_to_width(draw, text, val_fnt, width - 2 * pad - lw - 60),
                      font=val_fnt, fill="#e8e8f0")
            cy += row_h
        return y + card_h

    def _cluster_convergence_chart(self, close_by_date, points, roster, palette, figsize=(11, 3.3),
                                   avg_buy=None, dots_color=None, dots_label=None, show_legend=False,
                                   ylabel=None, face="#ffffff", label_color="#666",
                                   shade_color=None, marker_edge_color="white"):
        """Market-close line with each insider's trades scattered on top, colored per holder."""
        import io
        from collections import defaultdict
        from datetime import datetime, timedelta
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        closes = sorted((d, c) for d, c in close_by_date.items() if c is not None)
        usable = [p for p in points if p.get("price")]
        if len(usable) < 1 and len(closes) < 2:
            return None

        TEAL = "#3288BD"  # market-price line (Spectral blue)
        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_alpha(0.0)
        ax.set_facecolor("none" if face in (None, "none") else face)

        if len(closes) >= 2:
            cx = [datetime.strptime(d, "%Y-%m-%d") for d, _ in closes]
            cy = [c for _, c in closes]
            ax.plot(cx, cy, "-", color=TEAL, linewidth=2.2, label="Market close", zorder=2)

        # Shaded "buy zone" so the filing period is visible even when dots overlap.
        buy_dates = []
        for p in usable:
            try:
                buy_dates.append(datetime.strptime(p["date"], "%Y-%m-%d"))
            except (TypeError, ValueError):
                continue
        if buy_dates:
            lo, hi = min(buy_dates), max(buy_dates)
            if (hi - lo).days < 6:
                lo, hi = lo - timedelta(days=4), hi + timedelta(days=4)
            ax.axvspan(lo, hi, color=shade_color or dots_color or "#5BAA5A", alpha=0.10, zorder=1)

        if avg_buy:
            ax.axhline(avg_buy, color="#5E4FA2", linewidth=1.6, linestyle="--", zorder=1,
                       label=f"Avg filing price (IDR {int(avg_buy):,})")

        # Dots are colored to match the roster's colored dots (the roster is the key).
        # When dots_color is given (slides without a roster), use one colour + one label.
        # Fan out same-day buys horizontally so stacked dots (e.g. 9 insiders on one day) all show.
        per_day = defaultdict(list)
        for p in usable:
            per_day[p["date"]].append(p)
        jitter = {}
        for d, plist in per_day.items():
            n = len(plist)
            for i, p in enumerate(plist):
                jitter[id(p)] = (i - (n - 1) / 2) * 1.1 if n > 1 else 0  # days offset, centered

        top_keys = {h["key"]: palette[i] for i, h in enumerate(roster) if i < len(palette)}
        single_labeled = False
        other_labeled = False
        for p in usable:
            try:
                xd = datetime.strptime(p["date"], "%Y-%m-%d") + timedelta(days=jitter.get(id(p), 0))
            except ValueError:
                continue
            if dots_color is not None:
                col = dots_color
                lbl = None if single_labeled else dots_label
                single_labeled = True
            elif p["hkey"] in top_keys:
                col, lbl = top_keys[p["hkey"]], None
            else:
                col = "#9aa0ab"
                lbl = None if other_labeled else "Other insiders"
                other_labeled = True
            edge_color = marker_edge_color or "none"
            edge_width = 0 if marker_edge_color is None else 2.0
            ax.scatter([xd], [p["price"]], s=150, color=col, edgecolors=edge_color,
                       linewidths=edge_width, alpha=0.98, zorder=4, label=lbl)

        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{int(v):,}"))
        locator = mdates.AutoDateLocator(minticks=3, maxticks=6)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))  # consistent "Dec 2025" — no lone year token
        plt.setp(ax.xaxis.get_majorticklabels(), fontsize=10)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        spine_color = "#555" if label_color != "#666" else "#bbb"
        grid_color = "#444" if label_color != "#666" else "#c8c1b6"
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color(spine_color)
        ax.tick_params(colors=label_color, labelsize=10)
        ax.grid(True, alpha=0.22, linestyle="--", color=grid_color)
        if ylabel:
            ax.set_title(ylabel, loc="left", fontsize=11, color=label_color, pad=10)
        if show_legend:
            ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=False,
                      fontsize=12, handletextpad=0.3, columnspacing=1.2,
                      labelcolor=label_color)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", transparent=True)
        buf.seek(0)
        chart = Image.open(buf).convert("RGBA")
        plt.close(fig)
        return chart

    def _cross_price_chart(self, stocks_data, figsize=(11, 4.6), face="none", label_color="#c0c0d0",
                           filing_window=None):
        """Multi-stock daily price chart (normalized to % change) with one weighted-average
        filing dot per stock.

        stocks_data: list of dicts — base_symbol, close_by_date, points, color
        filing_window: optional (start_date_str, end_date_str) to draw a shaded band
        """
        import io
        from datetime import datetime, timedelta
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_alpha(0.0)
        ax.set_facecolor("none" if face in (None, "none") else face)

        # Determine normalization base: price at filing window start, fallback to first close
        fw_start_dt, fw_end_dt = None, None
        if filing_window:
            try:
                fw_start_dt = datetime.strptime(filing_window[0][:10], "%Y-%m-%d")
                fw_end_dt = datetime.strptime(filing_window[1][:10], "%Y-%m-%d")
                if fw_start_dt == fw_end_dt:
                    fw_end_dt += timedelta(days=1)
            except (TypeError, ValueError):
                pass

        for sd in stocks_data:
            closes = sorted((d, c) for d, c in sd["close_by_date"].items() if c is not None)
            color = sd["color"]
            base = sd["base_symbol"]
            if len(closes) < 2:
                continue
            # Use price on/before each stock's own first filing date as the 0% baseline
            stock_first_date = sd.get("first_date")
            if stock_first_date:
                candidates = [(d, c) for d, c in closes if d <= stock_first_date]
                base_price = candidates[-1][1] if candidates else closes[0][1]
            elif fw_start_dt:
                fw_start_str = fw_start_dt.strftime("%Y-%m-%d")
                candidates = [(d, c) for d, c in closes if d <= fw_start_str]
                base_price = candidates[-1][1] if candidates else closes[0][1]
            else:
                base_price = closes[0][1]
            if not base_price:
                continue
            cx = [datetime.strptime(d, "%Y-%m-%d") for d, _ in closes]
            cy = [(c / base_price - 1) * 100 for _, c in closes]
            ax.plot(cx, cy, "-", color=color, linewidth=2.2, label=base, zorder=2, alpha=0.92)

            BUY_COLOR = "#A6D94E"
            SELL_COLOR = "#F46D43"

            def _weighted_dot(pts_subset, offset_days=0):
                total_val = sum(p["value"] for p in pts_subset)
                if total_val <= 0:
                    return
                avg_price = sum(p["price"] * p["value"] for p in pts_subset) / total_val
                ts_pairs = []
                for p in pts_subset:
                    try:
                        ts_pairs.append((datetime.strptime(p["date"][:10], "%Y-%m-%d").timestamp(), p["value"]))
                    except (TypeError, ValueError):
                        pass
                if not ts_pairs:
                    return
                total_tv = sum(v for _, v in ts_pairs)
                avg_ts = sum(t * v for t, v in ts_pairs) / total_tv
                avg_date = datetime.fromtimestamp(avg_ts) + timedelta(days=offset_days)
                avg_pct = (avg_price / base_price - 1) * 100
                direction_pts = {p.get("direction") for p in pts_subset}
                ring = BUY_COLOR if direction_pts <= {"buy"} else SELL_COLOR
                ax.scatter([avg_date], [avg_pct], s=280, color=color,
                           edgecolors=ring, linewidths=2.8, alpha=1.0, zorder=5)

            pts = [p for p in (sd.get("points") or []) if p.get("price") and p.get("value")]
            direction = sd.get("direction", "buy")
            if pts:
                if direction == "mixed":
                    buy_pts = [p for p in pts if p.get("direction") == "buy"]
                    sell_pts = [p for p in pts if p.get("direction") == "sell"]
                    if buy_pts:
                        _weighted_dot(buy_pts, offset_days=-1)
                    if sell_pts:
                        _weighted_dot(sell_pts, offset_days=1)
                else:
                    _weighted_dot(pts)

        # Filing window boundary lines only — subtitle already shows the dates
        if fw_start_dt and fw_end_dt:
            ax.axvline(fw_start_dt, color="#F29942", linewidth=1.2, linestyle="--", alpha=0.55, zorder=2)
            ax.axvline(fw_end_dt, color="#F29942", linewidth=1.2, linestyle="--", alpha=0.55, zorder=2)

        ax.axhline(0, color="#666", linewidth=1.0, linestyle="--", zorder=1, alpha=0.5)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color("#555")
        ax.tick_params(colors=label_color, labelsize=10)
        ax.grid(True, alpha=0.18, linestyle="--", color="#444")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{v:+.0f}%"))
        ax.set_title("% RETURN SINCE FIRST FILING (PER STOCK)", loc="left", fontsize=10, color=label_color, pad=10)
        locator = mdates.AutoDateLocator(minticks=3, maxticks=6)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        plt.setp(ax.xaxis.get_majorticklabels(), fontsize=10)
        import matplotlib.lines as mlines
        ticker_legend = ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13),
                                  ncol=min(len(stocks_data), 4), frameon=False, fontsize=12,
                                  handletextpad=0.3, columnspacing=1.2, labelcolor=label_color)
        ax.add_artist(ticker_legend)

        buy_handle = mlines.Line2D([], [], marker="o", color="none", markerfacecolor="#555",
                                   markeredgecolor="#A6D94E", markeredgewidth=2.5, markersize=8,
                                   label="Buy")
        sell_handle = mlines.Line2D([], [], marker="o", color="none", markerfacecolor="#555",
                                    markeredgecolor="#F46D43", markeredgewidth=2.5, markersize=8,
                                    label="Sell")
        dir_legend = ax.legend(handles=[buy_handle, sell_handle],
                               loc="upper center", bbox_to_anchor=(0.5, -0.38), ncol=2,
                               frameon=False, fontsize=11, handletextpad=0.5, columnspacing=2.0,
                               labelcolor=label_color, title="Dot Ring  =  Direction\n",
                               title_fontsize=9, labelspacing=1.0)
        dir_legend.get_title().set_color(label_color)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", transparent=True)
        buf.seek(0)
        chart = Image.open(buf).convert("RGBA")
        plt.close(fig)
        return chart

    def _cross_timeline_chart(self, stocks_data, figsize=(11, 4.2), face="none", label_color="#c0c0d0"):
        """Filing timeline strip — one row per stock, dots on a horizontal rail colored by direction.

        Each dot = one filing event. Green = buy, red = sell. No y-axis values — just time.
        """
        import io
        from datetime import datetime
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        BUY_COLOR = "#A6D94E"
        SELL_COLOR = "#F46D43"
        RAIL_COLOR = "#3a3a4a"

        # Collect all filing dates across stocks for the shared x-range
        all_dates = []
        for sd in stocks_data:
            for p in (sd.get("points") or []):
                try:
                    all_dates.append(datetime.strptime(p["date"][:10], "%Y-%m-%d"))
                except (TypeError, ValueError, KeyError):
                    pass
        if not all_dates:
            return None

        x_min = min(all_dates)
        x_max = max(all_dates)
        span = (x_max - x_min).days
        # Pad edges so edge dots don't get clipped
        from datetime import timedelta
        pad_days = max(7, span * 0.06)
        x_min_pad = x_min - timedelta(days=pad_days)
        x_max_pad = x_max + timedelta(days=pad_days)

        n = len(stocks_data)
        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_alpha(0.0)
        ax.set_facecolor("none" if face in (None, "none") else face)

        for row_idx, sd in enumerate(stocks_data):
            y = n - 1 - row_idx  # top stock = highest y
            # Horizontal rail
            ax.plot([x_min_pad, x_max_pad], [y, y], color=RAIL_COLOR, linewidth=1.5, zorder=1)

            pts = [p for p in (sd.get("points") or []) if p.get("date")]
            # Group filings by date so same-day events don't fully overlap
            from collections import defaultdict
            by_date = defaultdict(list)
            for p in pts:
                try:
                    dt = datetime.strptime(p["date"][:10], "%Y-%m-%d")
                    by_date[dt].append(p)
                except (TypeError, ValueError):
                    pass

            for dt, day_pts in by_date.items():
                direction = sd.get("direction", "buy")
                # Per-point direction if available, else stock-level direction
                directions = {p.get("direction") or direction for p in day_pts}
                if directions == {"buy"}:
                    color = BUY_COLOR
                elif directions == {"sell"}:
                    color = SELL_COLOR
                else:
                    color = "#F29942"  # mixed on same day
                ax.scatter([dt], [y], s=220, color=color, zorder=4, linewidths=0)

            # Stock label on the left
            ax.text(x_min_pad, y, f"  {sd['base_symbol']}", va="center", ha="left",
                    fontsize=13, color="#F0EBE0", fontweight="bold", zorder=5)

        ax.set_xlim(x_min_pad, x_max_pad)
        ax.set_ylim(-0.7, n - 0.3)
        ax.yaxis.set_visible(False)
        for spine in ["top", "right", "left"]:
            ax.spines[spine].set_visible(False)
        ax.spines["bottom"].set_color("#555")
        ax.tick_params(colors=label_color, labelsize=10, length=4)
        locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y" if span > 60 else "%b %d"))
        plt.setp(ax.xaxis.get_majorticklabels(), fontsize=10)

        # Legend
        import matplotlib.lines as mlines
        buy_h = mlines.Line2D([], [], marker="o", color="none", markerfacecolor=BUY_COLOR,
                              markersize=9, label="Buy")
        sell_h = mlines.Line2D([], [], marker="o", color="none", markerfacecolor=SELL_COLOR,
                               markersize=9, label="Sell")
        ax.legend(handles=[buy_h, sell_h], loc="upper center", bbox_to_anchor=(0.5, -0.18),
                  ncol=2, frameon=False, fontsize=11, handletextpad=0.4, columnspacing=2.0,
                  labelcolor=label_color)

        ax.set_title("WHEN THE INSIDER MOVED", loc="left", fontsize=10, color=label_color, pad=10)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", transparent=True)
        buf.seek(0)
        chart = Image.open(buf).convert("RGBA")
        plt.close(fig)
        return chart

    def _cross_return_bars_chart(self, stocks_data, figsize=(11, 4.0), face="none", label_color="#c0c0d0"):
        """Horizontal bar chart — one bar per stock showing % return since first filing.

        Bar color: green = positive return, red = negative. No time axis, no dots.
        stocks_data: list of dicts — base_symbol, close_by_date, first_date
        """
        import io
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        BUY_COLOR = "#A6D94E"
        SELL_COLOR = "#F46D43"
        ZERO_COLOR = "#888899"

        labels, values, bar_colors = [], [], []
        for sd in stocks_data:
            closes = sorted((d, c) for d, c in sd["close_by_date"].items() if c is not None)
            if len(closes) < 2:
                continue
            first_date = sd.get("first_date")
            if first_date:
                candidates = [(d, c) for d, c in closes if d <= first_date]
                base = candidates[-1][1] if candidates else closes[0][1]
            else:
                base = closes[0][1]
            latest = closes[-1][1]
            if not base:
                continue
            ret = (latest / base - 1) * 100
            labels.append(sd["base_symbol"])
            values.append(ret)
            bar_colors.append(BUY_COLOR if ret >= 0 else SELL_COLOR)

        if not labels:
            return None

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_alpha(0.0)
        ax.set_facecolor("none" if face in (None, "none") else face)

        y_pos = list(range(len(labels) - 1, -1, -1))  # top-to-bottom order

        # Plot absolute values so bar lengths are always proportional in magnitude
        abs_values = [abs(v) for v in values]
        bars = ax.barh(y_pos, abs_values, color=bar_colors, height=0.52, zorder=3, left=0)

        max_abs = max(abs_values) if abs_values else 1
        for bar, val in zip(bars, values):
            x_pos = bar.get_width() + max_abs * 0.03
            sign_arrow = "▲" if val >= 0 else "▼"
            ax.text(x_pos, bar.get_y() + bar.get_height() / 2,
                    f"{sign_arrow} {abs(val):.1f}%", va="center", ha="left",
                    fontsize=12, color=BUY_COLOR if val >= 0 else SELL_COLOR, fontweight="bold")

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=13, color="#F0EBE0", fontweight="bold")
        ax.set_xlim(0, max_abs * 1.3)  # room for labels
        for spine in ["top", "right", "bottom", "left"]:
            ax.spines[spine].set_visible(False)
        ax.xaxis.set_visible(False)
        ax.tick_params(axis="y", length=0, colors=label_color)
        ax.grid(False)
        # Direction legend at bottom
        up_label = f"▲  Up from entry" if any(v >= 0 for v in values) else ""
        dn_label = f"▼  Down from entry" if any(v < 0 for v in values) else ""
        legend_parts = []
        import matplotlib.patches as mpatches
        if up_label:
            legend_parts.append(mpatches.Patch(color=BUY_COLOR, label=up_label))
        if dn_label:
            legend_parts.append(mpatches.Patch(color=SELL_COLOR, label=dn_label))
        if legend_parts:
            ax.legend(handles=legend_parts, loc="lower right", frameon=False,
                      fontsize=10, labelcolor=label_color, handlelength=0.8)
        ax.set_title("RETURN SINCE FIRST FILING", loc="left", fontsize=10, color=label_color, pad=10)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", transparent=True)
        buf.seek(0)
        chart = Image.open(buf).convert("RGBA")
        plt.close(fig)
        return chart

    def _cross_money_bars_chart(self, stocks, figsize=(11, 5.0), face="none",
                                label_color="#c0c0d0", max_bars=6):
        """The cross-stock story chart: one horizontal bar per stock, length = money
        traded, split green=bought / red=sold. Bar length is instantly comparable so
        a non-finance viewer sees breadth (how many stocks), magnitude (how big), and
        direction-mix (bought vs sold) in one glance — no axes to read.
        """
        import io
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        BUY_COLOR = "#A6D94E"
        SELL_COLOR = "#F46D43"

        rows = [s for s in stocks if (s.get("value") or 0) > 0][:max_bars]
        if not rows:
            return None

        def compact(v):
            v = float(v or 0)
            if abs(v) >= 1e12: return f"IDR {v / 1e12:,.2f}T"
            if abs(v) >= 1e9:  return f"IDR {v / 1e9:,.1f}B"
            if abs(v) >= 1e6:  return f"IDR {v / 1e6:,.0f}M"
            return f"IDR {v / 1e3:,.0f}K"

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_alpha(0.0)
        ax.set_facecolor("none" if face in (None, "none") else face)

        n = len(rows)
        y_pos = list(range(n - 1, -1, -1))  # first stock on top
        max_total = max((s.get("value") or 0) for s in rows) or 1
        has_buy = any((s.get("buy_value") or 0) > 0 for s in rows)
        has_sell = any((s.get("sell_value") or 0) > 0 for s in rows)

        for y, s in zip(y_pos, rows):
            buy_v = float(s.get("buy_value") or 0)
            sell_v = float(s.get("sell_value") or 0)
            if buy_v > 0:
                ax.barh(y, buy_v, height=0.56, color=BUY_COLOR, zorder=3, left=0)
            if sell_v > 0:
                ax.barh(y, sell_v, height=0.56, color=SELL_COLOR, zorder=3, left=buy_v)
            total = buy_v + sell_v
            ax.text(total + max_total * 0.02, y, compact(total), va="center", ha="left",
                    fontsize=13, color="#F0EBE0", fontweight="bold")

        ax.set_yticks(y_pos)
        ax.set_yticklabels([s["base_symbol"] for s in rows], fontsize=15,
                           color="#F0EBE0", fontweight="bold")
        ax.set_xlim(0, max_total * 1.26)
        ax.set_ylim(-0.7, n - 0.3)
        for spine in ["top", "right", "bottom", "left"]:
            ax.spines[spine].set_visible(False)
        ax.tick_params(axis="y", length=0, colors=label_color, pad=10)
        # Subtle vertical "scaffold" so the panel reads as a chart, not empty space.
        ax.set_axisbelow(True)
        ax.xaxis.set_major_locator(plt.MaxNLocator(5))
        ax.tick_params(axis="x", length=0, labelbottom=False)
        ax.grid(axis="x", color="#3a3a4a", linestyle="-", linewidth=1.0, alpha=0.45, zorder=0)

        legend_parts = []
        if has_buy:
            legend_parts.append(mpatches.Patch(color=BUY_COLOR, label="Bought"))
        if has_sell:
            legend_parts.append(mpatches.Patch(color=SELL_COLOR, label="Sold"))
        if len(legend_parts) > 1:
            # Anchor to the FIGURE centre (not the axes) so the legend sits centred
            # under the post — the y-axis labels otherwise push the axes centre right.
            fig.legend(handles=legend_parts, loc="lower center", bbox_to_anchor=(0.5, -0.02),
                       ncol=2, frameon=False, fontsize=13, labelcolor=label_color,
                       handlelength=1.0, columnspacing=2.2)

        ax.set_title("HOW MUCH WAS TRADED IN EACH STOCK", loc="left",
                     fontsize=11, color=label_color, pad=12)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", transparent=True)
        buf.seek(0)
        chart = Image.open(buf).convert("RGBA")
        plt.close(fig)
        return chart

    def _insider_bg(self):
        """Fresh 1080x1350 copy of the branded insider-trading background."""
        if getattr(self, "_insider_bg_cache", None) is None:
            base = Image.open(self.background_dir / "Insider trading.png").convert("RGBA")
            self._insider_bg_cache = base.resize((1080, 1350), Image.Resampling.LANCZOS)
        return self._insider_bg_cache.copy()

    def _idx_fillings_bg(self):
        """Fresh 1080x1350 copy of the dark IDX Fillings background."""
        if getattr(self, "_idx_fillings_bg_cache", None) is None:
            base = Image.open(self.background_dir / "IDX Fillings.png").convert("RGBA")
            self._idx_fillings_bg_cache = base.resize((1080, 1350), Image.Resampling.LANCZOS)
        return self._idx_fillings_bg_cache.copy()

    def _page_dots(self, draw, w, y, page, total, accent):
        dot, gap = 14, 12
        x = (w - (total * dot + (total - 1) * gap)) // 2
        for i in range(total):
            draw.ellipse((x, y, x + dot, y + dot), fill=accent if i == page else "#ded6c8")
            x += dot + gap

    def _close_on_or_before(self, close_by_date, date):
        keys = [k for k in close_by_date if k <= date]
        return close_by_date[max(keys)] if keys else None

    def _close_on_or_after(self, close_by_date, date):
        keys = [k for k in close_by_date if k >= date]
        return close_by_date[min(keys)] if keys else None

    def _paste_chart(self, image, chart, x, y, max_w, max_h, center_v=True):
        if not chart:
            return y
        ratio = max_w / float(chart.width)
        cw, ch = max_w, int(chart.height * ratio)
        if ch > max_h:
            ratio = max_h / float(chart.height)
            cw, ch = int(chart.width * ratio), max_h
        chart = chart.resize((cw, ch), Image.Resampling.LANCZOS)
        off = (max_h - ch) // 2 if (center_v and max_h > ch) else 0
        image.paste(chart, (x + (max_w - cw) // 2, y + off), chart)
        return y + off + ch

    def _eyebrow(self, draw, x, y, text, color):
        """Small uppercase category label (replaces the boxed badge)."""
        f = font("Inter-Bold.ttf", 20)
        draw.text((x, y), text.upper(), font=f, fill=color)

    def _fit_headline(self, draw, text, max_w, start_size, min_size=30):
        size = start_size
        while size > min_size:
            f = font("Inter-Bold.ttf", size)
            if draw.textlength(text, font=f) <= max_w:
                return f
            size -= 2
        return font("Inter-Bold.ttf", min_size)

    def _draw_segments(self, draw, x, y, segments, fnt):
        """Draw a single line of (text, color) segments inline; returns end x."""
        for text, color in segments:
            draw.text((x, y), text, font=fnt, fill=color)
            x += draw.textlength(text, font=fnt)
        return x

    def _chart_card(self, draw, image, x, y, w, h, chart, pad=18):
        """Tinted chart panel that keeps market/support data visually connected."""
        self._card(draw, (x, y, x + w, y + h), radius=18, fill="#fbf7ef", outline="#eadfce", width=2)
        self._paste_chart(image, chart, x + pad, y + pad, w - 2 * pad, h - 2 * pad, center_v=True)
        return y + h

    def render_insider_cluster_carousel(self, cluster, filename_prefix=None, chart_on_card=True):
        """Two-slide cluster buy/sell carousel — data only, no commentary.

        chart_on_card: True puts the slide-1 chart on a white card; False lets it
        sit directly on the peach background (transparent plot area).

        Slide 1 (what): headline with the price move + value/shares subhead +
        market-close chart (one weighted-avg dot per insider) + three hero stats
        (insiders / combined value / shares).
        Slide 2 (who): the insider roster with per-insider value bars +
        avg-buy vs market-now comparison stats.
        """
        from datetime import datetime, timedelta
        from ..data import fetch_daily_prices

        W, H, M = 1080, 1350, 76
        HX = M + 32  # shared content gutter: header text + roster content align to this x
        symbol, base = cluster["symbol"], cluster["base_symbol"]
        direction, roster = cluster["direction"], cluster["roster"]
        accent = self.CLUSTER_COLORS["buy"] if direction == "buy" else self.CLUSTER_COLORS["sell"]
        palette = self.CLUSTER_PALETTE
        verb = "bought" if direction == "buy" else "sold"
        # The dated label = the actual filing period (matches the shaded band on the chart),
        # not the 6-month detection window, which confused viewers vs. the chart's full range.
        fd0, fd1 = cluster["first_date"], cluster["last_date"]
        filing_span = self._fmt_date(fd0) if fd0 == fd1 else f"{self._fmt_date(fd0)} – {self._fmt_date(fd1)}"
        points = sorted(cluster["points"], key=lambda p: (p.get("date") or "", p.get("price") or 0))
        total_value = cluster["total_value"] or 0
        total_shares = cluster["total_shares"] or 0
        prefix = filename_prefix or f"insider_cluster_{clean_slug(base + '_' + direction)}"
        paths = []

        # --- market close line (pad the window a little on each side) ---
        try:
            since = (datetime.strptime(cluster["first_date"], "%Y-%m-%d") - timedelta(days=14)).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            since = None
        until = datetime.now().strftime("%Y-%m-%d")
        close_by_date = {}
        try:
            pdf = fetch_daily_prices(symbol, since=since, until=until)
            if pdf is not None and not pdf.empty:
                close_by_date = {str(d)[:10]: float(c) for d, c in zip(pdf["date"], pdf["close"]) if c is not None}
        except Exception as e:
            print(f"Cluster carousel price fetch failed for {symbol}: {e}")

        start_close = self._close_on_or_before(close_by_date, cluster["first_date"])
        latest_date = max(close_by_date) if close_by_date else None
        latest_close = close_by_date[latest_date] if latest_date else None
        market_move = ((latest_close - start_close) / start_close * 100) if (start_close and latest_close) else None
        avg_buy = (total_value / total_shares) if total_shares else None
        vs_avg = ((latest_close - avg_buy) / avg_buy * 100) if (avg_buy and latest_close) else None

        def compact(v):
            v = float(v or 0)
            if abs(v) >= 1e12: return f"{v / 1e12:,.2f}T"
            if abs(v) >= 1e9:  return f"{v / 1e9:,.2f}B"
            if abs(v) >= 1e6:  return f"{v / 1e6:,.2f}M"
            if abs(v) >= 1e3:  return f"{v / 1e3:,.1f}K"
            return f"{v:,.0f}"

        peach = self._insider_bg().getpixel((60, 900))  # plain background tone, for covering the baked-in band

        cluster_label = f"CLUSTER {direction.upper()}"  # green/red pill that names the pattern

        from PIL import ImageFilter

        def _pill(draw, image, x, y, text, fill, h=48, arrow=None):
            """Filled rounded pill with a soft drop shadow (+ optional up/down arrow). Returns right edge x."""
            pf = font("Inter-Bold.ttf", 22)
            tw = draw.textlength(text, font=pf)
            aw = 30 if arrow else 0
            w = tw + 44 + aw
            # Soft drop shadow so the pill lifts off the white panel.
            shl = Image.new("RGBA", image.size, (0, 0, 0, 0))
            ImageDraw.Draw(shl).rounded_rectangle((x, y + 6, x + w, y + h + 6), radius=h // 2, fill=(70, 45, 20, 70))
            image.alpha_composite(shl.filter(ImageFilter.GaussianBlur(7)))
            draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=fill)
            draw.text((x + 22, y + (h - pf.size) // 2 - 2), text, font=pf, fill="#ffffff")
            if arrow:
                ax, ay, s = x + 22 + tw + 13, y + h // 2, 7
                pts = [(ax, ay + s), (ax + 2 * s, ay + s), (ax + s, ay - s)] if arrow == "up" \
                    else [(ax, ay - s), (ax + 2 * s, ay - s), (ax + s, ay + s)]
                draw.polygon(pts, fill="#ffffff")
            return x + w

        def header_panel(draw, image, panel_bottom, subtitle):
            """White rounded header card: two matching pills + logo + green subtitle. Returns subtitle baseline y."""
            # Paint over the background's built-in header band so it never ghosts behind our panel.
            draw.rectangle((0, 0, W, 300), fill=peach)
            self._card(draw, (M, 40, W - M, panel_bottom), radius=30, fill="#ffffff", outline="#efe7da", width=2)
            ex, ey = HX, 88
            # Two pills in the same style: brand category (orange) + pattern (accent) with a direction arrow.
            x2 = _pill(draw, image, ex, ey, "INSIDER TRADING", "#F29942")
            _pill(draw, image, x2 + 16, ey, cluster_label, accent, arrow=("up" if direction == "buy" else "down"))
            logo_sz = 62  # smaller so low-res ticker logos stay crisp; centered on the pill row
            self._logo(image, (W - M - 32 - logo_sz, ey + (48 - logo_sz) // 2), base, size=logo_sz, accent=accent)
            sty = ey + 70  # tighter gap between the pills and the subtitle
            draw.text((ex, sty), subtitle, font=font("Inter-Bold.ttf", 24), fill=accent)
            return sty

        gap = 18
        sw = (W - 2 * M - 2 * gap) // 3
        side_word = "buying" if direction == "buy" else "selling"
        buyers = "buyers" if direction == "buy" else "sellers"

        sy = 1000  # stat-card row, shared y across both slides

        # ============ SLIDE 1 — what happened ============
        img = self._insider_bg()
        draw = ImageDraw.Draw(img)
        side = "cluster buy" if direction == "buy" else "cluster sell"

        # Headline as explicit lines so the price-move clause never orphans (subject / "as it fell X%").
        max_w = W - 2 * HX
        subject = f"{cluster['holder_count']} insiders {verb} {base}"
        clause = ""
        if market_move is not None:
            clause = f"as it fell {abs(market_move):.0f}%" if market_move < 0 else f"as it rose {market_move:.0f}%"
        hlines = [subject] + ([clause] if clause else [])
        hsize = 58
        while hsize > 34:
            hf = font("Inter-Bold.ttf", hsize)
            if all(draw.textlength(ln, font=hf) <= max_w for ln in hlines):
                break
            hsize -= 2
        else:
            hf = font("Inter-Bold.ttf", 34)
            hlines = wrap_text(draw, f"{subject} {clause}".strip(), hf, max_w, max_lines=2)

        n_lines = min(len(hlines), 2)
        head_start = 158 + 50  # sty (ey+70=158) + gap before headline
        line_gap = 10
        hy = head_start + n_lines * (hf.size + line_gap)
        sub_fnt = font("Inter-SemiBold.ttf", 28)
        sub_gap = 24  # extra breathing room between headline and subhead
        panel_bottom = hy + sub_gap + 34 + 28

        header_panel(draw, img, panel_bottom, f"{base} · {filing_span}")
        for i, ln in enumerate(hlines[:2]):
            ly = head_start + i * (hf.size + line_gap)
            # Highlight the ticker (accent) on the subject line; clause line stays heading colour.
            if i == 0 and ln == subject and base in ln:
                pre = ln[:ln.rfind(base)]
                self._draw_segments(draw, HX, ly, [(pre, COLORS["heading"]), (base, accent)], hf)
            else:
                draw.text((HX, ly), ln, font=hf, fill=COLORS["heading"])
        verb_sub = "accumulated" if direction == "buy" else "sold"
        subhead = f"IDR {compact(total_value)} {verb_sub} across {format_shares(total_shares)} shares"
        draw.text((HX, hy + sub_gap), ellipsize_to_width(draw, subhead, sub_fnt, max_w), font=sub_fnt, fill=COLORS["dark"])

        # Chart on a white card so it sits in the same visual system as the stat cards.
        # Pass avg_buy so the dashed avg-insider-price line ties slide 1 to slide 2's AVG BUY stat.
        chart = self._cluster_convergence_chart(
            close_by_date, points, roster, palette, figsize=(11, 4.6), avg_buy=avg_buy,
            dots_color=accent, dots_label=f"Insider avg {direction}", show_legend=True, ylabel="PRICE (IDR)",
            face="#ffffff" if chart_on_card else "none")
        chart_y = panel_bottom + 36
        chart_h = (sy - 32) - chart_y
        if chart_on_card:
            self._card(draw, (M, chart_y, W - M, chart_y + chart_h), radius=22, fill="#ffffff", outline="#eeeeee", width=2)
            self._paste_chart(img, chart, M + 22, chart_y + 18, W - 2 * M - 44, chart_h - 36, center_v=True)
        else:
            self._paste_chart(img, chart, M, chart_y, W - 2 * M, chart_h, center_v=True)

        self._stat_card(draw, M, sy, sw, "INSIDERS", str(cluster["holder_count"]), f"distinct {buyers}", accent)
        self._stat_card(draw, M + sw + gap, sy, sw, "COMBINED", f"IDR {compact(total_value)}", "total value", self.CLUSTER_COLORS["market"])
        self._stat_card(draw, M + 2 * (sw + gap), sy, sw, "SHARES", compact(total_shares),
                        "shares accumulated" if direction == "buy" else "shares sold", "#F29942")
        self._page_dots(draw, W, 1180, 0, 2, accent)
        paths.append(self._save(img, f"{prefix}_1.png"))

        # ============ SLIDE 2 — who ============
        img = self._insider_bg()
        draw = ImageDraw.Draw(img)
        header_panel(draw, img, 210, f"{base} · {filing_span}")

        # Roster height is content-driven (a fixed comfortable row height); the stat row
        # then sits a fixed gap below the roster instead of being pinned to a fixed y.
        roster_bottom = self._cluster_roster_card(draw, M, 252, W - 2 * M, roster, direction, accent, palette,
                                                  max_rows=4, row_h=124)
        sy2 = roster_bottom + 44

        avg_lbl = "AVG BUY" if direction == "buy" else "AVG SELL"
        # Purple pill ties to the dashed avg-price line on slide 1; MARKET NOW blue ties to the price line.
        self._stat_card(draw, M, sy2, sw, avg_lbl, f"IDR {avg_buy:,.0f}" if avg_buy else "-", "volume-weighted", self.CLUSTER_COLORS["avg"])
        self._stat_card(draw, M + sw + gap, sy2, sw, "MARKET NOW", f"IDR {latest_close:,.0f}" if latest_close else "-",
                        self._fmt_date(latest_date) if latest_date else "", self.CLUSTER_COLORS["market"])
        if vs_avg is not None:
            vs_color = self.CLUSTER_COLORS["sell"] if vs_avg < 0 else self.CLUSTER_COLORS["buy"]
            vs_sub = f"market below avg {direction}" if vs_avg < 0 else f"market above avg {direction}"
            self._stat_card(draw, M + 2 * (sw + gap), sy2, sw, f"VS AVG {direction.upper()}", f"{vs_avg:+.0f}%", vs_sub, vs_color, value_color=vs_color)
        else:
            self._stat_card(draw, M + 2 * (sw + gap), sy2, sw, f"VS AVG {direction.upper()}", "-", "", COLORS["muted"])
        self._page_dots(draw, W, 1180, 1, 2, accent)
        paths.append(self._save(img, f"{prefix}_2.png"))

        return paths

    def _cluster_roster_card(self, draw, x, y, width, roster, direction, accent, palette, max_rows=4, row_h=118):
        """Insider roster table with per-insider value bars (reference cluster layout, data-only)."""
        pad = 32
        title = "Who's Buying" if direction == "buy" else "Who's Selling"
        shown = roster[:max_rows]
        overflow = len(roster) - len(shown)
        card_h = pad + 72 + 34 + len(shown) * row_h + (34 if overflow > 0 else 0) + pad
        self._card(draw, (x, y, x + width, y + card_h), radius=22, fill="#ffffff", outline="#eeeeee", width=2)

        cx, cy = x + pad, y + pad
        draw.text((cx, cy), title, font=font("Inter-Bold.ttf", 34), fill=COLORS["heading"])
        cnt = f"{len(roster)} insiders"
        cf = font("Inter-SemiBold.ttf", 26)
        draw.text((x + width - pad - draw.textlength(cnt, font=cf), cy + 10), cnt, font=cf, fill=accent)
        cy += 52
        draw.line((cx, cy, x + width - pad, cy), fill=accent, width=3)
        cy += 20

        import datetime as _dt

        def _my(ds):
            try:
                return _dt.datetime.strptime(str(ds)[:10], "%Y-%m-%d").strftime("%b %Y")
            except (ValueError, TypeError):
                return None

        head_fnt = font("Inter-SemiBold.ttf", 18)
        shares_right = x + width * 0.74
        value_right = x + width - pad
        draw.text((cx + 30, cy), "INSIDER", font=head_fnt, fill=COLORS["muted"])
        draw.text((shares_right - draw.textlength("SHARES", font=head_fnt), cy), "SHARES", font=head_fnt, fill=COLORS["muted"])
        draw.text((value_right - draw.textlength("VALUE (IDR)", font=head_fnt), cy), "VALUE (IDR)", font=head_fnt, fill=COLORS["muted"])
        cy += 34

        name_fnt = font("Inter-Bold.ttf", 28)
        sub_fnt = font("Inter-Regular.ttf", 18)
        num_fnt = font("Inter-SemiBold.ttf", 31)
        for idx, h in enumerate(shown):
            # Center the name + sub block inside the row so stretched rows stay balanced.
            ry = cy + max(0, (row_h - 70) // 2)
            draw.ellipse((cx, ry + 6, cx + 18, ry + 24), fill=accent)
            name = ellipsize_to_width(draw, h["name"], name_fnt, width * 0.52)
            draw.text((cx + 30, ry), name, font=name_fnt, fill=COLORS["ink"])
            # Sub-line: filing count + WHEN they filed + ownership stake.
            d0, d1 = _my(h.get("first_date")), _my(h.get("last_date"))
            date_part = d0 if (not d1 or d0 == d1) else f"{d0} – {d1}"
            owns = self._fmt_pct(h["ownership_after"]) if h.get("ownership_after") not in (None, 0) else None
            bits = [f"{h['filings']} filing{'s' if h['filings'] != 1 else ''}"]
            if date_part:
                bits.append(date_part)
            if owns:
                bits.append(f"owns {owns}")
            draw.text((cx + 30, ry + 44), " · ".join(bits), font=sub_fnt, fill=COLORS["muted"])
            sh = format_shares(h["shares"])
            draw.text((shares_right - draw.textlength(sh, font=num_fnt), ry + 2), sh, font=num_fnt, fill=COLORS["soft_ink"])
            val = currency_idr(h["value"]).replace("IDR ", "")
            draw.text((value_right - draw.textlength(val, font=num_fnt), ry + 2), val, font=num_fnt, fill=COLORS["ink"])
            if idx < len(shown) - 1:
                draw.line((cx, cy + row_h - 1, x + width - pad, cy + row_h - 1), fill="#f0ece4", width=1)
            cy += row_h
        if overflow > 0:
            draw.text((cx + 30, cy + 2), f"+{overflow} more insider{'s' if overflow != 1 else ''}",
                      font=font("Inter-Italic.ttf", 20), fill=COLORS["muted"])
        return y + card_h

    def _chain_cumulative_chart(self, points, accent, direction, figsize=(11, 4.4), face="#ffffff", label_color="#666"):
        """Running total of rupiah traded over time — the accumulation/distribution curve."""
        import io
        from datetime import datetime
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        usable = sorted([p for p in points if p.get("value")], key=lambda p: p["date"])
        if len(usable) < 2:
            return None
        xs, cum, run = [], [], 0.0
        for p in usable:
            try:
                xs.append(datetime.strptime(p["date"], "%Y-%m-%d"))
            except (TypeError, ValueError):
                continue
            run += p["value"]
            cum.append(run / 1e9)  # rupiah in billions
        if len(xs) < 2:
            return None

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_alpha(0.0)
        ax.set_facecolor("none" if face in (None, "none") else face)
        ax.fill_between(xs, cum, step="post", color=accent, alpha=0.16, zorder=1)
        ax.step(xs, cum, where="post", color=accent, linewidth=2.6, zorder=3)
        ax.scatter(xs, cum, s=46, color=accent, edgecolors="white", linewidths=1.4, zorder=4)
        ax.scatter([xs[-1]], [cum[-1]], s=150, color=accent, edgecolors="white", linewidths=2.2, zorder=5)

        top = max(cum)
        fmt = (lambda v, _p: f"{v:,.1f}B") if top < 10 else (lambda v, _p: f"{v:,.0f}B")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(fmt))
        ax.set_ylim(bottom=0)
        locator = mdates.AutoDateLocator(minticks=3, maxticks=6)
        ax.xaxis.set_major_locator(locator)
        # Short chains span days, not months — fall back to day-level labels so the
        # ticks don't all collapse to the same "Mon YYYY".
        span_days = (xs[-1] - xs[0]).days
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b" if span_days < 75 else "%b %Y"))
        plt.setp(ax.xaxis.get_majorticklabels(), fontsize=10)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        spine_color = "#555" if label_color != "#666" else "#bbb"
        grid_color = "#444" if label_color != "#666" else "#c8c1b6"
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color(spine_color)
        ax.tick_params(colors=label_color, labelsize=10)
        ax.grid(True, alpha=0.22, linestyle="--", color=grid_color)
        title = "CUMULATIVE BOUGHT (IDR)" if direction == "buy" else "CUMULATIVE SOLD (IDR)"
        ax.set_title(title, loc="left", fontsize=11, color=label_color, pad=10)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", transparent=True)
        buf.seek(0)
        chart = Image.open(buf).convert("RGBA")
        plt.close(fig)
        return chart

    def _chain_signal_card(self, draw, x, y, width, modules, accent):
        """Conditional 'what the history says' strip: 0–2 data-backed signal rows."""
        if not modules:
            return y
        pad, row_h = 28, 64
        card_h = pad + 40 + len(modules) * row_h + pad - 12
        self._card(draw, (x, y, x + width, y + card_h), radius=22, fill="#ffffff", outline="#eeeeee", width=2)
        cx, cy = x + pad, y + pad
        draw.text((cx, cy), "PAST INSIGHTS", font=font("Inter-Bold.ttf", 18), fill=COLORS["muted"])
        cy += 44
        lab_fnt = font("Inter-Bold.ttf", 18)
        val_fnt = font("Inter-SemiBold.ttf", 26)
        for label, text, color in modules:
            lw = draw.textlength(label, font=lab_fnt)
            draw.rounded_rectangle((cx, cy + 4, cx + lw + 26, cy + 4 + 34), radius=10, fill=color)
            draw.text((cx + 13, cy + 10), label, font=lab_fnt, fill="#ffffff")
            draw.text((cx + lw + 26 + 18, cy + 6), ellipsize_to_width(draw, text, val_fnt, width - 2 * pad - lw - 60),
                      font=val_fnt, fill=COLORS["ink"])
            cy += row_h
        return y + card_h

    def _chain_price_chart_simple(self, close_by_date, points, direction, accent,
                                   figsize=(11, 4.6), face="none", label_color="#c0c0d0"):
        """Slide-1 chain chart: clean market-close line with filing-date dots snapped
        onto the line.  No avg-price dashed line, no per-holder colour coding, no
        multi-legend — just "stock price over time" + "when they bought/sold"."""
        import io
        from datetime import datetime, timedelta
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        closes = sorted((d, c) for d, c in close_by_date.items() if c is not None)
        # Keep EVERY dated filing — a filing on a non-trading day (holiday/weekend)
        # has no exact close, so we snap its dot to the nearest trading-day close
        # below. Filtering on an exact close here would silently drop those dots
        # and the chart would show fewer markers than the "N times" headline.
        usable = [p for p in points if p.get("date")]
        if len(closes) < 2:
            return None

        TEAL = "#3288BD"
        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_alpha(0.0)
        ax.set_facecolor("none" if face in (None, "none") else face)

        cx = [datetime.strptime(d, "%Y-%m-%d") for d, _ in closes]
        cy = [c for _, c in closes]
        ax.plot(cx, cy, "-", color=TEAL, linewidth=2.2, zorder=2)

        # Shaded filing window
        if usable:
            dates = []
            for p in usable:
                try:
                    dates.append(datetime.strptime(p["date"], "%Y-%m-%d"))
                except (TypeError, ValueError):
                    pass
            if dates:
                lo, hi = min(dates), max(dates)
                if (hi - lo).days < 6:
                    lo, hi = lo - timedelta(days=4), hi + timedelta(days=4)
                ax.axvspan(lo, hi, color=accent, alpha=0.12, zorder=1)

        # Dots snapped to close price — one per filing, all same accent colour
        plotted = False
        for p in usable:
            # Snap to the exact-day close; if the filing landed on a non-trading
            # day, fall back to the nearest trading-day close (prior, then next)
            # so every filing still gets a dot.
            close_price = (close_by_date.get(p["date"])
                           or self._close_on_or_before(close_by_date, p["date"])
                           or self._close_on_or_after(close_by_date, p["date"]))
            if close_price is None:
                continue
            try:
                xd = datetime.strptime(p["date"], "%Y-%m-%d")
            except ValueError:
                continue
            lbl = ("Bought here" if direction == "buy" else "Sold here") if not plotted else None
            ax.scatter([xd], [close_price], s=160, color=accent, edgecolors="#ffffff",
                       linewidths=1.8, zorder=5, label=lbl)
            plotted = True

        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{int(v):,}"))
        locator = mdates.AutoDateLocator(minticks=3, maxticks=6)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        plt.setp(ax.xaxis.get_majorticklabels(), fontsize=10)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        spine_color = "#555" if label_color != "#666" else "#bbb"
        grid_color = "#444" if label_color != "#666" else "#c8c1b6"
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color(spine_color)
        ax.tick_params(colors=label_color, labelsize=10)
        ax.grid(True, alpha=0.22, linestyle="--", color=grid_color)
        ax.set_title("STOCK PRICE (IDR)", loc="left", fontsize=11, color=label_color, pad=10)
        if plotted:
            ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=False,
                      fontsize=12, handletextpad=0.3, labelcolor=label_color)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", transparent=True)
        buf.seek(0)
        chart = Image.open(buf).convert("RGBA")
        plt.close(fig)
        return chart

    def _chain_bar_chart(self, points, direction, accent,
                          figsize=(11, 4.4), face="none", label_color="#c0c0d0"):
        """Slide-2 chain chart: one bar per filing showing IDR value, x = date label.
        Single colour, no legend needed — immediately readable at a glance."""
        import io
        from datetime import datetime
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        usable = sorted([p for p in points if p.get("value") and p.get("date")],
                        key=lambda p: p["date"])
        if not usable:
            return None

        def fmt_val(v):
            v = float(v)
            if abs(v) >= 1e12: return v / 1e12, "T"
            if abs(v) >= 1e9:  return v / 1e9,  "B"
            if abs(v) >= 1e6:  return v / 1e6,  "M"
            return v / 1e3, "K"

        # Determine unit from the largest value so all bars use the same scale
        max_v = max(p["value"] for p in usable)
        _, unit = fmt_val(max_v)
        divisor = {"T": 1e12, "B": 1e9, "M": 1e6, "K": 1e3}[unit]

        values = [p["value"] / divisor for p in usable]
        try:
            labels = [datetime.strptime(p["date"], "%Y-%m-%d").strftime("%-d %b") for p in usable]
        except ValueError:
            labels = [datetime.strptime(p["date"], "%Y-%m-%d").strftime("%d %b") for p in usable]

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_alpha(0.0)
        ax.set_facecolor("none" if face in (None, "none") else face)

        bars = ax.bar(range(len(usable)), values, color=accent, alpha=0.88, width=0.62, zorder=3)

        # Value labels above each bar
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02,
                    f"{val:.1f}{unit}", ha="center", va="bottom", fontsize=10,
                    color=label_color, fontweight="bold")

        ax.set_xticks(range(len(usable)))
        ax.set_xticklabels(labels, fontsize=10, rotation=30 if len(usable) > 5 else 0, ha="right")
        ax.set_ylabel(f"Value (IDR {unit})", fontsize=10, color=label_color)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{v:.1f}"))
        ax.tick_params(colors=label_color, labelsize=10)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        spine_color = "#555" if label_color != "#666" else "#bbb"
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color(spine_color)
        ax.grid(True, axis="y", alpha=0.22, linestyle="--",
                color="#444" if label_color != "#666" else "#c8c1b6")
        verb = "Bought" if direction == "buy" else "Sold"
        ax.set_title(f"{verb} each time (IDR {unit})", loc="left", fontsize=11,
                     color=label_color, pad=10)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", transparent=True)
        buf.seek(0)
        chart = Image.open(buf).convert("RGBA")
        plt.close(fig)
        return chart

    def render_insider_chain_carousel(self, chain, filename_prefix=None, chart_on_card=True):
        """Two-slide single-holder chain carousel — data only, no commentary.

        Slide 1 (the cadence): headline (who/what/how-many-times) + value/shares
        subhead + price chart with one dot per filing + dashed avg cost line +
        three hero stats (filings / total value / avg price).
        Slide 2 (the position): cumulative rupiah curve + stake stats
        (stake now / change in stake / market vs avg cost) + conditional signals.
        """
        from datetime import datetime, timedelta
        from ..data import fetch_daily_prices

        W, H, M = 1080, 1350, 76
        HX = M + 32
        symbol, base = chain["symbol"], chain["base_symbol"]
        direction = chain["direction"]
        holder = chain["holder_name"]
        accent = self.CLUSTER_COLORS["buy"] if direction == "buy" else self.CLUSTER_COLORS["sell"]
        palette = self.CLUSTER_PALETTE
        verb = "bought" if direction == "buy" else "sold"
        verb_sub = "accumulated" if direction == "buy" else "sold"
        fd0, fd1 = chain["first_date"], chain["last_date"]
        filing_span = self._fmt_date(fd0) if fd0 == fd1 else f"{self._fmt_date(fd0)} – {self._fmt_date(fd1)}"
        points = sorted(chain["points"], key=lambda p: (p.get("date") or "", p.get("price") or 0))
        total_value = chain["total_value"] or 0
        total_shares = chain["total_shares"] or 0
        filing_count = chain["filing_count"]
        avg_buy = chain.get("avg_price")
        prefix = filename_prefix or f"insider_chain_{clean_slug(base + '_' + direction)}"
        paths = []

        # --- market close line ---
        try:
            since = (datetime.strptime(fd0, "%Y-%m-%d") - timedelta(days=14)).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            since = None
        until = datetime.now().strftime("%Y-%m-%d")
        close_by_date = {}
        try:
            pdf = fetch_daily_prices(symbol, since=since, until=until)
            if pdf is not None and not pdf.empty:
                close_by_date = {str(d)[:10]: float(c) for d, c in zip(pdf["date"], pdf["close"]) if c is not None}
        except Exception as e:
            print(f"Chain carousel price fetch failed for {symbol}: {e}")

        latest_date = max(close_by_date) if close_by_date else None
        latest_close = close_by_date[latest_date] if latest_date else None
        vs_avg = ((latest_close - avg_buy) / avg_buy * 100) if (avg_buy and latest_close) else None

        def compact(v):
            v = float(v or 0)
            if abs(v) >= 1e12: return f"{v / 1e12:,.2f}T"
            if abs(v) >= 1e9:  return f"{v / 1e9:,.2f}B"
            if abs(v) >= 1e6:  return f"{v / 1e6:,.2f}M"
            if abs(v) >= 1e3:  return f"{v / 1e3:,.1f}K"
            return f"{v:,.0f}"

        peach = self._insider_bg().getpixel((60, 900))
        chain_label = f"CHAIN {direction.upper()}"

        from PIL import ImageFilter

        def _pill(draw, image, x, y, text, fill, h=48, arrow=None):
            pf = font("Inter-Bold.ttf", 22)
            tw = draw.textlength(text, font=pf)
            aw = 30 if arrow else 0
            w = tw + 44 + aw
            shl = Image.new("RGBA", image.size, (0, 0, 0, 0))
            ImageDraw.Draw(shl).rounded_rectangle((x, y + 6, x + w, y + h + 6), radius=h // 2, fill=(70, 45, 20, 70))
            image.alpha_composite(shl.filter(ImageFilter.GaussianBlur(7)))
            draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=fill)
            draw.text((x + 22, y + (h - pf.size) // 2 - 2), text, font=pf, fill="#ffffff")
            if arrow:
                ax, ay, s = x + 22 + tw + 13, y + h // 2, 7
                pts = [(ax, ay + s), (ax + 2 * s, ay + s), (ax + s, ay - s)] if arrow == "up" \
                    else [(ax, ay - s), (ax + 2 * s, ay - s), (ax + s, ay + s)]
                draw.polygon(pts, fill="#ffffff")
            return x + w

        def header_panel(draw, image, panel_bottom, subtitle):
            draw.rectangle((0, 0, W, 300), fill=peach)
            self._card(draw, (M, 40, W - M, panel_bottom), radius=30, fill="#ffffff", outline="#efe7da", width=2)
            ex, ey = HX, 88
            x2 = _pill(draw, image, ex, ey, "INSIDER CHAIN", "#F29942")
            _pill(draw, image, x2 + 16, ey, chain_label, accent, arrow=("up" if direction == "buy" else "down"))
            logo_sz = 62
            self._logo(image, (W - M - 32 - logo_sz, ey + (48 - logo_sz) // 2), base, size=logo_sz, accent=accent)
            sty = ey + 70
            draw.text((ex, sty), subtitle, font=font("Inter-Bold.ttf", 24), fill=accent)
            return sty

        gap = 18
        sw = (W - 2 * M - 2 * gap) // 3
        sy = 1000

        # ============ SLIDE 1 — the cadence ============
        img = self._insider_bg()
        draw = ImageDraw.Draw(img)

        max_w = W - 2 * HX
        subject = holder
        clause = f"{verb} {base} {filing_count} times"
        hlines = [subject, clause]
        hsize = 58
        while hsize > 34:
            hf = font("Inter-Bold.ttf", hsize)
            if all(draw.textlength(ln, font=hf) <= max_w for ln in hlines):
                break
            hsize -= 2
        else:
            hf = font("Inter-Bold.ttf", 34)
            subject = ellipsize_to_width(draw, subject, hf, max_w)
            hlines = [subject, clause]

        n_lines = 2
        head_start = 158 + 50
        line_gap = 10
        hy = head_start + n_lines * (hf.size + line_gap)
        sub_fnt = font("Inter-SemiBold.ttf", 28)
        sub_gap = 24
        panel_bottom = hy + sub_gap + 34 + 28

        header_panel(draw, img, panel_bottom, f"{base} · {filing_span}")
        # Line 1: holder name (heading). Line 2: "<verb> <TICKER> N times" with ticker in accent.
        draw.text((HX, head_start), hlines[0], font=hf, fill=COLORS["heading"])
        ly = head_start + (hf.size + line_gap)
        if base in clause:
            pre = clause[:clause.find(base)]
            post = clause[clause.find(base) + len(base):]
            self._draw_segments(draw, HX, ly, [(pre, COLORS["heading"]), (base, accent), (post, COLORS["heading"])], hf)
        else:
            draw.text((HX, ly), clause, font=hf, fill=COLORS["heading"])

        subhead = f"IDR {compact(total_value)} {verb_sub} across {format_shares(total_shares)} shares"
        draw.text((HX, hy + sub_gap), ellipsize_to_width(draw, subhead, sub_fnt, max_w), font=sub_fnt, fill=COLORS["dark"])

        chart = self._cluster_convergence_chart(
            close_by_date, points, [], palette, figsize=(11, 4.6), avg_buy=avg_buy,
            dots_color=accent, dots_label=f"{verb.capitalize()} trade", show_legend=True,
            ylabel="PRICE (IDR)", face="#ffffff" if chart_on_card else "none")
        chart_y = panel_bottom + 36
        chart_h = (sy - 32) - chart_y
        if chart_on_card:
            self._card(draw, (M, chart_y, W - M, chart_y + chart_h), radius=22, fill="#ffffff", outline="#eeeeee", width=2)
            self._paste_chart(img, chart, M + 22, chart_y + 18, W - 2 * M - 44, chart_h - 36, center_v=True)
        else:
            self._paste_chart(img, chart, M, chart_y, W - 2 * M, chart_h, center_v=True)

        months = chain.get("months") or 1
        self._stat_card(draw, M, sy, sw, "FILINGS", str(filing_count), f"in {months} month{'s' if months != 1 else ''}", accent)
        self._stat_card(draw, M + sw + gap, sy, sw, "TOTAL", f"IDR {compact(total_value)}",
                        "accumulated" if direction == "buy" else "sold", self.CLUSTER_COLORS["market"])
        self._stat_card(draw, M + 2 * (sw + gap), sy, sw, "AVG PRICE",
                        f"IDR {avg_buy:,.0f}" if avg_buy else "-", "volume-weighted", self.CLUSTER_COLORS["avg"])
        self._page_dots(draw, W, 1180, 0, 2, accent)
        paths.append(self._save(img, f"{prefix}_1.png"))

        # ============ SLIDE 2 — the position ============
        img = self._insider_bg()
        draw = ImageDraw.Draw(img)
        header_panel(draw, img, 210, f"{base} · {filing_span}")

        chart2_y = 252
        chart2_h = 470
        chart2 = self._chain_cumulative_chart(points, accent, direction, figsize=(11, 4.6),
                                              face="#ffffff" if chart_on_card else "none")
        if chart2 is not None:
            if chart_on_card:
                self._card(draw, (M, chart2_y, W - M, chart2_y + chart2_h), radius=22, fill="#ffffff", outline="#eeeeee", width=2)
                self._paste_chart(img, chart2, M + 22, chart2_y + 18, W - 2 * M - 44, chart2_h - 36, center_v=True)
            else:
                self._paste_chart(img, chart2, M, chart2_y, W - 2 * M, chart2_h, center_v=True)

        sy2 = chart2_y + chart2_h + 26
        own_now = chain.get("ownership_last")
        own_first = chain.get("ownership_first")
        d_stake = (own_now - own_first) if (own_now is not None and own_first is not None) else None

        self._stat_card(draw, M, sy2, sw, "STAKE NOW",
                        self._fmt_pct(own_now) if own_now not in (None, 0) else "-", "current ownership", accent)
        if d_stake is not None and abs(d_stake) >= 0.0005:
            d_color = self.CLUSTER_COLORS["buy"] if d_stake > 0 else self.CLUSTER_COLORS["sell"]
            self._stat_card(draw, M + sw + gap, sy2, sw, "STAKE CHANGE", f"{d_stake:+.2f}", "percentage points",
                            d_color, value_color=d_color)
        else:
            self._stat_card(draw, M + sw + gap, sy2, sw, "Δ STAKE", "flat", "stake unchanged", COLORS["muted"])
        if vs_avg is not None:
            vs_color = self.CLUSTER_COLORS["sell"] if vs_avg < 0 else self.CLUSTER_COLORS["buy"]
            vs_sub = "market below avg cost" if vs_avg < 0 else "market above avg cost"
            self._stat_card(draw, M + 2 * (sw + gap), sy2, sw, "VS AVG COST", f"{vs_avg:+.0f}%", vs_sub, vs_color, value_color=vs_color)
        else:
            self._stat_card(draw, M + 2 * (sw + gap), sy2, sw, "VS AVG COST", "-", "", COLORS["muted"])

        # Conditional data-backed signal strip (forward-return / size anomaly).
        modules = []
        fwd = chain.get("forward_return")
        if fwd:
            modules.append(("PAST RETURN", f"Avg {fwd['mean']:+.1f}% after {fwd['days']}d (median {fwd['median']:+.1f}%)",
                            self.CLUSTER_COLORS["avg"]))
        size = chain.get("size_anomaly")
        if size:
            modules.append(("SIZE", f"{size['mult']:.1f}× typical {direction} (IDR {size['at']})", "#F29942"))
        sig_y = sy2 + 146 + 22
        self._chain_signal_card(draw, M, sig_y, W - 2 * M, modules[:2], accent)

        self._page_dots(draw, W, 1180, 1, 2, accent)
        paths.append(self._save(img, f"{prefix}_2.png"))

        return paths

    def render_insider_chain_carousel_dark(self, chain, filename_prefix=None, variant="story", story=None):
        """Dark-themed two-slide chain carousel on the IDX Fillings background.

        Same data structure as render_insider_chain_carousel; the visual
        treatment flips to white text, semi-transparent stat cards, transparent
        chart backgrounds, and the Spectral-palette accent colors suited for
        the dark gradient bg.
        """
        from datetime import datetime, timedelta
        from ..data import fetch_daily_prices

        W, H, M = 1080, 1350, 76
        HX = M + 32
        symbol, base = chain["symbol"], chain["base_symbol"]
        direction = chain["direction"]
        holder = chain["holder_name"]
        colors = self.IDX_CHAIN_COLORS
        accent = colors["buy"] if direction == "buy" else colors["sell"]
        palette = self.CLUSTER_PALETTE
        verb = "bought" if direction == "buy" else "sold"
        verb_sub = "accumulated" if direction == "buy" else "sold"
        fd0, fd1 = chain["first_date"], chain["last_date"]
        filing_span = self._fmt_date(fd0) if fd0 == fd1 else f"{self._fmt_date(fd0)} – {self._fmt_date(fd1)}"
        points = sorted(chain["points"], key=lambda p: (p.get("date") or "", p.get("price") or 0))
        total_value = chain["total_value"] or 0
        total_shares = chain["total_shares"] or 0
        filing_count = chain["filing_count"]
        avg_buy = chain.get("avg_price")
        is_signal = variant == "signal"
        prefix_kind = "insider_chain_signal_dark" if is_signal else "insider_chain_dark"
        prefix = filename_prefix or f"{prefix_kind}_{clean_slug(base + '_' + direction)}"
        paths = []

        try:
            since = (datetime.strptime(fd0, "%Y-%m-%d") - timedelta(days=14)).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            since = None
        until = datetime.now().strftime("%Y-%m-%d")
        close_by_date = {}
        try:
            pdf = fetch_daily_prices(symbol, since=since, until=until)
            if pdf is not None and not pdf.empty:
                close_by_date = {str(d)[:10]: float(c) for d, c in zip(pdf["date"], pdf["close"]) if c is not None}
        except Exception as e:
            print(f"Chain dark carousel price fetch failed for {symbol}: {e}")

        start_close = self._close_on_or_before(close_by_date, chain["first_date"])
        latest_date = max(close_by_date) if close_by_date else None
        latest_close = close_by_date[latest_date] if latest_date else None
        market_move = ((latest_close - start_close) / start_close * 100) if (start_close and latest_close) else None
        vs_avg = ((latest_close - avg_buy) / avg_buy * 100) if (avg_buy and latest_close) else None
        move_label = None
        if story is not None:
            mv = story["move"] * 100
            hm = story["horizon_months"]
            move_dir = "up" if mv >= 0 else "down"
            move_label = f"Stock is {move_dir} {abs(mv):.0f}% in the {hm} months since"
        elif market_move is not None and not is_signal:
            move_dir = "up" if market_move >= 0 else "down"
            move_label = f"Stock is {move_dir} {market_move:+.0f}% since first filing"

        def compact(v):
            v = float(v or 0)
            if abs(v) >= 1e12: return f"{v / 1e12:,.2f}T"
            if abs(v) >= 1e9:  return f"{v / 1e9:,.2f}B"
            if abs(v) >= 1e6:  return f"{v / 1e6:,.2f}M"
            if abs(v) >= 1e3:  return f"{v / 1e3:,.1f}K"
            return f"{v:,.0f}"

        chain_label = f"CHAIN {direction.upper()}"
        HEAD_COLOR = "#FFFFFF"
        SUB_COLOR = "#C8C8D8"
        LABEL_COLOR = "#c0c0d0"

        from PIL import ImageFilter

        _card_fill = self.IDX_DARK_CARD_FILL
        _border = self.IDX_DARK_BORDER

        def _pill(draw, image, x, y, text, border_color, h=48, arrow=None):
            """Glass pill: dark semi-transparent fill + colored border + white text."""
            pf = font("Inter-Bold.ttf", 22)
            tw = draw.textlength(text, font=pf)
            aw = 30 if arrow else 0
            pw = int(tw + 44 + aw)
            pill_ov = Image.new("RGBA", image.size, (0, 0, 0, 0))
            ImageDraw.Draw(pill_ov).rounded_rectangle((x, y, x + pw, y + h), radius=h // 2, fill=_card_fill)
            image.alpha_composite(pill_ov)
            draw.rounded_rectangle((x, y, x + pw, y + h), radius=h // 2, outline=border_color, width=2)
            draw.text((x + 22, y + (h - pf.size) // 2 - 2), text, font=pf, fill="#ffffff")
            if arrow:
                arx, ary, s = x + 22 + tw + 13, y + h // 2, 7
                pts = [(arx, ary + s), (arx + 2 * s, ary + s), (arx + s, ary - s)] if arrow == "up" \
                    else [(arx, ary - s), (arx + 2 * s, ary - s), (arx + s, ary + s)]
                draw.polygon(pts, fill=border_color)
            return x + pw

        def header_panel(draw, image, panel_bottom, subtitle):
            ex, ey = HX, 56
            x2 = _pill(draw, image, ex, ey, "INSIDER CHAIN", "#F29942")
            _pill(draw, image, x2 + 16, ey, chain_label, accent, arrow=("up" if direction == "buy" else "down"))
            logo_sz = 62
            self._logo(image, (W - M - 32 - logo_sz, ey + (48 - logo_sz) // 2), base, size=logo_sz, accent=accent)
            sty = ey + 76
            draw.text((ex, sty), subtitle, font=font("Inter-Bold.ttf", 24), fill=accent)
            return sty

        gap = 18
        sw = (W - 2 * M - 2 * gap) // 3
        sy = 1000

        # ============ SLIDE 1 — the cadence ============
        img = self._idx_fillings_bg()
        draw = ImageDraw.Draw(img)

        max_w = W - 2 * HX
        subject = holder
        clause = f"{verb} {base} {filing_count} times"
        hlines = [subject, clause]
        hsize = 58
        while hsize > 34:
            hf = font("Inter-Bold.ttf", hsize)
            if all(draw.textlength(ln, font=hf) <= max_w for ln in hlines):
                break
            hsize -= 2
        else:
            hf = font("Inter-Bold.ttf", 34)
            subject = ellipsize_to_width(draw, subject, hf, max_w)
            hlines = [subject, clause]

        head_start = 188
        line_gap = 10
        hy = head_start + 2 * (hf.size + line_gap)
        sub_fnt = font("Inter-SemiBold.ttf", 28)
        sub_gap = 24
        panel_bottom = hy + sub_gap + 34 + 28

        header_panel(draw, img, panel_bottom, f"{base} · {filing_span}")
        draw.text((HX, head_start), hlines[0], font=hf, fill=HEAD_COLOR)
        ly = head_start + (hf.size + line_gap)
        if base in clause:
            pre = clause[:clause.find(base)]
            post = clause[clause.find(base) + len(base):]
            self._draw_segments(draw, HX, ly, [(pre, HEAD_COLOR), (base, accent), (post, HEAD_COLOR)], hf)
        else:
            draw.text((HX, ly), clause, font=hf, fill=HEAD_COLOR)

        if is_signal:
            subhead = f"IDR {compact(total_value)} {verb_sub} · {format_shares(total_shares)} shares"
        else:
            subhead = f"IDR {compact(total_value)} {verb_sub} across {format_shares(total_shares)} shares"
        if move_label:
            subhead = f"IDR {compact(total_value)} {verb_sub} · {move_label}"
        draw.text((HX, hy + sub_gap), ellipsize_to_width(draw, subhead, sub_fnt, max_w), font=sub_fnt, fill=SUB_COLOR)

        chart = self._chain_price_chart_simple(
            close_by_date, points, direction, accent,
            figsize=(11, 4.6), face="none", label_color=LABEL_COLOR)
        chart_y = panel_bottom + 36
        chart_h = (sy - 32) - chart_y
        self._paste_chart(img, chart, M, chart_y, W - 2 * M, chart_h, center_v=True)

        months = chain.get("months") or 1
        self._dark_stat_card(img, draw, M, sy, sw, "FILINGS", str(filing_count),
                             f"in {months} month{'s' if months != 1 else ''}", accent)
        self._dark_stat_card(img, draw, M + sw + gap, sy, sw, "TOTAL", f"IDR {compact(total_value)}",
                             "accumulated" if direction == "buy" else "sold", colors["market"])
        self._dark_stat_card(img, draw, M + 2 * (sw + gap), sy, sw, "AVG PER SHARE",
                             f"IDR {avg_buy:,.0f}" if avg_buy else "-", "from filing totals", colors["avg"])
        self._dark_page_dots(draw, W, 1180, 0, 2, accent)
        paths.append(self._save(img, f"{prefix}_1.png"))

        # ============ SLIDE 2 — the position ============
        img = self._idx_fillings_bg()
        draw = ImageDraw.Draw(img)
        header_panel(draw, img, 200, f"{base} · {filing_span}")

        chart2_y = 240
        chart2_h = 470
        # Cumulative accumulation/distribution curve — far more legible than 30+
        # per-filing bars, and no confusing "0.0B" labels on tiny filings.
        chart2 = self._chain_cumulative_chart(points, accent, direction,
                                              figsize=(11, 4.4), face="none", label_color=LABEL_COLOR)
        if chart2 is not None:
            self._paste_chart(img, chart2, M, chart2_y, W - 2 * M, chart2_h, center_v=True)

        sy2 = chart2_y + chart2_h + 26
        own_now = chain.get("ownership_last")
        own_first_val = chain.get("ownership_first")
        d_stake = (own_now - own_first_val) if (own_now is not None and own_first_val is not None) else None

        self._dark_stat_card(img, draw, M, sy2, sw, "STAKE NOW",
                             self._fmt_pct(own_now) if own_now not in (None, 0) else "-", "current ownership", accent)
        if d_stake is not None and abs(d_stake) >= 0.0005:
            d_color = colors["buy"] if d_stake > 0 else colors["sell"]
            self._dark_stat_card(img, draw, M + sw + gap, sy2, sw, "STAKE CHANGE", f"{d_stake:+.2f}",
                                 "percentage points", d_color, value_color=d_color)
        else:
            self._dark_stat_card(img, draw, M + sw + gap, sy2, sw, "Δ STAKE", "flat", "stake unchanged", "#555566")
        if vs_avg is not None:
            vs_color = colors["sell"] if vs_avg < 0 else colors["buy"]
            vs_sub = "market below filing price" if vs_avg < 0 else "market above filing price"
            self._dark_stat_card(img, draw, M + 2 * (sw + gap), sy2, sw, "MARKET VS FILING", f"{vs_avg:+.0f}%",
                                 vs_sub, vs_color, value_color=vs_color)
        else:
            self._dark_stat_card(img, draw, M + 2 * (sw + gap), sy2, sw, "MARKET VS FILING", "-", "", "#555566")

        modules = []
        fwd = chain.get("forward_return")
        if fwd:
            modules.append(("PAST RETURN", f"Avg {fwd['mean']:+.1f}% after {fwd['days']}d (median {fwd['median']:+.1f}%)",
                            colors["avg"]))
        size_anom = chain.get("size_anomaly")
        if size_anom:
            modules.append(("SIZE", f"{size_anom['mult']:.1f}× typical {direction} (IDR {size_anom['at']})", "#F29942"))
        sig_y = sy2 + 164 + 22
        self._dark_signal_card(draw, img, M, sig_y, W - 2 * M, modules[:2], accent)

        self._dark_page_dots(draw, W, 1180, 1, 2, accent)
        paths.append(self._save(img, f"{prefix}_2.png"))

        return paths

    def _dark_cluster_roster_card(self, image, draw, x, y, width, roster, direction, accent, palette, max_rows=4, row_h=118):
        pad = 32
        title = "Who's Buying" if direction == "buy" else "Who's Selling"
        shown = roster[:max_rows]
        overflow = len(roster) - len(shown)
        card_h = pad + 72 + 34 + len(shown) * row_h + (34 if overflow > 0 else 0) + pad
        card_ov = Image.new("RGBA", image.size, (0, 0, 0, 0))
        ImageDraw.Draw(card_ov).rounded_rectangle((x, y, x + width, y + card_h), radius=22, fill=self.IDX_DARK_CARD_FILL)
        image.alpha_composite(card_ov)
        draw.rounded_rectangle((x, y, x + width, y + card_h), radius=22, outline=self.IDX_DARK_BORDER, width=2)

        cx, cy = x + pad, y + pad
        draw.text((cx, cy), title, font=font("Inter-Bold.ttf", 34), fill="#FFFFFF")
        cnt = f"{len(roster)} insiders"
        cf = font("Inter-SemiBold.ttf", 26)
        draw.text((x + width - pad - draw.textlength(cnt, font=cf), cy + 10), cnt, font=cf, fill=accent)
        cy += 52
        self._alpha_line(image, (cx, cy, x + width - pad, cy), accent, alpha=90, width=3)
        cy += 20

        import datetime as _dt

        def _my(ds):
            try:
                return _dt.datetime.strptime(str(ds)[:10], "%Y-%m-%d").strftime("%b %Y")
            except (ValueError, TypeError):
                return None

        head_fnt = font("Inter-SemiBold.ttf", 18)
        shares_right = x + width * 0.74
        value_right = x + width - pad
        draw.text((cx + 30, cy), "INSIDER", font=head_fnt, fill="#9090a8")
        draw.text((shares_right - draw.textlength("SHARES", font=head_fnt), cy), "SHARES", font=head_fnt, fill="#9090a8")
        draw.text((value_right - draw.textlength("VALUE (IDR)", font=head_fnt), cy), "VALUE (IDR)", font=head_fnt, fill="#9090a8")
        cy += 34

        name_fnt = font("Inter-Bold.ttf", 28)
        sub_fnt = font("Inter-Regular.ttf", 18)
        num_fnt = font("Inter-SemiBold.ttf", 31)
        for idx, h in enumerate(shown):
            ry = cy + max(0, (row_h - 70) // 2)
            dot_color = palette[idx % len(palette)] if palette else accent
            draw.ellipse((cx, ry + 6, cx + 18, ry + 24), fill=dot_color)
            name = ellipsize_to_width(draw, h["name"], name_fnt, width * 0.52)
            draw.text((cx + 30, ry), name, font=name_fnt, fill="#F0EBE0")
            d0, d1 = _my(h.get("first_date")), _my(h.get("last_date"))
            date_part = d0 if (not d1 or d0 == d1) else f"{d0} – {d1}"
            owns = self._fmt_pct(h["ownership_after"]) if h.get("ownership_after") not in (None, 0) else None
            bits = [f"{h['filings']} filing{'s' if h['filings'] != 1 else ''}"]
            if date_part:
                bits.append(date_part)
            if owns:
                bits.append(f"owns {owns}")
            draw.text((cx + 30, ry + 44), " · ".join(bits), font=sub_fnt, fill="#9090a8")
            sh = format_shares(h["shares"])
            draw.text((shares_right - draw.textlength(sh, font=num_fnt), ry + 2), sh, font=num_fnt, fill="#c0c0d0")
            val = currency_idr(h["value"]).replace("IDR ", "")
            draw.text((value_right - draw.textlength(val, font=num_fnt), ry + 2), val, font=num_fnt, fill="#F0EBE0")
            if idx < len(shown) - 1:
                self._alpha_line(image, (cx, cy + row_h - 1, x + width - pad, cy + row_h - 1), "#32323a", alpha=80, width=1)
            cy += row_h
        if overflow > 0:
            draw.text((cx + 30, cy + 2), f"+{overflow} more insider{'s' if overflow != 1 else ''}",
                      font=font("Inter-Italic.ttf", 20), fill="#9090a8")
        return y + card_h

    def render_insider_cluster_carousel_dark(self, cluster, filename_prefix=None, variant="story", story=None):
        from datetime import datetime, timedelta
        from ..data import fetch_daily_prices
        from PIL import ImageFilter

        W, H, M = 1080, 1350, 76
        HX = M + 32
        symbol, base = cluster["symbol"], cluster["base_symbol"]
        direction, roster = cluster["direction"], cluster["roster"]
        colors = self.IDX_CHAIN_COLORS
        accent = colors["buy"] if direction == "buy" else colors["sell"]
        palette = self.CLUSTER_PALETTE
        verb = "bought" if direction == "buy" else "sold"
        filing_count = cluster.get("filing_count") or len(cluster.get("points") or [])
        fd0, fd1 = cluster["first_date"], cluster["last_date"]
        filing_span = self._fmt_date(fd0) if fd0 == fd1 else f"{self._fmt_date(fd0)} – {self._fmt_date(fd1)}"
        points = sorted(cluster["points"], key=lambda p: (p.get("date") or "", p.get("price") or 0))
        total_value = cluster["total_value"] or 0
        total_shares = cluster["total_shares"] or 0
        is_signal = variant == "signal"
        prefix_kind = "insider_cluster_signal_dark" if is_signal else "insider_cluster_dark"
        prefix = filename_prefix or f"{prefix_kind}_{clean_slug(base + '_' + direction)}"
        paths = []

        try:
            since = (datetime.strptime(cluster["first_date"], "%Y-%m-%d") - timedelta(days=14)).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            since = None
        until = datetime.now().strftime("%Y-%m-%d")
        close_by_date = {}
        try:
            pdf = fetch_daily_prices(symbol, since=since, until=until)
            if pdf is not None and not pdf.empty:
                close_by_date = {str(d)[:10]: float(c) for d, c in zip(pdf["date"], pdf["close"]) if c is not None}
        except Exception as e:
            print(f"Cluster dark carousel price fetch failed for {symbol}: {e}")

        start_close = self._close_on_or_before(close_by_date, cluster["first_date"])
        latest_date = max(close_by_date) if close_by_date else None
        latest_close = close_by_date[latest_date] if latest_date else None
        market_move = ((latest_close - start_close) / start_close * 100) if (start_close and latest_close) else None
        avg_buy = (total_value / total_shares) if total_shares else None
        vs_avg = ((latest_close - avg_buy) / avg_buy * 100) if (avg_buy and latest_close) else None
        move_label = None
        if story is not None:
            # Hindsight story: move is trigger-computed over the 3/6/9mo horizon
            # since the last filing — honest for confirming AND contradicting.
            mv = story["move"] * 100
            hm = story["horizon_months"]
            move_dir = "up" if mv >= 0 else "down"
            move_label = f"Stock is {move_dir} {abs(mv):.0f}% in the {hm} months since"
        elif market_move is not None and not is_signal:
            move_dir = "up" if market_move >= 0 else "down"
            move_label = f"Stock is {move_dir} {market_move:+.0f}% since first filing"

        def compact(v):
            v = float(v or 0)
            if abs(v) >= 1e12: return f"{v / 1e12:,.2f}T"
            if abs(v) >= 1e9:  return f"{v / 1e9:,.2f}B"
            if abs(v) >= 1e6:  return f"{v / 1e6:,.2f}M"
            if abs(v) >= 1e3:  return f"{v / 1e3:,.1f}K"
            return f"{v:,.0f}"

        cluster_label = f"CLUSTER {direction.upper()}"
        HEAD_COLOR = "#FFFFFF"
        SUB_COLOR = "#C8C8D8"
        LABEL_COLOR = "#c0c0d0"

        _card_fill = self.IDX_DARK_CARD_FILL
        _border = self.IDX_DARK_BORDER

        def _pill(draw, image, x, y, text, border_color, h=48, arrow=None):
            pf = font("Inter-Bold.ttf", 22)
            tw = draw.textlength(text, font=pf)
            aw = 30 if arrow else 0
            pw = int(tw + 44 + aw)
            pill_ov = Image.new("RGBA", image.size, (0, 0, 0, 0))
            ImageDraw.Draw(pill_ov).rounded_rectangle((x, y, x + pw, y + h), radius=h // 2, fill=_card_fill)
            image.alpha_composite(pill_ov)
            draw.rounded_rectangle((x, y, x + pw, y + h), radius=h // 2, outline=border_color, width=2)
            draw.text((x + 22, y + (h - pf.size) // 2 - 2), text, font=pf, fill="#ffffff")
            if arrow:
                arx, ary, s = x + 22 + tw + 13, y + h // 2, 7
                pts = [(arx, ary + s), (arx + 2 * s, ary + s), (arx + s, ary - s)] if arrow == "up" \
                    else [(arx, ary - s), (arx + 2 * s, ary - s), (arx + s, ary + s)]
                draw.polygon(pts, fill=border_color)
            return x + pw

        def header_panel(draw, image, panel_bottom, subtitle):
            ex, ey = HX, 56
            x2 = _pill(draw, image, ex, ey, "INSIDER TRADING", "#F29942")
            _pill(draw, image, x2 + 16, ey, cluster_label, accent, arrow=("up" if direction == "buy" else "down"))
            logo_sz = 62
            self._logo(image, (W - M - 32 - logo_sz, ey + (48 - logo_sz) // 2), base, size=logo_sz, accent=accent)
            sty = ey + 76
            draw.text((ex, sty), subtitle, font=font("Inter-Bold.ttf", 24), fill=accent)
            return sty

        gap = 18
        sw = (W - 2 * M - 2 * gap) // 3
        buyers = "buyers" if direction == "buy" else "sellers"
        sy = 1000

        img = self._idx_fillings_bg()
        draw = ImageDraw.Draw(img)

        max_w = W - 2 * HX
        subject = f"{cluster['holder_count']} insiders {verb} {base}"
        clause = ""
        if story is None and market_move is not None and not is_signal:
            clause = f"as it fell {abs(market_move):.0f}%" if market_move < 0 else f"as it rose {market_move:.0f}%"
        hlines = [subject] + ([clause] if clause else [])
        hsize = 58
        while hsize > 34:
            hf = font("Inter-Bold.ttf", hsize)
            if all(draw.textlength(ln, font=hf) <= max_w for ln in hlines):
                break
            hsize -= 2
        else:
            hf = font("Inter-Bold.ttf", 34)
            hlines = wrap_text(draw, f"{subject} {clause}".strip(), hf, max_w, max_lines=2)

        n_lines = min(len(hlines), 2)
        head_start = 188
        line_gap = 10
        hy = head_start + n_lines * (hf.size + line_gap)
        sub_fnt = font("Inter-SemiBold.ttf", 28)
        sub_gap = 24
        panel_bottom = hy + sub_gap + 34 + 28

        header_panel(draw, img, panel_bottom, f"{base} · {filing_span}")
        for i, ln in enumerate(hlines[:2]):
            ly = head_start + i * (hf.size + line_gap)
            if i == 0 and ln == subject and base in ln:
                pre = ln[:ln.rfind(base)]
                self._draw_segments(draw, HX, ly, [(pre, HEAD_COLOR), (base, accent)], hf)
            else:
                draw.text((HX, ly), ln, font=hf, fill=HEAD_COLOR)
        verb_sub = "accumulated" if direction == "buy" else "sold"
        if is_signal:
            subhead = f"IDR {compact(total_value)} {verb_sub} · {format_shares(total_shares)} shares"
        else:
            subhead = f"IDR {compact(total_value)} {verb_sub} across {format_shares(total_shares)} shares"
        if move_label:
            subhead = f"IDR {compact(total_value)} {verb_sub} · {move_label}"
        draw.text((HX, hy + sub_gap), ellipsize_to_width(draw, subhead, sub_fnt, max_w), font=sub_fnt, fill=SUB_COLOR)

        chart = self._cluster_convergence_chart(
            close_by_date, points, roster, palette, figsize=(11, 4.6), avg_buy=avg_buy,
            dots_label=f"Insider avg {direction}", show_legend=True, ylabel="AVG BUY PRICE (IDR)" if direction == "buy" else "AVG SELL PRICE (IDR)",
            face="none", label_color=LABEL_COLOR, shade_color=accent,
            marker_edge_color=None)
        chart_y = panel_bottom + 36
        chart_h = (sy - 32) - chart_y
        self._paste_chart(img, chart, M, chart_y, W - 2 * M, chart_h, center_v=True)

        self._dark_stat_card(img, draw, M, sy, sw, "INSIDERS", str(cluster["holder_count"]), f"distinct {buyers}", accent)
        self._dark_stat_card(img, draw, M + sw + gap, sy, sw, "COMBINED", f"IDR {compact(total_value)}", "total value", colors["market"])
        self._dark_stat_card(img, draw, M + 2 * (sw + gap), sy, sw, "SHARES", compact(total_shares),
                             "shares accumulated" if direction == "buy" else "shares sold", "#F29942")
        self._dark_page_dots(draw, W, 1180, 0, 2, accent)
        paths.append(self._save(img, f"{prefix}_1.png"))

        img = self._idx_fillings_bg()
        draw = ImageDraw.Draw(img)
        header_panel(draw, img, 200, f"{base} · {filing_span}")

        roster_bottom = self._dark_cluster_roster_card(img, draw, M, 252, W - 2 * M, roster, direction, accent, palette, max_rows=4, row_h=124)
        sy2 = roster_bottom + 44

        avg_lbl = "AVG PER SHARE"
        self._dark_stat_card(img, draw, M, sy2, sw, avg_lbl, f"IDR {avg_buy:,.0f}" if avg_buy else "-", "from filing totals", colors["avg"])
        self._dark_stat_card(img, draw, M + sw + gap, sy2, sw, "MARKET NOW", f"IDR {latest_close:,.0f}" if latest_close else "-",
                             self._fmt_date(latest_date) if latest_date else "", colors["market"])
        if vs_avg is not None:
            vs_color = colors["sell"] if vs_avg < 0 else colors["buy"]
            vs_sub = "market below filing price" if vs_avg < 0 else "market above filing price"
            self._dark_stat_card(img, draw, M + 2 * (sw + gap), sy2, sw, "MARKET VS FILING", f"{vs_avg:+.0f}%", vs_sub, vs_color, value_color=vs_color)
        else:
            self._dark_stat_card(img, draw, M + 2 * (sw + gap), sy2, sw, "MARKET VS FILING", "-", "", "#555566")
        self._dark_page_dots(draw, W, 1180, 1, 2, accent)
        paths.append(self._save(img, f"{prefix}_2.png"))

        return paths

    def render_insider_cross_card(self, cross, filename=None):
        """One self-contained 1080x1350 cross-stock card — data only.

        Header (who) + a basket table of every stock the holder traded
        (logo + direction + rupiah value bar) + three footer stats
        (total deployed / # stocks / net direction).
        """
        from PIL import ImageFilter

        W, H, M = 1080, 1350, 76
        HX = M + 32
        holder = cross["holder_name"]
        stocks = cross["stocks"]
        accent = "#5E4FA2"  # cross theme (Spectral purple); per-row dirs stay green/red
        BUY, SELL, MIX = self.CLUSTER_COLORS["buy"], self.CLUSTER_COLORS["sell"], "#F29942"

        def dcol(d):
            return BUY if d == "buy" else SELL if d == "sell" else MIX

        def dlabel(d):
            return "BUY" if d == "buy" else "SELL" if d == "sell" else "BUY + SELL"

        def compact(v):
            v = float(v or 0)
            if abs(v) >= 1e12: return f"{v / 1e12:,.2f}T"
            if abs(v) >= 1e9:  return f"{v / 1e9:,.2f}B"
            if abs(v) >= 1e6:  return f"{v / 1e6:,.2f}M"
            if abs(v) >= 1e3:  return f"{v / 1e3:,.1f}K"
            return f"{v:,.0f}"

        fd0, fd1 = cross["first_date"], cross["last_date"]
        filing_span = self._fmt_date(fd0) if fd0 == fd1 else f"{self._fmt_date(fd0)} – {self._fmt_date(fd1)}"
        total_value = cross["total_value"] or 0
        buy_value, sell_value = cross["buy_value"] or 0, cross["sell_value"] or 0
        peach = self._insider_bg().getpixel((60, 900))

        img = self._insider_bg()
        draw = ImageDraw.Draw(img)

        def _pill(x, y, text, fill, h=48):
            pf = font("Inter-Bold.ttf", 22)
            tw = draw.textlength(text, font=pf)
            w = tw + 44
            shl = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(shl).rounded_rectangle((x, y + 6, x + w, y + h + 6), radius=h // 2, fill=(70, 45, 20, 70))
            img.alpha_composite(shl.filter(ImageFilter.GaussianBlur(7)))
            draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=fill)
            draw.text((x + 22, y + (h - pf.size) // 2 - 2), text, font=pf, fill="#ffffff")
            return x + w

        # --- Header card ---
        draw.rectangle((0, 0, W, 300), fill=peach)
        header_bottom = 272
        self._card(draw, (M, 40, W - M, header_bottom), radius=30, fill="#ffffff", outline="#efe7da", width=2)
        ex, ey = HX, 88
        x2 = _pill(ex, ey, "INSIDER", "#F29942")
        _pill(x2 + 16, ey, "CROSS-STOCK", accent)
        # Up to 3 ticker logos, fanned right-to-left in the top-right.
        logo_sz = 56
        lx = W - M - 32 - logo_sz
        for st in stocks[:3]:
            self._logo(img, (lx, ey + (48 - logo_sz) // 2), st["base_symbol"], size=logo_sz, accent=accent)
            lx -= logo_sz + 14

        nf = self._fit_headline(draw, holder, W - 2 * HX, 46, 30)
        draw.text((HX, 150), ellipsize_to_width(draw, holder, nf, W - 2 * HX), font=nf, fill=COLORS["heading"])
        parts = []
        if cross["n_buy"]:
            parts.append(f"{cross['n_buy']} bought")
        if cross["n_sell"]:
            parts.append(f"{cross['n_sell']} sold")
        if cross["n_mixed"]:
            parts.append(f"{cross['n_mixed']} both")
        subhead = " · ".join(parts) + f" · {filing_span}"
        draw.text((HX, 218), ellipsize_to_width(draw, subhead, font("Inter-Bold.ttf", 24), W - 2 * HX),
                  font=font("Inter-Bold.ttf", 24), fill=accent)

        # --- Basket card (content-driven height; footer stats follow the row count) ---
        shown = stocks
        row_h = 112 if len(shown) <= 4 else 96
        card_y = header_bottom + 36
        card_bottom = card_y + 32 + 52 + 18 + len(shown) * row_h + 32
        self._card(draw, (M, card_y, W - M, card_bottom), radius=22, fill="#ffffff", outline="#eeeeee", width=2)
        pad = 32
        cx = M + pad
        cy = card_y + pad
        draw.text((cx, cy), "Stocks traded", font=font("Inter-Bold.ttf", 34), fill=COLORS["heading"])
        cnt = f"{cross['n_symbols']} stocks"
        cf = font("Inter-SemiBold.ttf", 26)
        draw.text((W - M - pad - draw.textlength(cnt, font=cf), cy + 10), cnt, font=cf, fill=accent)
        cy += 52
        draw.line((cx, cy, W - M - pad, cy), fill=accent, width=3)
        cy += 18

        max_val = max((s["value"] for s in shown), default=1) or 1

        logo_r = 50
        name_x = cx + logo_r + 20
        value_right = W - M - pad
        bar_x0 = name_x
        bar_x1 = value_right
        for idx, s in enumerate(shown):
            ry = cy + idx * row_h
            mid = ry + row_h / 2
            col = dcol(s["direction"])
            self._logo(img, (cx, int(mid - logo_r / 2), ), s["base_symbol"], size=logo_r, accent=col)
            # Symbol + inline direction chip
            sym_fnt = font("Inter-Bold.ttf", 30)
            draw.text((name_x, ry + row_h / 2 - 40), s["base_symbol"], font=sym_fnt, fill=COLORS["ink"])
            chip_x = name_x + draw.textlength(s["base_symbol"], font=sym_fnt) + 16
            lbl, lf = dlabel(s["direction"]), font("Inter-Bold.ttf", 16)
            lw = draw.textlength(lbl, font=lf)
            draw.rounded_rectangle((chip_x, ry + row_h / 2 - 36, chip_x + lw + 22, ry + row_h / 2 - 36 + 28), radius=10, fill=col)
            draw.text((chip_x + 11, ry + row_h / 2 - 36 + 5), lbl, font=lf, fill="#ffffff")
            # Sub: company name + filings + ownership
            company = self.company_profiles.get(s["symbol"]) or self.company_profiles.get(s["base_symbol"]) or s["base_symbol"]
            owns = self._fmt_pct(s["ownership_after"]) if s.get("ownership_after") not in (None, 0) else None
            bits = [str(company), f"{s['filings']} trade{'s' if s['filings'] != 1 else ''}"]
            if owns:
                bits.append(f"owns {owns}")
            sub = ellipsize_to_width(draw, " · ".join(bits), font("Inter-Regular.ttf", 18), (value_right - 180) - name_x)
            draw.text((name_x, ry + row_h / 2 - 4), sub, font=font("Inter-Regular.ttf", 18), fill=COLORS["muted"])
            # Value (right aligned, on the symbol line)
            val = f"IDR {compact(s['value'])}"
            vf = font("Inter-Bold.ttf", 30)
            draw.text((value_right - draw.textlength(val, font=vf), ry + row_h / 2 - 40), val, font=vf, fill=COLORS["ink"])
            # Value bar (proportional to the largest stock), under the row content
            by = ry + row_h / 2 + 30
            draw.rounded_rectangle((bar_x0, by, bar_x1, by + 12), radius=6, fill="#f0ece4")
            fillw = max(14, int((bar_x1 - bar_x0) * (s["value"] / max_val)))
            draw.rounded_rectangle((bar_x0, by, bar_x0 + fillw, by + 12), radius=6, fill=col)
            if idx < len(shown) - 1:
                draw.line((cx, ry + row_h, W - M - pad, ry + row_h), fill="#f5f1ea", width=1)

        # --- Footer stats ---
        gap = 18
        sw = (W - 2 * M - 2 * gap) // 3
        sy = card_bottom + 24
        self._stat_card(draw, M, sy, sw, "TOTAL", f"IDR {compact(total_value)}", "value traded", self.CLUSTER_COLORS["market"])
        self._stat_card(draw, M + sw + gap, sy, sw, "STOCKS", str(cross["n_symbols"]), "distinct tickers", accent)
        if sell_value == 0:
            self._stat_card(draw, M + 2 * (sw + gap), sy, sw, "MIX", f"{cross['n_buy']} buy", "all buy-side", BUY, value_color=BUY)
        elif buy_value == 0:
            self._stat_card(draw, M + 2 * (sw + gap), sy, sw, "MIX", f"{cross['n_sell']} sell", "all sell-side", SELL, value_color=SELL)
        else:
            mix_value = f"{cross['n_buy']} buy / {cross['n_sell']} sell"
            if cross["n_mixed"]:
                mix_value = f"{mix_value} / {cross['n_mixed']} both"
            self._stat_card(draw, M + 2 * (sw + gap), sy, sw, "MIX", mix_value, "stock directions", MIX)

        prefix = filename or f"insider_cross_{clean_slug(holder)}.png"
        return self._save(img, prefix)

    def render_insider_cross_card_dark(self, cross, filename=None):
        """Two-slide cross-stock carousel (one holder active across >=2 stocks).

        Slide 1 (the story): who + a plain-English sentence + the money-per-stock
        bar chart so a non-finance viewer SEES the breadth at a glance.
        Slide 2 (the detail): per-stock roster with direction-aware outcomes
        (a stock falling AFTER a sale is a good exit, shown green — not a loss).
        """
        W, H, M = 1080, 1350, 76
        HX = M + 32
        holder = cross["holder_name"]
        stocks = cross["stocks"]
        accent = "#5E4FA2"
        colors = self.IDX_CHAIN_COLORS
        BUY = colors["buy"]
        SELL = colors["sell"]
        MIX = "#F29942"
        HEAD_COLOR = "#FFFFFF"
        SUB_COLOR = "#C8C8D8"
        LABEL_COLOR = "#c0c0d0"
        n_sym = cross["n_symbols"]

        def dcol(d):
            return BUY if d == "buy" else SELL if d == "sell" else MIX

        def dlabel(d):
            return "Bought" if d == "buy" else "Sold" if d == "sell" else "Bought & sold"

        def compact(v):
            v = float(v or 0)
            if abs(v) >= 1e12: return f"{v / 1e12:,.2f}T"
            if abs(v) >= 1e9:  return f"{v / 1e9:,.2f}B"
            if abs(v) >= 1e6:  return f"{v / 1e6:,.2f}M"
            if abs(v) >= 1e3:  return f"{v / 1e3:,.1f}K"
            return f"{v:,.0f}"

        def short_date(date_str):
            from datetime import datetime
            try:
                return datetime.strptime(str(date_str)[:10], "%Y-%m-%d").strftime("%b %d")
            except (TypeError, ValueError):
                return str(date_str)[:10]

        fd0, fd1 = cross["first_date"], cross["last_date"]
        filing_span = short_date(fd0) if fd0 == fd1 else f"{short_date(fd0)} – {short_date(fd1)}"
        total_value = cross["total_value"] or 0
        buy_value, sell_value = cross["buy_value"] or 0, cross["sell_value"] or 0
        net_value = buy_value - sell_value
        total_filings = sum(int(s.get("filings") or 0) for s in stocks)

        # --- Plain-English story line (no pronouns — holders can be companies). ---
        if buy_value and sell_value:
            if abs(net_value) < 1:
                story_line = f"Buying and selling — {n_sym} stocks"
                stance_color = MIX
            elif net_value > 0:
                story_line = f"Mostly buying — across {n_sym} stocks"
                stance_color = BUY
            else:
                story_line = f"Mostly selling — across {n_sym} stocks"
                stance_color = SELL
        elif buy_value:
            story_line = f"Bought into {n_sym} different stocks"
            stance_color = BUY
        elif sell_value:
            story_line = f"Sold out of {n_sym} different stocks"
            stance_color = SELL
        else:
            story_line = f"Traded across {n_sym} stocks"
            stance_color = accent

        # --- Sub-line with spelled-out money (ibu-ibu test). ---
        flow_bits = []
        if buy_value:
            flow_bits.append(f"Bought IDR {self._money_words(buy_value)}")
        if sell_value:
            flow_bits.append(f"Sold IDR {self._money_words(sell_value)}")
        flow_bits.append(f"{total_filings} filing{'s' if total_filings != 1 else ''}")
        subline = "  ·  ".join(flow_bits)
        prefix = filename or f"insider_cross_dark_{clean_slug(holder)}"
        paths = []

        # --- Fetch return-since-entry for each stock upfront ---
        from datetime import datetime, timedelta
        from ..data import fetch_daily_prices

        stock_returns = {}
        for s in stocks:
            sym = s["symbol"]
            all_dates = [p["date"] for p in s.get("points") or [] if p.get("date")]
            stock_fd = min(all_dates) if all_dates else fd0
            try:
                since = (datetime.strptime(stock_fd, "%Y-%m-%d") - timedelta(days=14)).strftime("%Y-%m-%d")
                pdf = fetch_daily_prices(sym, since=since, until=datetime.now().strftime("%Y-%m-%d"))
                if pdf is not None and not pdf.empty:
                    cbd = {str(d)[:10]: float(c) for d, c in zip(pdf["date"], pdf["close"]) if c is not None}
                    closes = sorted(cbd.items())
                    candidates = [(d, c) for d, c in closes if d <= stock_fd]
                    base = candidates[-1][1] if candidates else (closes[0][1] if closes else None)
                    latest = closes[-1][1] if closes else None
                    if base and latest:
                        stock_returns[s["base_symbol"]] = (latest / base - 1) * 100
            except Exception as e:
                print(f"Cross dark price fetch failed for {sym}: {e}")

        _card_fill = self.IDX_DARK_CARD_FILL
        _border = self.IDX_DARK_BORDER

        def _pill(draw, image, x, y, text, border_color, h=48):
            pf = font("Inter-Bold.ttf", 22)
            tw = draw.textlength(text, font=pf)
            pw = int(tw + 44)
            pill_ov = Image.new("RGBA", image.size, (0, 0, 0, 0))
            ImageDraw.Draw(pill_ov).rounded_rectangle((x, y, x + pw, y + h), radius=h // 2, fill=_card_fill)
            image.alpha_composite(pill_ov)
            draw.rounded_rectangle((x, y, x + pw, y + h), radius=h // 2, outline=border_color, width=2)
            draw.text((x + 22, y + (h - pf.size) // 2 - 2), text, font=pf, fill="#ffffff")
            return x + pw

        def header_block(draw, image):
            ex, ey = HX, 56
            x2 = _pill(draw, image, ex, ey, "INSIDER", "#F29942")
            _pill(draw, image, x2 + 16, ey, "CROSS STOCKS", accent)
            logo_sz = 56
            lx = W - M - 32 - logo_sz
            for st in stocks[:3]:
                self._logo(image, (lx, ey + (48 - logo_sz) // 2), st["base_symbol"], size=logo_sz, accent=accent)
                lx -= logo_sz + 14

        gap = 18
        sw = (W - 2 * M - 2 * gap) // 3

        # ====================== SLIDE 1 — STORY + CHART ======================
        img = self._idx_fillings_bg()
        draw = ImageDraw.Draw(img)
        header_block(draw, img)

        holder_fnt = self._fit_headline(draw, holder, W - 2 * HX, 46, 30)
        draw.text((HX, 144), ellipsize_to_width(draw, holder, holder_fnt, W - 2 * HX),
                  font=holder_fnt, fill=HEAD_COLOR)
        story_fnt = self._fit_headline(draw, story_line, W - 2 * HX, 36, 24)
        draw.text((HX, 204), ellipsize_to_width(draw, story_line, story_fnt, W - 2 * HX),
                  font=story_fnt, fill=stance_color)
        sub_fnt = font("Inter-SemiBold.ttf", 23)
        draw.text((HX, 252), ellipsize_to_width(draw, subline, sub_fnt, W - 2 * HX),
                  font=sub_fnt, fill=SUB_COLOR)

        sy = 1000
        chart = self._cross_money_bars_chart(stocks, figsize=(11, 5.8), face="none",
                                             label_color=LABEL_COLOR)
        chart_y = 312
        self._paste_chart(img, chart, M, chart_y, W - 2 * M, (sy - 32) - chart_y, center_v=True)

        # Consistent stat grid across both slides: left chip = accent ("what"),
        # middle chip = orange ("secondary"), right chip = blue (the TOTAL money).
        # Values stay off-white everywhere — matches the cluster/chain family, where
        # only a directional ± metric is ever coloured.
        self._dark_stat_card(img, draw, M, sy, sw, "STOCKS", str(n_sym), "different stocks", accent)
        self._dark_stat_card(img, draw, M + sw + gap, sy, sw, "FILINGS",
                             str(total_filings), "buy & sell orders", "#F29942")
        self._dark_stat_card(img, draw, M + 2 * (sw + gap), sy, sw, "TOTAL",
                             f"IDR {compact(total_value)}", "value traded", colors["market"])
        self._dark_page_dots(draw, W, 1180, 0, 2, accent)
        paths.append(self._save(img, f"{prefix}_1.png"))

        # ====================== SLIDE 2 — THE DETAIL ======================
        img = self._idx_fillings_bg()
        draw = ImageDraw.Draw(img)
        header_block(draw, img)

        shown = stocks[:4]
        overflow = max(0, len(stocks) - len(shown))
        row_h = 132

        pad = 32
        cx = M + pad
        value_right = W - M - pad
        split_parts = []
        if buy_value:
            split_parts.append(("Bought", buy_value, BUY))
        if sell_value:
            split_parts.append(("Sold", sell_value, SELL))
        is_mixed_direction = len(split_parts) > 1
        split_section = 112 if is_mixed_direction else 8

        card_y = 150
        card_bottom = card_y + 32 + 52 + 24 + split_section + len(shown) * row_h + (40 if overflow else 0) + 24
        card_ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(card_ov).rounded_rectangle((M, card_y, W - M, card_bottom), radius=22, fill=_card_fill)
        img.alpha_composite(card_ov)
        draw.rounded_rectangle((M, card_y, W - M, card_bottom), radius=22, outline=_border, width=2)

        cy = card_y + pad
        draw.text((cx, cy), "Where The Trades Happened", font=font("Inter-Bold.ttf", 34), fill="#FFFFFF")
        cnt = f"{n_sym} stocks"
        cf = font("Inter-SemiBold.ttf", 26)
        draw.text((W - M - pad - draw.textlength(cnt, font=cf), cy + 10), cnt, font=cf, fill=accent)
        cy += 52
        self._alpha_line(img, (cx, cy, W - M - pad, cy), accent, alpha=90, width=3)
        cy += 24

        if is_mixed_direction:
            draw.text((cx, cy), "Bought vs Sold", font=font("Inter-Bold.ttf", 22), fill="#F0EBE0")
            # Buy/sell make-up lives here (next to the split it describes), muted —
            # not as a bottom stat card, where it didn't read as a "stat".
            makeup_bits = []
            if cross["n_buy"]:
                makeup_bits.append(f"{cross['n_buy']} buy")
            if cross["n_sell"]:
                makeup_bits.append(f"{cross['n_sell']} sell")
            if cross["n_mixed"]:
                makeup_bits.append(f"{cross['n_mixed']} both")
            makeup = " · ".join(makeup_bits)
            mk_fnt = font("Inter-SemiBold.ttf", 19)
            draw.text((W - M - pad - draw.textlength(makeup, font=mk_fnt), cy + 3),
                      makeup, font=mk_fnt, fill="#8888a0")
            split_x0, split_x1 = cx, W - M - pad
            split_y = cy + 38
            split_w = split_x1 - split_x0
            split_ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(split_ov).rounded_rectangle((split_x0, split_y, split_x1, split_y + 18),
                                                       radius=9, fill=(255, 255, 255, 24))
            img.alpha_composite(split_ov)
            cursor = split_x0
            for idx, (_label, value, color) in enumerate(split_parts):
                if total_value <= 0:
                    continue
                seg_w = int(split_w * (value / total_value))
                if idx == len(split_parts) - 1:
                    seg_w = split_x1 - cursor
                seg_w = max(4, seg_w)
                self._alpha_line(img, (cursor, split_y + 9, min(split_x1, cursor + seg_w), split_y + 9),
                                 color, alpha=230, width=18)
                cursor += seg_w
            legend_y = split_y + 34
            lx = cx
            split_label_fnt = font("Inter-SemiBold.ttf", 17)
            for label, value, color in split_parts:
                dot = 10
                draw.ellipse((lx, legend_y + 6, lx + dot, legend_y + 6 + dot), fill=color)
                text = f"{label} IDR {compact(value)}"
                txt = ellipsize_to_width(draw, text, split_label_fnt, 280)
                draw.text((lx + 18, legend_y), txt, font=split_label_fnt, fill="#c8c8d8")
                lx += 18 + draw.textlength(txt, font=split_label_fnt) + 28
            cy += split_section
        else:
            cy += 8

        logo_r = 50
        rank_w = 38
        logo_x = cx + rank_w + 14
        name_x = logo_x + logo_r + 20
        all_same_direction = len({st.get("direction", "buy") for st in shown}) == 1
        for idx, s in enumerate(shown):
            ry = cy + idx * row_h
            mid = ry + row_h / 2
            col = dcol(s["direction"])
            rank = str(idx + 1)
            rf = font("Inter-Bold.ttf", 22)
            rw = draw.textlength(rank, font=rf)
            draw.text((cx + (rank_w - rw) / 2, mid - 14), rank, font=rf, fill="#9090a8")
            self._logo(img, (logo_x, int(mid - logo_r / 2),), s["base_symbol"], size=logo_r, accent=col)
            sym_fnt = font("Inter-Bold.ttf", 30)
            draw.text((name_x, mid - 40), s["base_symbol"], font=sym_fnt, fill="#F0EBE0")
            if not all_same_direction:
                chip_x = name_x + draw.textlength(s["base_symbol"], font=sym_fnt) + 16
                lbl, lf = dlabel(s["direction"]), font("Inter-Bold.ttf", 15)
                lw = draw.textlength(lbl, font=lf)
                chip_ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
                ImageDraw.Draw(chip_ov).rounded_rectangle(
                    (chip_x, mid - 41, chip_x + lw + 22, mid - 41 + 28), radius=10, fill=_card_fill)
                img.alpha_composite(chip_ov)
                draw.rounded_rectangle((chip_x, mid - 41, chip_x + lw + 22, mid - 41 + 28),
                                       radius=10, outline=col, width=1)
                draw.text((chip_x + 11, mid - 41 + 5), lbl, font=lf, fill="#ffffff")
            company = self.company_profiles.get(s["symbol"]) or self.company_profiles.get(s["base_symbol"]) or s["base_symbol"]
            stock_pts = sorted([p for p in (s.get("points") or []) if p.get("share_percentage_after")],
                               key=lambda p: p.get("date") or "")
            own_val = stock_pts[-1]["share_percentage_after"] if stock_pts else s.get("ownership_after")
            owns = self._fmt_pct(own_val) if own_val not in (None, 0) else None
            bits = [str(company), f"{s['filings']} filing{'s' if s['filings'] != 1 else ''}"]
            if owns:
                bits.append(f"owns {owns}")
            sub = ellipsize_to_width(draw, " · ".join(bits), font("Inter-Regular.ttf", 18), (value_right - 180) - name_x)
            draw.text((name_x, mid + 6), sub, font=font("Inter-Regular.ttf", 18), fill="#9090a8")
            val = f"IDR {compact(s['value'])}"
            vf = font("Inter-Bold.ttf", 28)
            ret = stock_returns.get(s["base_symbol"])
            direction = s.get("direction", "buy")
            if ret is not None:
                # Direction-aware outcome: a stock FALLING after a SALE is a good exit
                # (green), not a loss. Colour by whether the move helped the holder.
                # Mixed (bought & sold) stays neutral grey — no single "right" direction.
                if direction == "buy":
                    helped = ret >= 0
                    caption = f"{'up' if ret >= 0 else 'down'} {abs(ret):.0f}% since the buy"
                    out_color = colors["buy"] if helped else colors["sell"]
                elif direction == "sell":
                    helped = ret < 0
                    caption = f"{'down' if ret < 0 else 'up'} {abs(ret):.0f}% after selling"
                    out_color = colors["buy"] if helped else colors["sell"]
                else:  # mixed
                    caption = f"stock {'up' if ret >= 0 else 'down'} {abs(ret):.0f}% since"
                    out_color = "#9aa0b4"
                cap_fnt = font("Inter-SemiBold.ttf", 18)
                draw.text((value_right - draw.textlength(val, font=vf), mid - 36), val, font=vf, fill="#F0EBE0")
                draw.text((value_right - draw.textlength(caption, font=cap_fnt), mid + 16),
                          caption, font=cap_fnt, fill=out_color)
            else:
                draw.text((value_right - draw.textlength(val, font=vf), mid - 14), val, font=vf, fill="#F0EBE0")
            if idx < len(shown) - 1:
                self._alpha_line(img, (cx, ry + row_h, W - M - pad, ry + row_h), "#32323a", alpha=80, width=1)
        if overflow:
            oy = cy + len(shown) * row_h + 6
            draw.text((name_x, oy), f"+{overflow} more stock{'s' if overflow != 1 else ''} not shown",
                      font=font("Inter-Italic.ttf", 20), fill="#9090a8")

        # Slide-2 stats mirror slide 1's grid for consistency: accent / orange / blue
        # chips, off-white values. BIGGEST (the standout position) / PERIOD / TOTAL.
        sy2 = card_bottom + 28
        top_stock = max(stocks, key=lambda x: x.get("value") or 0) if stocks else None
        if top_stock:
            self._dark_stat_card(img, draw, M, sy2, sw, "BIGGEST", top_stock["base_symbol"],
                                 f"IDR {compact(top_stock['value'])}", accent)
        else:
            self._dark_stat_card(img, draw, M, sy2, sw, "STOCKS", str(n_sym), "different stocks", accent)
        self._dark_stat_card(img, draw, M + sw + gap, sy2, sw, "PERIOD", filing_span, "filing dates", "#F29942")
        self._dark_stat_card(img, draw, M + 2 * (sw + gap), sy2, sw, "TOTAL",
                             f"IDR {compact(total_value)}", "value traded", colors["market"])
        self._dark_page_dots(draw, W, 1180, 1, 2, accent)
        paths.append(self._save(img, f"{prefix}_2.png"))

        return paths

    def _dark_pill(self, draw, image, x, y, text, border_color, h=48, arrow=None):
        """Glass pill (same treatment as the chain/cluster header pills)."""
        pf = font("Inter-Bold.ttf", 22)
        tw = draw.textlength(text, font=pf)
        aw = 30 if arrow else 0
        pw = int(tw + 44 + aw)
        ov = Image.new("RGBA", image.size, (0, 0, 0, 0))
        ImageDraw.Draw(ov).rounded_rectangle((x, y, x + pw, y + h), radius=h // 2,
                                             fill=self.IDX_DARK_CARD_FILL)
        image.alpha_composite(ov)
        draw.rounded_rectangle((x, y, x + pw, y + h), radius=h // 2, outline=border_color, width=2)
        draw.text((x + 22, y + (h - pf.size) // 2 - 2), text, font=pf, fill="#ffffff")
        if arrow:
            arx, ary, s = x + 22 + tw + 13, y + h // 2, 7
            pts = [(arx, ary + s), (arx + 2 * s, ary + s), (arx + s, ary - s)] if arrow == "up" \
                else [(arx, ary - s), (arx + 2 * s, ary - s), (arx + s, ary + s)]
            draw.polygon(pts, fill=border_color)
        return x + pw

    @staticmethod
    def _compact_num(v):
        v = float(v or 0)
        if abs(v) >= 1e12: return f"{v / 1e12:,.2f}T"
        if abs(v) >= 1e9:  return f"{v / 1e9:,.2f}B"
        if abs(v) >= 1e6:  return f"{v / 1e6:,.2f}M"
        if abs(v) >= 1e3:  return f"{v / 1e3:,.1f}K"
        return f"{v:,.0f}"

    @staticmethod
    def _money_words(v):
        """Spelled-out money for the ibu-ibu test: 'IDR 11.9 billion', not 'IDR 11.94B'."""
        v = float(v or 0)
        a = abs(v)
        if a >= 1e12: return f"{v / 1e12:,.1f} trillion"
        if a >= 1e9:  return f"{v / 1e9:,.1f} billion"
        if a >= 1e6:  return f"{v / 1e6:,.0f} million"
        if a >= 1e3:  return f"{v / 1e3:,.0f} thousand"
        return f"{v:,.0f}"

    @staticmethod
    def _unit_word(max_v):
        """Pick a divisor + spelled unit word from the largest value on a chart."""
        a = abs(float(max_v or 0))
        if a >= 1e12: return 1e12, "trillion"
        if a >= 1e9:  return 1e9, "billion"
        if a >= 1e6:  return 1e6, "million"
        return 1e3, "thousand"

    def _becoming_price_chart(self, close_by_date, cross_date, cross_price, accent,
                              figsize=(11, 4.6), face="none", label_color="#c0c0d0", title=None):
        """Slide-1 chart: the share price over time, with a dot for the purchase.

        Deliberately NOT labelled '5%' — that's an ownership figure and would
        confuse it with the price axis. The dot just says 'bought here'.
        """
        import io
        from datetime import datetime
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if not close_by_date:
            return None
        items = sorted(close_by_date.items())
        xs = [datetime.strptime(d, "%Y-%m-%d") for d, _ in items]
        ys = [c for _, c in items]

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_alpha(0.0)
        ax.set_facecolor("none" if face in (None, "none") else face)
        ax.plot(xs, ys, color="#7FB3D5", linewidth=2.2, zorder=2)
        ax.fill_between(xs, ys, min(ys), color="#3288BD", alpha=0.08, zorder=1)

        try:
            cd = datetime.strptime(cross_date, "%Y-%m-%d")
            cy = cross_price or self._close_on_or_before(close_by_date, cross_date)
            if cy:
                ax.axvline(cd, color=accent, linestyle="--", linewidth=1.6, alpha=0.7, zorder=2)
                ax.scatter([cd], [cy], s=190, color=accent, edgecolors="white",
                           linewidths=2, zorder=4)
                ax.annotate("bought here", (cd, cy), textcoords="offset points",
                            xytext=(0, 18), ha="center", fontsize=12, fontweight="bold",
                            color=accent)
        except (ValueError, TypeError):
            pass

        ax.tick_params(colors=label_color, labelsize=11)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color("#555")
        ax.grid(True, alpha=0.22, linestyle="--", color="#444")
        ax.set_title(title or "Share price (IDR)", loc="left", fontsize=12,
                     color="#e8e8f0", pad=10, fontweight="bold")
        import matplotlib.dates as mdates
        # Choose tick granularity by span so a short history doesn't repeat the
        # same month label ("May '26 May '26 May '26"). Day labels when the
        # window is narrow; month labels (one per month) when it's wide.
        span_days = (xs[-1] - xs[0]).days if len(xs) > 1 else 0
        if span_days <= 75:
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=6))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        else:
            # One tick per N months (N grows with span) so each label is a
            # distinct month and the axis never crowds.
            month_interval = max(1, round(span_days / 30 / 6))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=month_interval))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
        plt.setp(ax.xaxis.get_majorticklabels(), ha="right")

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", transparent=True)
        buf.seek(0)
        chart = Image.open(buf).convert("RGBA")
        plt.close(fig)
        return chart

    def _becoming_trajectory_chart(self, trajectory, accent, figsize=(11, 4.4),
                                   face="none", label_color="#c0c0d0",
                                   stake_before=None, stake_after=None, title=None):
        """Slide-2 chart: ownership % over time crossing the dashed 5% threshold.

        With a real multi-filing accumulation path it plots stake-over-time; when
        only the single crossing filing exists it falls back to a Before → After
        slope (from that filing's own before/after) so the crossing still reads.
        """
        import io
        from datetime import datetime
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        usable = sorted([t for t in trajectory if t.get("pct") is not None and t.get("date")],
                        key=lambda t: t["date"])
        if len(usable) >= 2:
            xs = list(range(len(usable)))
            ys = [t["pct"] for t in usable]
            try:
                labels = [datetime.strptime(t["date"], "%Y-%m-%d").strftime("%-d %b") for t in usable]
            except ValueError:
                labels = [datetime.strptime(t["date"], "%Y-%m-%d").strftime("%d %b") for t in usable]
        elif stake_before is not None and stake_after is not None:
            # Single-filing crossing — show the before→after slope over the 5% line.
            xs, ys, labels = [0, 1], [stake_before, stake_after], ["Before", "After filing"]
        elif len(usable) == 1:
            xs, ys, labels = [0], [usable[0]["pct"]], ["After filing"]
        else:
            return None

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_alpha(0.0)
        ax.set_facecolor("none" if face in (None, "none") else face)

        top = max(max(ys), 5) * 1.18
        ax.axhspan(5, top, color=accent, alpha=0.07, zorder=1)
        ax.axhline(5, color=accent, linestyle="--", linewidth=1.8, alpha=0.9, zorder=2)
        ax.text(0, 5, "  5% = becomes a major owner", va="bottom", ha="left",
                fontsize=12, color=accent, fontweight="bold")

        ax.plot(xs, ys, color="#F0EBE0", linewidth=2.6, zorder=3, marker="o",
                markersize=11, markerfacecolor=accent, markeredgecolor="white",
                markeredgewidth=1.6)
        for x, y in zip(xs, ys):
            ax.text(x, y + top * 0.03, f"{y:.2f}%", ha="center", va="bottom",
                    fontsize=12, color="#e8e8f0", fontweight="bold")

        ax.set_ylim(min(min(ys), 4) * 0.9, top)
        ax.set_xticks(xs)
        ax.set_xticklabels(labels, fontsize=12, rotation=30 if len(usable) > 5 else 0, ha="right")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{v:.0f}%"))
        ax.tick_params(colors=label_color, labelsize=11)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color("#555")
        ax.grid(True, axis="y", alpha=0.22, linestyle="--", color="#444")
        ax.set_title(title or "Ownership of the company (%)", loc="left",
                     fontsize=12, color="#e8e8f0", pad=10, fontweight="bold")

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", transparent=True)
        buf.seek(0)
        chart = Image.open(buf).convert("RGBA")
        plt.close(fig)
        return chart

    def render_becoming_insider_dark(self, event, filename_prefix=None):
        """Two-slide 'becoming insider' carousel on the IDX Fillings dark bg.

        Slide 1 (the milestone): headline that a holder crossed 5% + the buy
        that did it + market-price chart with the crossing marked + 3 stats.
        Slide 2 (the road to 5%): ownership trajectory crossing the threshold +
        accumulation stats.
        """
        from datetime import datetime, timedelta
        from ..data import fetch_daily_prices

        W, H, M = 1080, 1350, 76
        HX = M + 32
        symbol, base = event["symbol"], event["base_symbol"]
        holder = event["holder_name"]
        accent = self.IDX_CHAIN_COLORS["buy"]   # crossing up is always an accumulation
        colors = self.IDX_CHAIN_COLORS
        compact = self._compact_num
        cross_span = self._fmt_date(event["cross_date"])
        prefix = filename_prefix or f"becoming_insider_{clean_slug(base + '_' + holder)}"
        paths = []

        try:
            since = (datetime.strptime(event["first_date"], "%Y-%m-%d") - timedelta(days=21)).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            since = None
        until = datetime.now().strftime("%Y-%m-%d")
        close_by_date = {}
        try:
            pdf = fetch_daily_prices(symbol, since=since, until=until)
            if pdf is not None and not pdf.empty:
                close_by_date = {str(d)[:10]: float(c) for d, c in zip(pdf["date"], pdf["close"]) if c is not None}
        except Exception as e:
            print(f"Becoming-insider price fetch failed for {symbol}: {e}")

        latest_date = max(close_by_date) if close_by_date else None
        latest_close = close_by_date[latest_date] if latest_date else None
        avg_buy = event.get("avg_price")
        vs_avg = ((latest_close - avg_buy) / avg_buy * 100) if (avg_buy and latest_close) else None

        HEAD_COLOR, SUB_COLOR, LABEL_COLOR = "#FFFFFF", "#C8C8D8", "#c0c0d0"
        kind_label = "INSTITUTION" if event["holder_type"] == "institution" else "INSIDER"

        money = self._money_words

        def header_panel(draw, image, subtitle):
            ex, ey = HX, 56
            x2 = self._dark_pill(draw, image, ex, ey, "MAJOR SHAREHOLDER", "#F29942")
            self._dark_pill(draw, image, x2 + 16, ey, "PASSED 5%", accent, arrow="up")
            logo_sz = 62
            self._logo(image, (W - M - 32 - logo_sz, ey + (48 - logo_sz) // 2), base, size=logo_sz, accent=accent)
            draw.text((ex, ey + 76), subtitle, font=font("Inter-Bold.ttf", 24), fill=accent)

        gap = 18
        sw = (W - 2 * M - 2 * gap) // 3
        sy = 1000

        # ============ SLIDE 1 — the milestone ============
        img = self._idx_fillings_bg()
        draw = ImageDraw.Draw(img)
        max_w = W - 2 * HX

        subject = holder
        clause = f"now owns over 5% of {base}"
        hlines = [subject, clause]
        hsize = 58
        while hsize > 34:
            hf = font("Inter-Bold.ttf", hsize)
            if all(draw.textlength(ln, font=hf) <= max_w for ln in hlines):
                break
            hsize -= 2
        else:
            hf = font("Inter-Bold.ttf", 34)
            subject = ellipsize_to_width(draw, subject, hf, max_w)

        head_start = 188
        line_gap = 10
        header_panel(draw, img, f"{base} · {cross_span}")
        draw.text((HX, head_start), subject, font=hf, fill=HEAD_COLOR)
        ly = head_start + (hf.size + line_gap)
        pre = clause[:clause.find(base)]
        post = clause[clause.find(base) + len(base):]
        self._draw_segments(draw, HX, ly, [(pre, HEAD_COLOR), (base, accent), (post, HEAD_COLOR)], hf)

        hy = head_start + 2 * (hf.size + line_gap)
        subhead = "Owning 5%+ makes you a “major shareholder”"
        sub_fnt = font("Inter-SemiBold.ttf", 26)
        draw.text((HX, hy + 24), ellipsize_to_width(draw, subhead, sub_fnt, max_w),
                  font=sub_fnt, fill=SUB_COLOR)

        chart = self._becoming_price_chart(close_by_date, event["cross_date"],
                                           event.get("cross_price"), accent,
                                           figsize=(11, 4.6), face="none", label_color=LABEL_COLOR,
                                           title=f"{base} share price (IDR)")
        chart_y = hy + 24 + 40 + 30
        self._paste_chart(img, chart, M, chart_y, W - 2 * M, (sy - 32) - chart_y, center_v=True)

        self._dark_stat_card(img, draw, M, sy, sw, "OWNS NOW", f"{event['stake_after']:.2f}%",
                             f"up from {event['stake_before']:.2f}%", accent, value_color=accent)
        self._dark_stat_card(img, draw, M + sw + gap, sy, sw, "AMOUNT SPENT",
                             f"IDR {money(event['cross_value'])}", "on this purchase", colors["market"])
        self._dark_stat_card(img, draw, M + 2 * (sw + gap), sy, sw, "PRICE PAID",
                             f"IDR {event['cross_price']:,.0f}" if event.get("cross_price") else "-",
                             "per share", colors["avg"])
        self._dark_page_dots(draw, W, 1180, 0, 2, accent)
        paths.append(self._save(img, f"{prefix}_1.png"))

        # ============ SLIDE 2 — the road past 5% ============
        img = self._idx_fillings_bg()
        draw = ImageDraw.Draw(img)
        header_panel(draw, img, f"{base} · the road past 5%")

        chart2 = self._becoming_trajectory_chart(event["trajectory"], accent,
                                                 figsize=(11, 4.4), face="none", label_color=LABEL_COLOR,
                                                 stake_before=event.get("stake_before"),
                                                 stake_after=event.get("stake_after"),
                                                 title=f"Ownership of {base} (%)")
        chart2_y, chart2_h = 250, 470
        if chart2 is not None:
            self._paste_chart(img, chart2, M, chart2_y, W - 2 * M, chart2_h, center_v=True)

        sy2 = chart2_y + chart2_h + 26
        months = event.get("months") or 1
        self._dark_stat_card(img, draw, M, sy2, sw, "TIMES BOUGHT",
                             f"{event['filing_count']} time{'s' if event['filing_count'] != 1 else ''}",
                             f"in {months} month{'s' if months != 1 else ''}", accent)
        self._dark_stat_card(img, draw, M + sw + gap, sy2, sw, "TOTAL SPENT",
                             f"IDR {money(event['total_value'])}", "in total", colors["market"])
        if vs_avg is not None:
            vs_color = colors["sell"] if vs_avg < 0 else colors["buy"]
            vs_sub = "below the buy price" if vs_avg < 0 else "above the buy price"
            self._dark_stat_card(img, draw, M + 2 * (sw + gap), sy2, sw, "PRICE NOW",
                                 f"{vs_avg:+.0f}%", vs_sub, vs_color, value_color=vs_color)
        else:
            self._dark_stat_card(img, draw, M + 2 * (sw + gap), sy2, sw, "AVG PRICE PAID",
                                 f"IDR {avg_buy:,.0f}" if avg_buy else "-", "per share", colors["avg"])

        modules = [("WHY 5%?", "Anyone owning 5%+ must be publicly reported", "#F29942")]
        sig_y = sy2 + 164 + 22
        self._dark_signal_card(draw, img, M, sig_y, W - 2 * M, modules, accent, header="GOOD TO KNOW")
        self._dark_page_dots(draw, W, 1180, 1, 2, accent)
        paths.append(self._save(img, f"{prefix}_2.png"))

        return paths

    def _earnings_metric_bars(self, quarters, value_key, accent, title, growth=None,
                              figsize=(11, 4.6), face="none", label_color="#c0c0d0"):
        """Quarterly bars for one metric (profit or sales), with the YoY comparison
        made explicit: the same-quarter-last-year bar and the now bar are both
        highlighted and labelled 'last year' / 'now', and the % change is called
        out above the now bar. Everything else stays grey context.
        """
        import io
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        usable = [q for q in quarters if q.get(value_key) is not None]
        if len(usable) < 2:
            return None

        max_v = max(abs(q[value_key]) for q in usable) or 1
        div, unit = self._unit_word(max_v)
        abbr = {"trillion": "T", "billion": "B", "million": "M", "thousand": "K"}.get(unit, "")
        vals = [q[value_key] / div for q in usable]
        labels = [q["label"].replace("-", " ") for q in usable]

        has_yoy = len(usable) >= 5
        now_i = len(usable) - 1
        yoy_i = len(usable) - 5 if has_yoy else None
        if has_yoy:
            labels[yoy_i] = labels[yoy_i] + "\n(last year)"
            labels[now_i] = labels[now_i] + "\n(now)"

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_alpha(0.0)
        ax.set_facecolor("none" if face in (None, "none") else face)

        light = "#9aa0ad"            # the 'last year' comparison bar
        context = "#7a8294"          # the in-between quarters (drawn translucent below)
        cols = [context] * len(usable)
        cols[now_i] = accent
        if has_yoy:
            cols[yoy_i] = light
        # Context quarters fade back so the eye lands on last-year vs now.
        alphas = [0.28] * len(usable)
        alphas[now_i] = 1.0
        if has_yoy:
            alphas[yoy_i] = 1.0
        bars = ax.bar(range(len(usable)), vals, color=cols, width=0.66, zorder=3)
        for bar, a in zip(bars, alphas):
            bar.set_alpha(a)
        for i, (bar, v) in enumerate(zip(bars, vals)):
            big = i in (now_i, yoy_i)
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + (max(vals) * 0.02 if v >= 0 else -max(vals) * 0.04),
                    f"IDR {v:.1f} {abbr}".rstrip(), ha="center",
                    va="bottom" if v >= 0 else "top",
                    fontsize=12 if big else 9,
                    color="#f0ebe0" if big else "#6f6f80", fontweight="bold")

        # Big % callout above the 'now' bar so the picture matches the headline.
        if growth is not None and has_yoy:
            ax.annotate(f"{growth * 100:+.0f}% vs last year",
                        (now_i, vals[now_i]), textcoords="offset points",
                        xytext=(0, 30), ha="center", fontsize=14, fontweight="bold",
                        color=accent)

        ax.set_xticks(range(len(usable)))
        ax.set_xticklabels(labels, fontsize=11, ha="center")
        ax.tick_params(colors=label_color, labelsize=11)
        ax.tick_params(axis="x", pad=10)  # lift date labels off the baseline
        # Single baseline: the bottom frame IS the zero line, so bars sit on one
        # axis. Only drop below zero (and draw a separate zero marker) when a bar
        # actually goes negative — otherwise the empty gap reads as a 2nd x-axis.
        top_v = max(vals)
        if min(vals) < 0:
            ax.axhline(0, color="#777", linewidth=1)
            bottom_v = min(vals) - top_v * 0.08
        else:
            bottom_v = 0
        ax.set_ylim(bottom=bottom_v, top=top_v * 1.22)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color("#555")
        ax.grid(True, axis="y", alpha=0.22, linestyle="--", color="#444")
        ax.set_title(f"{title} (IDR {unit}, each quarter)", loc="left", fontsize=12,
                     color="#e8e8f0", pad=12, fontweight="bold")

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", transparent=True)
        buf.seek(0)
        chart = Image.open(buf).convert("RGBA")
        plt.close(fig)
        return chart

    def render_earnings_spike_dark(self, spike, filename_prefix=None):
        """Two-slide 'earnings spike' carousel on the IDX Fillings dark bg.

        Plain-language, ibu-ibu-first:
        Slide 1 (the spike): 'X's profit jumped +N% vs last year' + profit-per-
        quarter bars with the same-quarter-last-year and now bars highlighted.
        Slide 2 (is it real): sales-per-quarter bars (same highlight) + plain
        stats (profit per share, company size) + a quality note.
        """
        W, H, M = 1080, 1350, 76
        HX = M + 32
        base = spike["base_symbol"]
        money = self._money_words
        g = spike["earnings_growth"]
        rg = spike.get("revenue_growth")
        is_drop = g < 0
        tag_text = "EARNINGS DROP" if is_drop else "EARNINGS SPIKE"
        accent = self.IDX_CHAIN_COLORS["buy"] if g >= 0 else self.IDX_CHAIN_COLORS["sell"]
        colors = self.IDX_CHAIN_COLORS
        kind = "drop" if is_drop else "spike"
        prefix = filename_prefix or f"earnings_{kind}_{clean_slug(base)}"
        paths = []

        HEAD_COLOR, SUB_COLOR, LABEL_COLOR = "#FFFFFF", "#C8C8D8", "#c0c0d0"
        sector = spike.get("sub_sector") or spike.get("sector") or ""

        def header_panel(draw, image, subtitle):
            ex, ey = HX, 56
            x2 = self._dark_pill(draw, image, ex, ey, tag_text, "#F29942")
            self._dark_pill(draw, image, x2 + 16, ey, f"{g * 100:+.0f}% vs last year", accent,
                            arrow=("up" if g >= 0 else "down"))
            logo_sz = 62
            self._logo(image, (W - M - 32 - logo_sz, ey + (48 - logo_sz) // 2), base, size=logo_sz, accent=accent)
            draw.text((ex, ey + 76), subtitle, font=font("Inter-Bold.ttf", 24), fill=accent)

        gap = 18
        sw = (W - 2 * M - 2 * gap) // 3
        sy = 1000

        # ============ SLIDE 1 — the spike ============
        img = self._idx_fillings_bg()
        draw = ImageDraw.Draw(img)
        max_w = W - 2 * HX

        name = spike.get("company_name") or base
        hf = self._fit_headline(draw, name, max_w, 56, 34)
        clause = "profit fell" if is_drop else "profit jumped"
        cf = font("Inter-Bold.ttf", 56)
        while cf.size > 34 and draw.textlength(clause, font=cf) > max_w:
            cf = font("Inter-Bold.ttf", cf.size - 2)

        head_start = 184
        line_gap = 10
        header_panel(draw, img, f"{base} · latest quarter · {sector}")
        draw.text((HX, head_start), ellipsize_to_width(draw, name, hf, max_w),
                  font=hf, fill=HEAD_COLOR)
        ly = head_start + (hf.size + line_gap)
        end_x = self._draw_segments(draw, HX, ly, [(clause + " ", HEAD_COLOR)], cf)
        draw.text((end_x, ly), f"{g * 100:+.0f}%", font=cf, fill=accent)

        hy = head_start + (hf.size + line_gap) + (cf.size + line_gap)
        if rg is not None:
            verb = "grew" if rg >= 0 else "fell"
            link = "also " if (rg >= 0) == (g >= 0) else ""  # "also" only if same direction
            subhead = f"Revenue {link}{verb} {rg * 100:+.0f}% vs last year"
        else:
            subhead = "compared with the same quarter last year"
        sub_fnt = font("Inter-SemiBold.ttf", 28)
        draw.text((HX, hy + 18), ellipsize_to_width(draw, subhead, sub_fnt, max_w),
                  font=sub_fnt, fill=SUB_COLOR)

        chart = self._earnings_metric_bars(spike["quarters"], "earnings", accent,
                                           "Profit", growth=g,
                                           figsize=(11, 4.6), face="none", label_color=LABEL_COLOR)
        chart_y = hy + 18 + 40 + 28
        self._paste_chart(img, chart, M, chart_y, W - 2 * M, (sy - 32) - chart_y, center_v=True)

        self._dark_stat_card(img, draw, M, sy, sw, "PROFIT", f"{g * 100:+.0f}%",
                             "vs last year", accent, value_color=accent)
        if rg is not None:
            rcol = colors["buy"] if rg >= 0 else colors["sell"]
            self._dark_stat_card(img, draw, M + sw + gap, sy, sw, "REVENUE", f"{rg * 100:+.0f}%",
                                 "vs last year", rcol, value_color=rcol)
        else:
            self._dark_stat_card(img, draw, M + sw + gap, sy, sw, "REVENUE", "-", "", colors["market"])
        self._dark_stat_card(img, draw, M + 2 * (sw + gap), sy, sw, "THIS QUARTER",
                             f"IDR {money(spike['latest_earnings'])}" if spike.get("latest_earnings") else "-",
                             "in profit", colors["market"])
        self._dark_page_dots(draw, W, 1180, 0, 2, accent)
        paths.append(self._save(img, f"{prefix}_1.png"))

        # ============ SLIDE 2 — is it real ============
        img = self._idx_fillings_bg()
        draw = ImageDraw.Draw(img)
        header_panel(draw, img, f"{base} · {'what changed?' if is_drop else 'is the growth real?'}")

        # Revenue bars, same last-year-vs-now highlight as slide 1. Colour the 'now'
        # bar by revenue direction, exactly like profit: green up, orange-red down.
        rev_accent = (colors["market"] if rg is None
                      else colors["buy"] if rg >= 0 else colors["sell"])
        chart2 = self._earnings_metric_bars(spike["quarters"], "revenue", rev_accent,
                                            "Revenue", growth=rg,
                                            figsize=(11, 4.4), face="none", label_color=LABEL_COLOR)
        chart2_y, chart2_h = 250, 470
        if chart2 is not None:
            self._paste_chart(img, chart2, M, chart2_y, W - 2 * M, chart2_h, center_v=True)

        sy2 = chart2_y + chart2_h + 26
        rank = spike.get("market_cap_rank")
        # Keep slide-2 numbers consistent with the +N% headline: show profit/share
        # and SALES growth (same story), not the annual per-share figure which is a
        # different basis and reads as a contradictory second percentage.
        self._dark_stat_card(img, draw, M, sy2, sw, "PROFIT / SHARE",
                             f"IDR {spike['eps']:,.0f}" if spike.get("eps") else "-",
                             "for each share", accent)
        if rg is not None:
            rcol = colors["buy"] if rg >= 0 else colors["sell"]
            self._dark_stat_card(img, draw, M + sw + gap, sy2, sw, "REVENUE",
                                 f"{rg * 100:+.0f}%", "vs last year", rcol, value_color=rcol)
        else:
            self._dark_stat_card(img, draw, M + sw + gap, sy2, sw, "REVENUE", "-", "", colors["avg"])
        self._dark_stat_card(img, draw, M + 2 * (sw + gap), sy2, sw, "COMPANY SIZE",
                             f"#{rank}" if rank else "-", "biggest on IDX", colors["market"])

        if is_drop:
            if rg is not None and rg > 0:
                quality = "Sold more but earned less — costs grew faster"
            elif rg is not None and rg < 0:
                quality = "Profit AND revenue both fell — a real slowdown"
            else:
                quality = "Profit fell even though revenue held up"
            module_title = "WHAT HAPPENED?"
        else:
            if rg is not None and rg > 0:
                quality = "Both profit AND revenue are up — healthy growth"
            elif rg is not None and rg < 0:
                quality = "Profit up but revenue slipped — could be a one-off"
            else:
                quality = "Profit up mostly on margins or one-offs"
            module_title = "IS IT REAL?"
        modules = [(module_title, quality, "#F29942")]
        sig_y = sy2 + 164 + 22
        self._dark_signal_card(draw, img, M, sig_y, W - 2 * M, modules, accent, header="GOOD TO KNOW")
        self._dark_page_dots(draw, W, 1180, 1, 2, accent)
        paths.append(self._save(img, f"{prefix}_2.png"))

        return paths
