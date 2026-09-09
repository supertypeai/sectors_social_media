"""Generator-side helper for the Mailroom social API.

This is the single write path the generator jobs use to hand a rendered post
off: images go to POST /social/uploads, queue rows to POST /social/posts.
Mailroom owns the queue, the image hosting and the publishing that the
Supabase `social_post_queue` table + publisher.py used to do.
"""

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import hashlib
import re

from . import mailroom


VALID_PLATFORMS = {"ig", "threads"}
VALID_POST_TYPES = {"feed", "story"}

# Mailroom rejects a scheduled_at more than 60s in the past, and that 422 is
# produced *inside* its idempotency wrapper - so it gets cached under our key
# and replayed for the rest of the day. A "same_day" policy whose hour has
# already passed (agm 19:00 WIB generated at 21:00) would hit exactly that, so
# anything not comfortably in the future is sent as "now" instead.
SCHEDULE_MIN_LEAD_S = 120

# Meta's own ceiling, which Mailroom enforces at queue time.
IG_MAX_CAPTION_CHARS = 2200

# Meta's real per-platform carousel caps (2026): IG tops out at 10 children,
# Threads at 20. Exceeding these doesn't get politely rejected per-item - the
# whole carousel container creation fails, taking down the entire post. A
# content type that occasionally renders more items than this (volume-spike
# on a busy day, a combined multi-source Threads crosspost) should lose its
# overflow items rather than lose the whole post.
_CAROUSEL_LIMIT = {"ig": 10, "threads": 20}

# Every caption builder in cli.py/workflow_cli.py was written for Slack
# mrkdwn (:emoji_shortcode: + *bold*), since Slack was the only posting
# target until now. Neither renders on IG/Threads - they show up as the
# literal characters - so upsert_post converts known shortcodes to real
# Unicode emoji and strips the bold asterisks before a caption is stored.
_SLACK_EMOJI_MAP = {
    ":arrows_counterclockwise:": "🔄",
    ":link:": "🔗",
    ":busts_in_silhouette:": "👥",
    ":star2:": "🌟",
    ":zap:": "⚡",
    ":memo:": "📝",
    ":bar_chart:": "📊",
    ":trophy:": "🏆",
    ":chart_with_upwards_trend:": "📈",
    ":chart_with_downwards_trend:": "📉",
    ":crown:": "👑",
}
_SLACK_BOLD_RE = re.compile(r"\*(\S(?:.*?\S)?)\*")
_HASHTAG_RE = re.compile(r"#\w+")


def sanitize_caption(caption: str | None) -> str | None:
    """Strip Slack-only mrkdwn from a caption so it reads correctly as plain
    text on IG/Threads: known :shortcode: emoji become real Unicode emoji,
    *bold* markers are removed (IG/Threads captions support no bold at all,
    so the asterisks would otherwise show up literally), and every #hashtag
    (the Slack-era "#IDX #StockMarket ..." tag block every caption builder
    appends) is dropped.
    """
    if not caption:
        return caption
    for shortcode, emoji in _SLACK_EMOJI_MAP.items():
        caption = caption.replace(shortcode, emoji)
    caption = _SLACK_BOLD_RE.sub(r"\1", caption)
    caption = _HASHTAG_RE.sub("", caption)
    # Hashtags are usually their own trailing line - clean up the blank
    # line(s) and trailing whitespace left behind once they're gone.
    caption = "\n".join(line.rstrip() for line in caption.split("\n"))
    return caption.strip()


def _normalize(post: dict) -> dict:
    """Mailroom returns `image_urls`; every call site in this repo reads
    `image_url` (the old queue column name). Alias it once, here."""
    post["image_url"] = post.get("image_urls") or []
    return post


def upload_image_to_storage(
    local_path,
    bucket: str | None = None,
    dest_name: str | None = None,
    content_group: str | None = None,
) -> str:
    """Convert a local image to JPEG (Instagram requires JPEG) and upload it
    to Mailroom, returning its permanent public URL. `bucket` is kept only so
    existing call sites keep working - Mailroom picks the storage location.

    `content_group` becomes a folder in the stored object's key, so it has to
    match the content_group the post is queued with - otherwise the image and
    the row that references it disagree about which group they belong to.

    The Idempotency-Key is the JPEG's own content hash, so re-running a
    generator on the same input replays the first upload instead of storing
    the same bytes again under a second URL.
    """
    from PIL import Image

    local_path = Path(local_path)
    dest_name = dest_name or f"{local_path.stem}.jpg"

    image = Image.open(local_path).convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    payload = buffer.getvalue()

    result = mailroom.post(
        "/social/uploads",
        idempotency_key=f"upload:{hashlib.sha256(payload).hexdigest()}",
        files={"file": (dest_name, payload, "image/jpeg")},
        data={"content_group": content_group} if content_group else None,
    )
    return result["url"]


def upsert_post(
    platform: str,
    post_type: str,
    content_type: str,
    image_url: str | list[str] | None,
    caption: str | None,
    scheduled_at: str | None = None,
    content_group: str | None = None,
) -> dict:
    """Queue one platform-post for Mailroom's publisher to pick up.

    `image_url` may be a single URL string or a list of URLs (2+ means a
    carousel post).

    Idempotent on (platform, post_type, content_type, calendar day of
    scheduled_at) via Mailroom's Idempotency-Key: a repeat within 24h replays
    the original response instead of queueing a duplicate, so re-running a
    generator job for "today" is always safe to repeat.

    `scheduled_at` accepts an ISO 8601 string and defaults to now (UTC). It is
    always sent explicitly - omitting it would leave a permanent draft that
    never publishes - and a time already in the past is sent as now.
    """
    if platform not in VALID_PLATFORMS:
        raise ValueError(f"platform must be one of {VALID_PLATFORMS}, got {platform!r}")
    if post_type not in VALID_POST_TYPES:
        raise ValueError(f"post_type must be one of {VALID_POST_TYPES}, got {post_type!r}")
    if post_type == "story" and platform != "ig":
        raise ValueError("post_type='story' is ig-only")

    if image_url is None:
        image_urls = []
    elif isinstance(image_url, str):
        image_urls = [image_url]
    else:
        image_urls = list(image_url)

    if post_type == "story" and len(image_urls) > 1:
        raise ValueError("post_type='story' supports exactly one image, got multiple")

    carousel_limit = _CAROUSEL_LIMIT[platform]
    if len(image_urls) > carousel_limit:
        image_urls = image_urls[:carousel_limit]

    # Mailroom type-checks caption as a string, so a null one is a 422 - and it
    # rejects an IG caption over the Meta limit outright, where the old queue
    # just stored it. Both would drop the whole post.
    caption = sanitize_caption(caption)
    if platform == "ig" and caption and len(caption) > IG_MAX_CAPTION_CHARS:
        caption = caption[:IG_MAX_CAPTION_CHARS - 1].rstrip() + "…"

    now = datetime.now(timezone.utc)
    when = datetime.fromisoformat(scheduled_at) if scheduled_at else now
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    if when.timestamp() < now.timestamp() + SCHEDULE_MIN_LEAD_S:
        when = now

    # The dedupe day is the TARGET day, not today: filings-becoming generates
    # on Monday and posts on Tuesday, and Tuesday's slot is the one to hold.
    day = when.astimezone(timezone.utc).date().isoformat()

    return _normalize(mailroom.post(
        "/social/posts",
        idempotency_key=f"{platform}:{post_type}:{content_type}:{day}",
        json={
            "platform": platform,
            "post_type": post_type,
            "content_type": content_type,
            "image_urls": image_urls,
            **({"caption": caption} if caption else {}),
            **({"content_group": content_group} if content_group else {}),
            "scheduled_at": when.isoformat(),
        },
    ))


def queue_post(
    base_content_type: str,
    image_paths,
    caption: str | None,
    content_type: str | None = None,
    platform: str = "ig",
    scheduled_at: str | None = None,
) -> dict | None:
    """Convenience wrapper for generator call sites: looks up post_type from
    post_routing.post_type_for(base_content_type), uploads each local image
    to Mailroom, and queues the post - or does nothing at all when the
    content type isn't mapped to 'feed'/'story' yet (returns None; no upload,
    no queue write, no scheduled_at set).

    `base_content_type` is the routing-table key (e.g. "earnings-report").
    `content_type` is what's actually stored on the row; pass a per-item
    value (e.g. f"earnings-report-{symbol}") for any content type that can
    produce multiple distinct posts in one run, so each gets its own
    idempotency slot instead of colliding on (platform, post_type,
    base_content_type, day) and silently dropping every item after the
    first. Defaults to base_content_type for genuinely one-per-run digests
    (news-tier1, macro-news, broker-bandar, ...).
    """
    from .post_routing import content_group_for, post_type_for

    post_type = post_type_for(base_content_type)
    if post_type is None:
        return None

    if isinstance(image_paths, (str, Path)):
        image_paths = [image_paths]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    slug = content_type or base_content_type
    # The group is the theme, not `slug` - slug carries a per-item suffix
    # (earnings-report-BBCA-up) that would make a group per symbol.
    group = content_group_for(base_content_type)
    image_urls = [
        upload_image_to_storage(p, dest_name=f"{slug}_{stamp}_{i + 1}.jpg", content_group=group)
        for i, p in enumerate(image_paths)
    ]

    return upsert_post(
        platform=platform,
        post_type=post_type,
        content_type=slug,
        image_url=image_urls,
        caption=caption,
        scheduled_at=scheduled_at,
        content_group=group,
    )


def crosspost_to_threads(
    base_content_type: str,
    image_urls: list[str],
    caption: str | None,
    content_type: str | None = None,
    summarizer=None,
    scheduled_at: str | None = None,
) -> dict | None:
    """Cross-post an already-queued IG post to Threads, reusing its already-
    uploaded image_url(s) as-is - no new render, no re-upload. See
    image_generator.threads_routing for which content types this applies to,
    the caption strategy ('generic' template vs 'paraphrase' of `caption`
    via summarizer.paraphrase_caption), and the Threads-specific schedule.

    Returns None (no-op, no queue write) when base_content_type has no Threads
    policy, or when there are no images to attach.
    """
    from .post_routing import content_group_for
    from .threads_routing import generic_caption, policy_for, threads_scheduled_at_for

    policy = policy_for(base_content_type)
    if policy is None or not image_urls:
        return None

    # Threads' 20-item carousel cap is enforced centrally in upsert_post()
    # below, alongside IG's own (lower) 10-item cap.

    if policy["caption_mode"] == "generic":
        final_caption = generic_caption(policy["label"])
    else:
        final_caption = caption
        if summarizer is not None and caption:
            try:
                final_caption = summarizer.paraphrase_caption(caption) or caption
            except Exception:
                final_caption = caption

    slug = content_type or base_content_type
    return upsert_post(
        platform="threads",
        post_type="feed",
        content_type=f"{slug}-threads",
        image_url=image_urls,
        caption=final_caption,
        scheduled_at=scheduled_at or threads_scheduled_at_for(base_content_type),
        # Same group as the IG post it reuses the images from, so a theme
        # reads as one group across both platforms.
        content_group=content_group_for(base_content_type),
    )


def find_posts(
    platform: str = "ig",
    content_type: str | None = None,
    content_type_prefix: str | None = None,
    since: str | None = None,
) -> list[dict]:
    """Already-queued posts, oldest first (Mailroom lists newest first; the
    crosspost call sites care about carousel page order).

    Mailroom's content_type filter is exact-match only, so a prefix (the
    paginated "macro-news-1", "macro-news-2", ... content types) is filtered
    here instead. `since` filters on created_at, as the old queries did.
    """
    params = {"platform": platform, "limit": 500}
    if content_type:
        params["content_type"] = content_type
    if since:
        params["since"] = since

    posts = mailroom.get("/social/posts", params=params).get("data") or []
    # Mailroom's retention sweep deletes the objects behind image_urls; a
    # crosspost built from those URLs would fail at publish time, when Meta
    # fetches them.
    posts = [p for p in posts if not p.get("assets_purged_at")]
    if content_type_prefix:
        posts = [p for p in posts if (p.get("content_type") or "").startswith(content_type_prefix)]
    return [_normalize(p) for p in reversed(posts)]


def parse_image_urls(image_url_field) -> list[str]:
    """Normalize a post's image_url field back into a list of URLs. Mailroom
    already returns a list - this just tolerates a bare string too."""
    if not image_url_field:
        return []
    if isinstance(image_url_field, list):
        return image_url_field
    return [image_url_field]
