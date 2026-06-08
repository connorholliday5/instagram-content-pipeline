"""Pure stage functions for the Monthly Games carousel."""
from datetime import date


def _build_caption(pick_titles: list, today: date) -> str:
    from src.caption.groq_caption import generate_caption
    pick_str = ", ".join(pick_titles) if pick_titles else "this month's top releases"
    month_str = today.strftime("%B %Y")
    raw_caption = generate_caption(
        title=f"Games This Month - {month_str}",
        category="games",
        description=(
            f"Top 10 video game releases in {month_str} across PC, PlayStation, Xbox, and Switch. "
            f"Picks: {pick_str}. "
            f"No plot descriptions. No made-up details. "
            f"End with a question asking what they're playing this month."
        ),
        release_date=month_str,
    )
    hashtags = (
        "#Gaming #VideoGames #Gamer #Games #GamingCommunity"
    )
    return f"{raw_caption}\n\n{hashtags}"


def stage_fetch(today_iso: str) -> dict:
    from src.ingest.rawg import (
        fetch_anticipated_games,
        get_game_title, get_game_poster_url, get_game_release_date,
        get_game_platforms,
    )
    from src.ingest.steam import (
        fetch_most_played, get_steam_title, get_steam_players, format_players,
    )
    from src.db.models import init_db
    init_db()

    top_games = fetch_anticipated_games(limit=10)
    most_played = fetch_most_played(limit=3)

    items_view = []
    for i, g in enumerate(top_games):
        platforms = get_game_platforms(g)
        rel = get_game_release_date(g)
        subtitle = f"{rel} - {platforms}" if platforms else rel
        items_view.append({
            "index": i,
            "title": get_game_title(g),
            "subtitle": subtitle,
            "image_url": get_game_poster_url(g),
        })

    bonus_items = []
    for g in most_played:
        bonus_items.append({
            "title": get_steam_title(g),
            "subtitle": f"{format_players(get_steam_players(g))} players",
        })

    return {
        "today": today_iso,
        "top_games_raw": top_games,
        "most_played_raw": most_played,
        "items_view": items_view,
        "bonus_items": bonus_items,
    }


def stage_build(data: dict) -> dict:
    from src.ingest.rawg import get_game_title, get_game_poster_url
    from src.ingest.steam import (
        get_steam_title, get_steam_poster_url, get_steam_players, format_players,
    )
    from src.generate.games_carousel import (
        build_games_cover, build_games_top10,
        build_games_picks, build_games_most_played,
    )

    today = date.fromisoformat(data["today"])
    top_games = data["top_games_raw"]
    most_played = data.get("most_played_raw", [])
    picks_indices = data.get("picks", []) or []

    pick_games, pick_titles = [], []
    for idx in picks_indices:
        if 0 <= idx < len(top_games):
            pick_games.append(top_games[idx])
            pick_titles.append(get_game_title(top_games[idx]))

    slides = []
    slides.append(str(build_games_cover(today)))
    slides.append(str(build_games_top10(top_games, today, get_game_title, get_game_poster_url)))
    slides.append(str(build_games_picks(pick_games, today, get_game_title, get_game_poster_url)))
    if most_played:
        slides.append(str(build_games_most_played(
            most_played, today, get_steam_title, get_steam_poster_url,
            get_steam_players, format_players
        )))

    full_caption = _build_caption(pick_titles, today)
    return {"slides": slides, "caption": full_caption, "pick_titles": pick_titles}


def stage_regenerate_caption(data: dict) -> dict:
    today = date.fromisoformat(data["today"])
    return {"caption": _build_caption(data.get("pick_titles", []), today)}