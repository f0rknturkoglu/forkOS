"""PHASE 3 sahiplik sınırı: legacy Notlar dondurulmuş arşivdir.

Bu dosya, ürünün bir daha Notlar sahibi gibi davranmadığını kanıtlar:

  - Legacy Notes CRUD uçları KAYITLI DEĞİLDİR (§42/A).
  - `note` / `note_folder` canlı bilgi kaydı değildir: aramada çıkmaz,
    ilişki panellerinde görünmez (§43, §44, §45).
  - Günlük bakım dondurulmuş arşive YAZMAZ (§6).
  - Göç aracı ve arşiv tabloları yerinde durur (§5, §7).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.core import search as search_svc
from app.core.entity import create_entity
from app.core.links import ARCHIVED_ENTITY_TYPES, backlinks, link, related
from app.core.models import Event
from app.core.registry import type_spec
from app.db import SessionLocal
from app.integrations.obsidian.service import vault_index
from app.main import app
from app.modules.note import MODULE as note_module
from app.modules.note.models import Note, NoteAttachment, NoteFolder
from app.modules.project.models import Project
from app.modules.system import maintenance

#: Ürün yüzeyinden TAMAMEN kalkması gereken legacy yollar.
REMOVED_LEGACY_PATHS = (
    "/api/notes",
    "/api/notes/daily/{journal_day}",
    "/api/notes/{note_id}",
    "/api/notes/{note_id}/archive",
    "/api/notes/{note_id}/restore",
    "/api/notes/{note_id}/unarchive",
    "/api/notes/{note_id}/permanent",
    "/api/notes/{note_id}/attachments",
    "/api/note-folders",
    "/api/graph",
)


def test_legacy_notes_routes_are_not_registered() -> None:
    """§42/A: eski CRUD yüzeyi kayıtlı değil; 410 router'ı da YOK."""
    paths = set(app.openapi()["paths"])
    assert not [path for path in paths if path in REMOVED_LEGACY_PATHS]
    assert not [path for path in paths if path.startswith("/api/note")]
    assert not [path for path in paths if path.startswith("/api/graph")]


def test_no_registered_route_writes_legacy_notes() -> None:
    """Hiçbir çalışma zamanı rotası legacy note tablolarına dokunmaz."""
    offenders: list[str] = []
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/note") or path == "/api/graph":
            offenders.append(path)
    assert offenders == []


def test_note_module_contributes_no_routes() -> None:
    """Modül kayıtlı kalır (şema + olay sözlüğü) ama HTTP yüzeyi üretmez."""
    assert note_module.router.routes == []
    # Şema kaydı için modeller hâlâ import edilebilir olmalı.
    from app.modules.note.models import Note as _Note  # noqa: F401


def test_vault_bridge_routes_exist() -> None:
    paths = set(app.openapi()["paths"])
    assert {
        "/api/obsidian/status",
        "/api/obsidian/index/refresh",
        "/api/obsidian/uri/search",
        "/api/obsidian/items/{forkos_id}",
        "/api/obsidian/capture",
        "/api/obsidian/ensure",
        "/api/projects/{project_id}/journal/{day}/obsidian",
        "/api/bookmarks/{bookmark_id}/source-note",
    } <= paths


def test_legacy_note_entity_types_are_not_live_knowledge() -> None:
    """§43: arşiv tipleri ne aranabilir ne linklenebilir."""
    for entity_type in ("note", "note_folder"):
        spec = type_spec(entity_type)
        assert spec is not None, f"{entity_type} tarihsel yönlendirme için kayıtlı kalmalı"
        assert spec.searchable is False
        assert spec.linkable is False
        assert spec.route.startswith("/activity")

    assert set(search_svc.searchable_types()).isdisjoint({"note", "note_folder"})


async def test_global_search_excludes_legacy_notes_but_keeps_operational_records() -> None:
    """§44: arama operasyonel kalır; arşiv notları sonuç dönmez."""
    from app.modules.note import service as note_service
    from app.modules.note.schemas import NoteIn

    async with SessionLocal() as session:
        await note_service.create(session, NoteIn(body="Kuantum arşiv notu"))
        operational = await create_entity(
            session, type="todo", title="Kuantum arşiv görevi", search_text="Kuantum arşiv görevi"
        )
        await session.commit()
        operational_id = operational.id

    async with SessionLocal() as session:
        hits = await search_svc.search_entities(session, "Kuantum")

    hit_types = {hit.type for hit in hits}
    ids = {hit.id for hit in hits}
    assert "note" not in hit_types
    assert operational_id in ids


async def test_related_panel_hides_archived_note_relations_only() -> None:
    """§45: legacy not bağları gizlenir; operasyonel ilişkiler KORUNUR."""
    from app.modules.note import service as note_service
    from app.modules.note.schemas import NoteIn

    async with SessionLocal() as session:
        project = await create_entity(session, type="project", title="İlişki projesi")
        session.add(Project(id=project.id, status="active", position=0))
        todo = await create_entity(session, type="todo", title="Bağlı görev")
        await link(session, todo.id, project.id, "belongs_to")
        note = await note_service.create(
            session, NoteIn(body="Projeye bağlı eski not", relate_to=project.id)
        )
        await session.commit()
        project_id, todo_id, note_id = project.id, todo.id, uuid.UUID(str(note.id))

    async with SessionLocal() as session:
        rows = await related(session, project_id)
        backlink_rows = await backlinks(session, project_id)

    related_ids = {uuid.UUID(row["entity"]["id"]) for row in rows}
    assert todo_id in related_ids
    assert note_id not in related_ids
    assert all(row["entity"]["type"] not in ARCHIVED_ENTITY_TYPES for row in rows)
    assert backlink_rows == []


async def test_maintenance_never_touches_the_frozen_archive() -> None:
    """§6: günlük bakımda Notlar adımı YOKTUR."""
    assert [name for name, _ in maintenance.STEPS] == ["retention", "rss"]

    from app.modules.note import service as note_service
    from app.modules.note.schemas import NoteIn

    async with SessionLocal() as session:
        await note_service.create(session, NoteIn(body="Bakım görmemeli"))
        await session.commit()

    async def counts() -> tuple[int, int, int]:
        async with SessionLocal() as session:
            return (
                int((await session.execute(select(func.count()).select_from(Note))).scalar_one()),
                int(
                    (await session.execute(select(func.count()).select_from(NoteFolder))).scalar_one()
                ),
                int(
                    (await session.execute(select(func.count()).select_from(NoteAttachment))).scalar_one()
                ),
            )

    before = await counts()
    async with SessionLocal() as session:
        summary = await maintenance.run_maintenance(
            session, now=datetime.now(UTC), force=True
        )
    assert summary is not None
    assert "attachments" not in summary["results"]
    assert await counts() == before


async def test_maintenance_does_not_emit_note_events() -> None:
    async with SessionLocal() as session:
        await maintenance.run_maintenance(session, now=datetime.now(UTC), force=True)

    async with SessionLocal() as session:
        verbs = list((await session.execute(select(Event.verb))).scalars())

    assert not [verb for verb in verbs if verb.startswith("note.")]


def test_migration_tooling_and_archive_tables_still_present() -> None:
    """§5/§7: fiziksel arşiv ve göç aracı yerinde kalır."""
    from app.db import Base
    from app.integrations.obsidian.migration import engine  # noqa: F401
    from app.integrations.obsidian.migration.manifest import MANIFEST_DIR  # noqa: F401
    from app.modules.note import storage as attachment_storage

    assert attachment_storage.ATTACHMENTS_DIR.name == "attachments"
    assert {"note", "note_folder", "note_attachment"} <= set(Base.metadata.tables)


def test_obsidian_service_exposes_knowledge_api() -> None:
    """§9: bilgi API'si tek merkezde ve gerekli yetenekleri taşır."""
    from app.integrations.obsidian import service

    for name in (
        "capture_knowledge_note",
        "create_managed_note",
        "ensure_entity_knowledge_note",
        "ensure_project_journal",
        "get_vault_status",
        "read_managed_note_body",
        "refresh_vault_index",
        "resolve_managed_item",
        "update_managed_note_body",
        "vault_search_uri",
    ):
        assert callable(getattr(service, name)), name

    assert vault_index.get_managed_count() == 0


@pytest.mark.no_database
def test_uri_helpers_are_centralized_and_encoded() -> None:
    """§18: URI'ler tek yerde üretilir ve parametreler kaçışlanır."""
    from app.integrations.obsidian.uri import (
        daily_note_uri,
        open_file_uri,
        open_vault_uri,
        search_uri,
    )

    assert open_vault_uri("Kasa Adı") == "obsidian://open?vault=Kasa%20Ad%C4%B1"
    assert daily_note_uri("Kasa") == "obsidian://daily?vault=Kasa"
    assert search_uri("Kasa", 'a&b "c"') == "obsidian://search?vault=Kasa&query=a%26b%20%22c%22"
    assert open_file_uri("Kasa", "10 Daily/2026-09-20.md") == (
        "obsidian://open?vault=Kasa&file=10%20Daily/2026-09-20"
    )
