import os
import requests
from pathlib import Path

GRAPH_URL = "https://graph.facebook.com/v19.0"
ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
IG_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")


def _post(endpoint: str, data: dict) -> dict:
    data["access_token"] = ACCESS_TOKEN
    resp = requests.post(f"{GRAPH_URL}/{endpoint}", data=data)
    resp.raise_for_status()
    return resp.json()


def upload_image_container(image_url: str, caption: str) -> str:
    """Step 1: Create a media container. Returns creation_id."""
    result = _post(f"{IG_ACCOUNT_ID}/media", {
        "image_url": image_url,
        "caption": caption,
    })
    return result["id"]


def publish_container(creation_id: str) -> str:
    """Step 2: Publish the container. Returns media_id."""
    result = _post(f"{IG_ACCOUNT_ID}/media_publish", {
        "creation_id": creation_id,
    })
    return result["id"]


def post_image(image_url: str, caption: str, dry_run: bool = True) -> dict:
    """Full post flow. image_url must be publicly accessible."""
    if dry_run:
        print(f"[DRY RUN] Would post: {image_url[:60]}...")
        print(f"[DRY RUN] Caption preview: {caption[:120]}...")
        return {"status": "dry_run"}

    creation_id = upload_image_container(image_url, caption)
    media_id = publish_container(creation_id)
    return {"status": "posted", "media_id": media_id}
