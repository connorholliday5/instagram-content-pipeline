from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def cache_path(cache_dir: Path, key: str, suffix: str = ".json") -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{sha256_hex(key)}{suffix}"

def load_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
