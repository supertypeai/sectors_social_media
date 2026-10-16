"""Top broker story: who moved the most money last week, and the one broker whose flow stood out. Two IG story frames.

    python -m image_generator.story_broker [--out output_stories/broker] [--week-start 2026-10-05]

Frames, drawn by iso/hl/render.mjs in the Sectors Hairline style (9:16, DATA.format = "story"):
  1. story_broker_rank    the eight busiest brokers of the week, bars true to scale (buy + sell value),
                          share of all broker trades, change vs the week before
  2. story_broker_spot    the broker with the largest net position (bought or sold): the week's net, its
                          net day by day (diverging bars), and the three stocks behind it

Source: idx_broker_summary_daily (+ idx_broker_registry for names). The table answers at most 8,000 rows per
request and a trading day has ~20,000 rows, so it is read one day at a time, ordered, in pages of 5,000.
(data._fetch_broker_summary_range asks for 20,000 and stops on the first short page: it reads part of one day.)
"""
import argparse
import json
import re
import subprocess
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from .data import fetch_supabase_table
from .weekly_calendar import _logo

ROOT = Path(__file__).resolve().parent.parent
RENDER_JS = ROOT / "iso" / "hl" / "render.mjs"
COLS = "symbol,date,broker_code,bval,sval,nval"
PAGE = 5000


def _day_rows(d):
    """Every broker × stock row of one trading day, paged under the server's 8,000-row cap."""
    out, off = [], 0
    while True:
        for attempt in range(4):  # the connection resets now and then under load; a page is safe to re-ask
            try:
                p = fetch_supabase_table("idx_broker_summary_daily", columns=COLS,
                                         query_modifier=lambda q, o=off: q.eq("date", d).order("symbol").order("broker_code").range(o, o + PAGE - 1))
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 * (attempt + 1))
        out.append(p)
        if len(p) < PAGE:
            break
        off += PAGE
    return pd.concat(out, ignore_index=True)


def _week_rows(start):
    days = [(start + timedelta(days=i)).isoformat() for i in range(5)]
    df = pd.concat([_day_rows(d) for d in days], ignore_index=True)
    df = df[df["broker_code"] != "--"].copy()
    df["symbol"] = df["symbol"].str.split(".").str[0]
    df["gross"] = df["bval"] + df["sval"]
    return df


def last_full_week(today):
    """Monday of the last Mon–Fri wholly before today."""
    mon = today - timedelta(days=today.weekday())
    return mon - timedelta(days=7) if today.weekday() < 5 else mon


_DROP = r"\b(PT|Tbk|Sekuritas|Securities|Indonesia|Digital|Investindo|Investama|Capital)\b"


def short_name(name, code):
    if not isinstance(name, str) or not name.strip():
        return code
    s = re.sub(r"\s+", " ", re.sub(_DROP, "", name)).strip(" .,")
    return s or name


def fmt_rp(v, sign=False):
    a = abs(v)
    s = f"{a / 1e12:.1f} T" if a >= 1e12 else f"{a / 1e9:.0f} B" if a >= 1e9 else f"{a / 1e6:.0f} M"
    pre = ("+" if v > 0 else "−" if v < 0 else "") if sign else ("−" if v < 0 else "")
    return f"{pre}Rp {s}"


def build(start):
    end = start + timedelta(days=4)
    df, prior = _week_rows(start), _week_rows(start - timedelta(days=7))
    if df.empty:
        raise SystemExit(f"no broker data for week of {start}")
    reg = fetch_supabase_table("idx_broker_registry", columns="broker_code, broker_name, is_foreign, cohort").set_index("broker_code")

    def info(code):
        r = reg.loc[code] if code in reg.index else None
        return {"code": code, "name": short_name(r["broker_name"] if r is not None else None, code),
                "foreign": bool(r["is_foreign"]) if r is not None and pd.notna(r["is_foreign"]) else False,
                "cohort": (r["cohort"] if r is not None and r["cohort"] not in (None, "Unknown") else "")}

    tot = df.groupby("broker_code").agg(gross=("gross", "sum"), net=("nval", "sum")).sort_values("gross", ascending=False)
    ptot = prior.groupby("broker_code")["gross"].sum()
    all_gross = tot["gross"].sum()
    market = df["bval"].sum()  # every trade has one buyer: summed buy value = what the market traded
    top = tot.head(8)
    rows = []
    for code, r in top.iterrows():
        p = ptot.get(code)
        rows.append({**info(code), "gross": float(r["gross"]), "gross_s": fmt_rp(r["gross"]),
                     "share": float(r["gross"] / all_gross * 100), "net": float(r["net"]),
                     "wow": (float((r["gross"] / p - 1) * 100) if p else None)})
    lead = rows[0]
    week = f"{start.day}–{end.day} {end:%b %Y}" if start.month == end.month else f"{start.day} {start:%b} – {end.day} {end:%b %Y}"
    base = {"format": "story", "company": week, "source": "IDX broker summary · Sectors"}
    f1 = {**base, "kicker": "Top brokers", "direction": "info",
          "title": f"{lead['name']} moved the most money last week",
          "market": fmt_rp(market), "top8": float(top["gross"].sum() / all_gross * 100), "rows": rows}

    # the broker with the largest net position either way
    code = tot["net"].abs().idxmax()
    net = float(tot.loc[code, "net"])
    side = "buy" if net > 0 else "sell"
    sub = df[df["broker_code"] == code]
    daily = sub.groupby("date")["nval"].sum()
    days = [(start + timedelta(days=i)) for i in range(5)]
    by_stock = sub.groupby("symbol")["nval"].sum()
    picks = (by_stock.nlargest(3) if net > 0 else by_stock.nsmallest(3))
    picks = picks[picks * net > 0]
    b = info(code)
    f2 = {**base, "kicker": "Biggest net " + ("buyer" if net > 0 else "seller"), "direction": side,
          "broker": b, "net": net, "net_s": fmt_rp(net, sign=True), "gross_s": fmt_rp(tot.loc[code, "gross"]),
          "rank": int(list(tot.index).index(code) + 1),
          "daily": [{"dow": f"{d:%a}", "v": float(daily.get(d.isoformat(), 0.0)), "s": fmt_rp(daily.get(d.isoformat(), 0.0), sign=True)} for d in days],
          "stocks": [{"sym": s, "logo": _logo(s), "v": float(v), "s": fmt_rp(v, sign=True),
                      "pct": float(v / net * 100)} for s, v in picks.items()],
          "question": "Following " + b["code"] + " next week?"}
    return [("story_broker_rank", f1), ("story_broker_spot", f2)]


def render(start, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (kind, data) in enumerate(build(start), 1):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
        out = out_dir / f"story_broker_{start:%Y%m%d}_{i}.png"
        run = subprocess.run(["node", str(RENDER_JS), kind, f.name, "--out", str(out)], capture_output=True, text=True, encoding="utf-8")
        Path(f.name).unlink(missing_ok=True)
        if run.returncode != 0:
            raise RuntimeError(f"render failed for {kind}:\n{run.stderr.strip() or run.stdout.strip()}")
        paths.append(str(out))
    return paths


def main():
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="output_stories/broker")
    p.add_argument("--week-start", default=None, help="Monday of the week (default: last full week)")
    a = p.parse_args()
    start = date.fromisoformat(a.week_start) if a.week_start else last_full_week(date.today())
    for path in render(start, a.out):
        print(path)


if __name__ == "__main__":
    main()
