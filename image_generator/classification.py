import ast
import json
import re
from datetime import timedelta

import pandas as pd


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








EXCLUDED_PLAIN_FILINGS_TAGS = {"mesop", "takeover"}


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


# ---------------------------------------------------------------------------
# Multi-holder clusters (the proper "cluster" pattern):
#   >= 3 DISTINCT insiders buying/selling the SAME symbol inside a rolling
#   6-month window. Mirrors the upstream rule that generates the
#   "N insiders bought <SYM> in the last 6 months." context strings.
# ---------------------------------------------------------------------------

MAX_SANE_PRICE = 1_000_000  # IDR/share; guards against corrupt price_transaction rows




















# ---------------------------------------------------------------------------
# Single-holder chains (the "chain" pattern):
#   ONE insider trading the SAME symbol+direction repeatedly inside a rolling
#   6-month window. Pivots on the HOLDER (cluster pivots on the symbol).
#   Mirrors the upstream "Nth insider buy by <HOLDER> in the last 6 months."
# ---------------------------------------------------------------------------








# ---------------------------------------------------------------------------
# Becoming-insider (the "5% crossing" pattern):
#   A holder whose stake crosses the 5% substantial-shareholder threshold
#   upward via accumulation. Pivots on the milestone; the story is "X just
#   became a substantial shareholder of COMPANY." OJK/IDX rule: >=5% ownership
#   makes you a reportable substantial shareholder.
# ---------------------------------------------------------------------------






# ---------------------------------------------------------------------------
# Cross-stock holders (the "cross" pattern):
#   ONE insider trading >= `min_symbols` DISTINCT symbols inside a trailing
#   6-month window. Pivots on the holder; the story is breadth / rotation.
#   Mirrors "<HOLDER> bought <SYM> and <OTHER> in the last 6 months."
# ---------------------------------------------------------------------------




def filter_tagged_filings(df):
    df = add_parsed_tags(df)
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
