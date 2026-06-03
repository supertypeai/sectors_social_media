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
    group_tier1_news,
)
from .data import (
    fetch_company_profiles, 
    fetch_filings, 
    fetch_news, 
    load_records,
    fetch_dividend_history,
)
from .utils.slack import upload_posts_to_slack
from .render import SocialImageRenderer
from .summarizer import NewsSummarizer


SNAPSHOT_CATEGORIES = {"Dividend Announcement", "Suspension", "Rights Issue", "IPO", "Stock Buyback"}


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
        if not df.empty and "created_at" in df.columns:
            print(f"After {args.hours}h filter: {len(df)} news rows, oldest={df['created_at'].min()}, newest={df['created_at'].max()}")
        if args.mode == "news-tier1":
            groups = group_tier1_news(df)
            if args.limit:
                groups = groups[: args.limit]
            for group in groups:
                category = group["category"]
                if category not in SNAPSHOT_CATEGORIES:
                    continue
                print(f"Processing category: {category}...")

                for news in group["news"]:
                    title = news.get("title")
                    body = news.get("body") or news.get("summary") or news.get("description") or ""
                    if not (title and body):
                        continue

                    safe_title = title[:50].encode('ascii', 'ignore').decode()

                    if category == "Dividend Announcement":
                        print(f"Extracting dividend data for: {safe_title}...")
                        extracted = summarizer.optimize_dividend_news(title, body)

                        missing_count = sum(1 for k in ["dividend_per_share", "total_dividend", "cum_date", "profit_metric", "payout_ratio"] if extracted.get(k, "-") == "-")
                        if missing_count > 3:
                            print(f"Skipping {safe_title} - too many missing metrics ({missing_count}/5)")
                            news["_skip_render"] = True
                            continue

                        news.update(extracted)
                        from .render import format_tickers
                        tickers_str = format_tickers(news.get("tickers") or news.get("ticker") or news.get("symbol") or "")
                        first_ticker = tickers_str.split("/")[0].strip() if tickers_str else None
                        if first_ticker:
                            ticker_jk = first_ticker if first_ticker.endswith(".JK") else f"{first_ticker}.JK"
                            news["dividend_history"] = fetch_dividend_history(ticker_jk)

                    elif category == "Suspension":
                        print(f"Extracting suspension data for: {safe_title}...")
                        extracted = summarizer.optimize_suspension_news(title, body)

                        if extracted.get("reason", "-") == "-" and extracted.get("effective_date", "-") == "-":
                            print(f"Skipping {safe_title} - no reason or effective date extracted")
                            news["_skip_render"] = True
                            continue

                        news.update(extracted)

                    elif category == "Rights Issue":
                        print(f"Extracting rights issue data for: {safe_title}...")
                        extracted = summarizer.optimize_rights_issue_news(title, body)
                        missing_count = sum(1 for k in ["issue_price", "ratio", "total_size", "cum_date", "use_of_funds"] if extracted.get(k, "-") == "-")
                        if missing_count > 3:
                            print(f"Skipping {safe_title} - too many missing metrics ({missing_count}/5)")
                            news["_skip_render"] = True
                            continue
                        news.update(extracted)

                    elif category == "IPO":
                        print(f"Extracting IPO data for: {safe_title}...")
                        extracted = summarizer.optimize_ipo_news(title, body)
                        missing_count = sum(1 for k in ["offer_price", "offer_size", "listing_date", "market_cap", "use_of_funds"] if extracted.get(k, "-") == "-")
                        if missing_count > 3:
                            print(f"Skipping {safe_title} - too many missing metrics ({missing_count}/5)")
                            news["_skip_render"] = True
                            continue
                        news.update(extracted)

                    elif category == "Stock Buyback":
                        print(f"Extracting buyback data for: {safe_title}...")
                        extracted = summarizer.optimize_buyback_news(title, body)
                        missing_count = sum(1 for k in ["budget", "max_price", "shares_target", "duration", "pct_outstanding"] if extracted.get(k, "-") == "-")
                        if missing_count > 3:
                            print(f"Skipping {safe_title} - too many missing metrics ({missing_count}/5)")
                            news["_skip_render"] = True
                            continue
                        news.update(extracted)
                
                
                # Filter out skipped news
                group["news"] = [n for n in group["news"] if not n.get("_skip_render")]
                
                if not group["news"]:
                    print(f"Skipping {category} - no valid news left after filtering.")
                    continue
                
                pages = renderer.render_tier1_news_group(group, date_label(args.date_label))
                pages = pages[:1]  # one paginated post per category per run; rest dropped to let other categories ship

                for path, page_news in pages:
                    caption = (
                        f":chart_with_upwards_trend: *{len(page_news)} {category} update(s)* "
                        f"— {date_label(args.date_label)}\n"
                        f"See card for details.\n\n"
                        "#IDX #StockMarket #Indonesia #Investing #FinancialData #SectorsApp"
                    )
                    paths.append((path, caption))
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
            "companies-mover"
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