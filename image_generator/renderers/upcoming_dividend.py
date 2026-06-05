from PIL import Image, ImageDraw
from datetime import datetime
import pandas as pd

from image_generator.render import SocialImageRenderer, COLORS, font


MAX_ROWS_PER_PAGE = 7
ROW_H = 110
TABLE_BG = (30, 32, 38, 240)
SEP_COLOR = "#414146"
COL_LIGHT = "#bebebe"


class UpcomingDividendRenderer(SocialImageRenderer):

    def get_background(self):
        return self._open("upcoming_dividend.png")

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

        PAD = 60
        T_TOP = 375
        T_L = PAD
        T_R = W - PAD
        HEADER_BLOCK = 90
        BOTTOM_PAD = 20
        n = len(df_page)

        T_BOT = T_TOP + HEADER_BLOCK + int(ROW_H * n) + BOTTOM_PAD
        draw.rounded_rectangle([T_L, T_TOP, T_R, T_BOT], radius=22, fill=TABLE_BG)

        IP = 30
        SYM_X = T_L + IP
        DIV_X = T_L + 280
        YLD_X = T_L + 578
        CUM_X = T_L + 890

        f_hdr = font("Inter-Bold.ttf", 26)
        f_hdr_sub = font("Inter-Regular.ttf", 17)
        f_sym = font("Inter-Bold.ttf", 28)
        f_val = font("Inter-Regular.ttf", 26)
        f_yld = font("Inter-Bold.ttf", 26)

        HDR_TOP = T_TOP + 22
        draw.text((SYM_X + 32, HDR_TOP + 6), "Symbol", fill=COLORS["orange"], font=f_hdr)
        draw.text((DIV_X, HDR_TOP + 6), "Dividend Amount", fill=COLORS["orange"], font=f_hdr)
        draw.text((YLD_X, HDR_TOP - 2), "Yield", fill=COLORS["orange"], font=f_hdr)
        draw.text(
            (YLD_X, HDR_TOP + 28),
            f"(close price as of {UpcomingDividendRenderer._fmt_date(close_date_str)})",
            fill=COL_LIGHT,
            font=f_hdr_sub,
        )
        draw.text((CUM_X, HDR_TOP + 6), "Cum Date", fill=COLORS["orange"], font=f_hdr)

        SEP_Y = T_TOP + HEADER_BLOCK
        draw.line([(T_L + 10, SEP_Y), (T_R - 10, SEP_Y)], fill=SEP_COLOR, width=2)

        LOGO_R = 26

        for i, (_, row) in enumerate(df_page.iterrows()):
            cy = int(SEP_Y + i * ROW_H + ROW_H / 2)
            sym = str(row["symbol"]).replace(".JK", "")

            self._logo(overlay, (T_L + IP, cy - LOGO_R), sym, size=LOGO_R * 2, accent=COLORS["orange"])
            draw.text((T_L + IP + LOGO_R * 2 + 14, cy - 14), sym, fill=COLORS["white"], font=f_sym)
            draw.text((DIV_X, cy - 14), self._fmt_dividend(row["dividend_amount"]), fill=COL_LIGHT, font=f_val)

            yld_text = f"{row['dividend_yield'] * 100:.2f}%"
            draw.text((YLD_X, cy - 14), yld_text, fill=COLORS["white"], font=f_yld)
            draw.text((CUM_X, cy - 14), self._fmt_date(row["cum_date"]), fill=COL_LIGHT, font=f_val)

            if i < n - 1:
                ly = int(SEP_Y + (i + 1) * ROW_H)
                draw.line([(T_L + 10, ly), (T_R - 10, ly)], fill=SEP_COLOR, width=1)

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
