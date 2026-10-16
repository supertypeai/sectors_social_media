"""Earnings cover, four illustration approaches (exploration; slides 2-5 unchanged).

    python -m image_generator.earnings_cover_explore [--symbol PTBA DSSA UNTR]

Approaches (iso/hl/slides/feed/earnings_cover_explore):
  ec_type     typography is the illustration: last year's and this year's profit set at area-true sizes
  ec_stripes  data-pattern art: every quarter one vertical stripe, its brightness = profit ("warming stripes")
  ec_brand    brand-led: the company logo as a big halftone, its dots scaled by the change
  ec_scene    one hairline scene of the industry (mine cart): the load that stayed vs the load that moved
"""
import argparse
import base64
import io
import json
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

from .data import fetch_company_report_earnings
from .earnings_v_object import build
from .insider_patterns import select_earnings_spikes

ROOT = Path(__file__).resolve().parent.parent
RENDER_JS = ROOT / "iso" / "hl" / "render.mjs"
APPROACHES = ["ec_type", "ec_stripes", "ec_brand", "ec_scene"]
LABELS = {"ec_type": "1 Typography", "ec_stripes": "2 Data stripes", "ec_brand": "3 Brand halftone", "ec_scene": "4 Hairline scene"}


def halftone(logo_uri, n=34):
    """The logo sampled on an n x n grid: ink amount 0..1 per cell (dark or coloured pixels = ink)."""
    if not logo_uri:
        return None
    from PIL import Image
    if logo_uri.startswith("data:"):
        im = Image.open(io.BytesIO(base64.b64decode(logo_uri.split(",", 1)[1])))
    else:
        p = unquote(urlparse(logo_uri).path).lstrip("/")
        im = Image.open(p if Path(p).exists() else "/" + p)
    im = im.convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    g = bg.convert("L")
    w, h = g.size
    s = max(w, h)
    sq = Image.new("L", (s, s), 255)
    sq.paste(g, ((s - w) // 2, (s - h) // 2))
    sm = sq.resize((n, n), Image.LANCZOS)
    return [[round(1 - sm.getpixel((x, y)) / 255, 2) for x in range(n)] for y in range(n)]


def cover_data(e, df):
    frames = build(e, df)
    if not frames:
        return None
    _, d = frames[0]
    s = d["slide"]
    qs = [{"label": q["label"], "v": float(q["earnings"] or 0)} for q in e["quarters"]]
    s["quarters"] = qs
    s["sector"] = e.get("sub_sector") or e.get("sector") or ""
    s["ink"] = halftone(s["logo"])
    return d


def render(kind, data, out):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, default=str)
    r = subprocess.run(["node", str(RENDER_JS), kind, f.name, "--out", str(out)], capture_output=True, text=True, encoding="utf-8")
    Path(f.name).unlink(missing_ok=True)
    if r.returncode != 0:
        raise RuntimeError(f"render failed for {kind}:\n{r.stderr.strip()}")


def sheet(out_dir, syms):
    from PIL import Image, ImageDraw, ImageFont
    tw, th, pad, lw, top = 360, 450, 12, 200, 36
    img = Image.new("RGB", (lw + len(syms) * (tw + pad) + pad, top + len(APPROACHES) * (th + pad) + pad), (10, 9, 8))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    for x, s in enumerate(syms):
        d.text((lw + x * (tw + pad) + 8, 8), s, fill=(239, 236, 231), font=font)
    for y, a in enumerate(APPROACHES):
        d.text((12, top + y * (th + pad) + th // 2), LABELS[a], fill=(239, 236, 231), font=font)
        for x, s in enumerate(syms):
            p = Path(out_dir) / f"{a}_{s}.png"
            if p.exists():
                img.paste(Image.open(p).convert("RGB").resize((tw, th), Image.LANCZOS), (lw + x * (tw + pad), top + y * (th + pad)))
    img.save(Path(out_dir) / "_sheet.png")


def main():
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="output_feed/earnings_cover_explore")
    p.add_argument("--symbol", nargs="*", default=["PTBA", "DSSA", "UNTR"])
    p.add_argument("--only", nargs="*", default=APPROACHES)
    a = p.parse_args()
    df = fetch_company_report_earnings(200)
    ev = select_earnings_spikes(df, direction="spike") + select_earnings_spikes(df, direction="drop")
    want = [s.upper() for s in a.symbol]
    by = {e["base_symbol"]: e for e in ev if e["base_symbol"] in want}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    done = []
    for sym in want:
        e = by.get(sym)
        d = e and cover_data(e, df)
        if not d:
            print(sym, "not selected / no data")
            continue
        for k in a.only:
            render(k, d, out / f"{k}_{sym}.png")
        print(sym, d["slide"]["hero"], "ok")
        done.append(sym)
    sheet(out, done)


if __name__ == "__main__":
    main()
