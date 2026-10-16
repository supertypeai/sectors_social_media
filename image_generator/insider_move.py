"""Post type #1, "big insider move": one person's stake changing a lot in one filing, as a carousel.

    python -m image_generator.insider_move --out output_insider_move [--days 14] [--limit 3] [--min-pp 1]

Slides (each only when its data supports it), drawn by iso/hl/render.mjs in the Sectors Hairline style:
  1. move_hook    a question, and six months of the stock's price with the day of the move marked (the hook)
  2. move_gap     the deal price against the market, from Rp 0, when they are far apart
  3. move_owners  who owns the company now, as a donut; the mover's slice and its old size
  4. move_story   the holder's stake over the year as steps, three facts, a question to the reader

Copy rules: every number comes from the data, names are never given pronouns, English.
"""
import argparse
import json
import re
import subprocess
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from .data import fetch_daily_prices, fetch_filings, fetch_supabase_table
from .insider_patterns import drop_mixed_leg_filings

ROOT = Path(__file__).resolve().parent.parent
RENDER_JS = ROOT / "iso" / "hl" / "render.mjs"
PRICE_GAP_MIN = 0.15  # show the price slide only when the trade is ≥15% away from the close
NBSP = " "


# ---------------------------------------------------------------- formatting
def _rp(v):
    a = abs(float(v))
    for div, unit in ((1e12, " T"), (1e9, " B"), (1e6, " M")):
        if a >= div:
            return f"Rp {a / div:.2f}".rstrip("0").rstrip(".") + unit
    return f"Rp {a:,.0f}"


def _shares(n):
    n = float(n)
    return f"{n / 1e9:.2f} B shares" if n >= 1e9 else f"{n / 1e6:.1f} M shares"


def _day(d):
    d = d if isinstance(d, date) else date.fromisoformat(str(d)[:10])
    return f"{d.day} {d:%b}"


def _short_company(name):
    name = re.sub(r"\b(PT|Tbk\.?)\b", "", str(name or "")).strip(" .,")
    return re.sub(r"\s+", " ", name)


def _clean_name(name):
    return re.sub(r"\s+", " ", str(name or "")).strip()


def _name_key(name):
    """Comparable key for a person/company name: lowercase words without titles."""
    words = re.sub(r"[^a-z ]", " ", _clean_name(name).lower()).split()
    return {w for w in words if w not in {"dato", "dr", "pt", "tbk", "h", "ir", "drs", "sri", "tan"}}


def _same_holder(a, b):
    ka, kb = _name_key(a), _name_key(b)
    return bool(ka) and bool(kb) and len(ka & kb) >= min(2, len(ka), len(kb))


# ---------------------------------------------------------------- selection
def select_moves(df, days=14, min_pp=1.0):
    """Single filings where one insider's stake moved by at least `min_pp` percentage points, biggest first.

    A buy and a sell of the same stake in the same stock within three days are one deal seen from both
    sides: they become one move, led by the buyer, with the seller attached as `counterparty`.
    """
    since = (datetime.now() - timedelta(days=days)).isoformat()
    df = df[(df["timestamp"].astype(str) >= since) & df["transaction_type"].isin(["buy", "sell"])].copy()
    df = df.dropna(subset=["share_percentage_before", "share_percentage_after"])
    df["pp"] = (df["share_percentage_after"].astype(float) - df["share_percentage_before"].astype(float)).abs()
    df = df[df["pp"] >= min_pp].sort_values(["pp", "transaction_value"], ascending=False)
    rows = df.drop_duplicates(subset=["symbol", "holder_name"]).to_dict(orient="records")

    moves, used = [], set()
    for i, r in enumerate(rows):
        if i in used:
            continue
        day = date.fromisoformat(_trade_day(r))
        for j, o in enumerate(rows):
            if j == i or j in used or o["symbol"] != r["symbol"] or o["transaction_type"] == r["transaction_type"]:
                continue
            if abs(o["pp"] - r["pp"]) < 0.05 and abs((date.fromisoformat(_trade_day(o)) - day).days) <= 3:
                buyer, seller = (r, o) if r["transaction_type"] == "buy" else (o, r)
                buyer = {**buyer, "counterparty": seller}
                used.update({i, j})
                moves.append(buyer)
                break
        else:
            used.add(i)
            moves.append(r)
    return moves


def _latest_stakes(df, symbol):
    """Each holder's stake after their most recent filing in `df` for this symbol: fresher than the company report."""
    sub = df[df["symbol"] == symbol].dropna(subset=["share_percentage_after"]).sort_values("timestamp")
    return {_clean_name(r["holder_name"]): float(r["share_percentage_after"]) for r in sub.to_dict(orient="records")}


def _leg_days(row):
    """The distinct trade dates of a filing's legs."""
    legs = row.get("price_transaction") or []
    if isinstance(legs, str):
        try:
            legs = json.loads(legs.replace("'", '"'))
        except ValueError:
            legs = []
    return sorted({leg.get("date") for leg in legs if isinstance(leg, dict) and leg.get("date")})


def _trade_day(row):
    days = _leg_days(row)
    return days[-1] if days else str(row["timestamp"])[:10]


# ---------------------------------------------------------------- data for the charts
def _close_on(symbol, day):
    prices = fetch_daily_prices(symbol, since=(date.fromisoformat(day) - timedelta(days=7)).isoformat(), until=day)
    if prices is None or prices.empty:
        return None
    return float(prices.sort_values("date").iloc[-1]["close"])


def _prices(symbol, day, months=6):
    """Daily closes from `months` before the move to today: [{date, close}]."""
    since = (date.fromisoformat(day) - timedelta(days=30 * months)).isoformat()
    df = fetch_daily_prices(symbol, since=since)
    if df is None or df.empty:
        return []
    df = df.dropna(subset=["close"])
    return [{"date": str(r["date"])[:10], "close": float(r["close"])} for r in df.to_dict(orient="records")]


def _stake_history(symbol, holder, before, after, day):
    """The holder's stake as steps over ~4 months up to today: [{date, pct}], from their filings in this stock."""
    since = (date.fromisoformat(day) - timedelta(days=120)).isoformat()
    df = fetch_supabase_table(
        "idx_filings", columns="holder_name, share_percentage_before, share_percentage_after, timestamp",
        since_column="timestamp", since_value=since, symbol_column="symbol", symbol_value=symbol)
    rows = []
    if not df.empty:
        df = df.dropna(subset=["share_percentage_after"])
        rows = sorted((r for r in df.to_dict(orient="records") if _same_holder(r["holder_name"], holder)),
                      key=lambda r: str(r["timestamp"]))
    points = [{"date": since, "pct": float(rows[0]["share_percentage_before"]) if rows and rows[0].get("share_percentage_before") is not None else before}]
    for r in rows:
        points.append({"date": str(r["timestamp"])[:10], "pct": float(r["share_percentage_after"])})
    if not any(p["date"] >= day for p in points[1:]):  # the move itself, if the history query missed it
        points.append({"date": day, "pct": after})
    points.append({"date": date.today().isoformat(), "pct": points[-1]["pct"]})
    return points


def _logo_any(sym):
    """logos/<SYM>.webp, fetched from the Sectors CDN when missing."""
    from .weekly_calendar import _logo
    return _logo(sym)


def _company(symbol):
    df = fetch_supabase_table("idx_company_report", columns="symbol, company_name, sector, major_shareholders",
                              query_modifier=lambda q: q.eq("symbol", symbol))
    return df.iloc[0].to_dict() if not df.empty else {}


# ---------------------------------------------------------------- the carousel
def _trim(name, n=26):
    return name if len(name) <= n else name[: n - 1].rstrip() + "…"


def build_carousel(row, stakes=None):
    """The DATA objects for each slide of one move, in order. `stakes`: {holder: pct} from recent filings."""
    sym = str(row["symbol"]).split(".")[0]
    sell = row["transaction_type"] == "sell"
    holder = _clean_name(row["holder_name"])
    before, after = float(row["share_percentage_before"]), float(row["share_percentage_after"])
    moved = abs(before - after)
    value, shares, price = float(row["transaction_value"]), float(row["amount_transaction"]), float(row["price"])
    day = _trade_day(row)
    co = _company(row["symbol"])
    name = _short_company(co.get("company_name") or sym)
    verb = "sold" if sell else "bought"
    value_txt = _rp(value).replace(" ", NBSP)  # "Rp 26.05 T" never breaks across lines

    seller = row.get("counterparty")
    seller_name = _clean_name(seller["holder_name"]) if seller else None

    # the roster after the filing: the company report's holders, each overwritten by any fresher filing
    # (the mover's own, and e.g. the seller's in a paired deal), then the mover at their new stake
    fresh = dict(stakes or {})
    fresh[holder] = after
    roster = []
    for h in co.get("major_shareholders") or []:
        name_h = _clean_name(h.get("name"))
        match = next((k for k in fresh if _same_holder(k, name_h)), None)
        pct = fresh.pop(match) if match else float(h.get("share_percentage") or 0) * 100
        roster.append({"name": name_h, "pct": pct, "mover": bool(match) and _same_holder(match, holder)})
    roster += [{"name": k, "pct": v, "mover": _same_holder(k, holder)} for k, v in fresh.items()]
    roster = [r for r in roster if r["pct"] > 0.005]
    roster.sort(key=lambda r: -r["pct"])
    for r in roster:  # the mover under the same name as the other slides, not the register's "Dato' Dr …"
        if r["mover"]:
            r["name"] = holder

    base = {
        "direction": row["transaction_type"],
        "kicker": "Change of control" if seller else f"Insider {'selling' if sell else 'buying'}",
        "company": f"{sym} · {name}",
        "logo": (ROOT / "logos" / f"{sym}.webp").as_uri() if (ROOT / "logos" / f"{sym}.webp").exists() else None,
        "source": f"IDX insider filings · filed {_day(str(row['timestamp'])[:10])} {str(row['timestamp'])[:4]}",
    }
    slides = []
    prices = _prices(row["symbol"], day)
    close = _close_on(row["symbol"], day)
    gap_big = bool(close) and abs(price / close - 1) >= PRICE_GAP_MIN

    # 1 · hook: a question, and six months of the stock's price with the day of the move marked on it
    pp = f"{moved:.0f}%" if moved >= 10 else f"{moved:.1f}%"
    when = "in a single day" if len(_leg_days(row)) <= 1 else "in one filing"
    if seller:
        question = f"Why did {pp} of {name} change hands {when}?"
    else:
        question = f"Why would {holder} {'sell' if sell else 'buy'} {pp} of {name} {when}?"
    if len(prices) >= 10:
        slides.append(("move_cover3d", {
            "sym": sym, "name": name, "logo": _logo_any(sym),
            "question": question, "accent": [pp], "prices": prices, "moveDate": day, "holder": _trim(holder, 28),
            "moved": round(moved, 2), "before": round(before, 2), "after": round(after, 2),
            "value": value_txt, "day": _day(day), "buy": not sell,
        }))

    # 2 · the deal price against the market, from Rp 0, when the two are far apart
    if gap_big and len(prices) >= 10:
        cut = (date.fromisoformat(day) - timedelta(days=60)).isoformat()
        recent = [p for p in prices if p["date"] >= cut]
        slides.append(("move_gap", {
            "prices": recent if len(recent) >= 10 else prices, "moveDate": day, "day": _day(day),
            "salePrice": round(price), "close": round(close), "verb": verb, "shares": _shares(shares), "value": value_txt,
        }))

    # 3 · who owns it now, as a donut: the mover's slice in the accent, its old size as a dashed arc.
    # A stale roster that adds past 100% would draw a lie, so then the slide is dropped.
    if len(roster) >= 2 and sum(r["pct"] for r in roster[:5]) <= 100.5:
        slides.append(("move_owners", {
            "title": f"Who owns {sym} now", "accent": [sym], "holder": holder,
            "before": round(before, 2), "after": round(after, 2),
            "rows": [{"name": _trim(r["name"], 40), "pct": round(r["pct"], 2), "mover": bool(r["mover"])} for r in roster[:5]],
        }))

    # 4 · the short version: the holder's stake over the year as steps, three facts, the question
    facts = [{"value": value_txt, "label": f"{verb} on {_day(day)}", "accent": True},
             {"value": f"Rp {price:,.0f}", "label": f"a share · {_shares(shares)}"}]
    if gap_big:
        facts.append({"value": f"{(price / close - 1) * 100:+.0f}%".replace("-", "−"), "label": "vs the close that day"})
    else:
        facts.append({"value": f"{after:.2f}%", "label": "stake now"})
    slides.append(("move_story", {
        "title": f"{_trim(holder, 30)} in {sym}", "accent": [sym],
        "stake": _stake_history(row["symbol"], holder, before, after, day), "moveDate": day, "facts": facts,
        "question": ("A new controlling holder. What do you think comes next?" if seller
                     else "Is it a signal, or just a deal? Tell us what you think." if sell
                     else f"Would you follow {holder} into {sym}?" if len(holder) <= 18
                     else f"Would you follow this buy into {sym}?"),
        "cta": "Track every insider filing on sectors.app",
    }))

    return [(kind, {**base, "slide": {**s, "page": i + 1, "pages": len(slides)}}) for i, (kind, s) in enumerate(slides)]


def render_carousel(row, out_dir, stakes=None):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sym = str(row["symbol"]).split(".")[0]
    paths = []
    for i, (kind, data) in enumerate(build_carousel(row, stakes), 1):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        out = out_dir / f"insider_move_{sym}_{row['transaction_type']}_{i}.png"
        run = subprocess.run(["node", str(RENDER_JS), kind, f.name, "--out", str(out)], capture_output=True, text=True, encoding="utf-8")
        Path(f.name).unlink(missing_ok=True)
        if run.returncode != 0:
            raise RuntimeError(f"render failed for {kind}:\n{run.stderr.strip() or run.stdout.strip()}")
        paths.append(str(out))
    return paths


def main():
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="output_insider_move")
    p.add_argument("--days", type=int, default=14, help="Look at filings from the last N days.")
    p.add_argument("--limit", type=int, default=3)
    p.add_argument("--min-pp", type=float, default=1.0, help="Smallest stake change, in percentage points.")
    args = p.parse_args()
    df = drop_mixed_leg_filings(fetch_filings(since=(datetime.now() - timedelta(days=args.days + 5)).isoformat()))
    moves = select_moves(df, days=args.days, min_pp=args.min_pp)[: args.limit]
    print(f"{len(moves)} big insider moves")
    for row in moves:
        side = f" (from {row['counterparty']['holder_name']})" if row.get("counterparty") else ""
        print(f"  {row['symbol']} {row['holder_name']} {row['transaction_type']} {row['pp']:.2f}pp{side}")
        for path in render_carousel(row, args.out, _latest_stakes(df, row["symbol"])):
            print("   ", path)


if __name__ == "__main__":
    main()
