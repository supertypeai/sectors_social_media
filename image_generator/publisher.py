"""Queue consumer: publishes due rows from social_post_queue to Instagram
and Threads via Meta's official Graph APIs, then updates row status.

Run via: python -m image_generator.publisher
"""

from datetime import datetime, timezone

import json
import logging
import os
import sys
import time

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    pass

from .social_queue import TABLE, _service_client, parse_image_urls


MAX_ATTEMPTS = 3

IG_BASE = "https://graph.instagram.com/v23.0"
IG_CONTAINER_WAIT_S = 10

THREADS_BASE = "https://graph.threads.net/v1.0"
THREADS_CONTAINER_WAIT_S = 30
THREADS_MAX_CHARS = 500

REQUEST_TIMEOUT_S = 30


# ── structured logging ───────────────────────────────────────────────────────
class _JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        payload.update(getattr(record, "fields", None) or {})
        return json.dumps(payload)


def _make_logger():
    logger = logging.getLogger("publisher")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    logger.handlers = [handler]
    logger.propagate = False
    return logger


log = _make_logger()


def _log(level, message, **fields):
    log.log(level, message, extra={"fields": fields})


# ── queue access ──────────────────────────────────────────────────────────────
_PLATFORM_PRIORITY = {"ig": 0, "threads": 1}


def _fetch_due_rows(client):
    """Pending rows whose scheduled_at has passed, PLUS any row stuck in
    'publishing' - the only way a row is in 'publishing' when we start is a
    previous run crashing mid-publish (this function always resolves a row
    to 'published'/'pending'/'failed' before moving to the next one), so
    picking those back up is the crash-resume path. A GH Actions concurrency
    group (see the workflow) keeps two publisher runs from overlapping and
    racing on the same row.

    Sorted IG-first, then by scheduled_at within each platform - a Threads
    crosspost and its IG source can land in the same 30-min window with the
    Threads row's scheduled_at ties or even edges earlier, and IG should
    never end up waiting behind it.
    """
    now = datetime.now(timezone.utc).isoformat()
    result = (
        client.table(TABLE)
        .select("*")
        .in_("status", ["pending", "publishing"])
        .lte("scheduled_at", now)
        .order("scheduled_at", desc=False)
        .execute()
    )
    rows = result.data or []
    rows.sort(key=lambda row: (_PLATFORM_PRIORITY.get(row.get("platform"), 99), row.get("scheduled_at") or ""))
    return rows


def _update_row(client, row_id, fields):
    client.table(TABLE).update(fields).eq("id", row_id).execute()


# ── platform publishers ──────────────────────────────────────────────────────
def _create_ig_carousel_item(base, token, image_url):
    resp = requests.post(
        f"{base}/media",
        data={"image_url": image_url, "is_carousel_item": "true", "access_token": token},
        timeout=REQUEST_TIMEOUT_S,
    )
    data = resp.json()
    if "id" not in data:
        raise RuntimeError(f"IG carousel item creation failed: {data}")
    return data["id"]


def _publish_ig(client, row):
    token = os.getenv("IG_ACCESS_TOKEN")
    user_id = os.getenv("IG_USER_ID")
    if not token or not user_id:
        raise RuntimeError("IG_ACCESS_TOKEN / IG_USER_ID not configured")

    base = f"{IG_BASE}/{user_id}"
    container_id = row.get("container_id")
    image_urls = parse_image_urls(row.get("image_url"))
    if not image_urls:
        raise RuntimeError("row has no image_url(s)")

    if not container_id:
        if row["post_type"] == "story":
            payload = {"image_url": image_urls[0], "media_type": "STORIES", "access_token": token}
            resp = requests.post(f"{base}/media", data=payload, timeout=REQUEST_TIMEOUT_S)
            data = resp.json()
            if "id" not in data:
                raise RuntimeError(f"IG container creation failed: {data}")
            container_id = data["id"]

        elif len(image_urls) == 1:
            payload = {"image_url": image_urls[0], "caption": row.get("caption") or "", "access_token": token}
            resp = requests.post(f"{base}/media", data=payload, timeout=REQUEST_TIMEOUT_S)
            data = resp.json()
            if "id" not in data:
                raise RuntimeError(f"IG container creation failed: {data}")
            container_id = data["id"]

        else:
            # Carousel: an item container per image (no caption on items),
            # then a parent CAROUSEL container referencing them. Only the
            # parent id is persisted (the schema has one container_id column),
            # so a crash between item creation and parent creation means a
            # retry recreates the item containers - wasteful but harmless,
            # since unpublished item containers just expire after 24h.
            item_ids = [_create_ig_carousel_item(base, token, url) for url in image_urls]
            _log(logging.INFO, "ig carousel items created", row_id=row["id"], item_ids=item_ids)

            payload = {
                "media_type": "CAROUSEL",
                "children": ",".join(item_ids),
                "caption": row.get("caption") or "",
                "access_token": token,
            }
            resp = requests.post(f"{base}/media", data=payload, timeout=REQUEST_TIMEOUT_S)
            data = resp.json()
            if "id" not in data:
                raise RuntimeError(f"IG carousel container creation failed: {data}")
            container_id = data["id"]

        # Persist immediately so a crash before publish resumes here on the
        # next run instead of creating a duplicate container.
        _update_row(client, row["id"], {"container_id": container_id})
        _log(logging.INFO, "ig container created", row_id=row["id"], container_id=container_id)
    else:
        _log(logging.INFO, "resuming with existing ig container", row_id=row["id"], container_id=container_id)

    time.sleep(IG_CONTAINER_WAIT_S)

    resp = requests.post(
        f"{base}/media_publish",
        data={"creation_id": container_id, "access_token": token},
        timeout=REQUEST_TIMEOUT_S,
    )
    data = resp.json()
    if "id" not in data:
        raise RuntimeError(f"IG publish failed: {data}")
    return data["id"]


def _create_threads_carousel_item(base, token, image_url):
    resp = requests.post(
        f"{base}/threads",
        data={"media_type": "IMAGE", "image_url": image_url, "is_carousel_item": "true", "access_token": token},
        timeout=REQUEST_TIMEOUT_S,
    )
    data = resp.json()
    if "id" not in data:
        raise RuntimeError(f"Threads carousel item creation failed: {data}")
    return data["id"]


def _split_for_threads(text, limit=THREADS_MAX_CHARS):
    """Break `text` into <= limit-char pieces so nothing gets truncated or
    rejected: prefers cutting at the latest paragraph break (blank line)
    within the limit, falling back to the latest line break, then the
    latest space, and only hard-cutting mid-word if the stretch has no
    break at all. The overflow pieces get posted as chained replies (see
    _publish_threads) rather than being dropped.
    """
    chunks = []
    remaining = text.strip()
    while len(remaining) > limit:
        window = remaining[:limit]
        cut = window.rfind("\n\n")
        if cut <= 0:
            cut = window.rfind("\n")
        if cut <= 0:
            cut = window.rfind(" ")
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks



# Manual kill switch for Threads publishing - flip to True to resume. Rows
# keep queuing normally (crosspost_to_threads still runs) while this is
# off; they just sit pending until re-enabled, same as the missing-
# credentials case below.
THREADS_PUBLISHING_ENABLED = True


def _publish_threads(client, row):
    if not THREADS_PUBLISHING_ENABLED:
        _log(logging.INFO, "threads publishing suspended, skipping row", row_id=row["id"])
        return None  # sentinel: caller leaves the row pending, doesn't count an attempt

    token = os.getenv("THREADS_ACCESS_TOKEN")
    user_id = os.getenv("THREADS_USER_ID")
    if not token or not user_id:
        _log(logging.WARNING, "threads credentials not configured, skipping row", row_id=row["id"])
        return None  # sentinel: caller leaves the row pending, doesn't count an attempt

    caption = row.get("caption") or ""
    chunks = _split_for_threads(caption) or [""]
    if len(chunks) > 1:
        _log(logging.INFO, "caption exceeds threads limit, chaining as replies",
             row_id=row["id"], chars=len(caption), parts=len(chunks))

    base = f"{THREADS_BASE}/{user_id}"
    container_id = row.get("container_id")
    image_urls = parse_image_urls(row.get("image_url"))
    first_text = chunks[0]

    if not container_id:
        if not image_urls:
            payload = {"media_type": "TEXT", "text": first_text, "access_token": token}
            resp = requests.post(f"{base}/threads", data=payload, timeout=REQUEST_TIMEOUT_S)
            data = resp.json()
            if "id" not in data:
                raise RuntimeError(f"Threads container creation failed: {data}")
            container_id = data["id"]

        elif len(image_urls) == 1:
            payload = {
                "media_type": "IMAGE",
                "image_url": image_urls[0],
                "text": first_text,
                "access_token": token,
            }
            resp = requests.post(f"{base}/threads", data=payload, timeout=REQUEST_TIMEOUT_S)
            data = resp.json()
            if "id" not in data:
                raise RuntimeError(f"Threads container creation failed: {data}")
            container_id = data["id"]

        else:
            # Carousel: an item container per image (no text on items), then a
            # parent CAROUSEL container referencing them - same shape as the
            # IG carousel flow, just on Threads' endpoints. Only the parent id
            # is persisted, so a crash between item creation and parent
            # creation means a retry recreates the item containers - harmless,
            # since unpublished item containers just expire.
            item_ids = [_create_threads_carousel_item(base, token, url) for url in image_urls]
            _log(logging.INFO, "threads carousel items created", row_id=row["id"], item_ids=item_ids)

            # Threads item containers need a beat to finish processing before
            # a parent CAROUSEL container can reference them - skipping this
            # wait gets "invalid, non-existent or expired" on the later-
            # created items (confirmed live: 2-image carousel, second item
            # rejected with no wait).
            time.sleep(THREADS_CONTAINER_WAIT_S)

            payload = {
                "media_type": "CAROUSEL",
                "children": ",".join(item_ids),
                "text": first_text,
                "access_token": token,
            }
            resp = requests.post(f"{base}/threads", data=payload, timeout=REQUEST_TIMEOUT_S)
            data = resp.json()
            if "id" not in data:
                raise RuntimeError(f"Threads carousel container creation failed: {data}")
            container_id = data["id"]

        # Persist immediately so a crash before publish resumes here on the
        # next run instead of creating a duplicate container.
        _update_row(client, row["id"], {"container_id": container_id})
        _log(logging.INFO, "threads container created", row_id=row["id"], container_id=container_id)
    else:
        _log(logging.INFO, "resuming with existing threads container", row_id=row["id"], container_id=container_id)

    time.sleep(THREADS_CONTAINER_WAIT_S)

    resp = requests.post(
        f"{base}/threads_publish",
        data={"creation_id": container_id, "access_token": token},
        timeout=REQUEST_TIMEOUT_S,
    )
    data = resp.json()
    if "id" not in data:
        raise RuntimeError(f"Threads publish failed: {data}")
    published_id = data["id"]

    # Overflow text (beyond the 500-char limit) chains as text-only replies
    # to the post that precedes it, so the full caption still reads as one
    # continuous thread. Not crash-resumable past the main post (a retry
    # would resume at the main post via container_id above and re-send the
    # whole reply chain) - acceptable, same "harmless to redo" tradeoff as
    # the carousel item containers.
    reply_to_id = published_id
    for chunk in chunks[1:]:
        reply_payload = {
            "media_type": "TEXT",
            "text": chunk,
            "reply_to_id": reply_to_id,
            "access_token": token,
        }
        resp = requests.post(f"{base}/threads", data=reply_payload, timeout=REQUEST_TIMEOUT_S)
        data = resp.json()
        if "id" not in data:
            raise RuntimeError(f"Threads reply container creation failed: {data}")
        reply_container_id = data["id"]

        time.sleep(THREADS_CONTAINER_WAIT_S)

        resp = requests.post(
            f"{base}/threads_publish",
            data={"creation_id": reply_container_id, "access_token": token},
            timeout=REQUEST_TIMEOUT_S,
        )
        data = resp.json()
        if "id" not in data:
            raise RuntimeError(f"Threads reply publish failed: {data}")
        reply_to_id = data["id"]
        _log(logging.INFO, "threads reply published", row_id=row["id"], reply_id=reply_to_id)

    return published_id


# ── row processing ───────────────────────────────────────────────────────────
def _process_row(client, row):
    row_id = row["id"]
    platform = row["platform"]
    _update_row(client, row_id, {"status": "publishing"})
    _log(
        logging.INFO,
        "processing row",
        row_id=row_id,
        platform=platform,
        post_type=row.get("post_type"),
        content_type=row.get("content_type"),
    )

    try:
        if platform == "ig":
            media_id = _publish_ig(client, row)
        elif platform == "threads":
            media_id = _publish_threads(client, row)
            if media_id is None:
                _update_row(client, row_id, {"status": "pending"})
                return
        else:
            raise RuntimeError(f"unknown platform {platform!r}")

        _update_row(
            client,
            row_id,
            {
                "status": "published",
                "published_media_id": media_id,
                "published_at": datetime.now(timezone.utc).isoformat(),
                "error": None,
            },
        )
        _log(logging.INFO, "published", row_id=row_id, platform=platform, media_id=media_id)

    except Exception as error:
        attempts = (row.get("attempts") or 0) + 1
        next_status = "pending" if attempts < MAX_ATTEMPTS else "failed"
        _update_row(
            client,
            row_id,
            {"status": next_status, "attempts": attempts, "error": str(error)},
        )
        _log(
            logging.ERROR if next_status == "failed" else logging.WARNING,
            "publish failed",
            row_id=row_id,
            platform=platform,
            attempts=attempts,
            next_status=next_status,
            error=str(error),
        )


def main():
    client = _service_client()
    rows = _fetch_due_rows(client)
    _log(logging.INFO, "fetched due rows", count=len(rows))
    for row in rows:
        _process_row(client, row)


if __name__ == "__main__":
    main()
