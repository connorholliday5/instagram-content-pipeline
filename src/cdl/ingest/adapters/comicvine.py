from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from cdl.ingest.schema import Issue
from cdl.utils.http import HttpClient

API_BASE = "https://comicvine.gamespot.com/api"

def _key() -> str:
    k = os.getenv("COMICVINE_API_KEY", "").strip()
    if not k:
        raise RuntimeError("COMICVINE_API_KEY is missing. Add it to .env and restart your shell.")
    return k

def client(cache_dir: Path) -> HttpClient:
    return HttpClient(cache_dir=cache_dir, min_interval_sec=1.2)

def fetch_weekly_releases(cache_dir: Path, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Issue]:
    """
    Phase 2 stub: will implement API calls + normalization next.
    """
    _ = _key()
    _ = client(cache_dir)
    return []
