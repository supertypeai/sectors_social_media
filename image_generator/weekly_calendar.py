"""Weekly calendar: every IDX corporate-action date in the coming week, as one carousel.

    python -m image_generator.weekly_calendar --out output_weekly_calendar [--start 2026-10-13] [--days 7]

Slides, drawn by iso/hl/render.mjs in the Sectors Hairline style:
  1. cal_week     one row per trading day: the date large, that day's events grouped by type, with logos
  2. cal_divs     the week's dividends ranked by yield: Rp a share, yield, cum date
  3. cal_actions  rights issues, splits, warrants, AGMs: what each one is, in one line
  4. cal_close    the question and the CTA

Sources: idx_upcoming_dividend (+ last close for yield), idx_right_issue, idx_stock_split, idx_warrant, idx_agm,
idx_ipo_details. Weekend dates are not trading days and are left out.
"""
import argparse
import json
import subprocess
import tempfile
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from .data import fetch_supabase_table

ROOT = Path(__file__).resolve().parent.parent
RENDER_JS = ROOT / "iso" / "hl" / "render.mjs"

# kind → (group label, order on a row)
GROUPS = {"div": "Dividend", "rights": "Rights", "split": "Split", "warrant": "Warrant", "agm": "AGM", "ipo": "IPO"}
WHAT = {"Cum date": "cum", "Ex date": "ex", "Trading starts": "trading", "Trading ends": "last trading", "Subscription": "subscribe",
        "Last day": "last day",  # rights: last day to trade AND to subscribe, when they are the same day
        "Meeting": "", "Matures": "matures", "Offering": "offering", "Listing": "listing"}


LOGO_URL = "https://storage.googleapis.com/sectorsapp-sea/logo/{}.webp"  # same source as renderers/foreign_flow.py


def _logo(sym):
    """The company's logo from logos/, fetched once from the Sectors CDN when missing; None if there is none."""
    p = ROOT / "logos" / f"{sym}.webp"
    if not p.exists():
        try:
            with urllib.request.urlopen(LOGO_URL.format(sym), timeout=6) as r:
                if r.status == 200 and r.headers.get_content_type().startswith("image/"):
                    p.write_bytes(r.read())
        except Exception:
            return None
    return p.as_uri() if p.exists() else None


def _between(table, columns, date_cols, start, end):
    """Rows of `table` with any of `date_cols` inside [start, end]."""
    out = []
    for c in date_cols:
        df = fetch_supabase_table(table, columns=columns,
                                  query_modifier=lambda q, c=c: q.gte(c, start.isoformat()).lte(c, end.isoformat()))
        out += df.to_dict(orient="records")
    return out


def _d(v):
    return date.fromisoformat(str(v)[:10]) if v else None


def collect(start, end):
    """[{day, kind, sym, what}] for every event date inside the window, plus detail rows per kind."""
    ev, seen = [], set()

    def add(day, kind, sym, what):
        day = _d(day)
        sym = str(sym).split(".")[0]
        if not day or not (start <= day <= end) or day.weekday() >= 5 or (day, kind, sym, what) in seen:
            return
        seen.add((day, kind, sym, what))
        ev.append({"day": day, "kind": kind, "sym": sym, "what": what})

    divs = _between("idx_upcoming_dividend", "symbol, dividend_amount, cum_date, ex_date, payment_date",
                    ["cum_date", "ex_date", "payment_date"], start, end)
    for r in divs:
        add(r["cum_date"], "div", r["symbol"], "Cum date")
        add(r["ex_date"], "div", r["symbol"], "Ex date")
        add(r["payment_date"], "div", r["symbol"], "Pay date")

    rights = _between("idx_right_issue", "symbol, old_ratio, new_ratio, price, cum_date, ex_date, trading_period_start, trading_period_end, subscription_date",
                      ["cum_date", "ex_date", "trading_period_start", "trading_period_end", "subscription_date"], start, end)
    for r in rights:
        add(r["cum_date"], "rights", r["symbol"], "Cum date")
        add(r["ex_date"], "rights", r["symbol"], "Ex date")
        add(r["trading_period_start"], "rights", r["symbol"], "Trading starts")
        # the last trading day and the subscription date fall on the same day in 97% of IDX rights issues (all 26
        # in 2026): one "last day" row then, not two rows of the same tickers. Kept apart when they differ.
        if _d(r["trading_period_end"]) and _d(r["trading_period_end"]) == _d(r["subscription_date"]):
            add(r["trading_period_end"], "rights", r["symbol"], "Last day")
        else:
            add(r["trading_period_end"], "rights", r["symbol"], "Trading ends")
            add(r["subscription_date"], "rights", r["symbol"], "Subscription")

    splits = _between("idx_stock_split", "symbol, split_ratio, cum_date, date", ["cum_date", "date"], start, end)
    for r in splits:
        add(r["cum_date"] or r["date"], "split", r["symbol"], "Cum date")

    warrants = _between("idx_warrant", "symbol, ratio_warrant, ratio_shares, price, trading_period_start, trading_period_end, maturity_date",
                        ["trading_period_start", "trading_period_end", "maturity_date"], start, end)
    for r in warrants:
        add(r["trading_period_start"], "warrant", r["symbol"], "Trading starts")
        add(r["trading_period_end"], "warrant", r["symbol"], "Trading ends")
        add(r["maturity_date"], "warrant", r["symbol"], "Matures")

    agms = _between("idx_agm", "symbol, agm_date, agm_time", ["agm_date"], start, end)
    for r in agms:
        add(r["agm_date"], "agm", r["symbol"], "Meeting")

    ipos = _between("idx_ipo_details", "symbol, offering_price, offering_start_date, listing_date", ["offering_start_date", "listing_date"], start, end)
    for r in ipos:
        add(r["offering_start_date"], "ipo", r["symbol"], "Offering")
        add(r["listing_date"], "ipo", r["symbol"], "Listing")

    return ev, {"div": divs, "rights": rights, "split": splits, "warrant": warrants, "agm": agms, "ipo": ipos}


def _closes(symbols):
    if not symbols:
        return {}
    since = (date.today() - timedelta(days=10)).isoformat()
    df = fetch_supabase_table("idx_daily_data", columns="symbol, close, date", since_column="date", since_value=since,
                              order_column="date", order_desc=True, query_modifier=lambda q: q.in_("symbol", symbols))
    return {} if df.empty else df.drop_duplicates("symbol").set_index("symbol")["close"].astype(float).to_dict()


def _day(d):
    return f"{d.day} {d:%b}"


def _ratio(a, b):
    def n(x):
        x = float(x)
        return f"{x:,.0f}" if x == int(x) else f"{x:g}"
    return f"{n(a)}:{n(b)}"


def build_carousel(start, end):
    ev, detail = collect(start, end)
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            # one line per (type, date kind): "Dividend · cum", "Rights · trading" … Pay dates need no action, so they
            # stay off the calendar (they are on the dividend slide).
            items = [e for e in ev if e["day"] == d and e["what"] != "Pay date"]
            groups = []
            for kind, label in GROUPS.items():
                for what in dict.fromkeys(e["what"] for e in items if e["kind"] == kind):
                    g = [{"sym": e["sym"], "logo": _logo(e["sym"])} for e in items if e["kind"] == kind and e["what"] == what]
                    groups.append({"kind": kind, "label": label, "what": WHAT.get(what, what.lower()), "items": g})
            days.append({"date": d.isoformat(), "day": d.day, "mon": f"{d:%b}".upper(), "dow": f"{d:%a}".upper(), "groups": groups, "today": d == date.today()})
        d += timedelta(days=1)
    week = f"{_day(start)} – {_day(end)}"
    base = {"direction": "fig", "kicker": "Weekly calendar", "company": "IDX · Indonesia Stock Exchange", "logo": None,
            "source": "IDX corporate actions · Sectors"}
    slides = [("cal_week", {"title": "The week ahead", "week": week, "days": days,
                             "total": sum(len(g["items"]) for d in days for g in d["groups"])})]

    # dividends, ranked by yield
    divs = {}
    for r in detail["div"]:  # only dividends you can still buy into: cum date today or later
        if not r.get("cum_date") or _d(r["cum_date"]) < start:
            continue
        sym = r["symbol"].split(".")[0]
        if sym not in divs or str(r["cum_date"]) < str(divs[sym]["cum_date"]):
            divs[sym] = r
    closes = _closes([r["symbol"] for r in divs.values()])
    rows = []
    for sym, r in divs.items():
        close = closes.get(r["symbol"])
        amt = float(r["dividend_amount"] or 0)
        rows.append({"sym": sym, "logo": _logo(sym), "amount": amt, "yield": (amt / close * 100) if close else None,
                     "cum": _day(_d(r["cum_date"])) if r.get("cum_date") else "–",
                     "pay": _day(_d(r["payment_date"])) if r.get("payment_date") else "–"})
    rows.sort(key=lambda x: -(x["yield"] or 0))
    if rows:
        slides.append(("cal_divs", {"title": "Dividends you can still catch", "rows": rows[:6]}))

    # the other corporate actions, each in one plain line
    acts = []
    for r in detail["rights"]:
        sym = r["symbol"].split(".")[0]
        acts.append({"sym": sym, "logo": _logo(sym), "kind": "Rights issue",
                     "line": f"{_ratio(r['old_ratio'], r['new_ratio'])} at Rp {float(r['price']):,.0f}" if r.get("price") else _ratio(r["old_ratio"], r["new_ratio"]),
                     "note": "Holders get the right to buy new shares"})
    for r in detail["split"]:
        sym = r["symbol"].split(".")[0]
        acts.append({"sym": sym, "logo": _logo(sym), "kind": "Stock split", "line": f"1 share becomes {float(r['split_ratio']):g}" if r.get("split_ratio") else "",
                     "note": "More shares, lower price, same value"})
    for r in detail["warrant"]:
        sym = r["symbol"].split(".")[0]
        acts.append({"sym": sym, "logo": _logo(sym), "kind": "Warrant", "line": f"Exercise at Rp {float(r['price']):,.0f}" if r.get("price") else "",
                     "note": "A right to buy shares later at a fixed price"})
    for r in detail["agm"]:
        sym = r["symbol"].split(".")[0]
        acts.append({"sym": sym, "logo": _logo(sym), "kind": "AGM", "line": _day(_d(r["agm_date"])) + (f" · {str(r['agm_time'])[:5]}" if r.get("agm_time") else ""),
                     "note": "Shareholders vote on the company's plans"})
    uniq = {}
    for a in acts:
        uniq.setdefault((a["sym"], a["kind"]), a)
    if uniq:
        slides.append(("cal_actions", {"title": "Other corporate actions", "rows": list(uniq.values())[:6]}))

    slides.append(("cal_close", {"question": "Which one is on your watchlist this week?", "save": "Save this for the week",
                                 "cta": "Full calendar on sectors.app", "days": days}))
    return [(k, {**base, "slide": {**s, "page": i + 1, "pages": len(slides)}}) for i, (k, s) in enumerate(slides)]


def render(start, end, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (kind, data) in enumerate(build_carousel(start, end), 1):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
        out = out_dir / f"weekly_calendar_{start:%Y%m%d}_{i}.png"
        run = subprocess.run(["node", str(RENDER_JS), kind, f.name, "--out", str(out)], capture_output=True, text=True, encoding="utf-8")
        Path(f.name).unlink(missing_ok=True)
        if run.returncode != 0:
            raise RuntimeError(f"render failed for {kind}:\n{run.stderr.strip() or run.stdout.strip()}")
        paths.append(str(out))
    return paths


def main():
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="output_weekly_calendar")
    p.add_argument("--start", default=date.today().isoformat())
    p.add_argument("--days", type=int, default=7)
    args = p.parse_args()
    start = date.fromisoformat(args.start)
    for path in render(start, start + timedelta(days=args.days - 1), args.out):
        print(path)


if __name__ == "__main__":
    main()
