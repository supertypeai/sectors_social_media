"""News Flash: the day's top IDX stories as one carousel, from the Sectors news feed (idx_news).

    python -m image_generator.news_flash --out output_news_flash [--hours 36] [--stories 4]

Slides, drawn by iso/hl/render.mjs in the Sectors Hairline style:
  1. news_cover  the lead story's ticker, logo and headline, and the other tickers in the flash
  2. news_story  one per story: headline, the key figure large, up to three more figures, the lead
  3. news_close  today's stories as an index, a question, the CTA

Stories: the highest-scored news with a ticker, one per company, preferring stories that carry figures
(structured_body metrics blocks). Every figure is copied from the article; nothing is computed here.
"""
import argparse
import base64
import json
import urllib.request
import re
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from .data import fetch_supabase_table

ROOT = Path(__file__).resolve().parent.parent
RENDER_JS = ROOT / "iso" / "hl" / "render.mjs"
DIRECTION = {"Bullish": "buy", "Bearish": "sell"}


BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def dither(data_uri, style="bayer", cell=3, ink=(239, 236, 231), ground=(20, 18, 16), tint=(208, 50, 111)):
    """A photo as a two-tone dither (ascii-magic style): grey levels become a 4×4 ordered (Bayer) dot pattern of
    `cell`-px dots, or ASCII glyphs with style="ascii". Highlights in ink, shadows in ground, a touch of the accent
    in the midtones. Returns a PNG data URI."""
    import io
    from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps
    raw = base64.b64decode(data_uri.split(",", 1)[1])
    im = ImageOps.grayscale(Image.open(io.BytesIO(raw)).convert("RGB"))
    im = ImageOps.autocontrast(im, cutoff=2)
    im = ImageEnhance.Brightness(ImageEnhance.Contrast(im).enhance(1.5)).enhance(1.2)
    W0 = 1080
    im = im.resize((W0, round(im.height * W0 / im.width)))
    if style == "ascii":
        glyphs, step = " .:-=+*#%@", 9
        small = im.resize((W0 // step, im.height // step))
        out = Image.new("RGB", (small.width * step, small.height * step), ground)
        d = ImageDraw.Draw(out)
        try:
            font = ImageFont.truetype("consola.ttf", step + 2)
        except OSError:
            font = ImageFont.load_default()
        for y in range(small.height):
            for x in range(small.width):
                v = small.getpixel((x, y)) / 255
                g = glyphs[min(len(glyphs) - 1, int(v * len(glyphs)))]
                col = ink if v > 0.55 else tint
                d.text((x * step, y * step - 1), g, fill=col, font=font)
    else:
        small = im.resize((W0 // cell, im.height // cell))
        out = Image.new("RGB", (small.width * cell, small.height * cell), ground)
        d = ImageDraw.Draw(out)
        for y in range(small.height):
            for x in range(small.width):
                v = small.getpixel((x, y)) / 255
                t = (BAYER[y % 4][x % 4] + 0.5) / 16
                if v > t:
                    col = ink if v > 0.42 else tint
                    d.rectangle((x * cell, y * cell, x * cell + cell - 1, y * cell + cell - 1), fill=col)
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _photo(url):
    """The article's thumbnail as a data URI (so the render never waits on the network); None if it fails."""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            kind = r.headers.get_content_type()
            if not kind.startswith("image/"):
                return None
            return f"data:{kind};base64,{base64.b64encode(r.read()).decode()}"
    except Exception as e:  # a missing photo only means a slide without one
        print(f"    no photo ({e.__class__.__name__}): {url[:80]}")
        return None


def _logo(sym):
    """logos/<SYM>.webp, fetched once from the Sectors CDN when missing (same source as weekly_calendar)."""
    from .weekly_calendar import _logo as fetch_logo
    return fetch_logo(sym)


_SECTORS = {}


def _sector(sym):
    """The company's IDX sector (idx_company_report), used to draw a faint sector icon when a story has no photo."""
    if sym not in _SECTORS:
        try:
            rows = fetch_supabase_table("idx_company_report", columns="symbol, sector", symbol_column="symbol", symbol_value=f"{sym}.JK")
            _SECTORS[sym] = (rows[0].get("sector") if isinstance(rows, list) and rows else
                             None if not hasattr(rows, "empty") or rows.empty else rows.iloc[0]["sector"])
        except Exception:
            _SECTORS[sym] = None
    return _SECTORS[sym]


# ---------------------------------------------------------------- making the numbers readable
UNITS = {"trillion": 1e12, "triliun": 1e12, "t": 1e12, "billion": 1e9, "miliar": 1e9, "b": 1e9, "million": 1e6, "juta": 1e6, "m": 1e6}
MONTHS = "January February March April May June July August September October November December".split()


def _short(v):
    """26097380221560 → '26.1 T'; 2.005e12 → '2 T'; 2588 → '2,588'."""
    for div, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if v >= div:
            x = v / div
            return f"{x:.1f}".rstrip("0").rstrip(".") + f" {unit}" if x < 100 else f"{x:,.0f} {unit}"
    return f"{v:,.0f}" if v >= 100 else f"{v:,.2f}".rstrip("0").rstrip(".")


def _num(m):
    """A regex match of an amount (with optional Rp and unit) → short form."""
    rp, n, unit = m.group(1), m.group(2), (m.group(3) or "").lower()
    # Indonesian style "Rp 2.588" vs English "Rp2,588": a lone dot followed by 3 digits is a thousands mark
    if not unit and re.fullmatch(r"\d{1,3}(\.\d{3})+", n):
        n = n.replace(".", "")
    v = float(n.replace(",", "")) * UNITS.get(unit, 1)
    return f"{'Rp ' if rp else ''}{_short(v)}"


AMOUNT = re.compile(r"(Rp\s?)?(\d[\d,.]*\d|\d)(?:\s?(trillion|triliun|billion|miliar|million|juta|T|B|M)\b)?(?![\d%])", re.I)


def _readable(text):
    """Every amount short ('Rp26,097,380,221,560' → 'Rp 26.1 T'), dates short ('1 September 2026' → '1 Sep')."""
    text = re.sub(r"\b(\d{1,2}) (" + "|".join(MONTHS) + r")(?: \d{4})?\b", lambda m: f"{m.group(1)} {m.group(2)[:3]}", text)
    text = re.sub(r"\b(" + "|".join(MONTHS) + r") (\d{1,2})(?:, \d{4})?\b", lambda m: f"{m.group(2)} {m.group(1)[:3]}", text)
    out = []
    for part in re.split(r"(\d{4}\b(?!,\d))", text):  # leave years alone
        out.append(part if re.fullmatch(r"(19|20)\d{2}", part) else AMOUNT.sub(lambda m: _num(m) if (m.group(1) or m.group(3) or len(m.group(2)) > 4) else m.group(0), part))
    return "".join(out).replace("First-Half", "H1").replace("first-half", "H1")


def _headline(title, sym):
    """'PT Waskita Karya Tbk (WSKT) Accumulated Losses Reach Rp22.53 Trillion …' → 'Waskita Karya Accumulated Losses
    Reach Rp 22.5 T'. Commentary after the first comma goes when the title is long."""
    t = re.sub(r"\bPT\s+", "", title)
    t = re.sub(r"\s+Tbk\.?", "", t)
    t = re.sub(rf"\s*\({sym}\)", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > 64 and ", " in t:
        t = t.split(", ")[0]
    return _readable(t)


def _is_roundup(r):
    """Market wraps that bundle several companies' news in one title ('ASII …, PGEO …, VIVA …')."""
    return len(re.findall(r"\b[A-Z]{4}\b", r.get("title") or "")) >= 3


def _figure(item):
    """'Rp8.13 trillion, +53.73% YoY' → value 'Rp 8.1 T', sub '+53.73% YoY'. 'per share' moves to the sub."""
    value, _, sub = _readable(str(item.get("value", ""))).partition(", ")
    value, sub = value.strip(), sub.strip()
    sub = sub.split(", ")[0]  # one clause: "Rp 259 B total, cum date 12 Oct" → "Rp 259 B total"
    if value.endswith(" per share"):
        value, sub = value[: -len(" per share")], ("per share" + (f" · {sub}" if sub else ""))
    if len(sub) > 28:  # a sub that doesn't fit whole is dropped, never cut with an ellipsis
        sub = "per share" if sub.startswith("per share") else ""
    return {"label": _readable(item.get("label", "")), "value": value, "sub": sub}


def _figures(body):
    out = []
    for block in (body or {}).get("blocks", []):
        if block.get("type") == "metrics":
            out += [_figure(i) for i in block.get("items", []) if i.get("value")]
    return [f for f in out if len(f["value"]) <= 16 and len(f["label"]) <= 28]


HERO_LABEL = re.compile(r"value|revenue|profit|loss|total|dividend|price|target", re.I)


def _hero(figs):
    """The figure to set huge: a money or percent figure, the ones named like value/revenue/profit first."""
    money = [f for f in figs if re.search(r"Rp|%", f["value"])]
    return next((f for f in money if HERO_LABEL.search(f["label"])), money[0] if money else None)


def select_stories(hours=36, n=4):
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    df = fetch_supabase_table("idx_news", columns="id, title, source, timestamp, tags, symbols, score, structured_body, thumbnail",
                              since_column="timestamp", since_value=since, order_column="score", limit=200)
    picked, seen = [], set()
    rows = sorted(df.to_dict(orient="records"), key=lambda r: (-(bool(_figures(r.get("structured_body")))), -(r.get("score") or 0)))
    for r in rows:
        syms = [s.split(".")[0] for s in (r.get("symbols") or [])]
        if not syms or syms[0] in seen or (r.get("score") or 0) < 70 or _is_roundup(r):
            continue
        seen.add(syms[0])
        picked.append({**r, "sym": syms[0]})
        if len(picked) == n:
            break
    return sorted(picked, key=lambda r: -(r.get("score") or 0))


def build_carousel(stories, day, dither_cover=False):
    date_txt = f"{day.day} {day:%b}"
    for s in stories:
        s["photo"] = _photo(s.get("thumbnail"))
    lead = stories[0]
    base = {"page": "maroon", "kicker": "News flash", "company": f"IDX · {date_txt}", "logo": None,
            "source": f"Sectors news · {date_txt} {day.year}"}
    slides = [("news_cover", lead, {
        "sym": lead["sym"], "logo": _logo(lead["sym"]), "photo": dither(lead["photo"], style="bayer", cell=3) if dither_cover and lead["photo"] else lead["photo"],
        "headline": _headline(lead["title"], lead["sym"]),
        "date": date_txt, "more": [{"sym": s["sym"], "logo": _logo(s["sym"])} for s in stories[1:]],
        "sector": None if lead["photo"] else _sector(lead["sym"]),
    })]
    for s in stories:
        figs = _figures(s.get("structured_body"))
        hero = _hero(figs)
        slides.append(("news_story", s, {
            "sym": s["sym"], "logo": _logo(s["sym"]), "photo": s["photo"], "headline": _headline(s["title"], s["sym"]),
            "hero": hero, "figures": [f for f in figs if f is not hero][:2],
            "source": urlparse(s.get("source") or "").netloc.replace("www.", ""),
            "sector": None if s["photo"] else _sector(s["sym"]),
        }))
    slides.append(("news_close", None, {
        "title": "Today, in short",
        "items": [{"sym": s["sym"], "logo": _logo(s["sym"]), "headline": _headline(s["title"], s["sym"])} for s in stories],
        "question": "Which one are you watching?",
        "cta": "All stories on sectors.app/indonesia/news",
    }))
    out = []
    for i, (kind, story, s) in enumerate(slides):
        tags = (story or {}).get("tags") or []
        # the news accent is Foundations fig (plum-maroon); only a bearish story switches to terracotta
        direction = "sell" if "Bearish" in tags else "fig"
        out.append((kind, {**base, "direction": direction, "slide": {**s, "page": i + 1, "pages": len(slides)}}))
    return out


def render(stories, out_dir, day):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (kind, data) in enumerate(build_carousel(stories, day), 1):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        out = out_dir / f"news_flash_{day:%Y%m%d}_{i}.png"
        run = subprocess.run(["node", str(RENDER_JS), kind, f.name, "--out", str(out)], capture_output=True, text=True, encoding="utf-8")
        Path(f.name).unlink(missing_ok=True)
        if run.returncode != 0:
            raise RuntimeError(f"render failed for {kind}:\n{run.stderr.strip() or run.stdout.strip()}")
        paths.append(str(out))
    return paths


def main():
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="output_news_flash")
    p.add_argument("--hours", type=int, default=36)
    p.add_argument("--stories", type=int, default=4)
    args = p.parse_args()
    stories = select_stories(args.hours, args.stories)
    print(f"{len(stories)} stories")
    for s in stories:
        print(f"  {s['sym']:5} {s.get('score')}  {s['title'][:90]}")
    if stories:
        for path in render(stories, args.out, datetime.now()):
            print("   ", path)


if __name__ == "__main__":
    main()
