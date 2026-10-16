"""Volume Spike story: the day's loudest volume spike among the top-100 IDX names, as an Instagram story.

    python -m image_generator.story_volume [--date 2026-10-09] [--find-recent] [--out output_stories/volume]

Frames (1080 x 1920, drawn by iso/hl/render.mjs in the Sectors Hairline style):
  1. story_volume       the lead spike: one tall bar over a month of calm bars and a median line, the volume,
                        the multiple of normal, and three facts (price that day, how rare, foreign share)
  2. story_volume_rank  only when 2+ stocks spiked: every spike ranked by multiple of normal

Detection is the same rule as data.fetch_volume_spike_data: top-100 market cap, the day's volume above 3x the
median of BOTH the prior 30 calendar days and the prior 14 calendar days. With no spike the run prints
"no spikes" and exits 0 without rendering. --find-recent walks back through trading days to the latest one
that had a spike (for design work and backfills).
"""
import argparse
import json
import subprocess
import tempfile
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .data import _supabase_client, fetch_supabase_table

ROOT = Path(__file__).resolve().parent.parent
RENDER_JS = ROOT / "iso" / "hl" / "render.mjs"
LOGO_URL = "https://storage.googleapis.com/sectorsapp-sea/logo/{}.webp"
RATIO = 3.0
# A spike only counts when real money changed hands: on a stock that barely trades, one order of a few hundred
# million rupiah makes a 20x "spike" that is noise (SRAJ on 16 Oct 2026: Rp 160 M, 13.9K shares vs 600 normal).
MIN_VALUE = 5e9  # Rp traded that day
HISTORY_DAYS = 420  # a year+ of trading for "highest since", plus the 30-day baseline


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


def _short(v):
    """88_210_000 -> '88.2M'; 1_240_000_000 -> '1.24B'."""
    v = float(v)
    for div, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(v) >= div:
            x = v / div
            s = f"{x:.2f}" if x < 10 else f"{x:.1f}" if x < 100 else f"{x:.0f}"
            return s.rstrip("0").rstrip(".") + unit
    return f"{v:,.0f}"


def _mult(r):
    return f"{r:.1f}" if r < 10 else f"{r:,.0f}"


# ---------------------------------------------------------------- data
def _universe():
    df = fetch_supabase_table("idx_company_report", columns="symbol,company_name,sector,market_cap_rank",
                              query_modifier=lambda q: q.lte("market_cap_rank", 100))
    return df


def _daily(symbols, since):
    """idx_daily_data for the symbols since `since`, paged (the client caps a response at 1000 rows)."""
    cli, frames = _supabase_client(), []
    cols = "symbol,date,open,close,volume,value,foreign_buy_volume,foreign_sell_volume"
    for i in range(0, len(symbols), 8):
        chunk, start = symbols[i:i + 8], 0
        while True:
            rows = (cli.table("idx_daily_data").select(cols).in_("symbol", chunk).gte("date", since)
                    .order("date").order("symbol").range(start, start + 999).execute().data)
            frames.append(pd.DataFrame(rows))
            if len(rows) < 1000:
                break
            start += 1000
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    for c in ("open", "close", "volume", "value", "foreign_buy_volume", "foreign_sell_volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["close", "volume"]).sort_values(["symbol", "date"]).reset_index(drop=True)


def spikes_on(df, day):
    """The spikes on `day` (a Timestamp), loudest first: same rule as fetch_volume_spike_data."""
    today = df[df["date"] == day]
    prior = df[(df["date"] < day) & (df["date"] >= day - pd.Timedelta(days=30))]
    m30 = prior.groupby("symbol")["volume"].median()
    m14 = prior[prior["date"] >= day - pd.Timedelta(days=14)].groupby("symbol")["volume"].median()
    t = today.set_index("symbol")
    t = t.assign(med30=m30, med14=m14).dropna(subset=["med30", "med14"])
    t = t[(t["med30"] > 0) & (t["med14"] > 0)]
    t = t.assign(ratio=t["volume"] / t["med30"], ratio14=t["volume"] / t["med14"])
    t = t[(t["ratio"] > RATIO) & (t["ratio14"] > RATIO)]
    # value traded that day: the table's own column, else close x volume
    value = t["value"].where(t["value"] > 0, t["close"] * t["volume"])
    return t[value >= MIN_VALUE].sort_values("ratio", ascending=False)


def _facts(df, sym, day, row):
    s = df[df["symbol"] == sym].set_index("date").sort_index()
    before = s[s.index < day]
    prev = before["close"].iloc[-1] if len(before) else None
    chg = (row["close"] - prev) / prev * 100 if prev else None
    # how rare: the last earlier day with at least this much volume
    louder = before[before["volume"] >= row["volume"]]
    if len(louder):
        last = louder.index[-1]
        n = int((before.index > last).sum()) + 1
        rare = {"head": f"{n} days", "sub": f"most since {last.day} {last:%b %Y}"}
    else:
        span = (day - before.index[0]).days if len(before) else 0
        rare = {"head": "1 yr+" if span >= 360 else f"{len(before)} days", "sub": "most in our history" if span < 360 else "most in over a year"}
    fb, fs, v = row.get("foreign_buy_volume") or 0, row.get("foreign_sell_volume") or 0, row["volume"]
    fshare = (fb + fs) / (2 * v) * 100 if v else 0
    net = fb - fs
    bars = s[(s.index <= day)].tail(31)
    return {
        "price": row["close"], "chg": chg, "value": row.get("value"),
        "rare": rare, "foreign": {"share": fshare, "net": net},
        # each day's volume and close: the story draws the price line over the volume bars
        "bars": [{"d": f"{d:%Y-%m-%d}", "v": float(v), "c": float(c)} for d, v, c in zip(bars.index, bars["volume"], bars["close"])],
    }


def build(day=None, find_recent=False, lookback=30):
    uni = _universe()
    if uni.empty:
        return None, None
    names = dict(zip(uni["symbol"], uni["company_name"]))
    sectors = dict(zip(uni["symbol"], uni["sector"]))
    end = pd.Timestamp(day) if day else pd.Timestamp(date.today())
    df = _daily(uni["symbol"].tolist(), (end - pd.Timedelta(days=HISTORY_DAYS + lookback)).strftime("%Y-%m-%d"))
    days = sorted(d for d in df["date"].unique() if d <= end)
    if not days:
        return None, None
    tries = days[::-1][: (lookback if find_recent else 1)]
    if day and not find_recent and pd.Timestamp(day) not in days:
        return pd.Timestamp(day), None  # not a trading day
    for d in tries:
        sp = spikes_on(df, d)
        if len(sp):
            break
    else:
        return tries[0], None
    rows = []
    for sym, r in sp.iterrows():
        f = _facts(df, sym, d, r)
        code = sym.split(".")[0]
        rows.append({"sym": code, "name": names.get(sym, code), "sector": sectors.get(sym) or "", "logo": _logo(code),
                     "volume": float(r["volume"]), "median": float(r["med30"]), "ratio": float(r["ratio"]), **f})
    return d, rows


# ---------------------------------------------------------------- slides
def _clean_name(n):
    for t in (" Tbk.", " Tbk", "PT "):
        n = n.replace(t, "")
    return n.strip()


def _pct(c):
    if c is None:
        return ""
    return "0.0%" if round(c, 1) == 0 else f"{c:+.1f}%".replace("-", "−")


def _rare_days(r):
    h = r["rare"]["head"]
    return 9999 if not h.endswith(" days") else int(h.split()[0])


def slides(day, rows):
    # The lead must be the tallest bar of its own month, or the chart contradicts the headline (a stock on day
    # two of a run sits under day one). Among those, the loudest multiple; else simply the loudest.
    towering = [r for r in rows if _rare_days(r) >= 20]
    lead = towering[0] if towering else rows[0]
    dir_ = lambda c: "buy" if (c or 0) >= 0 else "sell"
    rare = _rare_days(lead) >= 5
    base = {"format": "story", "kicker": "Volume spike", "company": f"{day.day} {day:%b %Y}",
            "source": "Source: IDX daily data, top-100 market cap"}
    out = [("story_volume", {**base, "dir": dir_(lead["chg"]), "lead": {
        **lead, "name": _clean_name(lead["name"]), "volumeTxt": _short(lead["volume"]), "medianTxt": _short(lead["median"]),
        "ratioTxt": _mult(lead["ratio"]), "chgTxt": _pct(lead["chg"]) or "n/a",
        # a spike right after a louder one is not rare: show the money traded instead of "1 days"
        "rareHead": lead["rare"]["head"] if rare else f"Rp {_short(lead['value'])}",
        "rareSub": lead["rare"]["sub"].replace("most", "busiest") if rare else "traded that day",
        "foreignTxt": f"{lead['foreign']['share']:.0f}%",
        "foreignSub": ("foreign, net buy" if lead["foreign"]["net"] > 0 else "foreign, net sell" if lead["foreign"]["net"] < 0 else "foreign, flat"),
    }, "count": len(rows)})]
    if len(rows) >= 2:
        ranked = [{"sym": r["sym"], "logo": r["logo"], "ratio": r["ratio"], "ratioTxt": _mult(r["ratio"]),
                   "volumeTxt": _short(r["volume"]), "chgTxt": _pct(r["chg"]),
                   "up": (r["chg"] or 0) >= 0} for r in rows[:6]]
        out.append(("story_volume_rank", {**base, "dir": dir_(rows[0]["chg"]), "rows": ranked, "count": len(rows)}))
    n = len(out)
    return [(k, {**d, "slide": {"page": i + 1, "pages": n}}) for i, (k, d) in enumerate(out)]


def render(day=None, find_recent=False, out_dir="output_stories/volume"):
    d, rows = build(day, find_recent)
    if not rows:
        print(f"no spikes ({d:%Y-%m-%d})" if d is not None else "no data")
        return []
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (kind, data) in enumerate(slides(d, rows), 1):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
        out = out_dir / f"volume_{d:%Y%m%d}_{i}.png"
        run = subprocess.run(["node", str(RENDER_JS), kind, f.name, "--out", str(out)], capture_output=True, text=True, encoding="utf-8")
        Path(f.name).unlink(missing_ok=True)
        if run.returncode != 0:
            raise RuntimeError(f"render failed for {kind}:\n{run.stderr.strip() or run.stdout.strip()}")
        paths.append(str(out))
    return paths


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--date", help="trading day YYYY-MM-DD (default: latest)")
    p.add_argument("--find-recent", action="store_true", help="walk back to the latest day that had a spike")
    p.add_argument("--out", default="output_stories/volume")
    a = p.parse_args()
    for path in render(a.date, a.find_recent, a.out):
        print(path)


if __name__ == "__main__":
    main()
