"""Isometric feed posts: Python picks the data and writes the copy, iso/post.mjs draws it.

The drawing lives in iso/stories/<story>.js (the isostory engine, vendored in iso/vendor).
This module only shapes a pattern dict into the story's DATA and shells out to node.
"""
import json
import statistics
import subprocess
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POST_JS = ROOT / "iso" / "post.mjs"


def _rp(value):
    """61_750_000_000 -> 'Rp 61.8 B' (same rule as rp() in iso/parts.js)."""
    a = abs(value)
    for div, unit in ((1e12, " T"), (1e9, " B"), (1e6, " M")):
        if a >= div:
            n = a / div
            return f"Rp {n:.0f}{unit}" if n >= 100 else f"Rp {n:.1f}".rstrip("0").rstrip(".") + unit
    return f"Rp {a:,.0f}"


def _day(iso_date):
    d = date.fromisoformat(str(iso_date)[:10])
    return f"{d.day} {d:%b}"


def _span(first, last):
    a, b = date.fromisoformat(str(first)[:10]), date.fromisoformat(str(last)[:10])
    return f"{_day(a)} – {_day(b)} {b.year}"


def chain_data(chain):
    """The DATA object for iso/stories/insider_chain.js, copy included."""
    points = [
        {"date": str(p["date"])[:10], "value": float(p["value"]), "shares": float(p.get("shares") or 0),
         "price": float(p.get("price") or 0)}
        for p in chain["points"] if p.get("value")
    ]
    sym = chain.get("base_symbol") or chain["symbol"].split(".")[0]
    sell = chain["direction"] == "sell"
    verb = "sold" if sell else "bought"
    n = len(points)
    big = max(points, key=lambda p: p["value"])
    others = [p["value"] for p in points if p is not big]
    typical = statistics.median(others) if others else big["value"]
    # Same base as the "usual" pin, so the slide's numbers multiply out (not size_anomaly's own base).
    mult = big["value"] / typical if typical else 1

    # The angle: an outsized single trade, or a steady streak.
    if mult >= 5 and n >= 4:
        sub = f"One {('sale' if sell else 'buy')} was {mult:.0f}× the usual size"
        pin_small = f"usual {('sale' if sell else 'buy')} ≈ {_rp(typical)}"
    else:
        sub = f"{_rp(chain['total_value'])} across {n} filings"
        pin_small = ""  # the footer already carries the total

    # The headline must fit two lines at feed size; a long (usually corporate) name moves to the sub line.
    holder = chain["holder_name"]
    headline = f"{holder} {verb} {sym} {n} times"
    if len(headline) > 34:
        headline = f"{verb.capitalize()} {sym} {n} times"
        sub = f"by {holder}" if len(holder) <= 40 else f"by {holder[:38].rstrip()}…"

    first, last = chain.get("ownership_first"), chain.get("ownership_last")
    stat = f"Stake {first:.2f}% → {last:.2f}%" if first is not None and last is not None else f"Total {_rp(chain['total_value'])}"
    trade = "sale" if sell else "buy"
    tiles = [{"value": _rp(chain["total_value"]), "label": f"TOTAL {verb.upper()}"}]
    if last is not None:
        tiles.append({"value": f"{last:.2f}%", "label": f"STAKE NOW · WAS {first:.2f}%", "tone": "accent"})
    tiles.append({"value": f"{mult:.0f}×", "label": f"BIGGEST VS USUAL {trade.upper()}"} if mult >= 5 and n >= 4
                 else {"value": str(n), "label": "FILINGS"})
    return {
        "kind": "chain",
        "symbol": sym,
        "holder": chain["holder_name"],
        "direction": chain["direction"],
        "points": points,
        "chart": {"kind": "timeline", "title": f"Every {trade}, by size",
                  "items": [{"value": p["value"], "date": p["date"], "hi": p is big} for p in points]},
        "tiles": tiles,
        "scene": {"people": [chain["holder_name"]]},
        "copy": {
            "kicker": f"INSIDER {'SELLING' if sell else 'BUYING'} · {sym}",
            "headline": headline,
            "emphasis": [f"{n}"],
            "sub": sub,
            "pinBig": f"{_day(big['date'])} · {_rp(big['value'])}",
            "pinSmall": pin_small,
            "stat": stat,
            "statEmphasis": [f"{last:.2f}%"] if last is not None else [],
            "source": f"IDX insider filings · {_span(chain['first_date'], chain['last_date'])} · Total {_rp(chain['total_value'])}",
        },
    }


def cluster_data(cluster):
    """DATA for the layout stories: several insiders trading one stock in the same window."""
    sym = cluster.get("base_symbol") or cluster["symbol"].split(".")[0]
    sell = cluster["direction"] == "sell"
    verb = "sold" if sell else "bought"
    roster = sorted(cluster["roster"], key=lambda r: r["value"], reverse=True)
    n = len(roster)
    total = cluster["total_value"]
    top = roster[0]
    top_share = top["value"] / total if total else 0

    # The angle: one person dominates the group, or the group moved together.
    if top_share >= 0.8:
        sub = f"{top['name']} alone {verb} {_rp(top['value'])}"
    else:
        sub = f"{_rp(total)} across {cluster['filing_count']} filings"
    tiles = [
        {"value": _rp(total), "label": f"TOTAL {verb.upper()}", "tone": "accent"},
        {"value": str(n), "label": "INSIDERS"},
        {"value": f"{top_share * 100:.1f}%" if top_share >= 0.5 else str(cluster["filing_count"]),
         "label": "FROM THE TOP NAME" if top_share >= 0.5 else "FILINGS"},
    ]
    return {
        "kind": "cluster",
        "symbol": sym,
        "direction": cluster["direction"],
        "chart": {"kind": "roster", "title": f"Who {verb}, by value",
                  "items": [{"label": r["name"], "value": r["value"], "hi": i == 0} for i, r in enumerate(roster[:5])]},
        "tiles": tiles,
        "scene": {"people": [r["name"] for r in roster[:5]]},
        "copy": {
            "kicker": f"INSIDER {'SELLING' if sell else 'BUYING'} · {sym}",
            "headline": f"{n} insiders {verb} {sym}",
            "emphasis": [str(n)],
            "sub": sub,
            "source": f"IDX insider filings · {_span(cluster['first_date'], cluster['last_date'])}",
        },
    }


LAYOUTS = ("layout_card", "layout_board", "layout_plinth")


def render_layouts(data, out_dir="output", layouts=LAYOUTS):
    """One slide per layout for the same DATA, for side-by-side review."""
    paths = []
    for layout in layouts:
        prefix = f"iso_{data['kind']}_{data['symbol']}_{layout.removeprefix('layout_')}"
        paths += render_story(layout, data, out_dir, prefix)
    return paths


def render_story(story, data, out_dir, prefix, at=None, keep_html=False):
    """Run iso/post.mjs; returns the PNG paths it wrote."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        data_file = f.name
    cmd = ["node", str(POST_JS), story, data_file, "--out", str(out_dir), "--prefix", prefix]
    if at:
        cmd += ["--at", ",".join(str(t) for t in at)]
    if keep_html:
        cmd.append("--html")
    run = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    Path(data_file).unlink(missing_ok=True)
    if run.returncode != 0:
        raise RuntimeError(f"iso render failed:\n{run.stderr.strip() or run.stdout.strip()}")
    return [line for line in run.stdout.splitlines() if line.endswith(".png")]


# ---------------------------------------------------------------- carousels
# Slide 1 hooks with one hero number; the slides after it explain. Which slides a post gets depends on its
# data, so a post with nothing to say on a slide does not get that slide.

def _logo_uri(sym):
    path = ROOT / "logos" / f"{sym}.webp"
    return path.as_uri() if path.exists() else None


def chain_carousel(chain):
    base = chain_data(chain)
    sym, holder, sell = base["symbol"], base["holder"], base["direction"] == "sell"
    verb, trade = ("sold", "sale") if sell else ("bought", "buy")
    pts = base["points"]
    n = len(pts)
    big = max(pts, key=lambda p: p["value"])
    others = [p["value"] for p in pts if p is not big]
    typical = statistics.median(others) if others else big["value"]
    mult = big["value"] / typical if typical else 1
    outlier = mult >= 5 and n >= 4
    first, last = chain.get("ownership_first"), chain.get("ownership_last")

    slides = []
    if outlier:
        slides.append({"kind": "slide_hook", "hero": f"{mult:.0f}×",
                       "title": f"One {sym} {trade} was {mult:.0f}× bigger than the rest", "accentWords": [sym],
                       "sub": f"{holder} · {_day(big['date'])} · {_rp(big['value'])}"})
    else:
        slides.append({"kind": "slide_hook", "hero": _rp(chain["total_value"]),
                       "title": f"{holder} {verb} {sym} {n} times", "accentWords": [sym],
                       "sub": _span(chain["first_date"], chain["last_date"])})
    slides.append({"kind": "slide_bars", "title": f"{n} {trade}s. One giant." if outlier else f"{n} {trade}s in a row",
                   "accentWords": ["giant."], "sub": f"Every {holder} {trade} of {sym}, by rupiah value",
                   "items": [{"value": p["value"], "hi": p is big} for p in pts],
                   "hiLabel": _rp(big["value"]), "hiNote": f"{_day(big['date'])} · {mult:.0f}× the usual" if outlier else _day(big["date"]),
                   "usualLabel": f"usual {trade} ≈ {_rp(typical)}" if outlier else "",
                   "from": _day(pts[0]["date"]), "to": _day(pts[-1]["date"])})
    own = [o for o in chain.get("ownership") or [] if o.get("pct") is not None]
    if len(own) >= 3 and first is not None and last is not None and abs(last - first) >= 0.05:
        jump = max(range(1, len(own)), key=lambda i: abs(own[i]["pct"] - own[i - 1]["pct"]))
        points = [{"date": str(o["date"])[:10], "y": o["pct"]} for o in own]
        # each filing reports the stake AFTER it; the run starts from the stake before the first one
        if abs(own[0]["pct"] - first) >= 0.005:
            day0 = date.fromisoformat(points[0]["date"]).toordinal() - 1
            points.insert(0, {"date": date.fromordinal(day0).isoformat(), "y": first})
            jump += 1
        points[0].update(label=f"{first:.2f}%", note=f"{_day(points[0]['date'])} · before")
        points[jump].update(label=f"{points[jump]['y']:.2f}%", note=f"{_day(points[jump]['date'])} · the big {trade}")
        if jump != len(points) - 1:
            points[-1].update(label=f"{points[-1]['y']:.2f}%", note=f"{_day(points[-1]['date'])} · now")
        slides.append({"kind": "slide_curve", "title": f"Stake {first:.2f}% → {last:.2f}%", "accentWords": [f"{last:.2f}%"],
                       "sub": f"{holder}'s ownership of {sym} after each filing", "points": points})
    facts = [{"value": str(n), "text": f"{trade}s of {sym} by {holder}, {_span(chain['first_date'], chain['last_date'])}"},
             {"value": _rp(chain["total_value"]), "text": f"{verb} in total, at Rp {chain['avg_price']:,.0f} a share on average", "tone": "accent"}]
    if last is not None:
        facts.append({"value": f"{last:.2f}%", "text": f"stake now, from {first:.2f}% before the run"})
    caveat = "Insider filings show what was traded, not why. Not financial advice."
    slides.append({"kind": "slide_takeaway", "title": "The short version", "facts": facts, "caveat": caveat, "cta": "Track insiders on sectors.app"})
    return base, slides


def cluster_carousel(cluster):
    base = cluster_data(cluster)
    sym, sell = base["symbol"], base["direction"] == "sell"
    verb = "sold" if sell else "bought"
    roster = sorted(cluster["roster"], key=lambda r: r["value"], reverse=True)
    n, total, top = len(roster), cluster["total_value"], roster[0]
    top_share = top["value"] / total if total else 0
    days = (date.fromisoformat(str(top["last_date"])[:10]) - date.fromisoformat(str(top["first_date"])[:10])).days + 1

    slides = []
    if top_share >= 0.8:
        slides.append({"kind": "slide_hook", "hero": _rp(top["value"]),
                       "title": f"{top['name']} {verb} this much {sym} in {days} day{'s' if days > 1 else ''}", "accentWords": [sym],
                       "sub": f"Part of {n} insiders who {verb} {sym} since {_day(cluster['first_date'])}"})
    else:
        slides.append({"kind": "slide_hook", "hero": _rp(total), "title": f"{n} insiders {verb} {sym}", "accentWords": [sym],
                       "sub": _span(cluster["first_date"], cluster["last_date"])})
    slides.append({"kind": "slide_ranked", "title": f"Who {verb} {sym}", "accentWords": [sym],
                   "sub": f"Insiders by rupiah value · {_span(cluster['first_date'], cluster['last_date'])}",
                   "rows": [{"label": r["name"], "value": r["value"], "display": _rp(r["value"])} for r in roster[:5]]})
    # the running total, one point per filing date
    by_day = {}
    for p in cluster.get("points") or []:
        v = float(p.get("price") or 0) * float(p.get("shares") or 0)
        by_day[str(p["date"])[:10]] = by_day.get(str(p["date"])[:10], 0) + v
    if len(by_day) >= 3:
        run, points = 0, []
        for d in sorted(by_day):
            run += by_day[d]
            points.append({"date": d, "y": run})
        jump_day = max(by_day, key=by_day.get)
        share = by_day[jump_day] / run if run else 0
        ji = next(i for i, p in enumerate(points) if p["date"] == jump_day)
        if ji > 0:
            points[ji - 1].update(label=_rp(points[ji - 1]["y"]), note=f"by {_day(points[ji - 1]['date'])}")
        points[ji].update(label=_rp(points[ji]["y"]), note=f"{_day(jump_day)} · {share * 100:.0f}% in one day")
        if ji != len(points) - 1:
            points[-1].update(label=_rp(points[-1]["y"]), note=_day(points[-1]["date"]))
        slides.append({"kind": "slide_curve", "icon": "tower",
                       "title": f"{share * 100:.0f}% of it in one day" if share >= 0.5 else f"How the {'selling' if sell else 'buying'} added up",
                       "accentWords": [f"{share * 100:.0f}%"], "sub": f"Running total of insider {'sales' if sell else 'buys'} in {sym}", "points": points})
    facts = [{"value": str(n), "text": f"insiders {verb} {sym} between {_span(cluster['first_date'], cluster['last_date'])}"},
             {"value": f"{top_share * 100:.1f}%", "text": f"of the total came from {top['name']}", "tone": "accent"}]
    if top.get("ownership_after") is not None:
        facts.append({"value": f"{top['ownership_after']:.2f}%", "text": f"{top['name']}'s stake after the last filing"})
    slides.append({"kind": "slide_takeaway", "title": "The short version", "facts": facts,
                   "caveat": "Insider filings show what was traded, not why. Not financial advice.", "cta": "Track insiders on sectors.app"})
    return base, slides


def render_carousel(base, slides, out_dir="output"):
    """One PNG per slide, numbered in order."""
    sym, kind = base["symbol"], base["kind"]
    base = {**base, "logo": _logo_uri(sym)}
    base["copy"] = {**base["copy"], "tag": "From IDX insider filings"}
    paths = []
    for i, slide in enumerate(slides, 1):
        data = {**base, "slide": {**slide, "page": i, "pages": len(slides)}}
        paths += render_story(slide["kind"], data, out_dir, f"carousel_{kind}_{sym}_{i}")
    return paths


def render_insider_chain_iso(chain, out_dir="output", keep_html=False):
    data = chain_data(chain)
    prefix = f"iso_chain_{data['symbol']}_{chain['direction']}"
    return render_story("insider_chain", data, out_dir, prefix, keep_html=keep_html)
