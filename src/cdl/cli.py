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
