"""Insider cover exploration: four illustration techniques for slide 1 of the insider carousel (slides 2-5 unchanged).

    python -m image_generator.insider_cover_explore [--days 30] [--symbols BYAN KETR PPGL] [--cached]

Approaches (iso/hl/slides/feed/insider_cover_explore/):
  ic_type    editorial typography poster: the stake as a cut, struck-through number composition
  ic_deed    the filing as an artefact: a stylised deed with fields, a stamp and a signature line
  ic_flow    a proportional flow: the stake as a ribbon from the seller to the buyer (or to the market)
  ic_dither  image treatment: the holder's monogram (or logo) as a two-tone ordered dither, poster style

Writes output_feed/insider_cover_explore/<approach>_<SYM>.png and _sheet.png. --cached reuses the cover data saved
on the last run (output_feed/insider_cover_explore/_data/<SYM>.json), so the slides can be iterated without the DB.
"""
import argparse
import base64
import io
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from .insider_move import RENDER_JS, ROOT
from .news_flash import dither

APPROACHES = ["ic_type", "ic_deed", "ic_flow", "ic_dither"]
OUT = ROOT / "output_feed" / "insider_cover_explore"


def _monogram(initials, logo=None):
    """A big monogram (or the holder's logo when it is a listed company) dithered into a two-tone poster image."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    size = 900
    im = Image.new("RGB", (size, size), (0, 0, 0))
    if logo:
        if logo.startswith("data:"):
            src = io.BytesIO(base64.b64decode(logo.split(",", 1)[1]))
        else:
            from urllib.parse import unquote, urlparse
            src = unquote(urlparse(logo).path).lstrip("/") if logo.startswith("file:") else logo
        lg = Image.open(src).convert("RGBA")
        lg = lg.resize((680, round(680 * lg.height / lg.width)))
        # the logo's marks as light on dark: every opaque, non-white pixel becomes ink, brighter where darker
        from PIL import ImageOps
        lum = ImageOps.invert(ImageOps.grayscale(lg.convert("RGB")))
        alpha = lg.split()[3]
        ink = Image.composite(lum.point(lambda v: 0 if v < 40 else min(255, 90 + v)), Image.new("L", lg.size, 0), alpha)
        im = Image.new("L", (size, size), 0)
        im.paste(ink, ((size - lg.width) // 2, (size - lg.height) // 2))
        im = im.convert("RGB").filter(ImageFilter.GaussianBlur(3))
    else:
        d = ImageDraw.Draw(im)
        try:
            font = ImageFont.truetype("arialbd.ttf", 620 if len(initials) <= 2 else 470)
        except OSError:
            font = ImageFont.load_default()
        bb = d.textbbox((0, 0), initials, font=font)
        d.text(((size - bb[2] - bb[0]) / 2, (size - bb[3] - bb[1]) / 2 - bb[1] / 2), initials, fill=(255, 255, 255), font=font)
        # a soft light falling across the letters gives the dither its tonal range (midtones get the accent)
        grad = Image.linear_gradient("L").rotate(35, expand=False).resize((size, size))
        im = Image.composite(im, Image.new("RGB", (size, size), (0, 0, 0)), grad.point(lambda v: 15 + v * 0.9))
        im = im.filter(ImageFilter.GaussianBlur(5))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _cover_data(symbols, days):
    from .data import fetch_filings
    from .insider_move import _latest_stakes, select_moves
    from .insider_patterns import drop_mixed_leg_filings
    from .insider_v_people import build
    df = drop_mixed_leg_filings(fetch_filings(since=(datetime.now() - timedelta(days=days + 5)).isoformat()))
    out, seen = {}, set()
    for m in select_moves(df, days=days):
        s = str(m["symbol"]).split(".")[0]
        if s in seen or s not in symbols:
            continue
        seen.add(s)
        kind, data = build(m, _latest_stakes(df, m["symbol"]))[0]
        out[s] = data
    return out


def render(approach, data, out):
    tmp = OUT / "_data" / f"_{approach}_{out.stem}.json"
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    run = subprocess.run(["node", str(RENDER_JS), approach, str(tmp), "--out", str(out)], capture_output=True, text=True, encoding="utf-8")
    if run.returncode != 0:
        raise RuntimeError(f"render failed for {approach} {out.stem}:\n{run.stderr.strip() or run.stdout.strip()}")
    return out


def sheet(rows, cols, out):
    from PIL import Image, ImageDraw, ImageFont
    tw, th, gap, lw, top = 324, 405, 14, 150, 40
    img = Image.new("RGB", (lw + len(cols) * (tw + gap) + gap, top + len(rows) * (th + gap) + gap), (20, 18, 16))
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("arialbd.ttf", 20)
    except OSError:
        f = ImageFont.load_default()
    for c, s in enumerate(cols):
        d.text((lw + c * (tw + gap) + tw / 2 - 25, 10), s, fill=(239, 236, 231), font=f)
    for r, a in enumerate(rows):
        d.text((14, top + r * (th + gap) + th / 2 - 10), a.replace("ic_", ""), fill=(239, 236, 231), font=f)
        for c, s in enumerate(cols):
            p = OUT / f"{a.replace('ic_', '')}_{s}.png"
            if p.exists():
                img.paste(Image.open(p).convert("RGB").resize((tw, th), Image.LANCZOS), (lw + c * (tw + gap), top + r * (th + gap)))
    img.save(out)


def main():
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--symbols", nargs="*", default=["BYAN", "KETR", "PPGL"])
    p.add_argument("--approaches", nargs="*", default=APPROACHES)
    p.add_argument("--cached", action="store_true")
    args = p.parse_args()
    (OUT / "_data").mkdir(parents=True, exist_ok=True)
    if args.cached:
        covers = {s: json.loads((OUT / "_data" / f"{s}.json").read_text(encoding="utf-8")) for s in args.symbols
                  if (OUT / "_data" / f"{s}.json").exists()}
    else:
        covers = _cover_data(args.symbols, args.days)
        for s, d in covers.items():
            S = d["slide"]
            S["monogram"] = _monogram(S["holder"]["initials"], S["holder"].get("logo"))
            S["dither"] = dither(S["monogram"], cell=6, tint=(192, 113, 89) if S["sell"] else (129, 167, 137))
            S["otherDither"] = (dither(_monogram(S["other"]["initials"], S["other"].get("logo")), cell=6, tint=(138, 130, 123))
                                if S.get("other") else None)
            del S["monogram"]
            (OUT / "_data" / f"{s}.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    syms = [s for s in args.symbols if s in covers]
    for a in args.approaches:
        for s in syms:
            print(render(a, covers[s], OUT / f"{a.replace('ic_', '')}_{s}.png"))
    sheet(APPROACHES, syms, OUT / "_sheet.png")
    print(OUT / "_sheet.png")


if __name__ == "__main__":
    main()
