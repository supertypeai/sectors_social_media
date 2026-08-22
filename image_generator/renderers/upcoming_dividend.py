from PIL import Image, ImageDraw
from datetime import datetime
import pandas as pd

from image_generator.render import SocialImageRenderer, COLORS, font


MAX_ROWS_PER_PAGE = 7

# Story canvas (1080x1920) vs. the source background asset's native size
# (1200x1500, a portrait-feed ratio) - scaled uniformly by width so nothing
# in the baked-in artwork (title text, footer) stretches/distorts, then the
# canvas is extended to Story height using the empty gradient zone between
# the subtitle and the squiggle graphic (see _story_background below).
STORY_W, STORY_H = 1080, 1920
_SCALE = STORY_W / 1200

ROW_H = round(110 * _SCALE)
TABLE_BG = (30, 32, 38, 240)
SEP_COLOR = "#414146"
COL_LIGHT = "#bebebe"


class UpcomingDividendRenderer(SocialImageRenderer):

    def _story_background(self):
        """Fresh Story-sized (1080x1920) copy of upcoming_dividend.png.
        Uniformly scales to the target width (no distortion), then extends
        the canvas to Story height by tiling a band sampled from the empty
        gradient zone (no text/detail there) rather than stretching the
        whole image non-uniformly, which would distort the baked-in title
        and footer text.
        """
        original = self._open("upcoming_dividend.png")
        scaled = original.resize(
            (STORY_W, round(original.height * _SCALE)), Image.Resampling.LANCZOS
        )

        cut = 350  # empty zone starts here (below the subtitle), already in scaled coords
        band_h = 50
        extra = STORY_H - scaled.height

        canvas = Image.new("RGBA", (STORY_W, STORY_H), (0, 0, 0, 255))
        canvas.paste(scaled.crop((0, 0, STORY_W, cut)), (0, 0))

        band = scaled.crop((0, cut, STORY_W, cut + band_h))
        y = cut
        while y < cut + extra:
            h = min(band_h, cut + extra - y)
            canvas.paste(band.crop((0, 0, STORY_W, h)), (0, y))
            y += h

        canvas.paste(scaled.crop((0, cut, STORY_W, scaled.height)), (0, cut + extra))
        return canvas

    def get_background(self):
        return self._story_background()

    @staticmethod
    def _fmt_date(s):
        return datetime.strptime(s, "%Y-%m-%d").strftime("%d %B %Y")

    @staticmethod
    def _fmt_dividend(amount):
        if amount == int(amount):
            return f"IDR  {int(amount):,}"
        return f"IDR  {amount:,.2f}"

    def _render_page(self, df_page, page_num, total_pages, close_date_str):
        bg = self.get_background()
        W, H = bg.size

        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Every constant below is scaled by _SCALE (0.9) from the original
        # 1200-wide design, so the table's proportions/fit ratio against the
        # narrower 1080 Story canvas exactly match the original, validated
        # layout - just smaller, not re-tuned.
        PAD = round(60 * _SCALE)
        T_TOP = round(375 * _SCALE)
        T_L = PAD
        T_R = W - PAD
        HEADER_BLOCK = round(90 * _SCALE)
        BOTTOM_PAD = round(20 * _SCALE)
        n = len(df_page)

        T_BOT = T_TOP + HEADER_BLOCK + int(ROW_H * n) + BOTTOM_PAD
        draw.rounded_rectangle([T_L, T_TOP, T_R, T_BOT], radius=22, fill=TABLE_BG)

        IP = round(30 * _SCALE)
        SYM_X = T_L + IP
        DIV_X = T_L + round(280 * _SCALE)
        YLD_X = T_L + round(578 * _SCALE)
        CUM_X = T_L + round(890 * _SCALE)

        f_hdr = font("Inter-Bold.ttf", round(26 * _SCALE))
        f_hdr_sub = font("Inter-Regular.ttf", round(17 * _SCALE))
        f_sym = font("Inter-Bold.ttf", round(28 * _SCALE))
        f_val = font("Inter-Regular.ttf", round(26 * _SCALE))
        f_yld = font("Inter-Bold.ttf", round(26 * _SCALE))

        HDR_TOP = T_TOP + round(22 * _SCALE)
        draw.text((SYM_X + round(32 * _SCALE), HDR_TOP + round(6 * _SCALE)), "Symbol", fill=COLORS["orange"], font=f_hdr)
        draw.text((DIV_X, HDR_TOP + round(6 * _SCALE)), "Dividend Amount", fill=COLORS["orange"], font=f_hdr)
        draw.text((YLD_X, HDR_TOP - round(2 * _SCALE)), "Yield", fill=COLORS["orange"], font=f_hdr)
        draw.text(
            (YLD_X, HDR_TOP + round(28 * _SCALE)),
            f"(close price as of {UpcomingDividendRenderer._fmt_date(close_date_str)})",
            fill=COL_LIGHT,
            font=f_hdr_sub,
        )
        draw.text((CUM_X, HDR_TOP + round(6 * _SCALE)), "Cum Date", fill=COLORS["orange"], font=f_hdr)

        SEP_Y = T_TOP + HEADER_BLOCK
        draw.line([(T_L + round(10 * _SCALE), SEP_Y), (T_R - round(10 * _SCALE), SEP_Y)], fill=SEP_COLOR, width=2)

        LOGO_R = round(26 * _SCALE)

        for i, (_, row) in enumerate(df_page.iterrows()):
            cy = int(SEP_Y + i * ROW_H + ROW_H / 2)
            sym = str(row["symbol"]).replace(".JK", "")

            self._logo(overlay, (T_L + IP, cy - LOGO_R), sym, size=LOGO_R * 2, accent=COLORS["orange"])
            draw.text((T_L + IP + LOGO_R * 2 + round(14 * _SCALE), cy - round(14 * _SCALE)), sym, fill=COLORS["white"], font=f_sym)
            draw.text((DIV_X, cy - round(14 * _SCALE)), self._fmt_dividend(row["dividend_amount"]), fill=COL_LIGHT, font=f_val)

            yld_text = f"{row['dividend_yield'] * 100:.2f}%"
            draw.text((YLD_X, cy - round(14 * _SCALE)), yld_text, fill=COLORS["white"], font=f_yld)
            draw.text((CUM_X, cy - round(14 * _SCALE)), self._fmt_date(row["cum_date"]), fill=COL_LIGHT, font=f_val)

            if i < n - 1:
                ly = int(SEP_Y + (i + 1) * ROW_H)
                draw.line([(T_L + round(10 * _SCALE), ly), (T_R - round(10 * _SCALE), ly)], fill=SEP_COLOR, width=1)

        result = Image.alpha_composite(bg, overlay)
        suffix = f"_p{page_num}" if total_pages > 1 else ""
        return self._save(result, f"upcoming_dividend{suffix}.png")

    def render(self, data, filename=None):
        df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
        df = df.sort_values("cum_date").reset_index(drop=True)

        close_date = (
            str(df["date"].dropna().iloc[0])
            if "date" in df.columns and not df["date"].dropna().empty
            else datetime.now().strftime("%Y-%m-%d")
        )

        pages = [df.iloc[i:i + MAX_ROWS_PER_PAGE] for i in range(0, len(df), MAX_ROWS_PER_PAGE)]
        total_pages = len(pages)

        paths = []
        for pn, df_page in enumerate(pages, 1):
            paths.append(self._render_page(df_page, pn, total_pages, close_date))

        return paths
