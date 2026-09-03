"""Documents modülü çıktı şemaları.

GET /documents/usages: belge başına, belgenin kullanıldığı fırsat özetleri.
Eskiden DocumentsPage /opportunities listesini istemcide filtreliyordu
(limit:2000 hack'i); artık bu uç bağları tek sorguda sunar.
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class OpportunityUsageOut(BaseModel):
    """Bir fırsatın belgeyle bağı (cv: başvuru kaydındaki CV, requirement: gereksinim belgesi)."""

    opportunity_id: UUID
    title: str
    status: str
    kind: str
    relation: Literal["cv", "requirement"]


class DocumentUsagesOut(BaseModel):
    """Bir belgenin bağlı fırsat kullanım listesi."""

    document_id: UUID
    usages: list[OpportunityUsageOut]
