# post_instagram.py
import os, requests

GRAPH = "https://graph.facebook.com/v21.0"  # use the latest version available
IG_USER_ID = os.environ["17841477579530391"]
IG_TOKEN   = os.environ["IGAAPy8E1iGeBBZAFRmekx1a2VyTFo0ZA0gzckM1VFk2azNVSEZArRjR0M2F0NWJBdHhJSC1OLXlrbVhxLVpELVB0NzdzRkZAsTF9ZASWphaDhqd20td1VGaGVLU25vVlJjTTBzY0ItMzczcXFQa1FPeWNuWVpyZA21MTUtvRi01ZADBEMAZDZD"]

def ig_create_image_container(image_url, caption=""):
    r = requests.post(
        f"{GRAPH}/{IG_USER_ID}/media",
        params={"access_token": IG_TOKEN},
        data={"image_url": image_url, "caption": caption}
    )
    r.raise_for_status()
    return r.json()["id"]  # creation_id

def ig_publish(creation_id):
    r = requests.post(
        f"{GRAPH}/{IG_USER_ID}/media_publish",
        params={"access_token": IG_TOKEN},
        data={"creation_id": creation_id}
    )
    r.raise_for_status()
    return r.json()

def post_single(image_url, caption=""):
    cid = ig_create_image_container(image_url, caption)
    return ig_publish(cid)
