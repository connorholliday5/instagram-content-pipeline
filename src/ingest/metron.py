import os
import requests
from datetime import date, timedelta
from requests.auth import HTTPBasicAuth

BASE_URL = "https://metron.cloud/api"

MAJOR_PUBLISHERS = {
    "marvel": 1,
    "dc comics": 2,
    "dark horse comics": 3,
    "image comics": 4,
    "idw publishing": 6,
}

VARIANT_KEYWORDS = [
    "variant", "foil", "virgin", "connecting", "ratio",
    "1:10", "1:25", "1:50", "1:100", "1:500",
    "exclusive", "incentive", "sketch",
]

REPRINT_SERIES_TYPES = [
    "trade paperback", "hardcover", "omnibus", "annual",
    "graphic novel", "collected edition", "compendium"
]

REPRINT_TITLE_KEYWORDS = [
    "omnibus", "compendium", "hardcover", "collected",
    "complete", "trade paperback", "vol.", "volume",
    "2nd printing", "second printing", "anniversary"
]

PUB_ID_MAP = {1: "Marvel", 2: "DC Comics", 3: "Dark Horse", 4: "Image", 6: "IDW"}


def _auth() -> HTTPBasicAuth:
    username = os.getenv("METRON_USERNAME") or ""
    password = os.getenv("METRON_PASSWORD") or ""
    return HTTPBasicAuth(username, password)


def _week_range(start: date | None = None) -> tuple[str, str]:
    if start is None:
        today = date.today()
        start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()


def _fetch(params: dict) -> list[dict]:
    try:
        resp = requests.get(
            f"{BASE_URL}/issue/",
            auth=_auth(),
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as e:
        print(f"  [metron] error: {e}")
        return []


def _base_params(after: str, before: str, publisher_id: int, page_size: int = 20) -> dict:
    return {
        "store_date_range_after": after,
        "store_date_range_before": before,
        "publisher_id": publisher_id,
        "page_size": page_size,
    }


def _is_reprint(issue: dict) -> bool:
    series = issue.get("series") or {}
    series_type = ((series.get("series_type") or {}).get("name") or "").lower()
    title = get_title(issue).lower()
    return (
        any(rt in series_type for rt in REPRINT_SERIES_TYPES) or
        any(kw in title for kw in REPRINT_TITLE_KEYWORDS)
    )


def fetch_top_weekly_issues(start: date | None = None, limit: int = 10) -> list[dict]:
    after, before = _week_range(start)
    all_issues = []
    seen: set[int] = set()

    for pub_name, pub_id in MAJOR_PUBLISHERS.items():
        for issue in _fetch(_base_params(after, before, pub_id)):
            if _is_reprint(issue):
                continue
            if issue["id"] not in seen:
                seen.add(issue["id"])
                all_issues.append(issue)

    return all_issues[:limit]


def fetch_top_weekly_reprints(start: date | None = None, limit: int = 5) -> list[dict]:
    after, before = _week_range(start)
    reprints = []
    seen: set[int] = set()

    for pub_name, pub_id in MAJOR_PUBLISHERS.items():
        for issue in _fetch(_base_params(after, before, pub_id, page_size=30)):
            if _is_reprint(issue) and issue["id"] not in seen:
                seen.add(issue["id"])
                reprints.append(issue)

    return reprints[:limit]


def fetch_weekly_variants(start: date | None = None) -> list[dict]:
    after, before = _week_range(start)
    variants = []
    seen: set[str] = set()

    for pub_name, pub_id in MAJOR_PUBLISHERS.items():
        for issue in _fetch(_base_params(after, before, pub_id, page_size=50)):
            title = get_title(issue).lower()
            if any(kw in title for kw in VARIANT_KEYWORDS):
                display_title = get_title(issue)
                if display_title not in seen:
                    seen.add(display_title)
                    variants.append({
                        "title": display_title,
                        "cover_url": get_cover_url(issue),
                        "publisher": get_publisher(issue),
                    })

    return variants[:6]


def search_issue(title: str) -> dict | None:
    try:
        resp = requests.get(
            f"{BASE_URL}/issue/",
            auth=_auth(),
            params={"series_name": title, "page_size": 5},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0] if results else None
    except Exception:
        return None


def get_cover_url(issue: dict | None) -> str | None:
    if not issue:
        return None
    return issue.get("image")


def get_publisher(issue: dict | None) -> str:
    if not issue:
        return ""
    pub = issue.get("publisher")
    if isinstance(pub, dict):
        return pub.get("name", "")
    series = issue.get("series") or {}
    if isinstance(series, dict):
        pub2 = series.get("publisher")
        if isinstance(pub2, dict):
            return pub2.get("name", "")
    pub_id = issue.get("publisher_id")
    if isinstance(pub_id, int):
        return PUB_ID_MAP.get(pub_id, "")
    return ""


def get_title(issue: dict | None) -> str:
    if not issue:
        return "Unknown"
    return issue.get("issue") or issue.get("issue_name") or "Unknown"


def get_store_date(issue: dict | None) -> str:
    if not issue:
        return ""
    return issue.get("store_date") or issue.get("cover_date") or ""