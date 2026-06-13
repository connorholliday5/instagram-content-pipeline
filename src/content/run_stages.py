"""Pure stage functions for the Weekly Comics carousel."""
from datetime import date


def _build_caption(top_count: int, pick_titles: list, collector_items: list, street_date: date) -> str:
    from src.caption.groq_caption import generate_caption
    pick_str = ", ".join(pick_titles) if pick_titles else "this week's top releases"
    collector_str = ", ".join([f"{c['title']} ({c['reason']})" for c in collector_items]) if collector_items else ""
    raw_caption = generate_caption(
        title="New Comic Book Day",
        category="comics",
        description=(
            f"Keep it under 3 sentences. No made-up creative team details. "
            f"This is a preview posted ahead of time - {top_count} new comics drop "
            f"this Wednesday. Frame it as a heads up so readers can plan their pull list. "
            f"Connor's picks: {pick_str}. "
            f"{'Collector highlights: ' + collector_str if collector_str else ''} "
            f"End with a short question asking what's on their pull list this week."
        ),
        release_date=street_date.strftime("%B %d, %Y"),
    )
    hashtags = "#Comics #Marvel #DCComics #ComicBooks #NCBD"
    return f"{raw_caption}\n\n{hashtags}"


def stage_fetch(today_iso: str) -> dict:
    """Fetch top 10 issues + collector items. No picks yet."""
    from src.ingest.comicvine import (
        fetch_top_weekly_issues, fetch_variants_and_collectors,
        get_cover_url, get_publisher, get_title, get_store_date,
    )
    from src.db.models import init_db

    init_db()
    top_issues = fetch_top_weekly_issues(limit=10)
    collector_items = fetch_variants_and_collectors(limit=4)

    items_view = []
    for i, issue in enumerate(top_issues):
        items_view.append({
            "index": i,
            "title": get_title(issue),
            "subtitle": get_publisher(issue),
            "image_url": get_cover_url(issue),
            "store_date": get_store_date(issue),
        })

    bonus_items = [{"title": c["title"], "subtitle": c["reason"]} for c in collector_items]

    return {
        "today": today_iso,
        "top_issues_raw": top_issues,
        "items_view": items_view,
        "collector_items": collector_items,
        "bonus_items": bonus_items,
    }


def stage_build(data: dict) -> dict:
    """Take picks indices + extras, build slides and caption."""
    from src.ingest.comicvine import (
        search_issue, _upcoming_wednesday,
        get_cover_url, get_publisher, get_title,
    )
    from src.generate.comics_carousel import (
        build_cover_slide, build_top10_slide,
        build_picks_slide, build_collectors_slide,
    )

    today = date.fromisoformat(data["today"])
    # Posted Monday, about Wednesday's drop. All on-slide dates and the caption
    # should read as the Wednesday street date, not the day the job runs.
    street_date = _upcoming_wednesday(today)
    top_issues = data["top_issues_raw"]
    collector_items = data["collector_items"]
    picks_indices = data.get("picks", []) or []
    picks_extra = data.get("picks_extra", []) or []

    pick_issues, pick_titles = [], []
    for idx in picks_indices:
        if 0 <= idx < len(top_issues):
            pick_issues.append(top_issues[idx])
            pick_titles.append(get_title(top_issues[idx]))
    for s in picks_extra:
        s = (s or "").strip()
        if not s:
            continue
        issue = search_issue(s)
        if issue:
            pick_issues.append(issue)
            pick_titles.append(get_title(issue))
        else:
            pick_issues.append({"issue": s, "image": None, "publisher": {}, "series": {}})
            pick_titles.append(s)

    slides = []
    slides.append(str(build_cover_slide(street_date)))
    slides.append(str(build_top10_slide(
        top_issues, street_date, get_title, get_cover_url, get_publisher)))
    slides.append(str(build_picks_slide(
        pick_issues, street_date, get_title, get_cover_url, get_publisher)))
    if collector_items:
        slides.append(str(build_collectors_slide(collector_items, street_date)))

    full_caption = _build_caption(len(top_issues), pick_titles, collector_items, street_date)

    return {
        "slides": slides,
        "caption": full_caption,
        "pick_titles": pick_titles,
    }


def stage_regenerate_caption(data: dict) -> dict:
    from src.ingest.comicvine import _upcoming_wednesday
    today = date.fromisoformat(data["today"])
    street_date = _upcoming_wednesday(today)
    pick_titles = data.get("pick_titles", [])
    collector_items = data.get("collector_items", [])
    top_count = len(data.get("top_issues_raw", []))
    return {"caption": _build_caption(top_count, pick_titles, collector_items, street_date)}