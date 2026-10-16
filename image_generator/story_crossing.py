"""Instagram story, "crossing 5%": an investor becoming a major shareholder, in two 9:16 frames.

    python -m image_generator.story_crossing [--out output_stories/crossing] [--days 30] [--limit 2] [--symbol DOOH]

Frames, drawn by iso/hl/render.mjs in the Sectors Hairline style (story format, 1080 x 1920):
  1. story_crossing        the holder's stake as steps climbing through a dashed 5% line, the stake now set big
  2. story_crossing_owners who owns the company now, ranked bars, the newcomer in the accent

Selection reuses insider_patterns.group_becoming_insider (buy filings with before < 5 <= after); the data
helpers come from insider_move. Nothing is posted or written to the database.
"""
import argparse
import json
import subprocess
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from .data import fetch_filings
from .insider_move import (ROOT, RENDER_JS, NBSP, _clean_name, _company, _day, _leg_days, _prices, _rp,
                           _same_holder, _short_company, _stake_history, _latest_stakes)
from .insider_patterns import drop_mixed_leg_filings, group_becoming_insider

LOGO_CDN = "https://storage.googleapis.com/sectorsapp-sea/logo/{}.webp"


def _logo(sym):
    p = ROOT / "logos" / f"{sym}.webp"
    return p.as_uri() if p.exists() else LOGO_CDN.format(sym)


def _crossing_day(df, ev):
    """The trade date of the crossing filing (its last leg), else the filing date."""
    row = df[df["id"] == ev.get("completing_filing_id")]
    if not row.empty:
        days = _leg_days(row.iloc[0].to_dict())
        if days:
            return days[-1]
    return ev["cross_date"]


def _roster(co, stakes, holder, now):
    """Named holders >= ~1% after the filing: the company report's list, overwritten by fresher filings.
    'Public' is not a holder; whatever is left over becomes 'everyone else'."""
    issuer = _short_company(co.get("company_name") or "")
    # the issuer's own filings (e.g. treasury shares) are not a shareholder row
    fresh = {k: v for k, v in (stakes or {}).items() if not (issuer and _same_holder(k, issuer))}
    fresh[holder] = now
    filed = {k: v for k, v in fresh.items() if v >= 1}
    rows = []
    for h in co.get("major_shareholders") or []:
        name = _clean_name(h.get("name"))
        if name.lower() in {"public", "masyarakat", "publik"}:
            continue
        match = next((k for k in fresh if _same_holder(k, name)), None)
        pct = fresh.pop(match) if match else float(h.get("share_percentage") or 0) * 100
        rows.append({"name": name, "pct": pct, "mover": bool(match) and _same_holder(match, holder)})
    rows += [{"name": k, "pct": v, "mover": _same_holder(k, holder)} for k, v in fresh.items() if v >= 5]
    rows = [r for r in rows if r["pct"] >= 1]
    stale = sum(r["pct"] for r in rows) > 100.5
    if stale:  # the report and the filings disagree: keep only what was filed in the last ~6 months
        rows = [{"name": k, "pct": v, "mover": _same_holder(k, holder)} for k, v in filed.items()]
    for r in rows:
        if r["mover"]:
            r["name"] = holder
    rows.sort(key=lambda r: -r["pct"])
    return rows, ("Holders who filed with IDX in the last 6 months" if stale
                  else "Other holders from the latest company report")


def _steps(df, ev, holder, day):
    """The holder's stake as steps in this stock, from their own filings in `df` (trade dates), to today.
    Starts ~2 months before their first filing at that filing's 'before'. Falls back to insider_move's helper."""
    sub = df[(df["symbol"] == ev["symbol"])].dropna(subset=["share_percentage_after"])
    rows = sorted((r for r in sub.to_dict("records") if _same_holder(r["holder_name"], holder)),
                  key=lambda r: (_leg_days(r)[-1:] or [str(r["timestamp"])[:10]])[0])
    if not rows:
        return _stake_history(ev["symbol"], holder, ev["stake_before"], ev["stake_after"], day)
    tday = lambda r: (_leg_days(r)[-1:] or [str(r["timestamp"])[:10]])[0]
    first = date.fromisoformat(tday(rows[0]))
    b0 = rows[0].get("share_percentage_before")
    pts = [{"date": (first - timedelta(days=60)).isoformat(), "pct": float(b0) if b0 == b0 and b0 is not None else 0.0}]
    pts += [{"date": tday(r), "pct": float(r["share_percentage_after"])} for r in rows]
    pts.append({"date": date.today().isoformat(), "pct": pts[-1]["pct"]})
    return pts


def build_story(ev, df):
    sym = ev["base_symbol"]
    holder = _clean_name(ev["holder_name"])
    day = _crossing_day(df, ev)
    co = _company(ev["symbol"])
    name = _short_company(co.get("company_name") or sym)
    stake = _steps(df, ev, holder, day)
    now = stake[-1]["pct"]
    up = now >= 5
    prices = _prices(ev["symbol"], day)
    last_close = prices[-1]["close"] if prices else None

    base = {
        "format": "story",
        "direction": "buy" if up else "sell",
        "kicker": "Crossed 5%",
        "company": sym,
        "source": f"IDX ownership filings · filed {_day(ev['cross_date'])} {ev['cross_date'][:4]}",
    }
    facts = [
        {"value": _rp(ev["total_value"]).replace(" ", NBSP), "label": "spent"},
        {"value": f"Rp{NBSP}{ev['avg_price']:,.0f}" if ev.get("avg_price") else "", "label": "avg. price"},
    ]
    if last_close:
        facts.append({"value": f"Rp{NBSP}{last_close:,.0f}", "label": "last close"})
    frames = [("story_crossing", {**base, "slide": {
        "holder": holder, "sym": sym, "logo": _logo(sym), "name": name,
        "before": round(ev["stake_before"], 2), "after": round(ev["stake_after"], 2), "now": round(now, 2),
        "day": _day(day), "stake": stake, "facts": [f for f in facts if f["value"]],
    }})]

    roster, note = _roster(co, _latest_stakes(df, ev["symbol"]), holder, now)
    if len(roster) >= 2 and sum(r["pct"] for r in roster) <= 100.5 and any(r["mover"] for r in roster):
        frames.append(("story_crossing_owners", {**base, "slide": {
            "sym": sym, "logo": _logo(sym), "name": name, "holder": holder,
            # the four biggest others plus the newcomer, always, in rank order
            "rows": [{"name": r["name"], "pct": round(r["pct"], 2), "mover": r["mover"]}
                     for r in roster if r["mover"] or r in [o for o in roster if not o["mover"]][:4]],
            "note": note,
        }}))
    n = len(frames)
    return [(k, {**d, "slide": {**d["slide"], "page": i + 1, "pages": n}}) for i, (k, d) in enumerate(frames)]


def render_story(ev, df, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = "".join(c if c.isalnum() else "_" for c in ev["holder_name"].lower()).strip("_")[:32]
    paths = []
    for i, (kind, data) in enumerate(build_story(ev, df), 1):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        out = out_dir / f"crossing_{ev['base_symbol']}_{slug}_{i}.png"
        run = subprocess.run(["node", str(RENDER_JS), kind, f.name, "--out", str(out)],
                             capture_output=True, text=True, encoding="utf-8")
        Path(f.name).unlink(missing_ok=True)
        if run.returncode != 0:
            raise RuntimeError(f"render failed for {kind}:\n{run.stderr.strip() or run.stdout.strip()}")
        paths.append(str(out))
    return paths


def main():
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="output_stories/crossing")
    p.add_argument("--days", type=int, default=30, help="Crossings filed in the last N days.")
    p.add_argument("--limit", type=int, default=2)
    p.add_argument("--symbol", help="Only this ticker (e.g. DOOH).")
    args = p.parse_args()
    df = drop_mixed_leg_filings(fetch_filings(since=(datetime.now() - timedelta(days=200)).isoformat()))
    cut = (date.today() - timedelta(days=args.days)).isoformat()
    evs = [e for e in group_becoming_insider(df) if e["cross_date"] >= cut]
    if args.symbol:
        evs = [e for e in evs if e["base_symbol"] == args.symbol.upper()]
    print(f"{len(evs)} crossings of 5% since {cut}")
    done = 0
    for ev in evs:
        if done >= args.limit:
            break
        steps = _steps(df, ev, _clean_name(ev["holder_name"]), ev["cross_date"])
        now = steps[-1]["pct"]
        if now < 5:  # crossed, then sold back under 5%: the story would be stale, skip it
            print(f"  skip {ev['base_symbol']} {ev['holder_name']}: back to {now:.2f}%")
            continue
        if steps[0]["pct"] >= 5:  # filings contradict each other (already above 5% before "crossing")
            print(f"  skip {ev['base_symbol']} {ev['holder_name']}: filings start at {steps[0]['pct']:.2f}%")
            continue
        done += 1
        print(f"  {ev['base_symbol']} {ev['holder_name']} {ev['stake_before']:.2f}% -> {ev['stake_after']:.2f}%")
        for path in render_story(ev, df, args.out):
            print("   ", path)


if __name__ == "__main__":
    main()
