import os
import subprocess
import tempfile
import sqlite3
import requests
from pathlib import Path
from datetime import date
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from dotenv import load_dotenv

load_dotenv()
console = Console()

DB_PATH = Path("watchtower.db")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


# ── DB ────────────────────────────────────────────────────────────────────────

def init_books_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books_read (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            rating REAL NOT NULL,
            date_reviewed TEXT NOT NULL,
            cover_url TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_book(title: str, author: str, rating: float,
              cover_url: str = "", review_date: date = None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO books_read (title, author, rating, date_reviewed, cover_url) "
        "VALUES (?, ?, ?, ?, ?)",
        (title, author, rating,
         (review_date or date.today()).isoformat(), cover_url)
    )
    conn.commit()
    conn.close()


def get_books_2026() -> list[dict]:
    """Get all books with date_reviewed containing '2026'."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT title, author, rating, date_reviewed FROM books_read "
        "WHERE date_reviewed LIKE '%2026%' ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return [{"title": r[0], "author": r[1], "rating": r[2],
             "date_reviewed": r[3]} for r in rows]


def get_all_books() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT title, author, rating, date_reviewed FROM books_read "
        "ORDER BY date_reviewed DESC"
    ).fetchall()
    conn.close()
    return [{"title": r[0], "author": r[1], "rating": r[2],
             "date_reviewed": r[3]} for r in rows]


# ── Cover art ─────────────────────────────────────────────────────────────────

def fetch_book_cover(title: str, author: str) -> str | None:
    query = (title + " " + author).replace(" ", "+")
    try:
        resp = requests.get(
            f"https://openlibrary.org/search.json?q={query}&limit=3",
            timeout=10
        )
        resp.raise_for_status()
        docs = resp.json().get("docs", [])
        for doc in docs:
            if doc.get("cover_i"):
                return f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-L.jpg"
    except Exception:
        pass
    return None


# ── AI review ────────────────────────────────────────────────────────────────

def draft_review_with_groq(title: str, author: str, rating: float,
                            bullet_notes: str) -> str:
    """Use Groq to draft a review from bullet point notes."""
    system = """You are writing a short book review for @the.watch_tower Instagram account.
Tone: genuine, confident, 24+ audience. Not corny. Sounds like a real reader, not a critic.
Rules:
- 3-5 sentences max
- Use the reader's own bullet point notes as the basis — don't invent anything
- Do not describe plot — the reader already knows it
- Match the energy of the rating (5 = excited, 3 = mixed, etc.)
- No em dashes. No clichés. Sound human."""

    user = f"""Book: {title} by {author}
Rating: {rating}/5
Reader's notes: {bullet_notes}

Write a short Instagram review caption based ONLY on these notes. First person."""

    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                     "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": 300,
                "temperature": 0.8,
            },
            timeout=15
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Review draft failed: {e}"


def open_editor_with_content(content: str) -> str:
    """Open Notepad with pre-filled content for editing."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        tmp_path = f.name
    subprocess.run(["notepad.exe", tmp_path], check=True)
    with open(tmp_path, "r", encoding="utf-8") as f:
        result = f.read().strip()
    os.unlink(tmp_path)
    lines = [l for l in result.splitlines() if not l.startswith("#")]
    return "\n".join(lines).strip()


# ── Render stars ──────────────────────────────────────────────────────────────

def _render_stars(rating: float) -> str:
    full = int(rating)
    half = 1 if (rating - full) >= 0.5 else 0
    empty = 5 - full - half
    return "★" * full + "½" * half + "☆" * empty


# ── Main CLI ─────────────────────────────────────────────────────────────────

def run_review():
    from src.generate.book_review import (
        build_book_cover,
        build_book_review,
        build_books_read,
        build_next_read,
    )

    init_books_db()
    console.rule("[bold red]TheWatchtower_ — Book Review Creator[/bold red]")

    # ── Book details ──
    title  = Prompt.ask("[bold]Book title[/bold]")
    author = Prompt.ask("[bold]Author[/bold]")

    # Rating
    console.print("\n[bold yellow]Rating: 0 to 5 in 0.5 steps[/bold yellow]")
    console.print("[dim]e.g. 0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5[/dim]")
    while True:
        rating_str = Prompt.ask("Your rating").strip()
        try:
            rating = float(rating_str)
            if rating in [r/2 for r in range(0, 11)]:
                break
            console.print("[red]Must be between 0 and 5 in 0.5 increments[/red]")
        except ValueError:
            console.print("[red]Enter a number like 3.5 or 4[/red]")

    # ── Cover art ──
    console.log("\nSearching for cover art...")
    cover_url = fetch_book_cover(title, author)
    if cover_url:
        console.log("[green]✓ Cover found[/green]")
    else:
        console.log("[yellow]⚠ No cover found[/yellow]")
        cover_url = Prompt.ask("Cover image URL (or leave blank)", default="").strip() or None

    # ── Bullet point thoughts ──
    console.print("\n[bold yellow]Give me a few bullet points about your thoughts.[/bold yellow]")
    console.print("[dim]e.g. loved the atmosphere, slow start, best ending ever, great character work[/dim]")
    console.print("[dim]Separate with commas or write as a sentence — Groq will draft from these[/dim]")
    bullet_notes = Prompt.ask("Your thoughts").strip()

    # ── AI drafts review ──
    console.log("\n[bold]Groq drafting your review...[/bold]")
    draft = draft_review_with_groq(title, author, rating, bullet_notes)
    console.print(Panel(draft, title="[bold yellow]Groq Draft[/bold yellow]", border_style="yellow"))

    # ── Edit in Notepad ──
    action = Prompt.ask(
        "Review",
        choices=["approve", "edit"],
        default="approve"
    )
    if action == "edit":
        review_text = open_editor_with_content(
            f"# Edit your review below. Delete this line.\n\n{draft}"
        )
    else:
        review_text = draft

    if not review_text:
        review_text = draft

    # ── Next read ──
    console.rule("[bold]Next Read[/bold]")
    next_title  = Prompt.ask("[bold]Next book title[/bold]")
    next_author = Prompt.ask("[bold]Next book author[/bold]")
    console.log("Searching for next book cover...")
    next_cover = fetch_book_cover(next_title, next_author)
    if next_cover:
        console.log("[green]✓ Cover found[/green]")
    else:
        next_cover = Prompt.ask("Cover URL (or leave blank)", default="").strip() or None

    today = date.today()

    # ── Build slides ──
    console.rule("[bold]Building slides...[/bold]")
    slides = []

    console.log("Slide 1: Cover...")
    s1 = build_book_cover(title, author, cover_url, today)
    slides.append(str(s1))
    console.log(f"[green]✓[/green] {s1}")

    console.log("Slide 2: Review...")
    s2 = build_book_review(title, author, rating, cover_url, review_text, today)
    slides.append(str(s2))
    console.log(f"[green]✓[/green] {s2}")

    console.log("Slide 3: 2026 reading list...")
    books_so_far = get_books_2026()
    current = {"title": title, "author": author, "rating": rating,
               "date_reviewed": "2026"}
    # Put current book first, then rest of 2026 list
    all_books = [current] + [b for b in books_so_far if b["title"] != title]
    s3 = build_books_read(all_books, today)
    slides.append(str(s3))
    console.log(f"[green]✓[/green] {s3}")

    console.log("Slide 4: Next read...")
    s4 = build_next_read(next_title, next_author, next_cover, today)
    slides.append(str(s4))
    console.log(f"[green]✓[/green] {s4}")

    # ── Review slides ──
    console.rule("[bold yellow]Review Slides[/bold yellow]")
    for i, slide_path in enumerate(slides):
        console.print(f"[bold cyan]Slide {i+1}/{len(slides)}:[/bold cyan] {slide_path}")
        subprocess.Popen(["explorer", slide_path.replace("/", "\\")])
        input("  Press Enter for next slide...")

    # ── Caption ──
    console.rule("[bold]Caption[/bold]")
    stars_str = _render_stars(rating)
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

    hashtags = (
        "#BookReview #TheWatchtower #Reading #BookNerd "
        "#Bookstagram #BookCommunity #WhatImReading "
        "#BookRecommendation #ReadingList #Books2026"
    )
    full_caption = f"{raw_caption}\n\n{stars_str} {rating}/5\n\n{hashtags}"
    console.print(Panel(full_caption, title="[bold]Caption Preview[/bold]", border_style="cyan"))

    cap_action = Prompt.ask("Caption", choices=["approve", "edit"], default="approve")
    if cap_action == "edit":
        full_caption = open_editor_with_content(full_caption)

    # ── Save to DB ──
    save = Prompt.ask(
        "\n[bold green]Save to 2026 reading list?[/bold green]",
        choices=["yes", "no"], default="yes"
    )
    if save == "yes":
        save_book(title, author, rating, cover_url or "", today)
        console.log("[green]✓ Saved to reading list[/green]")

    console.print(f"\n[bold green]✓ {len(slides)} slides ready in output\\ folder.[/bold green]")
    console.print("[dim]Post manually to Instagram as a carousel.[/dim]")
    console.rule("[bold red]Done[/bold red]")