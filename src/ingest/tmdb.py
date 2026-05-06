import os
import requests
from datetime import date, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential

BASE_URL = "https://api.themoviedb.org/3"
API_KEY = os.getenv("TMDB_API_KEY")
IMAGE_BASE = "https://image.tmdb.org/t/p/w780"

SUPERHERO_KEYWORDS = [9715, 246423]  # superhero, based on comic book


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _get(endpoint: str, params: dict = {}) -> dict:
    params["api_key"] = API_KEY
    resp = requests.get(f"{BASE_URL}/{endpoint}", params=params)
    resp.raise_for_status()
    return resp.json()


def fetch_upcoming_movies() -> list[dict]:
    today = date.today()
    end = today + timedelta(days=30)
    data = _get("discover/movie", {
        "with_keywords": "|".join(str(k) for k in SUPERHERO_KEYWORDS),
        "primary_release_date.gte": today.isoformat(),
        "primary_release_date.lte": end.isoformat(),
        "sort_by": "popularity.desc",
    })
    return data.get("results", [])


def fetch_airing_shows() -> list[dict]:
    data = _get("discover/tv", {
        "with_keywords": "|".join(str(k) for k in SUPERHERO_KEYWORDS),
        "sort_by": "popularity.desc",
        "first_air_date.gte": date.today().isoformat(),
    })
    return data.get("results", [])


def poster_url(path: str) -> str:
    return f"{IMAGE_BASE}{path}" if path else ""
