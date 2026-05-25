import os
import subprocess
import click
from datetime import date
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

load_dotenv()
console = Console()


def open_image(path: str):
    subprocess.Popen(["explorer", path.replace("/", "\\")])


def run_weekly_carousel(dry_run: bool = True):
    from src.ingest.metron import (
        fetch_top_weekly_issues,
        fetch_top_weekly_reprints,
        fetch_weekly_variants,
        search_issue,
        get_cover_url,
        get_publisher,
        get_title,
        get_store_date,
    )
    from src.generate.carousel import (
        build_cover_slide,
        build_list_slide,
        build_reprint_slide,
        build_pick_slide,
        build_variant_slide,
    )
    from src.caption.groq_caption import generate_caption
    from src.post.carousel_post import post_carousel
    from src.db.models import init_db

    init_db()
    today = date.today()
    mode = "[DRY RUN]" if dry_run else "[LIVE]"
    console.rule(f"[bold red]TheWatchtower_ Weekly Carousel {mode}[/bold red]")

    # --- Fetch top 10 new releases ---
    console.log("Fetching top 10 new releases this week...")
    top_issues = fetch_top_weekly_issues(limit=10)
    total = len(top_issues)

    if total == 0:
        console.print("[red]No issues found for this week. Try again closer to release day.[/red]")
        return

    console.print(f"\n[bold green]Top {total} new releases this week:[/bold green]\n")
    table = Table(show_header=True, header_style="bold red")
    table.add_column("#", width=4)
    table.add_column("Title")
    table.add_column("Publisher")
    table.add_column("Date")
    for i, issue in enumerate(top_issues):
        table.add_row(str(i + 1), get_title(issue), get_publisher(issue), get_store_date(issue))
    console.print(table)

    # --- Fetch reprints ---
    console.log("\nFetching top 5 reprints & collected editions...")
    reprint_issues = fetch_top_weekly_reprints(limit=5)
    if reprint_issues:
        console.print(f"[bold gold1]{len(reprint_issues)} reprint(s) found:[/bold gold1]")
        for r in reprint_issues:
            console.print(f"  [gold1]•[/gold1] {get_title(r)} ({get_publisher(r)})")
    else:
        console.print("[dim]No reprints found this week.[/dim]")

    # --- Auto-fetch variants ---
    console.log("\nScanning for rare variants...")
    auto_variants = fetch_weekly_variants()
    if auto_variants:
        console.print(f"[bold gold1]⚡ {len(auto_variants)} variant(s) detected:[/bold gold1]")
        for v in auto_variants:
            console.print(f"  [gold1]•[/gold1] {v['title']} ({v['publisher']})")
    else:
        console.print("[dim]No variants detected.[/dim]")

    # --- Personal picks ---
    console.print("\n[bold yellow]Which comics are you excited for this week?[/bold yellow]")
    console.print("[dim]Type title(s) separated by commas, or leave blank to skip[/dim]")
    console.print("[dim]Example: Batman #163, Superman #38[/dim]")
    picks_input = Prompt.ask("Your picks").strip()
    pick_titles = [p.strip() for p in picks_input.split(",")] if picks_input else []

    # --- Additional variants ---
    console.print("\n[bold yellow]Any additional variants to highlight?[/bold yellow]")
    console.print("[dim]Auto-detected variants above are included. Add more or leave blank.[/dim]")
    extra_input = Prompt.ask("Extra variants").strip()
    for vt in [v.strip() for v in extra_input.split(",") if v.strip()]:
        issue = search_issue(vt)
        auto_variants.append({
            "title": vt,
            "cover_url": get_cover_url(issue) if issue else None,
            "publisher": get_publisher(issue) if issue else "",
        })

    # --- Build slides ---
    console.rule("[bold]Building slides...[/bold]")
    slides = []

    # Slide 1 — Cover page
    console.log("Building slide 1: Cover page...")
    slides.append(str(build_cover_slide(today)))
    console.log(f"[green]✓[/green] {slides[-1]}")

    # Slides 2-3 — Top 10 new releases split across 2 slides
    mid = (total + 1) // 2
    list_a_dicts = [{
        "name": get_title(i),
        "volume": {"publisher": {"name": get_publisher(i)}},
        "store_date": get_store_date(i),
    } for i in top_issues[:mid]]

    console.log("Building slide 2: New releases part 1...")
    slides.append(str(build_list_slide(list_a_dicts, 2, total)))
    console.log(f"[green]✓[/green] {slides[-1]}")

    if top_issues[mid:]:
        list_b_dicts = [{
            "name": get_title(i),
            "volume": {"publisher": {"name": get_publisher(i)}},
            "store_date": get_store_date(i),
        } for i in top_issues[mid:]]
        console.log("Building slide 3: New releases part 2...")
        slides.append(str(build_list_slide(list_b_dicts, 3, total)))
        console.log(f"[green]✓[/green] {slides[-1]}")

    # Slide 4 — Reprints
    if reprint_issues:
        reprint_dicts = [{
            "name": get_title(r),
            "publisher": get_publisher(r),
            "store_date": get_store_date(r),
        } for r in reprint_issues]
        slide_num = len(slides) + 1
        console.log(f"Building slide {slide_num}: Reprints & collected editions...")
        slides.append(str(build_reprint_slide(reprint_dicts, slide_num)))
        console.log(f"[green]✓[/green] {slides[-1]}")

    # Slides 5-6 — Personal picks with cover art
    for pick_title in pick_titles[:2]:
        slide_num = len(slides) + 1
        console.log(f"Building slide {slide_num}: Pick — {pick_title}...")
        issue = search_issue(pick_title)
        slides.append(str(build_pick_slide(
            pick_title,
            get_cover_url(issue),
            get_publisher(issue),
            slide_num,
        )))
        console.log(f"[green]✓[/green] {slides[-1]}")

    # Slide 7 — Rare variants
    if auto_variants:
        slide_num = len(slides) + 1
        console.log(f"Building slide {slide_num}: Rare variants...")
        slides.append(str(build_variant_slide(auto_variants)))
        console.log(f"[green]✓[/green] {slides[-1]}")

    # --- Review slides ---
    console.rule("[bold yellow]Review Slides[/bold yellow]")
    console.print(f"[dim]{len(slides)} slides total. Opening each image for review...[/dim]\n")
    for i, slide_path in enumerate(slides):
        console.print(f"[bold cyan]Slide {i+1}/{len(slides)}:[/bold cyan] {slide_path}")
        open_image(slide_path)
        input("  Press Enter when ready for next slide...")

    # --- Caption ---
    console.rule("[bold]Caption[/bold]")
    pick_str = ", ".join(pick_titles) if pick_titles else "this week's top releases"
    variant_str = ", ".join([v["title"] for v in auto_variants]) if auto_variants else ""

    raw_caption = generate_caption(
        title="Top 10 Comics This Week",
        category="comics",
        description=(
            f"Top 10 new comic releases this week from DC, Marvel, Image and more. "
            f"{total} major titles dropping. "
            f"{'Plus ' + str(len(reprint_issues)) + ' reprints and collected editions. ' if reprint_issues else ''}"
            f"Connor's picks: {pick_str}. "
            f"{'Rare variants: ' + variant_str if variant_str else ''}"
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

    # --- Final confirm ---
    confirm = Prompt.ask(
        f"\n[bold red]Post {len(slides)} slides to Instagram?[/bold red]",
        choices=["yes", "no"],
        default="no"
    )

    if confirm == "yes":
        result = post_carousel(slides, full_caption, dry_run=dry_run)
        if dry_run:
            console.print("[yellow]DRY RUN complete — nothing posted.[/yellow]")
        else:
            console.log(f"[bold green]✓ Posted! Media ID: {result.get('media_id')}[/bold green]")
    else:
        console.print("[yellow]Cancelled.[/yellow]")

    console.rule("[bold red]Done[/bold red]")


@click.group()
def cli():
    """TheWatchtower_ Instagram pipeline."""
    pass


@cli.command()
@click.option("--live", is_flag=True, default=False, help="Post live to Instagram")
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


if __name__ == "__main__":
    cli()