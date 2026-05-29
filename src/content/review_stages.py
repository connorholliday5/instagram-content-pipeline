"""Pure stage functions for the book review pipeline."""
from datetime import date


def _build_hashtags() -> str:
    return (
        "#BookReview #TheWatchtower #Reading #BookNerd "
        "#Bookstagram #BookCommunity #WhatImReading "
        "#BookRecommendation #ReadingList #Books2026"
    )


def _render_stars(rating: float) -> str:
    full = int(rating)
    half = 1 if (rating - full) >= 0.5 else 0
    empty = 5 - full - half
    return "*" * full + "1/2" * half + "o" * empty


def _build_caption(title: str, author: str, rating: float, review_text: str, today: date) -> str:
    from src.caption.groq_caption import generate_caption
    raw_caption = generate_caption(
        title=f"Book Review: {title}",
        category="books",
        description=(
            f"Book review of {title} by {author}. "
            f"Rating: {rating}/5. Review: {review_text[:200]}. "
            f"No made-up details. End with a question."
        ),
        release_date=today.strftime("%B %d, %Y"),
    )
    stars = _render_stars(rating)
    return f"{raw_caption}\n\n{stars} {rating}/5\n\n{_build_hashtags()}"


def stage_draft(data: dict) -> dict:
    """Initial payload should contain: title, author, rating, bullet_notes, next_title, next_author.
    Optionally cover_url, next_cover_url (else auto-fetch)."""
    from src.create.review import (
        init_books_db, fetch_book_cover, draft_review_with_groq,
    )

    init_books_db()
    today = date.today().isoformat()

    title  = (data.get("title") or "").strip()
    author = (data.get("author") or "").strip()
    try:
        rating = float(data.get("rating"))
    except (TypeError, ValueError):
        raise ValueError("rating must be a number 0-5 in 0.5 steps")
    bullet_notes = (data.get("bullet_notes") or "").strip()
    next_title = (data.get("next_title") or "").strip()
    next_author = (data.get("next_author") or "").strip()

    if not title or not author:
        raise ValueError("title and author are required")

    cover_url = data.get("cover_url") or fetch_book_cover(title, author) or ""
    next_cover_url = data.get("next_cover_url") or fetch_book_cover(next_title, next_author) or ""

    draft = draft_review_with_groq(title, author, rating, bullet_notes)

    return {
        "today": today,
        "title": title,
        "author": author,
        "rating": rating,
        "bullet_notes": bullet_notes,
        "cover_url": cover_url,
        "next_title": next_title,
        "next_author": next_author,
        "next_cover_url": next_cover_url,
        "review_text": draft,
    }


def stage_build(data: dict) -> dict:
    """Build all 4 slides and the caption."""
    from src.generate.book_review import (
        build_book_cover, build_book_review,
        build_books_read, build_next_read,
    )
    from src.create.review import get_books_2026

    today = date.fromisoformat(data["today"])
    title = data["title"]
    author = data["author"]
    rating = float(data["rating"])
    cover_url = data.get("cover_url") or None
    review_text = data["review_text"]
    next_title = data["next_title"]
    next_author = data["next_author"]
    next_cover_url = data.get("next_cover_url") or None

    slides = []
    slides.append(str(build_book_cover(title, author, cover_url, today)))
    slides.append(str(build_book_review(title, author, rating, cover_url, review_text, today)))

    books_so_far = get_books_2026()
    current = {"title": title, "author": author, "rating": rating, "date_reviewed": "2026"}
    all_books = [current] + [b for b in books_so_far if b["title"] != title]
    slides.append(str(build_books_read(all_books, today)))

    slides.append(str(build_next_read(next_title, next_author, next_cover_url, today)))

    caption = _build_caption(title, author, rating, review_text, today)
    return {"slides": slides, "caption": caption}


def stage_regenerate_caption(data: dict) -> dict:
    today = date.fromisoformat(data["today"])
    return {"caption": _build_caption(
        data["title"], data["author"], float(data["rating"]), data["review_text"], today
    )}


def stage_save(data: dict) -> dict:
    """Persist the book to the 2026 reading list. Returns saved record."""
    from src.create.review import save_book
    today = date.fromisoformat(data["today"])
    save_book(
        data["title"], data["author"], float(data["rating"]),
        data.get("cover_url") or "", today
    )
    return {"saved": True, "saved_at": today.isoformat()}
