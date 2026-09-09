"""Cross-post an existing Mailroom post's content to Threads.

Takes the image_url(s) + caption from an existing post (any platform/post_type)
and queues a NEW one with platform='threads', post_type='feed' (Threads has
no Stories concept, and 'story' post_type is IG-only by upsert_post's own
validation). Supports both single-image and multi-image (carousel) sources.

This only queues the post - Mailroom's own publisher sends it.

Usage:
    python scripts/queue_to_threads.py <post_id>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from image_generator import mailroom
from image_generator.social_queue import upsert_post


def queue_to_threads(row_id: str) -> dict:
    source = mailroom.get(f"/social/posts/{row_id}")
    image_url = source.get("image_urls") or []
    caption = source.get("caption")
    if not image_url:
        raise ValueError(f"Post {row_id} has no image(s) to cross-post")

    return upsert_post(
        platform="threads",
        post_type="feed",
        content_type=f"{source.get('content_type') or row_id}-threads",
        image_url=image_url,
        caption=caption,
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/queue_to_threads.py <post_id>")
        sys.exit(1)

    row = queue_to_threads(sys.argv[1])
    print(f"Queued post id={row['id']} platform={row['platform']} "
          f"content_type={row['content_type']} images={len(row['image_url'])}")
    print("caption:")
    print(row["caption"])
