"""The two picked combinations, one carousel each:

    python -m image_generator.combo_posts earnings --symbols PTBA,DSSA,UNTR
    python -m image_generator.combo_posts insider  --symbols BYAN,KETR,PPGL

  earnings = the coin cover (earnings_v_object) + the data-led slides (earnings_v_data: where the profit came
             from, is the margin normal, vs peers, what it did to the valuation)
  insider  = the magazine cover (insider_v_people: the holder's name and the 100-seat grid) + the data-led slides
             (insider_v_data: who is this holder, did they sell near the top, what the price says, who owns it after)
"""
import argparse
import json
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
RENDER_JS = ROOT / "iso" / "hl" / "render.mjs"


def _renumber(frames):
    n = len(frames)
    return [(k, {**d, "slide": {**d["slide"], "page": i + 1, "pages": n}}) for i, (k, d) in enumerate(frames)]


def earnings_frames(e, df):
    from . import earnings_v_data, earnings_v_object
    cover = earnings_v_object.build(e, df)[:1]
    rest = earnings_v_data.build(e, df)[1:]
    return _renumber(cover + rest) if cover and rest else []


def insider_frames(row, df):
    from . import insider_v_data, insider_v_people
    from .insider_move import _latest_stakes
    cover = insider_v_people.build(row, _latest_stakes(df, row["symbol"]))[:1]
    rest = insider_v_data.build(row, df)[1:]
    return _renumber(cover + rest) if cover and rest else []


def render(frames, out, theme=None):
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (kind, data) in enumerate(frames, 1):
        if theme:
            data = {**data, "theme": theme}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
        p = out / f"{i}.png"
        r = subprocess.run(["node", str(RENDER_JS), kind, f.name, "--out", str(p)], capture_output=True, text=True, encoding="utf-8")
        Path(f.name).unlink(missing_ok=True)
        if r.returncode != 0:
            raise RuntimeError(f"{kind}: {r.stderr.strip()[-400:]}")
        paths.append(p)
    return paths


def main():
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("kind", choices=["earnings", "insider"])
    p.add_argument("--symbols", required=True)
    p.add_argument("--out", default="output_feed")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--theme", choices=["light", "blue"], help="colour theme for every slide (default: warm dark)")
    a = p.parse_args()
    syms = [s.strip().upper() for s in a.symbols.split(",")]
    base = Path(a.out) / (f"{a.kind}_combo" + (f"_{a.theme}" if a.theme else ""))
    if a.kind == "earnings":
        from .data import fetch_company_report_earnings
        from .insider_patterns import select_earnings_spikes
        df = fetch_company_report_earnings(200)
        ev = select_earnings_spikes(df, direction="spike") + select_earnings_spikes(df, direction="drop")
        for s in syms:
            e = next((x for x in ev if x["base_symbol"] == s), None)
            if e:
                print(s, [p.name for p in render(earnings_frames(e, df), base / s, a.theme)])
    else:
        from .data import fetch_filings
        from .insider_move import select_moves
        from .insider_patterns import drop_mixed_leg_filings
        df = drop_mixed_leg_filings(fetch_filings(since=(datetime.now() - timedelta(days=a.days + 20)).isoformat()))
        moves = select_moves(df, days=a.days, min_pp=1.0)
        for s in syms:
            row = next((m for m in moves if str(m["symbol"]).split(".")[0] == s), None)
            if row:
                print(s, [p.name for p in render(insider_frames(row, df), base / s, a.theme)])


if __name__ == "__main__":
    main()
