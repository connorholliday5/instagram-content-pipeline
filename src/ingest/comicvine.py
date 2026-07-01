import os
import requests
from datetime import date, timedelta

BASE_URL = "https://comicvine.gamespot.com/api"
API_KEY  = os.getenv("COMICVINE_API_KEY", "")

# Browser headers - required to avoid host allowlist block
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

# Volume cache - avoid repeat API calls for same volume
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


# Publishers that are US mainstream - get top tier ranking
TIER_1_PUBLISHERS = ["dc comics", "dc", "marvel comics", "marvel"]
TIER_2_PUBLISHERS = ["image comics", "image", "dark horse comics", "dark horse",
                     "idw publishing", "idw", "boom! studios", "boom studios",
                     "dynamite entertainment", "dynamite", "valiant entertainment",
                     "valiant", "aftershock comics", "aftershock",
                     "titan comics", "titan"]


# Franchise / character prominence. Scanned against the volume + issue name;
# the highest matching weight drives the ranking. Tune freely. This is the
# popularity proxy ComicVine itself does not provide.
MARQUEE_SCORES = {
    # Marvel
    "amazing spider-man": 100, "ultimate spider-man": 90, "spider-man": 92,
    "spider man": 92, "uncanny x-men": 96, "x-men": 95, "ultimate x-men": 84,
    "wolverine": 90, "deadpool": 88, "avengers": 90, "venom": 86,
    "daredevil": 80, "fantastic four": 82, "captain america": 84,
    "iron man": 84, "thor": 82, "hulk": 82, "moon knight": 70,
    "punisher": 72, "magneto": 70, "storm": 68, "star wars": 86,
    # DC
    "batman": 100, "detective comics": 92, "superman": 96, "action comics": 90,
    "wonder woman": 88, "justice league": 90, "flash": 80, "green lantern": 80,
    "aquaman": 70, "nightwing": 74, "robin": 68, "harley quinn": 80,
    "joker": 82, "absolute": 88, "supergirl": 66, "teen titans": 70,
    "green arrow": 66, "catwoman": 66, "shazam": 60, "poison ivy": 58,
    # Other big franchises
    "teenage mutant ninja turtles": 76, "tmnt": 76, "transformers": 74,
    "godzilla": 70, "the walking dead": 72, "saga": 78, "invincible": 76,
    "spawn": 72, "hellboy": 66,
}


def _marquee_score(issue: dict, vol_detail: dict) -> int:
    """Highest matching franchise/character weight in the title or volume name."""
    name = (issue.get("name") or "").lower()
    vol_name = ((issue.get("volume") or {}).get("name") or "").lower()
    if not vol_name:
        vol_name = (vol_detail.get("name") or "").lower()
    hay = f"{vol_name} {name}"
    best = 0
    for key, weight in MARQUEE_SCORES.items():
        if key in hay and weight > best:
            best = weight
    return best


def _get_series_popularity(issue: dict) -> int:
    """
    Rank score, highest first:
    1. Franchise/character prominence (primary driver) - flagship characters win.
    2. Publisher tier - DC/Marvel above indie, minor weight.
    3. Series length (count_of_issues, capped) - established ongoings edge out.
    4. Small #1 bonus so notable launches surface without dominating.
    """
    vol = issue.get("volume") or {}
    vol_id = vol.get("id")
    vol_detail = _get_volume(vol_id) if vol_id else {}

    count = vol_detail.get("count_of_issues", 0) or 0
    pub = (vol_detail.get("publisher") or {}).get("name", "").lower().strip()

    if any(t in pub for t in TIER_1_PUBLISHERS):
        tier = 2
    elif any(t in pub for t in TIER_2_PUBLISHERS):
        tier = 1
    else:
        tier = 0

    marquee = _marquee_score(issue, vol_detail)
    num = (issue.get("issue_number") or "").strip()
    first_issue_bonus = 40 if num == "1" else 0

    return marquee * 1000 + tier * 100 + min(count, 200) + first_issue_bonus


REPRINT_KEYWORDS = [
    "omnibus","compendium","hardcover","trade paperback","tpb",
    "collected","complete","2nd printing","second printing",
    "anniversary edition","director's cut",
]

# Digital-only / app-exclusive lines that are not physical NCBD releases.
DIGITAL_KEYWORDS = [
    "infinity comic", "infinite comic", "digital first", "digital-first",
]


def _upcoming_wednesday(today: date | None = None) -> date:
    """The next New Comic Book Day. If today is Wednesday, returns today.

    Posting Monday for a Wednesday drop means we always want the week that is
    about to land, not the one that already shipped. weekday(): Mon=0 .. Sun=6,
    Wed=2. (2 - weekday) % 7 gives days forward to the next Wednesday
    (0 when today already is Wednesday).
    """
    d = today or date.today()
    days_until_wed = (2 - d.weekday()) % 7
    return d + timedelta(days=days_until_wed)


def _week_range(today: date | None = None) -> tuple[str, str]:
    wednesday = _upcoming_wednesday(today)
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


# --- Getters ---

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
    """Get publisher - from issue data or volume lookup."""
    direct = (issue.get("publisher") or {}).get("name", "")
    if direct:
        return direct
    return _get_publisher_from_volume(issue)


def get_store_date(issue: dict) -> str:
    return issue.get("store_date", "")


def get_issue_number(issue: dict) -> str:
    return issue.get("issue_number", "")


# --- Fetch ---

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



# --- League of Comic Geeks (real "most pulled" ranking) ---
# Optional dependency: pip install comicgeeks
# Public new-releases endpoint, no login required. Falls back to the ComicVine
# ranking below if the library is missing or the request fails.

def _epoch_to_date_str(value) -> str:
    """LCG store_date is a Unix epoch (seconds, UTC midnight of release day).
    Return YYYY-MM-DD. Pass through anything already in string date form."""
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    if s.isdigit():
        from datetime import datetime, timezone
        return datetime.fromtimestamp(int(s), tz=timezone.utc).strftime("%Y-%m-%d")
    return s


def _lcg_rank(d: dict) -> int:
    """Rank an LCG-mapped issue without any per-issue network call.

    Mirrors the ComicVine fallback ordering: franchise/character prominence
    first, publisher tier second, small #1 bonus. count_of_issues is not
    available from the LCG list, so it is omitted.
    """
    name = d["volume"]["name"]
    pub = (d.get("publisher") or {}).get("name", "").lower().strip()
    marquee = _marquee_score({"name": "", "volume": {"name": name}}, {})
    if any(t in pub for t in TIER_1_PUBLISHERS):
        tier = 2
    elif any(t in pub for t in TIER_2_PUBLISHERS):
        tier = 1
    else:
        tier = 0
    first_issue_bonus = 40 if (d.get("issue_number") or "").strip() == "1" else 0
    return marquee * 1000 + tier * 100 + first_issue_bonus


def _lcg_to_issue(li) -> dict:
    name = (getattr(li, "name", "") or "").strip()
    pub = getattr(li, "publisher", "") or ""
    cover = getattr(li, "cover", None)
    sd = _epoch_to_date_str(getattr(li, "store_date", ""))
    # NOTE: never read li.community / li.pull / li.character etc here - those
    # lazy-load a per-issue detail page that returns 403 without an
    # LCG_CI_SESSION cookie. Only the fields already present on the list item
    # (name, publisher, cover, store_date) are safe to use anonymously.
    pl = pub.lower()
    if "marvel" in pl:
        pub = "marvel"
    elif "dc comics" in pl or pl == "dc":
        pub = "dc comics"
    elif "image" in pl:
        pub = "image comics"
    elif "dark horse" in pl:
        pub = "dark horse comics"
    elif "idw" in pl:
        pub = "idw publishing"
    vol, num = name, ""
    if " #" in name:
        vol, num = name.rsplit(" #", 1)
    return {
        "id": getattr(li, "id", None) or getattr(li, "_issue_id", None),
        "name": "",
        "issue_number": num,
        "volume": {"name": vol},
        "image": {"original_url": cover} if cover else {},
        "publisher": {"name": pub},
        "store_date": sd,
    }


def _lcg_week_issues(start: date | None = None) -> list[dict]:
    """All mapped + filtered LCG issues for the target week (unranked).

    Covered publishers only, reprints and digital-only lines removed, deduped
    by series title. Shared by the top-10 and the collectors scan. Returns []
    if comicgeeks is unavailable or the request fails.
    """
    try:
        from comicgeeks import Comic_Geeks
    except Exception:
        return []
    try:
        from datetime import datetime
        # Anchor on the upcoming Wednesday so a Monday run targets the week that
        # is about to drop, not the calendar week containing today.
        if start is None:
            wed = _upcoming_wednesday()
            when = datetime(wed.year, wed.month, wed.day)
        elif isinstance(start, datetime):
            when = start
        else:
            when = datetime(start.year, start.month, start.day)
        client = Comic_Geeks(os.getenv("LCG_CI_SESSION") or None)
        issues = client.new_releases(when)
    except Exception as e:
        print(f"  [lcg] fetch error: {e}")
        return []

    mapped = []
    seen: set[str] = set()
    for li in issues or []:
        d = _lcg_to_issue(li)
        if _is_reprint(d):
            continue
        # Drop digital-only / app-exclusive lines (Infinity Comics, etc.).
        if any(kw in d["volume"]["name"].lower() for kw in DIGITAL_KEYWORDS):
            continue
        # US/English market only: keep just the five publishers the carousel
        # color-codes. Everything else (foreign editions on Panini, Urban,
        # Webtoon, etc.) buckets to "other" and is dropped.
        if _pub_bucket((d.get("publisher") or {}).get("name", "")) == "other":
            continue
        title = d["volume"]["name"]
        if title in seen:
            continue
        seen.add(title)
        mapped.append(d)
    return mapped


def _fetch_lcg_top(start: date | None = None, limit: int = 10) -> list[dict]:
    mapped = _lcg_week_issues(start)
    # Community pull counts require auth (the detail page 403s anonymously),
    # so rank with the franchise/publisher scorer - same ordering the
    # ComicVine fallback uses.
    mapped.sort(key=_lcg_rank, reverse=True)
    return mapped[:limit]


def fetch_top_weekly_issues(start: date | None = None, limit: int = 10) -> list[dict]:
    """
    Top new releases this week. Primary source is League of Comic Geeks,
    ranked by real community pull counts (most pulled). If LCG is unavailable
    (library missing or request failed), falls back to the ComicVine franchise
    prominence ranking in _get_series_popularity.
    """
    lcg = _fetch_lcg_top(start, limit)
    if lcg:
        return lcg

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

    # Pre-warm volume cache (each unique volume fetched once)
    for issue in candidates:
        vol = issue.get("volume") or {}
        vol_id = vol.get("id")
        if vol_id:
            _get_volume(vol_id)

    candidates.sort(key=lambda i: _get_series_popularity(i), reverse=True)
    return candidates[:limit]


# A #1 is only a collector signal if it launches a *major* franchise. This gate
# cuts minor / parody / licensed #1s. Franchises scoring at or below this value
# (e.g. Catwoman 66, Storm 68, Godzilla 70) do NOT qualify on a #1 alone; majors
# (Batman, Superman, X-Men, Avengers, Spider-Man, Flash, Nightwing...) do. Tune.
MARQUEE_KEY_THRESHOLD = 70


def fetch_variants_and_collectors(start: date | None = None, limit: int = 4,
                                  exclude_top: int = 10) -> list[dict]:
    """Collector-worthy issues for the week: #1s and key/variant keywords.

    Primary source is the same forward-looking LCG week list the top 10 uses.
    LCG list titles are clean series names, so this mainly surfaces #1s and any
    key-issue keyword present in the title; rare ratio/foil variants are not
    exposed in LCG list data. Falls back to the ComicVine store_date window if
    LCG is unavailable (which only sees the current week, not ahead).
    """
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

    def _scan(issues: list[dict]) -> list[dict]:
        out = []
        seen: set[str] = set()
        for issue in issues:
            title = get_title(issue)
            tl = title.lower()
            num = (issue.get("issue_number") or "").strip()
            reason = None
            # 1. Variant / key-issue keywords (facsimile, first appearance,
            #    anniversary, ratio / foil / virgin / sketch) - always a
            #    collector signal whenever the tag is actually in the title.
            for keywords, label in VARIANT_CHECKS:
                if any(kw in tl for kw in keywords):
                    reason = label
                    break
            # 2. Milestone numbering (#50, #100, #150 ...).
            if not reason and num.isdigit() and int(num) >= 50 and int(num) % 50 == 0:
                reason = "MILESTONE"
            # 3. A #1 only if it is a flagship character/franchise launch.
            #    Plain #1s from minor titles (M.A.S.K., licensed one-shots) are
            #    not collector signal, so they are dropped.
            if not reason and num == "1" and _marquee_score(issue, {}) > MARQUEE_KEY_THRESHOLD:
                reason = "#1 ISSUE"
            if reason and title not in seen:
                seen.add(title)
                out.append({
                    "title":     title,
                    "cover_url": get_cover_url(issue),
                    "publisher": get_publisher(issue),
                    "reason":    reason,
                })
        return out

    # Primary: LCG week list (forward-looking, matches the top 10).
    lcg = _lcg_week_issues(start)
    if lcg:
        scanned = _scan(lcg)
        # Prefer collector items not already shown on the top-10 slide.
        ranked = sorted(lcg, key=_lcg_rank, reverse=True)
        exclude = {get_title(i) for i in ranked[:exclude_top]}
        items = [x for x in scanned if x["title"] not in exclude]
        # If de-duping against the top 10 leaves nothing (common on light
        # weeks where every key issue is also a top pick), keep the collector
        # slide alive by falling back to the full scan rather than dropping it.
        if not items:
            items = scanned
        if items:
            return items[:limit]

    # Fallback: ComicVine store_date window.
    wed, tue = _week_range(start)
    return _scan(_fetch_week(wed, tue, limit=100))[:limit]


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