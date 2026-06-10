from slack_sdk import WebClient
from pathlib import Path 

import os 


def upload_posts_to_slack(posts: list, slack_channel: str | None = None):
    """Upload each post to Slack. Returns the list of items that ACTUALLY
    uploaded, so callers can persist state only for posts that truly went out
    (a swallowed Slack error must not be mistaken for success). When Slack is
    not configured nothing is uploaded, so an empty list is returned.
    """
    slack_token = os.getenv("SLACK_BOT_TOKEN")

    if slack_token:
        slack_token = slack_token.strip(' "\'')

    if not slack_channel or not slack_token or not WebClient:
        for item in posts:
            path = item[0] if isinstance(item, tuple) else item
            print(Path(path).resolve())

        return []

    client = WebClient(token=slack_token)
    target_channel = slack_channel

    if target_channel.startswith("U"):
        try:
            resp = client.conversations_open(users=target_channel)
            target_channel = resp["channel"]["id"]
            print(f"Resolved user {slack_channel} -> DM {target_channel}")

        except Exception as error:
            print(f"Could not open DM with {slack_channel}: {error}")
            return []

    uploaded = []
    for item in posts:
        if isinstance(item, tuple):
            path, caption = item

        else:
            path = item
            caption = f"New image generated: {Path(item).name}\n\n#IDX #StockMarket #Indonesia #SectorsApp"

        resolved = Path(path).resolve()
        print(resolved)

        try:
            print(f"Uploading {resolved.name} to Slack...")
            client.files_upload_v2(
                channel=target_channel,
                file=str(resolved),
                initial_comment=caption,
            )
            # Return the path (not the whole item) so callers can match uploaded
            # slides whether they passed bare paths or (path, caption) tuples.
            uploaded.append(path)

        except Exception as error:
            print(f"Slack error: {error}")

    return uploaded

