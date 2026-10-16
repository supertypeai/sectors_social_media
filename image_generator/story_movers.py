"""Top movers story: the week's biggest gainers and losers among IDX's 100 largest companies, as IG story frames.

    python -m image_generator.story_movers --out output_stories/movers [--week 2026-10-05] [--top 5]

Frames (1080 x 1920, drawn by iso/hl/render.mjs in the Sectors Hairline story format):
  1. story_movers        diverging bars, true to scale: top gainers right (green), top losers left (terracotta),
                         IHSG's week as a dashed reference line, logos on every row
  2. story_movers_paths  the #1 gainer and #1 loser: their daily path through the week against IHSG, sector,
                         and trading value vs their normal (prior 20 sessions)

The week defaults to the last COMPLETED Mon-Fri week, so a mid-week run never renders an empty board. A stock's
weekly return is last close of the week vs the last close BEFORE the week (so Monday's move counts). Stocks that
traded on fewer than 3 days of the week are left out. If the week has fewer than 3 trading days, or fewer than
3 gainers/losers, nothing is rendered and the run exits cleanly.
"""
import argparse
import json
import subprocess
import tempfile
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from .data import fetch_supabase_table

ROOT = Path(__file__).resolve().parent.parent
RENDER_JS = ROOT / "iso" / "hl" / "render.mjs"
LOGO_URL = "https://storage.googleapis.com/sectorsapp-sea/logo/{}.webp"


def _logo(sym):
    """logos/<SYM>.webp, fetched once from the Sectors CDN when missing; None if there is none."""
    p = ROOT / "logos" / f"{sym}.webp"
    if not p.exists():
        try:
            with urllib.request.urlopen(LOGO_URL.format(sym), timeout=6) as r:
                if r.status == 200 and r.headers.get_content_type().startswith("image/"):
                    p.write_bytes(r.read())
        except Exception:
            return None
    return p.as_uri() if p.exists() else None


def last_completed_week(today=None):
    """Monday of the most recent Mon-Fri week whose Friday is before today."""
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    return monday - timedelta(days=7) if today.weekday() < 5 else monday


def _short(name, n=22):
    """A company name short enough for one line, without an ellipsis: drop legal suffixes, then trailing words."""
    s = str(name or "").replace("PT ", "").replace(" Tbk.", "").replace(" Tbk", "").replace(" (Persero)", "").strip()
    while len(s) > n and " " in s:
        s = s.rsplit(" ", 1)[0]
    return s if len(s) <= n else ""


def collect(monday, top_n=5, mcap_rank_max=100):
    """Everything both frames need, or None when the week is too thin to post."""
    friday = monday + timedelta(days=4)
    comp = fetch_supabase_table("idx_company_report", columns="symbol,company_name,market_cap_rank,sector,sub_sector,market_cap",
                                query_modifier=lambda q: q.lte("market_cap_rank", mcap_rank_max))
    if comp.empty:
        return None
    since = (monday - timedelta(days=40)).isoformat()  # room for the base close and a 20-session normal
    syms = comp["symbol"].tolist()
    parts = []
    for i in range(0, len(syms), 50):  # keep the IN list and the row count per request modest
        chunk = syms[i:i + 50]
        parts.append(fetch_supabase_table("idx_daily_data", columns="symbol,date,close,value",
                                          query_modifier=lambda q, c=chunk: q.in_("symbol", c).gte("date", since).lte("date", friday.isoformat())))
    daily = pd.concat(parts, ignore_index=True)
    if daily.empty:
        return None
    daily["date"] = pd.to_datetime(daily["date"]).dt.date
    daily["close"] = pd.to_numeric(daily["close"], errors="coerce")
    daily["value"] = pd.to_numeric(daily["value"], errors="coerce")
    daily = daily[daily["close"] > 0].sort_values(["symbol", "date"])

    week_days = sorted(d for d in daily["date"].unique() if monday <= d <= friday)
    if len(week_days) < 3:
        return None

    rows = []
    for sym, g in daily.groupby("symbol"):
        before, inweek = g[g["date"] < monday], g[g["date"] >= monday]
        if before.empty or len(inweek) < 3:
            continue
        base = float(before["close"].iloc[-1])
        norm = before["value"].tail(20).mean()
        path = [{"date": d.isoformat(), "close": float(c)} for d, c in zip(inweek["date"], inweek["close"])]
        rows.append({"symbol": sym, "sym": sym.replace(".JK", ""), "base": base, "last": float(inweek["close"].iloc[-1]),
                     "ret": float(inweek["close"].iloc[-1]) / base - 1, "path": path,
                     "value_x": float(inweek["value"].mean() / norm) if norm and norm > 0 else None})
    perf = pd.DataFrame(rows).merge(comp, on="symbol", how="left")
    up = perf[perf["ret"] > 0].sort_values("ret", ascending=False).head(top_n)
    dn = perf[perf["ret"] < 0].sort_values("ret").head(top_n)
    if len(up) < 3 or len(dn) < 3:
        return None

    ix = fetch_supabase_table("index_daily_data", columns="date,price",
                              query_modifier=lambda q: q.eq("index_code", "IHSG").gte("date", since).lte("date", friday.isoformat()))
    ix["date"] = pd.to_datetime(ix["date"]).dt.date
    ix["price"] = pd.to_numeric(ix["price"], errors="coerce")
    ix = ix.dropna().sort_values("date")
    ib, iw = ix[ix["date"] < monday], ix[ix["date"] >= monday]
    ihsg = None
    if not ib.empty and not iw.empty:
        ibase = float(ib["price"].iloc[-1])
        ihsg = {"ret": float(iw["price"].iloc[-1]) / ibase - 1, "base": ibase, "last": float(iw["price"].iloc[-1]),
                "path": [{"date": d.isoformat(), "close": float(p)} for d, p in zip(iw["date"], iw["price"])]}

    def row(r):
        sector = str(r["sub_sector"] or r["sector"] or "")
        if len(sector) > 24:  # "Pharmaceuticals & Health Care Research" → "Pharmaceuticals"
            sector = sector.split(" & ")[0] if len(sector.split(" & ")[0]) <= 24 else ""
        return {"sym": r["sym"], "logo": _logo(r["sym"]), "ret": round(r["ret"], 5), "name": _short(r["company_name"]),
                "sector": sector, "rank": int(r["market_cap_rank"]),
                "base": r["base"], "last": r["last"], "path": r["path"],
                "value_x": round(r["value_x"], 2) if r["value_x"] else None}

    return {"monday": monday, "friday": week_days[-1], "days": [d.isoformat() for d in week_days],
            "up": [row(r) for _, r in up.iterrows()], "down": [row(r) for _, r in dn.iterrows()],
            "ihsg": ihsg, "universe": int(len(perf)),
            "breadth": {"up": int((perf["ret"] > 0).sum()), "down": int((perf["ret"] < 0).sum())}}


def _span(a, b):
    return f"{a.day} – {b.day} {b:%b}" if a.month == b.month else f"{a.day} {a:%b} – {b.day} {b:%b}"


def build(monday, top_n=5):
    c = collect(monday, top_n)
    if not c:
        return []
    base = {"format": "story", "direction": "buy", "kicker": "Top movers", "company": _span(c["monday"], c["friday"]),
            "source": "IDX daily closes · top 100 by market cap · Sectors"}
    frames = [("story_movers", {**base, "slide": {"title": "The week's biggest moves", "up": c["up"], "down": c["down"],
                                                  "ihsg": c["ihsg"], "breadth": c["breadth"], "universe": c["universe"]}})]
    frames.append(("story_movers_paths", {**base, "slide": {"title": "How the week unfolded", "days": c["days"],
                                                            "up": c["up"][0], "down": c["down"][0], "ihsg": c["ihsg"]}}))
    return frames


def render(monday, out_dir, top_n=5):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (kind, data) in enumerate(build(monday, top_n), 1):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
        out = out_dir / f"story_movers_{monday:%Y%m%d}_{i}.png"
        run = subprocess.run(["node", str(RENDER_JS), kind, f.name, "--out", str(out)], capture_output=True, text=True, encoding="utf-8")
        Path(f.name).unlink(missing_ok=True)
        if run.returncode != 0:
            raise RuntimeError(f"render failed for {kind}:\n{run.stderr.strip() or run.stdout.strip()}")
        paths.append(str(out))
    return paths


def main():
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="output_stories/movers")
    p.add_argument("--week", help="any date in the Mon-Fri week to show (default: last completed week)")
    p.add_argument("--top", type=int, default=5)
    args = p.parse_args()
    if args.week:
        d = date.fromisoformat(args.week)
        monday = d - timedelta(days=d.weekday())
    else:
        monday = last_completed_week()
    paths = render(monday, args.out, args.top)
    if not paths:
        print(f"skip: not enough data for the week of {monday}")
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
