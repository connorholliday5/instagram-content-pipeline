from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Issue:
    # Provenance
    source: str
    source_issue_id: Optional[int]
    source_volume_id: Optional[int]

    # Business fields
    publisher: Optional[str]
    series_name: str
    issue_number: Optional[str]
    title: Optional[str]
    release_date: Optional[str]  # ISO YYYY-MM-DD
    description: Optional[str]
    detail_url: Optional[str]
