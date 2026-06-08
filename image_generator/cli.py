import argparse
import os
from datetime import datetime
from pathlib import Path

try:
    from slack_sdk import WebClient
except ImportError:
    WebClient = None

from .classification import (
    classify_news,
    filter_daily_filings,
    filter_recent_news,
    filter_tagged_filings,
    group_context_filings,
)
from .data import (
    fetch_broker_bandar_scorecard,
    fetch_broker_trending_movers,
    fetch_broker_weekly_recap,
    fetch_company_profiles,
    fetch_filings,
    fetch_latest_broker_date,
    fetch_news,
    fetch_weekly_accumulation,
    fetch_weekly_bandar_plays,
    fetch_weekly_distribution,
    load_records,
)
from .utils.slack import upload_posts_to_slack
from .render import SocialImageRenderer
from .summarizer import NewsSummarizer


def date_label(value=None):
    if value:
        return value
    return datetime.now().strftime("%d %B %Y")


def load_input(args, kind):
    if args.input:
        return load_records(args.input)
    if kind == "filings":
        return fetch_filings(since=args.filings_since)
    if kind == "news":
        return fetch_news()
    raise ValueError(f"Unsupported input kind: {kind}")


def generate(args):
    renderer = SocialImageRenderer(output_dir=args.output)
    try:
        renderer.company_profiles = fetch_company_profiles()
    except Exception as e:
        print(f"Warning: Could not fetch company profiles: {e}")
        renderer.company_profiles = {}
        
    summarizer = NewsSummarizer()
    paths = []

    if args.mode in {"filings-daily", "filings-context", "filings-tags"}:
        df = load_input(args, "filings")

        if args.mode == "filings-daily":
            filtered = filter_daily_filings(df, hours=args.hours)
            rows = filtered.to_dict("records")
            if args.limit:
                rows = rows[: args.limit]
            
            for row in rows:
                title = row.get("title") or "Filing Transaction"
                print(f"Summarizing context for: {title[:50]}...")
                row["title_summarized"] = summarizer.summarize_filing_context(title)
                
            paths.append(renderer.render_daily_filings(rows, date_label(args.date_label)))
        elif args.mode == "filings-context":
            rows = group_context_filings(df)
            if args.limit:
                rows = rows[: args.limit]
            for group in rows:
                paths.append(renderer.render_context_filing(group))
        elif args.mode == "filings-tags":
            rows = filter_tagged_filings(df).to_dict("records")
            if args.limit:
                rows = rows[: args.limit]
            for filing in rows:
                paths.append(renderer.render_tagged_filing(filing))

    if args.mode == "broker-bandar":
        if args.input:
            df = load_records(args.input)
        else:
            target_date = None
            if args.date_label:
                try:
                    target_date = datetime.strptime(args.date_label, "%d %B %Y").strftime("%Y-%m-%d")
                except ValueError:
                    target_date = args.date_label
            if not target_date:
                target_date = fetch_latest_broker_date()
            if not target_date:
                print("No broker data available.")
                df = None
            else:
                print(f"Fetching broker scorecard for {target_date}...")
                df = fetch_broker_bandar_scorecard(target_date)
        if df is not None and not df.empty:
            display_date = date_label(args.date_label)
            try:
                if not args.date_label and target_date:
                    display_date = datetime.strptime(target_date, "%Y-%m-%d").strftime("%d %B %Y")
            except (ValueError, TypeError):
                pass
            print(f"Rendering bandar scorecard with {len(df)} broker(s)")
            records = df.to_dict("records")
            path = renderer.render_broker_bandar_scorecard(records, display_date)
            caption = (
                f":bar_chart: *Bandar Scorecard — {display_date}*\n\n"
                "#IDX #StockMarket #Indonesia #BrokerActivity #SectorsApp"
            )
            paths.append((path, caption))
        else:
            print("No broker rows to render.")

    if args.mode == "broker-trending":
        target_date = None
        if args.date_label:
            try:
                target_date = datetime.strptime(args.date_label, "%d %B %Y").strftime("%Y-%m-%d")
            except ValueError:
                target_date = args.date_label
        if not target_date:
            target_date = fetch_latest_broker_date()
        if target_date:
            print(f"Fetching trending movers for {target_date}...")
            payload = fetch_broker_trending_movers(target_date)
            display_date = date_label(args.date_label) if args.date_label else datetime.strptime(target_date, "%Y-%m-%d").strftime("%d %B %Y")
            if payload["stocks"]:
                print(f"Rendering trending movers with {len(payload['stocks'])} stock(s)")
                path = renderer.render_broker_trending_movers(payload, display_date)
                caption = (
                    f":zap: *Trending Movers — {display_date}*\n\n"
                    "#IDX #StockMarket #Indonesia #BrokerActivity #SectorsApp"
                )
                paths.append((path, caption))
            else:
                print("No trending-mover data to render.")

    if args.mode == "broker-weekly":
        from datetime import timedelta
        week_end = None
        if args.date_label:
            try:
                week_end_dt = datetime.strptime(args.date_label, "%d %B %Y")
                week_end = week_end_dt.strftime("%Y-%m-%d")
            except ValueError:
                week_end = args.date_label
        if not week_end:
            latest = fetch_latest_broker_date()
            if latest:
                week_end = latest
        if week_end:
            week_end_dt = datetime.strptime(week_end, "%Y-%m-%d")
            week_start_dt = week_end_dt - timedelta(days=4)
            prior_end_dt = week_end_dt - timedelta(days=7)
            prior_start_dt = prior_end_dt - timedelta(days=4)
            week_start = week_start_dt.strftime("%Y-%m-%d")
            prior_start = prior_start_dt.strftime("%Y-%m-%d")
            prior_end = prior_end_dt.strftime("%Y-%m-%d")
            print(f"Fetching weekly recap for {week_start}..{week_end} (prior: {prior_start}..{prior_end})...")
            df = fetch_broker_weekly_recap(week_start, week_end, prior_start, prior_end)
            if week_start_dt.month == week_end_dt.month:
                display_range = f"{week_start_dt.strftime('%d')}–{week_end_dt.strftime('%d %B %Y')}"
            else:
                display_range = f"{week_start_dt.strftime('%d %b')} – {week_end_dt.strftime('%d %b %Y')}"
            if not df.empty:
                print(f"Rendering weekly recap with {len(df)} broker(s)")
                path = renderer.render_broker_weekly_recap(df.to_dict("records"), display_range)
                caption = (
                    f":trophy: *Weekly Broker Recap — {display_range}*\n\n"
                    "#IDX #StockMarket #Indonesia #BrokerActivity #SectorsApp"
                )
                paths.append((path, caption))
            else:
                print("No weekly recap data to render.")

    if args.mode in {"weekly-accumulation", "weekly-distribution", "weekly-bandar"}:
        from datetime import timedelta
        week_end = None
        if args.date_label:
            try:
                week_end_dt = datetime.strptime(args.date_label, "%d %B %Y")
                week_end = week_end_dt.strftime("%Y-%m-%d")
            except ValueError:
                week_end = args.date_label
        if not week_end:
            latest = fetch_latest_broker_date()
            if latest:
                week_end = latest
        if week_end:
            week_end_dt = datetime.strptime(week_end, "%Y-%m-%d")
            week_start_dt = week_end_dt - timedelta(days=4)
            week_start = week_start_dt.strftime("%Y-%m-%d")
            if week_start_dt.month == week_end_dt.month:
                display_range = f"{week_start_dt.strftime('%d')}–{week_end_dt.strftime('%d %B %Y')}"
            else:
                display_range = f"{week_start_dt.strftime('%d %b')} – {week_end_dt.strftime('%d %b %Y')}"

            if args.mode == "weekly-accumulation":
                print(f"Fetching weekly accumulation for {week_start}..{week_end}...")
                payload = fetch_weekly_accumulation(week_start, week_end)
                if payload["stocks"]:
                    print(f"Rendering accumulation with {len(payload['stocks'])} stock(s)")
                    path = renderer.render_weekly_accumulation(payload, display_range)
                    caption = (
                        f":chart_with_upwards_trend: *Most Accumulated — {display_range}*\n\n"
                        "#IDX #StockMarket #Indonesia #BrokerFlow #SectorsApp"
                    )
                    paths.append((path, caption))
                else:
                    print("No accumulation data to render.")

            elif args.mode == "weekly-distribution":
                print(f"Fetching weekly distribution for {week_start}..{week_end}...")
                payload = fetch_weekly_distribution(week_start, week_end)
                if payload["stocks"]:
                    print(f"Rendering distribution with {len(payload['stocks'])} stock(s)")
                    path = renderer.render_weekly_distribution(payload, display_range)
                    caption = (
                        f":chart_with_downwards_trend: *Most Distributed — {display_range}*\n\n"
                        "#IDX #StockMarket #Indonesia #BrokerFlow #SectorsApp"
                    )
                    paths.append((path, caption))
                else:
                    print("No distribution data to render.")

            elif args.mode == "weekly-bandar":
                print(f"Fetching weekly bandar plays for {week_start}..{week_end}...")
                payload = fetch_weekly_bandar_plays(week_start, week_end)
                if payload["plays"]:
                    print(f"Rendering bandar plays with {len(payload['plays'])} play(s)")
                    path = renderer.render_weekly_bandar_plays(payload, display_range)
                    caption = (
                        f":crown: *Bandar of the Week — {display_range}*\n\n"
                        "#IDX #StockMarket #Indonesia #BrokerActivity #SectorsApp"
                    )
                    paths.append((path, caption))
                else:
                    print("No bandar plays to render.")

    if args.mode in {"news-tier1", "news-tier2"}:
        df = classify_news(load_input(args, "news"))
        if not args.all_news:
            df = filter_recent_news(df, hours=args.hours)
        if not df.empty and "created_at" in df.columns:
            print(f"After {args.hours}h filter: {len(df)} news rows, oldest={df['created_at'].min()}, newest={df['created_at'].max()}")
        if args.mode == "news-tier1":
            rows = df[df["tier"] == "Tier 1"].sort_values("created_at", ascending=False).to_dict("records")
            if args.limit:
                rows = rows[: args.limit]
            if rows:
                print(f"Rendering Tier 1 digest with {len(rows)} item(s)")
                path = renderer.render_tier1_digest(rows, date_label(args.date_label))
                caption = (
                    f":chart_with_upwards_trend: *Tier 1 IDX News — {date_label(args.date_label)}*\n\n"
                    "#IDX #StockMarket #Indonesia #Investing #FinancialData #SectorsApp"
                )
                paths.append((path, caption))
            else:
                print("No Tier 1 news in window; skipping digest.")
        elif args.mode == "news-tier2":
            rows = df[df["tier"] == "Tier 2"].to_dict("records")
            if args.limit:
                rows = rows[: args.limit]
            paths.append(renderer.render_tier2_news_summary(rows, date_label(args.date_label)))

    if args.max_posts and len(paths) > args.max_posts:
        print(f"Capping output at {args.max_posts} posts (would have been {len(paths)})")
        paths = paths[: args.max_posts]

    if args.dry_run:
        print(f"[dry-run] {len(paths)} post(s) generated, skipping Slack upload")
        for item in paths:
            path = item[0] if isinstance(item, tuple) else item
            print(f"[dry-run] {Path(path).resolve()}")
        return

    upload_posts_to_slack(paths, slack_channel=args.slack_channel)


def build_parser():
    parser = argparse.ArgumentParser(description="Generate Sectors social media images from filings/news data.")
    parser.add_argument(
        "--mode",
        required=True,
        choices=[
            "filings-daily", 
            "filings-context", 
            "filings-tags", 
            "news-tier1", 
            "news-tier2",
            "quarterly-low",
            "companies-mover",
            "broker-bandar",
            "broker-trending",
            "broker-weekly",
            "weekly-accumulation",
            "weekly-distribution",
            "weekly-bandar",
        ],
        help="Content type to generate.",
    )
    parser.add_argument("--input", help="Optional CSV, JSON, or JSONL override for local QA. Supabase is used by default.")
    parser.add_argument("--output", default="output", help="Output directory.")
    parser.add_argument("--date-label", help="Display date label, defaults to today.")
    parser.add_argument("--hours", type=int, default=24, help="Lookback window for daily filings and news.")
    parser.add_argument("--limit", type=int, help="Maximum records to render for per-item modes (categories for news-tier1).")
    parser.add_argument("--max-posts", type=int, default=3, help="Hard cap on total Slack posts emitted per run. Defaults to 3.")
    parser.add_argument("--dry-run", action="store_true", help="Generate images but skip Slack upload.")
    parser.add_argument("--all-news", action="store_true", help="Backfill all tiered news instead of filtering by --hours.")
    parser.add_argument(
        "--filings-since",
        help="Supabase idx_filings timestamp lower bound, matching the notebook default.",
    )
    parser.add_argument("--slack-channel", help="Slack channel ID to post results to (requires SLACK_BOT_TOKEN).")
    return parser


def main():
    args = build_parser().parse_args()
    generate(args)


if __name__ == "__main__":
    main()

# python -m image_generator.cli --mode companies-mover
# python -m image_generator.cli --mode quarterly-low