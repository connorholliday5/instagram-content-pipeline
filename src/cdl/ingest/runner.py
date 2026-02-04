from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import List

from cdl.ingest.schema import Issue
from cdl.ingest.adapters import comicvine

def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v else default

def run_ingest(source: str, start_date: str, end_date: str) -> Path:
    """
    Runs ingestion and writes artifacts into var/outputs/YYYY-MM-DD/.
    Returns the output directory path.
    """
    cache_dir = Path(_env("CDL_CACHE_DIR", "./var/cache"))
    out_root = Path(_env("CDL_OUTPUT_DIR", "./var/outputs"))

    # Use today's folder (created by CLI new-run) if present; otherwise create it.
    # We choose "today" in local timezone as a folder name already used in your CLI.
    # If you want strictly UTC, we can change later.
    from datetime import datetime
    date_slug = datetime.utcnow().strftime("%Y-%m-%d")
    out_dir = out_root / date_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    if source == "comicvine":
        issues: List[Issue] = comicvine.fetch_releases(cache_dir, start_date, end_date, max_pages=10)
    else:
        raise ValueError(f"Unknown source: {source}")

    # Write normalized releases
    releases_path = out_dir / f"releases_{source}_{start_date}_to_{end_date}.json"
    releases_path.write_text(json.dumps([asdict(x) for x in issues], indent=2), encoding="utf-8")

    # Lightweight summary
    summary = {
        "source": source,
        "start_date": start_date,
        "end_date": end_date,
        "count": len(issues),
        "artifact": str(releases_path),
    }
    (out_dir / "ingest_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return out_dir
