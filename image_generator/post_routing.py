"""Single source of truth for which content types get queued to
social_post_queue, and as which post_type ('feed' vs 'story'), plus when
each one should actually go out (scheduled_at).

Keyed by the command/mode name exactly as it's invoked (--mode X for
cli.py, or the Typer command name for workflow_cli.py). A value of None
means "don't queue this" - the generator command still runs and can still
post to Slack as before, it just skips the upsert_post step entirely: no
row, no image upload, no scheduled_at.

This is the only place that decision lives - to turn queuing on/off for a
content type, move it between feed and story, or change when it posts,
edit this file rather than hardcoding the choice at each call site.
"""

from datetime import datetime, time, timedelta, timezone

WIB = timezone(timedelta(hours=7))

POST_TYPE_BY_CONTENT_TYPE: dict[str, str | None] = {
    # ── feed: LLM-grounded captions ──────────────────────────────────────
    "filings-becoming": "feed",    # insider crossing 5% ownership
    "filings-signal": "feed",      # insider cluster / cross / chain (signal feed)
    "filings-story": "feed",       # insider cluster / chain (story feed)
    "volume-spike": "feed",
    "earnings-report": "feed",     # profit/earnings spike
    "stock-performance": "feed",   # index drivers
    "companies-mover": "feed",     # top movers (1-month leaders/laggards)

    # ── story: static/rule-based captions ────────────────────────────────
    "broker-bandar": "story",      # daily top broker (Bandar Scorecard)
    "broker-trending": "story",    # daily top broker (Trending Movers)
    "filings-daily": "story",      # insider filings (raw digest)
    "filings-plain": "story",      # insider filings (raw digest)
    "filings-context": "story",    # insider filings (raw digest)
    "filings-tags": "story",       # insider filings (raw digest)
    "news-tier1": "story",         # idx_news (tags)
    "news-tier2": "story",         # idx_news (tags)
    "macro-news": "story",         # idx_news (macro news)
    "upcoming-dividend": "story",
    "agm": "story",
    "foreign-flow": "story",
    "weekly-accumulation": "story",  # weekly top-net-buy stocks (Most Accumulated)
    "weekly-distribution": "story",  # weekly top-net-sell stocks (Most Distributed)
    "weekly-bandar": "story",        # weekly top broker-stock pairs (Bandar of the Week)
    "broker-weekly": "story",        # weekly top broker recap
    "dividend": "story",             # recurring dividend post, distinct from upcoming-dividend
    "insider-roundup": "story",

    # ── not yet decided - left null on purpose, don't queue ──────────────
    "quarterly": None,           # workflow_cli.py
    "weekly-movers": None,       # "daily top mover" candidate - unconfirmed
    "anomaly-changes": None,
    "ownership": None,
    "ownership-board": None,
    "sector-heatmap": None,
    "lq45-ytd": None,
}


def post_type_for(content_type: str) -> str | None:
    """'feed', 'story', or None (don't queue) for a content type. Unknown
    content types also return None rather than raising, so a new command
    added later just silently doesn't queue until someone adds it here.
    """
    return POST_TYPE_BY_CONTENT_TYPE.get(content_type)


# When a content type should actually post, independent of when its
# generator runs (e.g. filings-becoming generates Mon-Fri 20:30 WIB, but
# posts the NEXT day at 10:00 WIB - spreads the day's content out for the
# audience instead of dumping it all at generation time).
#
# Each policy is a dict: {"target": "same_day" | "next_day" | "next_weekday",
# "hour": int, "minute": int}, plus "weekday" (0=Monday..6=Sunday) when
# target is "next_weekday". Content types not listed here have no explicit
# post-schedule policy - upsert_post falls back to its own default of "now"
# (due for the very next publisher run).
POST_SCHEDULE_BY_CONTENT_TYPE: dict[str, dict] = {
    "filings-becoming": {"target": "next_day", "hour": 10, "minute": 0},
    "filings-signal": {"target": "next_day", "hour": 11, "minute": 0},
    "earnings-report": {"target": "next_day", "hour": 9, "minute": 0},
    "volume-spike": {"target": "same_day", "hour": 20, "minute": 0},
    "stock-performance": {"target": "same_day", "hour": 21, "minute": 0},
    "companies-mover": {"target": "next_day", "hour": 8, "minute": 0},
    "broker-bandar": {"target": "same_day", "hour": 20, "minute": 0},
    "broker-trending": {"target": "same_day", "hour": 20, "minute": 0},
    # Generated Friday - posts the following Monday at 08:00 WIB.
    "broker-weekly": {"target": "next_weekday", "weekday": 0, "hour": 8, "minute": 0},
    "upcoming-dividend": {"target": "next_day", "hour": 9, "minute": 0},
    "agm": {"target": "same_day", "hour": 19, "minute": 0},
    "macro-news": {"target": "same_day", "hour": 16, "minute": 0},
    "news-tier1": {"target": "same_day", "hour": 13, "minute": 0},
    "filings-plain": {"target": "same_day", "hour": 20, "minute": 0},
    # Generated Saturday - posts the following Monday, same time-of-day.
    "foreign-flow": {"target": "next_weekday", "weekday": 0, "hour": 9, "minute": 0},
}


def scheduled_at_for(content_type: str, now: datetime | None = None) -> str | None:
    """Target scheduled_at (ISO 8601, UTC) for a content type per the post-
    schedule policy above, computed relative to `now` (when the generator
    actually runs). Returns None when there's no explicit policy, so the
    caller can fall back to upsert_post's own "now" default.
    """
    policy = POST_SCHEDULE_BY_CONTENT_TYPE.get(content_type)
    if policy is None:
        return None

    now = now or datetime.now(timezone.utc)
    now_wib = now.astimezone(WIB)

    target = policy["target"]
    if target == "same_day":
        target_date = now_wib.date()
    elif target == "next_day":
        target_date = now_wib.date() + timedelta(days=1)
    elif target == "next_weekday":
        # Always strictly in the future - if generation ever lands ON the
        # target weekday, that means next week's occurrence, not today's.
        delta = (policy["weekday"] - now_wib.weekday()) % 7 or 7
        target_date = now_wib.date() + timedelta(days=delta)
    else:
        raise ValueError(f"unknown scheduled_at target mode: {target!r}")

    target_wib = datetime.combine(target_date, time(policy["hour"], policy["minute"]), tzinfo=WIB)
    return target_wib.astimezone(timezone.utc).isoformat()
