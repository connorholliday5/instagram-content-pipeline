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
    Fetch top anticipated movies releasing this month, ranked by weighted
    anticipation (_movie_anticipation: western + comic/superhero + fantasy/
    sci-fi + animation boosts) with comic titles capped so non-comic films
    stay represented.
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

    results = [m for m in results if m.get("poster_path")]
    caps = [
        (lambda x: not _is_western_movie(x), max(1, round(limit * MOVIE_MAX_NONWESTERN_SHARE))),
        (lambda x: _is_comic_hero(get_movie_title(x)), max(1, round(limit * COMIC_MAX_SHARE))),
    ]
    return _select_balanced(results, _movie_anticipation, limit, caps)


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

# Genre ids that define this account's geek/genre lane. TV is filtered to these
# (plus comic/superhero titles) so generic drama / rom-com / reality / soap gets
# demoted no matter where it's from. TMDB TV: 10765 Sci-Fi & Fantasy, 10759
# Action & Adventure, 16 Animation. Movies split fantasy/sci-fi into 14 / 878.
SCIFI_FANTASY_TV_GENRE = 10765
ACTION_ADVENTURE_TV_GENRE = 10759
FANTASY_MOVIE_GENRES = {14, 878}


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


# Comic-book / superhero franchises (and a few comic-adjacent ones). Matched
# against the title so shows/movies like "My Adventures with Superman" or
# "Batman: Caped Crusader" get a ranking boost — especially the animated ones.
COMIC_HERO_TERMS = {
    # Marvel
    "marvel", "spider-man", "spider man", "spiderman", "x-men", "wolverine",
    "deadpool", "avengers", "venom", "daredevil", "fantastic four",
    "captain america", "captain marvel", "iron man", "thor", "hulk",
    "black panther", "guardians of the galaxy", "moon knight", "loki",
    "wandavision", "hawkeye", "ironheart", "agatha", "punisher", "blade",
    "ghost rider", "wakanda", "x-force", "eyes of wakanda",
    # DC
    "superman", "batman", "wonder woman", "justice league", "the flash",
    "green lantern", "green arrow", "aquaman", "shazam", "supergirl",
    "teen titans", "harley quinn", "suicide squad", "peacemaker",
    "blue beetle", "gotham", "titans", "doom patrol", "creature commandos",
    "the penguin", "joker", "nightwing", "swamp thing", "constantine",
    "my adventures with superman", "caped crusader",
    # Other comics / comic-adjacent
    "the boys", "invincible", "the walking dead", "hellboy", "spawn",
    "kick-ass", "kingsman", "umbrella academy", "sandman", "watchmen",
    "sweet tooth", "y the last man", "paper girls", "locke & key",
    "the old guard", "kraven", "sin city", "v for vendetta",
    "teenage mutant ninja turtles", "tmnt", "transformers",
    "superhero", "super hero", "super-hero",
}

# Western languages for the (less strict) movie region bias, used when a movie
# has no origin_country. TV uses country codes (PREFERRED_TV_COUNTRIES) instead.
WESTERN_LANGUAGES = {
    "en", "fr", "de", "es", "it", "nl", "sv", "no", "da", "fi", "is",
    "pt", "pl", "cs", "el", "hu", "ro", "ga",
}

# Anticipation weights (added to a base of 1.0, then multiplied by TMDB
# popularity — the anticipation proxy). TV leans harder on region + comics;
# movies use the same idea but softer, and treat any animated film as welcome
# if it's anticipated. Content matching none of the signals is demoted by the
# "other" penalty instead of getting a bonus.
# TV leads with genre (this is a geek account): sci-fi/fantasy, action/adventure,
# animation, and comic/superhero are the lane. Region (western) and rating (good
# anime) are secondary nudges among that genre content; anything that isn't genre
# content is demoted by "other".
TV_WEIGHTS = {"fantasy": 2.5, "action": 1.5, "comic_hero": 2.5, "animation": 1.0,
              "western": 1.0, "good_anime": 1.0, "other": 0.2}
MOVIE_WEIGHTS = {"western": 0.7, "comic_hero": 1.2, "fantasy": 1.0, "animation": 0.8, "other": 0.6}

# Cap comic/superhero titles at this share of a carousel so non-comic content
# (fantasy, sci-fi, drama, animation, etc.) is always represented. The rest of
# the slots go to the highest-ranked non-comic titles.
COMIC_MAX_SHARE = 0.5

# Cap non-American/European titles so the carousels stay mostly Western. The
# limited non-Western slots go to the highest-scoring foreign content, which —
# after the anime boost and the penalty on everything else — is good anime. TV
# is stricter than movies. Bumped up/down to allow more or less foreign content.
MAX_NONWESTERN_SHARE = 0.3          # TV: ~70% American / European
MOVIE_MAX_NONWESTERN_SHARE = 0.4    # movies: less strict about region

# "Most popular last month" needs real audience traction — ignore obscure
# entries with only a handful of votes so a 3-vote show can't rank #1.
POPULAR_MIN_VOTES = 50


def _is_comic_hero(title: str) -> bool:
    t = (title or "").lower()
    return any(term in t for term in COMIC_HERO_TERMS)


def _is_scifi_fantasy(obj: dict, is_tv: bool) -> bool:
    ids = obj.get("genre_ids") or [g.get("id") for g in obj.get("genres", [])] or []
    if is_tv:
        return SCIFI_FANTASY_TV_GENRE in ids
    return any(g in FANTASY_MOVIE_GENRES for g in ids)


def _is_western_movie(movie: dict) -> bool:
    """Movie region bias (less strict than TV): origin country when present,
    otherwise original language."""
    countries = movie.get("origin_country") or []
    if any(c in PREFERRED_TV_COUNTRIES for c in countries):
        return True
    return (movie.get("original_language") or "") in WESTERN_LANGUAGES


def _is_geek_tv(show: dict) -> bool:
    """Genre content that fits the account: sci-fi/fantasy, action/adventure,
    animation, or a comic/superhero title."""
    genres = show.get("genre_ids") or [g.get("id") for g in show.get("genres", [])] or []
    if SCIFI_FANTASY_TV_GENRE in genres or ACTION_ADVENTURE_TV_GENRE in genres:
        return True
    if _is_animation(show):
        return True
    return _is_comic_hero(get_show_title(show))


def _tv_anticipation(show: dict) -> float:
    """Effective anticipation for a show. This is a geek/genre account, so genre
    content — sci-fi & fantasy, action/adventure, animation, comic/superhero — is
    the lane. Region (western) and rating (good anime) are secondary nudges among
    that genre content. Generic drama / rom-com / reality / soap is demoted."""
    pop = show.get("popularity", 0.0) or 0.0
    genres = show.get("genre_ids") or [g.get("id") for g in show.get("genres", [])] or []
    weight, geek = 1.0, False
    if SCIFI_FANTASY_TV_GENRE in genres:
        weight += TV_WEIGHTS["fantasy"]; geek = True
    if ACTION_ADVENTURE_TV_GENRE in genres:
        weight += TV_WEIGHTS["action"]; geek = True
    if _is_animation(show):
        weight += TV_WEIGHTS["animation"]; geek = True
    if _is_comic_hero(get_show_title(show)):
        weight += TV_WEIGHTS["comic_hero"]; geek = True
    if geek:
        if _is_western(show):
            weight += TV_WEIGHTS["western"]
        if _is_good_animation(show):
            weight += TV_WEIGHTS["good_anime"]
    else:
        weight = TV_WEIGHTS["other"]
    return pop * weight


def _movie_anticipation(movie: dict) -> float:
    """Effective anticipation for a movie. Same idea as TV but softer, and any
    anticipated animated movie counts as preferred."""
    pop = movie.get("popularity", 0.0) or 0.0
    weight, preferred = 1.0, False
    if _is_western_movie(movie):
        weight += MOVIE_WEIGHTS["western"]; preferred = True
    if _is_animation(movie):
        weight += MOVIE_WEIGHTS["animation"]; preferred = True
    if _is_comic_hero(get_movie_title(movie)):
        weight += MOVIE_WEIGHTS["comic_hero"]; preferred = True
    if _is_scifi_fantasy(movie, is_tv=False):
        weight += MOVIE_WEIGHTS["fantasy"]; preferred = True
    if not preferred:
        weight = MOVIE_WEIGHTS["other"]
    return pop * weight


def _select_balanced(items: list[dict], score, limit: int, caps) -> list[dict]:
    """Rank by `score`, enforcing per-category maximums so no single kind of
    content dominates a carousel. `caps` is a list of (predicate, max_count):
    an item is placed only if every category it belongs to still has room.
    Over-cap items backfill any unused slots in score order.
    """
    ranked = sorted(items, key=score, reverse=True)
    counts = [0] * len(caps)
    out, deferred = [], []
    for it in ranked:
        if len(out) >= limit:
            break
        if any(pred(it) and counts[i] >= mx for i, (pred, mx) in enumerate(caps)):
            deferred.append(it)
            continue
        out.append(it)
        for i, (pred, mx) in enumerate(caps):
            if pred(it):
                counts[i] += 1
    for it in deferred:  # backfill only if caps left the carousel short
        if len(out) >= limit:
            break
        out.append(it)
    return sorted(out, key=score, reverse=True)[:limit]


def _tv_caps(limit: int):
    return [
        (lambda x: not _is_western(x), max(1, round(limit * MAX_NONWESTERN_SHARE))),
        (lambda x: _is_comic_hero(get_show_title(x)), max(1, round(limit * COMIC_MAX_SHARE))),
    ]


def fetch_anticipated_shows(target: date = None, limit: int = 10) -> list[dict]:
    """
    Fetch TV shows premiering this month that are available in the US, then
    rank by weighted anticipation (_tv_anticipation): American / European,
    good anime, and comic/superhero content — especially animated superhero
    shows — are boosted. Non-Western titles are capped (MAX_NONWESTERN_SHARE)
    so the list stays mostly American / European instead of all anime.
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

    results = [s for s in results if s.get("poster_path")]
    return _select_balanced(results, _tv_anticipation, limit, _tv_caps(limit))


def fetch_popular_shows_last_month(target: date = None, limit: int = 3) -> list[dict]:
    """
    Most popular shows from last month, American / European first to match the
    top 10 ranking. Requires a poster and a real vote count so obscure,
    barely-rated entries don't sneak onto the slide.
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

    results = [s for s in results
               if s.get("poster_path") and (s.get("vote_count", 0) or 0) >= POPULAR_MIN_VOTES]
    caps = [(lambda x: not _is_western(x), max(1, round(limit * MAX_NONWESTERN_SHARE)))]
    return _select_balanced(results, _tv_anticipation, limit, caps)


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