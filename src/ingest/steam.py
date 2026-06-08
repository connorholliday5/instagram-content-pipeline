import time
import requests

STEAM_BASE = "https://api.steampowered.com"
STORE_BASE = "https://store.steampowered.com"

RETRY_STATUS = {429, 500, 502, 503, 504}

# Fallback pool if the charts endpoint is unavailable. Well-known high
# concurrency titles; final ranking is always by live player count.
STEAM_FALLBACK_APPIDS = [
    730, 570, 578080, 271590, 1172470, 1085660,
    252490, 359550, 230410, 1245620, 413150, 1086940,
]


def _get_json(url: str, params: dict = None, attempts: int = 3) -> dict:
    last_exc = None
    for i in range(attempts):
        try:
            r = requests.get(url, params=params or {}, timeout=12)
            if r.status_code in RETRY_STATUS:
                last_exc = requests.exceptions.HTTPError(
                    f"{r.status_code} from Steam", response=r)
                time.sleep(1.5 * (i + 1))
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            last_exc = e
            time.sleep(1.5 * (i + 1))
    if last_exc:
        raise last_exc
    return {}


def _most_played_appids(pool: int = 12) -> list[int]:
    """Ordered appids from Steam's most-played charts, fallback to a static
    pool if the endpoint is unavailable."""
    try:
        data = _get_json(f"{STEAM_BASE}/ISteamChartsService/GetMostPlayedGames/v1/")
        ranks = (data.get("response") or {}).get("ranks") or []
        appids = [r.get("appid") for r in ranks if r.get("appid")]
        if appids:
            return appids[:pool]
    except requests.exceptions.RequestException:
        pass
    return list(STEAM_FALLBACK_APPIDS)


def _current_players(appid: int) -> int:
    try:
        data = _get_json(
            f"{STEAM_BASE}/ISteamUserStats/GetNumberOfCurrentPlayers/v1/",
            {"appid": appid})
        resp = data.get("response") or {}
        if resp.get("result") == 1:
            return int(resp.get("player_count", 0) or 0)
    except requests.exceptions.RequestException:
        pass
    return 0


def _app_name(appid: int) -> str:
    try:
        data = _get_json(f"{STORE_BASE}/api/appdetails",
                         {"appids": appid, "filters": "basic"})
        entry = data.get(str(appid)) or {}
        if entry.get("success") and entry.get("data"):
            return entry["data"].get("name") or f"App {appid}"
    except requests.exceptions.RequestException:
        pass
    return f"App {appid}"


def _poster_url(appid: int) -> str:
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_600x900.jpg"


# Accessors used by the carousel builder

def get_steam_title(g: dict) -> str:
    return g.get("name", "Unknown")


def get_steam_poster_url(g: dict) -> str | None:
    return g.get("poster_url")


def get_steam_players(g: dict) -> int:
    return g.get("players", 0) or 0


def format_players(n: int) -> str:
    n = n or 0
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{n:,}"


def fetch_most_played(limit: int = 3) -> list[dict]:
    """
    Live most played games on Steam, ranked by current concurrent players.
    Returns [] if Steam is unreachable so the carousel skips slide 4.
    """
    appids = _most_played_appids()
    counted = []
    for appid in appids:
        players = _current_players(appid)
        if players > 0:
            counted.append((appid, players))

    counted.sort(key=lambda x: x[1], reverse=True)
    top = counted[:limit]

    rows = []
    for appid, players in top:
        rows.append({
            "appid": appid,
            "players": players,
            "name": _app_name(appid),
            "poster_url": _poster_url(appid),
        })
    return rows