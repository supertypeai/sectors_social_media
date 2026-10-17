"""News story: the day's IDX news as two Instagram story frames (1080 x 1920), Sectors Hairline style.

    python -m image_generator.story_news --out output_stories/news [--hours 36] [--stories 5]

Frames, drawn by iso/hl/render.mjs (DATA.format = "story"):
  1. story_news_list  today's headlines as a tight list: logo, ticker, a short headline, the one key number
  2. story_news_lead  the lead story: its photo full-bleed, a short headline, the key number huge, two more

Data and helpers come from image_generator.news_flash (selection, number shortener, headline cleaner,
figures from structured_body metrics, photo as data URI, logos). Nothing is computed; figures are copied.
Replaces the text-heavy news-tier1 / news-tier2 stories. Renders only; never posts.
"""
import argparse
import json
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from .news_flash import DIRECTION, RENDER_JS, _figures, _headline, _hero, _logo, _photo, select_stories

# the story's category, from idx_news tags, as one short word (first match wins)
CATEGORY = [("Mergers & Acquisitions", "M&A"), ("Rights Issue", "Rights issue"), ("Dividend Announcement", "Dividend"),
            ("IPO", "IPO"), ("Financial Metrics", "Earnings"), ("Insider Trading", "Insider"), ("Ownership", "Ownership"),
            ("Capital & Funding", "Funding"), ("Business Expansion", "Expansion"), ("Analyst Ratings", "Analysts")]
SCALE = re.compile(r"\d\s?(T|B)\b")


def _category(tags):
    return next((short for tag, short in CATEGORY if tag in (tags or [])), "News")


def _direction(tags):
    return next((DIRECTION[t] for t in (tags or []) if t in DIRECTION), "buy")


def _key(figs, sym):
    """The one number for a glance: a rupiah deal / revenue size (T or B) beats a per-share price. In a
    round-up a figure labelled with another company's ticker is not this story's number."""
    figs = [f for f in figs if not (re.fullmatch(r"[A-Z]{4}", f["label"]) and f["label"] != sym)]
    # a round-up's own row ("ASII: Rp 98 per share"): the per-share figure, labelled by what it is
    own = [f for f in figs if f["label"] == sym and f["sub"].startswith("per share")]
    if own:
        return {**own[0], "label": "per share", "sub": ""}
    figs = [f for f in figs if f["label"] != sym]  # an unlabelled number is not a glance
    big = [f for f in figs if "Rp" in f["value"] and SCALE.search(f["value"])]
    return big[0] if big else _hero(figs)


def _short_headline(text, limit):
    """Shorten at a clause boundary until it fits `limit` characters; drop the trailing clause, never '…'."""
    text = re.sub(r"\s*\([A-Z]{4}\)", "", text)
    while len(text) > limit:
        cut = max(text.rfind(sep, 0, limit + 1) for sep in (", ", " for ", " to ", " and ", " via ", " of ", " as ", " amid ", " after ", " from "))
        if cut < 18:
            words = text[: limit + 1].rsplit(" ", 1)[0]
            return words.rstrip(",;:-– ")
        text = text[:cut].rstrip(",; ")
    return text


def build_frames(stories, day):
    date_txt = f"{day.day} {day:%b}"
    lead = next((s for s in stories if s.get("thumbnail")), stories[0])
    base = {"format": "story", "kicker": "IDX news", "company": date_txt, "source": f"Sectors news · {date_txt} {day.year}"}
    rows = []
    for s in stories:
        k = _key(_figures(s.get("structured_body")), s["sym"])
        rows.append({"sym": s["sym"], "logo": _logo(s["sym"]), "cat": _category(s.get("tags")),
                     "bear": _direction(s.get("tags")) == "sell",
                     "headline": _short_headline(_headline(s["title"], s["sym"]), 78),
                     "value": k["value"] if k and len(k["value"]) <= 10 else None,
                     "label": k["label"] if k and len(k["label"]) <= 24 else None})
    figs = _figures(lead.get("structured_body"))
    key = _key(figs, lead["sym"])
    more = [f for f in figs if f is not key and len(f["value"]) <= 10 and not re.fullmatch(r"\d{1,2} \w{3}|[A-Za-z ]+", f["value"])][:2]
    return [
        ("story_news_list", {**base, "direction": _direction(lead.get("tags")), "slide": {"title": "Today's headlines", "rows": rows}}),
        ("story_news_lead", {**base, "kicker": "Top story", "direction": _direction(lead.get("tags")), "slide": {
            "sym": lead["sym"], "logo": _logo(lead["sym"]), "photo": _photo(lead.get("thumbnail")), "cat": _category(lead.get("tags")),
            "headline": _short_headline(_headline(lead["title"], lead["sym"]), 70), "hero": key, "figures": more}}),
    ]


def build_combo(stories, day, theme="light"):
    """The posted story: ("news_combo", DATA) - up to five photo tiles (the lead big), each with its logo, ticker,
    category, one key number and the headline."""
    from .news_flash import _sector
    tiles = []
    for s in stories[:5]:
        photo = _photo(s.get("thumbnail"))
        tiles.append({"sym": s["sym"], "logo": _logo(s["sym"]), "photo": photo,
                      "sector": None if photo else _sector(s["sym"]),  # the placeholder when there is no photo
                      "cat": _category(s.get("tags")), "bear": _direction(s.get("tags")) == "sell",
                      "headline": _headline(s["title"], s["sym"]), "full": s["title"],
                      "key": _key(_figures(s.get("structured_body")), s["sym"])})
    return ("news_combo", {"format": "story", "theme": theme, "company": f"{day.day} {day:%b %Y}", "stories": tiles,
                           "source": f"Sectors news · {day.day} {day:%b %Y}"})


def render(stories, out_dir, day):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (kind, data) in enumerate(build_frames(stories, day), 1):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        out = out_dir / f"story_news_{day:%Y%m%d}_{i}.png"
        run = subprocess.run(["node", str(RENDER_JS), kind, f.name, "--out", str(out)], capture_output=True, text=True, encoding="utf-8")
        Path(f.name).unlink(missing_ok=True)
        if run.returncode != 0:
            raise RuntimeError(f"render failed for {kind}:\n{run.stderr.strip() or run.stdout.strip()}")
        paths.append(str(out))
    return paths


def main():
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="output_stories/news")
    p.add_argument("--hours", type=int, default=36)
    p.add_argument("--stories", type=int, default=5)
    args = p.parse_args()
    stories = select_stories(args.hours, args.stories)
    print(f"{len(stories)} stories")
    if stories:
        for path in render(stories, args.out, datetime.now()):
            print("   ", path)


if __name__ == "__main__":
    main()
