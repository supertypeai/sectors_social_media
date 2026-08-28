import argparse
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .classification import (
    classify_news,
    filter_daily_filings,
    filter_recent_news,
    filter_tagged_filings,
    group_context_filings,
)
from .insider_patterns import (
    _filing_date,
    _safe_float,
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
    fetch_news_for_symbol,
    fetch_supabase_table,
    fetch_weekly_accumulation,
    fetch_weekly_bandar_plays,
    fetch_weekly_distribution,
    load_records,
)
from .utils.io_helper import next_rotating_theme
from .render import SocialImageRenderer, clean_slug, normalize_tags
from .summarizer import NewsSummarizer
from .social_queue import queue_post, crosspost_to_threads
from .post_routing import scheduled_at_for


def _resolve_theme(theme):
    return next_rotating_theme() if theme == "rotate" else theme


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


# Slack only renders an upload as a channel MESSAGE when it carries an
# initial_comment; a bare file just lands in Files/Media. So every feed post gets
# a branded caption, matching the broker/dividend/AGM posts.
_TAGS = "#IDX #StockMarket #Indonesia"


def _extend_captioned(paths, rp, caption):
    """Append a carousel's slides as (path, caption) tuples. Slide 1 carries the
    full caption + hashtags; extra slides get the title line only, so a 2-slide
    carousel doesn't repeat the hashtag block."""
    title = caption.split("\n", 1)[0]
    for i, slide in enumerate(rp):
        paths.append((slide, caption if i == 0 else title))


def _pattern_filing_excerpts(df, symbols, holder_names, window_start=None, window_end=None, limit=6):
    """Real filing title/body text for a holder+symbol(s) combo, so a caption
    can cite the actually-disclosed transaction purpose (filings often
    literally say "The stated purpose of the transaction was ...") instead of
    inventing a cause. Early filings in a chain carry that real text; later
    ones in the same chain degrade into an auto-generated "Nth insider
    sell..." summary - excerpts with "stated purpose" are surfaced first so
    those aren't crowded out by the generic ones.

    `symbols` may be a single symbol string or an iterable of symbols (e.g.
    for a "cross" pattern spanning several stocks).
    """
    if df is None or df.empty or not holder_names:
        return []

    want_symbols = {symbols} if isinstance(symbols, str) else set(symbols)
    want = {str(h).strip().lower() for h in holder_names}
    sub = df[
        (df["symbol"].isin(want_symbols)) &
        (df["holder_name"].apply(lambda v: str(v).strip().lower() in want))
    ]

    dated = []
    for row in sub.to_dict("records"):
        d = _filing_date(row)
        if d is None:
            continue
        day = d.strftime("%Y-%m-%d")
        if window_start and day < window_start:
            continue
        if window_end and day > window_end:
            continue
        dated.append((d, row))
    dated.sort(key=lambda pair: pair[0])

    def _has_purpose(row):
        return "stated purpose" in str(row.get("body") or "").lower()

    ordered = sorted(dated, key=lambda pair: 0 if _has_purpose(pair[1]) else 1)

    excerpts, seen = [], set()
    for _, row in ordered:
        body = str(row.get("body") or "").strip()
        title = str(row.get("title") or "").strip()
        if not body and not title:
            continue
        if body in seen:
            continue
        seen.add(body)
        excerpts.append({"title": title or "(untitled filing)", "text": body[:500]})
        if len(excerpts) >= limit:
            break
    return excerpts


def _find_counterparty_filing(df, symbol, date_str, shares, exclude_holder, day_tolerance=1, pct_tolerance=0.02):
    """Best-effort match for the other side of a negotiated block trade: another
    holder who filed the opposite-direction transaction for ~the same share
    count on the same symbol within a day or two of the crossing filing.
    """
    if df is None or df.empty or not shares or not date_str:
        return None

    exclude = str(exclude_holder).strip().lower()
    sub = df[
        (df["symbol"] == symbol) &
        (df["holder_name"].apply(lambda v: str(v).strip().lower() != exclude))
    ]
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None

    best, best_diff = None, None
    for row in sub.to_dict("records"):
        d = _filing_date(row)
        if d is None or abs((d.date() - target.date()).days) > day_tolerance:
            continue
        amount = _safe_float(row.get("amount_transaction"))
        if not amount:
            continue
        diff = abs(amount - shares) / shares
        if diff > pct_tolerance:
            continue
        if best_diff is None or diff < best_diff:
            best_diff, best = diff, row
    return best


def _ownership_note(symbol):
    """Short factual note on who runs/owns the company - key executives and
    the major-shareholder cap table - so a caption can note e.g. that an
    acting holder is a minority stakeholder relative to a family/group that
    holds board control, without inventing a controlling-family label that
    isn't evidenced by the data (e.g. a shared surname across executives)."""
    try:
        df = fetch_supabase_table(
            "idx_company_report",
            columns="symbol,key_executives,major_shareholders",
            symbol_column="symbol",
            symbol_value=f"{symbol}.JK" if not symbol.endswith(".JK") else symbol,
        )
    except Exception:
        return None
    if df.empty:
        return None

    row = df.to_dict("records")[0]
    lines = []

    execs = row.get("key_executives")
    if isinstance(execs, list) and execs:
        names = "; ".join(
            f"{e.get('name')} ({e.get('position')})" for e in execs if e.get("name")
        )
        if names:
            lines.append(f"Key executives: {names}.")

    holders = row.get("major_shareholders")
    if isinstance(holders, list) and holders:
        parts = []
        for h in sorted(holders, key=lambda x: _safe_float(x.get("share_percentage")) or 0, reverse=True):
            pct = _safe_float(h.get("share_percentage"))
            if h.get("name") and pct is not None:
                parts.append(f"{h['name']} {pct * 100:.1f}%")
        if parts:
            lines.append("Major shareholders: " + ", ".join(parts) + ".")

    return " ".join(lines) if lines else None


def _insider_caption(p, feed, df=None, summarizer=None):
    sym = str(p.get("base_symbol") or p.get("symbol") or "").upper()
    direction = str(p.get("direction") or "").lower()
    kind = p.get("kind")
    if kind == "cross":
        holder = p.get("holder_name") or "One insider"
        n = len(p.get("stocks") or [])
        across = f"{n} stocks" if n else "multiple stocks"
        title = f":arrows_counterclockwise: *{holder} trading across {across}*"
    elif kind == "chain":
        holder = p.get("holder_name") or "An insider"
        verb = "bought" if direction == "buy" else "sold"
        title = f":link: *{holder} {verb} {sym} repeatedly*"
    else:  # cluster
        word = "buy" if direction == "buy" else "sell"
        title = f":busts_in_silhouette: *Insider {word} cluster — {sym}*"

    insight = None
    if summarizer is not None and df is not None and kind in {"cluster", "chain", "cross"}:
        try:
            if kind == "cluster":
                holder_names = [h["name"] for h in (p.get("roster") or []) if h.get("name")]
                excerpts = _pattern_filing_excerpts(
                    df, p.get("symbol"), holder_names,
                    window_start=p.get("window_start"), window_end=p.get("window_end"),
                )
                news_articles = fetch_news_for_symbol(sym, since=p.get("window_start"))
                ownership_note = _ownership_note(sym)
                insight = summarizer.generate_insider_cluster_caption(p, excerpts, news_articles, ownership_note)
            elif kind == "chain":
                holder_names = [p.get("holder_name")] if p.get("holder_name") else []
                excerpts = _pattern_filing_excerpts(
                    df, p.get("symbol"), holder_names,
                    window_start=p.get("window_start"), window_end=p.get("window_end"),
                )
                news_articles = fetch_news_for_symbol(sym, since=p.get("window_start"))
                insight = summarizer.generate_insider_chain_caption(p, excerpts, news_articles)
            else:  # cross: one holder rotating across several stocks
                holder = p.get("holder_name")
                stocks = p.get("stocks") or []
                stock_symbols = [s["symbol"] for s in stocks if s.get("symbol")]
                excerpts = _pattern_filing_excerpts(
                    df, stock_symbols, [holder] if holder else [],
                    window_start=p.get("window_start"), window_end=p.get("window_end"),
                )
                news_articles = []
                # Stocks are pre-sorted by value desc - only the biggest few
                # are worth grounding; a 6-stock rotation doesn't need news
                # for every name.
                for s in stocks[:3]:
                    news_articles.extend(
                        fetch_news_for_symbol(s["base_symbol"], since=p.get("window_start"), limit=3)
                    )
                insight = summarizer.generate_insider_cross_caption(p, excerpts, news_articles)
        except Exception as error:
            print(f"Insider caption LLM failed for {sym or p.get('holder_name')}: {error}")

    body = f"\n\n{insight}" if insight else ""
    feedtag = "#InsiderStory" if feed == "story" else "#InsiderSignal"
    return f"{title}{body}\n\n{_TAGS} {feedtag} #SectorsApp"


def _becoming_caption(e, df=None, summarizer=None):
    sym = str(e.get("base_symbol") or e.get("symbol") or "").upper()
    holder = e.get("holder_name") or "An insider"
    title = f":star2: *{holder} crossed 5% ownership in {sym}*"

    insight = None
    if summarizer is not None and df is not None:
        try:
            excerpts = _pattern_filing_excerpts(
                df, e.get("symbol"), [holder],
                window_start=e.get("first_date"), window_end=e.get("cross_date"),
            )
            counterparty = _find_counterparty_filing(
                df, e.get("symbol"), e.get("cross_date"), e.get("cross_shares"), holder,
            )
            news_articles = fetch_news_for_symbol(sym, since=e.get("first_date"))
            insight = summarizer.generate_becoming_insider_caption(e, excerpts, counterparty, news_articles)
        except Exception as error:
            print(f"Becoming-insider caption LLM failed for {sym}: {error}")

    body = f"\n\n{insight}" if insight else ""
    return f"{title}{body}\n\n{_TAGS} #InsiderTrading #SectorsApp"


def _todays_broker_bandar_images():
    """Look up today's already-queued broker-bandar IG row so broker-trending
    (which always runs right after it, in the same broker_social.yml job's
    `for MODE in broker-bandar broker-trending` loop) can combine both into
    ONE Threads post instead of two separate ones."""
    from .social_queue import _client, TABLE, parse_image_urls

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        client = _client()
        result = (
            client.table(TABLE)
            .select("image_url")
            .eq("platform", "ig")
            .eq("content_type", "broker-bandar")
            .gte("created_at", f"{today}T00:00:00")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as error:
        print(f"Threads crosspost lookup failed for broker-bandar: {error}")
        return []
    if not result.data:
        return []
    return parse_image_urls(result.data[0].get("image_url"))


def _earnings_caption(s, summarizer=None):
    sym = str(s.get("base_symbol") or s.get("symbol") or "").upper()
    word = "jumped" if s.get("direction") == "spike" else "fell"
    quarter = str(s.get("latest_quarter") or "").replace("-", " ")  # "Q1-2026" -> "Q1 2026"
    g = s.get("earnings_growth")
    # State the comparison explicitly (YoY) so the headline can't be misread as QoQ.
    pct = f" {abs(g) * 100:.0f}% YoY" if g is not None else ""
    lead = f"{quarter} net profit {word}{pct}" if quarter else f"quarterly net profit {word}{pct}"
    header = f":zap: *{sym} — {lead}*"

    insight = None
    if summarizer is not None:
        try:
            quarters = s.get("quarters") or []
            # Cover the whole comparison window so an M&A/dividend/other event
            # anywhere between the base and latest quarter still gets caught.
            since = quarters[-5].get("date") if len(quarters) >= 5 else None
            news_articles = fetch_news_for_symbol(sym, since=since)
            insight = summarizer.generate_earnings_caption(s, news_articles)
        except Exception as error:
            print(f"Earnings caption LLM failed for {sym}: {error}")

    body = f"\n\n{insight}" if insight else ""
    return f"{header}{body}\n\n{_TAGS} #Earnings #SectorsApp"


def load_input(args, kind):
    if args.input:
        return load_records(args.input)
    if kind == "filings":
        since = args.filings_since
        if since is None:
            if args.mode in FEED_LOOKBACK_DAYS:
                since = (datetime.now() - timedelta(days=FEED_LOOKBACK_DAYS[args.mode])).isoformat()
            elif args.mode == "filings-plain":
                # Window is "yesterday" by filing timestamp, but some of yesterday's
                # filings are scraped a day or two late — fetch a small created_at
                # buffer so they're present before the timestamp filter runs.
                since = (datetime.now() - timedelta(days=5)).isoformat()
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

    def _queue(base_content_type, image_paths, caption, content_type=None):
        # --dry-run means "render locally, touch nothing external" - the
        # DB/Storage queue counts as external the same way Slack does, so
        # skip it here rather than at each call site.
        if args.dry_run:
            return None
        try:
            scheduled_at = scheduled_at_for(base_content_type)
            return queue_post(base_content_type, image_paths, caption, content_type=content_type, scheduled_at=scheduled_at)
        except Exception as error:
            print(f"Queue write failed for {content_type or base_content_type}: {error}")
            return None

    def _crosspost(base_content_type, row, caption, summarizer=None):
        # Reuses the IG row's already-uploaded image_url(s) - never
        # re-renders or re-uploads. No-op if _queue returned None (dry-run,
        # queue failure, or the content type has no Threads policy at all).
        if args.dry_run or not row:
            return
        try:
            crosspost_to_threads(base_content_type, row.get("image_url") or [], caption, summarizer=summarizer)
        except Exception as error:
            print(f"Threads crosspost failed for {base_content_type}: {error}")

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

        try:
            summarizer = NewsSummarizer()
        except Exception as error:
            print(f"LLM insider caption disabled (summarizer init failed): {error}")
            summarizer = None

        state_path = Path(args.state_path) if args.state_path else triggers.DEFAULT_STATE_PATH
        state = triggers.load_state(state_path)
        run_date = args.run_date or datetime.now().strftime("%Y-%m-%d")
        carousel_cap = max(1, (args.max_posts or 4) // 2)  # 2 slides per carousel

        # Keep each carousel's paths together so we can persist state ONLY for
        # items that actually queued successfully (replaces the old "did this
        # upload to Slack" gate now that Slack is gone - queue_post succeeding
        # is the new signal that a carousel is actually going out).
        rendered = []
        queued = []
        dropped = []   # same (symbol, direction) runners-up suppressed this run
        # Only populated (and only crossposted) on the filings-signal branch -
        # filings-story has no Threads policy at all.
        crosspost_image_urls = []
        crosspost_captions = []
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
                        rp = renderer.render_insider_cluster_carousel_dark(p, variant="signal", theme=_resolve_theme(args.theme))
                    elif p["kind"] == "cross":
                        rp = renderer.render_insider_cross_card_dark(p, theme=_resolve_theme(args.theme))
                    else:
                        rp = renderer.render_insider_chain_carousel_dark(p, variant="signal", theme=_resolve_theme(args.theme))
                except Exception as e:
                    print(f"Render failed for signal {p['kind']} {p.get('base_symbol')}/{p.get('direction')}: {e}")
                    continue
                rendered.append((p, rp))
                caption = _insider_caption(p, "signal", df, summarizer)
                _extend_captioned(paths, rp, caption)
                ident = clean_slug(p.get("base_symbol") or p.get("holder_name"))
                row = _queue(
                    "filings-signal", rp, caption,
                    content_type=f"filings-signal-{p['kind']}-{ident}-{p.get('direction')}",
                )
                if row:
                    queued.append((p, rp))
                    crosspost_image_urls.extend(row.get("image_url") or [])
                    crosspost_captions.append(caption)
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
                        rp = renderer.render_insider_cluster_carousel_dark(p, variant="story", story=story, theme=_resolve_theme(args.theme))
                    else:
                        rp = renderer.render_insider_chain_carousel_dark(p, variant="story", story=story, theme=_resolve_theme(args.theme))
                except Exception as e:
                    print(f"Render failed for story {p['kind']} {p.get('base_symbol')}/{p.get('direction')}: {e}")
                    continue
                rendered.append((p, rp))
                caption = _insider_caption(p, "story", df, summarizer)
                _extend_captioned(paths, rp, caption)
                ident = clean_slug(p.get("base_symbol") or p.get("holder_name"))
                row = _queue(
                    "filings-story", rp, caption,
                    content_type=f"filings-story-{p['kind']}-{ident}-{p.get('direction')}",
                )
                if row:
                    queued.append((p, rp))

        if args.dry_run:
            print(f"[dry-run] {len(paths)} image(s) generated; state NOT updated")
            for item in paths:
                print(f"[dry-run] {Path(item[0] if isinstance(item, tuple) else item).resolve()}")
            return

        # One combined Threads carousel for the whole run - see the
        # earnings-report crosspost for the same pattern/reasoning. No-op for
        # filings-story (crosspost_image_urls stays empty on that branch).
        if crosspost_image_urls:
            try:
                joined_caption = "\n\n".join(crosspost_captions)
                crosspost_to_threads("filings-signal", crosspost_image_urls, joined_caption, summarizer=summarizer)
            except Exception as error:
                print(f"Threads crosspost failed for filings-signal: {error}")

        posted = queued
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

        try:
            summarizer = NewsSummarizer()
        except Exception as error:
            print(f"LLM becoming-insider caption disabled (summarizer init failed): {error}")
            summarizer = None

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
        queued = []
        crosspost_image_urls = []
        crosspost_captions = []
        for e in selections:
            try:
                rp = renderer.render_becoming_insider_dark(e)
            except Exception as ex:
                print(f"Render failed for becoming {e.get('base_symbol')}/{e.get('holder_name')}: {ex}")
                continue
            rendered.append((e, rp))
            caption = _becoming_caption(e, df, summarizer)
            _extend_captioned(paths, rp, caption)
            row = _queue(
                "filings-becoming", rp, caption,
                content_type=f"filings-becoming-{clean_slug(e.get('base_symbol'))}-{clean_slug(e.get('holder_name'))}",
            )
            if row:
                queued.append((e, rp))
                crosspost_image_urls.extend(row.get("image_url") or [])
                crosspost_captions.append(caption)

        if args.dry_run:
            print(f"[dry-run] {len(paths)} image(s) generated; state NOT updated")
            for item in paths:
                print(f"[dry-run] {Path(item[0] if isinstance(item, tuple) else item).resolve()}")
            return

        # One combined Threads carousel for the whole run - see the
        # earnings-report crosspost above for the same pattern/reasoning.
        if crosspost_image_urls:
            try:
                joined_caption = "\n\n".join(crosspost_captions)
                crosspost_to_threads("filings-becoming", crosspost_image_urls, joined_caption, summarizer=summarizer)
            except Exception as error:
                print(f"Threads crosspost failed for filings-becoming: {error}")

        posted = queued
        for e, _ in posted:
            triggers.record_becoming(state, e, run_date)
        triggers.save_state(state, state_path)
        print(f"Posted {len(posted)}/{len(selections)} carousel(s); state -> {state_path}")
        return

    if args.mode == "earnings-report":
        # Standalone earnings feed: spikes AND drops in one pass, deduped on
        # (symbol, quarter, direction), recency-gated to the current season.
        from . import triggers

        try:
            summarizer = NewsSummarizer()
        except Exception as error:
            print(f"LLM earnings caption disabled (summarizer init failed): {error}")
            summarizer = None

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
        queued = []
        crosspost_image_urls = []
        crosspost_captions = []
        for s in selections:
            try:
                rp = renderer.render_earnings_spike_dark(s)
            except Exception as ex:
                print(f"Render failed for earnings {s.get('base_symbol')}/{s.get('direction')}: {ex}")
                continue
            rendered.append((s, rp))
            caption = _earnings_caption(s, summarizer)
            _extend_captioned(paths, rp, caption)
            row = _queue(
                "earnings-report", rp, caption,
                content_type=f"earnings-report-{clean_slug(s.get('base_symbol'))}-{s.get('direction')}",
            )
            if row:
                queued.append((s, rp))
                crosspost_image_urls.extend(row.get("image_url") or [])
                crosspost_captions.append(caption)

        if args.dry_run:
            print(f"[dry-run] {len(paths)} image(s) generated; state NOT updated")
            for item in paths:
                print(f"[dry-run] {Path(item[0] if isinstance(item, tuple) else item).resolve()}")
            return

        # One combined Threads carousel for the whole run rather than one
        # crosspost per symbol: all of today's report captions get joined
        # and paraphrased together into a single caption backing a single
        # carousel of every report card.
        if crosspost_image_urls:
            try:
                joined_caption = "\n\n".join(crosspost_captions)
                crosspost_to_threads("earnings-report", crosspost_image_urls, joined_caption, summarizer=summarizer)
            except Exception as error:
                print(f"Threads crosspost failed for earnings-report: {error}")

        posted = queued
        for s, _ in posted:
            triggers.record_earnings(state, s, run_date)
        triggers.save_state(state, state_path)
        print(f"Posted {len(posted)}/{len(selections)} carousel(s); state -> {state_path}")
        return

    if args.mode in {"filings-daily", "filings-plain", "filings-context", "filings-cluster-dark", "filings-cluster-signal-dark", "filings-chain-dark", "filings-chain-signal-dark", "filings-cross-dark", "filings-becoming-insider-dark", "filings-tags"}:
        df = load_input(args, "filings")

        if args.mode == "filings-plain":
            # Morning feed: yesterday's plain insider filings by event timestamp.
            # run_date (a WIB-naive "YYYY-MM-DD") lets us replay a past day; None
            # = live WIB now. filter_plain_filings parses it.
            filtered = filter_plain_filings(df, now=args.run_date or None)
            rows = filtered.to_dict("records")
            if args.limit:
                rows = rows[: args.limit]
            print(f"Plain filings (yesterday, no context, not MESOP/takeover): {len(rows)} row(s)")
            if rows:
                # Label with the filing day (yesterday in WIB), not the run day.
                run_day = (datetime.strptime(args.run_date, "%Y-%m-%d")
                           if args.run_date else datetime.now(timezone.utc) + timedelta(hours=7))
                filing_day_label = (run_day - timedelta(days=1)).strftime("%d %B %Y")
                caption = (f":memo: *Daily insider filings — {filing_day_label}*\n\n"
                           f"{_TAGS} #InsiderTrading #SectorsApp")
                plain_path = renderer.render_daily_filings(rows, filing_day_label)
                paths.append((plain_path, caption))
                row = _queue("filings-plain", plain_path, caption)
                try:
                    summarizer = NewsSummarizer()
                except Exception:
                    summarizer = None
                _crosspost("filings-plain", row, caption, summarizer=summarizer)
            else:
                print("No plain filings for yesterday — nothing to post.")
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
            daily_label = date_label(args.date_label)
            daily_path = renderer.render_daily_filings(rows, daily_label)
            paths.append(daily_path)
            if rows:
                daily_caption = (f":memo: *Daily insider filings — {daily_label}*\n\n"
                                  f"{_TAGS} #InsiderTrading #SectorsApp")
                _queue("filings-daily", daily_path, daily_caption)
        elif args.mode == "filings-context":
            rows = group_context_filings(df)
            if args.limit:
                rows = rows[: args.limit]
            for group in rows:
                context_path = renderer.render_context_filing(group)
                paths.append(context_path)
                context_caption = (
                    f":memo: *{group.get('symbol')} — {group.get('context_pattern') or 'Context'}* "
                    f"({group.get('count')} filing(s))\n\n{_TAGS} #InsiderTrading #SectorsApp"
                )
                _queue(
                    "filings-context", context_path, context_caption,
                    content_type=f"filings-context-{clean_slug(group.get('symbol'))}-{clean_slug(group.get('context_pattern'))}",
                )
        elif args.mode == "filings-cluster-dark":
            clusters = group_insider_clusters(df)
            if args.limit: clusters = clusters[:args.limit]
            print(f"Multi-holder insider clusters (dark): {len(clusters)} (2-slide carousel each)")
            for cluster in clusters:
                paths.extend(renderer.render_insider_cluster_carousel_dark(cluster, theme=_resolve_theme(args.theme)))
        elif args.mode == "filings-cluster-signal-dark":
            clusters = group_insider_clusters(df)
            if args.limit: clusters = clusters[:args.limit]
            print(f"Multi-holder insider clusters (signal dark preview): {len(clusters)} (2-slide carousel each)")
            for cluster in clusters:
                paths.extend(renderer.render_insider_cluster_carousel_dark(cluster, variant="signal", theme=_resolve_theme(args.theme)))
        elif args.mode == "filings-chain-dark":
            chains = group_insider_chains(df)
            if args.limit:
                chains = chains[: args.limit]
            print(f"Single-holder insider chains (dark): {len(chains)} (2-slide carousel each)")
            for chain in chains:
                paths.extend(renderer.render_insider_chain_carousel_dark(chain, theme=_resolve_theme(args.theme)))
        elif args.mode == "filings-chain-signal-dark":
            chains = group_insider_chains(df)
            if args.limit:
                chains = chains[: args.limit]
            print(f"Single-holder insider chains (signal dark preview): {len(chains)} (2-slide carousel each)")
            for chain in chains:
                paths.extend(renderer.render_insider_chain_carousel_dark(chain, variant="signal", theme=_resolve_theme(args.theme)))
        elif args.mode == "filings-cross-dark":
            crosses = group_insider_cross(df)
            if args.limit: crosses = crosses[:args.limit]
            print(f"Cross-stock insider holders (dark): {len(crosses)}")
            for cross in crosses:
                paths.extend(renderer.render_insider_cross_card_dark(cross, theme=_resolve_theme(args.theme)))
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
                tagged_path = renderer.render_tagged_filing(filing)
                paths.append(tagged_path)
                tags = normalize_tags(filing.get("tags_parsed") or [])
                important = next((t for t in tags if t.lower() in {"takeover", "mesop"}), tags[0] if tags else "Important Filing")
                title = filing.get("headline") or filing.get("title") or "Important Filing"
                tagged_caption = (
                    f":memo: *{important.upper()} — {filing.get('symbol') or ''}*\n\n{title}\n\n"
                    f"{_TAGS} #InsiderTrading #SectorsApp"
                )
                _queue(
                    "filings-tags", tagged_path, tagged_caption,
                    content_type=f"filings-tags-{clean_slug(filing.get('symbol'))}-{clean_slug(important)}",
                )

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
                # Auto-resolved (not an explicit --date-label backfill) - if
                # the latest broker data isn't from today (WIB), the market
                # was likely closed for a holiday, so skip rather than
                # regenerate yesterday's scorecard as if it were today's.
                today_wib = (datetime.now(timezone.utc) + timedelta(hours=7)).strftime("%Y-%m-%d")
                if target_date and target_date != today_wib:
                    print(f"Latest broker data ({target_date}) is not today ({today_wib}) - likely a market holiday, skipping.")
                    target_date = None
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
            _queue("broker-bandar", path, caption)
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
            # Same holiday guard as broker-bandar above.
            today_wib = (datetime.now(timezone.utc) + timedelta(hours=7)).strftime("%Y-%m-%d")
            if target_date and target_date != today_wib:
                print(f"Latest broker data ({target_date}) is not today ({today_wib}) - likely a market holiday, skipping.")
                target_date = None
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
                row = _queue("broker-trending", path, caption)
                if row and not args.dry_run:
                    combined_images = _todays_broker_bandar_images() + (row.get("image_url") or [])
                    try:
                        crosspost_to_threads("broker-trending", combined_images, None)
                    except Exception as error:
                        print(f"Threads crosspost failed for broker-trending: {error}")
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
                # No individual Threads crosspost here - broker-weekly's
                # images get folded into foreign-flow's combined "Weekly
                # Update" post the next morning (see workflow_cli.foreign_flow()).
                _queue("broker-weekly", path, caption)
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
                    _queue("weekly-accumulation", path, caption)
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
                    _queue("weekly-distribution", path, caption)
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
                    _queue("weekly-bandar", path, caption)
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
                # No individual Threads crosspost here - news-tier1's images
                # get folded into agm's combined "Daily News & AGM Update"
                # post later the same day (see workflow_cli.agm()).
                _queue("news-tier1", path, caption)
            else:
                print("No Tier 1 news in window; skipping digest.")
        elif args.mode == "news-tier2":
            rows = df[df["tier"] == "Tier 2"].to_dict("records")
            if args.limit:
                rows = rows[: args.limit]
            tier2_label = date_label(args.date_label)
            tier2_path = renderer.render_tier2_news_summary(rows, tier2_label)
            paths.append(tier2_path)
            if rows:
                tier2_caption = f":memo: *Tier 2 IDX News — {tier2_label}*\n\n{_TAGS} #SectorsApp"
                _queue("news-tier2", tier2_path, tier2_caption)

    if args.max_posts and len(paths) > args.max_posts:
        print(f"Capping output at {args.max_posts} posts (would have been {len(paths)})")
        paths = paths[: args.max_posts]

    if args.dry_run:
        print(f"[dry-run] {len(paths)} post(s) generated; state NOT updated")
        for item in paths:
            path = item[0] if isinstance(item, tuple) else item
            print(f"[dry-run] {Path(path).resolve()}")
        return


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
    parser.add_argument("--theme", default="default",
                        help="Color theme for insider cluster/chain/cross carousels "
                             "(default, aurora, ember, neon). Use 'rotate' to cycle "
                             "them per post via state/theme_rotation.json.")
    parser.add_argument("--max-posts", type=int, default=3, help="Hard cap on total Slack posts emitted per run. Defaults to 3.")
    parser.add_argument("--dry-run", action="store_true", help="Generate images but skip Slack upload.")
    parser.add_argument("--all-news", action="store_true", help="Backfill all tiered news instead of filtering by --hours.")
    parser.add_argument(
        "--filings-since",
        help="Supabase idx_filings timestamp lower bound, matching the notebook default.",
    )
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
