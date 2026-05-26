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
from .data import DEFAULT_FILINGS_SINCE, fetch_company_profiles, fetch_filings, fetch_news, load_records
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

    if args.mode in {"news-tier1", "news-tier2"}:
        df = classify_news(load_input(args, "news"))
        if not args.all_news:
            df = filter_recent_news(df, hours=args.hours)
        if args.mode == "news-tier1":
            rows = df[df["tier"] == "Tier 1"].to_dict("records")
            if args.limit:
                rows = rows[: args.limit]
            for news in rows:
                # Optimize news for social media using LLM
                title = news.get("title")
                body = news.get("body") or news.get("summary") or news.get("description") or ""
                if title and body:
                    safe_title = title[:50].encode('ascii', 'ignore').decode()
                    print(f"Optimizing: {safe_title}...")
                    optimized = summarizer.optimize_news(title, body)
                    news.update(optimized)
                
                path = renderer.render_tier1_news(news)
                caption = f":chart_with_upwards_trend: *{news.get('headline', title)}*\n\n"
                if news.get("bullets"):
                    caption += "\n".join(f"• {b}" for b in news.get("bullets", [])) + "\n\n"
                caption += "#IDX #StockMarket #Indonesia #Investing #FinancialData #SectorsApp"
                paths.append((path, caption))
        elif args.mode == "news-tier2":
            rows = df[df["tier"] == "Tier 2"].to_dict("records")
            if args.limit:
                rows = rows[: args.limit]
            paths.append(renderer.render_tier2_news_summary(rows, date_label(args.date_label)))

    slack_client = None
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    if slack_token:
        slack_token = slack_token.strip(' "''')
    if getattr(args, "slack_channel", None) and slack_token and WebClient:
        slack_client = WebClient(token=slack_token)

    for item in paths:
        if isinstance(item, tuple):
            path, caption = item
        else:
            path, caption = item, f"New image generated: {Path(item).name}\n\n#IDX #StockMarket #Indonesia #SectorsApp"
            
        resolved = Path(path).resolve()
        print(resolved)
        
        if slack_client:
            print(f"Uploading {resolved.name} to Slack...")
            try:
                slack_client.files_upload_v2(
                    channel=args.slack_channel,
                    file=str(resolved),
                    initial_comment=caption
                )
            except Exception as e:
                print(f"Slack error: {e}")


def build_parser():
    parser = argparse.ArgumentParser(description="Generate Sectors social media images from filings/news data.")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["filings-daily", "filings-context", "filings-tags", "news-tier1", "news-tier2"],
        help="Content type to generate.",
    )
    parser.add_argument("--input", help="Optional CSV, JSON, or JSONL override for local QA. Supabase is used by default.")
    parser.add_argument("--output", default="output", help="Output directory.")
    parser.add_argument("--date-label", help="Display date label, defaults to today.")
    parser.add_argument("--hours", type=int, default=24, help="Lookback window for daily filings and news.")
    parser.add_argument("--limit", type=int, help="Maximum records to render for per-item modes.")
    parser.add_argument("--all-news", action="store_true", help="Backfill all tiered news instead of filtering by --hours.")
    parser.add_argument(
        "--filings-since",
        default=DEFAULT_FILINGS_SINCE,
        help="Supabase idx_filings timestamp lower bound, matching the notebook default.",
    )
    parser.add_argument("--slack-channel", help="Slack channel ID to post results to (requires SLACK_BOT_TOKEN).")
    return parser


def main():
    args = build_parser().parse_args()
    generate(args)


if __name__ == "__main__":
    main()
