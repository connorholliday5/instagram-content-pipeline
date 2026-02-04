from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Issue:
    source: str
    publisher: Optional[str]
    series_name: str
    issue_number: Optional[str]
    title: Optional[str]
    release_date: Optional[str]  # ISO date string YYYY-MM-DD
    description: Optional[str]
    detail_url: Optional[str]
