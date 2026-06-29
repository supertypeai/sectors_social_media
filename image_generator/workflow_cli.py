from pathlib import Path
from datetime import date, datetime
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
from .render import BACKGROUND_DIR
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

    if slack_channel:
        upload_posts_to_slack(
            [(path, "Top movers update\n\n#IDX #StockMarket #Indonesia #SectorsApp")],
            slack_channel=slack_channel,
        )


@app.command("agm")
def agm(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel"),
):
    renderer = AGMRenderer(output_dir=output)

    df = fetch_agm_data()
    if df.empty:
        typer.echo("Skipping agm: no data for today")
        raise typer.Exit(code=0)

    typer.echo(f"Rendering {len(df)} AGM card(s)...")
    paths = renderer.render(data=df)
    for path in paths:
        typer.echo(path.resolve())

    if slack_channel:
        posts = [
            (path, "AGM Results\n\n#IDX #StockMarket #Indonesia #AGM #SectorsApp")
            for path in paths
        ]
        upload_posts_to_slack(posts, slack_channel=slack_channel)


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

    if slack_channel:
        posts = [
            (path, "Upcoming Dividends\n\n#IDX #StockMarket #Indonesia #Dividends #SectorsApp")
            for path in paths
        ]
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
    

@app.command("volume-spike")
def volume_spike(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel"),
):
    renderer = VolumeSpikeRenderer(output_dir=output)

    data = fetch_volume_spike_data()
    if not data or data["df_spike"].empty:
        typer.echo("Skipping volume-spike: no spikes detected today")
        raise typer.Exit(code=0)

    typer.echo(f"Rendering {len(data['df_spike'])} volume spike card(s)...")
    paths = renderer.render(data=data)
    for path in paths:
        typer.echo(path.resolve())

    if slack_channel:
        posts = [
            (path, "Volume Spike Alert\n\n#IDX #StockMarket #Indonesia #VolumeSpike #SectorsApp")
            for path in paths
        ]
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


@app.command("foreign-flow")
def foreign_flow(
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    slack_channel: str | None = typer.Option(None, "--slack-channel"),
):
    renderer = ForeignFlowRenderer(output_dir=output)

    data = fetch_foreign_flow_data()
    if not data or (not data.get("net_buy") and not data.get("net_sell")):
        typer.echo("Skipping foreign-flow: no foreign flow data")
        raise typer.Exit(code=0)

    paths = renderer.render(data=data)
    for path in paths:
        typer.echo(path.resolve())

    if slack_channel:
        posts = [
            (path, "Where foreign money moved this week\n\n#IDX #StockMarket #Indonesia #ForeignFlow #SectorsApp")
            for path in paths
        ]
        upload_posts_to_slack(posts, slack_channel=slack_channel)


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
):
    today = datetime.now()
    period_label = f"{today.strftime("%Y-%m-%d")}"

    summarizer = NewsSummarizer()
    renderer = MacroNewsRenderer(
        template_path=BACKGROUND_DIR / "IDX - News 1.png",
        period_label=period_label,
        output_dir=output,
        render_scale=render_scale,
    )

    records = fetch_macro_news(th_score=70)

    if not records: 
        typer.echo("Skipping macro-news: no records found")
        raise typer.Exit(code=0)

    records = sorted(
        records, 
        key=lambda record: record['score'],
        reverse=True
    )

    slides = []

    for record in records:
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

    if slack_channel and paths:
        caption = "Macro News\n\n#IDX #StockMarket #Indonesia #MacroNews #SectorsApp"
        posts = [(paths[0], caption), *paths[1:]]

        upload_posts_to_slack(posts, slack_channel=slack_channel)


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

    paths = []

    for company_index in target_indices:
        return_key = f"return_{day}d"

        records_gainers = sorted(
            data_indices[company_index],
            key=lambda record: record[return_key],
            reverse=True,
        )

        records_losers = sorted(
            data_indices[company_index],
            key=lambda record: record[return_key],
            reverse=False,
        )

        path_gainers = renderer.render(
            index_name=company_index,
            records=records_gainers,
            index_performance=indices_performance.get(company_index),
            as_of_date=today.strftime("%Y-%m-%d"),
            filename=f"{day}_stock_performance_gainers_{company_index.lower()}.png",
            direction="gainers",
            day=day,
        )

        path_losers = renderer.render(
            index_name=company_index,
            records=records_losers,
            as_of_date=today.strftime("%Y-%m-%d"),
            index_performance=indices_performance.get(company_index),
            filename=f"{day}_stock_performance_losers_{company_index.lower()}.png",
            direction="losers",
            day=day,
        )

        paths.append(path_gainers)
        paths.append(path_losers)

    for path in paths:
        typer.echo(path.resolve())

    if slack_channel and paths:
        caption = "Stock Performance\n\n#IDX #StockMarket #Indonesia #StockPerformance #SectorsApp"
        posts = [(paths[0], caption), *paths[1:]]
        upload_posts_to_slack(posts, slack_channel=slack_channel)


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
