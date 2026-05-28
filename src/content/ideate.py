import os
import requests
import json
from datetime import date, timedelta
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from dotenv import load_dotenv

load_dotenv()

console = Console()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

CATEGORIES = [
    "DC Comics characters or storylines",
    "Marvel Comics characters or storylines",
    "Comic books general",
    "Fantasy books like Game of Thrones or Red Rising",
    "Sci-fi books",
    "Superhero movies",
    "Action or thriller movies",
    "Blockbuster movies",
    "Streaming TV shows",
    "Pop culture general",
    "Would you rather — nerd culture",
    "Hot takes — comics, movies, or TV",
    "Ranking debate — best of a franchise",
    "Overrated or underrated — anything",
]


def _next_wednesday(from_date: date = None) -> date:
    d = from_date or date.today()
    days_ahead = 2 - d.weekday()  # Wednesday = 2
    if days_ahead <= 0:
        days_ahead += 7
    return d + timedelta(days=days_ahead)


def _is_first_of_month_this_week(from_date: date = None) -> tuple[bool, date | None]:
    """Check if the 1st falls within the next 7 days."""
    d = from_date or date.today()
    for i in range(8):
        check = d + timedelta(days=i)
        if check.day == 1:
            return True, check
    return False, None


def _fetch_upcoming_comics(wednesday: date) -> list[str]:
    """Pull confirmed comics for upcoming Wednesday from Metron."""
    try:
        from src.ingest.comicvine import fetch_top_weekly_issues, get_title
        issues = fetch_top_weekly_issues(limit=10)
        return [get_title(i) for i in issues]
    except Exception:
        return []


def _generate_weekly_polls(days: list[date]) -> list[dict]:
    """Generate 7 poll questions in one Groq call."""
    import random
    categories = random.sample(CATEGORIES, min(7, len(CATEGORIES)))
    cats_str = "\n".join([f"{i+1}. {c}" for i, c in enumerate(categories)])

    system = """You generate Instagram Story poll questions for @the.watch_tower — covering comics, movies, TV, and books.
Rules:
- Each question max 12 words, genuinely debatable
- Options max 4 words each, no obvious answers
- Vary format: comparisons, would-you-rather, hot takes, rankings
- Return ONLY a JSON array of 7 objects, no extra text:
[{"question":"...","option_a":"...","option_b":"..."},...]"""

    user = f"Generate 7 polls, one per category:\n{cats_str}"

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
                "max_tokens": 800,
                "temperature": 1.0,
            },
            timeout=20
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        raw = raw.replace("```json","").replace("```","").strip()
        polls = json.loads(raw)
        # Attach dates
        for i, poll in enumerate(polls[:7]):
            poll["date"] = days[i].strftime("%A %b %d")
            poll["category"] = categories[i]
        return polls[:7]
    except Exception as e:
        console.print(f"[red]Poll generation failed: {e}[/red]")
        return []


def _save_plan(plan_text: str, polls: list[dict], week_start: date):
    """Save weekly plan and polls to project folder."""
    output_dir = Path("output/weekly_plans")
    output_dir.mkdir(parents=True, exist_ok=True)

    plan_path = output_dir / f"plan_{week_start.strftime('%Y_%m_%d')}.txt"
    polls_path = output_dir / f"polls_{week_start.strftime('%Y_%m_%d')}.json"

    plan_path.write_text(plan_text, encoding="utf-8")
    polls_path.write_text(json.dumps(polls, indent=2), encoding="utf-8")

    return plan_path, polls_path


def _build_poll_slides_batch(polls: list[dict], week_start: date):
    """Build all 7 poll story slides at once."""
    from src.generate.poll import build_poll_story
    saved = []
    for i, poll in enumerate(polls):
        poll_date = week_start + timedelta(days=i)
        slide_path = build_poll_story(poll, poll_date)
        saved.append(str(slide_path))
        console.log(f"[green]✓[/green] Day {i+1}: {slide_path.name}")
    return saved


def run_ideation():
    today = date.today()
    week_start = today
    days = [today + timedelta(days=i) for i in range(7)]

    console.rule("[bold red]TheWatchtower_ — Weekly Content Plan[/bold red]")
    console.print(f"[dim]Week of {today.strftime('%B %d, %Y')}[/dim]\n")

    # ── Check what's happening this week ──
    next_wed = _next_wednesday(today)
    first_in_week, first_date = _is_first_of_month_this_week(today)

    # ── Fetch upcoming comics ──
    console.log("Checking Metron for upcoming Wednesday releases...")
    comics = _fetch_upcoming_comics(next_wed)
    comics_note = ""
    if comics:
        console.print(f"[bold green]{len(comics)} confirmed releases for {next_wed.strftime('%b %d')}:[/bold green]")
        for c in comics:
            console.print(f"  [dim]•[/dim] {c}")
        comics_note = f"{len(comics)} confirmed releases"
    else:
        console.print(f"[yellow]⚠ No comics confirmed yet for {next_wed.strftime('%b %d')} — check back Tuesday[/yellow]")
        comics_note = "Not yet updated — check back Tuesday"

    # ── Generate 7 polls ──
    console.log("\nGenerating 7 poll questions for the week...")
    polls = _generate_weekly_polls(days)

    if not polls:
        console.print("[red]Poll generation failed.[/red]")
        return

    # ── Show polls for batch approval ──
    console.rule("[bold yellow]7 Daily Polls — Review All[/bold yellow]")
    table = Table(show_header=True, header_style="bold red", show_lines=True)
    table.add_column("Day", width=14)
    table.add_column("Question")
    table.add_column("A", width=16)
    table.add_column("B", width=16)

    for poll in polls:
        table.add_row(
            poll.get("date",""),
            poll["question"],
            poll["option_a"],
            poll["option_b"],
        )
    console.print(table)

    action = Prompt.ask(
        "\nPolls",
        choices=["approve", "regenerate", "edit"],
        default="approve"
    )

    if action == "regenerate":
        console.log("Regenerating...")
        polls = _generate_weekly_polls(days)
        # Show again
        for poll in polls:
            console.print(f"  [yellow]{poll.get('date','')}[/yellow] — {poll['question']} | {poll['option_a']} vs {poll['option_b']}")
        action = Prompt.ask("Polls", choices=["approve","edit"], default="approve")

    if action == "edit":
        console.print("[dim]Edit each poll — leave blank to keep as is[/dim]")
        for i, poll in enumerate(polls):
            console.print(f"\n[bold]Poll {i+1} ({poll.get('date','')}):[/bold] {poll['question']}")
            new_q = Prompt.ask("  Question", default=poll["question"]).strip()
            new_a = Prompt.ask("  Option A", default=poll["option_a"]).strip()
            new_b = Prompt.ask("  Option B", default=poll["option_b"]).strip()
            polls[i]["question"] = new_q
            polls[i]["option_a"] = new_a
            polls[i]["option_b"] = new_b

    # ── Build poll slides ──
    console.rule("[bold]Building 7 poll story slides...[/bold]")
    saved_slides = _build_poll_slides_batch(polls, week_start)

    # ── Build weekly plan text ──
    plan_lines = [
        f"WATCHTOWER WEEKLY PLAN — {today.strftime('%B %d, %Y')}",
        "=" * 50,
        "",
        "FIXED POSTS:",
        f"  Wednesday {next_wed.strftime('%b %d')} — python -m app run  (New Comic Book Day)",
        f"  Comics confirmed: {comics_note}",
        "",
    ]

    if first_in_week and first_date:
        plan_lines += [
            f"  {first_date.strftime('%A %b %d')} is the 1st — run both:",
            "    python -m app movies",
            "    python -m app tv",
            "",
        ]

    plan_lines += [
        "DAILY POLLS (slides saved to output/weekly_plans/):",
    ]
    for poll in polls:
        plan_lines.append(
            f"  {poll.get('date','')} — {poll['question']} "
            f"({poll['option_a']} vs {poll['option_b']})"
        )

    plan_lines += [
        "",
        "BOOK REVIEW — run anytime: python -m app review",
        "",
        "=" * 50,
    ]

    plan_text = "\n".join(plan_lines)

    # ── Save everything ──
    plan_path, polls_path = _save_plan(plan_text, polls, week_start)

    # ── Show final summary ──
    console.rule("[bold green]Weekly Plan[/bold green]")
    console.print(Panel(plan_text, border_style="green"))
    console.print(f"\n[dim]Plan saved: {plan_path}[/dim]")
    console.print(f"[dim]Polls JSON: {polls_path}[/dim]")
    console.print(f"[dim]Poll slides: output/[/dim]")
    console.rule("[bold red]Done[/bold red]")