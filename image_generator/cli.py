import argparse
import os
from datetime import datetime, timedelta
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
from .insider_patterns import (
    drop_mixed_leg_filings,
    filter_plain_filings,
    group_becoming_insider,
    group_insider_chains,
    group_insider_clusters,
    group_insider_cross,
    select_earnings_spikes,
)
from .data import (
    fetch_broker_bandar_scorecard,
    fetch_broker_trending_movers,
    fetch_broker_weekly_recap,
    fetch_company_profiles,
    fetch_company_report_earnings,
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


# Window-based modes need months of history to detect patterns, not just 24h.
WINDOW_MODES = {
    "filings-cluster-dark",
    "filings-cluster-signal-dark",
    "filings-chain-dark",
    "filings-chain-signal-dark",
    "filings-cross-dark",
    "filings-becoming-insider-dark",
    "filings-context",
}

# Feed modes need even more history: the story feed reaches back to a pattern's
# last filing (up to 9mo ago) PLUS the 6-month detection window before it.
FEED_LOOKBACK_DAYS = {
    "filings-signal": 260,   # 6mo window + freshness slack
    "filings-story": 520,    # 9mo horizon + 6mo window + buffer
    "filings-becoming": 260, # 6mo accumulation window + freshness slack
}


def _dedupe_key(p):
    """Collapse identity for one run. Cluster/chain dedupe on (base_symbol,
    direction) so a cluster + its chains on the same stock become one carousel.
    Cross is holder-pivoted (no single symbol/direction), so it dedupes on its
    signal_key — a holder's rotation and a stock's cluster are distinct stories
    and must never collide.
    """
    if p.get("kind") == "cross":
        return ("cross", p.get("signal_key"))
    return (p.get("base_symbol"), p.get("direction"))


def _dedupe_symbol_dir(fires):
    """One carousel per dedupe-identity per run. `fires` must be pre-sorted by
    priority; the first hit per key is kept, the rest are dropped (a cluster +
    its chains, or two chains on the same stock, collapse to one).
    Returns (kept, dropped) preserving order.
    """
    seen, kept, dropped = set(), [], []
    for p in fires:
        key = _dedupe_key(p)
        if key in seen:
            dropped.append(p)
        else:
            seen.add(key)
            kept.append(p)
    return kept, dropped


def load_input(args, kind):
    if args.input:
        return load_records(args.input)
    if kind == "filings":
        since = args.filings_since
        if since is None:
            if args.mode in FEED_LOOKBACK_DAYS:
                since = (datetime.now() - timedelta(days=FEED_LOOKBACK_DAYS[args.mode])).isoformat()
            elif args.mode in WINDOW_MODES:
                since = (datetime.now() - timedelta(days=220)).isoformat()
        return fetch_filings(since=since)
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
        
    paths = []

    if args.mode in {"earnings-spike-dark", "earnings-drop-dark"}:
        direction = "drop" if args.mode == "earnings-drop-dark" else "spike"
        df = fetch_company_report_earnings()
        spikes = select_earnings_spikes(df, direction=direction)
        if args.limit:
            spikes = spikes[: args.limit]
        label = "drops" if direction == "drop" else "spikes"
        print(f"Earnings {label} (report-led): {len(spikes)} (2-slide carousel each)")
        for spike in spikes:
            paths.extend(renderer.render_earnings_spike_dark(spike))

    if args.mode in {"filings-signal", "filings-story"}:
        from . import triggers
        from .data import fetch_daily_prices

        df = load_input(args, "filings")
        df = drop_mixed_leg_filings(df)  # corrupt netted filings out of BOTH feeds
        patterns = group_insider_clusters(df) + group_insider_chains(df)
        state_path = Path(args.state_path) if args.state_path else triggers.DEFAULT_STATE_PATH
        state = triggers.load_state(state_path)
        run_date = args.run_date or datetime.now().strftime("%Y-%m-%d")
        carousel_cap = max(1, (args.max_posts or 4) // 2)  # 2 slides per carousel

        # Keep each carousel's paths together so we can persist state ONLY for
        # carousels whose slides actually uploaded (a swallowed Slack error must
        # not burn a dedup key — see upload_posts_to_slack).
        rendered = []  # list of (pattern, [slide_paths])
        dropped = []   # same (symbol, direction) runners-up suppressed this run
        if args.mode == "filings-signal":
            # Cross (holder rotation) rides the SIGNAL feed only — never the story
            # feed, where a mixed-direction basket's "return since" is ambiguous.
            cross_patterns = group_insider_cross(df)
            fires = triggers.select_signal_fires(patterns + cross_patterns, run_date, state)
            # Recency-first: with cap 1, the single slot goes to the FRESHEST
            # completion so a brand-new signal isn't starved (and aged out of the
            # 7-day window) by an older-but-bigger one. Ties broken flagship-first
            # (cluster > chain > cross), then biggest value.
            kind_rank = {"cluster": 0, "chain": 1, "cross": 2}
            fires.sort(key=lambda p: (
                p.get("completed_date") or "",        # newest completion wins
                -kind_rank.get(p.get("kind"), 9),     # then cluster > chain > cross
                p.get("total_value") or 0,            # then biggest value
            ), reverse=True)
            kept, dropped = _dedupe_symbol_dir(fires)
            selections = kept[:carousel_cap]
            print(f"Signal feed: {len(fires)} fresh, {len(kept)} after dedupe; posting {len(selections)}")
            for p in selections:
                try:
                    if p["kind"] == "cluster":
                        rp = renderer.render_insider_cluster_carousel_dark(p, variant="signal")
                    elif p["kind"] == "cross":
                        rp = renderer.render_insider_cross_card_dark(p)
                    else:
                        rp = renderer.render_insider_chain_carousel_dark(p, variant="signal")
                except Exception as e:
                    print(f"Render failed for signal {p['kind']} {p.get('base_symbol')}/{p.get('direction')}: {e}")
                    continue
                rendered.append((p, rp))
                paths.extend(rp)
        else:  # filings-story
            def _price_fetcher(symbol, completed):
                since = (completed - timedelta(days=14)).strftime("%Y-%m-%d")
                until = datetime.now().strftime("%Y-%m-%d")
                try:
                    pdf = fetch_daily_prices(symbol, since=since, until=until)
                except Exception as e:
                    print(f"Story price fetch failed for {symbol}: {e}")
                    return {}
                if pdf is None or pdf.empty:
                    return {}
                return {str(d)[:10]: float(c) for d, c in zip(pdf["date"], pdf["close"]) if c is not None}

            fires = triggers.select_story_fires(patterns, run_date, state, _price_fetcher)
            fires.sort(key=lambda p: abs(p["_story"]["move"]), reverse=True)
            kept, dropped = _dedupe_symbol_dir(fires)
            selections = kept[:carousel_cap]
            print(f"Story feed: {len(fires)} checkpoint(s), {len(kept)} after symbol-dedupe; posting {len(selections)}")
            for p in selections:
                story = p["_story"]
                try:
                    if p["kind"] == "cluster":
                        rp = renderer.render_insider_cluster_carousel_dark(p, variant="story", story=story)
                    else:
                        rp = renderer.render_insider_chain_carousel_dark(p, variant="story", story=story)
                except Exception as e:
                    print(f"Render failed for story {p['kind']} {p.get('base_symbol')}/{p.get('direction')}: {e}")
                    continue
                rendered.append((p, rp))
                paths.extend(rp)

        if args.dry_run:
            print(f"[dry-run] {len(paths)} image(s) generated; state NOT updated")
            for item in paths:
                print(f"[dry-run] {Path(item[0] if isinstance(item, tuple) else item).resolve()}")
            return

        uploaded = set(upload_posts_to_slack(paths, slack_channel=args.slack_channel)) if paths else set()
        # A carousel counts as posted only if EVERY one of its slides uploaded.
        posted = [(p, rp) for (p, rp) in rendered if rp and all(s in uploaded for s in rp)]
        posted_keys = {_dedupe_key(p) for p, _ in posted}
        if args.mode == "filings-signal":
            for p, _ in posted:
                triggers.record_signal(state, p, run_date)
            # Runners-up on a dedupe-identity we DID post are covered by it.
            for p in dropped:
                if _dedupe_key(p) in posted_keys:
                    triggers.record_signal(state, p, run_date)
        else:
            for p, _ in posted:
                triggers.record_story(state, p, run_date)
            for p in dropped:
                if _dedupe_key(p) in posted_keys:
                    triggers.retire_story(state, p, run_date)
            # Under-gate / price-insane horizons never post regardless of Slack.
            triggers.record_story_skips(state, patterns, run_date)
        triggers.save_state(state, state_path)
        print(f"Posted {len(posted)}/{len(selections)} carousel(s); state -> {state_path}")
        return

    if args.mode == "filings-becoming":
        # Standalone becoming-insider feed: fresh 5% crossings, own state file,
        # never mixed with the cluster/chain/cross signal feed.
        from . import triggers

        df = load_input(args, "filings")
        df = drop_mixed_leg_filings(df)
        events = group_becoming_insider(df)
        state_path = Path(args.state_path) if args.state_path else triggers.BECOMING_STATE_PATH
        state = triggers.load_becoming_state(state_path)
        run_date = args.run_date or datetime.now().strftime("%Y-%m-%d")
        carousel_cap = max(1, (args.max_posts or 4) // 2)

        fires = triggers.select_becoming_fires(events, run_date, state)
        # Recency-first (newest crossing wins the single slot), then bigger stake.
        fires.sort(key=lambda e: (e.get("cross_date") or "", e.get("stake_after") or 0), reverse=True)
        selections = fires[:carousel_cap]
        print(f"Becoming-insider feed: {len(fires)} fresh crossing(s); posting {len(selections)}")
        rendered = []
        for e in selections:
            try:
                rp = renderer.render_becoming_insider_dark(e)
            except Exception as ex:
                print(f"Render failed for becoming {e.get('base_symbol')}/{e.get('holder_name')}: {ex}")
                continue
            rendered.append((e, rp))
            paths.extend(rp)

        if args.dry_run:
            print(f"[dry-run] {len(paths)} image(s) generated; state NOT updated")
            for item in paths:
                print(f"[dry-run] {Path(item[0] if isinstance(item, tuple) else item).resolve()}")
            return

        uploaded = set(upload_posts_to_slack(paths, slack_channel=args.slack_channel)) if paths else set()
        posted = [(e, rp) for (e, rp) in rendered if rp and all(s in uploaded for s in rp)]
        for e, _ in posted:
            triggers.record_becoming(state, e, run_date)
        triggers.save_state(state, state_path)
        print(f"Posted {len(posted)}/{len(selections)} carousel(s); state -> {state_path}")
        return

    if args.mode == "earnings-report":
        # Standalone earnings feed: spikes AND drops in one pass, deduped on
        # (symbol, quarter, direction), recency-gated to the current season.
        from . import triggers

        df = fetch_company_report_earnings()
        spikes = select_earnings_spikes(df, direction="spike")
        drops = select_earnings_spikes(df, direction="drop")
        state_path = Path(args.state_path) if args.state_path else triggers.EARNINGS_STATE_PATH
        state = triggers.load_earnings_state(state_path)
        run_date = args.run_date or datetime.now().strftime("%Y-%m-%d")
        carousel_cap = max(1, (args.max_posts or 2) // 2)

        fires = triggers.select_earnings_fires(spikes + drops, run_date, state)
        # Biggest absolute YoY move first — the most newsworthy report leads.
        fires.sort(key=lambda s: abs(s.get("earnings_growth") or 0), reverse=True)
        selections = fires[:carousel_cap]
        print(f"Earnings feed: {len(fires)} unposted report(s); posting {len(selections)}")
        rendered = []
        for s in selections:
            try:
                rp = renderer.render_earnings_spike_dark(s)
            except Exception as ex:
                print(f"Render failed for earnings {s.get('base_symbol')}/{s.get('direction')}: {ex}")
                continue
            rendered.append((s, rp))
            paths.extend(rp)

        if args.dry_run:
            print(f"[dry-run] {len(paths)} image(s) generated; state NOT updated")
            for item in paths:
                print(f"[dry-run] {Path(item[0] if isinstance(item, tuple) else item).resolve()}")
            return

        uploaded = set(upload_posts_to_slack(paths, slack_channel=args.slack_channel)) if paths else set()
        posted = [(s, rp) for (s, rp) in rendered if rp and all(p in uploaded for p in rp)]
        for s, _ in posted:
            triggers.record_earnings(state, s, run_date)
        triggers.save_state(state, state_path)
        print(f"Posted {len(posted)}/{len(selections)} carousel(s); state -> {state_path}")
        return

    if args.mode in {"filings-daily", "filings-plain", "filings-context", "filings-cluster-dark", "filings-cluster-signal-dark", "filings-chain-dark", "filings-chain-signal-dark", "filings-cross-dark", "filings-becoming-insider-dark", "filings-tags"}:
        df = load_input(args, "filings")

        if args.mode == "filings-plain":
            filtered = filter_plain_filings(df, hours=args.hours)
            rows = filtered.to_dict("records")
            if args.limit:
                rows = rows[: args.limit]
            print(f"Plain filings (no context, not MESOP/takeover): {len(rows)} row(s)")
            paths.append(renderer.render_daily_filings(rows, date_label(args.date_label)))
        elif args.mode == "filings-daily":
            filtered = filter_daily_filings(df, hours=args.hours)
            rows = filtered.to_dict("records")
            if args.limit:
                rows = rows[: args.limit]
            print(f"Daily filings: {len(rows)} row(s)")
            summarizer = NewsSummarizer()
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
        elif args.mode == "filings-cluster-dark":
            clusters = group_insider_clusters(df)
            if args.limit: clusters = clusters[:args.limit]
            print(f"Multi-holder insider clusters (dark): {len(clusters)} (2-slide carousel each)")
            for cluster in clusters:
                paths.extend(renderer.render_insider_cluster_carousel_dark(cluster))
        elif args.mode == "filings-cluster-signal-dark":
            clusters = group_insider_clusters(df)
            if args.limit: clusters = clusters[:args.limit]
            print(f"Multi-holder insider clusters (signal dark preview): {len(clusters)} (2-slide carousel each)")
            for cluster in clusters:
                paths.extend(renderer.render_insider_cluster_carousel_dark(cluster, variant="signal"))
        elif args.mode == "filings-chain-dark":
            chains = group_insider_chains(df)
            if args.limit:
                chains = chains[: args.limit]
            print(f"Single-holder insider chains (dark): {len(chains)} (2-slide carousel each)")
            for chain in chains:
                paths.extend(renderer.render_insider_chain_carousel_dark(chain))
        elif args.mode == "filings-chain-signal-dark":
            chains = group_insider_chains(df)
            if args.limit:
                chains = chains[: args.limit]
            print(f"Single-holder insider chains (signal dark preview): {len(chains)} (2-slide carousel each)")
            for chain in chains:
                paths.extend(renderer.render_insider_chain_carousel_dark(chain, variant="signal"))
        elif args.mode == "filings-cross-dark":
            crosses = group_insider_cross(df)
            if args.limit: crosses = crosses[:args.limit]
            print(f"Cross-stock insider holders (dark): {len(crosses)}")
            for cross in crosses:
                paths.extend(renderer.render_insider_cross_card_dark(cross))
        elif args.mode == "filings-becoming-insider-dark":
            events = group_becoming_insider(df)
            if args.limit: events = events[:args.limit]
            print(f"Becoming-insider (5% crossings, dark): {len(events)} (2-slide carousel each)")
            for event in events:
                paths.extend(renderer.render_becoming_insider_dark(event))
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
            "filings-plain",
            "filings-context",
            "filings-cluster-dark",
            "filings-cluster-signal-dark",
            "filings-chain-dark",
            "filings-chain-signal-dark",
            "filings-cross-dark",
            "filings-becoming-insider-dark",
            "filings-signal",
            "filings-story",
            "filings-becoming",
            "earnings-report",
            "earnings-spike-dark",
            "earnings-drop-dark",
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
    parser.add_argument(
        "--state-path",
        help="JSON dedup-state file for the signal/story feeds (default: state/posted_insider.json).",
    )
    parser.add_argument(
        "--run-date",
        help="Override 'today' for the signal/story feeds (YYYY-MM-DD) — for testing/backfill.",
    )
    return parser


def main():
    args = build_parser().parse_args()
    generate(args)


if __name__ == "__main__":
    main()

# python -m image_generator.cli --mode companies-mover
# python -m image_generator.cli --mode quarterly-low
