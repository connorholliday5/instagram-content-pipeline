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



def fetch_collectors_items(start=None, limit: int = 4) -> list[dict]:
    """
    Detect collector-worthy issues: true #1s, facsimiles, anniversaries,
    ratio variants, foil, omnibus. Excludes ongoing series issues.
    """
    after, before = _week_range(start)
    results = []
    seen: set[int] = set()

    COLLECTOR_CHECKS = [
        # True first issues — series number must be exactly 1
        ("is_first_issue", ""),
        (["facsimile"], "FACSIMILE EDITION"),
        (["anniversary"], "ANNIVERSARY ISSUE"),
        (["omnibus"], "OMNIBUS RELEASE"),
        (["compendium"], "COMPENDIUM"),
        (["hardcover hc"], "HARDCOVER EDITION"),
        (["1:100"], "1:100 RATIO VARIANT"),
        (["1:50"], "1:50 RATIO VARIANT"),
        (["1:25"], "1:25 RATIO VARIANT"),
        (["gold foil", "foil variant", "foil cover"], "FOIL VARIANT"),
        (["director's cut", "special edition"], "SPECIAL EDITION"),
        (["first appearance", "1st appearance"], "FIRST APPEARANCE"),
    ]

    for pub_name, pub_id in MAJOR_PUBLISHERS.items():
        try:
            issues = _fetch({
                "store_date_range_after": after,
                "store_date_range_before": before,
                "publisher_id": pub_id,
                "page_size": 50,
            })
            for issue in issues:
                if issue["id"] in seen:
                    continue
                title = get_title(issue)
                title_lower = title.lower()
                issue_number = str(issue.get("number", "") or "").strip()

                for check in COLLECTOR_CHECKS:
                    keywords, reason = check

                    # True #1 issues — number field must be "1"
                    if keywords == "is_first_issue":
                        if issue_number == "1":
                            seen.add(issue["id"])
                            results.append({
                                "title": title,
                                "cover_url": get_cover_url(issue),
                                "publisher": get_publisher(issue),
                                "reason": "#1 ISSUE",
                            })
                            break
                    else:
                        if any(kw in title_lower for kw in keywords):
                            seen.add(issue["id"])
                            results.append({
                                "title": title,
                                "cover_url": get_cover_url(issue),
                                "publisher": get_publisher(issue),
                                "reason": reason,
                            })
                            break
        except Exception:
            continue

    return results[:limit]


def fetch_variants_and_collectors(start=None, limit: int = 4) -> list[dict]:
    """
    Combined fetch: rare variants + collector key issues.
    Returns merged list up to limit, deduped.
    """
    after, before = _week_range(start)
    combined = []
    seen: set[int] = set()

    VARIANT_KEYWORDS = [
        ("1:100", "1:100 RATIO"), ("1:50", "1:50 RATIO"),
        ("1:25", "1:25 RATIO"), ("1:10", "1:10 RATIO"),
        ("foil variant", "FOIL VARIANT"), ("foil cover", "FOIL VARIANT"),
        ("gold foil", "GOLD FOIL"), ("virgin variant", "VIRGIN COVER"),
        ("virgin cover", "VIRGIN COVER"), ("connecting", "CONNECTING CVR"),
        ("sketch variant", "SKETCH COVER"),
    ]

    COLLECTOR_KEYWORDS_LIST = [
        (["facsimile"], "FACSIMILE"),
        (["anniversary"], "ANNIVERSARY"),
        (["omnibus"], "OMNIBUS"),
        (["compendium"], "COMPENDIUM"),
        (["first appearance", "1st appearance"], "FIRST APPEARANCE"),
        (["special edition"], "SPECIAL EDITION"),
    ]

    for pub_name, pub_id in MAJOR_PUBLISHERS.items():
        try:
            issues = _fetch({
                "store_date_range_after": after,
                "store_date_range_before": before,
                "publisher_id": pub_id,
                "page_size": 50,
            })
            for issue in issues:
                if issue["id"] in seen:
                    continue
                title = get_title(issue)
                title_lower = title.lower()
                issue_number = str(issue.get("number", "") or "").strip()
                reason = None

                # True #1 issues
                if issue_number == "1":
                    reason = "#1 ISSUE"

                # Variant keywords
                if not reason:
                    for kw, label in VARIANT_KEYWORDS:
                        if kw in title_lower:
                            reason = label
                            break

                # Collector keywords
                if not reason:
                    for kws, label in COLLECTOR_KEYWORDS_LIST:
                        if any(kw in title_lower for kw in kws):
                            reason = label
                            break

                if reason:
                    seen.add(issue["id"])
                    combined.append({
                        "title": title,
                        "cover_url": get_cover_url(issue),
                        "publisher": get_publisher(issue),
                        "reason": reason,
                    })
        except Exception:
            continue

    return combined[:limit]