from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from cdl.ingest.schema import Issue
from cdl.ingest.adapters import comicvine

def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v else default

def _dedupe(issues: List[Issue]) -> Tuple[List[Issue], Dict[str, int]]:
    seen = set()
    out: List[Issue] = []
    dropped = 0

    for x in issues:
        if x.source_issue_id is not None:
            key = ("id", x.source, x.source_issue_id)
        else:
            key = ("fallback", x.source, x.series_name, x.issue_number or "", x.release_date or "")
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        out.append(x)

    return out, {"input": len(issues), "deduped": len(out), "dropped": dropped}

def run_ingest(source: str, start_date: str, end_date: str) -> Path:
    cache_dir = Path(_env("CDL_CACHE_DIR", "./var/cache"))
    out_root = Path(_env("CDL_OUTPUT_DIR", "./var/outputs"))

    date_slug = datetime.utcnow().strftime("%Y-%m-%d")
    out_dir = out_root / date_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    if source == "comicvine":
        issues = comicvine.fetch_releases(cache_dir, start_date, end_date, max_pages=200)
    else:
        raise ValueError(f"Unknown source: {source}")

    deduped, dq = _dedupe(issues)

    releases_path = out_dir / f"releases_{source}_{start_date}_to_{end_date}.json"
    releases_path.write_text(json.dumps([asdict(x) for x in deduped], indent=2), encoding="utf-8")

    summary = {
        "source": source,
        "start_date": start_date,
        "end_date": end_date,
        "count": len(deduped),
        "dq": dq,
        "artifact": str(releases_path),
        "run_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    (out_dir / "ingest_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # quick DQ report
    pub_missing = sum(1 for x in deduped if not (x.publisher or "").strip())
    (out_dir / "dq_report.json").write_text(
        json.dumps(
            {
                "publisher_missing": pub_missing,
                "publisher_missing_rate": (pub_missing / max(1, len(deduped))),
                **dq,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return out_dir
