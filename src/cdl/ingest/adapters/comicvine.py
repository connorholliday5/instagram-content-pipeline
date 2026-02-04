from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cdl.ingest.schema import Issue
from cdl.utils.http import HttpClient

API_BASE = "https://comicvine.gamespot.com/api"

def _key() -> str:
    k = os.getenv("COMICVINE_API_KEY", "").strip()
    if not k:
        raise RuntimeError("COMICVINE_API_KEY is missing. Add it to .env (local) and restart your shell.")
    return k

def client(cache_dir: Path) -> HttpClient:
    # ComicVine can be sensitive to rate; keep conservative.
    return HttpClient(cache_dir=cache_dir, min_interval_sec=1.25)

def _parse_date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    # ComicVine often uses "YYYY-MM-DD" (cover_date) or may include time elsewhere.
    # Normalize to YYYY-MM-DD when possible.
    try:
        if len(s) >= 10:
            return s[:10]
    except Exception:
        return None
    return None

def _get_issues_page(http: HttpClient, api_key: str, page: int, date_range: Tuple[str, str]) -> Dict[str, Any]:
    # ComicVine "issues" endpoint
    # Filters are documented by ComicVine; we use cover_date range when available.
    # NOTE: We keep parameters explicit and cacheable.
    start, end = date_range
    url = f"{API_BASE}/issues/"
    params = {
        "api_key": api_key,
        "format": "json",
        "sort": "cover_date:asc",
        "page": page,
        # cover_date is typically the on-sale date in ComicVine data; range filter syntax:
        "filter": f"cover_date:{start}|{end}",
        "field_list": "id,name,issue_number,cover_date,description,site_detail_url,volume,publisher",
    }
    cache_key = f"comicvine issues page={page} cover_date={start}|{end}"
    return http.get_json(url, params=params, cache_key=cache_key)

def fetch_releases(cache_dir: Path, start_date: str, end_date: str, max_pages: int = 10) -> List[Issue]:
    """
    Fetch issues between start_date and end_date (inclusive-ish) and normalize to Issue records.
    """
    api_key = _key()
    http = client(cache_dir)

    issues: List[Issue] = []
    for page in range(1, max_pages + 1):
        payload = _get_issues_page(http, api_key, page, (start_date, end_date))

        status = payload.get("status_code")
        if status != 1:
            # ComicVine uses status_code == 1 for OK
            err = payload.get("error") or "Unknown ComicVine error"
            raise RuntimeError(f"ComicVine API error: status_code={status} error={err}")

        results = payload.get("results") or []
        if not results:
            break

        for r in results:
            vol = r.get("volume") or {}
            publisher = None
            # Some payloads include publisher nested; sometimes only in volume/publisher on other endpoints
            pub = r.get("publisher")
            if isinstance(pub, dict):
                publisher = pub.get("name")
            if not publisher and isinstance(vol, dict):
                vp = vol.get("publisher")
                if isinstance(vp, dict):
                    publisher = vp.get("name")

            series_name = None
            if isinstance(vol, dict):
                series_name = vol.get("name")

            issues.append(
                Issue(
                    source="comicvine",
                    publisher=publisher,
                    series_name=series_name or "(unknown series)",
                    issue_number=(str(r.get("issue_number")) if r.get("issue_number") is not None else None),
                    title=r.get("name"),
                    release_date=_parse_date(r.get("cover_date")),
                    description=r.get("description"),
                    detail_url=r.get("site_detail_url"),
                )
            )

        # Stop early if we've already pulled fewer than a full page size (ComicVine default is 100)
        limit = payload.get("limit")
        if isinstance(limit, int) and len(results) < limit:
            break

    return issues
