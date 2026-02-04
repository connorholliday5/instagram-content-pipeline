from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cdl.ingest.schema import Issue
from cdl.utils.http import HttpClient

API_BASE = "https://comicvine.gamespot.com/api"

def _key() -> str:
    k = os.getenv("COMICVINE_API_KEY", "").strip()
    if not k:
        raise RuntimeError("COMICVINE_API_KEY is missing. Add it to .env and restart your shell.")
    return k

def client(cache_dir: Path) -> HttpClient:
    return HttpClient(cache_dir=cache_dir, min_interval_sec=1.25)

def _parse_date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    return s[:10] if len(s) >= 10 else None

def _get_issues_page(http: HttpClient, api_key: str, page: int, date_range: Tuple[str, str]) -> Dict[str, Any]:
    start, end = date_range
    url = f"{API_BASE}/issues/"
    params = {
        "api_key": api_key,
        "format": "json",
        "sort": "cover_date:asc",
        "page": page,
        "filter": f"cover_date:{start}|{end}",
        # include volume so we can enrich publisher via volume endpoint
        "field_list": "id,name,issue_number,cover_date,description,site_detail_url,volume",
    }
    cache_key = f"comicvine issues page={page} cover_date={start}|{end}"
    return http.get_json(url, params=params, cache_key=cache_key)

def _get_volume(http: HttpClient, api_key: str, volume_id: int) -> Dict[str, Any]:
    # volume resource is /volume/4050-{id}/
    url = f"{API_BASE}/volume/4050-{volume_id}/"
    params = {
        "api_key": api_key,
        "format": "json",
        "field_list": "id,name,publisher",
    }
    cache_key = f"comicvine volume id={volume_id}"
    return http.get_json(url, params=params, cache_key=cache_key)

def fetch_releases(
    cache_dir: Path,
    start_date: str,
    end_date: str,
    max_pages: int = 200,
) -> List[Issue]:
    api_key = _key()
    http = client(cache_dir)

    raw_rows: List[Dict[str, Any]] = []
    total_expected: Optional[int] = None

    for page in range(1, max_pages + 1):
        payload = _get_issues_page(http, api_key, page, (start_date, end_date))

        if payload.get("status_code") != 1:
            err = payload.get("error") or "Unknown ComicVine error"
            raise RuntimeError(f"ComicVine API error: status_code={payload.get('status_code')} error={err}")

        if total_expected is None:
            ntr = payload.get("number_of_total_results")
            if isinstance(ntr, int):
                total_expected = ntr

        results = payload.get("results") or []
        if not results:
            break

        raw_rows.extend(results)

        # Stop if we've collected all reported results
        if isinstance(total_expected, int) and len(raw_rows) >= total_expected:
            break

        # Extra safe stop if last page is short
        limit = payload.get("limit")
        if isinstance(limit, int) and len(results) < limit:
            break

    # Volume publisher enrichment (cached): build map volume_id -> publisher_name
    volume_ids = sorted({(r.get("volume") or {}).get("id") for r in raw_rows if isinstance(r.get("volume"), dict) and (r.get("volume") or {}).get("id")})
    vol_to_pub: Dict[int, Optional[str]] = {}
    for vid in volume_ids:
        try:
            vpay = _get_volume(http, api_key, int(vid))
            vres = vpay.get("results") or {}
            pub = vres.get("publisher")
            pub_name = pub.get("name") if isinstance(pub, dict) else None
            vol_to_pub[int(vid)] = pub_name
        except Exception:
            vol_to_pub[int(vid)] = None

    issues: List[Issue] = []
    for r in raw_rows:
        vol = r.get("volume") if isinstance(r.get("volume"), dict) else {}
        volume_id = vol.get("id") if isinstance(vol, dict) else None
        series_name = vol.get("name") if isinstance(vol, dict) and vol.get("name") else "(unknown series)"
        publisher = vol_to_pub.get(int(volume_id)) if volume_id else None

        issues.append(
            Issue(
                source="comicvine",
                source_issue_id=(int(r["id"]) if r.get("id") is not None else None),
                source_volume_id=(int(volume_id) if volume_id is not None else None),
                publisher=publisher,
                series_name=series_name,
                issue_number=(str(r.get("issue_number")) if r.get("issue_number") is not None else None),
                title=r.get("name"),
                release_date=_parse_date(r.get("cover_date")),
                description=r.get("description"),
                detail_url=r.get("site_detail_url"),
            )
        )

    return issues
