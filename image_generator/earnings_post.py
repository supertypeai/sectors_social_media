"""Earnings post: a company whose quarterly profit jumped (or collapsed) versus the same quarter a year ago.

    python -m image_generator.earnings_post --out output_feed/earnings [--limit 3] [--symbol PTBA] [--direction spike]

Slides, drawn by iso/hl/render.mjs in the Sectors Hairline style (4:5 feed):
  1. earn_cover     the hook: this quarter vs the same quarter last year as two iso columns, the multiple huge
  2. earn_quarters  the last six quarters of profit, so the jump is seen in its trend, not alone
  3. earn_split     revenue vs profit, year on year: did sales grow too, or only the margin?
  4. earn_close     three facts, valuation, the question

Selection is insider_patterns.select_earnings_spikes (60%–800% growth, a sane base, top-200 by market cap), so
the near-zero-base trap (profit Rp 1 B → Rp 50 B shown as +4,900%) never reaches a post.
"""
import argparse
import json
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from .data import fetch_company_report_earnings
from .insider_patterns import select_earnings_spikes
from .weekly_calendar import _logo

ROOT = Path(__file__).resolve().parent.parent
RENDER_JS = ROOT / "iso" / "hl" / "render.mjs"


def _rp(v):
    a, s = abs(float(v)), "−" if float(v) < 0 else ""
    for div, unit in ((1e12, " T"), (1e9, " B"), (1e6, " M")):
        if a >= div:
            x = a / div
            return f"{s}Rp {x:.1f}".rstrip("0").rstrip(".") + unit if x < 100 else f"{s}Rp {x:,.0f}{unit}"
    return f"{s}Rp {a:,.0f}"


def _q(label):
    """'Q2-2026' → 'Q2 2026'."""
    return label.replace("-", " ")


def _short_name(n):
    import re
    n = re.sub(r"\b(PT|Tbk\.?)\b", "", str(n or "")).strip(" .,")
    return re.sub(r"\s+", " ", n)


def build(e):
    qs = [{**q, "earnings": float(q["earnings"] or 0), "revenue": float(q["revenue"] or 0)} for q in e["quarters"]]
    now = qs[-1]
    prev = next((q for q in qs if q["label"].split("-")[0] == now["label"].split("-")[0] and int(q["label"][-4:]) == int(now["label"][-4:]) - 1), None)
    if not prev or prev["earnings"] <= 0:
        return None
    up = e["direction"] == "spike"
    sym, name = e["base_symbol"], _short_name(e["company_name"])
    g = now["earnings"] / prev["earnings"] - 1
    rg = (now["revenue"] / prev["revenue"] - 1) if prev["revenue"] else None
    mult = now["earnings"] / prev["earnings"]
    hero = f"{mult:.1f}×" if up and mult >= 2 else f"{g * 100:+.0f}%".replace("-", "−")
    base = {"direction": "buy" if up else "sell", "kicker": "Earnings", "company": f"{sym} · {_q(now['label'])}",
            "logo": None, "source": "Quarterly reports · Sectors"}
    logo = _logo(sym)
    q_now, q_prev = _q(now["label"]), _q(prev["label"])
    slides = [("earn_cover", {
        "sym": sym, "name": name, "logo": logo, "sector": e.get("sub_sector") or e.get("sector") or "",
        "hero": hero, "up": up, "growth": g,
        "line": (f"{name}'s profit in {q_now} vs a year earlier" if up else f"{name}'s profit in {q_now} vs a year earlier"),
        "prev": {"label": q_prev, "v": prev["earnings"], "s": _rp(prev["earnings"])},
        "now": {"label": q_now, "v": now["earnings"], "s": _rp(now["earnings"])},
    })]
    slides.append(("earn_quarters", {
        "title": "Profit, quarter by quarter", "sym": sym, "logo": logo,
        "bars": [{"label": q["label"].replace("-20", " '"), "v": q["earnings"], "s": _rp(q["earnings"]),
                  "hi": q is now, "pair": q is prev} for q in qs],
    }))
    if rg is not None:
        slides.append(("earn_split", {
            "title": "Sales vs profit, year on year", "sym": sym, "q_now": q_now, "q_prev": q_prev,
            "rows": [{"label": "Revenue", "prev": prev["revenue"], "now": now["revenue"], "ps": _rp(prev["revenue"]), "ns": _rp(now["revenue"]), "g": rg},
                     {"label": "Net profit", "prev": prev["earnings"], "now": now["earnings"], "ps": _rp(prev["earnings"]), "ns": _rp(now["earnings"]), "g": g}],
            "verdict": ("Profit grew much faster than sales: margins widened." if up and rg is not None and g > rg * 2
                        else "Sales and profit grew together." if up
                        else "Profit fell much harder than sales: margins were squeezed." if rg is not None and rg > g + 0.3
                        else "Sales and profit fell together."),
        }))
    pe = e.get("forward_pe")
    facts = [{"value": hero, "label": f"profit vs {q_prev}", "accent": True},
             {"value": _rp(now["earnings"]), "label": f"net profit, {q_now}"}]
    if pe and pe == pe and 0 < float(pe) < 200:
        facts.append({"value": f"{float(pe):.1f}×", "label": "forward P/E"})
    else:
        facts.append({"value": f"Rp {float(e['last_close_price']):,.0f}", "label": "last close"})
    slides.append(("earn_close", {
        "title": "The short version", "sym": sym, "logo": logo, "facts": facts,
        "question": f"Is {sym}'s jump a new level, or a one-off quarter?" if up else f"A bad quarter for {sym}, or the start of a slide?",
        "cta": f"Full financials on sectors.app/idx/{sym.lower()}",
    }))
    n = len(slides)
    return [(k, {**base, "slide": {**s, "page": i + 1, "pages": n}}) for i, (k, s) in enumerate(slides)]


def render(e, out_dir):
    frames = build(e)
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


def main():
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="output_feed/earnings")
    p.add_argument("--limit", type=int, default=3)
    p.add_argument("--symbol")
    p.add_argument("--direction", choices=["spike", "drop", "both"], default="both")
    a = p.parse_args()
    df = fetch_company_report_earnings(200)
    ev = []
    for d in (["spike", "drop"] if a.direction == "both" else [a.direction]):
        ev += select_earnings_spikes(df, direction=d)
    if a.symbol:
        ev = [e for e in ev if e["base_symbol"] == a.symbol.upper()]
    for e in ev[: a.limit]:
        print(e["base_symbol"], e["direction"], [Path(x).name for x in render(e, a.out)])


if __name__ == "__main__":
    main()
