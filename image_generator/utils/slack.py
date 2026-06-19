from slack_sdk import WebClient
from pathlib import Path 

import requests as http_requests
import os 


def upload_posts_to_slack(posts: list, slack_channel: str | None = None) -> list:
    """ 
    Upload posts to Slack as a single batched message when multiple images
    are provided. Returns the list of paths that were actually uploaded.
    When Slack is not configured, nothing is uploaded and an empty list is returned.
    """
    slack_token = os.getenv("SLACK_BOT_TOKEN")

    if slack_token:
        slack_token = slack_token.strip(' "\'')

    if not slack_channel or not slack_token or not WebClient:
        for item in posts:
            path = item[0] if isinstance(item, tuple) else item
            print(Path(path).resolve())

        return []

    if not posts:
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

    if len(posts) == 1:
        item = posts[0]

        if isinstance(item, tuple):
            path, caption = item

        else:
            path = item
            caption = f"New image generated: {Path(item).name}\n\n#IDX #StockMarket #Indonesia #SectorsApp"
        
        resolved = Path(path).resolve()

        try:
            print(f"Uploading {resolved.name} to Slack")
            client.files_upload_v2(
                channel=target_channel,
                file=str(resolved),
                initial_comment=caption,
            )
            return [path]
        
        except Exception as error:
            print(f"Slack error: {error}")
            return []

    # Multiple files: batch into one message
    file_refs = []
    initial_comment = None

    for index, item in enumerate(posts):
        if isinstance(item, tuple):
            path, caption = item

        else:
            path = item
            caption = f"New image generated: {Path(item).name}\n\n#IDX #StockMarket #Indonesia #SectorsApp"

        resolved = Path(path).resolve()

        if index == 0:
            initial_comment = caption

        try:
            url_response = client.files_getUploadURLExternal(
                filename=resolved.name,
                length=resolved.stat().st_size,
            )

            with open(resolved, "rb") as file_data:
                http_requests.post(url_response["upload_url"], data=file_data).raise_for_status()
            
            file_refs.append({"id": url_response["file_id"], "title": resolved.stem})
        
        except Exception as error:
            print(f"Failed to stage {resolved.name}: {error}")
            return []

    try:
        print(f"Uploading batch of {len(file_refs)} files to Slack")
        client.files_completeUploadExternal(
            files=file_refs,
            channel_id=target_channel,
            initial_comment=initial_comment,
        )
        return [item[0] if isinstance(item, tuple) else item for item in posts]
    
    except Exception as error:
        print(f"Slack error: {error}")
        return []