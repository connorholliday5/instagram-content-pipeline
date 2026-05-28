import os
import requests
from datetime import date, timedelta

BASE_URL = "https://comicvine.gamespot.com/api"
API_KEY  = os.getenv("COMICVINE_API_KEY", "")

# Browser headers — required to avoid host allowlist block
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept":     "application/json",
    "Referer":    "https://comicvine.gamespot.com",
}

# Publisher name matching
DC_NAMES      = ["dc comics", "dc", "vertigo", "black label", "dc black label"]
MARVEL_NAMES  = ["marvel comics", "marvel", "marvel universe"]
IMAGE_NAMES   = ["image comics", "image"]
DH_NAMES      = ["dark horse comics", "dark horse"]
IDW_NAMES     = ["idw publishing", "idw"]

# Volume cache — avoid repeat API calls for same volume
_volume_cache: dict[int, dict] = {}


def _get_volume(volume_id: int) -> dict:
    """Fetch volume detail with publisher + issue count. Cached."""
    if volume_id in _volume_cache:
        return _volume_cache[volume_id]
    try:
        data = _get(f"volume/4050-{volume_id}", {
            "field_list": "id,name,publisher,count_of_issues",
        })
        vol = data.get("results", {})
        _volume_cache[volume_id] = vol
        return vol
    except Exception:
        return {}


def _get_publisher_from_volume(issue: dict) -> str:
    """Get publisher name via volume lookup."""
    vol = issue.get("volume") or {}
    vol_id = vol.get("id")
    if not vol_id:
        return ""
    if vol.get("publisher"):
        return (vol["publisher"] or {}).get("name", "")
    vol_detail = _get_volume(vol_id)
    pub = vol_detail.get("publisher") or {}
    return pub.get("name", "")


# Publishers that are US mainstream — get top tier ranking
TIER_1_PUBLISHERS = ["dc comics", "dc", "marvel comics", "marvel"]
TIER_2_PUBLISHERS = ["image comics", "image", "dark horse comics", "dark horse",
                     "idw publishing", "idw", "boom! studios", "boom studios",
                     "dynamite entertainment", "dynamite", "valiant entertainment",
                     "valiant", "aftershock comics", "aftershock", "awá studios",
                     "titan comics", "titan"]


def _get_series_popularity(issue: dict) -> int:
    """
    Two-factor ranking:
    1. Publisher tier — DC/Marvel always beat regional/manga publishers
    2. Series count_of_issues — within tier, more established = higher rank
    #1 issues get a bonus to surface new launches.

    Score breakdown:
    - Tier 1 (DC/Marvel):  base 1,000,000 + count_of_issues
    - Tier 2 (Image/DH):   base 500,000  + count_of_issues
    - Other:               base 0        + count_of_issues
    """
    vol = issue.get("volume") or {}
    vol_id = vol.get("id")
    if not vol_id:
        return 0

    vol_detail = _get_volume(vol_id)
    count = vol_detail.get("count_of_issues", 0) or 0

    # Get publisher for tier scoring
    pub = (vol_detail.get("publisher") or {}).get("name", "").lower().strip()

    if any(t in pub for t in TIER_1_PUBLISHERS):
        base = 1_000_000
    elif any(t in pub for t in TIER_2_PUBLISHERS):
        base = 500_000
    else:
        base = 0

    # #1 issues bonus — new launches are high interest
    num = (issue.get("issue_number") or "").strip()
    bonus = 200_000 if num == "1" else 0

    return base + count + bonus


REPRINT_KEYWORDS = [
    "omnibus","compendium","hardcover","trade paperback","tpb",
    "collected","complete","2nd printing","second printing",
    "anniversary edition","director's cut",
]


def _week_range(today: date = None) -> tuple[str, str]:
    d = today or date.today()
    days_since_wed = (d.weekday() - 2) % 7
    wednesday = d - timedelta(days=days_since_wed)
    tuesday   = wednesday + timedelta(days=6)
    return wednesday.strftime("%Y-%m-%d"), tuesday.strftime("%Y-%m-%d")


def _get(endpoint: str, params: dict) -> dict:
    params.update({"api_key": API_KEY, "format": "json"})
    resp = requests.get(
        f"{BASE_URL}/{endpoint}/",
        headers=HEADERS,
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _is_reprint(issue: dict) -> bool:
    name = (issue.get("name") or "").lower()
    vol  = (issue.get("volume") or {}).get("name", "").lower()
    return any(kw in name or kw in vol for kw in REPRINT_KEYWORDS)


def _pub_bucket(pub_name: str) -> str:
    p = pub_name.lower().strip()
    if any(n in p for n in DC_NAMES):     return "dc"
    if any(n in p for n in MARVEL_NAMES): return "marvel"
    if any(n in p for n in IMAGE_NAMES):  return "image"
    if any(n in p for n in DH_NAMES):     return "dark_horse"
    if any(n in p for n in IDW_NAMES):    return "idw"
    return "other"


# ── Getters ────────────────────────────────────────────────────────────────────

def get_title(issue: dict) -> str:
    vol  = (issue.get("volume") or {}).get("name", "Unknown")
    num  = issue.get("issue_number", "")
    name = issue.get("name") or ""
    if name:
        return f"{vol}: {name} #{num}" if num else f"{vol}: {name}"
    return f"{vol} #{num}" if num else vol


def get_cover_url(issue: dict) -> str | None:
    img = issue.get("image") or {}
    return (img.get("original_url") or
            img.get("super_url") or
            img.get("medium_url"))


def get_publisher(issue: dict) -> str:
    """Get publisher — from issue data or volume lookup."""
    # Try direct publisher field first
    direct = (issue.get("publisher") or {}).get("name", "")
    if direct:
        return direct
    # Fall back to volume lookup
    return _get_publisher_from_volume(issue)


def get_store_date(issue: dict) -> str:
    return issue.get("store_date", "")


def get_issue_number(issue: dict) -> str:
    return issue.get("issue_number", "")


# ── Fetch ──────────────────────────────────────────────────────────────────────

def _fetch_week(wed: str, tue: str, limit: int = 100) -> list[dict]:
    """Fetch all issues releasing this week in one call."""
    try:
        data = _get("issues", {
            "filter":     f"store_date:{wed}|{tue}",
            "field_list": "id,name,issue_number,volume,image,store_date,publisher",
            "sort":       "store_date:desc",
            "limit":      limit,
            "offset":     0,
        })
        return data.get("results", [])
    except Exception as e:
        print(f"  [comicvine] fetch error: {e}")
        return []


def fetch_top_weekly_issues(start: date = None, limit: int = 10) -> list[dict]:
    """
    Fetch top 10 new releases this week ranked by real series popularity.
    Uses count_of_issues from parent volume as popularity metric —
    flagship titles (Batman, Spider-Man) naturally rank above random indie books.
    #1 issues get a bonus to surface new launches.
    """
    wed, tue = _week_range(start)
    all_issues = _fetch_week(wed, tue, limit=100)

    seen: set[int] = set()
    candidates = []

    for issue in all_issues:
        iid = issue.get("id")
        if not iid or iid in seen:
            continue
        if _is_reprint(issue):
            continue
        seen.add(iid)
        candidates.append(issue)

    # Fetch publisher + popularity for all candidates
    # (volume cache means each unique volume is only fetched once)
    for issue in candidates:
        vol = issue.get("volume") or {}
        vol_id = vol.get("id")
        if vol_id:
            _get_volume(vol_id)  # pre-warm cache

    # Sort by series popularity descending
    candidates.sort(key=lambda i: _get_series_popularity(i), reverse=True)
    return candidates[:limit]


def fetch_variants_and_collectors(start: date = None, limit: int = 4) -> list[dict]:
    """Detect collector-worthy issues: #1s, ratio variants, foil, key issues."""
    wed, tue = _week_range(start)
    all_issues = _fetch_week(wed, tue, limit=100)

    VARIANT_CHECKS = [
        (["1:100"], "1:100 RATIO"),
        (["1:50"],  "1:50 RATIO"),
        (["1:25"],  "1:25 RATIO"),
        (["1:10"],  "1:10 RATIO"),
        (["foil variant","foil cover","gold foil"], "FOIL VARIANT"),
        (["virgin variant","virgin cover"],          "VIRGIN COVER"),
        (["connecting"],                             "CONNECTING CVR"),
        (["sketch variant"],                         "SKETCH COVER"),
        (["facsimile"],                              "FACSIMILE"),
        (["first appearance","1st appearance"],      "FIRST APPEARANCE"),
        (["anniversary"],                            "ANNIVERSARY"),
    ]

    combined = []
    seen: set[int] = set()

    for issue in all_issues:
        iid = issue.get("id")
        if not iid or iid in seen:
            continue
        title  = get_title(issue).lower()
        num    = (issue.get("issue_number") or "").strip()
        reason = None

        if num == "1":
            reason = "#1 ISSUE"
        if not reason:
            for keywords, label in VARIANT_CHECKS:
                if any(kw in title for kw in keywords):
                    reason = label
                    break

        if reason:
            seen.add(iid)
            combined.append({
                "title":     get_title(issue),
                "cover_url": get_cover_url(issue),
                "publisher": get_publisher(issue),
                "reason":    reason,
            })

    return combined[:limit]


def search_issue(query: str) -> dict | None:
    try:
        data = _get("search", {
            "query":      query,
            "resources":  "issue",
            "field_list": "id,name,issue_number,volume,image,store_date,publisher",
            "limit":      1,
        })
        results = data.get("results", [])
        return results[0] if results else None
    except Exception:
        return None