from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timezone
import json
import typer
from rich import print

app = typer.Typer(add_completion=False)

def _env(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return v if v is not None and v != "" else default

def _utc_now_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def _output_dir() -> Path:
    return Path(_env("CDL_OUTPUT_DIR", "./var/outputs"))

@app.command()
def doctor() -> None:
    """
    Prints environment + paths to confirm the container/runtime is configured.
    """
    print("[bold cyan]Comic Data Lab  Doctor[/bold cyan]")
    print(f"CDL_DB_URL = [green]{_env('CDL_DB_URL','(missing)')}[/green]")
    print(f"CDL_CACHE_DIR = [green]{_env('CDL_CACHE_DIR','./var/cache')}[/green]")
    print(f"CDL_OUTPUT_DIR = [green]{str(_output_dir())}[/green]")

@app.command()
def new_run(tag: str = "weekly") -> None:
    """
    Creates a deterministic output bundle directory + run manifest.
    """
    out_root = _output_dir()
    date_slug = _utc_now_slug()
    run_dir = out_root / date_slug
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "project": "comic-data-lab",
        "tag": tag,
        "date_utc": date_slug,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "db_url": _env("CDL_DB_URL", ""),
        "cache_dir": _env("CDL_CACHE_DIR", "./var/cache"),
        "output_dir": str(run_dir),
        "notes": "Phase 1 scaffold manifest (no ingestion yet).",
    }

    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[bold green]Created[/bold green] {run_dir}")
    print(f"[bold green]Wrote[/bold green] {run_dir / 'run_manifest.json'}")

def main() -> None:
    app()

if __name__ == "__main__":
    main()

@app.command()
def ingest(
    source: str = typer.Option("comicvine", "--source", "-s"),
    start: str = typer.Option(..., "--start"),
    end: str = typer.Option(..., "--end"),
) -> None:
    """
    Ingest releases from a source in a date range and write artifacts into var/outputs/YYYY-MM-DD/.
    Example:
      python -m cdl ingest --source comicvine --start 2026-02-01 --end 2026-02-07
    """
    from cdl.ingest.runner import run_ingest
    out_dir = run_ingest(source=source, start_date=start, end_date=end)
    print(f"[bold green]Ingest complete[/bold green] -> {out_dir}")

@app.command("viz-weekly")
def viz_weekly() -> None:
    """
    Generate weekly summary JSON + charts + an Instagram-ready card from the latest output folder.
    Expects ingest_summary.json to exist in var/outputs/YYYY-MM-DD/.
    """
    import json
    from pathlib import Path
    import os
    from cdl.viz.weekly import load_issues, write_summary, save_bar_chart, save_instagram_card, top_publishers, top_series

    out_root = Path(os.getenv("CDL_OUTPUT_DIR", "./var/outputs"))
    # Pick latest folder by name (YYYY-MM-DD lexicographic works)
    folders = sorted([p for p in out_root.iterdir() if p.is_dir()])
    if not folders:
        raise RuntimeError(f"No output folders found in {out_root}")
    out_dir = folders[-1]

    ingest_summary = out_dir / "ingest_summary.json"
    if not ingest_summary.exists():
        raise RuntimeError(f"Missing {ingest_summary}. Run ingestion first.")

    meta = json.loads(ingest_summary.read_text(encoding="utf-8"))
    artifact_path = Path(meta["artifact"])
    start_date = meta["start_date"]
    end_date = meta["end_date"]

    df = load_issues(artifact_path)

    # Write summary
    summary_path = out_dir / "weekly_summary.json"
    summary = write_summary(df, summary_path, start_date, end_date)

    # Charts
    pubs_df = top_publishers(df, n=12)
    series_df = top_series(df, n=12)

    if len(pubs_df) > 0:
        save_bar_chart(pubs_df, "publisher", "count", "Top publishers (weekly releases)", out_dir / "top_publishers.png")

    if len(series_df) > 0:
        save_bar_chart(series_df, "series_name", "count", "Top series (weekly releases)", out_dir / "top_series.png")

    # Instagram card
    top_pub = (summary["top_publishers"][0]["publisher"], summary["top_publishers"][0]["count"]) if summary["top_publishers"] else None
    top_ser = (summary["top_series"][0]["series_name"], summary["top_series"][0]["count"]) if summary["top_series"] else None
    save_instagram_card(start_date, end_date, summary["total"], top_pub, top_ser, out_dir / "ig_weekly_card.png")

    print(f"[bold green]Viz complete[/bold green] -> {out_dir}")


@app.command("publish-ig")
def publish_ig(
    caption: str = typer.Option("", "--caption", help="Caption text to publish with the IG card."),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Validate credentials without posting."),
) -> None:
    """
    Phase 3: Publish the latest ig_weekly_card.png to Instagram via Graph API.
    Defaults to dry-run (credential validation only).
    """
    import os
    from pathlib import Path
    from cdl.utils.http import client
    from cdl.publish.instagram import load_ig_env, validate_ig_connection, find_latest_ig_card

    out_root = Path(os.getenv("CDL_OUTPUT_DIR", "./var/outputs"))
    card_path = find_latest_ig_card(out_root)

    ig = load_ig_env()
    http = client(Path(os.getenv("CDL_CACHE_DIR", "./var/cache")))

    info = validate_ig_connection(http, ig)
    print(f"[bold green]IG validated[/bold green] -> @{info.get('username')} (id={info.get('id')})")
    print(f"[bold]Card[/bold]: {card_path}")

    if dry_run:
        print("[yellow]Dry-run[/yellow]: not posting. Re-run with --no-dry-run after wiring upload.")
        return

    raise RuntimeError("Posting not implemented yet. Next Phase 3 step will add upload + publish.")


