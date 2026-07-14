"""Cross-post an existing social_post_queue row's content to Threads.

Takes the image_url(s) + caption from an existing row (any platform/post_type)
and queues a NEW row with platform='threads', post_type='feed' (Threads has
no Stories concept, and 'story' post_type is IG-only by upsert_post's own
validation). Supports both single-image and multi-image (carousel) source
rows - publisher.py's Threads carousel support handles either.

This only inserts a queue row - it does not publish anything itself. Run
`python -m image_generator.publisher` afterward (needs THREADS_ACCESS_TOKEN /
THREADS_USER_ID in the environment) to actually post it.

Usage:
    python scripts/queue_to_threads.py <row_id>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from image_generator.social_queue import _client, TABLE, upsert_post


def queue_to_threads(row_id: int) -> dict:
    client = _client()
    result = client.table(TABLE).select("*").eq("id", row_id).execute()
    if not result.data:
        raise ValueError(f"No row with id={row_id}")

    source = result.data[0]
    image_url = source.get("image_url") or []
    caption = source.get("caption")
    if not image_url:
        raise ValueError(f"Row {row_id} has no image_url(s) to cross-post")

    return upsert_post(
        platform="threads",
        post_type="feed",
        content_type=f"{source['content_type']}-threads",
        image_url=image_url,
        caption=caption,
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/queue_to_threads.py <row_id>")
        sys.exit(1)

    row = queue_to_threads(int(sys.argv[1]))
    print(f"Queued row id={row['id']} platform={row['platform']} "
          f"content_type={row['content_type']} images={len(row['image_url'])}")
    print("caption:")
    print(row["caption"])
