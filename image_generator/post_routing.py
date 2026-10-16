"""Single source of truth for which content types get queued to Mailroom,
and as which post_type ('feed' vs 'story'), plus when each one should
actually go out (scheduled_at).

Keyed by the command/mode name exactly as it's invoked (--mode X for
cli.py, or the Typer command name for workflow_cli.py). A value of None
means "don't queue this" - the generator command still runs and still
renders its images, it just skips the upsert_post step entirely: no post,
no image upload, no scheduled_at.

This is the only place that decision lives - to turn queuing on/off for a
content type, move it between feed and story, or change when it posts,
edit this file rather than hardcoding the choice at each call site.
"""

from datetime import datetime, time, timedelta, timezone

WIB = timezone(timedelta(hours=7))

POST_TYPE_BY_CONTENT_TYPE: dict[str, str | None] = {
    # ── redesigned posts (Sectors Hairline, image_generator/redesign_cli.py) ──
    # feed carousels, one weekly slot each
    "news-flash": "feed",          # Wed - the week's top stories (maroon)
    "weekly-calendar": "feed",     # Mon - the week's corporate actions (maroon)
    "insider-carousel": "feed",    # Tue - one insider move, 5 slides (blue)
    "earnings-carousel": "feed",   # Thu - one earnings report, 4-5 slides (blue)
    # daily stories, one image each (light); breaking news is posted by hand
    "story-news": "story",         # news compilation
    "story-volume": "story",       # volume spike
    "story-broker": "story",       # top 5 brokers (podium)
    "story-movers": "story",       # top movers (list)
    "story-crossing": "story",     # new 5% holder

    # ── retired 2026-10 (replaced by the redesigned posts above) ────────
    # Kept as None so a stray cron-job.org / manual run can't post them.
    "filings-becoming": None,
    "filings-signal": None,
    "filings-story": None,
    "volume-spike": None,
    "earnings-report": None,
    "stock-performance": None,
    "companies-mover": None,
    "broker-bandar": None,
    "broker-trending": None,
    "filings-daily": None,
    "filings-plain": None,
    "filings-context": None,
    "filings-tags": None,
    "news-tier1": None,
    "news-tier2": None,
    "macro-news": None,
    "upcoming-dividend": None,
    "agm": None,
    "foreign-flow": None,
    "weekly-accumulation": None,
    "weekly-distribution": None,
    "weekly-bandar": None,
    "broker-weekly": None,
    "dividend": None,
    "insider-roundup": None,

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


# Which Mailroom content group a content type belongs to - the theme, not the
# generator job, so the dashboard rolls up by subject rather than listing all
# 25 content types. The group also becomes a folder in the stored image's
# object key, so it has to be a valid slug: lowercase, [a-z0-9-], max 40.
#
# A content type's IG post and its Threads crosspost share a group, so a theme
# reads as one group across both platforms.
CONTENT_GROUP_BY_CONTENT_TYPE: dict[str, str] = {
    # Insider filings, in all their renderings.
    "filings-becoming": "filings",
    "filings-signal": "filings",
    "filings-story": "filings",
    "filings-plain": "filings",
    "filings-daily": "filings",
    "filings-context": "filings",
    "filings-tags": "filings",
    "insider-roundup": "filings",

    # Company financials and payouts.
    "earnings-report": "financial",
    "dividend": "financial",
    "upcoming-dividend": "financial",

    # Price and flow movements.
    "volume-spike": "volume",
    "stock-performance": "volume",
    "companies-mover": "volume",
    "foreign-flow": "volume",
    "weekly-accumulation": "volume",
    "weekly-distribution": "volume",

    # Broker activity, daily and weekly.
    "broker-bandar": "broker",
    "broker-trending": "broker",
    "broker-weekly": "broker",
    "weekly-bandar": "broker",

    "news-tier1": "news",
    "news-tier2": "news",
    "macro-news": "news",

    "agm": "news",
    # Redesigned posts.
    "news-flash": "news",
    "story-news": "news",
    "weekly-calendar": "calendar",
    "insider-carousel": "filings",
    "story-crossing": "filings",
    "earnings-carousel": "financial",
    "story-volume": "volume",
    "story-movers": "volume",
    "story-broker": "broker",
}


def content_group_for(content_type: str) -> str:
    """The content group a content type is filed under. Falls back to the
    content type itself, so a new one added to POST_TYPE_BY_CONTENT_TYPE but
    forgotten here still gets grouped - as its own group, visibly, rather
    than silently landing ungrouped.
    """
    return CONTENT_GROUP_BY_CONTENT_TYPE.get(content_type, content_type)


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
    "filings-plain": {"target": "same_day", "hour": 8, "minute": 0},
    # Generated Saturday - posts the following Monday, same time-of-day.
    "foreign-flow": {"target": "next_weekday", "weekday": 0, "hour": 9, "minute": 0},
    # Redesigned posts: generated ~30 min before these go-live times (WIB), on the day itself.
    "news-flash": {"target": "same_day", "hour": 16, "minute": 30},       # Wed
    "weekly-calendar": {"target": "same_day", "hour": 13, "minute": 0},   # Mon
    "insider-carousel": {"target": "same_day", "hour": 13, "minute": 0},  # Tue
    "earnings-carousel": {"target": "same_day", "hour": 13, "minute": 0}, # Thu
    "story-crossing": {"target": "same_day", "hour": 10, "minute": 0},
    "story-news": {"target": "same_day", "hour": 13, "minute": 0},
    "story-volume": {"target": "same_day", "hour": 20, "minute": 0},
    "story-broker": {"target": "same_day", "hour": 9, "minute": 30},     # the previous trading day's brokers
    "story-movers": {"target": "same_day", "hour": 21, "minute": 0},
}


def scheduled_at_from_policy(policy: dict, now: datetime | None = None) -> str:
    """Shared target-date math behind scheduled_at_for - also used by
    threads_routing.threads_scheduled_at_for, which needs the exact same
    same_day/next_day/next_weekday semantics but its own schedule table
    (Threads posts at different times of day than IG for the same content).
    """
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


def scheduled_at_for(content_type: str, now: datetime | None = None) -> str | None:
    """Target scheduled_at (ISO 8601, UTC) for a content type per the post-
    schedule policy above, computed relative to `now` (when the generator
    actually runs). Returns None when there's no explicit policy, so the
    caller can fall back to upsert_post's own "now" default.
    """
    policy = POST_SCHEDULE_BY_CONTENT_TYPE.get(content_type)
    if policy is None:
        return None
    return scheduled_at_from_policy(policy, now)
