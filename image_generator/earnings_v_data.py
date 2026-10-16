"""Earnings carousel, data-led / editorial-chart direction (no isometric solids).

    python -m image_generator.earnings_v_data --out output_feed/earnings_v_data --symbol PTBA,DSSA,UNTR

One idea per slide, drawn by iso/hl/render.mjs (slides in iso/hl/slides/feed/earnings_v_data):
  1. evd_cover   the stretched timeline: six years of quarterly profit, this quarter lit, a ruler back to the
                 last time profit was this high (or low). Hook = "best quarter since Q4 2022" + the multiple.
  2. evd_bridge  where the change came from: a profit bridge (waterfall) from the year-ago quarter to this one,
                 sales, costs, overheads, one-offs, tax, minorities.
  3. evd_margin  is it sustainable? net margin over six years, its normal band, today's dot.
  4. evd_peers   vs the sub-sector: this quarter's YoY profit change, ranked.
  5. evd_value   what it does to the price tag: trailing P/E before vs after this quarter at today's price,
                 placed on a ruler of peers' P/Es.

Selection is the same as earnings_post (insider_patterns.select_earnings_spikes). Uses the full
historical_financials_quarterly block (cost_of_revenue, operating_expense, non_operating_income_or_loss, tax,
earnings_before_tax) and market_cap, which earnings_post leaves unused.
"""
import argparse
import json
import statistics
import subprocess
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from .data import fetch_company_report_earnings
from .earnings_post import RENDER_JS, _q, _rp, _short_name
from .insider_patterns import select_earnings_spikes
from .weekly_calendar import _logo


def _key(label):
    try:
        q, y = str(label).split("-")
        return (int(y), int(q.lstrip("Qq")))
    except (ValueError, AttributeError):
        return (0, 0)


def _f(v):
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def _hfq(row):
    h = row.get("historical_financials_quarterly")
    if isinstance(h, str):
        try:
            h = json.loads(h)
        except ValueError:
            return []
    if not isinstance(h, dict):
        return []
    return [{"label": k, **(h[k] or {})} for k in sorted(h, key=_key)]


def _yago(qs, label):
    q, y = label.split("-")
    return next((x for x in qs if x["label"] == f"{q}-{int(y) - 1}"), None)


def _ttm(qs, i):
    """Sum of earnings over the four quarters ending at index i (None when any is missing)."""
    if i < 3:
        return None
    vals = [_f(qs[j].get("earnings")) for j in range(i - 3, i + 1)]
    return sum(vals) if all(v is not None for v in vals) else None


def _pct(g):
    return f"{g * 100:+,.0f}%".replace("-", "−")


def _short_q(label):
    return label.replace("-20", " '")


def _peer_rows(df, e):
    """Every company in the same sub-sector with the same latest quarter: YoY profit change and trailing P/E."""
    out = []
    for row in df.to_dict("records"):
        if row.get("sub_sector") != e.get("sub_sector"):
            continue
        qs = _hfq(row)
        if not qs or qs[-1]["label"] != e["latest_quarter"]:
            continue
        now, prev = _f(qs[-1].get("earnings")), _f((_yago(qs, qs[-1]["label"]) or {}).get("earnings"))
        sym = str(row["symbol"]).split(".")[0]
        g = (now / prev - 1) if now is not None and prev and prev > 0 else None
        ttm, mc = _ttm(qs, len(qs) - 1), _f(row.get("market_cap"))
        pe = mc / ttm if mc and ttm and ttm > 0 else None
        out.append({"sym": sym, "g": g, "pe": pe, "mc": mc})
    return out


def build(e, df):
    row = next(r for r in df.to_dict("records") if str(r["symbol"]).split(".")[0] == e["base_symbol"])
    qs = [q for q in _hfq(row) if _f(q.get("earnings")) is not None]
    now = qs[-1]
    prev = _yago(qs, now["label"])
    if not prev or (_f(prev["earnings"]) or 0) <= 0:
        return None
    up = e["direction"] == "spike"
    sym, name = e["base_symbol"], _short_name(e["company_name"])
    logo = _logo(sym)
    en, ep = _f(now["earnings"]), _f(prev["earnings"])
    g, mult = en / ep - 1, en / ep
    hero = f"{mult:.1f}×" if up and mult >= 2 else _pct(g)
    q_now, q_prev = _q(now["label"]), _q(prev["label"])
    base = {"direction": "buy" if up else "sell", "kicker": "Earnings", "company": f"{sym} · {q_now}",
            "logo": None, "source": "Quarterly reports · Sectors"}
    slides = []

    # 1. cover: the stretched timeline + the ruler back to the last comparable quarter
    since = None
    for q in reversed(qs[:-1]):
        v = _f(q["earnings"])
        if (up and v >= en) or (not up and v <= en):
            since = q["label"]
            break
    first_year = qs[0]["label"][-4:]
    if since:
        head = (f"Best quarter since {_q(since)}" if up else f"Weakest quarter since {_q(since)}")
    else:
        yrs = int(now["label"][-4:]) - int(first_year)
        head = (f"Best quarter in {yrs}+ years" if up else f"Weakest quarter in {yrs}+ years")
    slides.append(("evd_cover", {
        "sym": sym, "name": name, "logo": logo, "hero": hero, "up": up, "head": head,
        "sub": f"Net profit {_rp(en)} in {q_now}, vs {_rp(ep)} a year earlier",
        "series": [{"label": q["label"], "v": _f(q["earnings"])} for q in qs],
        "since": since, "prev": prev["label"],
        "now_s": _rp(en),
    }))

    # 2. the bridge: year-ago profit → this quarter's, line by line
    need = ("revenue", "cost_of_revenue", "operating_expense", "tax")
    if all(_f(now.get(k)) is not None and _f(prev.get(k)) is not None for k in need):
        d = {k: _f(now[k]) - _f(prev[k]) for k in need}
        nonop = (_f(now.get("non_operating_income_or_loss")) or 0) - (_f(prev.get("non_operating_income_or_loss")) or 0)
        steps = [("Sales", d["revenue"]), ("Cost of sales", -d["cost_of_revenue"]),
                 ("Operating costs", -d["operating_expense"]), ("One-offs & interest", nonop),
                 ("Tax", -d["tax"])]
        other = (en - ep) - sum(v for _, v in steps)
        steps.append(("Minorities & other", other))
        big = max(abs(v) for _, v in steps)
        # name the line that moved profit most in the direction of the story
        driver = max(steps, key=lambda s: s[1] if up else -s[1])
        slides.append(("evd_bridge", {
            "title": "Where the profit came from" if up else "Where the profit went",
            "sub": f"Net profit, {q_prev} → {q_now}",
            "start": {"label": q_prev, "v": ep, "s": _rp(ep)}, "end": {"label": q_now, "v": en, "s": _rp(en)},
            "steps": [{"label": l, "v": v, "s": ("+" if v >= 0 else "") + _rp(v)} for l, v in steps if abs(v) >= big * 0.02],
            "driver": driver[0],
            "note": (f"Most of the gain came from {driver[0].lower()}: +{_rp(driver[1])}." if up
                     else f"The biggest hit came from {driver[0].lower()}: −{_rp(-driver[1])}."),
        }))

    # 3. margin: is the new level normal for this company?
    ms = []
    for q in qs:
        r, v = _f(q.get("revenue")), _f(q.get("earnings"))
        if r and r > 0 and v is not None:
            ms.append({"label": q["label"], "m": v / r})
    if len(ms) >= 8 and ms[-1]["label"] == now["label"]:
        vals = sorted(x["m"] for x in ms[:-1])
        lo, hi = vals[len(vals) // 4], vals[(3 * len(vals)) // 4]
        med, cur = statistics.median(vals), ms[-1]["m"]
        where = "above its usual range" if cur > hi else "below its usual range" if cur < lo else "inside its usual range"
        slides.append(("evd_margin", {
            "title": "Is this margin normal?",
            "sub": "Net margin: profit kept from every Rp 100 of sales",
            "series": ms, "lo": lo, "hi": hi, "med": med, "cur": cur,
            "verdict": f"{q_now}: Rp {cur * 100:.0f} kept per Rp 100, {where} (Rp {lo * 100:.0f}–{hi * 100:.0f} since {ms[0]['label'][-4:]}).",
        }))

    # 4 + 5. peers
    peers = _peer_rows(df, e)
    pg = sorted([p for p in peers if p["g"] is not None], key=lambda p: -p["g"])
    if len(pg) >= 4:
        idx = next(i for i, p in enumerate(pg) if p["sym"] == sym)
        keep = pg[:7] if idx < 7 else pg[:6] + [pg[idx]]
        slides.append(("evd_peers", {
            "title": f"vs {e.get('sub_sector') or 'sector'} peers",
            "sub": f"Net profit change, {q_now} vs a year earlier",
            "rows": [{"sym": p["sym"], "logo": _logo(p["sym"]), "g": p["g"], "s": _pct(p["g"]), "hi": p["sym"] == sym,
                      "rank": pg.index(p) + 1} for p in keep],
            "n": len(pg), "rank": idx + 1, "sector": e.get("sector") or row.get("sector"),
        }))
    mc = _f(e.get("market_cap")) or _f(row.get("market_cap"))
    t_now, t_before = _ttm(qs, len(qs) - 1), _ttm(qs, len(qs) - 2)
    if mc and t_now and t_now > 0 and t_before and t_before > 0:
        pe_now, pe_before = mc / t_now, mc / t_before
        ruler = sorted([{"sym": p["sym"], "pe": p["pe"]} for p in peers if p["pe"] and 0 < p["pe"] < 60 and p["sym"] != sym], key=lambda p: p["pe"])
        if len(ruler) < 4:  # too few peers for a fair ruler
            ruler = []
        cheaper = sum(1 for p in ruler if p["pe"] > pe_now)
        slides.append(("evd_value", {
            "title": "Is the stock cheaper now?",
            "sub": f"P/E on the last four quarters' profit, at today's price ({_rp(mc)} market cap)",
            "before": pe_before, "now": pe_now, "q_before": _q(qs[-2]["label"]), "q_now": q_now,
            "peers": ruler, "sym": sym, "logo": logo,
            "line": (f"Cheaper than {cheaper} of {len(ruler)} {e.get('sub_sector')} peers" if ruler else ""),
            "cta": f"Full financials on sectors.app/idx/{sym.lower()}",
        }))
    n = len(slides)
    return [(k, {**base, "slide": {**s, "page": i + 1, "pages": n}}) for i, (k, s) in enumerate(slides)]


def render(e, df, out_dir):
    frames = build(e, df)
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
    p.add_argument("--out", default="output_feed/earnings_v_data")
    p.add_argument("--limit", type=int, default=3)
    p.add_argument("--symbol", help="comma-separated")
    p.add_argument("--pickle", help="cached fetch_company_report_earnings frame (dev)")
    a = p.parse_args()
    import pandas as pd
    df = pd.read_pickle(a.pickle) if a.pickle else fetch_company_report_earnings(200)
    ev = select_earnings_spikes(df, direction="spike") + select_earnings_spikes(df, direction="drop")
    if a.symbol:
        want = [s.strip().upper() for s in a.symbol.split(",")]
        ev = sorted([e for e in ev if e["base_symbol"] in want], key=lambda e: want.index(e["base_symbol"]))
    else:
        ev = ev[: a.limit]
    for e in ev:
        print(e["base_symbol"], e["direction"], [Path(x).name for x in render(e, df, a.out)])


if __name__ == "__main__":
    main()
