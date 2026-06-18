import os
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.font_manager as fm
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch, BoxStyle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import requests
from PIL import Image

from image_generator.render import SocialImageRenderer, FONT_DIR


# ── palette ───────────────────────────────────────────────────────────────────
LIME      = '#A6D94E'
EMBER     = '#F46D43'
SPECTRAL  = '#3288BD'
AMBER     = '#FDAE61'
TAG_OG    = '#F29942'
WHITE     = '#FFFFFF'
BONE      = '#F0EBE0'
BONE_L    = '#e8e8f0'
COOL      = '#c0c0d0'
LILAC_S   = '#8888a0'
BORDER    = '#28282e'
BG        = '#07070e'
CARD_FILL = (20/255, 20/255, 24/255, 0.30)


# ── small helpers ─────────────────────────────────────────────────────────────
def _fmt_vol(v):
    if v >= 1e9: return f"{v/1e9:.1f}B"
    if v >= 1e6: return f"{v/1e6:.1f}M"
    if v >= 1e3: return f"{v/1e3:.1f}K"
    return str(int(v))


def _fmt_idr(v):
    s, av = ('+', abs(v)) if v >= 0 else ('-', abs(v))
    if av >= 1e12: return f"IDR {s}{av/1e12:.1f}T"
    if av >= 1e9:  return f"IDR {s}{av/1e9:.0f}B"
    return f"IDR {s}{av/1e6:.0f}M"


def _sparkline(pct, n=40, seed=0):
    rng  = np.random.RandomState(seed)
    walk = np.cumsum(rng.randn(n))
    if walk[-1] != 0:
        walk = walk / abs(walk[-1]) * abs(pct) * n * 0.1
    if (pct >= 0 and walk[-1] < 0) or (pct < 0 and walk[-1] > 0):
        walk = -walk
    walk -= walk[0]
    span  = walk.max() - walk.min()
    return np.linspace(0, 1, n), (walk - walk.min()) / (span if span else 1)


def _card(fig, pos, fc=CARD_FILL, ec=BORDER, lw=2.0):
    l, b, w, h = pos
    fig.add_artist(FancyBboxPatch(
        (l, b), w, h,
        boxstyle=BoxStyle('round', pad=0, rounding_size=0.022),
        facecolor=fc, edgecolor=ec, linewidth=lw,
        transform=fig.transFigure, zorder=1, clip_on=False,
    ))


def _overlay(fig, pos, zorder=3):
    ax = fig.add_axes(pos, zorder=zorder)
    ax.set_facecolor('none')
    ax.patch.set_visible(False)
    ax.axis('off')
    return ax


def _fetch_icon(url, size=64):
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert('RGBA')
        return np.array(img.resize((size, size), Image.LANCZOS))
    except Exception:
        return None


def _gradient_tint_icon(arr, rgb_start, rgb_end):
    out = arr.astype(float).copy()
    w = arr.shape[1]
    brightness = out[:, :, :3].max(axis=2)
    t = np.linspace(0, 1, w)[np.newaxis, :]
    for i, (s, e) in enumerate(zip(rgb_start, rgb_end)):
        out[:, :, i] = brightness * ((1 - t) * s + t * e)
    return np.clip(out, 0, 255).astype(np.uint8)


def _place_icon(ax, arr, xy, zoom=0.4, zorder=6):
    if arr is None:
        return
    ab = AnnotationBbox(OffsetImage(arr, zoom=zoom), xy,
                        frameon=False, zorder=zorder, xycoords=ax.transData)
    ax.add_artist(ab)


class VolumeSpikeRenderer(SocialImageRenderer):
    _fonts_registered = False

    def _register_fonts(self):
        if VolumeSpikeRenderer._fonts_registered:
            return
        for fp in FONT_DIR.iterdir():
            if fp.suffix.lower() in {'.ttf', '.otf'}:
                fm.fontManager.addfont(str(fp))
        plt.rcParams['font.family'] = 'Inter'
        plt.rcParams['font.weight'] = 'regular'
        VolumeSpikeRenderer._fonts_registered = True

    def _fetch_logo(self, sym):
        clean = sym.replace('.JK', '')
        logo_path = self.output_dir.parent / 'logos' / f'{clean}.webp'
        try:
            if logo_path.exists():
                img = Image.open(logo_path).convert('RGBA')
            else:
                url = f'https://storage.googleapis.com/sectorsapp/logo/{clean}.webp'
                resp = requests.get(url, timeout=5)
                resp.raise_for_status()
                img = Image.open(BytesIO(resp.content)).convert('RGBA')
                logo_path.parent.mkdir(parents=True, exist_ok=True)
                logo_path.write_bytes(resp.content)
            size = 80
            img = img.resize((size, size), Image.LANCZOS)
            from PIL import ImageDraw as _ID
            mask = Image.new('L', (size, size), 0)
            _ID.Draw(mask).ellipse((0, 0, size, size), fill=255)
            img.putalpha(mask)
            return np.array(img)
        except Exception:
            return None

    def _render_card(self, row, sym_v, df_history, compro_df):
        sym    = row['symbol']
        t_vol  = row['volume']
        m_vol  = row['avg_volume']
        v_rat  = row['volume_ratio']
        c1     = (row.get('close_change_1d') or 0) * 100
        c3     = (row.get('close_change_3d') or 0) * 100
        c7     = (row.get('close_change_7d') or 0) * 100
        fb     = row['foreign_buy_volume']
        fs     = row['foreign_sell_volume']
        f_net  = (fb - fs) * row['close']
        f_act  = row['foreign_activity']

        cn_arr = compro_df[compro_df['symbol'] == sym]['company_name'].values
        cname  = cn_arr[0] if len(cn_arr) else sym

        vols  = sym_v['volume'].values
        dates = pd.to_datetime(sym_v['date'].values)
        n     = len(vols)
        xlbls = [d.strftime('%d %b') for d in dates]

        buy_days = sell_days = net_30d_idr = 0
        if df_history is not None and len(df_history):
            h = df_history[df_history['symbol'] == sym].copy()
            if len(h):
                net_f      = h['foreign_buy_volume'] - h['foreign_sell_volume']
                buy_days   = int((net_f > 0).sum())
                sell_days  = int((net_f < 0).sum())
                net_30d_idr = (net_f * h['close']).sum()

        # ── layout ────────────────────────────────────────────────────────────
        L, W = 0.04, 0.92
        HDR = (L, 0.864, W, 0.126)
        STK = (L, 0.745, W, 0.110)
        CHT = (L, 0.385, W, 0.350)
        FRN = (L, 0.082, W, 0.158)
        _cg = 0.016
        _cw = (W - 2 * _cg) / 3
        PRC = [(L + i * (_cw + _cg), 0.250, _cw, 0.125) for i in range(3)]
        CHT_L, CHT_B, CHT_W, CHT_H = CHT
        CHT_AX = (CHT_L + 0.095, CHT_B + 0.048, CHT_W - 0.115, CHT_H - 0.088)

        # ── figure ────────────────────────────────────────────────────────────
        fig = plt.figure(figsize=(9, 13), facecolor=BG, dpi=150)

        bg_arr = np.array(Image.open(self.background_dir / 'volume_spike.png').convert('RGB'))
        ax_bg = fig.add_axes([0, 0, 1, 1], zorder=0)
        ax_bg.imshow(bg_arr, aspect='auto', origin='upper', interpolation='bilinear',
                     extent=[0, 1, 0, 1], transform=ax_bg.transAxes)
        ax_bg.axis('off')
        ax_bg.patch.set_visible(False)

        # ── header ────────────────────────────────────────────────────────────
        _card(fig, HDR, ec=TAG_OG, lw=2.0)
        a0 = _overlay(fig, HDR)
        a0.set_xlim(0, 10); a0.set_ylim(0, 3)
        a0.text(0.35, 1.95, 'VOLUME SPIKE', fontsize=40, fontweight='bold', color=WHITE, va='center')
        sym_clean = sym.replace('.JK', '')
        # 3-day trend EXCLUDING today (the spike day) vs the 30D median, so the bullet
        # answers "was volume already building up?" rather than restating today's spike.
        prior3 = vols[-4:-1]
        a0.text(0.35, 1.05,
                f"•  Today's transaction volume of {sym_clean} is {v_rat:.2f}x the 30D median",
                fontsize=12.5, color=COOL, va='center')
        if len(prior3) and m_vol:
            r3 = float(np.mean(prior3)) / m_vol
            a0.text(0.35, 0.50,
                    f"•  Over the past 3 days, {sym_clean}'s average volume was "
                    f"{r3:.1f}x its 30D median",
                    fontsize=12.5, color=COOL, va='center')

        # ── stock info ────────────────────────────────────────────────────────
        _card(fig, STK)
        a1 = _overlay(fig, STK)
        a1.set_xlim(0, 10); a1.set_ylim(0, 3)

        logo_arr = self._fetch_logo(sym)
        if logo_arr is not None:
            ab = AnnotationBbox(OffsetImage(logo_arr, zoom=0.55), (0.72, 1.50),
                                frameon=False, zorder=6, xycoords=a1.transData)
            a1.add_artist(ab)
        else:
            a1.add_patch(plt.Circle((0.72, 1.50), 0.62, color='#1a4e9e', zorder=5, clip_on=False))
            a1.text(0.72, 1.50, sym[:2], fontsize=11, fontweight='bold',
                    color=WHITE, ha='center', va='center', zorder=6)

        a1.text(1.35, 2.05, sym.replace('.JK', ''), fontsize=20, fontweight='bold', color=WHITE, va='center')
        _MAX_CN = 22
        if len(cname) > _MAX_CN:
            w = cname.rfind(' ', 0, _MAX_CN)
            w = w if w != -1 else _MAX_CN
            a1.text(1.35, 1.45, cname[:w].strip(), fontsize=10, color=COOL, va='center')
            a1.text(1.35, 0.95, cname[w:].strip(), fontsize=10, color=COOL, va='center')
        else:
            a1.text(1.35, 1.25, cname, fontsize=10, color=COOL, va='center')

        for xv in [6, 8]:
            a1.plot([xv, xv], [0.4, 2.5], color=BORDER, lw=1, alpha=0.9, zorder=2)

        def _stat(ax, x, label, value, vc):
            ax.text(x, 2.3, label, fontsize=13, color=WHITE, va='top', ha='center', fontweight='bold')
            ax.text(x, 1.1, value, fontsize=24, fontweight='bold', color=vc, ha='center', va='center')

        _stat(a1, 4.75, "TODAY'S VOLUME", _fmt_vol(t_vol), LIME)
        _stat(a1, 7.00, "30D MEDIAN",     _fmt_vol(m_vol), BONE)
        _stat(a1, 9.00, "VOLUME RATIO",   f"{v_rat:.2f}x", SPECTRAL)

        # ── bar chart ─────────────────────────────────────────────────────────
        _card(fig, CHT)
        fig.text(CHT_L + 0.025, CHT_B + CHT_H - 0.017,
                 'LAST 7 TRADING DAYS – TRANSACTION VOLUME',
                 color=WHITE, fontsize=9.5, fontweight='bold', va='top', zorder=5)

        a2 = fig.add_axes(CHT_AX, zorder=3)
        a2.set_facecolor('none'); a2.patch.set_visible(False)
        a2.spines['top'].set_visible(False); a2.spines['right'].set_visible(False)
        for sp in ['left', 'bottom']:
            a2.spines[sp].set_color('#555'); a2.spines[sp].set_alpha(0.8)
        a2.yaxis.grid(True, ls='--', color='#444', alpha=0.20, zorder=0)

        _vscale = 1e6 if max(vols) >= 1e6 else 1e3
        _vunit  = 'M' if _vscale == 1e6 else 'K'

        a2.bar(range(n - 1), vols[:-1] / _vscale, color='#4a4a5c', width=0.65, zorder=3, alpha=0.7)
        h_last = vols[-1] / _vscale
        cmap_b = LinearSegmentedColormap.from_list('', [AMBER, LIME])
        for j in range(60):
            y0 = j * h_last / 60
            a2.bar(n - 1, h_last / 60, bottom=y0, width=0.65, color=cmap_b(j / 60), zorder=3, edgecolor='none')

        max_v = max(vols) / _vscale
        for i, v in enumerate(vols):
            cl = BONE_L if i == n - 1 else COOL
            a2.text(i, v / _vscale + max_v * 0.02, _fmt_vol(v),
                    ha='center', va='bottom', color=cl, fontsize=7.5, fontweight='bold')

        med_v = m_vol / _vscale
        a2.axhline(med_v, color=SPECTRAL, ls='--', lw=1.6, zorder=5, alpha=0.85)
        a2.set_xticks(range(n))
        a2.set_xticklabels(xlbls, color=COOL, fontsize=7.5)
        a2.set_ylim(0, max_v * 1.38)
        _auto = [t for t in a2.get_yticks() if 0 <= t <= max_v * 1.38]
        a2.set_yticks(sorted(set(_auto + [med_v])))
        _tol = max(max_v * 1e-4, 1e-9)
        a2.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: '30D Median' if abs(x - med_v) < _tol else f'{x:.0f}{_vunit}'
        ))
        a2.tick_params(axis='y', colors=COOL, labelsize=7)
        a2.tick_params(axis='x', length=0)
        for tick, pos in zip(a2.yaxis.get_major_ticks(), a2.get_yticks()):
            if abs(pos - med_v) < _tol:
                tick.label1.set_color(COOL)
                tick.label1.set_fontsize(9)
                tick.label1.set_fontweight('bold')
                tick.label1.set_bbox(dict(facecolor='#000000', edgecolor=COOL,
                                          linewidth=0.8, pad=3, boxstyle='round,pad=0.3', alpha=1.0))
        a2.set_ylabel(f'Volume ({_vunit} shares)', color=COOL, fontsize=7)

        # ── price change cards ────────────────────────────────────────────────
        for (lx, py, pw, ph), (lbl, pct, seed) in zip(
            PRC, [('1D PRICE CHANGE', c1, 0), ('3D PRICE CHANGE', c3, 1), ('7D PRICE CHANGE', c7, 2)]
        ):
            _card(fig, (lx, py, pw, ph))
            ac = _overlay(fig, (lx, py, pw, ph))
            ac.set_xlim(0, 1); ac.set_ylim(0, 1)
            col  = LIME if pct >= 0 else EMBER
            sign = '+' if pct >= 0 else ''
            ac.text(0.07, 0.88, lbl, fontsize=10, color=WHITE, va='top')
            ac.text(0.07, 0.60, f'{sign}{pct:.2f}%', fontsize=18, fontweight='bold', color=col, va='center')
            ac.text(0.89, 0.60, '↗' if pct >= 0 else '↘', fontsize=16, color=col, va='center', ha='center',
                    bbox=dict(boxstyle='circle,pad=0.22',
                              fc='#1a2e0a' if pct >= 0 else '#2e1208', ec='none'))
            xs, ys = _sparkline(pct, seed=seed)
            asp = fig.add_axes([lx + pw * 0.03, py + ph * 0.03, pw * 0.94, ph * 0.28], zorder=3)
            asp.set_facecolor('none'); asp.patch.set_visible(False)
            asp.plot(xs, ys, color=col, lw=1.5)
            asp.fill_between(xs, ys, 0, alpha=0.18, color=col)
            asp.axis('off')

        # ── foreign flow ──────────────────────────────────────────────────────
        _card(fig, FRN)
        a3 = _overlay(fig, FRN)
        a3.set_xlim(0, 10); a3.set_ylim(0, 4)

        icon_globe = _fetch_icon('https://img.icons8.com/ios/96/globe.png')
        if icon_globe is not None:
            alpha = icon_globe[:, :, 3].copy()
            rgb   = 255 - icon_globe[:, :, :3]
            icon_globe = _gradient_tint_icon(np.dstack([rgb, alpha]), (1.00, 0.44, 0.26), (1.00, 0.33, 0.60))
        _place_icon(a3, icon_globe, (0.57, 2.75), zoom=0.75)

        net_col = LIME if f_net >= 0 else EMBER
        a3.text(1.15, 3.15, "FOREIGN NET BUY / SELL (TODAY)", fontsize=13, color=WHITE, va='center', fontweight='bold')
        a3.text(1.15, 2.35, _fmt_idr(f_net), fontsize=30, fontweight='bold', color=net_col, va='center')
        a3.text(1.15, 1.6, f_act, fontsize=15, color=net_col, fontweight='bold', va='center')
        a3.plot([5.25, 5.25], [0.5, 3.5], color=BORDER, lw=1, alpha=0.9, zorder=2)

        net30_col = LIME if net_30d_idr >= 0 else EMBER
        net30_act = "Net Buy" if net_30d_idr >= 0 else "Net Sell"
        a3.text(7.5, 3.15, "30D NET FOREIGN ACTIVITY", fontsize=13, color=WHITE, va='center', ha='center', fontweight='bold')
        a3.text(7.5, 2.55, f"{net30_act} - {_fmt_idr(net_30d_idr)}", fontsize=18, fontweight='bold', color=net30_col, va='center', ha='center')
        a3.text(6.5, 1.55, str(buy_days),  fontsize=18, fontweight='bold', color=LIME,  va='center', ha='center')
        a3.text(6.5, 1.0,  "Buy Days",     fontsize=10, color=LIME,  va='center', fontweight='bold', ha='center')
        a3.text(8.5, 1.55, str(sell_days), fontsize=18, fontweight='bold', color=EMBER, va='center', ha='center')
        a3.text(8.5, 1.0,  "Sell Days",    fontsize=10, color=EMBER, va='center', fontweight='bold', ha='center')
        a3.plot([7.5, 7.5], [0.5, 2.15], color=BORDER, lw=1, alpha=0.7, zorder=2)

        return fig

    def render_one(self, row: dict, df_latest_7: pd.DataFrame,
                   df_history: pd.DataFrame, compro_df: pd.DataFrame) -> Path:
        sym   = str(row['symbol']).replace('.JK', '')
        sym_v = df_latest_7[df_latest_7['symbol'] == row['symbol']].sort_values('date').reset_index(drop=True)
        fig   = self._render_card(row, sym_v, df_history, compro_df)
        path  = self.output_dir / f'volume_spike_{sym}.png'
        fig.savefig(str(path), dpi=150, pad_inches=0)
        plt.close(fig)
        print(f"Saved: {path}")
        return path

    def render(self, data: dict) -> list[Path]:
        self._register_fonts()
        df_spike   = data['df_spike']
        df_latest_7 = data['df_latest_7']
        df_history  = data['df_history']
        compro_df   = data['compro_df']

        paths = []
        for _, row in df_spike.iterrows():
            paths.append(self.render_one(row.to_dict(), df_latest_7, df_history, compro_df))
        return paths
