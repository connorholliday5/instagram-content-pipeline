import os
import subprocess
import click
from datetime import date, datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

load_dotenv()
console = Console()


def _cleanup_output(days: int = 7):
    """Silently delete output files older than N days."""
    output_dir = Path("output")
    if not output_dir.exists():
        return
    cutoff = datetime.now() - timedelta(days=days)
    deleted = 0
    for f in output_dir.rglob("*"):
        if f.is_file():
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    f.unlink()
                    deleted += 1
            except Exception:
                pass
    if deleted:
        console.log(f"[dim]🗑 Cleaned {deleted} output file(s) older than {days} days[/dim]")


def open_image(path: str):
    subprocess.Popen(["explorer", path.replace("/", "\\")])



def run_weekly_carousel(dry_run: bool = True):
    from src.ingest.comicvine import (
        fetch_top_weekly_issues,
        fetch_variants_and_collectors,
        search_issue,
        get_cover_url,
        get_publisher,
        get_title,
        get_store_date,
    )
    from src.generate.carousel import (
        build_cover_slide,
        build_top10_slide,
        build_picks_slide,
        build_collectors_slide,
    )
    from src.caption.groq_caption import generate_caption
    from src.post.carousel_post import post_carousel
    from src.db.models import init_db

    init_db()
    today = date.today()
    mode = "[DRY RUN]" if dry_run else "[LIVE]"
    console.rule(f"[bold red]TheWatchtower_ Weekly Carousel {mode}[/bold red]")

    # ── Fetch releases ──
    console.log("Fetching top 10 new releases this week...")
    top_issues = fetch_top_weekly_issues(limit=10)
    total = len(top_issues)

    if total == 0:
        console.print("[red]No issues found. Try again closer to release day.[/red]")
        return

    console.print(f"\n[bold green]{total} new releases found:[/bold green]\n")
    table = Table(show_header=True, header_style="bold red")
    table.add_column("#", width=4)
    table.add_column("Title")
    table.add_column("Publisher")
    table.add_column("Date")
    for i, issue in enumerate(top_issues):
        table.add_row(str(i+1), get_title(issue), get_publisher(issue), get_store_date(issue))
    console.print(table)

    # ── Combined variants + collector items ──
    console.log("\nScanning for collector items & rare variants...")
    collector_items = fetch_variants_and_collectors(limit=4)
    if collector_items:
        console.print(f"[bold gold1]🔑 {len(collector_items)} item(s) found:[/bold gold1]")
        for c in collector_items:
            console.print(f"  [gold1]•[/gold1] {c['title']} — [bold]{c['reason']}[/bold]")
    else:
        console.print("[dim]No collector items detected.[/dim]")

    # ── Picks ──
    console.print(f"\n[bold yellow]Your picks this week?[/bold yellow]")
    console.print(f"[dim]Enter numbers from the list above (e.g. 1, 3, 7) or leave blank[/dim]")
    picks_input = Prompt.ask("Picks").strip()

    pick_issues, pick_titles = [], []
    if picks_input:
        for part in picks_input.split(","):
            part = part.strip()
            try:
                idx = int(part) - 1
                if 0 <= idx < len(top_issues):
                    pick_issues.append(top_issues[idx])
                    pick_titles.append(get_title(top_issues[idx]))
                else:
                    console.print(f"[yellow]⚠ {part} out of range[/yellow]")
            except ValueError:
                issue = search_issue(part)
                if issue:
                    pick_issues.append(issue)
                    pick_titles.append(get_title(issue))
                else:
                    pick_issues.append({"issue": part, "image": None,
                                        "publisher": {}, "series": {}})
                    pick_titles.append(part)

    # ── Build slides ──
    console.rule("[bold]Building slides...[/bold]")
    slides = []

    console.log("Slide 1: Cover page...")
    slides.append(str(build_cover_slide(today)))
    console.log(f"[green]✓[/green] {slides[-1]}")

    console.log("Slide 2: Top 10...")
    slides.append(str(build_top10_slide(
        top_issues, today, get_title, get_cover_url, get_publisher)))
    console.log(f"[green]✓[/green] {slides[-1]}")

    console.log("Slide 3: Picks...")
    slides.append(str(build_picks_slide(
        pick_issues, today, get_title, get_cover_url, get_publisher)))
    console.log(f"[green]✓[/green] {slides[-1]}")

    if collector_items:
        console.log("Slide 4: Collector's Corner...")
        slides.append(str(build_collectors_slide(collector_items, today)))
        console.log(f"[green]✓[/green] {slides[-1]}")

    # ── Review ──
    console.rule("[bold yellow]Review Slides[/bold yellow]")
    console.print(f"[dim]{len(slides)} slides. Opening each for review...[/dim]\n")
    for i, slide_path in enumerate(slides):
        console.print(f"[bold cyan]Slide {i+1}/{len(slides)}:[/bold cyan] {slide_path}")
        open_image(slide_path)
        input("  Press Enter for next slide...")

    # ── Caption — short, no hallucination ──
    console.rule("[bold]Caption[/bold]")
    pick_str = ", ".join(pick_titles) if pick_titles else "this week's top releases"
    collector_str = ", ".join([f"{c['title']} ({c['reason']})"
                               for c in collector_items]) if collector_items else ""

    raw_caption = generate_caption(
        title="New Comic Book Day",
        category="comics",
        description=(
            f"Keep it under 3 sentences. No made-up creative team details. "
            f"New comic book day — {total} releases this week. "
            f"Connor's picks: {pick_str}. "
            f"{'Collector highlights: ' + collector_str if collector_str else ''} "
            f"End with a short question asking what's on their pull list."
        ),
        release_date=today.strftime("%B %d, %Y"),
    )

    hashtags = (
        "#NewComicBookDay #NCBD #TheWatchtower #DCComics #MarvelComics "
        "#IndieComics #ComicBookCommunity #WeeklyComics #ComicBooks "
        "#NewRelease #ComicBookDay #PullList #ComicBookNerd #LCS #LocalComicShop"
    )
    full_caption = f"{raw_caption}\n\n{hashtags}"
    console.print(Panel(full_caption, title="[bold]Caption Preview[/bold]", border_style="cyan"))

    action = Prompt.ask("Caption", choices=["approve", "edit"], default="approve")
    if action == "edit":
        full_caption = Prompt.ask("Enter new caption")

    # ── Post ──
    today_str = today.strftime("%A, %B %d")
    confirm = Prompt.ask(
        f"\n[bold red]Post {len(slides)} slides? (Scheduled: Wednesday)[/bold red]",
        choices=["yes", "no"], default="no"
    )

    if confirm != "yes":
        console.print("[yellow]Cancelled.[/yellow]")
        console.rule("[bold red]Done[/bold red]")
        return

    if today.weekday() != 2:
        override = Prompt.ask(
            f"[yellow]Today is {today_str}, not Wednesday. Post anyway?[/yellow]",
            choices=["yes", "no"], default="no"
        )
        if override != "yes":
            console.print("[yellow]Cancelled.[/yellow]")
            console.rule("[bold red]Done[/bold red]")
            return

    result = post_carousel(slides, full_caption, dry_run=dry_run)
    if dry_run:
        console.print("[yellow]DRY RUN — nothing posted.[/yellow]")
    else:
        console.log(f"[bold green]✓ Posted! Media ID: {result.get('media_id')}[/bold green]")

    console.rule("[bold red]Done[/bold red]")


@click.group()
def cli():
    """TheWatchtower_ Instagram pipeline."""
    _cleanup_output(days=7)


@cli.command()
@click.option("--live", is_flag=True, default=False)
def run(live):
    """Run the weekly comics carousel pipeline."""
    run_weekly_carousel(dry_run=not live)


@cli.command()
def review():
    """Launch the manual book review creator."""
    from src.create.review import run_review
    run_review()


@cli.command()
def schedule():
    """Start the Tuesday scheduler."""
    from src.scheduler.weekly import start_scheduler
    start_scheduler()


@cli.command()
def initdb():
    """Initialize the SQLite database."""
    from src.db.models import init_db
    init_db()
    console.log("[green]Database initialized.[/green]")




@cli.command()
@click.option("--live", is_flag=True, default=False)
def movies(live):
    """Run the monthly movies carousel pipeline."""
    from src.ingest.tmdb import (
        fetch_anticipated_movies,
        fetch_top_grossing_last_month,
        get_movie_title,
        get_movie_poster_url,
        get_movie_release_date,
        get_movie_revenue,
        format_revenue,
    )
    from src.generate.movies_carousel import (
        build_movies_cover,
        build_movies_top10,
        build_movies_picks,
        build_movies_grossing,
    )
    from src.caption.groq_caption import generate_caption
    from src.db.models import init_db

    init_db()
    today = date.today()
    mode = "[DRY RUN]" if not live else "[LIVE]"
    console.rule(f"[bold red]TheWatchtower_ Monthly Movies {mode}[/bold red]")

    console.log("Fetching top 10 most anticipated movies this month...")
    top_movies = fetch_anticipated_movies(limit=10)

    if not top_movies:
        console.print("[red]No movies found for this month.[/red]")
        return

    console.print(f"\n[bold green]{len(top_movies)} movies found:[/bold green]\n")
    table = Table(show_header=True, header_style="bold red")
    table.add_column("#", width=4)
    table.add_column("Title")
    table.add_column("Release Date")
    from rich.table import Table as RTable
    table = RTable(show_header=True, header_style="bold red")
    table.add_column("#", width=4)
    table.add_column("Title")
    table.add_column("Release Date")
    for i, movie in enumerate(top_movies):
        table.add_row(str(i+1), get_movie_title(movie), get_movie_release_date(movie))
    console.print(table)

    console.log("\nFetching highest grossing movies from last month...")
    grossing = fetch_top_grossing_last_month(limit=3)
    if grossing:
        console.print(f"[bold gold1]💰 Top {len(grossing)} grossing last month:[/bold gold1]")
        for m in grossing:
            console.print(f"  [gold1]•[/gold1] {get_movie_title(m)} — {format_revenue(get_movie_revenue(m))}")

    console.print(f"\n[bold yellow]Your picks this month?[/bold yellow]")
    console.print(f"[dim]Enter numbers from the list (e.g. 1, 3, 5) or leave blank[/dim]")
    picks_input = Prompt.ask("Picks").strip()

    pick_movies = []
    pick_titles = []
    if picks_input:
        for part in picks_input.split(","):
            part = part.strip()
            try:
                idx = int(part) - 1
                if 0 <= idx < len(top_movies):
                    pick_movies.append(top_movies[idx])
                    pick_titles.append(get_movie_title(top_movies[idx]))
                else:
                    console.print(f"[yellow]⚠ {part} out of range[/yellow]")
            except ValueError:
                console.print(f"[yellow]⚠ Could not parse {part}[/yellow]")

    console.rule("[bold]Building slides...[/bold]")
    slides = []

    console.log("Slide 1: Cover...")
    slides.append(str(build_movies_cover(today)))
    console.log(f"[green]✓[/green] {slides[-1]}")

    console.log("Slide 2: Top 10 anticipated...")
    slides.append(str(build_movies_top10(top_movies, today, get_movie_title, get_movie_poster_url)))
    console.log(f"[green]✓[/green] {slides[-1]}")

    console.log("Slide 3: Picks...")
    slides.append(str(build_movies_picks(pick_movies, today, get_movie_title, get_movie_poster_url)))
    console.log(f"[green]✓[/green] {slides[-1]}")

    if grossing:
        console.log("Slide 4: Highest grossing last month...")
        slides.append(str(build_movies_grossing(
            grossing, today, get_movie_title, get_movie_poster_url,
            get_movie_revenue, format_revenue
        )))
        console.log(f"[green]✓[/green] {slides[-1]}")

    console.rule("[bold yellow]Review Slides[/bold yellow]")
    for i, slide_path in enumerate(slides):
        console.print(f"[bold cyan]Slide {i+1}/{len(slides)}:[/bold cyan] {slide_path}")
        open_image(slide_path)
        input("  Press Enter for next slide...")

    console.rule("[bold]Caption[/bold]")
    pick_str = ", ".join(pick_titles) if pick_titles else "this month's top releases"
    month_str = today.strftime("%B %Y")

    raw_caption = generate_caption(
        title=f"Movies This Month — {month_str}",
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
        "#MovieMonth #NewMovies #TheWatchtower #FilmTwitter #MovieLovers "
        "#NowPlaying #ComingSoon #FilmCommunity #MovieNight #Cinema "
        "#MovieRecommendations #WatchList #FilmFan #Movies2026"
    )
    full_caption = f"{raw_caption}\n\n{hashtags}"
    console.print(Panel(full_caption, title="[bold]Caption Preview[/bold]", border_style="cyan"))

    action = Prompt.ask("Caption", choices=["approve", "edit"], default="approve")
    if action == "edit":
        full_caption = Prompt.ask("Enter new caption")

    console.print(f"\n[bold green]✓ {len(slides)} slides ready.[/bold green]")
    console.print("[dim]Post manually to Instagram as a carousel.[/dim]")
    console.rule("[bold red]Done[/bold red]")



@cli.command()
@click.option("--live", is_flag=True, default=False)
def tv(live):
    """Run the monthly TV shows carousel pipeline."""
    from src.ingest.tmdb import (
        fetch_anticipated_shows,
        fetch_popular_shows_last_month,
        get_show_title,
        get_show_poster_url,
        get_show_premiere_date,
        get_show_network,
        get_show_vote_average,
        get_show_vote_count,
        format_vote_count,
    )
    from src.generate.tv_carousel import (
        build_tv_cover,
        build_tv_top10,
        build_tv_picks,
        build_tv_popular,
    )
    from src.caption.groq_caption import generate_caption
    from src.db.models import init_db

    init_db()
    today = date.today()
    mode = "[DRY RUN]" if not live else "[LIVE]"
    console.rule(f"[bold red]TheWatchtower_ Monthly TV {mode}[/bold red]")

    console.log("Fetching top 10 TV shows premiering this month...")
    top_shows = fetch_anticipated_shows(limit=10)

    if not top_shows:
        console.print("[red]No shows found for this month.[/red]")
        return

    console.print(f"\n[bold green]{len(top_shows)} shows found:[/bold green]\n")
    from rich.table import Table as RTable
    table = RTable(show_header=True, header_style="bold red")
    table.add_column("#", width=4)
    table.add_column("Title")
    table.add_column("Premiere Date")
    table.add_column("Network")
    for i, show in enumerate(top_shows):
        table.add_row(str(i+1), get_show_title(show),
                      get_show_premiere_date(show), get_show_network(show))
    console.print(table)

    console.log("\nFetching most popular shows from last month...")
    popular = fetch_popular_shows_last_month(limit=3)
    if popular:
        console.print(f"[bold cyan]📺 Top {len(popular)} most popular last month:[/bold cyan]")
        for s in popular:
            console.print(f"  [cyan]•[/cyan] {get_show_title(s)} ({get_show_network(s)})")

    console.print(f"\n[bold yellow]Your picks this month?[/bold yellow]")
    console.print(f"[dim]Enter numbers from the list (e.g. 1, 3, 5) or leave blank[/dim]")
    picks_input = Prompt.ask("Picks").strip()

    pick_shows = []
    pick_titles = []
    if picks_input:
        for part in picks_input.split(","):
            part = part.strip()
            try:
                idx = int(part) - 1
                if 0 <= idx < len(top_shows):
                    pick_shows.append(top_shows[idx])
                    pick_titles.append(get_show_title(top_shows[idx]))
                else:
                    console.print(f"[yellow]⚠ {part} out of range[/yellow]")
            except ValueError:
                console.print(f"[yellow]⚠ Could not parse {part}[/yellow]")

    console.rule("[bold]Building slides...[/bold]")
    slides = []

    console.log("Slide 1: Cover...")
    slides.append(str(build_tv_cover(today)))
    console.log(f"[green]✓[/green] {slides[-1]}")

    console.log("Slide 2: Top 10 shows...")
    slides.append(str(build_tv_top10(top_shows, today, get_show_title, get_show_poster_url)))
    console.log(f"[green]✓[/green] {slides[-1]}")

    console.log("Slide 3: Picks...")
    slides.append(str(build_tv_picks(pick_shows, today, get_show_title, get_show_poster_url)))
    console.log(f"[green]✓[/green] {slides[-1]}")

    if popular:
        console.log("Slide 4: Most popular last month...")
        slides.append(str(build_tv_popular(
            popular, today, get_show_title, get_show_poster_url, get_show_network,
            get_show_vote_average, get_show_vote_count, format_vote_count
        )))
        console.log(f"[green]✓[/green] {slides[-1]}")

    console.rule("[bold yellow]Review Slides[/bold yellow]")
    for i, slide_path in enumerate(slides):
        console.print(f"[bold cyan]Slide {i+1}/{len(slides)}:[/bold cyan] {slide_path}")
        open_image(slide_path)
        input("  Press Enter for next slide...")

    console.rule("[bold]Caption[/bold]")
    pick_str = ", ".join(pick_titles) if pick_titles else "this month's top shows"
    month_str = today.strftime("%B %Y")

    raw_caption = generate_caption(
        title=f"TV Shows This Month — {month_str}",
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
    full_caption = f"{raw_caption}\n\n{hashtags}"
    console.print(Panel(full_caption, title="[bold]Caption Preview[/bold]", border_style="cyan"))

    action = Prompt.ask("Caption", choices=["approve", "edit"], default="approve")
    if action == "edit":
        full_caption = Prompt.ask("Enter new caption")

    console.print(f"\n[bold green]✓ {len(slides)} slides ready.[/bold green]")
    console.print("[dim]Post manually to Instagram as a carousel.[/dim]")
    console.rule("[bold red]Done[/bold red]")



@cli.command()
def poll():
    """Generate a daily story poll."""
    from src.generate.poll import generate_poll_question, build_poll_story
    from rich.table import Table as RTable

    today = date.today()
    console.rule("[bold red]TheWatchtower_ — Daily Story Poll[/bold red]")

    while True:
        console.log("Groq generating poll question...")
        poll_data = generate_poll_question()

        console.print(f"\n[bold yellow]Category:[/bold yellow] {poll_data['category']}")
        console.print(f"[bold white]Question:[/bold white] {poll_data['question']}")
        console.print(f"  [bold yellow]A:[/bold yellow] {poll_data['option_a']}")
        console.print(f"  [bold cyan]B:[/bold cyan] {poll_data['option_b']}")

        action = Prompt.ask(
            "\nPoll",
            choices=["approve", "regenerate", "edit"],
            default="approve"
        )

        if action == "regenerate":
            continue
        elif action == "edit":
            poll_data["question"] = Prompt.ask("Question").strip()
            poll_data["option_a"] = Prompt.ask("Option A").strip()
            poll_data["option_b"] = Prompt.ask("Option B").strip()

        console.log("Building story slide...")
        slide_path = build_poll_story(poll_data, today)
        console.log(f"[green]✓[/green] {slide_path}")

        import subprocess
        subprocess.Popen(["explorer", str(slide_path).replace("/", "\\")])

        console.print(f"\n[bold green]✓ Poll ready: {slide_path}[/bold green]")
        console.print("[dim]Post to Instagram Story manually.[/dim]")
        console.rule("[bold red]Done[/bold red]")
        break



@cli.command()
def ideate():
    """Generate the weekly content plan."""
    from src.content.ideate import run_ideation
    run_ideation()

if __name__ == "__main__":
    cli()