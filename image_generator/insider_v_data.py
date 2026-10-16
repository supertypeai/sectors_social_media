"""Insider filings, "data-led / story of the deal": one big filing told as five answers.

    python -m image_generator.insider_v_data --out output_feed/insider_v_data [--days 30] [--symbols BYAN,KETR,PPGL]

Slides (iso/hl/slides/feed/insider_v_data, drawn by iso/hl/render.mjs):
  1. ivd_cover   the deal in one number: how much of the company moved, who, for how much
  2. ivd_who     who is this holder: kind of holder, every filing on record across stocks, what else they own
  3. ivd_timing  when: a year of the price, the holder's own trades on it, where the deal day sat in the year's range
  4. ivd_price   at what price: deal vs market vs today, and what the deal price values the whole company at
  5. ivd_after   what changed: the owner table before and after, the related filings around it, the question

Copy rules: every number comes from the data, names are never given pronouns, nothing implies wrongdoing.
"""
import argparse
import json
import re
import subprocess
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from .data import fetch_filings, fetch_supabase_table
from .insider_move import (ROOT, RENDER_JS, _clean_name, _close_on, _day, _leg_days, _logo_any, _prices, _rp,
                           _same_holder, _short_company, _trade_day, select_moves)
from .insider_patterns import drop_mixed_leg_filings

NBSP = " "
ENTITY = re.compile(r"\b(pt|tbk|capital|invest\w*|sentosa|group|holdings?|sekuritas|securities|bank|mandiri|nusantara|"
                    r"ltd|limited|pte|corp\w*|international|resources|global|sejahtera|persada|ventura|enterprise|fund|"
                    r"asset|management|partners|trust|abadi|jaya|makmur|utama|prima|mining|energi|energy)\b", re.I)


def _rpn(v):
    """Short money, three significant figures, never broken across lines: Rp 26 T, Rp 520 B, Rp 59.3 B."""
    a = abs(float(v))
    for div, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if a >= div:
            x = a / div
            s = f"{x:.0f}" if x >= 100 else f"{x:.1f}".rstrip("0").rstrip(".") if x >= 10 else f"{x:.2f}".rstrip("0").rstrip(".")
            return f"Rp{NBSP}{s}{NBSP}{unit}"
    return f"Rp{NBSP}{a:,.0f}"


def _pct(v):
    v = float(v)
    return f"{v:.0f}%" if v >= 10 and abs(v - round(v)) < 0.05 else f"{v:.1f}%" if v >= 10 else f"{v:.2f}%".replace(".00%", "%")


def _legs(row):
    legs = row.get("price_transaction") or []
    if isinstance(legs, str):
        try:
            legs = json.loads(legs.replace("'", '"'))
        except ValueError:
            legs = []
    return [l for l in legs if isinstance(l, dict)]


# ---------------------------------------------------------------- data
_REPORTS = None


def _reports():
    """Every company report's symbol, name and holders, fetched once per run."""
    global _REPORTS
    if _REPORTS is None:
        df = fetch_supabase_table("idx_company_report", columns="symbol, company_name, major_shareholders")
        _REPORTS = df.to_dict(orient="records")
    return _REPORTS


def _shares_out(report):
    for h in report.get("major_shareholders") or []:
        p, n = float(h.get("share_percentage") or 0), float(h.get("share_amount") or 0)
        if p > 0.01 and n > 0:
            return n / p
    return None


def _holder_filings(holder):
    """Every filing on record by this holder, in any stock, oldest first."""
    words = sorted(re.sub(r"[^A-Za-z ]", " ", holder).split(), key=len, reverse=True)
    df = fetch_supabase_table(
        "idx_filings", columns="symbol, holder_name, transaction_type, share_percentage_before, share_percentage_after, "
        "price, amount_transaction, transaction_value, price_transaction, timestamp",
        query_modifier=lambda q: q.ilike("holder_name", f"%{words[0]}%"))
    if df.empty:
        return []
    rows = [r for r in df.to_dict(orient="records") if _same_holder(r["holder_name"], holder)
            and r["transaction_type"] in ("buy", "sell")]
    return sorted(rows, key=lambda r: str(r["timestamp"]))


def _holder_kind(holder):
    """('listed', 'DSSA') when the holder is itself a listed company, else ('company'|'person', None)."""
    for rep in _reports():
        if _same_holder(rep.get("company_name") or "", holder) and len(holder.split()) >= 2:
            return "listed", str(rep["symbol"]).split(".")[0]
    return ("company" if ENTITY.search(holder) else "person"), None


def _holdings(holder, sym, after):
    """The holder's stakes in listed companies, from every company report; this stock at its post-deal stake."""
    out = []
    for rep in _reports():
        s = str(rep["symbol"]).split(".")[0]
        for h in rep.get("major_shareholders") or []:
            if _same_holder(h.get("name") or "", holder):
                out.append({"sym": s, "pct": float(h.get("share_percentage") or 0) * 100})
                break
    out = [o for o in out if o["sym"] != sym]
    out.append({"sym": sym, "pct": after, "this": True})
    out = [o for o in out if o["pct"] > 0.005 or o.get("this")]
    out.sort(key=lambda o: (not o.get("this"), -o["pct"]))
    for o in out:
        o["logo"] = _logo_any(o["sym"])
    return out[:5]


def _rosters(sym_jk, df_recent, move_day):
    """The owner table just before and after the move: the company report, overwritten by fresher filings."""
    rep = next((r for r in _reports() if r["symbol"] == sym_jk), {})
    base = [{"name": _clean_name(h.get("name")), "pct": float(h.get("share_percentage") or 0) * 100}
            for h in rep.get("major_shareholders") or [] if _clean_name(h.get("name")).lower() != "public"]
    sub = df_recent[df_recent["symbol"] == sym_jk].dropna(subset=["share_percentage_after"]).sort_values("timestamp")
    rows = sub.to_dict(orient="records")

    def table(until, strict):
        t = [dict(b) for b in base]
        for r in rows:  # by trade date, not filing time: the two sides of one deal are filed days apart
            d = _trade_day(r)
            if d > until or (strict and d == until):
                continue
            name = _clean_name(r["holder_name"])
            hit = next((x for x in t if _same_holder(x["name"], name)), None)
            if hit:
                hit["pct"] = float(r["share_percentage_after"])
                hit["name"] = name
            elif float(r["share_percentage_after"]) >= 5 or float(r["share_percentage_before"] or 0) >= 5:
                t.append({"name": name, "pct": float(r["share_percentage_after"])})
        return t

    return table(move_day, True), table(move_day, False)


# ---------------------------------------------------------------- the carousel
def build(row, df_recent):
    sym = str(row["symbol"]).split(".")[0]
    sell = row["transaction_type"] == "sell"
    holder = _clean_name(row["holder_name"])
    before, after = float(row["share_percentage_before"]), float(row["share_percentage_after"])
    moved = abs(after - before)
    value, shares, price = float(row["transaction_value"]), float(row["amount_transaction"]), float(row["price"])
    day = _trade_day(row)
    rep = next((r for r in _reports() if r["symbol"] == row["symbol"]), {})
    name = _short_company(rep.get("company_name") or sym)
    verb = "sold" if sell else "bought"
    seller = row.get("counterparty")
    kind, listed_sym = _holder_kind(holder)
    logo = _logo_any(sym)

    base = {
        "direction": row["transaction_type"],
        "kicker": "Change of control" if seller else f"Insider {'selling' if sell else 'buying'}",
        "company": f"{sym} · {name}",
        "logo": logo,
        "source": f"IDX insider filings · filed {_day(str(row['timestamp'])[:10])} {str(row['timestamp'])[:4]}",
    }
    slides = []

    # 1 · cover: one number
    full_exit = sell and after < 0.005
    line = (f"{holder} {verb} {'the whole stake' if full_exit else 'a ' + _pct(moved) + ' stake'} for {_rpn(value)}."
            if not seller else f"{holder} bought it for {_rpn(value)}, from {_clean_name(seller['holder_name'])}.")
    slides.append(("ivd_cover", {
        "sym": sym, "name": name, "logoSym": logo, "big": _pct(moved), "of": f"of {name}",
        "verbLine": f"{'changed hands' if seller else verb} {'in a single day' if len(_leg_days(row)) <= 1 else 'in one filing'}",
        "line": line, "buy": not sell,
        "strip": [{"v": f"{_pct(before)} → {_pct(after)}", "l": "stake before → after"},
                  {"v": f"Rp {price:,.0f}", "l": "price a share"},
                  {"v": _day(day), "l": "trade date"}],
    }))

    # 2 · who: kind, filings on record, holdings
    filings = _holder_filings(holder)
    stocks = sorted({str(f["symbol"]).split(".")[0] for f in filings})
    buys = sum(f["transaction_type"] == "buy" for f in filings)
    first = str(filings[0]["timestamp"])[:10] if filings else day
    tape = []
    for f in filings:
        legs = _legs(f)
        d = legs[-1].get("date") if legs and legs[-1].get("date") else str(f["timestamp"])[:10]
        tape.append({"sym": str(f["symbol"]).split(".")[0], "date": d, "buy": f["transaction_type"] == "buy",
                     "value": float(f["transaction_value"] or 0), "move": str(f["timestamp"]) == str(row["timestamp"])})
    who_line = {"listed": f"A listed company ({listed_sym}).",
                "company": "A company, not a person.",
                "person": "An individual, not a company."}[kind]
    slides.append(("ivd_who", {
        "title": f"Who is {holder}?", "holder": holder, "whoLine": who_line, "listedSym": listed_sym,
        "listedLogo": _logo_any(listed_sym) if listed_sym else None,
        "stats": [{"v": str(len(filings)), "l": f"filing{'s' if len(filings) != 1 else ''} since {_day(first)} {first[:4]}"},
                  {"v": f"{buys} / {len(filings) - buys}", "l": "buys / sells"},
                  {"v": str(len(stocks)), "l": f"stock{'s' if len(stocks) != 1 else ''} traded"}],
        "holdings": _holdings(holder, sym, after), "tape": tape, "moveDate": day,
    }))

    # 3 · timing: a year of the price and the holder's own trades in this stock
    prices = _prices(row["symbol"], day, months=12)
    close = _close_on(row["symbol"], day) or price
    if len(prices) >= 20:
        year = [p["close"] for p in prices if p["date"] <= day and p["date"] >= (date.fromisoformat(day) - timedelta(days=365)).isoformat()]
        rank = sum(c < close for c in year) / max(1, len(year))
        trades = []
        for f in filings:
            if str(f["symbol"]).split(".")[0] != sym:
                continue
            for l in _legs(f) or [{"date": str(f["timestamp"])[:10], "price": f["price"]}]:
                if l.get("price") and l.get("date") and l["date"] >= prices[0]["date"]:
                    trades.append({"date": l["date"], "price": float(l["price"]), "buy": f["transaction_type"] == "buy",
                                   "move": str(f["timestamp"]) == str(row["timestamp"])})
        third = "top third" if rank >= 2 / 3 else "bottom third" if rank < 1 / 3 else "middle third"
        slides.append(("ivd_timing", {
            "title": f"Did {'the seller sell' if sell else 'the buyer buy'} near the {'top' if sell else 'bottom'}?",
            "answer": f"On {_day(day)} {sym} closed at Rp {close:,.0f}, in the {third} of its past year."
                      + (f" The deal itself was priced at Rp {price:,.0f}." if abs(price / close - 1) >= 0.15 else ""),
            "prices": prices, "trades": trades, "moveDate": day, "close": close, "now": prices[-1]["close"],
            "lo": min(year), "hi": max(year), "rank": round(rank * 100),
        }))

    # 4 · price: deal vs market vs today, and the implied value of the whole company
    so = _shares_out(rep)
    now = prices[-1]["close"] if prices else close
    gap = price / close - 1
    slides.append(("ivd_price", {
        "title": f"Rp {price:,.0f} a share vs the market", "accent": [f"{price:,.0f}"],
        "bars": [{"l": "deal price", "v": price, "acc": True}, {"l": f"market close {_day(day)}", "v": close},
                 {"l": "today", "v": now}],
        "gap": round(gap * 100), "sinceDeal": round((now / close - 1) * 100),
        "implied": round(price * so) if so else None, "market": round(close * so) if so else None,
        "impliedTxt": _rpn(price * so) if so else None, "marketTxt": _rpn(close * so) if so else None,
        "name": name,
        "note": ("A price this far from the market usually means the two sides agreed it privately, off the exchange."
                 if abs(gap) >= 0.15 else "Close to the market price, like a normal trade on the exchange."),
    }))

    # 5 · what changed: owners before and after, and the filings around this one
    bef, aft = _rosters(row["symbol"], df_recent, day)
    for t, v in ((bef, before), (aft, after)):
        hit = next((x for x in t if _same_holder(x["name"], holder)), None)
        if hit:
            hit["pct"], hit["name"] = v, holder
        else:
            t.append({"name": holder, "pct": v})
    names = []
    for x in sorted(bef + aft, key=lambda x: -x["pct"]):
        if not any(_same_holder(x["name"], n) for n in names):
            names.append(x["name"])
    rows = []
    for n in names[:4]:
        b = next((x["pct"] for x in bef if _same_holder(x["name"], n)), 0.0)
        a = next((x["pct"] for x in aft if _same_holder(x["name"], n)), 0.0)
        rows.append({"name": n, "before": round(b, 2), "after": round(a, 2), "mover": _same_holder(n, holder)})
    if not any(r["mover"] for r in rows):
        rows[-1] = {"name": holder, "before": before, "after": after, "mover": True}
    # filings by others in this stock within two weeks of the move, biggest first
    near = df_recent[(df_recent["symbol"] == row["symbol"])].to_dict(orient="records")
    d0 = date.fromisoformat(day)
    rel = []
    if seller:  # a change of control: the seller's own filings tell how the stake left
        near = [r for r in near if _same_holder(r["holder_name"], seller["holder_name"])]
    for r in near:
        if _same_holder(r["holder_name"], holder) and str(r["timestamp"]) == str(row["timestamp"]):
            continue
        rd = date.fromisoformat(_trade_day(r))
        if abs((rd - d0).days) <= 14 and r["transaction_type"] in ("buy", "sell"):
            pp = abs(float(r["share_percentage_after"] or 0) - float(r["share_percentage_before"] or 0))
            rel.append({"date": _day(rd), "t": rd.isoformat(), "name": _clean_name(r["holder_name"]),
                        "buy": r["transaction_type"] == "buy", "pp": round(pp, 2), "price": float(r["price"] or 0)})
    rel = sorted(sorted(rel, key=lambda r: -r["pp"])[:3], key=lambda r: r["t"])
    gone = 100 - sum(r["after"] for r in rows)
    slides.append(("ivd_after", {
        "title": f"Who owns {sym} after the deal", "accent": [sym], "rows": rows, "related": rel,
        "question": (f"{sym} has a new controlling holder. What do you expect next?" if seller
                     else f"Why do you think they left {sym} completely?" if full_exit
                     else f"Would you sell {sym} too?" if sell
                     else f"Would you follow this buy into {sym}?"),
        "cta": "Track every insider filing on sectors.app",
        "buyerUnknown": sell and not seller and moved >= 5,
    }))

    return [(k, {**base, "slide": {**s, "page": i + 1, "pages": len(slides)}}) for i, (k, s) in enumerate(slides)]


def render(row, df_recent, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (kind, data) in enumerate(build(row, df_recent), 1):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        p = out / f"{i}.png"
        run = subprocess.run(["node", str(RENDER_JS), kind, f.name, "--out", str(p)], capture_output=True, text=True, encoding="utf-8")
        Path(f.name).unlink(missing_ok=True)
        if run.returncode != 0:
            raise RuntimeError(f"render failed for {kind}:\n{run.stderr.strip() or run.stdout.strip()}")
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
    p.add_argument("--out", default="output_feed/insider_v_data")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--symbols", default="BYAN,KETR,PPGL")
    p.add_argument("--dump", action="store_true", help="Print the slide data instead of rendering.")
    a = p.parse_args()
    df = drop_mixed_leg_filings(fetch_filings(since=(datetime.now() - timedelta(days=a.days + 20)).isoformat()))
    moves = select_moves(df, days=a.days, min_pp=1.0)
    done = []
    for s in a.symbols.split(","):
        row = next((m for m in moves if str(m["symbol"]).split(".")[0] == s), None)
        if row is None:
            print(f"{s}: no move in the last {a.days} days")
            continue
        if a.dump:
            for k, d in build(row, df):
                sl = {k2: v for k2, v in d["slide"].items() if k2 not in ("prices",)}
                print(s, k, json.dumps(sl, ensure_ascii=False, default=str)[:900])
            continue
        print(s, render(row, df, Path(a.out) / s))
        done.append(s)
    if done:
        sheet(a.out, done)


if __name__ == "__main__":
    main()
