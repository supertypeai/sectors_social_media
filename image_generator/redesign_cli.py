"""The redesigned posts (Sectors Hairline), one command each: render, then queue to Mailroom.

    python -m image_generator.redesign_cli <command> [--dry-run] [--out output/redesign]

Feed carousels (one weekly slot each; times are the go-live times in post_routing.POST_SCHEDULE_BY_CONTENT_TYPE):
  news-flash         Wed 16:30  the day's top stories, maroon                         (news_flash.py)
  weekly-calendar    Mon 13:00  the week's corporate actions, maroon                  (weekly_calendar.py)
  insider-carousel   Tue 13:00  the week's biggest unposted insider move, blue        (insider_v_people + insider_v_data)
  earnings-carousel  Thu 13:00  the biggest unposted earnings spike/drop, blue        (earnings_v_data)

Daily stories (one image each, light theme; breaking news is posted by hand, not here):
  story-crossing  10:00   story-news  13:00   story-volume  20:00   story-broker  20:30   story-movers  21:00

Every command exits 0 without queuing when there is nothing new (no trading day, no spike, nothing unposted).
--dry-run renders the images and prints the caption but never touches Mailroom or the state file.

Dedup: the two carousels and story-crossing remember what they posted in state/posted_redesign.json (the
workflow commits it back). The other posts are one per day / week by construction.

Slide 1 of both carousels is the motion cover's last frame (insider_seats_motion / earn_bars_motion) as a still;
the MP4 is rendered next to it with --video for a manual upload, since the Mailroom queue takes images only.
"""
import json
import subprocess
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import typer
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
RENDER_JS = ROOT / "iso" / "hl" / "render.mjs"
STATE_PATH = ROOT / "state" / "posted_redesign.json"
TAGS = "#IDX #StockMarket #Indonesia #SectorsApp"
WIB = timezone(timedelta(hours=7))

app = typer.Typer(help="Render and queue the redesigned Sectors posts.")


# ---------------------------------------------------------------- helpers
def _today():
    return datetime.now(WIB).date()


def _render(kind, data, out, video=False):
    """One slide through iso/hl/render.mjs; returns the PNG path (an MP4 is written beside it with video=True)."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, default=str)
    cmd = ["node", str(RENDER_JS), kind, f.name, "--out", str(out)] + (["--video", "6"] if video else [])
    run = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    Path(f.name).unlink(missing_ok=True)
    if run.returncode != 0:
        raise RuntimeError(f"render failed for {kind}:\n{run.stderr.strip() or run.stdout.strip()}")
    return out


def _load_state():
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _remember(kind, key):
    state = _load_state()
    state.setdefault(kind, [])
    if key not in state[kind]:
        state[kind].append(key)
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _posted(kind, key):
    return key in _load_state().get(kind, [])


def _summarizer():
    try:
        from .summarizer import NewsSummarizer
        return NewsSummarizer()
    except Exception as error:  # no LLM key: captions fall back to their template
        typer.echo(f"LLM captions disabled: {error}")
        return None


def _queue(content_type, paths, caption, dry_run, item=None, threads=False):
    """Queue one post (feed carousel or one-image story) with its go-live time; crosspost feed posts to Threads.
    Returns True when it was queued (or would have been, on a dry run)."""
    typer.echo(f"\n[{content_type}] {len(paths)} image(s):")
    for p in paths:
        typer.echo(f"  {p}")
    if caption:
        typer.echo(f"caption:\n{caption}\n")
    if dry_run:
        typer.echo("dry run: not queued")
        return True
    from .post_routing import scheduled_at_for
    from .social_queue import crosspost_to_threads, queue_post
    row = queue_post(content_type, [str(p) for p in paths], caption,
                     content_type=f"{content_type}-{item}" if item else None,
                     scheduled_at=scheduled_at_for(content_type))
    if not row:
        typer.echo(f"not queued: {content_type} is not routed (post_routing) or the queue write failed")
        return False
    typer.echo(f"queued for {row.get('scheduled_at')}")
    if threads:
        try:
            crosspost_to_threads(content_type, row.get("image_url") or [], caption, summarizer=_summarizer())
        except Exception as error:
            typer.echo(f"Threads crosspost failed: {error}")
    return True


def _renumber(frames):
    n = len(frames)
    return [(k, {**d, "slide": {**d["slide"], "page": i + 1, "pages": n}}) for i, (k, d) in enumerate(frames)]


# ---------------------------------------------------------------- feed carousels
@app.command("news-flash")
def news_flash(out: Path = typer.Option(Path("output/redesign/news_flash"), "--out"),
               dry_run: bool = typer.Option(False, "--dry-run"),
               hours: int = typer.Option(36, "--hours"), stories: int = typer.Option(4, "--stories")):
    """Wed: the top stories of the last day and a half, one slide each, as a maroon carousel."""
    from . import news_flash as nf
    picked = nf.select_stories(hours=hours, n=stories)
    if not picked:
        typer.echo("skip: no news with a ticker")
        raise typer.Exit(0)
    paths = [Path(p) for p in nf.render(picked, out, datetime.now(WIB))]
    lines = "\n".join(f"• ${s['sym']}: {nf._headline(s['title'], s['sym'])}" for s in picked)
    caption = f"Today on the IDX, in {len(picked)} stories:\n\n{lines}\n\nWhich one are you watching?\n\n{TAGS} #News"
    _queue("news-flash", paths, caption, dry_run, item=f"{_today():%Y%m%d}", threads=True)


@app.command("weekly-calendar")
def weekly_calendar(out: Path = typer.Option(Path("output/redesign/weekly_calendar"), "--out"),
                    dry_run: bool = typer.Option(False, "--dry-run")):
    """Mon: this week's dividends, rights issues, splits, warrants and AGMs, as a maroon carousel."""
    from . import weekly_calendar as wc
    start = _today()
    paths = [Path(p) for p in wc.render(start, start + timedelta(days=6), out)]
    if not paths:
        typer.echo("skip: nothing on the calendar this week")
        raise typer.Exit(0)
    end = start + timedelta(days=6)
    caption = (f"The IDX week ahead, {start.day} {start:%b} – {end.day} {end:%b}: dividends you can still catch, "
               f"rights issues, splits and shareholder meetings, day by day.\n\nSave this for the week.\n\n{TAGS} #Dividend")
    _queue("weekly-calendar", paths, caption, dry_run, item=f"{start:%Y%m%d}", threads=True)


def _insider_key(row):
    return f"{str(row['symbol']).split('.')[0]}|{row.get('holder_name')}|{str(row.get('timestamp'))[:10]}"


@app.command("insider-carousel")
def insider_carousel(out: Path = typer.Option(Path("output/redesign/insider"), "--out"),
                     dry_run: bool = typer.Option(False, "--dry-run"),
                     days: int = typer.Option(7, "--days"), video: bool = typer.Option(False, "--video")):
    """Tue: the biggest insider move of the last week not posted yet, as a 5-slide blue carousel."""
    from .combo_posts import insider_frames
    from .data import fetch_filings
    from .insider_move import select_moves
    from .insider_patterns import drop_mixed_leg_filings
    df = drop_mixed_leg_filings(fetch_filings(since=(datetime.now() - timedelta(days=days + 20)).isoformat()))
    moves = [m for m in select_moves(df, days=days, min_pp=1.0) if not _posted("insider", _insider_key(m))]
    for row in moves:
        frames = insider_frames(row, df)
        if not frames:
            continue
        frames = _renumber([("insider_seats_motion", frames[0][1])] + frames[1:])
        sym = str(row["symbol"]).split(".")[0]
        paths = [_render(k, {**d, "theme": "blue"}, out / sym / f"{i}.png", video=(video and i == 1))
                 for i, (k, d) in enumerate(frames, 1)]
        S = frames[0][1]["slide"]
        caption = (f"{S['holder']['name']} {S['headline']}.\n\n"
                   f"Deal value {S['value']}, traded {S['span']} {S['year']}. Swipe for who they are, whether the "
                   f"timing was good and who owns ${sym} now.\n\nNot financial advice.\n\n{TAGS} #InsiderTrading")
        if _queue("insider-carousel", paths, caption, dry_run, item=sym, threads=True) and not dry_run:
            _remember("insider", _insider_key(row))
        return
    typer.echo(f"skip: no unposted insider move in the last {days} days")


@app.command("earnings-carousel")
def earnings_carousel(out: Path = typer.Option(Path("output/redesign/earnings"), "--out"),
                      dry_run: bool = typer.Option(False, "--dry-run"), video: bool = typer.Option(False, "--video")):
    """Thu: the biggest earnings spike or drop of the season not posted yet, as a blue carousel."""
    from . import earnings_v_data
    from .cli import _earnings_caption
    from .data import fetch_company_report_earnings
    from .insider_patterns import select_earnings_spikes
    df = fetch_company_report_earnings(200)
    events = select_earnings_spikes(df, direction="spike") + select_earnings_spikes(df, direction="drop")
    events.sort(key=lambda e: abs(e.get("earnings_growth") or 0), reverse=True)
    for e in events:
        key = f"{e['base_symbol']}|{e.get('latest_quarter')}"
        if _posted("earnings", key):
            continue
        frames = earnings_v_data.build(e, df) or []
        if len(frames) < 3:
            continue
        frames = _renumber([("earn_bars_motion", frames[0][1])] + frames[1:])
        sym = e["base_symbol"]
        paths = [_render(k, {**d, "theme": "blue"}, out / sym / f"{i}.png", video=(video and i == 1))
                 for i, (k, d) in enumerate(frames, 1)]
        caption = _earnings_caption(e, _summarizer())
        if _queue("earnings-carousel", paths, caption, dry_run, item=sym, threads=True) and not dry_run:
            _remember("earnings", key)
        return
    typer.echo("skip: no unposted earnings spike or drop")


# ---------------------------------------------------------------- daily stories (light)
@app.command("story-broker")
def story_broker(out: Path = typer.Option(Path("output/redesign/stories"), "--out"),
                 dry_run: bool = typer.Option(False, "--dry-run"), day: str = typer.Option(None, "--date")):
    """The day's top 5 brokers on the podium. Skips when today has no broker data (market shut)."""
    from . import story_broker as sb
    d = date.fromisoformat(day) if day else sb.latest_trading_day()
    paths = sb.render_day(d, out) if d else []
    if not paths:
        typer.echo("skip: no broker data for today")
        raise typer.Exit(0)
    _queue("story-broker", [Path(p) for p in paths], None, dry_run)


@app.command("story-movers")
def story_movers(out: Path = typer.Option(Path("output/redesign/stories"), "--out"),
                 dry_run: bool = typer.Option(False, "--dry-run"), day: str = typer.Option(None, "--date")):
    """The day's 5 biggest gainers and losers in the top 100. Skips when IHSG has no close for today."""
    from . import story_movers as sm
    d = date.fromisoformat(day) if day else sm.latest_trading_day()
    paths = sm.render_day(d, out) if d else []
    if not paths:
        typer.echo("skip: no trading data for today")
        raise typer.Exit(0)
    _queue("story-movers", [Path(p) for p in paths], None, dry_run)


@app.command("story-volume")
def story_volume(out: Path = typer.Option(Path("output/redesign/stories"), "--out"),
                 dry_run: bool = typer.Option(False, "--dry-run"), day: str = typer.Option(None, "--date")):
    """The day's loudest volume spike in the top 100 (price line over volume bars). Skips on a day with no spike."""
    from . import story_volume as sv
    d, rows = sv.build(date.fromisoformat(day) if day else _today())
    if not rows:
        typer.echo("skip: no volume spike today")
        raise typer.Exit(0)
    kind, data = sv.slides(d, rows)[0]
    data = {**data, "slide": {"page": 1, "pages": 1}}  # one story frame, not the old two
    path = _render("volume_spike", {**data, "theme": "light"}, out / f"story_volume_{d:%Y%m%d}.png")
    _queue("story-volume", [path], None, dry_run)


@app.command("story-news")
def story_news(out: Path = typer.Option(Path("output/redesign/stories"), "--out"),
               dry_run: bool = typer.Option(False, "--dry-run"), hours: int = typer.Option(24, "--hours")):
    """Today's top 5 stories as photo tiles. Skips when there are fewer than 3."""
    from . import story_news as sn
    from .news_flash import select_stories
    picked = select_stories(hours=hours, n=5)
    if len(picked) < 3:
        typer.echo(f"skip: only {len(picked)} stories with a ticker")
        raise typer.Exit(0)
    d = _today()
    kind, data = sn.build_combo(picked, d)
    _queue("story-news", [_render(kind, data, out / f"story_news_{d:%Y%m%d}.png")], None, dry_run)


@app.command("story-crossing")
def story_crossing(out: Path = typer.Option(Path("output/redesign/stories"), "--out"),
                   dry_run: bool = typer.Option(False, "--dry-run"), days: int = typer.Option(3, "--days")):
    """The newest investor to cross 5% of a company (filed in the last few days, not posted yet)."""
    from . import story_crossing as sc
    from .data import fetch_filings
    from .insider_patterns import drop_mixed_leg_filings, group_becoming_insider
    df = drop_mixed_leg_filings(fetch_filings(since=(datetime.now() - timedelta(days=200)).isoformat()))
    cut = (_today() - timedelta(days=days)).isoformat()
    for ev in [e for e in group_becoming_insider(df) if e["cross_date"] >= cut]:
        key = f"{ev['base_symbol']}|{ev['holder_name']}|{ev['cross_date']}"
        if _posted("crossing", key) or not sc.usable(ev, df):
            continue
        built = sc.build_podium(ev, df)
        if not built:
            continue
        path = _render(*built, out / f"story_crossing_{ev['base_symbol']}.png")
        if _queue("story-crossing", [path], None, dry_run, item=ev["base_symbol"]) and not dry_run:
            _remember("crossing", key)
        return
    typer.echo(f"skip: no new 5% crossing in the last {days} days")


if __name__ == "__main__":
    load_dotenv()
    app()
