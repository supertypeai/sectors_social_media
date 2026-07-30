from pathlib import Path
from datetime import date, datetime, timedelta, timezone
import tldextract

from .renderers.quarterly import QuarterlyRenderer
from .renderers.top_movers import TopCompaniesMoversRenderer
from .renderers.upcoming_dividend import UpcomingDividendRenderer
from .renderers.agm import AGMRenderer
from .renderers.dividend import DividendRenderer
from .renderers.volume_spike import VolumeSpikeRenderer
from .renderers.anomalies_changes import AnomalyChangesRenderer
from .renderers.foreign_flow import ForeignFlowRenderer
from .renderers.ownership import OwnershipRenderer
from .renderers.ownership_board import OwnershipBoardRenderer
from .renderers.winners_losers import WinnersLosersRenderer
from .renderers.sector_heatmap import SectorHeatmapRenderer
from .renderers.lq45_ytd import LQ45YTDRenderer
from .renderers.insider_roundup import InsiderRoundupRenderer
from .renderers.macro_news import MacroNewsRenderer
from .renderers.stock_performance import StockPerformanceRenderer
from .render import BACKGROUND_DIR, clean_slug
from .utils.slack import upload_posts_to_slack
from .classification import (
    prepare_data_by_mcap,
    select_quarterly_data,
    prepare_data_upcoming_dividend,
    select_ownership_posts,
)
from .data import (
    fetch_company_report,
    fetch_workflow_data,
    fetch_ihsg_weekly_data,
    fetch_idx_company_report,
    fetch_idx_upcoming_dividend,
    fetch_agm_data,
    fetch_upcoming_dividends,
    fetch_volume_spike_data,
    fetch_news_for_symbol,
    fetch_anomaly_data,
    fetch_foreign_flow_data,
    fetch_company_report_ownership,
    fetch_weekly_movers_data,
    fetch_weekly_sector_data,
    fetch_lq45_ytd_data,
    fetch_weekly_insider_aggregates,
    fetch_macro_news,
    fetch_stock_indices,
    fetch_stock_performance,
    fetch_index_performance,
    group_companies_by_index
)
from .summarizer import NewsSummarizer
from .social_queue import queue_post, crosspost_to_threads
from .post_routing import scheduled_at_for
from .utils.io_helper import (
    next_rotating_theme,
    VOLUME_SPIKE_THEME_ROTATION_ORDER,
    VOLUME_SPIKE_THEME_ROTATION_PATH,
)


def _resolve_volume_spike_theme(theme: str) -> str:
    if theme == "rotate":
        return next_rotating_theme(VOLUME_SPIKE_THEME_ROTATION_ORDER, VOLUME_SPIKE_THEME_ROTATION_PATH)
    return theme
from .utils.io_helper import load_dividend_state, save_dividend_state
from .triggers import (
    load_ownership_state,
    save_ownership_state,
    select_ownership_fires,
    record_ownership,
    load_ownership_board_state,
    save_ownership_board_state,
    board_period_key,
    board_already_posted,
    record_board,
)

import typer
import time 


app = typer.Typer(help="Run Sectors social media generation jobs.")


def _queue_post(base_content_type, image_paths, caption, content_type=None):
    """queue_post wrapper that applies the post-schedule policy from
    post_routing.py (when a content type should post vs. when it was
    generated), so every call site gets it automatically."""
    return queue_post(
        base_content_type, image_paths, caption,
        content_type=content_type,
        scheduled_at=scheduled_at_for(base_content_type),
    )


def _crosspost(base_content_type, row, caption, summarizer=None):
    """Cross-post an IG row (from _queue_post) to Threads, reusing its
    already-uploaded image_url(s). No-op if row is None (dry-run, queue
    failure) or the content type has no Threads policy."""
    if not row:
        return
    try:
        crosspost_to_threads(base_content_type, row.get("image_url") or [], caption, summarizer=summarizer)
    except Exception as error:
        typer.echo(f"Threads crosspost failed for {base_content_type}: {error}")


@app.command("quarterly")
def quarterly(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel")
):
    renderer = QuarterlyRenderer(output_dir=output)

    df_workflow = fetch_workflow_data(
        table_name="idx_workflow_data",
        columns="symbol, company_name, quarterly_low, quarterly_high",
        required_columns=["quarterly_low", "quarterly_high"],
    )

    df_company_report = fetch_company_report()
    payload_ihsg_weekly = fetch_ihsg_weekly_data()

    payload_workflow = prepare_data_by_mcap(df_workflow, df_company_report)

    payload = select_quarterly_data(payload_ihsg_weekly, payload_workflow)
   
    if not payload:
        typer.echo(f"Skipping quarterly: no data found to trigger render")
        raise typer.Exit(code=0)

    path = renderer.render(data=payload)
    typer.echo(path.resolve())

    if slack_channel:
        upload_posts_to_slack(
            [(path, "Quarterly lows update\n\n#IDX #StockMarket #Indonesia #SectorsApp")],
            slack_channel=slack_channel,
        )


@app.command("companies-mover")
def companies_mover(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel")
):
    renderer = TopCompaniesMoversRenderer(output_dir=output)

    workflow_data = fetch_workflow_data(
        table_name="idx_workflow_data",
        columns="symbol, company_name, one_month_leaders, one_month_laggards",
        is_output_json=True,
        required_columns=["one_month_leaders", "one_month_laggards"],
    )

    if not workflow_data or len(workflow_data) < 20:
        typer.echo("Skipping companies-mover: not enough data")
        raise typer.Exit(code=0)

    path = renderer.render(data=workflow_data)
    typer.echo(path.resolve())

    leaders = renderer._ranked_companies(workflow_data, "one_month_leaders")
    laggards = renderer._ranked_companies(workflow_data, "one_month_laggards")
    leaders = [{"symbol": c["symbol"].replace(".JK", ""), "pct_change": c["one_month_leaders"]["pct_change"]} for c in leaders]
    laggards = [{"symbol": c["symbol"].replace(".JK", ""), "pct_change": c["one_month_laggards"]["pct_change"]} for c in laggards]

    today = datetime.now(timezone.utc)
    since = today - timedelta(days=30)
    date_range = f"{since.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}"

    caption = None
    try:
        summarizer = NewsSummarizer()
    except Exception as error:
        typer.echo(f"LLM companies-mover caption disabled (summarizer init failed): {error}")
        summarizer = None

    if summarizer is not None:
        try:
            index_return = fetch_index_performance(target_indices=["IHSG"], day=30).get("IHSG")
            news_articles = fetch_macro_news(th_score=70, since=since)
            caption = summarizer.generate_companies_mover_caption(index_return, date_range, leaders, laggards, news_articles)
        except Exception as error:
            typer.echo(f"Companies-mover caption LLM failed: {error}")

    caption = f"{caption or 'Top movers update'}\n\n#IDX #StockMarket #Indonesia #SectorsApp"
    typer.echo("--- caption ---")
    typer.echo(caption)

    row = None
    try:
        row = _queue_post("companies-mover", path, caption)
    except Exception as error:
        typer.echo(f"Queue write failed for companies-mover: {error}")
    _crosspost("companies-mover", row, caption, summarizer=summarizer)

    if slack_channel:
        upload_posts_to_slack([(path, caption)], slack_channel=slack_channel)


def _crosspost_daily_news_agm(agm_image_urls: list[str]) -> None:
    """Combine today's news-tier1 + macro-news IG rows (generated by their
    own, separately-scheduled workflows earlier the same day) with agm's own
    images into ONE "Daily News & AGM Update" Threads post. agm runs last
    (18:00 WIB vs macro-news 15:00 and news-tier1 12:00), so it's always the
    trigger point - this fires even on a day with zero AGM data, since the
    other two should still get their combined post."""
    from .social_queue import _client, TABLE, parse_image_urls

    today = datetime.now().strftime("%Y-%m-%d")
    combined = []
    try:
        client = _client()
        # news-tier1 is a single row per run - exact content_type match.
        result = (
            client.table(TABLE)
            .select("image_url")
            .eq("platform", "ig")
            .eq("content_type", "news-tier1")
            .gte("created_at", f"{today}T00:00:00")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            combined.extend(parse_image_urls(result.data[0].get("image_url")))

        # macro-news paginates (macro-news-1, macro-news-2, ...).
        result = (
            client.table(TABLE)
            .select("image_url,created_at")
            .eq("platform", "ig")
            .like("content_type", "macro-news-%")
            .gte("created_at", f"{today}T00:00:00")
            .order("created_at")
            .execute()
        )
        for row in result.data or []:
            combined.extend(parse_image_urls(row.get("image_url")))
    except Exception as error:
        typer.echo(f"Threads crosspost lookup failed for daily news/AGM: {error}")

    combined.extend(agm_image_urls)
    if not combined:
        return
    try:
        crosspost_to_threads("agm", combined, None)
    except Exception as error:
        typer.echo(f"Threads crosspost failed for agm/daily-news: {error}")


@app.command("agm")
def agm(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel"),
):
    renderer = AGMRenderer(output_dir=output)

    df = fetch_agm_data()
    own_image_urls = []
    if df.empty:
        typer.echo("Skipping agm: no data for today")
    else:
        typer.echo(f"Rendering {len(df)} AGM card(s)...")
        paths = renderer.render(data=df)
        for path in paths:
            typer.echo(path.resolve())

        agm_caption = "AGM Results\n\n#IDX #StockMarket #Indonesia #AGM #SectorsApp"
        for i, path in enumerate(paths):
            try:
                row = _queue_post("agm", path, agm_caption, content_type=f"agm-{i + 1}")
                if row:
                    own_image_urls.extend(row.get("image_url") or [])
            except Exception as error:
                typer.echo(f"Queue write failed for agm page {i + 1}: {error}")

        if slack_channel:
            posts = [(path, agm_caption) for path in paths]
            upload_posts_to_slack(posts, slack_channel=slack_channel)

    _crosspost_daily_news_agm(own_image_urls)


@app.command("upcoming-dividend")
def upcoming_dividend(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel"),
):
    renderer = UpcomingDividendRenderer(output_dir=output)

    df = fetch_upcoming_dividends()
    if df.empty:
        typer.echo("Skipping upcoming-dividend: no data")
        raise typer.Exit(code=0)

    paths = renderer.render(data=df)
    for path in paths:
        typer.echo(path.resolve())

    dividend_caption = "Upcoming Dividends\n\n#IDX #StockMarket #Indonesia #Dividends #SectorsApp"
    # post_type='story' is single-image only, and this can paginate into
    # several table pages - queue each page as its own Story (a sequence of
    # Stories, not a carousel, since IG Stories can't hold multiple images).
    crosspost_image_urls = []
    for i, path in enumerate(paths):
        try:
            row = _queue_post("upcoming-dividend", path, dividend_caption, content_type=f"upcoming-dividend-{i + 1}")
            if row:
                crosspost_image_urls.extend(row.get("image_url") or [])
        except Exception as error:
            typer.echo(f"Queue write failed for upcoming-dividend page {i + 1}: {error}")

    # One combined Threads carousel for the whole run instead of one
    # crosspost per page - same reasoning as earnings-report above.
    if crosspost_image_urls:
        try:
            summarizer = NewsSummarizer()
        except Exception:
            summarizer = None
        try:
            crosspost_to_threads("upcoming-dividend", crosspost_image_urls, dividend_caption, summarizer=summarizer)
        except Exception as error:
            typer.echo(f"Threads crosspost failed for upcoming-dividend: {error}")

    if slack_channel:
        posts = [(path, dividend_caption) for path in paths]
        upload_posts_to_slack(posts, slack_channel=slack_channel)

        
@app.command("dividend")
def dividend(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel")
):
    renderer = DividendRenderer(output_dir=output)
    upcoming_dividends = fetch_idx_upcoming_dividend(to_df=False)
    
    if not upcoming_dividends:
        typer.echo("Skipping dividend: upcoming dividend data is null")
        raise typer.Exit(code=0)

    upcoming_symbols = [record['symbol'] for record in upcoming_dividends]

    company_reports = fetch_idx_company_report(upcoming_symbols)

    payload = prepare_data_upcoming_dividend(
        upcoming_dividends=upcoming_dividends, 
        company_reports=company_reports, 
        min_yield_growth=0.1
    )

    if not payload:
        typer.echo("Skipping dividend: payload to render is null")
        raise typer.Exit(code=0)

    state = load_dividend_state()
    posted_keys = set(state["dividends"])
    
    payload = [
        record 
        for record in payload
        if f"{record['symbol']}:{record['ex_date']}" not in posted_keys
    ]

    if not payload:
        typer.echo("Skipping dividend: all records already posted")
        raise typer.Exit(code=0)

    paths = []
    path_to_record = {}

    for record in payload:
        symbol = record["symbol"].replace(".JK", "")

        path = renderer.render(
            data=record,
            filename=f"upcoming_dividend_{symbol.lower()}.png",
        )

        caption = (
            f"{symbol} dividend with historical data\n"
            "#IDX #Dividend #SectorsApp"
        )

        paths.append((path, caption))
        path_to_record[path] = record
        try:
            _queue_post("dividend", path, caption, content_type=f"dividend-{clean_slug(symbol)}")
        except Exception as error:
            typer.echo(f"Queue write failed for dividend {symbol}: {error}")

    if slack_channel:
        uploaded = upload_posts_to_slack(
            paths, slack_channel=slack_channel
        )

        for path, _ in uploaded:
            record = path_to_record[path]

            key = f"{record['symbol']}:{record['ex_date']}"
            state["dividends"][key] = {
                "posted_at": date.today().isoformat(),
                "symbol": record["symbol"],
                "ex_date": record["ex_date"],
            }

        if uploaded:
            save_dividend_state(state)
    

_VOLUME_SPIKE_TAGS = "#IDX #StockMarket #Indonesia #VolumeSpike #SectorsApp"


def _volume_spike_stats(df_spike):
    """Per-symbol trading stats matching what VolumeSpikeRenderer draws on the
    card, reshaped for the caption prompt (see summarizer.generate_volume_spike_caption)."""
    rows = []
    for _, row in df_spike.iterrows():
        net_idr = (row["foreign_buy_volume"] - row["foreign_sell_volume"]) * row["close"]
        rows.append({
            "symbol": str(row["symbol"]).replace(".JK", ""),
            "close_change_7d": (row.get("close_change_7d") or 0) * 100,
            "volume_ratio": row["volume_ratio"],
            "foreign_activity": row["foreign_activity"],
            "foreign_net_idr": net_idr,
        })
    return rows


@app.command("volume-spike")
def volume_spike(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel"),
    theme: str = typer.Option(
        "rotate", "--theme",
        help="red, blue, orange, green, or 'rotate' to auto-advance through all four",
    ),
):
    renderer = VolumeSpikeRenderer(output_dir=output)

    data = fetch_volume_spike_data()
    if not data or data["df_spike"].empty:
        typer.echo("Skipping volume-spike: no spikes detected today")
        raise typer.Exit(code=0)

    resolved_theme = _resolve_volume_spike_theme(theme)
    typer.echo(f"Rendering {len(data['df_spike'])} volume spike card(s)... (theme: {resolved_theme})")
    paths = renderer.render(data=data, theme=resolved_theme)
    for path in paths:
        typer.echo(path.resolve())

    rows = _volume_spike_stats(data["df_spike"])

    try:
        summarizer = NewsSummarizer()
    except Exception as error:
        typer.echo(f"LLM volume-spike caption disabled (summarizer init failed): {error}")
        summarizer = None

    caption = None
    if summarizer is not None:
        try:
            news_articles = None
            if len(rows) == 1:
                # Single symbol: ground the "why" in real reporting from the
                # run-up to today rather than letting the model invent a cause.
                since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                news_articles = fetch_news_for_symbol(rows[0]["symbol"], since=since)
            caption = summarizer.generate_volume_spike_caption(rows, news_articles)
        except Exception as error:
            typer.echo(f"Volume spike caption LLM failed: {error}")

    caption = f"{caption or 'Volume Spike Alert'}\n\n{_VOLUME_SPIKE_TAGS}"
    typer.echo("--- caption ---")
    typer.echo(caption)

    row = None
    try:
        row = _queue_post("volume-spike", paths, caption)
    except Exception as error:
        typer.echo(f"Queue write failed for volume-spike: {error}")
    _crosspost("volume-spike", row, caption, summarizer=summarizer)

    if slack_channel:
        posts = [(paths[0], caption)] + [(path, "Volume Spike Alert") for path in paths[1:]]
        upload_posts_to_slack(posts, slack_channel=slack_channel)


@app.command("anomaly-changes")
def anomaly_changes(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel"),
):
    renderer = AnomalyChangesRenderer(output_dir=output)

    data = fetch_anomaly_data()
    if not data or data["filtered_df"].empty:
        typer.echo("Skipping anomaly-changes: no anomalies detected today")
        raise typer.Exit(code=0)

    df = data["filtered_df"]
    n_up   = int((df["daily_close_change_delta"] > 0).sum())
    n_down = int((df["daily_close_change_delta"] < 0).sum())
    typer.echo(f"Rendering anomaly cards ({n_up} gainers, {n_down} losers)...")

    paths = renderer.render(data=data)
    for path in paths:
        typer.echo(path.resolve())

    if slack_channel:
        posts = [
            (path, "Anomaly Movers — Stocks outperforming or underperforming peers by 15%+\n\n#IDX #StockMarket #Indonesia #SectorsApp")
            for path in paths
        ]
        upload_posts_to_slack(posts, slack_channel=slack_channel)


def _crosspost_weekly_market(foreign_flow_image_urls: list[str]) -> None:
    """Combine Friday's broker-weekly IG row (its own, separately-scheduled
    workflow) with foreign-flow's own images into ONE "Weekly Update" Threads
    post. foreign-flow runs the following morning (Saturday 08:00 WIB vs
    broker-weekly's Friday 18:45), so it's always the later trigger - this
    fires even on a week with no foreign-flow data, since broker-weekly
    should still get its post."""
    from .social_queue import _client, TABLE, parse_image_urls

    since = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    combined = []
    try:
        client = _client()
        # broker-weekly is a single row per run - exact content_type match.
        result = (
            client.table(TABLE)
            .select("image_url")
            .eq("platform", "ig")
            .eq("content_type", "broker-weekly")
            .gte("created_at", f"{since}T00:00:00")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            combined.extend(parse_image_urls(result.data[0].get("image_url")))
    except Exception as error:
        typer.echo(f"Threads crosspost lookup failed for broker-weekly: {error}")

    combined.extend(foreign_flow_image_urls)
    if not combined:
        return
    try:
        crosspost_to_threads("foreign-flow", combined, None)
    except Exception as error:
        typer.echo(f"Threads crosspost failed for foreign-flow/weekly-market: {error}")


@app.command("foreign-flow")
def foreign_flow(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel"),
):
    renderer = ForeignFlowRenderer(output_dir=output)

    data = fetch_foreign_flow_data()
    own_image_urls = []
    if not data or (not data.get("net_buy") and not data.get("net_sell")):
        typer.echo("Skipping foreign-flow: no foreign flow data")
    else:
        paths = renderer.render(data=data)
        for path in paths:
            typer.echo(path.resolve())

        flow_caption = "Where foreign money moved this week\n\n#IDX #StockMarket #Indonesia #ForeignFlow #SectorsApp"
        for i, path in enumerate(paths):
            try:
                row = _queue_post("foreign-flow", path, flow_caption, content_type=f"foreign-flow-{i + 1}")
                if row:
                    own_image_urls.extend(row.get("image_url") or [])
            except Exception as error:
                typer.echo(f"Queue write failed for foreign-flow page {i + 1}: {error}")

        if slack_channel:
            posts = [(path, flow_caption) for path in paths]
            upload_posts_to_slack(posts, slack_channel=slack_channel)

    _crosspost_weekly_market(own_image_urls)


@app.command("ownership")
def ownership(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel"),
    limit: int = typer.Option(1, "--limit", help="Max ownership carousels to post this run."),
):
    renderer = OwnershipRenderer(output_dir=output)

    df = fetch_company_report_ownership()
    posts = select_ownership_posts(df)   # sorted by market-cap rank (recognizable first)
    if not posts:
        typer.echo("Skipping ownership: no single-entity-holding-70 names")
        raise typer.Exit(code=0)

    state = load_ownership_state()
    fires = select_ownership_fires(posts, state)[:limit]
    if not fires:
        typer.echo("Skipping ownership: nothing new to post (all posted, none changed)")
        raise typer.Exit(code=0)

    typer.echo(f"Rendering {len(fires)} ownership carousel(s)...")
    all_paths = []
    slide_owner = {}
    for post in fires:
        slides = renderer.render(post)
        base = str(post["symbol"]).upper().split(".")[0]
        caption = (
            f"Who really owns {base}?\n\n#IDX #StockMarket #Indonesia #Ownership #SectorsApp"
        )
        for path in slides:
            typer.echo(path.resolve())
            all_paths.append((path, caption))
            slide_owner[path] = post

    if slack_channel:
        uploaded = upload_posts_to_slack(all_paths, slack_channel=slack_channel)

        # Only burn state for names whose slides actually went out.
        posted, seen = [], set()
        for path, _ in uploaded:
            post = slide_owner.get(path)
            if post is not None and id(post) not in seen:
                seen.add(id(post))
                posted.append(post)
        for post in posted:
            record_ownership(state, post, date.today())
        if posted:
            save_ownership_state(state)


@app.command("ownership-board")
def ownership_board(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel"),
    top_n: int = typer.Option(10, "--top-n", help="How many companies on the leaderboard."),
):
    renderer = OwnershipBoardRenderer(output_dir=output)

    state = load_ownership_board_state()
    key = board_period_key(date.today())
    if board_already_posted(state, key):
        typer.echo(f"Skipping ownership-board: already posted for {key}")
        raise typer.Exit(code=0)

    df = fetch_company_report_ownership()
    posts = select_ownership_posts(df)
    if not posts:
        typer.echo("Skipping ownership-board: no single-entity-holding-70 names")
        raise typer.Exit(code=0)

    paths = renderer.render(posts, top_n=top_n)
    for path in paths:
        typer.echo(path.resolve())

    if slack_channel:
        caption = (
            "Indonesian companies almost entirely owned by one shareholder\n\n"
            "#IDX #StockMarket #Indonesia #Ownership #SectorsApp"
        )
        uploaded = upload_posts_to_slack([(p, caption) for p in paths], slack_channel=slack_channel)
        if uploaded:
            board = sorted(posts[:top_n], key=lambda p: p["controller"]["pct"] or 0, reverse=True)
            symbols = [str(p["symbol"]).upper().split(".")[0] for p in board]
            record_board(state, key, symbols, date.today())
            save_ownership_board_state(state)


@app.command("macro-news")
def macro_news(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel"),
    render_scale: float = typer.Option(1.0, "--render-scale"),
    since: str | None = typer.Option(None, "--since", help="YYYY-MM-DD; defaults to today"),
):
    today = datetime.now()
    period_label = f"{today.strftime('%Y-%m-%d')}"

    summarizer = NewsSummarizer()
    renderer = MacroNewsRenderer(
        template_path=BACKGROUND_DIR / "IDX - News 1.png",
        period_label=period_label,
        output_dir=output,
        render_scale=render_scale,
    )

    since_dt = datetime.strptime(since, "%Y-%m-%d") if since else None
    records = fetch_macro_news(th_score=80, since=since_dt)

    if not records: 
        typer.echo("Skipping macro-news: no records found")
        raise typer.Exit(code=0)

    records = sorted(
        records, 
        key=lambda record: record['score'],
        reverse=True
    )

    slides = []

    for record in records[:1]:
        source = tldextract.extract(record['source'])

        slide = summarizer.generate_macro_slide(
            title=record['title'],
            body=record['body'],
            tags=record['tags'],
        )

        if not slide:
            continue

        slide['source'] = source.domain

        slides.append(slide)
        time.sleep(5)

    if not slides:
        typer.echo("Skipping macro-news: no records found")
        raise typer.Exit(code=0)

    paths = []

    for index, slide in enumerate(slides):
        path = renderer.render(
            data=slide,
            filename=f'macro_news_test_{index + 1}.png',
        )

        typer.echo(path.resolve())
        paths.append(path)

        headline = " ".join(slide.get("headline_lines") or [])
        body = slide.get("body") or ""
        insight = slide.get("insight") or ""
        slide_caption = "\n\n".join(part for part in [headline, body, insight] if part) or "Macro News"
        slide_caption = f"{slide_caption}\n\n#IDX #StockMarket #Indonesia #MacroNews #SectorsApp"
        try:
            _queue_post("macro-news", path, slide_caption, content_type=f"macro-news-{index + 1}")
        except Exception as error:
            typer.echo(f"Queue write failed for macro-news slide {index + 1}: {error}")

    if slack_channel and paths:
        caption = "Macro News\n\n#IDX #StockMarket #Indonesia #MacroNews #SectorsApp"
        posts = [(paths[0], caption), *paths[1:]]

        upload_posts_to_slack(posts, slack_channel=slack_channel)


_STOCK_PERF_TAGS = "#IDX #StockMarket #Indonesia #StockPerformance #SectorsApp"


def _pick_index_driver(index_return, records, day):
    """The constituent that tells the "diverging from the index" story:
    when the index is down, that's whoever is defying the trend hardest
    (best return - a resilience story); when the index is up, it's whoever
    is lagging hardest (worst return) - not just the biggest gap in either
    direction, which would as easily surface an underperformer-among-losers
    as a stock actually bucking the broader trend. Pairs with the gainers
    image (generate_index_driver_caption).
    """
    if index_return is None or not records:
        return None
    return_key = f"return_{day}d"
    picker = max if index_return <= 0 else min
    driver = picker(records, key=lambda r: r.get(return_key) or 0)
    return {
        "symbol": str(driver["symbol"]).replace(".JK", ""),
        "company_name": driver.get("company_name"),
        "return": driver.get(return_key) or 0.0,
    }


def _pick_index_laggard(records, day):
    """The single worst-performing constituent, full stop - the "biggest
    drop" name the losers image itself is built around, regardless of which
    way the index moved. Pairs with the losers image
    (generate_index_laggard_caption); unlike _pick_index_driver this isn't
    direction-aware because the losers slide's own framing already is.
    """
    if not records:
        return None
    return_key = f"return_{day}d"
    laggard = min(records, key=lambda r: r.get(return_key) or 0)
    return {
        "symbol": str(laggard["symbol"]).replace(".JK", ""),
        "company_name": laggard.get("company_name"),
        "return": laggard.get(return_key) or 0.0,
    }


def _crosspost_stock_performance(day: int, today: datetime) -> None:
    """Combine this cadence's per-index IG posts (LQ45/IDXBUMN20/JII70,
    generated on 3 separate days) into ONE Threads carousel - see the
    stock_performance() call site above for why."""
    from .social_queue import _client, TABLE, parse_image_urls

    lookback_days = 3
    since = (today - timedelta(days=lookback_days)).strftime("%Y-%m-%dT00:00:00")
    try:
        client = _client()
        result = (
            client.table(TABLE)
            .select("image_url,created_at")
            .eq("platform", "ig")
            .like("content_type", "stock-performance-%")
            .gte("created_at", since)
            .order("created_at")
            .execute()
        )
    except Exception as error:
        typer.echo(f"Threads crosspost lookup failed for stock-performance: {error}")
        return

    image_urls = []
    for row in result.data or []:
        image_urls.extend(parse_image_urls(row.get("image_url")))

    if not image_urls:
        return

    try:
        crosspost_to_threads("stock-performance", image_urls, None)
    except Exception as error:
        typer.echo(f"Threads crosspost failed for stock-performance: {error}")


@app.command("stock-performance")
def stock_performance(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel"),
    target_indices: list[str] = typer.Option(["LQ45", "JII70", "IDXBUMN20"], "--target-indices"),
    render_scale: float = typer.Option(1.0, "--render-scale"),
    day: int = typer.Option(7, "--day"),
):
    renderer = StockPerformanceRenderer(
        template_path=BACKGROUND_DIR / "volume_spike.png",
        render_scale=render_scale,
        output_dir=output,
    )

    today = datetime.now()

    indices_performance = fetch_index_performance(
        target_indices=target_indices,
        day=day,
    )

    companies = fetch_stock_indices(target_indices)
    companies = fetch_stock_performance(companies=companies, day=day)
    data_indices = group_companies_by_index(companies)

    try:
        summarizer = NewsSummarizer()
    except Exception as error:
        typer.echo(f"LLM index-driver caption disabled (summarizer init failed): {error}")
        summarizer = None

    # One post per index per run - which framing depends on how rough the
    # index's own move was. A steep drop (< -2.5%) makes "who's diverging
    # from the trend" a strange lead story; "biggest drops" (the full
    # laggard board) is the more honest one. Anything milder - flat, up, or
    # a shallow dip - flips back to "index drivers" (who's bucking/lagging
    # the trend), which needs an actual trend to diverge from to be
    # interesting.
    DROP_THRESHOLD_PCT = -2.5

    for company_index in target_indices:
        return_key = f"return_{day}d"
        index_return = indices_performance.get(company_index)
        since = (today - timedelta(days=day * 2)).strftime("%Y-%m-%d")

        use_biggest_drops = index_return is not None and index_return < DROP_THRESHOLD_PCT
        direction = "losers" if use_biggest_drops else "gainers"

        records = sorted(
            data_indices[company_index],
            key=lambda record: record[return_key],
            reverse=not use_biggest_drops,
        )

        path = renderer.render(
            index_name=company_index,
            records=records,
            index_performance=index_return,
            as_of_date=today.strftime("%Y-%m-%d"),
            filename=f"{day}_stock_performance_{direction}_{company_index.lower()}.png",
            direction=direction,
            day=day,
        )
        typer.echo(path.resolve())

        caption = None
        if summarizer is not None and index_return is not None:
            try:
                if use_biggest_drops:
                    laggard = _pick_index_laggard(data_indices[company_index], day)
                    if laggard:
                        news_articles = fetch_news_for_symbol(laggard["symbol"], since=since)
                        caption = summarizer.generate_index_laggard_caption(
                            company_index, index_return, day, laggard, news_articles
                        )
                else:
                    driver = _pick_index_driver(index_return, data_indices[company_index], day)
                    if driver:
                        news_articles = fetch_news_for_symbol(driver["symbol"], since=since)
                        caption = summarizer.generate_index_driver_caption(
                            company_index, index_return, day, driver, news_articles
                        )
            except Exception as error:
                kind = "laggard" if use_biggest_drops else "driver"
                typer.echo(f"Index {kind} caption LLM failed for {company_index}: {error}")

        default_caption = f"{company_index} Losers" if use_biggest_drops else "Stock Performance"
        caption = f"{caption or default_caption}\n\n{_STOCK_PERF_TAGS}"
        typer.echo(f"--- {company_index} {direction} caption ---")
        typer.echo(caption)

        try:
            _queue_post(
                "stock-performance", path, caption,
                content_type=f"stock-performance-{direction}-{clean_slug(company_index)}",
            )
        except Exception as error:
            typer.echo(f"Queue write failed for stock-performance {company_index}: {error}")

        if slack_channel:
            upload_posts_to_slack([(path, caption)], slack_channel=slack_channel)

    # Threads gets ONE combined post per cadence instead of the 3 separate
    # per-index posts IG receives across the week/month - see
    # threads_routing.py's "market_performance" policy: "don't separate by
    # index, combine it into one". Only fires on the last day of each
    # cadence (Friday for the weekly 7-day view, the 3rd of the month for
    # the monthly 30-day view) - the per-index cron dispatch runs LQ45 ->
    # IDXBUMN20 -> JII70 across the preceding days, so by then all 3 of
    # that cadence's IG rows already exist to combine.
    is_weekly_combine_day = day <= 7 and today.weekday() == 4
    is_monthly_combine_day = day > 7 and today.day == 3
    if is_weekly_combine_day or is_monthly_combine_day:
        _crosspost_stock_performance(day, today)


@app.command("weekly-movers")
def weekly_movers(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel"),
):
    renderer = WinnersLosersRenderer(output_dir=output)

    data = fetch_weekly_movers_data()
    if not data or (not data.get("winners") and not data.get("losers")):
        typer.echo("Skipping weekly-movers: no data")
        raise typer.Exit(code=0)

    typer.echo(
        f"Rendering weekly movers ({len(data.get('winners', []))} winners, "
        f"{len(data.get('losers', []))} losers) over {data.get('trading_days')} trading days..."
    )
    path = renderer.render(data=data)
    typer.echo(path.resolve())

    if slack_channel:
        caption = (
            "Week's Winners & Losers — top 100 by market cap\n\n"
            "#IDX #StockMarket #Indonesia #SectorsApp"
        )
        upload_posts_to_slack([(path, caption)], slack_channel=slack_channel)


@app.command("sector-heatmap")
def sector_heatmap(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel"),
):
    renderer = SectorHeatmapRenderer(output_dir=output)

    data = fetch_weekly_sector_data()
    if not data or not data.get("sectors"):
        typer.echo("Skipping sector-heatmap: no data")
        raise typer.Exit(code=0)

    typer.echo(
        f"Rendering sector heat map ({len(data['sectors'])} sectors, "
        f"{data.get('trading_days')} trading days)..."
    )
    path = renderer.render(data=data)
    typer.echo(path.resolve())

    if slack_channel:
        caption = (
            "IDX Sector Heat Map — weekly performance by sector\n\n"
            "#IDX #StockMarket #Indonesia #SectorsApp"
        )
        upload_posts_to_slack([(path, caption)], slack_channel=slack_channel)


@app.command("lq45-ytd")
def lq45_ytd(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel"),
    direction: str = typer.Option("worst", "--direction", help="'worst' or 'best'"),
):
    renderer = LQ45YTDRenderer(output_dir=output)

    data = fetch_lq45_ytd_data(direction=direction)
    if not data or not data.get("rows"):
        typer.echo("Skipping lq45-ytd: no data")
        raise typer.Exit(code=0)

    typer.echo(f"Rendering LQ45 {direction} YTD ({len(data['rows'])} rows)...")
    path = renderer.render(data=data)
    typer.echo(path.resolve())

    if slack_channel:
        verb = "Worst" if direction == "worst" else "Best"
        caption = (
            f"{verb} YTD performers in LQ45 — based on year-to-date close prices\n\n"
            "#IDX #LQ45 #StockMarket #Indonesia #SectorsApp"
        )
        upload_posts_to_slack([(path, caption)], slack_channel=slack_channel)


@app.command("insider-roundup")
def insider_roundup(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel"),
):
    renderer = InsiderRoundupRenderer(output_dir=output)

    data = fetch_weekly_insider_aggregates()
    if not data or (not data.get("buys") and not data.get("sells")):
        typer.echo("Skipping insider-roundup: no data")
        raise typer.Exit(code=0)

    typer.echo(
        f"Rendering insider roundup ({len(data.get('buys', []))} buys, "
        f"{len(data.get('sells', []))} sells, {data.get('n_filings')} filings)..."
    )
    path = renderer.render(data=data)
    typer.echo(path.resolve())

    if slack_channel:
        caption = (
            "Insider Action This Week — top stocks insiders bought and sold\n\n"
            "#IDX #InsiderTrading #Indonesia #SectorsApp"
        )
        upload_posts_to_slack([(path, caption)], slack_channel=slack_channel)


if __name__ == "__main__":
    app()
