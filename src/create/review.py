import os
import subprocess
import tempfile
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from dotenv import load_dotenv

load_dotenv()
console = Console()


def fetch_book_cover(title, author):
    import requests
    query = (title + " " + author).replace(" ", "+")
    try:
        resp = requests.get(
            f"https://openlibrary.org/search.json?q={query}&limit=1",
            timeout=10
        )
        resp.raise_for_status()
        docs = resp.json().get("docs", [])
        if docs and docs[0].get("cover_i"):
            cover_id = docs[0]["cover_i"]
            return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
    except Exception:
        pass
    return None


def open_editor_for_caption():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write("# Write your review caption below. Delete this line when done.\n\n")
        tmp_path = f.name

    subprocess.run(["notepad.exe", tmp_path], check=True)

    with open(tmp_path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    os.unlink(tmp_path)
    lines = [l for l in content.splitlines() if not l.startswith("#")]
    return "\n".join(lines).strip()


def run_review():
    from src.generate.image_builder import build_image

    console.rule("[bold red]TheWatchtower_ — Book Review Creator[/bold red]")

    title = Prompt.ask("[bold]Book title[/bold]")
    author = Prompt.ask("[bold]Author[/bold]")
    rating = Prompt.ask("[bold]Your rating[/bold]", choices=["1", "2", "3", "4", "5"])
    stars = "⭐" * int(rating)

    console.log("Fetching cover art...")
    cover_url = fetch_book_cover(title, author)
    if cover_url:
        console.log("[green]✓[/green] Cover found")
    else:
        console.log("[yellow]⚠ No cover found — using text-only layout[/yellow]")

    console.log("Generating image...")
    img_path = build_image(
        title=title,
        category="books",
        cover_url=cover_url,
        subtitle=f"by {author}",
        label=f"REVIEW {stars}",
    )
    console.log(f"[green]✓[/green] Image saved → {img_path}")

    while True:
        console.print("\n[bold yellow]Notepad will open — write your review caption, save, and close.[/bold yellow]")
        input("Press Enter to open Notepad...")

        caption = open_editor_for_caption()

        if not caption:
            console.print("[red]Caption was empty. Try again.[/red]")
            continue

        full_caption = (
            caption + "\n\n" + stars + " " + rating + "/5\n\n"
            "#BookReview #TheWatchtower #ComicBooks #GraphicNovels "
            "#DCComics #NerdCulture #BookNerd #WeeklyReads #NewRelease "
            "#BookRecommendation #ComicBookCommunity #Bookstagram #ReadingList #GeekCulture"
        )

        console.print(Panel(full_caption, title="[bold]Caption Preview[/bold]", border_style="cyan"))
        console.print(f"[dim]Image: {img_path}[/dim]\n")

        action = Prompt.ask(
            "[bold]What do you want to do?[/bold]",
            choices=["approve", "edit", "cancel"],
            default="approve"
        )

        if action == "approve":
            dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
            if dry_run:
                console.print("[bold yellow]DRY_RUN=true — not posting. Set DRY_RUN=false in .env to go live.[/bold yellow]")
            else:
                console.log(f"[green]✓ Posted: {img_path}[/green]")
            console.rule("[bold green]Done[/bold green]")
            break
        elif action == "edit":
            continue
        elif action == "cancel":
            console.print("[red]Cancelled.[/red]")
            break