from datetime import timedelta, date
from typing import Optional 

from .data import fetch_idx_daily_data

import pandas as pd
import ast
import json
import bisect 


IMPORTANT_FILINGS_TAGS = {
    "takeover",
    "capital-restructuring",
    "repurchase-agreement",
    "free_float_compliance",
    "mesop",
}

TIER_1_NEWS_TAGS = {
    "IPO",
    "Mergers & Acquisitions",
    "Dividend Announcement",
    "Stock Buyback",
    "Stock Split",
    "Rights Issue",
    "Insider Trading",
    "Trading Halt",
    "Suspension",
    "Delisting",
}

TIER_2_NEWS_TAGS = {
    "Executive Changes",
    "Business Expansion",
    "Joint Venture",
    "MoU",
    "Private Placement",
    "Oversubscribed",
    "Ownership",
    "Shareholders General Meeting",
    "Violation",
    "Foreign Investment",
    "OJK",
    "Government Policy",
}

IMPORTANT_NEWS_TAGS = TIER_1_NEWS_TAGS | TIER_2_NEWS_TAGS


def parse_tags(value):
    if isinstance(value, list):
        return [str(tag) for tag in value]
    if pd.isna(value):
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(text)
                if isinstance(parsed, list):
                    return [str(tag) for tag in parsed]
            except Exception:
                pass
        return [part.strip() for part in text.split(",") if part.strip()]
    return []


def extract_context_pattern(context):
    text = str(context or "").lower()
    if "bought" in text or "buy" in text:
        return "Cluster Buy"
    if "sell" in text or "sold" in text:
        return "Cluster Sell"
    return "Context"


def add_parsed_tags(df):
    df = df.copy()
    df["tags_parsed"] = df.get("tags", pd.Series(index=df.index, dtype=object)).apply(parse_tags)
    return df


def filter_daily_filings(df, now=None, hours=24, min_transaction_value=100_000_000, min_share_pct=0.5):
    df = df.copy()
    if df.empty:
        return df
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    if now is None:
        now = pd.Timestamp.now(tz="UTC")
    since = now - timedelta(hours=hours)
    return df[
        (df["created_at"] >= since)
        & (pd.to_numeric(df["transaction_value"], errors="coerce") > min_transaction_value)
        & (pd.to_numeric(df["share_percentage_transaction"], errors="coerce") >= min_share_pct)
    ].sort_values("transaction_value", ascending=False)


def group_context_filings(df):
    if df.empty or "context" not in df.columns:
        return []
    df = df[df["context"].notna() & (df["context"].astype(str).str.strip() != "")].copy()
    if df.empty:
        return []

    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    df["context_pattern"] = df["context"].apply(extract_context_pattern)
    groups = []
    for (symbol, pattern), group in df.sort_values("created_at").groupby(["symbol", "context_pattern"]):
        latest = group.iloc[-1].to_dict()
        groups.append(
            {
                "symbol": symbol,
                "context_pattern": pattern,
                "count": len(group),
                "holders": sorted(set(group["holder_name"].dropna().astype(str))),
                "latest": latest,
                "transactions": group.to_dict("records"),
            }
        )
    return sorted(groups, key=lambda row: row["latest"].get("created_at") or pd.Timestamp.min, reverse=True)


def filter_tagged_filings(df):
    df = add_parsed_tags(df)
    if df.empty:
        return df
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    mask = df["tags_parsed"].apply(lambda tags: bool(set(tags) & IMPORTANT_FILINGS_TAGS))
    return df[mask].sort_values("created_at", ascending=False)


def news_tier(tags):
    parsed = set(parse_tags(tags))
    if parsed & TIER_1_NEWS_TAGS:
        return "Tier 1"
    if parsed & TIER_2_NEWS_TAGS:
        return "Tier 2"
    return "Other"


def classify_news(df):
    df = add_parsed_tags(df)
    if df.empty:
        df["tier"] = []
        return df
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    df["tier"] = df["tags_parsed"].apply(news_tier)
    return df[df["tier"] != "Other"].sort_values(["tier", "created_at"], ascending=[True, False])


def filter_recent_news(df, now=None, hours=24):
    if df.empty or "created_at" not in df.columns:
        return df
    df = df.copy()
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    if now is None:
        now = pd.Timestamp.now(tz="UTC")
    since = now - timedelta(hours=hours)
    return df[df["created_at"] >= since]


def prepare_data_by_mcap(
    df_workflow: pd.DataFrame, 
    df_company_report: pd.DataFrame
) -> list[dict]:
    workflow_by_symbol = {
        row["symbol"]: row
        for row in df_workflow.to_dict(orient="records")
    }

    result = []
    for company in df_company_report.to_dict(orient="records"):
        symbol = company["symbol"]
        
        if symbol in workflow_by_symbol:
            result.append(workflow_by_symbol[symbol])

    return result


def select_quarterly_data(
    data_ihsg: list[dict], 
    data_workflow: list[dict]
) -> list[dict]: 
    prices = [record.get('price') for record in data_ihsg]

    price_today = prices[0]
    price_last_week = prices[-1]

    weekly_return = (price_today - price_last_week) / price_last_week

    if weekly_return <= -0.02:
        return [row for row in data_workflow if row.get("quarterly_low") is not None]
    
    return [row for row in data_workflow if row.get("quarterly_high") is not None]


def get_closest_price_to_date(
    daily_records: list[dict],
    target_date: str
) -> float | None:
    if not daily_records:
        return None

    dates = [record["date"] for record in daily_records]
    position = bisect.bisect_left(dates, target_date)

    if position == 0:
        return daily_records[0]["close"]
    
    if position >= len(dates):
        return daily_records[-1]["close"]

    days_to_before = (
        date.fromisoformat(target_date) - date.fromisoformat(dates[position - 1])
    ).days

    days_to_after = (
        date.fromisoformat(dates[position]) - date.fromisoformat(target_date)
    ).days

    if days_to_after <= days_to_before:
        return daily_records[position]["close"]
    
    return daily_records[position - 1]["close"]


def compute_yield_growth(
    current_yield: float,
    historical_dividends: dict,
    announcement_year: int
) -> float | None:
    sorted_years = sorted(historical_dividends.keys())

    prior_year = None

    for year in reversed(sorted_years):
        if int(year) < announcement_year:
            prior_year = year
            break

    if prior_year is None:
        return None

    prior_year_total_yield = historical_dividends[prior_year].get("total_yield")

    if not prior_year_total_yield:
        return None

    print(f'prior year yield: {prior_year_total_yield}')
    return (current_yield - prior_year_total_yield) / prior_year_total_yield


def prepare_data_upcoming_dividend(
    upcoming_dividends: list[dict],
    company_reports: list[dict],
    min_yield_growth: float = 0.0
) -> list[dict]:
    lookup_upcoming_dividend = {
        record['symbol']: record
        for record in upcoming_dividends
    }

    lookback_date = (date.today() - timedelta(days=30)).isoformat()
    enriched_reports = []

    for company_report in company_reports:
        symbol = company_report.get('symbol')
        historical_dividends = company_report.get('historical_dividends')
        yield_ttm = company_report.get('yield_ttm')

        if (
            symbol not in lookup_upcoming_dividend 
            or historical_dividends is None
            or yield_ttm < 0.1
        ):
            continue

        upcoming_dividend_record = lookup_upcoming_dividend[symbol]
        dividend_amount = upcoming_dividend_record.get('dividend_amount')
        cum_date = upcoming_dividend_record.get('cum_date')
        ex_date = upcoming_dividend_record.get('ex_date')

        if not all([dividend_amount, cum_date, ex_date]):
            continue

        announcement_year = date.fromisoformat(ex_date).year

        # idx daily data have 1m+ records, i found it unefficient to fetch all and create a hash map
        # so this fetching is inside loop, which i think more reasonable
        daily_records = fetch_idx_daily_data(symbol, lookback_date)
        close_price = get_closest_price_to_date(daily_records, cum_date)

        if not close_price:
            continue

        current_yield = dividend_amount / close_price
        print(f'symbol: {symbol} | close price: {close_price} | current yield: {current_yield}')

        yield_growth = compute_yield_growth(
            current_yield, historical_dividends, announcement_year
        )

        if yield_growth is None or yield_growth < min_yield_growth:
            continue

        enriched_reports.append({
            **company_report,
            **upcoming_dividend_record,
            'current_yield': current_yield,
            'yield_growth': yield_growth,
        })

    return enriched_reports

