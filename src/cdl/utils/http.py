from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from cdl.utils.cache import cache_path, load_json, save_json


@dataclass
class HttpClient:
    cache_dir: Path
    min_interval_sec: float = 1.25  # be polite by default
    timeout_sec: float = 30.0
    user_agent: str = "comic-data-lab/0.1 (+research; respectful crawler)"
    _last_request_ts: float = 0.0

    def _throttle(self) -> None:
        now = time.time()
        elapsed = now - self._last_request_ts
        if elapsed < self.min_interval_sec:
            time.sleep(self.min_interval_sec - elapsed)
        self._last_request_ts = time.time()

    def get_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        cache_key: Optional[str] = None,
    ) -> Any:
        key = cache_key or f"GET {url} {params}"
        path = cache_path(self.cache_dir, key, suffix=".json")

        cached = load_json(path)
        if cached is not None:
            return cached

        self._throttle()
        headers = {"User-Agent": self.user_agent}
        resp = requests.get(url, params=params, headers=headers, timeout=self.timeout_sec)

        if not resp.ok:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise RuntimeError(f"HTTP {resp.status_code} error for {url}: {detail}")

        data = resp.json()
        save_json(path, data)
        return data


def client(
    cache_dir: Path,
    min_interval_sec: float = 1.25,
    timeout_sec: float = 30.0,
    user_agent: str = "comic-data-lab/0.1 (+research; respectful crawler)",
) -> HttpClient:
    return HttpClient(
        cache_dir=cache_dir,
        min_interval_sec=min_interval_sec,
        timeout_sec=timeout_sec,
        user_agent=user_agent,
    )
