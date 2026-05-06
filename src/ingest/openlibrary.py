import requests
from tenacity import retry, stop_after_attempt, wait_exponential

BASE_URL = "https://openlibrary.org"

SUBJECTS = ["graphic novels", "manga", "comics", "superhero fiction"]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _get(endpoint: str, params: dict = {}) -> dict:
    resp = requests.get(f"{BASE_URL}{endpoint}.json", params=params)
    resp.raise_for_status()
    return resp.json()


def fetch_new_books(subject: str = "graphic novels", limit: int = 10) -> list[dict]:
    data = _get(f"/subjects/{subject.replace(' ', '_')}", {
        "limit": limit,
        "sort": "new",
    })
    return data.get("works", [])


def cover_url(cover_id: int, size: str = "L") -> str:
    return f"https://covers.openlibrary.org/b/id/{cover_id}-{size}.jpg"
