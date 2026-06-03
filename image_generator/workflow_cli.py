from pathlib import Path

from .classification import prepare_data_by_mcap, select_quarterly_data
from .data import fetch_company_report, fetch_workflow_data, fetch_ihsg_weekly_data
from .renderers.quarterly import QuarterlyRenderer
from .renderers.top_movers import TopCompaniesMoversRenderer
from .utils.slack import upload_posts_to_slack 

import typer


app = typer.Typer(help="Generate workflow-data social images.")


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


if __name__ == "__main__":
    app()