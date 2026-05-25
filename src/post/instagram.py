import os
import requests
from src.post.upload import upload_image

GRAPH_URL = "https://graph.facebook.com/v19.0"
ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
IG_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")


def _post(endpoint: str, data: dict) -> dict:
    data["access_token"] = ACCESS_TOKEN
    resp = requests.post(f"{GRAPH_URL}/{endpoint}", data=data)
    resp.raise_for_status()
    return resp.json()


def post_image(image_path: str, caption: str, dry_run: bool = True) -> dict:
    if dry_run:
        print(f"[DRY RUN] Would upload and post: {image_path}")
        print(f"[DRY RUN] Caption preview: {caption[:120]}...")
        return {"status": "dry_run"}

    print("Uploading image to Cloudinary...")
    public_url = upload_image(image_path)
    print(f"✓ Uploaded: {public_url}")

    creation_id = _post(f"{IG_ACCOUNT_ID}/media", {
        "image_url": public_url,
        "caption": caption,
    })["id"]

    media_id = _post(f"{IG_ACCOUNT_ID}/media_publish", {
        "creation_id": creation_id,
    })["id"]

    return {"status": "posted", "media_id": media_id, "url": public_url}