import ast
import json
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


def group_tier1_news(df):
    if df.empty:
        return []
    
    rows = df[df["tier"] == "Tier 1"].copy()
    if rows.empty:
        return []
        
    def get_tier1_category(tags_parsed):
        for tag in tags_parsed:
            if tag in TIER_1_NEWS_TAGS:
                return tag
        return "Other"
        
    rows["category"] = rows["tags_parsed"].apply(get_tier1_category)
    groups = []
    
    for category, group in rows.groupby("category"):
        groups.append({
            "category": category,
            "news": group.to_dict("records")
        })
        
    return sorted(groups, key=lambda x: x["category"])


def filter_recent_news(df, now=None, hours=24):
    if df.empty or "created_at" not in df.columns:
        return df
    df = df.copy()
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    if now is None:
        now = pd.Timestamp.now(tz="UTC")
    since = now - timedelta(hours=hours)
    return df[df["created_at"] >= since]
