from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from rich.console import Console

console = Console()


def run_weekly_pipeline():
    from src.cli import run_weekly_carousel
    console.log("[bold green]Scheduler triggered — running weekly carousel pipeline[/bold green]")
    run_weekly_carousel(dry_run=False)


def start_scheduler():
    scheduler = BlockingScheduler()
    # Every Tuesday at 9:00 AM
    scheduler.add_job(
        run_weekly_pipeline,
        CronTrigger(day_of_week="tue", hour=9, minute=0),
        id="weekly_watchtower_carousel",
        replace_existing=True,
    )
    console.log("[bold blue]Scheduler started — fires every Tuesday at 9:00 AM[/bold blue]")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        console.log("Scheduler stopped.")