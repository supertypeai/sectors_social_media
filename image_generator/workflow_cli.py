from pathlib import Path
from datetime import date 

from .renderers.quarterly import QuarterlyRenderer
from .renderers.top_movers import TopCompaniesMoversRenderer
from .renderers.upcoming_dividend import UpcomingDividendRenderer
from .renderers.agm import AGMRenderer
from .renderers.dividend import DividendRenderer
from .renderers.volume_spike import VolumeSpikeRenderer
from .renderers.anomalies_changes import AnomalyChangesRenderer
from .renderers.foreign_flow import ForeignFlowRenderer
from .renderers.winners_losers import WinnersLosersRenderer
from .utils.slack import upload_posts_to_slack
from .classification import (
    prepare_data_by_mcap, 
    select_quarterly_data, 
    prepare_data_upcoming_dividend
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
    fetch_weekly_movers_data,
)
from .utils.io_helper import load_dividend_state, save_dividend_state

import typer


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


if __name__ == "__main__":
    app()

