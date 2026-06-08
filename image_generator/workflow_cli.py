from pathlib import Path

from .renderers.quarterly import QuarterlyRenderer
from .renderers.top_movers import TopCompaniesMoversRenderer
from .renderers.upcoming_dividend import UpcomingDividendRenderer
from .renderers.agm import AGMRenderer
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
    fetch_upcoming_dividends
)
from .renderers.quarterly import QuarterlyRenderer
from .renderers.top_movers import TopCompaniesMoversRenderer
from .renderers.dividend import DividendRenderer
from .utils.slack import upload_posts_to_slack 

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
    )

    df_company_report = fetch_company_report()
    payload_ihsg_weekly = fetch_ihsg_weekly_data()

    payload_workflow = prepare_data_by_mcap(df_workflow, df_company_report)

    payload = select_quarterly_data(payload_ihsg_weekly, payload_workflow)

    if not payload or len(payload) < 16:
        typer.echo("Skipping quarterly: not enough data")
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

    paths = []

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
    
    if slack_channel:
        upload_posts_to_slack(
            paths,
            slack_channel=slack_channel,
        )


if __name__ == "__main__":
    app()

