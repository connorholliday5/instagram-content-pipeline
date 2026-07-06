import os
import requests
from datetime import date, timedelta
from calendar import monthrange

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/w500"

# TV region preference: keep the carousel mostly American / European. Shows that
# originate in one of these countries are surfaced first (good animated shows /
# anime are also surfaced — see _is_good_animation). Everything else (K-dramas,
# telenovelas, Turkish / Indian series, etc.) only backfills when there aren't
# enough preferred shows to fill the slide. Edit this set to widen or narrow
# what counts as "American / European".
PREFERRED_TV_COUNTRIES = {
    "US", "CA",                                  # North America
    "GB", "IE",                                  # UK + Ireland
    "FR", "DE", "ES", "IT", "NL", "BE", "PT",    # Western Europe
    "SE", "NO", "DK", "FI", "IS",                # Nordics
    "PL", "CZ", "AT", "CH", "GR", "HU", "RO",    # Central / Southern / Eastern Europe
}


def _get(endpoint: str, params: dict = {}) -> dict:
    params["api_key"] = TMDB_API_KEY
    params["language"] = "en-US"
    resp = requests.get(f"{TMDB_BASE}{endpoint}", params=params, timeout=12)
    resp.raise_for_status()
    return resp.json()


def _month_range(target: date = None) -> tuple[str, str]:
    """Return first and last day of target month as strings."""
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


# Movie helpers

def get_movie_poster_url(movie: dict) -> str | None:
    path = movie.get("poster_path")
    return f"{TMDB_IMG}{path}" if path else None


def get_movie_title(movie: dict) -> str:
    return movie.get("title", "Unknown")


def get_movie_release_date(movie: dict) -> str:
    return movie.get("release_date", "")


def get_movie_revenue(movie: dict) -> int:
    return movie.get("revenue", 0)


def get_movie_popularity(movie: dict) -> float:
    return movie.get("popularity", 0.0)


def get_movie_genres(movie: dict) -> list[str]:
    return [g["name"] for g in movie.get("genres", [])]


def format_revenue(n: int) -> str:
    if n >= 1_000_000_000:
        return f"${n/1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"${n/1_000:.0f}K"
    return f"${n:,}"


def fetch_anticipated_movies(target: date = None, limit: int = 10) -> list[dict]:
    """
    Fetch top anticipated movies releasing this month,
    sorted by TMDB popularity descending.
    """
    start, end = _month_range(target)
    results = []
    page = 1

    while len(results) < 50 and page <= 5:
        data = _get("/discover/movie", {
            "primary_release_date.gte": start,
            "primary_release_date.lte": end,
            "sort_by": "popularity.desc",
            "page": page,
            "region": "US",
        })
        movies = data.get("results", [])
        if not movies:
            break
        results.extend(movies)
        if page >= data.get("total_pages", 1):
            break
        page += 1

    results.sort(key=lambda m: m.get("popularity", 0), reverse=True)
    return results[:limit]


def fetch_top_grossing_last_month(target: date = None, limit: int = 3) -> list[dict]:
    """
    Fetch top grossing movies from last month with revenue data.
    """
    start, end = _prev_month_range(target)
    results = []
    page = 1

    while len(results) < 50 and page <= 5:
        data = _get("/discover/movie", {
            "primary_release_date.gte": start,
            "primary_release_date.lte": end,
            "sort_by": "revenue.desc",
            "page": page,
            "region": "US",
        })
        movies = data.get("results", [])
        if not movies:
            break
        results.extend(movies)
        if page >= data.get("total_pages", 1):
            break
        page += 1

    detailed = []
    for movie in results[:20]:
        try:
            detail = _get(f"/movie/{movie['id']}")
            if detail.get("revenue", 0) > 0:
                detailed.append(detail)
        except Exception:
            continue
        if len(detailed) >= limit:
            break

    detailed.sort(key=lambda m: m.get("revenue", 0), reverse=True)
    return detailed[:limit]


# TV helpers

def get_show_poster_url(show: dict) -> str | None:
    path = show.get("poster_path")
    return f"{TMDB_IMG}{path}" if path else None


def get_show_title(show: dict) -> str:
    return show.get("name", "Unknown")


def get_show_premiere_date(show: dict) -> str:
    return show.get("first_air_date", "")


def get_show_popularity(show: dict) -> float:
    return show.get("popularity", 0.0)


def get_show_network(show: dict) -> str:
    networks = show.get("networks", [])
    return networks[0]["name"] if networks else ""


def get_show_origin_country(show: dict) -> list[str]:
    return show.get("origin_country", []) or []


def get_show_original_language(show: dict) -> str:
    return show.get("original_language", "") or ""


# Good animated shows / anime are welcome even though they are not American /
# European. TMDB genre 16 == Animation. "Good" = well rated once enough people
# have voted; brand-new premieres with too few votes are allowed through and
# left to the popularity ordering (they can't be judged on rating yet).
ANIMATION_GENRE_ID = 16
GOOD_ANIME_MIN_RATING = 7.0
GOOD_ANIME_MIN_VOTES = 30


def _is_western(show: dict) -> bool:
    """American / European by origin country. Falls back to English language
    only when origin_country is missing, so US/UK shows with sparse metadata
    still count while Spanish/Portuguese-language Latin American shows do not
    sneak in on language alone."""
    countries = get_show_origin_country(show)
    if any(c in PREFERRED_TV_COUNTRIES for c in countries):
        return True
    if not countries and get_show_original_language(show) == "en":
        return True
    return False


def _is_animation(show: dict) -> bool:
    ids = show.get("genre_ids") or [g.get("id") for g in show.get("genres", [])]
    return ANIMATION_GENRE_ID in (ids or [])


def _is_good_animation(show: dict) -> bool:
    """Animated show / anime that is either well rated or too new to judge."""
    if not _is_animation(show):
        return False
    votes = show.get("vote_count", 0) or 0
    if votes >= GOOD_ANIME_MIN_VOTES:
        return (show.get("vote_average", 0.0) or 0.0) >= GOOD_ANIME_MIN_RATING
    return True  # too few votes to rate yet — let popularity decide


def _is_preferred(show: dict) -> bool:
    """Surfaced first: American / European shows plus good animated shows / anime."""
    return _is_western(show) or _is_good_animation(show)


def _ranked_preferred_first(shows: list[dict], limit: int) -> list[dict]:
    """
    American / European shows and good anime first, ranked by popularity.
    Everything else only backfills when there aren't enough preferred shows to
    fill the carousel, so the result is mostly Western plus quality animation.
    """
    by_pop = sorted(shows, key=lambda s: s.get("popularity", 0.0) or 0.0, reverse=True)
    preferred = [s for s in by_pop if _is_preferred(s)]
    if len(preferred) >= limit:
        return preferred[:limit]
    rest = [s for s in by_pop if not _is_preferred(s)]
    return (preferred + rest)[:limit]


def fetch_anticipated_shows(target: date = None, limit: int = 10) -> list[dict]:
    """
    Fetch TV shows premiering this month that are available in the US, then
    rank American / European shows and good anime first (_ranked_preferred_first).
    """
    start, end = _month_range(target)
    results = []
    page = 1

    while len(results) < 100 and page <= 5:
        data = _get("/discover/tv", {
            "first_air_date.gte": start,
            "first_air_date.lte": end,
            "sort_by": "popularity.desc",
            "watch_region": "US",
            "page": page,
        })
        shows = data.get("results", [])
        if not shows:
            break
        results.extend(shows)
        if page >= data.get("total_pages", 1):
            break
        page += 1

    return _ranked_preferred_first(results, limit)


def fetch_popular_shows_last_month(target: date = None, limit: int = 3) -> list[dict]:
    """
    Most popular shows from last month, American / European first to match the
    top 10 ranking.
    """
    start, end = _prev_month_range(target)
    results = []
    page = 1

    while len(results) < 100 and page <= 5:
        data = _get("/discover/tv", {
            "first_air_date.gte": start,
            "first_air_date.lte": end,
            "sort_by": "popularity.desc",
            "watch_region": "US",
            "page": page,
        })
        shows = data.get("results", [])
        if not shows:
            break
        results.extend(shows)
        if page >= data.get("total_pages", 1):
            break
        page += 1

    return _ranked_preferred_first(results, limit)


def get_show_vote_average(show: dict) -> float:
    return round(show.get("vote_average", 0.0), 1)


def get_show_vote_count(show: dict) -> int:
    return show.get("vote_count", 0)


def get_show_popularity_score(show: dict) -> float:
    return round(show.get("popularity", 0.0), 1)


def format_vote_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M votes"
    if n >= 1_000:
        return f"{n/1_000:.1f}K votes"
    return f"{n} votes"


def format_popularity(n: float) -> str:
    """TMDB popularity score - higher = more buzz."""
    if n >= 1000:
        return f"{n/1000:.1f}K popularity"
    return f"{n:.0f} popularity"