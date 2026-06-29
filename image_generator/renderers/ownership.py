"""Ownership-concentration post — a single-ticker dark carousel.

Answers one plain question a non-finance viewer gets in a glance: "who actually
owns this company?" These are `single-entity-holding-70` names where one entity
controls 70%+ of the shares, leaving a thin public float. Two slides, following
the dark "IDX Filings" system in docs/DESIGN.md:

  Slide 1 (hook):  a 100-shares waffle grid — "if this company were 100 shares",
                   84 glow for the one owner, the rest stay dark. Countable, so
                   the imbalance hits in a glance. + "one owner controls X%".
  Slide 2 (prove): the named shareholder roster (who they are, % and value) plus
                   a "WHAT THIS MEANS" card translating the number into plain
                   consequences a non-finance viewer feels.
"""
import re
from pathlib import Path

from PIL import Image, ImageDraw

from ..render import SocialImageRenderer, font, ellipsize_to_width


class OwnershipRenderer(SocialImageRenderer):
    # Ownership identity accent: spectral blue = "total / whole-company" (not a
    # directional good/bad signal, so it never implies the concentration is bad).
    ACCENT = "#3288BD"
    ORANGE = "#F29942"
    OTHERS = "#5E6373"   # muted slate — named minority holders
    PUBLIC = "#C2C9D6"   # soft cloud — the free float

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def _clean_holder(name: str) -> str:
        """Shorten a holder name for display: drop legal cruft + parentheticals."""
        n = re.sub(r"\([^)]*\)", "", str(name or "")).strip()
        n = re.sub(r"(?i)\b(PT\.?|Tbk\.?|Limited|Ltd\.?|Pte\.?|Inc\.?)\b", "", n)
        n = re.sub(r"\s+", " ", n).strip(" .,-")
        return n or str(name or "").strip()

    @staticmethod
    def _waffle_counts(controller_pct, others_pct, public_pct):
        """Integer square counts [controller, others, public] summing to 100.

        Largest-remainder rounding so no square is lost and the owner block is
        exactly the headline percentage (rounded).
        """
        raw = [max(0.0, controller_pct) * 100,
               max(0.0, others_pct) * 100,
               max(0.0, public_pct) * 100]
        floors = [int(x) for x in raw]
        rem = 100 - sum(floors)
        order = sorted(range(3), key=lambda i: raw[i] - floors[i], reverse=True)
        for i in range(max(0, rem)):
            floors[order[i % 3]] += 1
        return floors

    def _draw_waffle(self, img, draw, center_x, top, grid_w, counts):
        """A 10x10 grid of rounded squares: owner squares glow, the rest recede.

        Returns the y of the grid's bottom edge.
        """
        cols = 10
        gap = 5
        cell = (grid_w - (cols - 1) * gap) / cols
        x0 = center_x - grid_w / 2
        radius = max(3, int(cell * 0.20))
        colors = [self.ACCENT, self.OTHERS, self.PUBLIC]

        seq = []
        for ci, n in enumerate(counts):
            seq.extend([colors[ci]] * max(0, n))
        seq = (seq + [self.OTHERS] * 100)[:100]

        ctrl_n = counts[0]
        for idx in range(100):
            r, c = divmod(idx, cols)
            x = x0 + c * (cell + gap)
            y = top + r * (cell + gap)
            col = seq[idx]
            draw.rounded_rectangle((x, y, x + cell, y + cell), radius=radius, fill=col)
            # A crisp white-ish keyline on the owner block makes it read as one mass.
            if idx < ctrl_n:
                draw.rounded_rectangle((x, y, x + cell, y + cell), radius=radius,
                                       outline="#9FD0EC", width=1)
        return top + cols * cell + (cols - 1) * gap

    @staticmethod
    def _draw_tracked(draw, x, y, text, fnt, fill, tracking=3):
        """Draw letter-spaced text (PIL has no native tracking) for label styling."""
        cx = x
        for ch in text:
            draw.text((cx, y), ch, font=fnt, fill=fill)
            cx += draw.textlength(ch, font=fnt) + tracking
        return cx

    @staticmethod
    def _wrap_text(draw, text, fnt, max_w, max_lines=2):
        """Greedy word-wrap into <= max_lines, ellipsizing the final line if needed."""
        words = str(text).split()
        lines, cur = [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if cur and draw.textlength(trial, font=fnt) > max_w:
                lines.append(cur)
                cur = w
                if len(lines) == max_lines:
                    # No room left — fold the remainder into the last line + ellipsis.
                    lines[-1] = ellipsize_to_width(draw, f"{lines[-1]} {w}…", fnt, max_w)
                    cur = ""
                    break
            else:
                cur = trial
        if cur:
            lines.append(cur)
        if not lines:
            lines = [str(text)]
        return [ellipsize_to_width(draw, ln, fnt, max_w) for ln in lines[:max_lines]]

    def _waffle_legend_v(self, draw, x, grid_top, grid_h, items, name_max):
        """Vertical key beside the grid, vertically centered against the grid.

        items: list of (label, count, color); the first item is the named owner.
        Names wrap to two lines so long owners aren't clipped in the narrow column.
        """
        f_name = font("Inter-Bold.ttf", 22)
        f_sub = font("Inter-Regular.ttf", 19)
        box, line_h, sub_h, gap = 32, 29, 32, 44

        wrapped = []
        for lbl, n, col in items:
            lines = self._wrap_text(draw, lbl, f_name, name_max, 3)
            block = max(box, len(lines) * line_h) + sub_h
            wrapped.append((lines, n, col, block))
        total = sum(w[3] for w in wrapped) + gap * (len(wrapped) - 1)
        y = grid_top + (grid_h - total) / 2

        for lines, n, col, block in wrapped:
            draw.rounded_rectangle((x, y + 3, x + box, y + 3 + box), radius=7, fill=col)
            tx = x + box + 16
            ly = y - 2
            for ln in lines:
                draw.text((tx, ly), ln, font=f_name, fill="#F0EBE0")
                ly += line_h
            draw.text((tx, ly + 2), f"{n} of 100 shares", font=f_sub, fill="#9090a8")
            y += block + gap

    # -- slide 1 -------------------------------------------------------------
    def _slide1(self, post, page, filename):
        W, H, M = 1080, 1350, 76
        HX = M + 32
        accent = self.ACCENT
        max_w = W - 2 * HX

        ctrl = post["controller"]
        ctrl_pct = ctrl["pct"] or 0
        public_pct = post["public_pct"] or 0
        base = str(post["symbol"]).upper().split(".")[0]

        img = self._idx_fillings_bg()
        draw = ImageDraw.Draw(img)

        # --- header pills + logo ---
        ex, ey = HX, 56
        x2 = self._dark_pill(draw, img, ex, ey, "OWNERSHIP", self.ORANGE)
        self._dark_pill(draw, img, x2 + 16, ey, f"{ctrl_pct * 100:.0f}% CONTROLLED", accent)
        logo_sz = 62
        self._logo(img, (W - M - 32 - logo_sz, ey + (48 - logo_sz) // 2), base,
                   size=logo_sz, accent=accent)

        # --- eyebrow ---
        rank = post.get("market_cap_rank")
        eyebrow = f"{base} · {post.get('sector') or 'IDX'}"
        if rank:
            eyebrow += f" · #{int(rank)} by size"
        draw.text((ex, ey + 76), eyebrow, font=font("Inter-Bold.ttf", 24), fill=accent)

        # --- headline (names the owner + the ticker) ---
        owner = self._clean_holder(ctrl["name"])
        line1 = f"{owner} controls"
        line2_text = f"{ctrl_pct * 100:.0f}% of {base}"
        head_start = 184
        line_gap = 10
        probe = font("Inter-Bold.ttf", 56)
        fit_on = line1 if draw.textlength(line1, font=probe) >= draw.textlength(line2_text, font=probe) else line2_text
        hf = self._fit_headline(draw, fit_on, max_w, 56)
        draw.text((HX, head_start), ellipsize_to_width(draw, line1, hf, max_w), font=hf, fill="#FFFFFF")
        ly = head_start + (hf.size + line_gap)
        self._draw_segments(draw, HX, ly,
                            [(f"{ctrl_pct * 100:.0f}%", accent), (f" of {base}", "#FFFFFF")], hf)

        hy = head_start + 2 * (hf.size + line_gap)
        subhead = f"The public holds just {public_pct * 100:.0f}% — a thin free float"
        sub_fnt = font("Inter-SemiBold.ttf", 26)
        draw.text((HX, hy + 22), ellipsize_to_width(draw, subhead, sub_fnt, max_w),
                  font=sub_fnt, fill="#C8C8D8")

        # --- waffle caption: a tracked label with a leading accent tick, clearly
        #     subordinate to the subhead (smaller, spaced, muted) ---
        cap = "IF THIS COMPANY WERE 100 SHARES"
        cap_fnt = font("Inter-Bold.ttf", 18)
        cap_y = hy + 22 + 100
        tick_y = cap_y + 6
        draw.rounded_rectangle((HX, tick_y, HX + 26, tick_y + 4), radius=2, fill=accent)
        self._draw_tracked(draw, HX + 42, cap_y, cap, cap_fnt, "#8A8AA0", tracking=3)

        # --- 100-shares waffle hero (big, left-aligned; legend stacked at right) ---
        counts = self._waffle_counts(ctrl_pct, post["others_pct"], public_pct)
        grid_w = 630
        grid_x = HX
        grid_top = cap_y + 48
        grid_bottom = self._draw_waffle(img, draw, grid_x + grid_w / 2, grid_top, grid_w, counts)
        grid_h = grid_bottom - grid_top

        # Legend names the actual owner (not a generic "One owner").
        items = [(self._clean_holder(ctrl["name"]), counts[0], self.ACCENT)]
        if counts[1] > 0:
            items.append(("Other holders", counts[1], self.OTHERS))
        if counts[2] > 0:
            items.append(("Public float", counts[2], self.PUBLIC))
        leg_x = grid_x + grid_w + 36
        name_max = (W - M) - leg_x - (32 + 16)
        self._waffle_legend_v(draw, leg_x, grid_top, grid_h, items, name_max)

        self._dark_page_dots(draw, W, 1180, page, 2, accent)
        return self._save(img, filename)

    # -- slide 2 -------------------------------------------------------------
    def _slide2(self, post, page, filename):
        W, H, M = 1080, 1350, 76
        HX = M + 32
        accent = self.ACCENT
        base = str(post["symbol"]).upper().split(".")[0]

        img = self._idx_fillings_bg()
        draw = ImageDraw.Draw(img)

        # --- header pills + logo ---
        ex, ey = HX, 56
        x2 = self._dark_pill(draw, img, ex, ey, "OWNERSHIP", self.ORANGE)
        self._dark_pill(draw, img, x2 + 16, ey, "WHO OWNS IT", accent)
        logo_sz = 62
        self._logo(img, (W - M - 32 - logo_sz, ey + (48 - logo_sz) // 2), base,
                   size=logo_sz, accent=accent)

        # --- roster card ---
        # Show every real holder, but don't waste a row on each co-owner that
        # rounds to ~0%: keep the meaningful holders, then fold the long tail into
        # one honest "+N smaller holders" line (no one is hidden, just summarised).
        MAX_ROWS = 5
        all_h = post["holders"]
        sig = [h for h in all_h if (h["pct"] or 0) >= 0.005]
        if len(all_h) > len(sig) or len(sig) > MAX_ROWS:
            holders = sig[:MAX_ROWS - 1]
            remaining = [h for h in all_h if h not in holders]
        else:
            holders = sig
            remaining = []
        n_total = len(all_h)
        has_public = post["public_pct"] > 0.001

        card_w = W - 2 * M
        pad = 32
        ROW_TALL, ROW_SHORT = 118, 84  # two-line rows vs single-line rows
        title_block = 92

        # Build the display rows: named holders, an optional aggregated tail, and
        # the public free float — all in one list so spacing is even.
        rows = []
        for i, h in enumerate(holders):
            rows.append({
                "rank": str(i + 1),
                "name": self._clean_holder(h["name"]),
                "sub": f"Rp {self._money_words(h['value'])}" if h.get("value") else None,
                "pct": f"{(h['pct'] or 0) * 100:.1f}%",
                "color": "#F0EBE0",
            })
        if remaining:
            k = len(remaining)
            combined = sum((h["pct"] or 0) for h in remaining)
            pct_txt = "<0.1%" if combined * 100 < 0.05 else f"{combined * 100:.1f}%"
            rows.append({
                "rank": "", "name": f"+{k} smaller holder" + ("s" if k != 1 else ""),
                "sub": None, "pct": pct_txt, "color": "#9090a8",
            })
        if has_public:
            rows.append({
                "rank": "", "name": "Public (free float)", "sub": None,
                "pct": f"{post['public_pct'] * 100:.1f}%", "color": "#C2C9D6",
            })
        for r in rows:
            r["h"] = ROW_TALL if r["sub"] else ROW_SHORT

        card_h = title_block + sum(r["h"] for r in rows) + pad

        # Card is top-anchored; the read-more CTA is pinned to a fixed bottom line.
        card_x, card_y = M, 200
        cta_y = 1090
        card_ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(card_ov).rounded_rectangle(
            (card_x, card_y, card_x + card_w, card_y + card_h), radius=22, fill=self.IDX_DARK_CARD_FILL)
        img.alpha_composite(card_ov)
        draw.rounded_rectangle((card_x, card_y, card_x + card_w, card_y + card_h),
                               radius=22, outline=self.IDX_DARK_BORDER, width=2)

        ix = card_x + pad
        iy = card_y + pad
        draw.text((ix, iy), "Who owns the company", font=font("Inter-Bold.ttf", 34), fill="#FFFFFF")
        cnt = f"{n_total} holder" + ("s" if n_total != 1 else "")
        cf = font("Inter-SemiBold.ttf", 26)
        draw.text((card_x + card_w - pad - draw.textlength(cnt, font=cf), iy + 4),
                  cnt, font=cf, fill=accent)
        self._alpha_line(img, (ix, iy + 52, card_x + card_w - pad, iy + 52), accent, alpha=90, width=3)

        ry = iy + 78
        name_fnt = font("Inter-Bold.ttf", 29)
        meta_fnt = font("Inter-Regular.ttf", 18)
        pct_fnt = font("Inter-SemiBold.ttf", 33)
        name_max = card_w - 2 * pad - 230
        for i, r in enumerate(rows):
            rh = r["h"]
            if r["rank"]:
                draw.text((ix, ry + 30), r["rank"], font=font("Inter-Bold.ttf", 22), fill="#9090a8")
            nx = ix + 44
            draw.text((nx, ry + 14), ellipsize_to_width(draw, r["name"], name_fnt, name_max),
                      font=name_fnt, fill=r["color"])
            if r["sub"]:
                draw.text((nx, ry + 56), r["sub"], font=meta_fnt, fill="#9090a8")
            draw.text((card_x + card_w - pad - draw.textlength(r["pct"], font=pct_fnt), ry + 22),
                      r["pct"], font=pct_fnt, fill=r["color"])
            if i < len(rows) - 1:
                self._alpha_line(img, (ix, ry + rh - 8, card_x + card_w - pad, ry + rh - 8),
                                 "#32323a", alpha=80, width=1)
            ry += rh

        # --- read-more CTA (pinned to a fixed bottom line) ---
        self._draw_read_more(img, draw, W, cta_y, base.lower(), accent)

        self._dark_page_dots(draw, W, 1180, page, 2, accent)
        return self._save(img, filename)

    # -- entry ---------------------------------------------------------------
    def render(self, post: dict, filename_prefix: str = "ownership") -> list[Path]:
        base = str(post["symbol"]).upper().split(".")[0].lower()
        prefix = f"{filename_prefix}_{base}"
        return [
            self._slide1(post, 0, f"{prefix}_1.png"),
            self._slide2(post, 1, f"{prefix}_2.png"),
        ]
