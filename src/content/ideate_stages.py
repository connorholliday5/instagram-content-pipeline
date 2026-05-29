"""Pure stage functions for the ideate pipeline.
Each stage takes plain data in and returns plain data out.
No prompts, no console output, no side effects beyond the existing helpers.
"""
from datetime import date, timedelta
from src.content.ideate import (
    _next_wednesday,
    _is_first_of_month_this_week,
    _fetch_upcoming_comics,
    _generate_weekly_polls,
    _build_poll_slides_batch,
    _save_plan,
)


def stage_fetch(today: date) -> dict:
    """Stage 1: pull comics and generate 7 polls. Returns artifact data."""
    week_start = today
    days = [today + timedelta(days=i) for i in range(7)]
    next_wed = _next_wednesday(today)
    first_in_week, first_date = _is_first_of_month_this_week(today)

    comics = _fetch_upcoming_comics(next_wed)
    if comics:
        comics_note = f"{len(comics)} confirmed releases"
    else:
        comics_note = "Not yet updated — check back Tuesday"

    polls = _generate_weekly_polls(days)

    return {
        "today": today.isoformat(),
        "week_start": week_start.isoformat(),
        "next_wed": next_wed.isoformat(),
        "first_in_week": first_in_week,
        "first_date": first_date.isoformat() if first_date else None,
        "comics": comics,
        "comics_note": comics_note,
        "polls": polls,
    }


def stage_regenerate_polls(today_iso: str) -> list[dict]:
    """Regenerate polls only. Used when user taps Regenerate."""
    today = date.fromisoformat(today_iso)
    days = [today + timedelta(days=i) for i in range(7)]
    return _generate_weekly_polls(days)


def stage_build(data: dict) -> dict:
    """Stage 2: build the 7 poll slides and write the weekly plan text file."""
    polls = data["polls"]
    week_start = date.fromisoformat(data["week_start"])
    next_wed = date.fromisoformat(data["next_wed"])
    first_in_week = data["first_in_week"]
    first_date = date.fromisoformat(data["first_date"]) if data["first_date"] else None
    comics_note = data["comics_note"]
    today = date.fromisoformat(data["today"])

    slides = _build_poll_slides_batch(polls, week_start)

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
    plan_lines += ["DAILY POLLS (slides saved to output/weekly_plans/):"]
    for poll in polls:
        plan_lines.append(
            f"  {poll.get('date','')} — {poll['question']} "
            f"({poll['option_a']} vs {poll['option_b']})"
        )
    plan_lines += ["", "BOOK REVIEW — run anytime: python -m app review", "", "=" * 50]

    plan_text = "\n".join(plan_lines)
    plan_path, polls_path = _save_plan(plan_text, polls, week_start)

    return {
        "slides": [str(s) for s in slides],
        "plan_text": plan_text,
        "plan_path": str(plan_path),
        "polls_path": str(polls_path),
    }
