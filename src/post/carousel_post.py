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


def post_carousel(image_paths: list[str], caption: str, dry_run: bool = True) -> dict:
    """Upload images and post as Instagram carousel."""
    if dry_run:
        print(f"[DRY RUN] Would post carousel with {len(image_paths)} slides")
        print(f"[DRY RUN] Caption preview: {caption[:120]}...")
        return {"status": "dry_run"}

    print(f"Uploading {len(image_paths)} slides to Cloudinary...")
    public_urls = []
    for path in image_paths:
        url = upload_image(path)
        public_urls.append(url)
        print(f"  ✓ {path} → {url}")

    # Create child media containers
    child_ids = []
    for url in public_urls:
        result = _post(f"{IG_ACCOUNT_ID}/media", {
            "image_url": url,
            "is_carousel_item": "true",
        })
        child_ids.append(result["id"])
        print(f"  ✓ Container created: {result['id']}")

    # Create carousel container
    carousel = _post(f"{IG_ACCOUNT_ID}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(child_ids),
        "caption": caption,
    })

    # Publish
    result = _post(f"{IG_ACCOUNT_ID}/media_publish", {
        "creation_id": carousel["id"],
    })

    return {"status": "posted", "media_id": result["id"]}