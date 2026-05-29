"""Pure stage functions for the daily poll pipeline."""
from datetime import date
from src.generate.poll import generate_poll_question, build_poll_story


def stage_generate(today_iso: str) -> dict:
    """Generate one poll question via Groq. Returns artifact data."""
    poll_data = generate_poll_question()
    return {
        "today": today_iso,
        "poll": poll_data,
    }


def stage_regenerate(today_iso: str) -> dict:
    """Same as generate — just calls Groq again."""
    return stage_generate(today_iso)


def stage_build(data: dict) -> dict:
    """Build the poll story slide. Returns slide path."""
    poll_data = data["poll"]
    today = date.fromisoformat(data["today"])
    slide_path = build_poll_story(poll_data, today)
    return {
        "slide_path": str(slide_path),
    }
