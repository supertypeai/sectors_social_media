import json
import os
from pathlib import Path
import pandas as pd

FILINGS_COLUMNS = [
    "source",
    "created_at",
    "symbol",
    "title",
    "tags",
    "price",
    "transaction_value",
    "holding_before",
    "holding_after",
    "share_percentage_before",
    "share_percentage_after",
    "share_percentage_transaction",
    "holder_name",
    "context",
    "price_transaction",
]


NEWS_COLUMNS = [
    "id",
    "source",
    "url",
    "created_at",
    "title",
    "summary",
    "description",
    "content",
    "body",
    "tags",
    "tickers",
    "ticker",
    "symbol",
]


def load_records(path):
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".json", ".jsonl"}:
        if path.suffix.lower() == ".jsonl":
            return pd.read_json(path, lines=True)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return pd.DataFrame(payload)
    raise ValueError(f"Unsupported input format: {path.suffix}")


def _supabase_client():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ModuleNotFoundError:
        pass

    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required to fetch from Supabase.")

    return create_client(url, key)


def _select_existing_columns(df, columns):
    existing_columns = [column for column in columns if column in df.columns]
    if not existing_columns:
        return df
    return df[existing_columns]


def fetch_supabase_table(
    table_name: str,
    since_column: str | None = None,
    since_value=None,
    columns: str = "*",
    symbol_column: str | None = None,
    symbol_value=None,
    order_column: str | None = None,
    order_desc: bool = True,
    limit: int | None = None,
    query_modifier=None,
):
    query = _supabase_client().table(table_name).select(columns)

    if since_column and since_value:
        query = query.gte(since_column, since_value)

    if symbol_column and symbol_value:
        query = query.eq(symbol_column, symbol_value)

    if order_column:
        query = query.order(order_column, desc=order_desc)

    if limit:
        query = query.limit(limit)

    if query_modifier is not None:
        query = query_modifier(query)

    response = query.execute()
    return pd.DataFrame(response.data)


def fetch_filings(since=None):
    if since is None:
        from datetime import datetime, timedelta
        since = (datetime.now() - timedelta(hours=24)).isoformat()
    df = fetch_supabase_table("idx_filings", since_column="created_at", since_value=since)
    return _select_existing_columns(df, FILINGS_COLUMNS)


def fetch_news(since=None):
    if since is None:
        from datetime import datetime, timedelta
        since = (datetime.now() - timedelta(hours=24)).isoformat()
    df = fetch_supabase_table("idx_news", since_column="created_at", since_value=since)
    return _select_existing_columns(df, NEWS_COLUMNS)


def fetch_company_profiles():
    df = fetch_supabase_table("idx_company_profile", columns="symbol, company_name")
    if df.empty:
        return {}
    return df.set_index("symbol")["company_name"].to_dict()


def fetch_workflow_data(
    columns: str,
    table_name: str = "idx_workflow_data", 
    is_output_json: bool = False, 
    required_columns: list[str] = ['quarterly_low']
) -> pd.DataFrame | list[dict]:
    workflow_df = fetch_supabase_table(
        table_name=table_name,
        columns=columns,
         query_modifier=lambda query: query.or_(
            ",".join(f"{column_name}.not.is.null" for column_name in required_columns)
        ),
    )

    if is_output_json:
        return workflow_df.to_dict(orient="records")

    return workflow_df


def fetch_company_report():
    company_report_df = fetch_supabase_table(
        table_name="idx_company_report",
        columns="symbol, market_cap",
        query_modifier=lambda query: query.lte("market_cap_rank", 50),
    )

    return company_report_df


def fetch_ihsg_weekly_data():
    ihsg_df = fetch_supabase_table(
        table_name="index_daily_data",
        columns="date, index_code, price",
        query_modifier=lambda query: query
            .eq("index_code", "IHSG")
            .order("date", desc=True)
            .limit(6),
    )

    return ihsg_df.to_dict(orient="records")

