"""Threads cross-post routing: which IG content types also get cross-posted
to Threads, with what caption strategy and what Threads-specific schedule.

Every entry here assumes the IG post for that content type was already
generated and queued in the same run - crosspost() never renders a new
image, it reuses the image_url(s) already uploaded for the IG post (see
image_generator.social_queue.upsert_post).

Content types not listed in THREADS_CROSSPOST_POLICY simply don't get
cross-posted to Threads at all.
"""

from datetime import datetime

from .post_routing import scheduled_at_from_policy

# caption_mode:
#   "generic"    - a fixed, rotating template (GENERIC_CAPTIONS below). Used
#                   where grounding a caption in the day's specific numbers
#                   would misrepresent combined/partial data (e.g. several
#                   symbols' worth of earnings reports folded into one
#                   carousel), or where near-duplicate LLM prose across many
#                   combined items would read as spammy.
#   "paraphrase" - lightly reword the original IG caption via
#                   NewsSummarizer.paraphrase_caption() so the Threads post
#                   isn't a verbatim duplicate of the IG one.
#
# "schedule" uses the exact same policy shape as post_routing.py's
# POST_SCHEDULE_BY_CONTENT_TYPE (same_day/next_day/next_weekday + hour/
# minute), just with Threads' own times - Threads posts at a different
# time of day than the IG post for the same content.
THREADS_CROSSPOST_POLICY: dict[str, dict] = {
    "filings-becoming": {
        "caption_mode": "paraphrase", "label": None,
        "schedule": {"target": "next_day", "hour": 10, "minute": 0},
    },
    "filings-signal": {
        "caption_mode": "paraphrase", "label": None,
        "schedule": {"target": "next_day", "hour": 11, "minute": 0},
    },
    "earnings-report": {
        "caption_mode": "paraphrase", "label": None,
        "schedule": {"target": "next_day", "hour": 9, "minute": 0},
    },
    "volume-spike": {
        "caption_mode": "paraphrase", "label": None,
        "schedule": {"target": "same_day", "hour": 20, "minute": 0},
    },
    "broker-trending": {
        "caption_mode": "generic", "label": "market_daily",
        "schedule": {"target": "same_day", "hour": 20, "minute": 0},
    },
    "stock-performance": {
        "caption_mode": "generic", "label": "market_performance",
        "schedule": {"target": "same_day", "hour": 20, "minute": 0},
    },
    "companies-mover": {
        "caption_mode": "paraphrase", "label": None,
        "schedule": {"target": "next_day", "hour": 8, "minute": 0},
    },
    # Generated Friday only -> next_day lands on Saturday.
    "upcoming-dividend": {
        "caption_mode": "paraphrase", "label": None,
        "schedule": {"target": "next_day", "hour": 9, "minute": 0},
    },
    # news-tier1 (12:00 WIB) and macro-news (15:00 WIB) don't get their own
    # Threads policy entry - agm (18:00 WIB, the last of the three to
    # generate each day) looks both of them up from the DB and combines all
    # three into ONE "Daily News & AGM Update" post. See workflow_cli.py's
    # agm() / _crosspost_daily_news_agm() - same "last one triggers the
    # combine" pattern as broker-trending above.
    "agm": {
        "caption_mode": "generic", "label": "daily_news",
        "schedule": {"target": "same_day", "hour": 19, "minute": 0},
    },
    "filings-plain": {
        "caption_mode": "paraphrase", "label": None,
        "schedule": {"target": "same_day", "hour": 9, "minute": 0},
    },
    # broker-weekly (generated Friday 18:45 WIB) doesn't get its own Threads
    # policy entry - foreign-flow (Saturday 08:00 WIB, the later of the two)
    # looks it up from the DB and combines both into ONE "Weekly Update"
    # post. See workflow_cli.py's foreign_flow() /
    # _crosspost_weekly_market() - same "last one triggers the combine"
    # pattern as agm/broker-trending above.
    "foreign-flow": {
        "caption_mode": "generic", "label": "weekly_market",
        "schedule": {"target": "same_day", "hour": 11, "minute": 0},
    },
}

# Hand-written, non-hallucinating templates for "generic" caption_mode
# content types - rotated (not always the same string) but never derived
# from the day's actual data, since these back combined/multi-source
# carousels where a specific-sounding caption could misrepresent part of
# what's shown.
GENERIC_CAPTIONS: dict[str, list[str]] = {
    "market_daily": [
        "📊 Here's your Market Daily Update — the moves worth knowing about today.",
        "📈 Fresh off the close: today's Market Daily Update is in.",
        "🔔 Market Daily Update — a quick look at what moved today.",
    ],
    "market_performance": [
        "📊 A look at this period's top market movers, all in one place.",
        "📈 Here's how the market's biggest names performed this period.",
    ],
    "daily_news": [
        "🗞️ Your Daily News & AGM Update — catch up in a minute.",
        "📰 Here's today's Daily News & AGM Update.",
    ],
    "weekly_market": [
        "📅 Your Weekly Market Update is here.",
        "📊 This week in the market — the Weekly Update.",
    ],
}


def policy_for(content_type: str) -> dict | None:
    """The Threads crosspost policy for an IG content type, or None if that
    content type never gets cross-posted to Threads."""
    return THREADS_CROSSPOST_POLICY.get(content_type)


def generic_caption(label: str) -> str:
    import random

    return random.choice(GENERIC_CAPTIONS[label])


def threads_scheduled_at_for(content_type: str, now: datetime | None = None) -> str | None:
    """Target scheduled_at (ISO 8601, UTC) for a content type's Threads
    crosspost, per THREADS_CROSSPOST_POLICY above. Returns None when the
    content type has no Threads policy at all.
    """
    policy = policy_for(content_type)
    if policy is None:
        return None
    return scheduled_at_from_policy(policy["schedule"], now)
