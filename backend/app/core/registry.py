"""Modul kayit defterlerini tek yerden okuyan yardimcilar.

- EntityTypeSpec (tip -> etiket/rota/ikon) -- AGENTS.md kural 13'ün tek kaynagi.
- event_verbs (verb -> etiket) -- activity modulu bunu okur.

Frontend GET /api/registry/entity-types ve /api/registry/event-verbs ile bu
kayitlari alir; tip->rota veya verb->etiket sabiti YAZMAZ.
"""

from __future__ import annotations

from app.modules import MODULES, EntityTypeSpec


def all_entity_types() -> list[EntityTypeSpec]:
    return [spec for module in MODULES for spec in module.entity_types]


def type_spec(entity_type: str) -> EntityTypeSpec | None:
    for spec in all_entity_types():
        if spec.type == entity_type:
            return spec
    return None


def all_event_verbs() -> list[str]:
    return [verb for module in MODULES for verb in module.event_verbs]
