"""Earnings post, object direction: profit drawn as coins instead of columns.

    python -m image_generator.earnings_v_object --out output_feed/earnings_v_object [--symbol PTBA] [--limit 3]

Slides (iso/hl/slides/feed/earnings_v_object):
  1. eo_cover   the multiple huge; last year's coin pile vs this year's (1 coin = a fixed Rp amount)
  2. eo_ladder  "One-off?" six quarters, each profit set at a type size true to its value
  3. eo_slice   "Sales or margin?" of every Rp 100 of sales, the slice kept as profit, a year apart
  4. eo_gauge   "Whole sector, or just them?" a pressure gauge of YoY profit growth vs sub-sector peers
  5. eo_close   three facts and the question
"""
import argparse
import json
import math
import subprocess
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from .data import fetch_company_report_earnings
from .earnings_post import _q, _rp, _short_name
from .insider_patterns import select_earnings_spikes
from .weekly_calendar import _logo

ROOT = Path(__file__).resolve().parent.parent
RENDER_JS = ROOT / "iso" / "hl" / "render.mjs"


def _unit(vmax, most=30):
    """A round coin value so the bigger pile has at most `most` coins."""
    raw = vmax / most
    mag = 10 ** math.floor(math.log10(raw))
    return next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)


def _pct(x):
    return f"{x * 100:+.0f}%".replace("-", "−")


def build(e, peers_df):
    qs = [{**q, "earnings": float(q["earnings"] or 0), "revenue": float(q["revenue"] or 0)} for q in e["quarters"]]
    now = qs[-1]
    prev = next((q for q in qs if q["label"][:2] == now["label"][:2] and int(q["label"][-4:]) == int(now["label"][-4:]) - 1), None)
    if not prev or prev["earnings"] <= 0:
        return None
    up = e["direction"] == "spike"
    sym, name, logo = e["base_symbol"], _short_name(e["company_name"]), _logo(e["base_symbol"])
    g = now["earnings"] / prev["earnings"] - 1
    mult = now["earnings"] / prev["earnings"]
    hero = f"{mult:.1f}×" if up and mult >= 2 else _pct(g)
    q_now, q_prev = _q(now["label"]), _q(prev["label"])
    base = {"direction": "buy" if up else "sell", "kicker": "Earnings", "company": f"{sym} · {q_now}",
            "logo": None, "source": "Quarterly reports · Sectors"}
    slides = []

    # 1. cover: coin piles
    unit = _unit(max(now["earnings"], prev["earnings"]))
    slides.append(("eo_cover", {
        "sym": sym, "name": name, "logo": logo, "up": up, "hero": hero,
        "line": "more profit than a year ago" if up else "less profit than a year ago",
        "unit": _rp(unit),
        "prev": {"label": q_prev, "n": max(1, round(prev["earnings"] / unit)), "s": _rp(prev["earnings"])},
        "now": {"label": q_now, "n": max(1, round(now["earnings"] / unit)), "s": _rp(now["earnings"])},
    }))

    # 2. ladder: the numbers are the chart
    best = max(qs, key=lambda q: q["earnings"])
    worst = min(qs, key=lambda q: q["earnings"])
    n = len(qs)
    if up:
        verdict = (f"Best quarter of the last {n}." if best is now else
                   f"Strong, but {_q(best['label'])} was bigger.")
    else:
        verdict = (f"Weakest quarter of the last {n}." if worst is now else
                   f"Weak, but {_q(worst['label'])} was lower.")
    slides.append(("eo_ladder", {
        "title": "A one-off, or a trend?", "verdict": verdict,
        "rows": [{"label": _q(q["label"]), "v": q["earnings"], "s": _rp(q["earnings"]), "hi": q is now, "pair": q is prev} for q in qs],
    }))

    # 3. slice: of every Rp 100 of sales, how much is kept
    if prev["revenue"] > 0 and now["revenue"] > 0:
        mp, mn = prev["earnings"] / prev["revenue"], now["earnings"] / now["revenue"]
        rg = now["revenue"] / prev["revenue"] - 1
        if up:
            why = "Sales barely moved: the jump came from keeping more of each rupiah." if rg < g / 3 else "Sales grew and margins widened: both pushed profit up."
        else:
            why = "Sales held up: the drop came from keeping less of each rupiah." if rg > g / 3 else "Sales and margins fell together."
        slides.append(("eo_slice", {
            "title": "Of every Rp 100 of sales, kept as profit", "why": why,
            "sales": f"Sales {_pct(rg)}", "profit": f"Profit {hero}" if up and mult >= 2 else f"Profit {_pct(g)}",
            "prev": {"label": q_prev, "m": mp}, "now": {"label": q_now, "m": mn},
        }))

    # 4. gauge vs sub-sector peers (YoY quarterly profit growth)
    # widen the peer group until there are enough: sub-sector, then sector, then the whole top 200
    for col, sub in (("sub_sector", e.get("sub_sector")), ("sector", e.get("sector")), (None, "top-200")):
        pe = peers_df if col is None else peers_df[peers_df[col] == sub]
        others = [{"sym": r["symbol"].replace(".JK", ""), "g": float(r["yoy_quarter_earnings_growth"])}
                  for _, r in pe.iterrows()
                  if r.get("yoy_quarter_earnings_growth") == r.get("yoy_quarter_earnings_growth")
                  and r.get("yoy_quarter_earnings_growth") is not None and r["symbol"].replace(".JK", "") != sym]
        if len(others) >= 4:
            break
    if len(others) >= 3:
        beat = sum(1 for p in others if (p["g"] < g if up else p["g"] > g))
        med = sorted(p["g"] for p in others)[len(others) // 2]
        slides.append(("eo_gauge", {
            "title": "Just them, or the whole sector?", "sub": sub, "sym": sym, "logo": logo,
            "g": g, "gs": _pct(g), "med": med, "meds": _pct(med),
            "peers": [p["g"] for p in others],
            "line": (f"Grew faster than {beat} of {len(others)} {sub.lower()} peers." if up
                     else f"Fell harder than {beat} of {len(others)} {sub.lower()} peers."),
        }))

    # 5. close
    fpe = e.get("forward_pe")
    facts = [{"value": hero, "label": f"profit vs {q_prev}", "accent": True},
             {"value": _rp(now["earnings"]), "label": f"net profit, {q_now}"}]
    if fpe and fpe == fpe and 0 < float(fpe) < 200:
        facts.append({"value": f"{float(fpe):.1f}×", "label": "forward P/E"})
    else:
        facts.append({"value": f"Rp {float(e['last_close_price']):,.0f}", "label": "last close"})
    slides.append(("eo_close", {
        "sym": sym, "name": name, "logo": logo, "up": up, "facts": facts,
        "question": f"Is {sym}'s jump a new level, or a one-off quarter?" if up else f"A bad quarter for {sym}, or the start of a slide?",
        "cta": f"Full financials on sectors.app/idx/{sym.lower()}",
    }))
    k = len(slides)
    return [(kind, {**base, "slide": {**s, "page": i + 1, "pages": k}}) for i, (kind, s) in enumerate(slides)]


def render(e, peers_df, out_dir):
    frames = build(e, peers_df)
    if not frames:
        return []
    out = Path(out_dir) / e["base_symbol"]
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (kind, data) in enumerate(frames, 1):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
        p = out / f"{i}.png"
        r = subprocess.run(["node", str(RENDER_JS), kind, f.name, "--out", str(p)], capture_output=True, text=True, encoding="utf-8")
        Path(f.name).unlink(missing_ok=True)
        if r.returncode != 0:
            raise RuntimeError(f"render failed for {kind}:\n{r.stderr.strip()}")
        paths.append(str(p))
    return paths


def sheet(out_dir, syms):
    from PIL import Image
    rows = [sorted((Path(out_dir) / s).glob("*.png"), key=lambda p: int(p.stem)) for s in syms]
    rows = [r for r in rows if r]
    if not rows:
        return
    tw, th = 360, 450
    cols = max(len(r) for r in rows)
    img = Image.new("RGB", (cols * (tw + 12) + 12, len(rows) * (th + 12) + 12), (10, 9, 8))
    for y, r in enumerate(rows):
        for x, p in enumerate(r):
            img.paste(Image.open(p).convert("RGB").resize((tw, th), Image.LANCZOS), (12 + x * (tw + 12), 12 + y * (th + 12)))
    img.save(Path(out_dir) / "_sheet.png")


def main():
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="output_feed/earnings_v_object")
    p.add_argument("--limit", type=int, default=3)
    p.add_argument("--symbol", nargs="*")
    a = p.parse_args()
    df = fetch_company_report_earnings(200)
    ev = select_earnings_spikes(df, direction="spike") + select_earnings_spikes(df, direction="drop")
    if a.symbol:
        want = [s.upper() for s in a.symbol]
        ev = [e for e in ev if e["base_symbol"] in want]
    else:
        ev = ev[: a.limit]
    done = []
    for e in ev:
        print(e["base_symbol"], e["direction"], [Path(x).name for x in render(e, df, a.out)])
        done.append(e["base_symbol"])
    sheet(a.out, done)


if __name__ == "__main__":
    main()
