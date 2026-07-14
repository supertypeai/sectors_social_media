"""Generator-side helper for the social_post_queue table (Supabase) and the
image Storage bucket that backs it.

This is the single write path the generator jobs use to hand a rendered
post off to the publisher (image_generator/publisher.py). The queue table
already exists in Supabase - this module never migrates or creates schema.
"""

from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

import os
import re


TABLE = "social_post_queue"
STORAGE_BUCKET = "social_media_generation"
VALID_PLATFORMS = {"ig", "threads"}
VALID_POST_TYPES = {"feed", "story"}

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


def _client():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ModuleNotFoundError:
        pass

    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required.")

    return create_client(url, key)


# Kept for existing importers (publisher.py) - same client, old name.
_service_client = _client


def upload_image_to_storage(local_path, bucket: str = STORAGE_BUCKET, dest_name: str | None = None) -> str:
    """Convert a local image to JPEG (Instagram requires JPEG) and upload it
    to the given public Storage bucket, returning its public URL.
    """
    from PIL import Image

    local_path = Path(local_path)
    dest_name = dest_name or f"{local_path.stem}.jpg"

    image = Image.open(local_path).convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    buffer.seek(0)

    client = _client()
    client.storage.from_(bucket).upload(
        dest_name,
        buffer.read(),
        file_options={"content-type": "image/jpeg", "upsert": "true"},
    )
    return client.storage.from_(bucket).get_public_url(dest_name)


def upsert_post(
    platform: str,
    post_type: str,
    content_type: str,
    image_url: str | list[str] | None,
    caption: str | None,
    scheduled_at: str | None = None,
) -> dict:
    """Queue one platform-post for the publisher to pick up.

    `image_url` may be a single URL string or a list of URLs (2+ means an IG
    carousel post - see publisher._publish_ig). image_url is a native
    Postgres array column (text[]), so the list is passed straight through
    to supabase-py rather than JSON-encoded.

    Idempotent on (platform, post_type, content_type, calendar day of
    scheduled_at): if a row already exists for that key on that day
    (regardless of its status), it's returned unchanged instead of
    inserting a duplicate - so re-running a generator job for "today" is
    always safe to repeat.

    `scheduled_at` accepts an ISO 8601 string; defaults to now (UTC), which
    makes the row due for the very next publisher run.
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

    scheduled_at = scheduled_at or datetime.now(timezone.utc).isoformat()
    day = date.fromisoformat(scheduled_at[:10])
    day_start = f"{day.isoformat()}T00:00:00"
    day_end = f"{(day + timedelta(days=1)).isoformat()}T00:00:00"

    client = _client()

    existing = (
        client.table(TABLE)
        .select("*")
        .eq("platform", platform)
        .eq("post_type", post_type)
        .eq("content_type", content_type)
        .gte("scheduled_at", day_start)
        .lt("scheduled_at", day_end)
        .execute()
    )
    if existing.data:
        return existing.data[0]

    row = {
        "platform": platform,
        "post_type": post_type,
        "content_type": content_type,
        "image_url": image_urls,
        "caption": sanitize_caption(caption),
        "status": "pending",
        "attempts": 0,
        "scheduled_at": scheduled_at,
    }
    result = client.table(TABLE).insert(row).execute()
    return result.data[0]


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
    to Storage, and upserts the queue row - or does nothing at all when the
    content type isn't mapped to 'feed'/'story' yet (returns None; no upload,
    no DB write, no scheduled_at set).

    `base_content_type` is the routing-table key (e.g. "earnings-report").
    `content_type` is what's actually stored on the row; pass a per-item
    value (e.g. f"earnings-report-{symbol}") for any content type that can
    produce multiple distinct posts in one run, so each gets its own
    idempotency slot instead of colliding on (platform, post_type,
    base_content_type, day) and silently dropping every item after the
    first. Defaults to base_content_type for genuinely one-per-run digests
    (news-tier1, macro-news, broker-bandar, ...).
    """
    from .post_routing import post_type_for

    post_type = post_type_for(base_content_type)
    if post_type is None:
        return None

    if isinstance(image_paths, (str, Path)):
        image_paths = [image_paths]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    slug = content_type or base_content_type
    image_urls = [
        upload_image_to_storage(p, dest_name=f"{slug}_{stamp}_{i + 1}.jpg")
        for i, p in enumerate(image_paths)
    ]

    return upsert_post(
        platform=platform,
        post_type=post_type,
        content_type=slug,
        image_url=image_urls,
        caption=caption,
        scheduled_at=scheduled_at,
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

    Returns None (no-op, no DB write) when base_content_type has no Threads
    policy, or when there are no images to attach.
    """
    from .threads_routing import generic_caption, policy_for, threads_scheduled_at_for

    policy = policy_for(base_content_type)
    if policy is None or not image_urls:
        return None

    # Threads/IG carousels cap out at 10 children - combined multi-item
    # crossposts (earnings-report, upcoming-dividend, stock-performance)
    # can exceed that on a busy day, so keep only the first 10.
    image_urls = image_urls[:10]

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
    )


def parse_image_urls(image_url_field) -> list[str]:
    """Normalize the image_url column back into a list of URLs. image_url is
    a native Postgres array (text[]), so postgrest-py already deserializes
    it to a Python list - this just tolerates a bare string too, in case a
    row was ever written directly rather than through upsert_post."""
    if not image_url_field:
        return []
    if isinstance(image_url_field, list):
        return image_url_field
    return [image_url_field]
