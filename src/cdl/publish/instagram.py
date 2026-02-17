from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cdl.utils.http import HttpClient, client


@dataclass(frozen=True)
class IGEnv:
    access_token: str
    business_account_id: str
    api_version: str = "v20.0"  # safe default; can be overridden via env


def _env(name: str, default: Optional[str] = None) -> str:
    v = os.getenv(name, default)
    if v is None or str(v).strip() == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return str(v).strip()


def load_ig_env() -> IGEnv:
    # Minimal set for Graph API publishing
    return IGEnv(
        access_token=_env("IG_ACCESS_TOKEN"),
        business_account_id=_env("IG_BUSINESS_ACCOUNT_ID"),
        api_version=os.getenv("IG_API_VERSION", "v20.0").strip() or "v20.0",
    )


def validate_ig_connection(http: HttpClient, ig: IGEnv) -> dict:
    # Basic token/account validation
    base = f"https://graph.facebook.com/{ig.api_version}"
    url = f"{base}/{ig.business_account_id}"
    params = {"access_token": ig.access_token, "fields": "id,username"}
    payload = http.get_json(url, params=params, cache_key=None)
    if payload.get("error"):
        raise RuntimeError(f"IG validate failed: {payload['error']}")
    return payload


def find_latest_ig_card(out_root: Path) -> Path:
    # Pick latest folder by name; matches your viz-weekly behavior
    folders = sorted([p for p in out_root.iterdir() if p.is_dir()])
    if not folders:
        raise RuntimeError(f"No output folders found in {out_root}")
    out_dir = folders[-1]
    card = out_dir / "ig_weekly_card.png"
    if not card.exists():
        raise RuntimeError(f"Expected {card} to exist. Run: python -m cdl viz-weekly")
    return card

