import os
import click
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
console = Console()


def run_pipeline(dry_run: bool = True):
    from src.ingest.comicvine import fetch_weekly_issues
    from src.ingest.tmdb import fetch_upcoming_movies, fetch_airing_shows
    from src.generate.image_builder import build_image
    from src.caption.groq_caption import generate_caption
    from src.post.instagram import post_image
    from src.db.models import init_db, Release, Post
    from datetime import datetime

    init_db()
    mode = "[DRY RUN]" if dry_run else "[LIVE]"
    console.rule(f"[bold red]TheWatchtower_ Pipeline {mode}[/bold red]")

    # --- Comics ---
    console.log("Fetching comic releases...")
    issues = fetch_weekly_issues()[:3]
    for issue in issues:
        title = issue.get("name") or issue.get("volume", {}).get("name", "Unknown")
        cover = issue.get("image", {}).get("medium_url")
        desc = issue.get("description") or ""
        date_str = issue.get("store_date", "")

        img_path = build_image(title, "comics", cover_url=cover, label="NEW THIS WEEK")
        caption = generate_caption(title, "comics", desc, date_str)
        console.log(f"  [green]✓[/green] {title}")

        if not dry_run:
            post_image(str(img_path), caption, dry_run=False)
        else:
            console.print(f"    Caption preview: {caption[:100]}...")

    # --- Film ---
    console.log("Fetching upcoming superhero films...")
    movies = fetch_upcoming_movies()[:2]
    for movie in movies:
        title = movie.get("title", "Unknown")
        desc = movie.get("overview", "")
        date_str = movie.get("release_date", "")

        img_path = build_image(title, "film", label="COMING SOON")
        caption = generate_caption(title, "film", desc, date_str)
        console.log(f"  [green]✓[/green] {title}")

        if not dry_run:
            post_image(str(img_path), caption, dry_run=False)

    console.rule("[bold red]Pipeline Complete[/bold red]")


@click.group()
def cli():
    """TheWatchtower_ Instagram pipeline."""
    pass


@cli.command()
@click.option("--live", is_flag=True, default=False, help="Post live to Instagram (default: dry run)")
def run(live):
    """Run the full weekly pipeline."""
    run_pipeline(dry_run=not live)


@cli.command()
def review():
    """Launch the manual book review creator."""
    from src.create.review import run_review
    run_review()


@cli.command()
def schedule():
    """Start the Wednesday scheduler."""
    from src.scheduler.weekly import start_scheduler
    start_scheduler()


@cli.command()
def initdb():
    """Initialize the SQLite database."""
    from src.db.models import init_db
    init_db()
    console.log("[green]Database initialized.[/green]")


if __name__ == "__main__":
    cli()