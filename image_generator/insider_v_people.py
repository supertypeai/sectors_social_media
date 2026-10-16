"""Insider move, "people & objects" direction: the deal told as a magazine story about the holder.

    python -m image_generator.insider_v_people --out output_feed/insider_v_people [--days 30] [--symbols BYAN KETR PPGL]

Slides (iso/hl/slides/feed/insider_v_people/, drawn by iso/hl/render.mjs):
  1. vp_cover   the holder's name set big, one line on the deal, and the company as 100 seats (1 seat = 1%)
  2. vp_ticket  the deal as a receipt: who, when, how many shares, at what price, against that day's close
  3. vp_room    every insider filing on the stock in six months, as a timeline ribbon (when there are 3+)
  4. vp_price   the deal price against the market since, so the reader sees where the stock is now
  5. vp_table   who holds the company before and after, as two cap-table bars, and a question
"""
import argparse
import json
import subprocess
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from .data import fetch_filings, fetch_supabase_table
from .insider_patterns import drop_mixed_leg_filings
from .insider_move import (NBSP, RENDER_JS, ROOT, _clean_name, _close_on, _company, _day, _latest_stakes, _leg_days,
                           _logo_any, _name_key, _prices, _rp, _same_holder, _shares, _short_company, _trade_day,
                           select_moves)


def _legs(row):
    legs = row.get("price_transaction") or []
    if isinstance(legs, str):
        try:
            legs = json.loads(legs.replace("'", '"'))
        except ValueError:
            legs = []
    return [l for l in legs if isinstance(l, dict) and l.get("price") and l.get("amount_transacted")]


_LISTED = None


def _listed_symbol(holder):
    """The ticker of a listed company whose name is the holder's (e.g. Dian Swastatika Sentosa -> DSSA), or None."""
    global _LISTED
    if _LISTED is None:
        df = fetch_supabase_table("idx_company_report", columns="symbol, company_name")
        _LISTED = [(str(r["symbol"]).split(".")[0], _name_key(r["company_name"])) for r in df.to_dict(orient="records")]
    k = _name_key(holder)
    if len(k) < 2:
        return None
    for sym, ck in _LISTED:
        if ck and k == ck:
            return sym
    return None


def _badge(name):
    """A holder's badge: the listed company's logo when the holder is one, else initials."""
    sym = _listed_symbol(name)
    words = [w for w in _clean_name(name).split() if w[:1].isalpha()]
    return {"name": _clean_name(name), "sym": sym, "logo": _logo_any(sym) if sym else None,
            "initials": "".join(w[0] for w in words[:2]).upper()}


def _roster(co, stakes, holder, before, after, seller=None):
    """[{name, before, after, role}] from the company report overlaid with fresher filings. role: mover|seller|other."""
    fresh = dict(stakes or {})
    fresh[holder] = after
    prev = {holder: before}
    if seller:
        fresh[_clean_name(seller["holder_name"])] = float(seller["share_percentage_after"])
        prev[_clean_name(seller["holder_name"])] = float(seller["share_percentage_before"])
    out = []
    for h in co.get("major_shareholders") or []:
        n = _clean_name(h.get("name"))
        if n.lower() == "public":
            continue
        rep = float(h.get("share_percentage") or 0) * 100
        m = next((k for k in fresh if _same_holder(k, n)), None)
        now = fresh.pop(m) if m else rep
        out.append({"name": m or n, "after": now})
    out += [{"name": k, "after": v} for k, v in fresh.items()]
    for r in out:
        p = next((k for k in prev if _same_holder(k, r["name"])), None)
        r["before"] = prev[p] if p else r["after"]
        r["role"] = "mover" if _same_holder(r["name"], holder) else "seller" if p else "other"
    out = [r for r in out if max(r["before"], r["after"]) >= 1.0]
    out.sort(key=lambda r: -max(r["before"], r["after"]))
    return out[:5]


def _room(symbol, holder, day):
    """Every buy/sell filing on the stock in the six months up to now: [{date, name, type, pp, value, mover}]."""
    since = (date.fromisoformat(day) - timedelta(days=180)).isoformat()
    df = fetch_supabase_table(
        "idx_filings", columns="holder_name, transaction_type, share_percentage_before, share_percentage_after, transaction_value, timestamp, price_transaction",
        since_column="timestamp", since_value=since, symbol_column="symbol", symbol_value=symbol)
    out = []
    for r in df.to_dict(orient="records") if not df.empty else []:
        if r["transaction_type"] not in ("buy", "sell"):
            continue
        b, a = r.get("share_percentage_before"), r.get("share_percentage_after")
        out.append({"date": _trade_day(r), "name": _clean_name(r["holder_name"]), "type": r["transaction_type"],
                    "pp": round(abs(float(a) - float(b)), 2) if a is not None and b is not None else 0,
                    "value": float(r.get("transaction_value") or 0), "mover": _same_holder(r["holder_name"], holder)})
    names = [_clean_name(holder)]  # one spelling per holder ("Lintas Benua" and "PT Gema Lintas Benua" are the same filer)
    for e in out:
        same = next((n for n in names if _same_holder(n, e["name"])), None)
        if same is None:
            names.append(e["name"])
        elif len(e["name"]) > len(same) and not _same_holder(same, holder):
            names[names.index(same)] = e["name"]
    for e in out:
        e["name"] = next(n for n in names if _same_holder(n, e["name"]))
    return sorted(out, key=lambda x: x["date"])


def build(row, stakes):
    sym = str(row["symbol"]).split(".")[0]
    sell = row["transaction_type"] == "sell"
    holder = _clean_name(row["holder_name"])
    before, after = float(row["share_percentage_before"]), float(row["share_percentage_after"])
    moved = abs(after - before)
    value, shares, price = float(row["transaction_value"]), float(row["amount_transaction"]), float(row["price"])
    day = _trade_day(row)
    days = _leg_days(row)
    co = _company(row["symbol"])
    name = _short_company(co.get("company_name") or sym)
    seller = row.get("counterparty")
    value_txt = _rp(value).replace(" ", NBSP)
    pp = f"{moved:.0f}%" if moved >= 10 else f"{moved:.1f}%"
    close = _close_on(row["symbol"], day)
    prices = _prices(row["symbol"], day, months=3)

    base = {
        "direction": row["transaction_type"],
        "kicker": "Change of control" if seller else "Insider filing",
        "company": f"{sym} · {name}",
        "logo": _logo_any(sym),
        "source": f"IDX insider filings · filed {_day(str(row['timestamp'])[:10])} {str(row['timestamp'])[:4]}",
    }
    who = _badge(holder)
    other = _badge(seller["holder_name"]) if seller else None
    span = _day(days[0]) + "–" + _day(days[-1]) if len(days) > 1 and days[0] != days[-1] else _day(day)

    slides = []
    # 1 · cover
    if seller:
        headline = f"took {pp} of {name} from {' '.join(_short_company(other['name']).split()[:2])}"
    elif sell and after < 0.005:
        headline = f"sold the whole {pp} stake in {name}"
    else:
        headline = f"{'sold' if sell else 'bought'} {pp} of {name}"
    slides.append(("vp_cover", {
        "holder": who, "other": other, "headline": headline, "accent": [pp], "sym": sym, "name": name,
        "before": round(before, 2), "after": round(after, 2), "sell": sell,
        "otherBefore": round(float(seller["share_percentage_before"]), 2) if seller else None,
        "otherAfter": round(float(seller["share_percentage_after"]), 2) if seller else None,
        "value": value_txt, "span": span, "year": day[:4], "holderType": str(row.get("holder_type") or "").strip(),
    }))

    # 2 · ticket
    legs = _legs(row)
    slides.append(("vp_ticket", {
        "holder": who, "other": other, "sell": sell, "sym": sym, "name": name,
        "span": span, "year": day[:4], "shares": _shares(shares), "price": round(price, 1), "value": value_txt,
        "closeDay": _day(day), "close": round(close) if close else None, "gap": round((price / close - 1) * 100, 1) if close else None,
        "before": round(before, 2), "after": round(after, 2),
        "otherBefore": round(float(seller["share_percentage_before"]), 2) if seller else None,
        "otherAfter": round(float(seller["share_percentage_after"]), 2) if seller else None,
        "legs": [{"date": _day(l["date"]), "price": float(l["price"]), "shares": _shares(l["amount_transacted"])} for l in legs][:6],
        "nLegs": len(legs), "filed": _day(str(row["timestamp"])[:10]),
    }))

    # 3 · the room: only when the stock had at least three filings from at least two holders
    room = _room(row["symbol"], holder, day)
    if len(room) >= 3 and len({_clean_name(r["name"]).lower() for r in room}) >= 2:
        slides.append(("vp_room", {"sym": sym, "events": room, "moveDate": day, "today": date.today().isoformat(),
                                    "holder": holder}))

    # 4 · price since
    if len(prices) >= 10:
        last = prices[-1]
        slides.append(("vp_price", {
            "prices": prices, "moveDate": day, "dealPrice": round(price, 1), "sell": sell, "sym": sym,
            "last": last["close"], "lastDay": _day(last["date"]), "close": round(close) if close else None,
        }))

    # 5 · the table
    rows = _roster(co, stakes, holder, before, after, seller)
    slides.append(("vp_table", {
        "sym": sym, "rows": rows, "sell": sell, "paired": bool(seller),
        "question": ("New name at the top of the table. What changes next?" if seller
                     else "One holder fewer at the table. Who do you think bought?" if sell and after < 0.005
                     else "A big seat freed up. Signal, or just a deal?" if sell
                     else "Would you sit at this table too?"),
        "cta": "Track every insider filing on sectors.app",
    }))
    return [(k, {**base, "slide": {**s, "page": i + 1, "pages": len(slides)}}) for i, (k, s) in enumerate(slides)]


def render(row, out_dir, stakes):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (kind, data) in enumerate(build(row, stakes), 1):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        out = out_dir / f"{i}_{kind}.png"
        run = subprocess.run(["node", str(RENDER_JS), kind, f.name, "--out", str(out)], capture_output=True, text=True, encoding="utf-8")
        Path(f.name).unlink(missing_ok=True)
        if run.returncode != 0:
            raise RuntimeError(f"render failed for {kind}:\n{run.stderr.strip() or run.stdout.strip()}")
        paths.append(out)
    return paths


def sheet(groups, out):
    from PIL import Image
    tw, th, gap = 324, 405, 12
    cols = max(len(g) for g in groups)
    img = Image.new("RGB", (cols * (tw + gap) + gap, len(groups) * (th + gap) + gap), (20, 18, 16))
    for r, g in enumerate(groups):
        for c, p in enumerate(g):
            img.paste(Image.open(p).convert("RGB").resize((tw, th), Image.LANCZOS), (gap + c * (tw + gap), gap + r * (th + gap)))
    img.save(out)


def main():
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="output_feed/insider_v_people")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--symbols", nargs="*", default=None)
    args = p.parse_args()
    df = drop_mixed_leg_filings(fetch_filings(since=(datetime.now() - timedelta(days=args.days + 5)).isoformat()))
    moves, seen = [], set()
    for m in select_moves(df, days=args.days):  # biggest first: keep each stock's biggest move
        s = str(m["symbol"]).split(".")[0]
        if s in seen or (args.symbols and s not in args.symbols):
            continue
        seen.add(s)
        moves.append(m)
    groups = []
    for m in moves:
        s = str(m["symbol"]).split(".")[0]
        print(s, m["holder_name"], m["transaction_type"], m["pp"])
        groups.append(render(m, Path(args.out) / s, _latest_stakes(df, m["symbol"])))
        for path in groups[-1]:
            print("  ", path)
    if groups:
        sheet(groups, Path(args.out) / "_sheet.png")


if __name__ == "__main__":
    main()
