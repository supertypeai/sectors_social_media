from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from collections import defaultdict

import numpy as np
import pandas as pd
import json
import os


FILINGS_COLUMNS = [
    "id",
    "source",
    "created_at",
    "timestamp",
    "symbol",
    "title",
    "body",
    "tags",
    "transaction_type",
    "holder_type",
    "amount_transaction",
    "price",
    "transaction_value",
    "holding_before",
    "holding_after",
    "share_percentage_before",
    "share_percentage_after",
    "share_percentage_transaction",
    "holder_name",
    "context",
    "highlights",
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


def fetch_daily_prices(symbol, since=None, until=None):
    """Daily close prices for one symbol, ascending by date. Used for cluster charts."""
    def modifier(query):
        if since:
            query = query.gte("date", since)
        if until:
            query = query.lte("date", until)
        return query.order("date", desc=False)

    return fetch_supabase_table(
        "idx_daily_data",
        columns="date, close",
        symbol_column="symbol",
        symbol_value=symbol,
        query_modifier=modifier,
    )


def fetch_daily_market(symbol, since=None, until=None):
    """Daily close + volume + foreign flow for one symbol, ascending by date.

    Richer superset of fetch_daily_prices used by the insider-cluster carousel to
    add foreign-flow context. Columns beyond close may be null for illiquid names.
    """
    def modifier(query):
        if since:
            query = query.gte("date", since)
        if until:
            query = query.lte("date", until)
        return query.order("date", desc=False)

    return fetch_supabase_table(
        "idx_daily_data",
        columns="date, close, volume, foreign_buy_volume, foreign_sell_volume",
        symbol_column="symbol",
        symbol_value=symbol,
        query_modifier=modifier,
    )


def fetch_company_profiles():
    df = fetch_supabase_table("idx_company_profile", columns="symbol, company_name")
    if df.empty:
        return {}
    return df.set_index("symbol")["company_name"].to_dict()


def fetch_latest_broker_date():
    df = fetch_supabase_table(
        "idx_broker_summary_daily",
        columns="date",
        order_column="date",
        limit=1,
    )
    if df.empty:
        return None
    return str(df["date"].iloc[0])


def fetch_broker_bandar_scorecard(target_date: str) -> pd.DataFrame:
    pages = []
    page_size = 20000
    offset = 0
    while True:
        def modifier(q, d=target_date, off=offset, ps=page_size):
            return q.eq("date", d).range(off, off + ps - 1)
        page = fetch_supabase_table("idx_broker_summary_daily", query_modifier=modifier)
        if page.empty:
            break
        pages.append(page)
        if len(page) < page_size:
            break
        offset += page_size

    if not pages:
        return pd.DataFrame()
    df = pd.concat(pages, ignore_index=True)
    df = df[df["broker_code"] != "--"].reset_index(drop=True)
    df["gross_idr"] = df["bval"] + df["sval"]

    broker_totals = (
        df.groupby("broker_code", as_index=False)
          .agg(gross_idr=("gross_idr", "sum"), net_idr=("nval", "sum"))
          .sort_values("gross_idr", ascending=False)
          .head(10)
          .reset_index(drop=True)
    )
    broker_totals["rank"] = broker_totals.index + 1

    top_codes = set(broker_totals["broker_code"])
    df_top = df[df["broker_code"].isin(top_codes)]

    top_buys = (
        df_top.sort_values("nval", ascending=False)
              .groupby("broker_code", as_index=False)
              .head(1)[["broker_code", "symbol", "nval"]]
              .rename(columns={"symbol": "top_buy_symbol", "nval": "top_buy_net_idr"})
    )
    top_sells = (
        df_top.sort_values("nval", ascending=True)
              .groupby("broker_code", as_index=False)
              .head(1)[["broker_code", "symbol", "nval"]]
              .rename(columns={"symbol": "top_sell_symbol", "nval": "top_sell_net_idr"})
    )

    registry = fetch_supabase_table(
        "idx_broker_registry",
        columns="broker_code, broker_name, is_foreign, cohort",
    )
    profiles = fetch_company_profiles()

    result = broker_totals.merge(registry, on="broker_code", how="left")
    result = result.merge(top_buys, on="broker_code", how="left")
    result = result.merge(top_sells, on="broker_code", how="left")
    result["top_buy_company"] = result["top_buy_symbol"].map(profiles)
    result["top_sell_company"] = result["top_sell_symbol"].map(profiles)

    return result[[
        "rank", "broker_code", "broker_name", "is_foreign", "cohort",
        "gross_idr", "net_idr",
        "top_buy_symbol", "top_buy_company", "top_buy_net_idr",
        "top_sell_symbol", "top_sell_company", "top_sell_net_idr",
    ]]


def _fetch_broker_summary_range(start_date: str, end_date: str | None = None) -> pd.DataFrame:
    pages = []
    page_size = 20000
    offset = 0
    while True:
        def modifier(q, s=start_date, e=end_date, off=offset, ps=page_size):
            q = q.gte("date", s)
            if e:
                q = q.lte("date", e)
            return q.range(off, off + ps - 1)
        page = fetch_supabase_table("idx_broker_summary_daily", query_modifier=modifier)
        if page.empty:
            break
        pages.append(page)
        if len(page) < page_size:
            break
        offset += page_size
    if not pages:
        return pd.DataFrame()
    df = pd.concat(pages, ignore_index=True)
    return df[df["broker_code"] != "--"].reset_index(drop=True)


def fetch_broker_trending_movers(target_date: str) -> dict:
    df = _fetch_broker_summary_range(target_date, target_date)
    if df.empty:
        return {"date": target_date, "stocks": []}

    registry = fetch_supabase_table(
        "idx_broker_registry",
        columns="broker_code, broker_name, is_foreign, cohort",
    )
    df = df.merge(registry, on="broker_code", how="left")
    df["gross_idr"] = df["bval"] + df["sval"]
    df["volume_lots"] = df["blot"] + df["slot"]
    df["trade_count"] = df["bfreq"] + df["sfreq"]

    stock_stats = df.groupby("symbol", as_index=False).agg(
        gross_idr=("gross_idr", "sum"),
        volume_lots=("volume_lots", "sum"),
        trade_count=("trade_count", "sum"),
    )
    foreign_net = (
        df[df["is_foreign"] == True]
          .groupby("symbol", as_index=False)
          .agg(foreign_net=("nval", "sum"))
    )
    domestic_net = (
        df[df["is_foreign"] == False]
          .groupby("symbol", as_index=False)
          .agg(domestic_net=("nval", "sum"))
    )
    stock_stats = (
        stock_stats
          .merge(foreign_net, on="symbol", how="left")
          .merge(domestic_net, on="symbol", how="left")
          .fillna({"foreign_net": 0, "domestic_net": 0})
    )

    top5 = stock_stats.sort_values("gross_idr", ascending=False).head(5).reset_index(drop=True)
    profiles = fetch_company_profiles()
    top5["company"] = top5["symbol"].map(profiles)

    stocks = []
    for _, stock in top5.iterrows():
        sym = stock["symbol"]
        sb = (
            df[df["symbol"] == sym]
              .groupby(["broker_code", "broker_name", "is_foreign", "cohort"], as_index=False, dropna=False)
              .agg(net_idr=("nval", "sum"), gross_idr=("gross_idr", "sum"))
        )
        buyers = sb[sb["net_idr"] > 0].sort_values("net_idr", ascending=False).head(3)
        sellers = sb[sb["net_idr"] < 0].sort_values("net_idr", ascending=True).head(3)
        stocks.append({
            "symbol": sym,
            "company": stock["company"],
            "gross_idr": float(stock["gross_idr"]),
            "foreign_net": float(stock["foreign_net"]),
            "domestic_net": float(stock["domestic_net"]),
            "volume_lots": int(stock["volume_lots"]),
            "trade_count": int(stock["trade_count"]),
            "buyers": buyers.to_dict("records"),
            "sellers": sellers.to_dict("records"),
        })

    return {"date": target_date, "stocks": stocks}


def fetch_weekly_accumulation(week_start: str, week_end: str) -> dict:
    return _fetch_weekly_flow_top5(week_start, week_end, ascending=False)


def fetch_weekly_distribution(week_start: str, week_end: str) -> dict:
    return _fetch_weekly_flow_top5(week_start, week_end, ascending=True)


def _fetch_weekly_flow_top5(week_start: str, week_end: str, ascending: bool) -> dict:
    df = _fetch_broker_summary_range(week_start, week_end)
    if df.empty:
        return {"date_range": (week_start, week_end), "stocks": []}

    registry = fetch_supabase_table(
        "idx_broker_registry",
        columns="broker_code, broker_name, is_foreign, cohort",
    )
    df = df.merge(registry, on="broker_code", how="left")
    df["gross_idr"] = df["bval"] + df["sval"]
    df["trade_count"] = df["bfreq"] + df["sfreq"]

    # Per-stock foreign vs domestic net (sum of nval, signed)
    flow = df.groupby("symbol").apply(
        lambda g: pd.Series({
            "foreign_net": g.loc[g["is_foreign"] == True, "nval"].sum(),
            "domestic_net": g.loc[g["is_foreign"] == False, "nval"].sum(),
        }),
        include_groups=False,
    ).reset_index()

    stats = df.groupby("symbol", as_index=False).agg(
        gross_idr=("gross_idr", "sum"),
        trade_count=("trade_count", "sum"),
    )
    stock_stats = stats.merge(flow, on="symbol", how="left").fillna(
        {"foreign_net": 0, "domestic_net": 0}
    )

    top5 = stock_stats.sort_values("foreign_net", ascending=ascending).head(5)
    profiles = fetch_company_profiles()

    # Per-(broker, stock) weekly net â€” needed for top broker chips
    bs = df.groupby(
        ["broker_code", "broker_name", "is_foreign", "cohort", "symbol"],
        as_index=False, dropna=False,
    ).agg(broker_stock_net=("nval", "sum"))

    stocks = []
    for _, stock in top5.iterrows():
        sym = stock["symbol"]
        sub_bs = bs[(bs["symbol"] == sym) & (bs["is_foreign"] == True)]

        if ascending:  # distribution â†’ top foreign sellers
            tops = (
                sub_bs[sub_bs["broker_stock_net"] < 0]
                .sort_values("broker_stock_net", ascending=True)
                .head(3)
                .rename(columns={"broker_stock_net": "net_idr"})
            )
            key = "sellers"
        else:  # accumulation â†’ top foreign buyers
            tops = (
                sub_bs[sub_bs["broker_stock_net"] > 0]
                .sort_values("broker_stock_net", ascending=False)
                .head(3)
                .rename(columns={"broker_stock_net": "net_idr"})
            )
            key = "buyers"

        stocks.append({
            "symbol": sym,
            "company": profiles.get(sym),
            "foreign_net": float(stock["foreign_net"]),
            "domestic_net": float(stock["domestic_net"]),
            "gross_idr": float(stock["gross_idr"]),
            "trade_count": int(stock["trade_count"]),
            key: tops[["broker_code", "broker_name", "is_foreign", "cohort", "net_idr"]].to_dict("records"),
        })

    return {"date_range": (week_start, week_end), "stocks": stocks}


def fetch_weekly_bandar_plays(week_start: str, week_end: str) -> dict:
    df = _fetch_broker_summary_range(week_start, week_end)
    if df.empty:
        return {"date_range": (week_start, week_end), "plays": []}

    df["gross_idr"] = df["bval"] + df["sval"]

    pair_net = df.groupby(["broker_code", "symbol"], as_index=False).agg(pair_net=("nval", "sum"))
    top3 = pair_net[pair_net["pair_net"] > 0].sort_values("pair_net", ascending=False).head(3).reset_index(drop=True)

    broker_totals = df.groupby("broker_code", as_index=False).agg(
        broker_total_gross=("gross_idr", "sum"),
        broker_total_net=("nval", "sum"),
    )
    df_pos = df[df["nval"] > 0]
    broker_buying = df_pos.groupby("broker_code", as_index=False).agg(broker_total_buying=("nval", "sum"))
    stock_buying = df_pos.groupby("symbol", as_index=False).agg(stock_total_buying=("nval", "sum"))

    registry = fetch_supabase_table(
        "idx_broker_registry",
        columns="broker_code, broker_name, is_foreign, cohort",
    )
    profiles = fetch_company_profiles()

    plays = []
    for _, play in top3.iterrows():
        bc = play["broker_code"]
        sym = play["symbol"]
        net = float(play["pair_net"])

        bb = broker_buying.loc[broker_buying["broker_code"] == bc, "broker_total_buying"]
        bb_val = float(bb.iloc[0]) if not bb.empty else 0.0
        concentration = (net / bb_val * 100.0) if bb_val > 0 else 0.0

        sb = stock_buying.loc[stock_buying["symbol"] == sym, "stock_total_buying"]
        sb_val = float(sb.iloc[0]) if not sb.empty else 0.0
        stock_share = (net / sb_val * 100.0) if sb_val > 0 else 0.0

        bt = broker_totals[broker_totals["broker_code"] == bc]
        bt_gross = float(bt["broker_total_gross"].iloc[0]) if not bt.empty else 0.0
        bt_net = float(bt["broker_total_net"].iloc[0]) if not bt.empty else 0.0

        reg = registry[registry["broker_code"] == bc]
        if not reg.empty:
            broker_name = reg["broker_name"].iloc[0]
            is_foreign = bool(reg["is_foreign"].iloc[0]) if reg["is_foreign"].iloc[0] is not None else False
            cohort = reg["cohort"].iloc[0]
        else:
            broker_name = bc
            is_foreign = False
            cohort = "Mixed"

        plays.append({
            "broker_code": bc,
            "broker_name": broker_name,
            "is_foreign": is_foreign,
            "cohort": cohort,
            "symbol": sym,
            "company": profiles.get(sym),
            "net_idr": net,
            "concentration_pct": min(concentration, 100.0),
            "stock_share_pct": min(stock_share, 100.0),
            "broker_total_gross": bt_gross,
            "broker_total_net": bt_net,
        })

    return {"date_range": (week_start, week_end), "plays": plays}


def fetch_broker_weekly_recap(week_start: str, week_end: str, prior_start: str, prior_end: str) -> pd.DataFrame:
    this_df = _fetch_broker_summary_range(week_start, week_end)
    prior_df = _fetch_broker_summary_range(prior_start, prior_end)
    if this_df.empty:
        return pd.DataFrame()

    this_df["gross_idr"] = this_df["bval"] + this_df["sval"]
    this_totals = (
        this_df.groupby("broker_code", as_index=False)
               .agg(week_gross_idr=("gross_idr", "sum"), week_net_idr=("nval", "sum"))
               .sort_values("week_gross_idr", ascending=False)
               .reset_index(drop=True)
    )
    this_totals["this_rank"] = this_totals.index + 1

    if not prior_df.empty:
        prior_df["gross_idr"] = prior_df["bval"] + prior_df["sval"]
        prior_totals = (
            prior_df.groupby("broker_code", as_index=False)
                    .agg(prior_week_gross_idr=("gross_idr", "sum"))
                    .sort_values("prior_week_gross_idr", ascending=False)
                    .reset_index(drop=True)
        )
        prior_totals["prior_rank"] = prior_totals.index + 1
    else:
        prior_totals = pd.DataFrame(columns=["broker_code", "prior_week_gross_idr", "prior_rank"])

    merged = this_totals.merge(
        prior_totals[["broker_code", "prior_week_gross_idr", "prior_rank"]],
        on="broker_code",
        how="left",
    )

    def _label(row):
        if pd.isna(row["prior_rank"]):
            return "NEW"
        shift = int(row["prior_rank"]) - int(row["this_rank"])
        if shift > 0:
            return f"UP {shift}"
        if shift < 0:
            return f"DOWN {-shift}"
        return "SAME"

    merged["rank_shift"] = merged["prior_rank"] - merged["this_rank"]
    merged["rank_change_label"] = merged.apply(_label, axis=1)

    registry = fetch_supabase_table(
        "idx_broker_registry",
        columns="broker_code, broker_name, is_foreign, cohort",
    )
    merged = merged.merge(registry, on="broker_code", how="left")

    return merged[merged["this_rank"] <= 5].sort_values("this_rank").reset_index(drop=True)


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
        )
    )

    if is_output_json:
        return workflow_df.to_dict(orient="records")

    return workflow_df


def fetch_company_report():
    company_report_df = fetch_supabase_table(
        table_name="idx_company_report",
        columns="symbol, market_cap",
        query_modifier=lambda query: query.lte("market_cap_rank", 50)
    )

    return company_report_df


def fetch_company_report_earnings(max_rank: int = 200):
    """Per-symbol fundamentals for the earnings-spike post.

    Pulls the ready-made YoY growth fields plus the quarterly/annual history
    needed to draw the trend, limited to recognizable names by market-cap rank.
    """
    return fetch_supabase_table(
        table_name="idx_company_report",
        columns=(
            "symbol, company_name, sector, sub_sector, market_cap, market_cap_rank, "
            "last_close_price, daily_close_change, forward_pe, eps, "
            "yoy_quarter_earnings_growth, yoy_quarter_revenue_growth, "
            "historical_financials_quarterly, historical_eps"
        ),
        query_modifier=lambda query: query.lte("market_cap_rank", max_rank)
        .order("market_cap_rank", desc=False),
    )


def fetch_company_report_ownership(max_rank: int = 1000):
    """Per-symbol shareholder data for the ownership-concentration post.

    Pulls the major-shareholder roster + the local/foreign composition for every
    company, capped to recognizable names by market-cap rank. The `tags` column
    is returned so the selector can keep only `single-entity-holding-70` names.
    """
    return fetch_supabase_table(
        table_name="idx_company_report",
        columns=(
            "symbol, company_name, sector, sub_sector, market_cap, market_cap_rank, "
            "last_close_price, tags, major_shareholders, shareholders_composition"
        ),
        query_modifier=lambda query: query.lte("market_cap_rank", max_rank)
        .order("market_cap_rank", desc=False),
    )


def fetch_ihsg_weekly_data():
    ihsg_df = fetch_supabase_table(
        table_name="index_daily_data",
        columns="date, index_code, price",
        query_modifier=lambda query: query
            .eq("index_code", "IHSG")
            .order("date", desc=True)
            .limit(6)
    )

    return ihsg_df.to_dict(orient="records")


def fetch_agm_data():
    df_compro = fetch_supabase_table(
        "idx_company_report",
        columns="symbol,company_name,market_cap_rank",
        query_modifier=lambda q: q.lte("market_cap_rank", 300),
    )

    df_agm = fetch_supabase_table("idx_agm")

    if df_agm.empty or df_compro.empty:
        return pd.DataFrame()

    now = pd.Timestamp.now().normalize()
    seven_days_ago = (now - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    today = now.strftime("%Y-%m-%d")

    df_agm = (
        df_agm[
            (df_agm["agm_date"] >= seven_days_ago)
            & (df_agm["updated_on"] >= today)
            & (df_agm["summary"].notna())
            & (df_agm["symbol"].isin(df_compro["symbol"]))
        ]
        .sort_values("agm_date", ascending=False)
    )

    if df_agm.empty:
        return df_agm

    df_agm = df_agm.merge(df_compro, on="symbol", how="left")
    
    return df_agm.sort_values("agm_date", ascending=False).reset_index(drop=True)


def fetch_idx_upcoming_dividend(to_df: bool) -> pd.DataFrame | list[dict]:
    today = date.today().isoformat()

    idx_upcoming_dividend = fetch_supabase_table(
        table_name='idx_upcoming_dividend',
        query_modifier=lambda query: query 
            .gt("cum_date", today)
            .order("updated_on", desc=False)
    )

    if to_df:
        return idx_upcoming_dividend 
    
    return idx_upcoming_dividend.to_dict(orient="records")


def fetch_upcoming_dividends():
    lookback = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    df_div = fetch_idx_upcoming_dividend(to_df=True)

    if df_div.empty:
        return df_div

    symbols = df_div["symbol"].tolist()
    df_daily = fetch_supabase_table(
        "idx_daily_data",
        columns="symbol,close,date",
        since_column="date",
        since_value=lookback,
        order_column="date",
        order_desc=True,
        query_modifier=lambda q: q.in_("symbol", symbols),
    )

    if not df_daily.empty and "symbol" in df_daily.columns:
        df_daily = df_daily.drop_duplicates(subset="symbol", keep="first")

    df = df_div.merge(df_daily, on="symbol", how="left")
    df["dividend_yield"] = df["dividend_amount"] / df["close"]
    return df.sort_values("cum_date").reset_index(drop=True)


def fetch_idx_company_report(symbols: list[str]) -> list[dict]:
    columns = [
        'symbol, historical_dividends, yield_ttm, dividend_ttm, '
        'sector, last_ex_dividend_date, dividend_yield_avg, company_name'
    ]

    idx_company_report = fetch_supabase_table(
        table_name='idx_company_report',
        columns=columns,
        query_modifier=lambda query: query.in_("symbol", symbols)
    )

    return idx_company_report.to_dict(orient='records')


def fetch_anomaly_data():
    today           = pd.Timestamp.now().normalize().strftime("%Y-%m-%d")
    thirty_days_ago = (pd.Timestamp.now().normalize() - pd.Timedelta(days=30)).strftime("%Y-%m-%d")

    df_compro = fetch_supabase_table(
        "idx_company_report",
        columns="symbol,company_name,market_cap_rank,sub_sector",
        query_modifier=lambda q: q.lte("market_cap_rank", 300),
    )
    if df_compro.empty:
        return {}

    df_daily = fetch_supabase_table(
        "idx_daily_data",
        columns="symbol,close,date,market_cap,volume,foreign_sell_volume,foreign_buy_volume",
        since_column="date",
        since_value=thirty_days_ago,
        query_modifier=lambda q: q.in_("symbol", df_compro["symbol"].tolist()),
    )
    if df_daily.empty:
        return {}

    conditions = [
        df_daily["foreign_buy_volume"] > df_daily["foreign_sell_volume"],
        df_daily["foreign_buy_volume"] < df_daily["foreign_sell_volume"],
    ]
    df_daily["foreign_activity"]   = np.select(conditions, ["Net Buy", "Net Sell"], default="Neutral")
    df_daily["foreign_net_volume"] = df_daily["foreign_buy_volume"] - df_daily["foreign_sell_volume"]

    df_daily_change = (
        df_daily.sort_values("date")
        .groupby("symbol")
        .tail(2)
        .groupby("symbol")
        .apply(lambda g: pd.Series({
            "daily_close_change":  (g["close"].iloc[-1] - g["close"].iloc[-2]) / g["close"].iloc[-2],
            "latest_date":         g["date"].iloc[-1],
            "market_cap":          g["market_cap"].iloc[-1],
            "foreign_activity":    g["foreign_activity"].iloc[-1],
            "foreign_net_volume":  g["foreign_net_volume"].iloc[-1],
        }), include_groups=False)
        .reset_index()
    )

    df_compro = df_compro.merge(df_daily_change, on="symbol", how="left")

    df_subsec = (
        df_compro.groupby("sub_sector")
        .agg({"daily_close_change": "mean"})
        .reset_index()
        .sort_values("daily_close_change", ascending=False)
    )

    merge_df = df_compro.merge(df_subsec, on="sub_sector")
    merge_df["daily_close_change_delta"] = (
        merge_df["daily_close_change_x"] - merge_df["daily_close_change_y"]
    )

    filtered_df = merge_df[abs(merge_df["daily_close_change_delta"]) >= 0.15].sort_values(
        "daily_close_change_delta", ascending=False
    ).rename(columns={
        "daily_close_change_x": "daily_close_change",
        "daily_close_change_y": "sub_sector_avg_change",
    })

    return {
        "filtered_df": filtered_df.reset_index(drop=True),
        "df_daily":    df_daily,
    }


def _close_change(df, days):
    ref = (
        df[["symbol", "date", "close"]]
        .rename(columns={"close": f"close_{days}d_ago", "date": "ref_date"})
    )
    df_lookup = df.copy()
    df_lookup["ref_date"] = df_lookup["date"] - pd.Timedelta(days=days)
    return (
        pd.merge_asof(
            df_lookup.sort_values("ref_date").reset_index(drop=True),
            ref.sort_values("ref_date").reset_index(drop=True),
            on="ref_date", by="symbol", direction="backward",
        )
        .drop(columns=["ref_date"])
        .sort_values(["symbol", "date"])
    )


def fetch_volume_spike_data():
    df_compro = fetch_supabase_table(
        "idx_company_report",
        columns="symbol,company_name,market_cap_rank",
        query_modifier=lambda q: q.lte("market_cap_rank", 100),
    )
    if df_compro.empty:
        return {}

    thirty_days_ago = (pd.Timestamp.now().normalize() - pd.Timedelta(days=30)).strftime("%Y-%m-%d")

    df_daily = fetch_supabase_table(
        "idx_daily_data",
        columns="symbol,close,date,volume,foreign_sell_volume,foreign_buy_volume",
        since_column="date",
        since_value=thirty_days_ago,
        query_modifier=lambda q: q.in_("symbol", df_compro["symbol"].tolist()),
    )
    if df_daily.empty:
        return {}

    df_daily["date"] = pd.to_datetime(df_daily["date"])
    latest_date     = df_daily["date"].max()
    df_daily_last   = df_daily[df_daily["date"] == latest_date].copy()
    df_daily_others = df_daily[df_daily["date"] != latest_date].copy()

    df_daily = _close_change(df_daily, 1)
    df_daily = _close_change(df_daily, 3)
    df_daily = _close_change(df_daily, 7)
    for d in (1, 3, 7):
        df_daily[f"close_change_{d}d"] = (
            (df_daily["close"] - df_daily[f"close_{d}d_ago"]) / df_daily[f"close_{d}d_ago"]
        )
    df_daily = df_daily.drop(columns=["close_1d_ago", "close_3d_ago", "close_7d_ago"])

    vol_stats = (
        df_daily_others
        .groupby("symbol")[["volume", "foreign_buy_volume", "foreign_sell_volume"]]
        .median()
        .reset_index()
        .rename(columns={
            "volume": "avg_volume",
            "foreign_buy_volume": "avg_foreign_buy_volume",
            "foreign_sell_volume": "avg_foreign_sell_volume",
        })
    )

    df_spike = df_daily_last.merge(vol_stats, on="symbol", how="left")
    df_spike["volume_ratio"] = df_spike["volume"] / df_spike["avg_volume"]
    df_spike = df_spike[
        (df_spike["volume_ratio"] >= 3) & (df_spike["avg_volume"] > 0)
    ].sort_values("volume_ratio", ascending=False)

    df_spike["foreign_activity"] = np.select(
        [
            df_spike["foreign_buy_volume"] > df_spike["foreign_sell_volume"],
            df_spike["foreign_buy_volume"] < df_spike["foreign_sell_volume"],
        ],
        ["Net Buy", "Net Sell"],
        default="Neutral",
    )
    df_spike = df_spike.merge(
        df_daily[["symbol", "date", "close_change_1d", "close_change_3d", "close_change_7d"]],
        on=["symbol", "date"], how="left",
    )

    df_latest_7 = (
        df_daily.sort_values(["symbol", "date"])
        .groupby("symbol").tail(7)
    )[["symbol", "date", "volume"]]

    return {
        "df_spike":    df_spike.reset_index(drop=True),
        "df_latest_7": df_latest_7.reset_index(drop=True),
        "df_history":  df_daily_others.reset_index(drop=True),
        "compro_df":   df_compro,
    }


def fetch_idx_daily_data(symbol: str, from_date: str) -> list[dict]:
    idx_daily_data = fetch_supabase_table(
        table_name='idx_daily_data',
        query_modifier=lambda query: query
            .eq("symbol", symbol)
            .gte("date", from_date)
            .order("date", desc=False)
    )

    return [
        {"date": record["date"], "close": record["close"]}
        for record in idx_daily_data.to_dict(orient="records")
        if record.get("close") is not None
    ]


def fetch_foreign_flow_data(window_days: int = 7, top_n: int = 8, mcap_rank_max: int = 200):
    """Market-wide foreign net flow leaderboard over the last ~week of trading.

    Aggregates per-symbol foreign net value (IDR) = Î£ (foreign_buy_volume âˆ’
    foreign_sell_volume) Ã— close across the window, then ranks the strongest
    net-bought and net-sold names. Multi-ticker â€” the whole post compares stocks
    against each other, so unlike the per-stock anomaly post there is no single
    subject. Restricted to liquid top-mcap names so the board isn't dominated by
    thin small-caps where a single block trade swamps the ratio.

    Returns {} when there isn't enough data, else:
      {"net_buy": [rows], "net_sell": [rows], "window": (start, end), "trading_days": int}
    each row: symbol, base_symbol, company_name, sub_sector, net_value, gross_value.
    """
    df_compro = fetch_supabase_table(
        "idx_company_report",
        columns="symbol,company_name,market_cap_rank,sub_sector",
        query_modifier=lambda q: q.lte("market_cap_rank", mcap_rank_max),
    )
    if df_compro.empty:
        return {}

    since = (pd.Timestamp.now().normalize() - pd.Timedelta(days=window_days)).strftime("%Y-%m-%d")
    df_daily = fetch_supabase_table(
        "idx_daily_data",
        columns="symbol,date,close,foreign_buy_volume,foreign_sell_volume",
        since_column="date",
        since_value=since,
        query_modifier=lambda q: q.in_("symbol", df_compro["symbol"].tolist()),
    )
    if df_daily.empty:
        return {}

    for col in ("close", "foreign_buy_volume", "foreign_sell_volume"):
        df_daily[col] = pd.to_numeric(df_daily[col], errors="coerce")
    df_daily = df_daily.dropna(subset=["close", "foreign_buy_volume", "foreign_sell_volume"])
    if df_daily.empty:
        return {}

    # Per-row foreign flow in IDR (volume is in shares, so Ã— close = rupiah).
    df_daily["net_value"] = (
        (df_daily["foreign_buy_volume"] - df_daily["foreign_sell_volume"]) * df_daily["close"]
    )
    df_daily["gross_value"] = (
        (df_daily["foreign_buy_volume"] + df_daily["foreign_sell_volume"]) * df_daily["close"]
    )

    agg = (
        df_daily.groupby("symbol")
        .agg(net_value=("net_value", "sum"), gross_value=("gross_value", "sum"))
        .reset_index()
        .merge(df_compro[["symbol", "company_name", "sub_sector"]], on="symbol", how="left")
    )
    agg["base_symbol"] = agg["symbol"].str.replace(".JK", "", regex=False)

    trading_days = int(df_daily["date"].nunique())
    window = (str(df_daily["date"].min())[:10], str(df_daily["date"].max())[:10])

    def _rows(frame):
        return frame.to_dict(orient="records")

    net_buy = agg[agg["net_value"] > 0].sort_values("net_value", ascending=False).head(top_n)
    net_sell = agg[agg["net_value"] < 0].sort_values("net_value", ascending=True).head(top_n)

    if net_buy.empty and net_sell.empty:
        return {}

    return {
        "net_buy": _rows(net_buy),
        "net_sell": _rows(net_sell),
        "window": window,
        "trading_days": trading_days,
    }


def fetch_weekly_movers_data(top_n: int = 10, mcap_rank_max: int = 100):
    """Weekly winners + losers leaderboard from the top-mcap universe.

    Window = the current Mon-Fri calendar week. If the function runs on Sat or
    Sun (or after market close on Fri, which is the intended schedule), the
    window is this week's Mon â†’ Fri. Computes per-symbol return from
    `idx_daily_data.close[Mon]` to `close[Fri]`, restricted to stocks whose
    `market_cap_rank` is in the top `mcap_rank_max`. Returns the top `top_n`
    winners and losers. Filtering to liquid names keeps thin small-caps with
    stale prices out of the board.

    Returns {} when there isn't enough data, else:
      {"winners": [rows], "losers": [rows], "window": (start, end), "trading_days": int}
    each row: symbol, base_symbol, company_name, sub_sector,
              first_close, last_close, weekly_return.
    """
    df_compro = fetch_supabase_table(
        "idx_company_report",
        columns="symbol,company_name,market_cap_rank,sub_sector",
        query_modifier=lambda q: q.lte("market_cap_rank", mcap_rank_max),
    )
    if df_compro.empty:
        return {}

    # Anchor the window to the current calendar week (Mon-Fri). On a Sat or
    # Sun the "current week" is the just-completed one; on Mon-Fri it's the
    # in-flight week (so a mid-week debug run still returns partial data).
    today = pd.Timestamp.now().normalize()
    if today.weekday() >= 5:  # Sat or Sun
        # Go back to last Friday, then derive that week's Monday.
        last_friday = today - pd.Timedelta(days=today.weekday() - 4)
        week_monday = last_friday - pd.Timedelta(days=4)
        week_friday = last_friday
    else:
        week_monday = today - pd.Timedelta(days=today.weekday())
        week_friday = week_monday + pd.Timedelta(days=4)
    since = week_monday.strftime("%Y-%m-%d")
    until = week_friday.strftime("%Y-%m-%d")

    df_daily = fetch_supabase_table(
        "idx_daily_data",
        columns="symbol,date,close",
        query_modifier=lambda q: q.in_("symbol", df_compro["symbol"].tolist())
                                  .gte("date", since)
                                  .lte("date", until),
    )
    if df_daily.empty:
        return {}

    df_daily["close"] = pd.to_numeric(df_daily["close"], errors="coerce")
    df_daily = df_daily.dropna(subset=["close"])
    df_daily = df_daily[df_daily["close"] > 0]
    if df_daily.empty:
        return {}

    df_daily["date"] = pd.to_datetime(df_daily["date"])
    df_daily = df_daily.sort_values(["symbol", "date"])

    grp = df_daily.groupby("symbol")
    perf = pd.DataFrame({
        "first_close": grp["close"].first(),
        "last_close": grp["close"].last(),
        "n_points": grp["close"].count(),
    }).reset_index()
    # Need at least 2 datapoints to compute a return.
    perf = perf[perf["n_points"] >= 2]
    if perf.empty:
        return {}

    perf["weekly_return"] = (perf["last_close"] - perf["first_close"]) / perf["first_close"]
    perf = perf.merge(df_compro[["symbol", "company_name", "sub_sector"]], on="symbol", how="left")
    perf["base_symbol"] = perf["symbol"].str.replace(".JK", "", regex=False)

    trading_days = int(df_daily["date"].nunique())
    window = (str(df_daily["date"].min())[:10], str(df_daily["date"].max())[:10])

    def _rows(frame):
        return frame.to_dict(orient="records")

    winners = perf.sort_values("weekly_return", ascending=False).head(top_n)
    losers = perf.sort_values("weekly_return", ascending=True).head(top_n)

    if winners.empty and losers.empty:
        return {}

    return {
        "winners": _rows(winners),
        "losers": _rows(losers),
        "window": window,
        "trading_days": trading_days,
    }


def fetch_weekly_sector_data(mcap_rank_max: int = 300):
    """11-sector heat map of weekly performance for the current Mon-Fri week.

    Same window logic as `fetch_weekly_movers_data`. For each of the 11 IDX
    sectors (IDX-IC taxonomy), computes mcap-weighted weekly return across
    constituents in the top-mcap universe (top 300 by default â€” wide enough
    that small sectors like Healthcare / Transportation get meaningful sample
    size), plus the per-sector bellwether (largest stock by market cap) and
    its own weekly return.

    Returns {} when there isn't enough data, else:
      {"sectors": [rows], "window": (start, end), "trading_days": int}
    each row: sector, weighted_return, n_stocks, top_symbol, top_base_symbol,
              top_company_name, top_return.
    """
    df_compro = fetch_supabase_table(
        "idx_company_report",
        columns="symbol,company_name,sector,market_cap,market_cap_rank",
        query_modifier=lambda q: q.lte("market_cap_rank", mcap_rank_max),
    )
    if df_compro.empty:
        return {}

    df_compro = df_compro.dropna(subset=["sector"])
    df_compro["market_cap"] = pd.to_numeric(df_compro["market_cap"], errors="coerce")
    df_compro = df_compro.dropna(subset=["market_cap"])
    if df_compro.empty:
        return {}

    today = pd.Timestamp.now().normalize()
    if today.weekday() >= 5:
        last_friday = today - pd.Timedelta(days=today.weekday() - 4)
        week_monday = last_friday - pd.Timedelta(days=4)
        week_friday = last_friday
    else:
        week_monday = today - pd.Timedelta(days=today.weekday())
        week_friday = week_monday + pd.Timedelta(days=4)
    since = week_monday.strftime("%Y-%m-%d")
    until = week_friday.strftime("%Y-%m-%d")

    df_daily = fetch_supabase_table(
        "idx_daily_data",
        columns="symbol,date,close",
        query_modifier=lambda q: q.in_("symbol", df_compro["symbol"].tolist())
                                  .gte("date", since)
                                  .lte("date", until),
    )
    if df_daily.empty:
        return {}

    df_daily["close"] = pd.to_numeric(df_daily["close"], errors="coerce")
    df_daily = df_daily.dropna(subset=["close"])
    df_daily = df_daily[df_daily["close"] > 0]
    if df_daily.empty:
        return {}

    df_daily["date"] = pd.to_datetime(df_daily["date"])
    df_daily = df_daily.sort_values(["symbol", "date"])

    grp = df_daily.groupby("symbol")
    perf = pd.DataFrame({
        "first_close": grp["close"].first(),
        "last_close": grp["close"].last(),
        "n_points": grp["close"].count(),
    }).reset_index()
    perf = perf[perf["n_points"] >= 2]
    if perf.empty:
        return {}

    perf["weekly_return"] = (perf["last_close"] - perf["first_close"]) / perf["first_close"]
    perf = perf.merge(
        df_compro[["symbol", "company_name", "sector", "market_cap"]],
        on="symbol",
        how="left",
    )
    perf = perf.dropna(subset=["sector"])
    if perf.empty:
        return {}

    # Sector-level: market-cap weighted average return.
    perf["mcap_x_ret"] = perf["market_cap"] * perf["weekly_return"]
    sector_agg = (
        perf.groupby("sector", as_index=False)
            .agg(
                weighted_sum=("mcap_x_ret", "sum"),
                total_mcap=("market_cap", "sum"),
                n_stocks=("symbol", "count"),
            )
    )
    sector_agg["weighted_return"] = sector_agg["weighted_sum"] / sector_agg["total_mcap"]

    # Per-sector bellwether (largest stock by market cap) and its own weekly
    # return. The reader recognizes BBCA, TLKM, BREN, etc., so the row reads
    # as "sector did X this week, and here's how the giant in it moved."
    sector_top = (
        perf.sort_values("market_cap", ascending=False)
            .groupby("sector", as_index=False)
            .first()[["sector", "symbol", "company_name", "weekly_return"]]
            .rename(columns={
                "symbol": "top_symbol",
                "company_name": "top_company_name",
                "weekly_return": "top_return",
            })
    )
    sector_top["top_base_symbol"] = sector_top["top_symbol"].str.replace(".JK", "", regex=False)

    result = sector_agg.merge(sector_top, on="sector", how="left")
    result = result.sort_values("weighted_return", ascending=False).reset_index(drop=True)

    trading_days = int(df_daily["date"].nunique())
    window = (str(df_daily["date"].min())[:10], str(df_daily["date"].max())[:10])

    return {
        "sectors": result.to_dict(orient="records"),
        "window": window,
        "trading_days": trading_days,
    }


def fetch_lq45_ytd_data(top_n: int = 15, direction: str = "worst"):
    """LQ45 stocks ranked by YTD price return for the current year.

    LQ45 is IDX's 45-most-liquid-stocks index. Returns the `top_n` worst (or
    best, if `direction="best"`) YTD performers as of the most recent close
    available in `idx_daily_data`. YTD is computed from the first close in
    January vs the latest close.

    Returns {} when there isn't enough data, else:
      {"rows": [rows], "start_date": str, "end_date": str, "direction": str}
    each row: symbol, base_symbol, company_name, first_close, last_close,
              ytd_return.
    """
    df_compro = fetch_supabase_table(
        "idx_company_report",
        columns="symbol,company_name,indices",
        query_modifier=lambda q: q.lte("market_cap_rank", 200),
    )
    if df_compro.empty:
        return {}

    def is_lq45(idx):
        if idx is None:
            return False
        if isinstance(idx, list):
            return any("LQ45" in str(x) for x in idx)
        return "LQ45" in str(idx)

    df_lq45 = df_compro[df_compro["indices"].apply(is_lq45)]
    if df_lq45.empty:
        return {}

    today = pd.Timestamp.now().normalize()
    jan1 = pd.Timestamp(year=today.year, month=1, day=1)
    since = jan1.strftime("%Y-%m-%d")

    df_daily = fetch_supabase_table(
        "idx_daily_data",
        columns="symbol,date,close",
        since_column="date",
        since_value=since,
        query_modifier=lambda q: q.in_("symbol", df_lq45["symbol"].tolist()),
    )
    if df_daily.empty:
        return {}

    df_daily["close"] = pd.to_numeric(df_daily["close"], errors="coerce")
    df_daily = df_daily.dropna(subset=["close"])
    df_daily = df_daily[df_daily["close"] > 0]
    if df_daily.empty:
        return {}

    df_daily["date"] = pd.to_datetime(df_daily["date"])
    df_daily = df_daily.sort_values(["symbol", "date"])

    grp = df_daily.groupby("symbol")
    perf = pd.DataFrame({
        "first_close": grp["close"].first(),
        "last_close": grp["close"].last(),
        "n_points": grp["close"].count(),
    }).reset_index()
    perf = perf[perf["n_points"] >= 2]
    if perf.empty:
        return {}

    perf["ytd_return"] = (perf["last_close"] - perf["first_close"]) / perf["first_close"]
    perf = perf.merge(df_lq45[["symbol", "company_name"]], on="symbol", how="left")
    perf["base_symbol"] = perf["symbol"].str.replace(".JK", "", regex=False)

    ascending = direction == "worst"
    ranked = perf.sort_values("ytd_return", ascending=ascending).head(top_n)

    return {
        "rows": ranked.to_dict(orient="records"),
        "start_date": str(df_daily["date"].min())[:10],
        "end_date": str(df_daily["date"].max())[:10],
        "direction": direction,
    }


def fetch_weekly_insider_aggregates(window_days: int = 7, top_n: int = 5):
    """Insider buy/sell aggregates over the trailing N days.

    Aggregates `idx_filings` rows where `holder_type='insider'` over the last
    `window_days`, grouping by symbol. Returns top `top_n` by total buy_value
    and top `top_n` by total sell_value (separately).

    Returns {} when there isn't enough data, else:
      {"buys": [rows], "sells": [rows], "window": (start, end), "n_filings": int}
    each row: symbol, base_symbol, company_name, total_value, n_filings,
              top_holder.
    """
    since = (datetime.now() - timedelta(days=window_days)).isoformat()
    df = fetch_supabase_table(
        "idx_filings",
        columns="symbol,transaction_type,transaction_value,holder_type,holder_name,created_at",
        since_column="created_at",
        since_value=since,
    )
    if df.empty:
        return {}

    df = df[df["holder_type"] == "insider"]
    df["transaction_value"] = pd.to_numeric(df["transaction_value"], errors="coerce")
    df = df.dropna(subset=["transaction_value", "symbol"])
    df = df[df["transaction_value"] > 0]
    if df.empty:
        return {}

    buys_df = df[df["transaction_type"] == "buy"]
    sells_df = df[df["transaction_type"] == "sell"]

    def _aggregate(side_df):
        if side_df.empty:
            return pd.DataFrame()
        agg = (
            side_df.groupby("symbol", as_index=False)
                   .agg(
                       total_value=("transaction_value", "sum"),
                       n_filings=("transaction_value", "count"),
                   )
        )
        # Per-symbol: largest single filing's holder name is the "top holder".
        top_holder = (
            side_df.sort_values("transaction_value", ascending=False)
                   .groupby("symbol", as_index=False)
                   .first()[["symbol", "holder_name"]]
                   .rename(columns={"holder_name": "top_holder"})
        )
        agg = agg.merge(top_holder, on="symbol", how="left")
        agg["base_symbol"] = agg["symbol"].str.replace(".JK", "", regex=False)
        return agg

    buys_agg = _aggregate(buys_df).sort_values("total_value", ascending=False).head(top_n)
    sells_agg = _aggregate(sells_df).sort_values("total_value", ascending=False).head(top_n)

    if buys_agg.empty and sells_agg.empty:
        return {}

    # Enrich with company names from idx_company_report.
    all_syms = list(set(buys_agg["symbol"].tolist() + sells_agg["symbol"].tolist()))
    if all_syms:
        profiles = fetch_supabase_table(
            "idx_company_report",
            columns="symbol,company_name",
            query_modifier=lambda q: q.in_("symbol", all_syms),
        )
        sym_to_name = (
            dict(zip(profiles["symbol"], profiles["company_name"]))
            if not profiles.empty
            else {}
        )
    else:
        sym_to_name = {}

    def _enrich(agg):
        if agg.empty:
            return agg
        agg = agg.copy()
        agg["company_name"] = agg["symbol"].map(sym_to_name).fillna("")
        return agg

    buys_agg = _enrich(buys_agg)
    sells_agg = _enrich(sells_agg)

    end = pd.Timestamp.now().normalize()
    start = end - pd.Timedelta(days=window_days)

    return {
        "buys": buys_agg.to_dict(orient="records"),
        "sells": sells_agg.to_dict(orient="records"),
        "window": (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")),
        "n_filings": int(len(df)),
    }


def fetch_macro_news(th_score: int = 80):
    macro_tags = [
        "Central Bank",
        "Currency & FX",
        "Forex",
        "Inflation",
        "Interest Rate",
        "Global Economy",
        "Government Policy",
        "Tariff & VAT",
    ]

    tags_array = "{" + ",".join(macro_tags) + "}"

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    records = fetch_supabase_table(
        table_name="idx_news",
        order_column="timestamp",
        order_desc=True,
        since_column="timestamp",
        since_value=seven_days_ago,
        query_modifier=lambda query: (
            query
            .filter("tags", "ov", tags_array)
            .filter("tickers", "eq", "{}")
            .filter("score", "gt", th_score)
        ),
    ).to_dict(orient="records")

    print(f'length macro news: {len(records)}')

    return records


def fetch_stock_indices(target_indices: list[str]):
    records = fetch_supabase_table(
        table_name='idx_company_profile', 
        columns='symbol, company_name, indices',
        query_modifier=lambda query: (
            query
            .overlaps("indices", target_indices)
        )
    ).to_dict(orient='records')

    companies = {}

    for record in records: 
        companies[record['symbol']] = {
            "company_name": record["company_name"],
            "indices": [
                company_index 
                for company_index in record['indices']
                if company_index in target_indices
            ]
        }

    return companies 


def fetch_index_performance(target_indices: list[str], day: int = 7) -> float | None:
    lookback_date = datetime.now() - timedelta(days=day)

    df = fetch_supabase_table(
        table_name="index_daily_data",
        columns="date, price, index_code",
        query_modifier=lambda query: query
            .in_("index_code", target_indices)
            .gte("date", (lookback_date - timedelta(days=day)).strftime("%Y-%m-%d"))
            .order("date", desc=False)
    )

    if df.empty:
        return None

    df["date"] = pd.to_datetime(df["date"])
    
    result = {}

    for index, group in df.groupby("index_code"):
        latest = group.iloc[-1]["price"]
        previous_rows = group[group["date"] <= lookback_date]

        if previous_rows.empty:
            result[index] = None
            continue

        previous = previous_rows.iloc[-1]["price"]
        result[index] = float((latest - previous) / previous * 100)

    return result


def fetch_stock_performance(companies: dict, day: int = 7) -> dict:
    lookback_date = datetime.now() - timedelta(days=day)

    df_daily = fetch_supabase_table(
        "idx_daily_data",
        columns="symbol,close,date",
        since_column="date",
        since_value=(lookback_date - timedelta(days=day)).strftime("%Y-%m-%d"),  #buffer
        order_column="date",
        order_desc=False,
        query_modifier=lambda query: (
            query.in_("symbol", list(companies.keys()))
        ),
    )

    df_daily["date"] = pd.to_datetime(df_daily["date"])

    for symbol, daily_data in df_daily.groupby("symbol", sort=False):
        latest = daily_data.iloc[-1]

        previous_rows = daily_data[daily_data["date"] <= lookback_date]
        
        if previous_rows.empty:
            continue

        previous = previous_rows.iloc[-1]

        latest_close = latest["close"].item()
        previous_close = previous["close"].item()

        companies[symbol]["performance"] = {
            "latest_close": latest_close,
            f"close_{day}d": previous_close,
            f"return_{day}d": (latest_close - previous_close) / previous_close * 100,
        }

    return companies


def group_companies_by_index(companies: dict):
    companies_by_index = defaultdict(list)

    for symbol, company in companies.items(): 
        if "performance" not in company:
            continue

        for index in company['indices']:
            companies_by_index[index].append({
                "symbol": symbol,
                "company_name": company["company_name"],
                **company["performance"],
            }) 

    return dict(companies_by_index)
