from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from rich.console import Console

console = Console()


def run_weekly_pipeline():
    """Entry point called by scheduler — import and trigger the full pipeline."""
    from src.cli import run_pipeline
    console.log("[bold green]Scheduler triggered — running weekly pipeline[/bold green]")
    run_pipeline(dry_run=False)


def start_scheduler():
    scheduler = BlockingScheduler()
    # Every Wednesday at 9:00 AM
    scheduler.add_job(
        run_weekly_pipeline,
        CronTrigger(day_of_week="wed", hour=9, minute=0),
        id="weekly_watchtower",
        replace_existing=True,
    )
    console.log("[bold blue]Scheduler started — fires every Wednesday at 9:00 AM[/bold blue]")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        console.log("Scheduler stopped.")
