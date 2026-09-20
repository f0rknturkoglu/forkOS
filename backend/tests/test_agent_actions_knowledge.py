"""H1 bilgi (Vault) yazma adaptörleri.

Kanıtlananlar: yazma yalnızca Obsidian Vault'a gider (legacy Notlar'a sıfır
yazma), hedef kimliği `forkos_id`'dir (yol değil), ekleme yapılır (tam gövde
değiştirilmez), kullanıcı Markdown'ı ve frontmatter'ı korunur, bayat yazma
fail-closed davranır.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import Entity, Link
from app.db import SessionLocal
from app.integrations.agent.actions import (
    ActionError,
    capture_brain_note,
    save_to_entity_brain,
)
from app.integrations.agent.write_models import BrainCaptureIn, BrainSaveToEntityIn
from app.integrations.obsidian.frontmatter import parse_frontmatter
from app.integrations.obsidian.service import vault_index
from tests.agent_test_utils import legacy_notes_counts, table_counts


@pytest.fixture(autouse=True)
def reset_vault_index():
    def clear() -> None:
        vault_index._items.clear()
        vault_index._conflicts.clear()
        vault_index._invalid_files.clear()
        vault_index._last_scanned = None
        vault_index._last_status = None
        vault_index._last_root = None

    clear()
    yield
    clear()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "AgentVault"
    path.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "AgentVault")
    return path


async def _make_project(session: AsyncSession, title: str = "Roadmap Project") -> uuid.UUID:
    project_id = uuid.uuid4()
    session.add(Entity(id=project_id, type="project", title=title, search_text=""))
    await session.commit()
    return project_id


# ---------------------------------------------------------------------------
# brain_capture
# ---------------------------------------------------------------------------


async def test_capture_brain_note_writes_inbox_file_without_database_rows(
    db_session: AsyncSession, vault: Path
) -> None:
    before_tables = await table_counts(db_session)
    before_legacy = await legacy_notes_counts(db_session)

    receipt = await capture_brain_note(
        db_session,
        BrainCaptureIn(body="Toplantı notu: H1 sınırı korunacak.", title="H1 toplantısı"),
        request_id="k1",
    )

    assert receipt.status == "executed"
    assert receipt.tool == "brain_capture"
    assert receipt.target_type == "vault_note"
    assert receipt.target_id == receipt.after["forkos_id"]
    assert receipt.after["relative_path"] == "00 Inbox/H1 toplantısı.md"
    assert receipt.after["note_kind"] == "personal"
    # §129: gövde makbuza kopyalanmaz.
    assert "Toplantı notu" not in str(receipt.after)

    written = vault / receipt.after["relative_path"]
    assert written.is_file()
    metadata, body = parse_frontmatter(written.read_text(encoding="utf-8"))
    assert metadata is not None
    assert metadata["forkos_type"] == "note"
    assert metadata["forkos_note_kind"] == "personal"
    assert metadata["forkos_captured_from"] == "forkOS"
    assert "Toplantı notu" in body

    # §46/§82: forkOS veritabanı DEĞİŞMEZ.
    assert await table_counts(db_session) == before_tables
    # §120: legacy Notlar arşivine sıfır yazma.
    assert await legacy_notes_counts(db_session) == before_legacy


async def test_capture_brain_note_relation_is_metadata_only(
    db_session: AsyncSession, vault: Path
) -> None:
    """§47: ilişki hedefi sunucuda çözülür; istemcinin tip/başlığına güvenilmez."""
    project_id = await _make_project(db_session, "Hermes")
    before_tables = await table_counts(db_session)

    receipt = await capture_brain_note(
        db_session,
        BrainCaptureIn(body="Karar: semantic araçlar.", relate_to=str(project_id)),
    )

    metadata, _ = parse_frontmatter(
        (vault / receipt.after["relative_path"]).read_text(encoding="utf-8")
    )
    assert metadata is not None
    assert metadata["forkos_relations"] == [
        {
            "relation": "notes_about",
            "target_id": str(project_id),
            "target_type": "project",
            "target_title": "Hermes",
        }
    ]
    # İlişki DB'ye `link` satırı olarak YAZILMAZ (§46).
    assert await table_counts(db_session) == before_tables


async def test_capture_brain_note_unknown_relation_fails(
    db_session: AsyncSession, vault: Path
) -> None:
    with pytest.raises(ActionError, match="INVALID_TARGET"):
        await capture_brain_note(
            db_session, BrainCaptureIn(body="Yetim", relate_to=str(uuid.uuid4()))
        )
    assert not list(vault.rglob("*.md"))


async def test_capture_brain_note_fails_closed_when_vault_unavailable(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§54/§68: Vault yoksa legacy Notlar'a DÜŞÜLMEZ."""
    monkeypatch.setattr(settings, "obsidian_vault_path", "")
    before_legacy = await legacy_notes_counts(db_session)

    with pytest.raises(ActionError, match="VAULT_UNAVAILABLE"):
        await capture_brain_note(db_session, BrainCaptureIn(body="Yazılamamalı"))

    assert await legacy_notes_counts(db_session) == before_legacy


async def test_capture_brain_note_validation_bounds() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        BrainCaptureIn(body="   ")
    with pytest.raises(ValidationError):
        BrainCaptureIn(body="x" * 40001)
    with pytest.raises(ValidationError):
        BrainCaptureIn(body="ok", relate_to="not-a-uuid")


# ---------------------------------------------------------------------------
# brain_save_to_entity
# ---------------------------------------------------------------------------


async def test_save_to_entity_appends_without_replacing_user_content(
    db_session: AsyncSession, vault: Path
) -> None:
    project_id = await _make_project(db_session, "forkOS")
    before_legacy = await legacy_notes_counts(db_session)

    first = await save_to_entity_brain(
        db_session,
        BrainSaveToEntityIn(forkos_id=str(project_id), text="İlk karar: append-only."),
        request_id="s1",
    )
    assert first.status == "executed"
    assert first.target_id == str(project_id)
    assert first.changed_fields == ["body"]

    path = vault / first.after["relative_path"]
    # §50: not yoksa canonical `ensure` ile oluşturulur.
    assert path.is_file()
    text_after_first = path.read_text(encoding="utf-8")
    assert "İlk karar: append-only." in text_after_first
    # Proje şablonu (canonical varsayılan gövde) korunur.
    assert "## Amaç" in text_after_first

    # Kullanıcı Obsidian'da kendi frontmatter alanını ekledi.
    path.write_text(
        text_after_first.replace("forkos_type: project", "forkos_type: project\nkullanici_alani: korunmalı"),
        encoding="utf-8",
    )
    # İndeks tazelenir ki mtime güncel okunsun (kullanıcı düzenlemesi).
    from app.integrations.obsidian.service import refresh_vault_index

    refresh_vault_index()

    second = await save_to_entity_brain(
        db_session,
        BrainSaveToEntityIn(forkos_id=str(project_id), text="İkinci karar."),
    )
    assert second.status == "executed"

    final = path.read_text(encoding="utf-8")
    assert "İlk karar: append-only." in final  # önceki içerik SİLİNMEDİ (§51)
    assert "İkinci karar." in final
    metadata, _ = parse_frontmatter(final)
    assert metadata is not None
    assert metadata["kullanici_alani"] == "korunmalı"  # §52
    assert metadata["forkos_id"] == str(project_id)

    assert await legacy_notes_counts(db_session) == before_legacy


async def test_save_to_entity_appends_under_exact_heading(
    db_session: AsyncSession, vault: Path
) -> None:
    project_id = await _make_project(db_session, "Başlıklı proje")
    created = await save_to_entity_brain(
        db_session, BrainSaveToEntityIn(forkos_id=str(project_id), text="başlangıç")
    )
    path = vault / created.after["relative_path"]

    receipt = await save_to_entity_brain(
        db_session,
        BrainSaveToEntityIn(
            forkos_id=str(project_id), text="Karar: tek yazma sınırı.", heading="Amaç"
        ),
    )
    assert receipt.status == "executed"
    assert receipt.after["heading"] == "Amaç"

    body = path.read_text(encoding="utf-8")
    assert "Karar: tek yazma sınırı." in body
    # Diğer bölüm başlıkları korunur (§52: yeniden biçimlendirme yok).
    assert "## Kararlar" in body and "## Referanslar" in body


async def test_save_to_entity_heading_errors_are_explicit(
    db_session: AsyncSession, vault: Path
) -> None:
    project_id = await _make_project(db_session, "Başlık hataları")
    await save_to_entity_brain(
        db_session, BrainSaveToEntityIn(forkos_id=str(project_id), text="gövde")
    )

    with pytest.raises(ActionError, match="HEADING_NOT_FOUND"):
        await save_to_entity_brain(
            db_session,
            BrainSaveToEntityIn(forkos_id=str(project_id), text="x", heading="Olmayan Başlık"),
        )

    # Aynı başlığı iki kez ekleyip belirsizlik yarat.
    created = await save_to_entity_brain(
        db_session,
        BrainSaveToEntityIn(forkos_id=str(project_id), text="tek", heading="Amaç"),
    )
    path = vault / created.after["relative_path"]
    path.write_text(
        path.read_text(encoding="utf-8").replace("## Kararlar", "## Amaç"),
        encoding="utf-8",
    )
    from app.integrations.obsidian.service import refresh_vault_index

    refresh_vault_index()

    with pytest.raises(ActionError, match="AMBIGUOUS_HEADING"):
        await save_to_entity_brain(
            db_session,
            BrainSaveToEntityIn(forkos_id=str(project_id), text="y", heading="Amaç"),
        )


async def test_save_to_entity_stale_write_fails_closed(
    db_session: AsyncSession, vault: Path
) -> None:
    """§18/§51: kullanıcı düzenlemesi ezilmez."""
    project_id = await _make_project(db_session, "Bayat proje")
    created = await save_to_entity_brain(
        db_session, BrainSaveToEntityIn(forkos_id=str(project_id), text="ilk")
    )
    path = vault / created.after["relative_path"]
    original = path.read_text(encoding="utf-8")

    # Dosya, indeksin gördüğü andan SONRA değişti.
    stat = path.stat()
    os.utime(path, (stat.st_atime + 30, stat.st_mtime + 30))

    with pytest.raises(ActionError, match="VAULT_STALE"):
        await save_to_entity_brain(
            db_session, BrainSaveToEntityIn(forkos_id=str(project_id), text="ezilmemeli")
        )

    assert path.read_text(encoding="utf-8") == original


async def test_save_to_entity_unknown_entity_fails(db_session: AsyncSession, vault: Path) -> None:
    with pytest.raises(ActionError, match="INVALID_TARGET"):
        await save_to_entity_brain(
            db_session, BrainSaveToEntityIn(forkos_id=str(uuid.uuid4()), text="yok")
        )
    assert not list(vault.rglob("*.md"))


async def test_save_to_entity_cannot_target_a_path() -> None:
    """§49/§55: şemada `relative_path` YOKTUR; kullanıcı notu yazılamaz."""
    from pydantic import ValidationError

    assert "relative_path" not in BrainSaveToEntityIn.model_fields
    with pytest.raises(ValidationError):
        BrainSaveToEntityIn.model_validate(
            {"forkos_id": str(uuid.uuid4()), "text": "x", "relative_path": "30 Knowledge/Human.md"}
        )


async def test_brain_writes_never_create_links_or_note_rows(
    db_session: AsyncSession, vault: Path
) -> None:
    from sqlalchemy import func, select

    project_id = await _make_project(db_session, "Sınır projesi")
    before_legacy = await legacy_notes_counts(db_session)

    await capture_brain_note(db_session, BrainCaptureIn(body="yakalama"))
    await save_to_entity_brain(
        db_session, BrainSaveToEntityIn(forkos_id=str(project_id), text="ekleme")
    )

    links = int((await db_session.execute(select(func.count()).select_from(Link))).scalar_one())
    assert links == 0
    assert await legacy_notes_counts(db_session) == before_legacy
    # İki dosya: biri Inbox yakalaması, biri proje bilgi notu.
    assert len(list(vault.rglob("*.md"))) == 2
