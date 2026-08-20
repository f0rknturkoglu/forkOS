"""SourceAdapter protokolu.

Job Hunter, OSYM, YLSY, MSc scraper'lari ILERIDE bu arayuze yazilacak.
Boylece worker'i degistirmeden yeni kaynak eklenebilir ve gerekirse
tum scraper katmani bir VPS'e tasinabilir.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class RawItem:
    external_id: str                    # dedup anahtari
    title: str
    url: str | None = None
    summary: str | None = None
    published_at: datetime | None = None
    extra: dict = field(default_factory=dict)


class SourceAdapter(Protocol):
    id: str
    interval_minutes: int

    async def fetch(self) -> list[RawItem]:
        """Kaynagi cek. Hata firlatabilir -- worker source_run'a yazar."""
        ...
