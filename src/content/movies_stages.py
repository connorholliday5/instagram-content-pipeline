"""Pure stage functions for the Monthly Movies carousel."""
from datetime import date


def _build_caption(pick_titles: list, today: date) -> str:
    from src.caption.groq_caption import generate_caption
    pick_str = ", ".join(pick_titles) if pick_titles else "this month's top releases"
    month_str = today.strftime("%B %Y")
    raw_caption = generate_caption(
        title=f"Movies This Month - {month_str}",
        category="film",
        description=(
            f"Top 10 most anticipated movies releasing in {month_str}. "
            f"Picks: {pick_str}. "
            f"No plot descriptions. No made-up details. "
            f"End with a question asking what they're watching this month."
        ),
        release_date=month_str,
    )
    hashtags = (
        "#Movies #Film #Cinema #FilmTwitter #MovieReview"
    )
    return f"{raw_caption}\n\n{hashtags}"


def stage_fetch(today_iso: str) -> dict:
    from src.ingest.tmdb import (
        fetch_anticipated_movies, fetch_top_grossing_last_month,
        get_movie_title, get_movie_poster_url, get_movie_release_date,
        get_movie_revenue, format_revenue,
    )
    from src.db.models import init_db
    init_db()

    top_movies = fetch_anticipated_movies(limit=10)
    grossing = fetch_top_grossing_last_month(limit=3)

    items_view = []
    for i, m in enumerate(top_movies):
        items_view.append({
            "index": i,
            "title": get_movie_title(m),
            "subtitle": get_movie_release_date(m),
            "image_url": get_movie_poster_url(m),
        })

    bonus_items = []
    for m in grossing:
        bonus_items.append({
            "title": get_movie_title(m),
            "subtitle": format_revenue(get_movie_revenue(m)),
        })

    return {
        "today": today_iso,
        "top_movies_raw": top_movies,
        "grossing_raw": grossing,
        "items_view": items_view,
        "bonus_items": bonus_items,
    }


def stage_build(data: dict) -> dict:
    from src.ingest.tmdb import (
        get_movie_title, get_movie_poster_url,
        get_movie_revenue, format_revenue,
    )
    from src.generate.movies_carousel import (
        build_movies_cover, build_movies_top10,
        build_movies_picks, build_movies_grossing,
    )

    today = date.fromisoformat(data["today"])
    top_movies = data["top_movies_raw"]
    grossing = data.get("grossing_raw", [])
    picks_indices = data.get("picks", []) or []

    pick_movies, pick_titles = [], []
    for idx in picks_indices:
        if 0 <= idx < len(top_movies):
            pick_movies.append(top_movies[idx])
            pick_titles.append(get_movie_title(top_movies[idx]))

    slides = []
    slides.append(str(build_movies_cover(today)))
    slides.append(str(build_movies_top10(top_movies, today, get_movie_title, get_movie_poster_url)))
    slides.append(str(build_movies_picks(pick_movies, today, get_movie_title, get_movie_poster_url)))
    if grossing:
        slides.append(str(build_movies_grossing(
            grossing, today, get_movie_title, get_movie_poster_url,
            get_movie_revenue, format_revenue
        )))

    full_caption = _build_caption(pick_titles, today)

    return {"slides": slides, "caption": full_caption, "pick_titles": pick_titles}


def stage_regenerate_caption(data: dict) -> dict:
    today = date.fromisoformat(data["today"])
    return {"caption": _build_caption(data.get("pick_titles", []), today)}