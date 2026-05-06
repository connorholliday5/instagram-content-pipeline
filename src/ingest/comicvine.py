import os
import requests
from datetime import date, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential

BASE_URL = "https://comicvine.gamespot.com/api"
API_KEY = os.getenv("COMICVINE_API_KEY")

HEADERS = {"User-Agent": "TheWatchtower/1.0"}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _get(endpoint: str, params: dict) -> dict:
    params.update({"api_key": API_KEY, "format": "json"})
    resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def fetch_weekly_issues(start: date = None) -> list[dict]:
    """Fetch comic issues releasing this week."""
    if start is None:
        today = date.today()
        start = today - timedelta(days=today.weekday())  # Monday
    end = start + timedelta(days=6)

    data = _get("issues", {
        "filter": f"store_date:{start}|{end}",
        "field_list": "id,name,volume,description,image,store_date,publisher",
        "limit": 50,
        "sort": "store_date:asc",
    })
    return data.get("results", [])
