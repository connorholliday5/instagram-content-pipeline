"""Pure stage functions for the Monthly TV carousel."""
from datetime import date


def _build_caption(pick_titles: list, today: date) -> str:
    from src.caption.groq_caption import generate_caption
    pick_str = ", ".join(pick_titles) if pick_titles else "this month's top shows"
    month_str = today.strftime("%B %Y")
    raw_caption = generate_caption(
        title=f"TV Shows This Month - {month_str}",
        category="tv",
        description=(
            f"Top 10 most anticipated TV shows premiering in {month_str}. "
            f"Picks: {pick_str}. "
            f"No plot descriptions. No made-up details. "
            f"End with a question asking what they're watching this month."
        ),
        release_date=month_str,
    )
    hashtags = (
        "#TVShows #NewOnTV #TheWatchtower #Television #StreamingNow "
        "#WhatToWatch #TVRecommendations #BingWorthy #NewSeries "
        "#StreamingTV #MustWatch #TVCommunity #NewEpisodes #TVTime"
    )
    return f"{raw_caption}\n\n{hashtags}"


def stage_fetch(today_iso: str) -> dict:
    from src.ingest.tmdb import (
        fetch_anticipated_shows, fetch_popular_shows_last_month,
        get_show_title, get_show_poster_url, get_show_premiere_date,
        get_show_network,
    )
    from src.db.models import init_db
    init_db()

    top_shows = fetch_anticipated_shows(limit=10)
    popular = fetch_popular_shows_last_month(limit=3)

    items_view = []
    for i, s in enumerate(top_shows):
        items_view.append({
            "index": i,
            "title": get_show_title(s),
            "subtitle": f"{get_show_premiere_date(s)} • {get_show_network(s)}",
            "image_url": get_show_poster_url(s),
        })

    bonus_items = []
    for s in popular:
        bonus_items.append({
            "title": get_show_title(s),
            "subtitle": get_show_network(s),
        })

    return {
        "today": today_iso,
        "top_shows_raw": top_shows,
        "popular_raw": popular,
        "items_view": items_view,
        "bonus_items": bonus_items,
    }


def stage_build(data: dict) -> dict:
    from src.ingest.tmdb import (
        get_show_title, get_show_poster_url, get_show_network,
        get_show_vote_average, get_show_vote_count, format_vote_count,
    )
    from src.generate.tv_carousel import (
        build_tv_cover, build_tv_top10,
        build_tv_picks, build_tv_popular,
    )

    today = date.fromisoformat(data["today"])
    top_shows = data["top_shows_raw"]
    popular = data.get("popular_raw", [])
    picks_indices = data.get("picks", []) or []

    pick_shows, pick_titles = [], []
    for idx in picks_indices:
        if 0 <= idx < len(top_shows):
            pick_shows.append(top_shows[idx])
            pick_titles.append(get_show_title(top_shows[idx]))

    slides = []
    slides.append(str(build_tv_cover(today)))
    slides.append(str(build_tv_top10(top_shows, today, get_show_title, get_show_poster_url)))
    slides.append(str(build_tv_picks(pick_shows, today, get_show_title, get_show_poster_url)))
    if popular:
        slides.append(str(build_tv_popular(
            popular, today, get_show_title, get_show_poster_url, get_show_network,
            get_show_vote_average, get_show_vote_count, format_vote_count
        )))

    full_caption = _build_caption(pick_titles, today)
    return {"slides": slides, "caption": full_caption, "pick_titles": pick_titles}


def stage_regenerate_caption(data: dict) -> dict:
    today = date.fromisoformat(data["today"])
    return {"caption": _build_caption(data.get("pick_titles", []), today)}
