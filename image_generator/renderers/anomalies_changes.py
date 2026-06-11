from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

from image_generator.render import SocialImageRenderer, COLORS, font


# ── Palette ───────────────────────────────────────────────────────────────────
_GOLD       = '#9E4800'
_DARK       = '#1C1206'
_MUTED      = '#888888'
_DIVIDER    = '#D8D8D8'
_WHITE      = '#FFFFFF'
_GREEN_DARK = '#3A7A27'
_GREEN_LINE = '#4CAF50'
_RED_DARK   = '#B22222'
_RED_LINE   = '#E53935'


# ── Module-level helpers ──────────────────────────────────────────────────────
def _hex_rgb(h: str) -> tuple:
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _cx(draw, text, fnt, col_x, col_w) -> int:
    return col_x + (col_w - draw.textbbox((0, 0), text, font=fnt)[2]) // 2


def _cy(draw, text, fnt, row_y, row_h) -> int:
    bb = draw.textbbox((0, 0), text, font=fnt)
    return row_y + (row_h - (bb[3] - bb[1])) // 2 - bb[1]


def _wrap_text(draw, text: str, fnt, max_w: int) -> list[str]:
    if not text:
        return []
    if draw.textbbox((0, 0), text, font=fnt)[2] <= max_w:
        return [text]
    words, lines, current = text.split(), [], ''
    for word in words:
        candidate = (current + ' ' + word).strip()
        if draw.textbbox((0, 0), candidate, font=fnt)[2] <= max_w:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fmt_mcap(v: float) -> str:
    av = abs(v)
    if av >= 1e12: return f"{av/1e12:.0f}T"
    if av >= 1e9:  return f"{av/1e9:.0f}B"
    if av >= 1e6:  return f"{av/1e6:.0f}M"
    return f"{av:.0f}"


def _fmt_idr(v: float) -> str:
    av   = abs(v)
    sign = '+' if v >= 0 else '-'
    if av >= 1e12: return f"{sign}IDR {av/1e12:.0f}T"
    if av >= 1e9:  return f"{sign}IDR {av/1e9:.0f}B"
    if av >= 1e6:  return f"{sign}IDR {av/1e6:.0f}M"
    return f"{sign}IDR {av:.0f}"


def _rounded_card(canvas: Image.Image, xy: tuple, radius: int,
                  fill: tuple, outline: tuple, width: int = 2) -> None:
    x1, y1, x2, y2 = xy
    layer = Image.new('RGBA', (x2 - x1, y2 - y1), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(
        (0, 0, x2 - x1, y2 - y1),
        radius=radius, fill=fill, outline=outline, width=width,
    )
    canvas.paste(layer, (x1, y1), layer)


def _sparkline(draw: ImageDraw.ImageDraw, xy: tuple, w: int, h: int,
               prices, color: str, lw: int = 3) -> None:
    prices = np.array(prices, dtype=float)
    if len(prices) < 2:
        return
    mn, mx = prices.min(), prices.max()
    rng    = mx - mn if mx != mn else 1.0
    x0, y0 = xy
    pts = [
        (x0 + int(i / (len(prices) - 1) * w), y0 + h - int((p - mn) / rng * h))
        for i, p in enumerate(prices)
    ]
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=color, width=lw)


class AnomalyChangesRenderer(SocialImageRenderer):
    ROWS_PER_PAGE = 5

    def get_background(self):
        return self._open("anomalies_changes.png")

    def _render_card(self, df_filtered: pd.DataFrame, df_daily: pd.DataFrame,
                     is_increase: bool, page: int, total_pages: int) -> Path:
        if is_increase:
            df_show   = df_filtered[df_filtered['daily_close_change_delta'] > 0].sort_values(
                'daily_close_change_delta', ascending=False)
            accent    = _GREEN_DARK
            title_dir = "GAINERS"
            direction = 'OUTPERFORMING'
        else:
            df_show   = df_filtered[df_filtered['daily_close_change_delta'] < 0].sort_values(
                'daily_close_change_delta', ascending=True)
            accent    = _RED_DARK
            title_dir = "LOSERS"
            direction = 'UNDERPERFORMING'

        start   = (page - 1) * self.ROWS_PER_PAGE
        df_show = df_show.iloc[start:start + self.ROWS_PER_PAGE]

        if df_show.empty:
            return None

        df_close = (df_daily.sort_values('date')
                    .groupby('symbol').last().reset_index()[['symbol', 'close']])
        df_show  = df_show.merge(df_close, on='symbol', how='left')
        df_show['foreign_net_idr'] = df_show['foreign_net_volume'] * df_show['close']

        canvas  = self.get_background()
        W, _    = canvas.size
        MARGIN  = 60
        CONT_W  = W - 2 * MARGIN
        acc_rgb = _hex_rgb(accent)

        fnt_title    = font('Inter-Bold.ttf',     96)
        fnt_subtitle = font('Inter-Bold.ttf',     32)
        fnt_meta     = font('Inter-Regular.ttf',  20)
        fnt_hdr      = font('Inter-SemiBold.ttf', 22)
        fnt_sym      = font('Inter-Bold.ttf',     28)
        fnt_sector   = font('Inter-Regular.ttf',  16)
        fnt_lg       = font('Inter-Bold.ttf',     42)
        fnt_md       = font('Inter-Bold.ttf',     22)
        fnt_sm       = font('Inter-Regular.ttf',  19)
        fnt_mcap     = font('Inter-Bold.ttf',     34)
        fnt_badge    = font('Inter-SemiBold.ttf', 20)
        fnt_idr      = font('Inter-Bold.ttf',     24)

        # ── Title card ────────────────────────────────────────────────────────
        TITLE_BOX_X, TITLE_BOX_Y = MARGIN, 48
        TITLE_BOX_W, TITLE_BOX_H = CONT_W, 240

        _rounded_card(canvas,
                      (TITLE_BOX_X, TITLE_BOX_Y,
                       TITLE_BOX_X + TITLE_BOX_W, TITLE_BOX_Y + TITLE_BOX_H),
                      radius=24, fill=(255, 255, 255, 200),
                      outline=(*acc_rgb, 180), width=2)

        draw = ImageDraw.Draw(canvas)
        TY, TPX = TITLE_BOX_Y + 28, TITLE_BOX_X + 28
        draw.text((TPX, TY), 'ANOMALY', font=fnt_title, fill=_DARK)
        aw = draw.textbbox((0, 0), 'ANOMALY ', font=fnt_title)[2]
        draw.text((TPX + aw, TY), title_dir, font=fnt_title, fill=accent)
        draw.text((TPX, TY + 108), f'STOCKS {direction} PEERS BY 15%',
                  font=fnt_subtitle, fill=accent)
        draw.text((TPX, TY + 160),
                  'Top 300 IDX Companies by Market Cap  •  Relative Performance vs Industry Peers',
                  font=fnt_meta, fill=_MUTED)

        # ── Table card ────────────────────────────────────────────────────────
        n_rows = len(df_show)
        HDR_H, ROW_H = 72, 195
        CARD_X = MARGIN
        CARD_Y = TITLE_BOX_Y + TITLE_BOX_H + 24
        CARD_W = CONT_W
        CARD_H = HDR_H + n_rows * ROW_H

        _rounded_card(canvas,
                      (CARD_X, CARD_Y, CARD_X + CARD_W, CARD_Y + CARD_H),
                      radius=24, fill=(252, 249, 244, 240),
                      outline=(*acc_rgb, 120), width=2)

        draw = ImageDraw.Draw(canvas)

        # ── Column layout ─────────────────────────────────────────────────────
        IL = CARD_X + 24
        C_SYM_X, C_SYM_W = IL,        235
        C_PRC_X, C_PRC_W = IL + 235,  270
        C_CAP_X, C_CAP_W = IL + 505,  158
        C_FOR_X, C_FOR_W = IL + 663,  220
        C_TRD_X           = IL + 883
        C_TRD_W           = CARD_X + CARD_W - 24 - C_TRD_X

        # ── Header row ────────────────────────────────────────────────────────
        for text, cx, cw in [
            ('Symbol',                  C_SYM_X, C_SYM_W),
            ('Price Change\nvs Peers',  C_PRC_X, C_PRC_W),
            ('Market Cap\n(IDR)',        C_CAP_X, C_CAP_W),
            ('Net Foreign\nBuy / Sell', C_FOR_X, C_FOR_W),
            ('30D Trend',               C_TRD_X, C_TRD_W),
        ]:
            lines = text.split('\n')
            lh    = draw.textbbox((0, 0), lines[0], font=fnt_hdr)[3] + 4
            total_h = lh * len(lines)
            ly    = CARD_Y + (HDR_H - total_h) // 2
            for line in lines:
                tw = draw.textbbox((0, 0), line, font=fnt_hdr)[2]
                draw.text((cx + (cw - tw) // 2, ly), line, font=fnt_hdr, fill=_GOLD)
                ly += lh

        draw.line([(CARD_X + 12, CARD_Y + HDR_H),
                   (CARD_X + CARD_W - 12, CARD_Y + HDR_H)], fill=_DIVIDER, width=1)
        for vx in [C_PRC_X, C_CAP_X, C_FOR_X, C_TRD_X]:
            draw.line([(vx, CARD_Y + 16), (vx, CARD_Y + CARD_H - 16)], fill=_DIVIDER, width=1)

        # ── Data rows ─────────────────────────────────────────────────────────
        for idx, (_, row) in enumerate(df_show.iterrows()):
            RY  = CARD_Y + HDR_H + idx * ROW_H
            RCY = RY + ROW_H // 2

            sym      = str(row['symbol']).replace('.JK', '')
            change   = float(row.get('daily_close_change',       0) or 0) * 100
            peer_avg = float(row.get('sub_sector_avg_change',    0) or 0) * 100
            delta    = float(row.get('daily_close_change_delta', 0) or 0) * 100
            mcap     = float(row.get('market_cap', 0)               or 0)
            f_act    = str(row.get('foreign_activity', 'Neutral')   or 'Neutral')
            f_idr    = float(row.get('foreign_net_idr', 0)          or 0)

            row_col   = _GREEN_DARK if delta  >= 0 else _RED_DARK
            badge_col = _GREEN_DARK if 'Buy' in f_act else _RED_DARK
            idr_col   = _GREEN_DARK if f_idr  >= 0 else _RED_DARK

            # — Logo —
            LOGO_SZ = 70
            self._logo(canvas, (C_SYM_X + 4, RCY - LOGO_SZ // 2), sym,
                       size=LOGO_SZ, accent=COLORS['orange'])
            draw = ImageDraw.Draw(canvas)

            # — Symbol + sub-sector —
            sx        = C_SYM_X + 4 + LOGO_SZ + 10
            sub_raw   = str(row.get('sub_sector', '') or '')
            sub_lines = _wrap_text(draw, sub_raw, fnt_sector, C_SYM_W - (LOGO_SZ + 18))
            line_h    = draw.textbbox((0, 0), 'Ag', font=fnt_sector)[3] + 3
            sym_h     = draw.textbbox((0, 0), sym, font=fnt_sym)[3]
            sec_h     = line_h * len(sub_lines) if sub_lines else 0
            blk_h     = sym_h + (5 + sec_h if sub_lines else 0)
            sym_y     = RCY - blk_h // 2
            draw.text((sx, sym_y), sym, font=fnt_sym, fill=_DARK)
            for i, ln in enumerate(sub_lines):
                draw.text((sx, sym_y + sym_h + 5 + i * line_h), ln, font=fnt_sector, fill=_MUTED)

            # — Price change column —
            s1 = f"{'+' if change  >= 0 else ''}{change:.1f}%"
            s2 = f"Peer Avg {'+' if peer_avg >= 0 else ''}{peer_avg:.1f}%"
            s3 = f"{'▲' if delta >= 0 else '▼'} {'+' if delta >= 0 else ''}{delta:.1f}%"
            h1 = draw.textbbox((0, 0), s1, font=fnt_lg)[3]
            h2 = draw.textbbox((0, 0), s2, font=fnt_sm)[3]
            h3 = draw.textbbox((0, 0), s3, font=fnt_md)[3]
            py = RCY - (h1 + 8 + h2 + 8 + h3) // 2
            for text, fnt_f, color in [(s1, fnt_lg, row_col), (s2, fnt_sm, _MUTED), (s3, fnt_md, row_col)]:
                tw = draw.textbbox((0, 0), text, font=fnt_f)[2]
                draw.text((C_PRC_X + (C_PRC_W - tw) // 2, py), text, font=fnt_f, fill=color)
                py += draw.textbbox((0, 0), text, font=fnt_f)[3] + 8

            # — Market cap —
            mc = _fmt_mcap(mcap)
            draw.text((_cx(draw, mc, fnt_mcap, C_CAP_X, C_CAP_W),
                       _cy(draw, mc, fnt_mcap, RY, ROW_H)),
                      mc, font=fnt_mcap, fill=_DARK)

            # — Net foreign pill + IDR —
            CR      = 11
            i_tw    = draw.textbbox((0, 0), f_act, font=fnt_badge)[2]
            i_th    = draw.textbbox((0, 0), f_act, font=fnt_badge)[3]
            idr_str = _fmt_idr(f_idr)
            id_tw   = draw.textbbox((0, 0), idr_str, font=fnt_idr)[2]
            id_th   = draw.textbbox((0, 0), idr_str, font=fnt_idr)[3]

            pill_pad_x  = 12
            pill_pad_y  = 8
            inner_w     = CR * 2 + 8 + i_tw
            pill_w      = inner_w + pill_pad_x * 2
            pill_h      = max(i_th + pill_pad_y * 2, CR * 2 + pill_pad_y * 2)
            badge_blk_h = pill_h + 10 + id_th
            pill_x      = C_FOR_X + (C_FOR_W - pill_w) // 2
            pill_y      = RCY - badge_blk_h // 2

            badge_rgb  = _hex_rgb(badge_col)
            pill_layer = Image.new('RGBA', (CARD_W, pill_h + 4), (0, 0, 0, 0))
            ImageDraw.Draw(pill_layer).rounded_rectangle(
                (0, 0, pill_w, pill_h), radius=pill_h // 2,
                fill=(*badge_rgb, 28), outline=(*badge_rgb, 160), width=1,
            )
            canvas.paste(pill_layer, (pill_x, pill_y), pill_layer)
            draw = ImageDraw.Draw(canvas)

            cx_  = pill_x + pill_pad_x + CR
            ccy_ = pill_y + pill_h // 2
            draw.ellipse((cx_ - CR, ccy_ - CR, cx_ + CR, ccy_ + CR), fill=badge_col)
            draw.line([(cx_ - CR + 4, ccy_), (cx_ + CR - 4, ccy_)], fill=_WHITE, width=3)
            draw.text((pill_x + pill_pad_x + CR * 2 + 8, pill_y + (pill_h - i_th) // 2),
                      f_act, font=fnt_badge, fill=badge_col)
            draw.text((C_FOR_X + (C_FOR_W - id_tw) // 2, pill_y + pill_h + 10),
                      idr_str, font=fnt_idr, fill=idr_col)

            # — 30D sparkline —
            sym_data = df_daily[df_daily['symbol'] == row['symbol']].sort_values('date')
            if len(sym_data) >= 2:
                prices = sym_data['close'].values.astype(float)
                sp_col = _GREEN_LINE if prices[-1] >= prices[0] else _RED_LINE
                _sparkline(draw, (C_TRD_X + 6, RCY - 45), C_TRD_W - 12, 90, prices, sp_col, lw=3)

            if idx < n_rows - 1:
                draw.line([(CARD_X + 12, RY + ROW_H),
                           (CARD_X + CARD_W - 12, RY + ROW_H)], fill=_DIVIDER, width=1)

        # ── Footnote ─────────────────────────────────────────────────────────
        latest_date = pd.to_datetime(df_show['latest_date']).max()
        draw.text((CARD_X + 860, CARD_Y + CARD_H + 6),
                  f"Data as of {latest_date.strftime('%d %B %Y')}",
                  font=font('Inter-Regular.ttf', 18), fill=_DARK)

        prefix = 'up' if is_increase else 'down'
        suffix = f'_p{page}' if total_pages > 1 else ''
        return self._save(canvas, f'anomaly_movers_{prefix}{suffix}.png')

    def render(self, data: dict) -> list[Path]:
        filtered_df = data['filtered_df']
        df_daily    = data['df_daily']
        paths       = []

        for is_inc, col_filter in [(True, filtered_df['daily_close_change_delta'] > 0),
                                   (False, filtered_df['daily_close_change_delta'] < 0)]:
            sub = filtered_df[col_filter]
            if sub.empty:
                continue
            total_pages = max(1, (len(sub) + self.ROWS_PER_PAGE - 1) // self.ROWS_PER_PAGE)
            for p in range(1, total_pages + 1):
                path = self._render_card(filtered_df, df_daily, is_inc, p, total_pages)
                if path:
                    paths.append(path)

        return paths
