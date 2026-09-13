"""Modul kayit defterlerini tek yerden okuyan yardimcilar.

- EntityTypeSpec (tip -> etiket/rota/ikon) -- AGENTS.md kural 13'ün tek kaynagi.
- event_verbs (verb -> etiket) -- activity modulu bunu okur.

Frontend GET /api/registry/entity-types ve /api/registry/event-verbs ile bu
kayitlari alir; tip->rota veya verb->etiket sabiti YAZMAZ.
"""

from __future__ import annotations

from app.modules import MODULES, EntityTypeSpec

#: Cekirdegin (modulsuz) urettigi olaylar. `link.created` core/router.py'da,
#: `source.*` ve `source_sync.*` core/runs.py + core/source_sync.py'de yazilir;
#: bir modulun ozelligi olmadiklari icin burada, tek yerde kayitlidirler.
#: Kural: kodda cagrilan HER verb burada ya da bir ModuleSpec.event_verbs
#: icinde bulunur (bkz. tests/test_registry.py::test_every_logged_event_verb_is_registered).
CORE_EVENT_VERBS: tuple[str, ...] = (
    "link.created",
    "source.stalled",
    "source.failing",
    "source_sync.queued",
    "source_sync.started",
    "source_sync.sources_added",
    "source_sync.completed",
)


def all_entity_types() -> list[EntityTypeSpec]:
    return [spec for module in MODULES for spec in module.entity_types]


def type_spec(entity_type: str) -> EntityTypeSpec | None:
    for spec in all_entity_types():
        if spec.type == entity_type:
            return spec
    return None


def all_event_verbs() -> list[str]:
    return [*CORE_EVENT_VERBS, *(verb for module in MODULES for verb in module.event_verbs)]
