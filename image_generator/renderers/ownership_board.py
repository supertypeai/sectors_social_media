"""Ownership leaderboard — a single-slide, multi-ticker post.

A different post from the per-company `OwnershipRenderer`: instead of one stock
across two slides, this ranks a *bunch* of companies on one slide by how much a
single shareholder controls — a horizontal control-% bar beside each ticker.

The story in one glance (ibu-ibu test): "these well-known names are each almost
entirely owned by one party." Spectral blue = the ownership identity accent.
"""
import re
from pathlib import Path

from PIL import Image, ImageDraw

from ..render import SocialImageRenderer, font, ellipsize_to_width


class OwnershipBoardRenderer(SocialImageRenderer):
    ACCENT = "#3288BD"   # spectral blue — ownership / whole-company identity
    ORANGE = "#F29942"
    TRACK = "#26262e"    # bar track

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

    @staticmethod
    def _clean_holder(name: str) -> str:
        n = re.sub(r"\([^)]*\)", "", str(name or "")).strip()
        n = re.sub(r"(?i)\b(PT\.?|Tbk\.?|Limited|Ltd\.?|Pte\.?|Inc\.?)\b", "", n)
        n = re.sub(r"\s+", " ", n).strip(" .,-")
        return n or str(name or "").strip()

    def _board_slide(self, posts, filename):
        W, H, M = 1080, 1350, 76
        HX = M + 32
        accent = self.ACCENT
        n = len(posts)

        img = self._idx_fillings_bg()
        draw = ImageDraw.Draw(img)

        # --- header pills ---
        ex, ey = HX, 56
        x2 = self._dark_pill(draw, img, ex, ey, "OWNERSHIP", self.ORANGE)
        self._dark_pill(draw, img, x2 + 16, ey, f"TOP {n} MOST CONTROLLED", accent)

        # --- eyebrow + headline (one line) + subhead ---
        draw.text((HX, ey + 76), "IDX · SINGLE-OWNER CONTROL",
                  font=font("Inter-Bold.ttf", 24), fill=accent)
        hf = font("Inter-Bold.ttf", 46)
        self._draw_segments(draw, HX, 182,
                            [("One owner holds ", "#FFFFFF"), ("nearly all", accent),
                             (" of it", "#FFFFFF")], hf)
        sub_fnt = font("Inter-SemiBold.ttf", 26)
        draw.text((HX, 182 + 66),
                  f"The {n} biggest names each held by a single shareholder",
                  font=sub_fnt, fill="#C8C8D8")

        # --- leaderboard rows ---
        list_top = 344
        list_bot = 1168
        row_h = (list_bot - list_top) / n
        logo_sz = 46
        rank_col = M + 30             # right edge of the rank column (so "10" aligns)
        logo_x = rank_col + 26
        text_x = logo_x + logo_sz + 20
        bx0 = M + 392                 # bar track left (wider name column to the left)
        bx1 = W - M - 96              # bar track right (room for % label)
        bar_w = bx1 - bx0
        name_fnt = font("Inter-Bold.ttf", 30)
        own_fnt = font("Inter-Regular.ttf", 17)
        rank_fnt = font("Inter-Bold.ttf", 22)
        pct_fnt = font("Inter-Bold.ttf", 30)
        own_max = bx0 - text_x - 16

        for i, p in enumerate(posts):
            ry = list_top + i * row_h
            cy = ry + row_h / 2
            base = str(p["symbol"]).upper().split(".")[0]
            pct = p["controller"]["pct"] or 0
            owner = self._clean_holder(p["controller"]["name"])

            # rank (right-aligned so single & double digits line up away from logo)
            rnk = str(i + 1)
            draw.text((rank_col - draw.textlength(rnk, font=rank_fnt), cy - 13),
                      rnk, font=rank_fnt, fill="#9090a8")
            # logo
            self._logo(img, (logo_x, int(cy - logo_sz / 2)), base, size=logo_sz, accent=accent)
            # ticker + owner (owner wraps to 2 lines when long)
            own_lines = self._wrap_text(draw, owner, own_fnt, own_max, 2)
            if len(own_lines) == 1:
                draw.text((text_x, cy - 28), base, font=name_fnt, fill="#F0EBE0")
                draw.text((text_x, cy + 8), own_lines[0], font=own_fnt, fill="#9090a8")
            else:
                draw.text((text_x, cy - 38), base, font=name_fnt, fill="#F0EBE0")
                draw.text((text_x, cy - 2), own_lines[0], font=own_fnt, fill="#9090a8")
                draw.text((text_x, cy + 18), own_lines[1], font=own_fnt, fill="#9090a8")

            # bar track + fill
            by0, by1 = cy - 10, cy + 10
            track_ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(track_ov).rounded_rectangle((bx0, by0, bx1, by1), radius=10, fill=(255, 255, 255, 24))
            img.alpha_composite(track_ov)
            fill_w = max(2 * (by1 - by0) / 2, bar_w * pct)
            draw.rounded_rectangle((bx0, by0, bx0 + fill_w, by1), radius=10, fill=accent)

            # % label
            ptxt = f"{pct * 100:.0f}%"
            draw.text((W - M - draw.textlength(ptxt, font=pct_fnt), cy - 18),
                      ptxt, font=pct_fnt, fill="#F0EBE0")

            if i < n - 1:
                self._alpha_line(img, (M, ry + row_h, W - M, ry + row_h), "#32323a", alpha=70, width=1)

        return self._save(img, filename)

    def render(self, posts: list, top_n: int = 10, filename: str = "ownership_board.png") -> list[Path]:
        # Lead with the most recognizable (largest) names, ordered by concentration.
        sel = sorted(posts[:top_n], key=lambda p: p["controller"]["pct"] or 0, reverse=True)
        if not sel:
            return []
        return [self._board_slide(sel, filename)]
