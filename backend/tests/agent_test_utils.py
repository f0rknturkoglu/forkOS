"""H1 test desteği: mutasyon kapsamı ve değişmezlik kanıtları için ortak araçlar.

Bu modül `test_*.py` DEĞİLDİR (pytest toplamaz); test dosyaları buradan
import eder. H0'un "hiçbir şey değişmedi" kanıtı ile H1'in "yalnızca beklenen
domain değişti" kanıtı aynı ölçümü kullanır -- böylece iki fazın kanıtı
karşılaştırılabilir kalır.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity, Event, Link, Notification
from app.modules.bookmark.models import Bookmark
from app.modules.flashcard.models import FlashcardCard
from app.modules.note.models import Note, NoteAttachment, NoteFolder
from app.modules.opportunity.models import Application, Opportunity
from app.modules.project.models import Milestone, Project
from app.modules.todo.models import Todo


async def capture_db_content_fingerprint(session: AsyncSession) -> str:
    """Kritik tablolardaki SEÇİLMİŞ canonical alanların deterministik özeti.

    Not: bu, satırların her kolonunu baytı baytına özetleyen bir kanıt
    DEĞİLDİR; kapsam bilinçli olarak seçilmiş alanlardır (bkz. H0 dokümanı).
    """
    hasher = hashlib.sha256()

    rows = (
        await session.execute(
            select(Entity.id, Entity.type, Entity.title, Entity.search_text, Entity.archived_at)
            .order_by(Entity.id)
        )
    ).all()
    hasher.update(str(rows).encode("utf-8"))

    rows = (
        await session.execute(
            select(Event.id, Event.entity_id, Event.verb, Event.payload, Event.occurred_at)
            .order_by(Event.id)
        )
    ).all()
    hasher.update(str(rows).encode("utf-8"))

    rows = (
        await session.execute(
            select(Link.from_id, Link.to_id, Link.relation, Link.created_at)
            .order_by(Link.from_id, Link.to_id, Link.relation)
        )
    ).all()
    hasher.update(str(rows).encode("utf-8"))

    rows = (
        await session.execute(
            select(Todo.id, Todo.status, Todo.priority, Todo.due_at, Todo.completed_at)
            .order_by(Todo.id)
        )
    ).all()
    hasher.update(str(rows).encode("utf-8"))

    rows = (
        await session.execute(
            select(Project.id, Project.status, Project.next_action, Project.github_repo, Project.stack)
            .order_by(Project.id)
        )
    ).all()
    hasher.update(str(rows).encode("utf-8"))

    rows = (
        await session.execute(
            select(
                Milestone.id,
                Milestone.project_id,
                Milestone.title,
                Milestone.due_at,
                Milestone.completed_at,
            ).order_by(Milestone.id)
        )
    ).all()
    hasher.update(str(rows).encode("utf-8"))

    rows = (
        await session.execute(
            select(
                Notification.id,
                Notification.title,
                Notification.body,
                Notification.read_at,
                Notification.dismissed_at,
            ).order_by(Notification.id)
        )
    ).all()
    hasher.update(str(rows).encode("utf-8"))

    rows = (
        await session.execute(
            select(
                Opportunity.id,
                Opportunity.kind,
                Opportunity.status,
                Opportunity.organization,
                Opportunity.deadline_at,
            ).order_by(Opportunity.id)
        )
    ).all()
    hasher.update(str(rows).encode("utf-8"))

    rows = (
        await session.execute(
            select(
                Application.opportunity_id, Application.status, Application.status_changed_at
            ).order_by(Application.opportunity_id)
        )
    ).all()
    hasher.update(str(rows).encode("utf-8"))

    rows = (
        await session.execute(
            select(FlashcardCard.id, FlashcardCard.deck_id, FlashcardCard.reps, FlashcardCard.due_at)
            .order_by(FlashcardCard.id)
        )
    ).all()
    hasher.update(str(rows).encode("utf-8"))

    rows = (
        await session.execute(
            select(Bookmark.id, Bookmark.collection, Bookmark.url, Bookmark.read_status)
            .order_by(Bookmark.id)
        )
    ).all()
    hasher.update(str(rows).encode("utf-8"))

    rows = (
        await session.execute(
            select(Note.id, Note.folder_id, Note.project_id, Note.pinned, Note.body)
            .order_by(Note.id)
        )
    ).all()
    hasher.update(str(rows).encode("utf-8"))

    rows = (
        await session.execute(
            select(NoteFolder.id, NoteFolder.parent_id, NoteFolder.position).order_by(NoteFolder.id)
        )
    ).all()
    hasher.update(str(rows).encode("utf-8"))

    return hasher.hexdigest()


def capture_vault_fingerprint(vault_dir: Path) -> dict[str, tuple[str, float]]:
    """Vault içindeki her dosyanın sha256 + mtime kaydı."""
    fingerprints: dict[str, tuple[str, float]] = {}
    for root, _, files in os.walk(vault_dir):
        for name in files:
            path = Path(root) / name
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                rel = str(path.relative_to(vault_dir))
                fingerprints[rel] = (digest, os.path.getmtime(path))
            except OSError:
                continue
    return fingerprints


async def legacy_notes_counts(session: AsyncSession) -> dict[str, int]:
    """Dondurulmuş legacy Notlar arşivinin satır sayıları (§120 invaryantı)."""
    return {
        "note": int((await session.execute(select(func.count()).select_from(Note))).scalar_one()),
        "note_folder": int(
            (await session.execute(select(func.count()).select_from(NoteFolder))).scalar_one()
        ),
        "note_attachment": int(
            (await session.execute(select(func.count()).select_from(NoteAttachment))).scalar_one()
        ),
    }


async def table_counts(session: AsyncSession) -> dict[str, int]:
    """Mutasyon kapsamı kanıtı için hedef tablo sayıları."""
    return {
        "entity": int(
            (await session.execute(select(func.count()).select_from(Entity))).scalar_one()
        ),
        "todo": int((await session.execute(select(func.count()).select_from(Todo))).scalar_one()),
        "project": int(
            (await session.execute(select(func.count()).select_from(Project))).scalar_one()
        ),
        "milestone": int(
            (await session.execute(select(func.count()).select_from(Milestone))).scalar_one()
        ),
        "opportunity": int(
            (await session.execute(select(func.count()).select_from(Opportunity))).scalar_one()
        ),
        "application": int(
            (await session.execute(select(func.count()).select_from(Application))).scalar_one()
        ),
        "bookmark": int(
            (await session.execute(select(func.count()).select_from(Bookmark))).scalar_one()
        ),
        "flashcard_card": int(
            (await session.execute(select(func.count()).select_from(FlashcardCard))).scalar_one()
        ),
        "event": int((await session.execute(select(func.count()).select_from(Event))).scalar_one()),
    }


def _build_table_selects() -> dict[str, Any]:
    from app.core.models import EntityTag
    from app.modules.opportunity.models import ApplicationHistory
    from app.modules.todo.models import PlanSlot

    return {
        "entity": select(Entity.id, Entity.title, Entity.updated_at, Entity.archived_at).order_by(
            Entity.id
        ),
        "entity_tag": select(EntityTag.entity_id, EntityTag.tag_id).order_by(
            EntityTag.entity_id, EntityTag.tag_id
        ),
        "todo": select(
            Todo.id, Todo.status, Todo.priority, Todo.due_at, Todo.completed_at, Todo.recur
        ).order_by(Todo.id),
        "plan_slot": select(
            PlanSlot.entity_id, PlanSlot.day, PlanSlot.start_min, PlanSlot.duration_min
        ).order_by(PlanSlot.entity_id, PlanSlot.day),
        "project": select(Project.id, Project.status, Project.next_action).order_by(Project.id),
        "milestone": select(
            Milestone.id, Milestone.title, Milestone.due_at, Milestone.completed_at
        ).order_by(Milestone.id),
        "opportunity": select(
            Opportunity.id, Opportunity.kind, Opportunity.status, Opportunity.rejection_reason
        ).order_by(Opportunity.id),
        "application": select(
            Application.opportunity_id, Application.status, Application.status_changed_at
        ).order_by(Application.opportunity_id),
        "application_history": select(
            ApplicationHistory.id,
            ApplicationHistory.opportunity_id,
            ApplicationHistory.from_status,
            ApplicationHistory.to_status,
            ApplicationHistory.scope,
        ).order_by(ApplicationHistory.id),
        "bookmark": select(
            Bookmark.id, Bookmark.url, Bookmark.collection, Bookmark.read_status, Bookmark.favorite
        ).order_by(Bookmark.id),
        "flashcard_card": select(
            FlashcardCard.id, FlashcardCard.reps, FlashcardCard.due_at
        ).order_by(FlashcardCard.id),
        "note": select(
            Note.id, Note.body, Note.pinned, Note.trashed_at, Note.journal_day
        ).order_by(Note.id),
        "note_folder": select(NoteFolder.id, NoteFolder.parent_id, NoteFolder.position).order_by(
            NoteFolder.id
        ),
        "link": select(Link.from_id, Link.to_id, Link.relation, Link.created_at).order_by(
            Link.from_id, Link.to_id, Link.relation
        ),
        "event": select(Event.id, Event.verb, Event.entity_id, Event.occurred_at).order_by(Event.id),
    }


async def table_fingerprints(session: AsyncSession) -> dict[str, str]:
    """Her kritik tablo için AYRI deterministik özet.

    Mutasyon kapsamı kanıtı bunu kullanır: bir eylem yalnızca beklenen
    tabloların özetini değiştirmelidir (§73).
    """
    selects = _build_table_selects()
    fingerprints: dict[str, str] = {}
    for name, stmt in selects.items():
        rows = (await session.execute(stmt)).all()
        fingerprints[name] = hashlib.sha256(str(rows).encode("utf-8")).hexdigest()
    return fingerprints


def changed_tables(before: dict[str, str], after: dict[str, str]) -> set[str]:
    return {name for name in before if before[name] != after.get(name)}


@pytest.fixture(autouse=True)
def forbid_h1_network(monkeypatch: pytest.MonkeyPatch):
    """§118: H1 testleri sırasında beklenmeyen AĞ erişimini test hatasına çevirir.

    Yerel-only sözleşmesi yalnızca dokümanda kalmamalı: bir H1 eylemi dış
    servise istek atarsa (httpx, source adapter, enrichment, GitHub) test
    yüzeye çıkarır. Kullanan modüller bu fixture'ı import eder.
    """
    import httpx

    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("H1 eylemi dış ağ çağrısı yapmamalı")

    for attribute in ("AsyncClient", "Client", "get", "post", "put", "patch", "delete"):
        monkeypatch.setattr(httpx, attribute, _boom, raising=False)

    from app.core import readability

    monkeypatch.setattr(readability, "fetch_and_extract", _boom)
    yield
