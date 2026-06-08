import os
import time
import requests
from datetime import date, timedelta
from calendar import monthrange

RAWG_API_KEY = os.getenv("RAWG_API_KEY")
RAWG_BASE = "https://api.rawg.io/api"

# RAWG parent platform IDs: 1=PC, 2=PlayStation, 3=Xbox, 7=Nintendo
PARENT_PLATFORMS = "1,2,3,7"

# Short labels for the platform line on slides
PLATFORM_LABELS = {
    1: "PC",
    2: "PlayStation",
    3: "Xbox",
    7: "Switch",
}

# Transient gateway errors worth retrying
RETRY_STATUS = {429, 500, 502, 503, 504}


def _get(endpoint: str, params: dict = {}, attempts: int = 3) -> dict:
    params["key"] = RAWG_API_KEY
    last_exc = None
    for i in range(attempts):
        try:
            resp = requests.get(f"{RAWG_BASE}{endpoint}", params=params, timeout=12)
            if resp.status_code in RETRY_STATUS:
                last_exc = requests.exceptions.HTTPError(
                    f"{resp.status_code} from RAWG", response=resp)
                time.sleep(1.5 * (i + 1))
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            last_exc = e
            time.sleep(1.5 * (i + 1))
    if last_exc:
        raise last_exc
    return {}


def _month_range(target: date = None) -> tuple[str, str]:
    """Return first and last day of target month as YYYY-MM-DD strings."""
    d = target or date.today()
    first = d.replace(day=1)
    last = d.replace(day=monthrange(d.year, d.month)[1])
    return first.strftime("%Y-%m-%d"), last.strftime("%Y-%m-%d")


def _prev_month_range(target: date = None) -> tuple[str, str]:
    """Return first and last day of previous month."""
    d = target or date.today()
    first_this = d.replace(day=1)
    last_prev = first_this - timedelta(days=1)
    first_prev = last_prev.replace(day=1)
    return first_prev.strftime("%Y-%m-%d"), last_prev.strftime("%Y-%m-%d")


# Game helpers

def get_game_poster_url(game: dict) -> str | None:
    return game.get("background_image") or None


def get_game_title(game: dict) -> str:
    return game.get("name", "Unknown")


def get_game_release_date(game: dict) -> str:
    return game.get("released", "") or ""


def get_game_added(game: dict) -> int:
    """RAWG 'added' count: how many users have the game in their library.
    Best free proxy for player base / popularity (no live CCU exists free)."""
    return game.get("added", 0) or 0


def get_game_rating(game: dict) -> float:
    return round(game.get("rating", 0.0) or 0.0, 1)


def get_game_metacritic(game: dict):
    return game.get("metacritic")


def get_game_platforms(game: dict) -> str:
    """Compact platform string, e.g. 'PC, PlayStation, Xbox'."""
    seen = []
    for p in game.get("parent_platforms", []) or []:
        pid = (p.get("platform") or {}).get("id")
        label = PLATFORM_LABELS.get(pid)
        if label and label not in seen:
            seen.append(label)
    return ", ".join(seen)


def format_metacritic(n) -> str:
    if not n:
        return ""
    return f"Metacritic {n}"


def format_rating(n: float) -> str:
    if not n:
        return ""
    return f"{n:.1f}/5"


def format_added(n: int) -> str:
    n = n or 0
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{n}"


def fetch_anticipated_games(target: date = None, limit: int = 10) -> list[dict]:
    """
    Fetch this month's game releases (PC, PlayStation, Xbox, Switch),
    sorted by RAWG popularity (added count) descending. Degrades to whatever
    was collected if RAWG errors out mid-paging.
    """
    start, end = _month_range(target)
    results = []
    page = 1

    while len(results) < 60 and page <= 5:
        try:
            data = _get("/games", {
                "dates": f"{start},{end}",
                "parent_platforms": PARENT_PLATFORMS,
                "ordering": "-added",
                "page_size": 40,
                "page": page,
            })
        except requests.exceptions.RequestException:
            break
        games = data.get("results", [])
        if not games:
            break
        results.extend(games)
        if not data.get("next"):
            break
        page += 1

    results.sort(key=lambda g: g.get("added", 0) or 0, reverse=True)
    return results[:limit]


def fetch_most_played(limit: int = 3) -> list[dict]:
    """
    Most played games overall, ranked by RAWG 'added' count (largest player
    bases / libraries). Not date limited. Returns [] if RAWG is unavailable so
    the carousel just skips slide 4 instead of crashing.
    """
    results = []
    page = 1

    while len(results) < 40 and page <= 3:
        try:
            data = _get("/games", {
                "parent_platforms": PARENT_PLATFORMS,
                "ordering": "-added",
                "page_size": 20,
                "page": page,
            })
        except requests.exceptions.RequestException:
            break
        games = data.get("results", [])
        if not games:
            break
        results.extend(games)
        if not data.get("next"):
            break
        page += 1

    results.sort(key=lambda g: g.get("added", 0) or 0, reverse=True)
    return results[:limit]


def fetch_top_rated_last_month(target: date = None, limit: int = 3) -> list[dict]:
    """
    Last month's game releases by Metacritic. Kept for reference; the
    monthly carousel now uses fetch_most_played for slide 4.
    """
    start, end = _prev_month_range(target)
    results = []
    page = 1

    while len(results) < 60 and page <= 5:
        try:
            data = _get("/games", {
                "dates": f"{start},{end}",
                "parent_platforms": PARENT_PLATFORMS,
                "ordering": "-metacritic",
                "page_size": 40,
                "page": page,
            })
        except requests.exceptions.RequestException:
            break
        games = data.get("results", [])
        if not games:
            break
        results.extend(games)
        if not data.get("next"):
            break
        page += 1

    def _score(g: dict):
        mc = g.get("metacritic")
        if mc:
            return (1, mc)
        return (0, g.get("rating", 0.0) or 0.0)

    results.sort(key=_score, reverse=True)
    return results[:limit]