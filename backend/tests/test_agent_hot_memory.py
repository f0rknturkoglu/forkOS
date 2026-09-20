"""H2 sıcak hafıza: depolama ve adaptör doğruluğu.

Kanıtlanan sözleşmeler: öğe başına tek dosya, sunucu üretimi UUID kimliği,
içerik revizyonu, emeklilik ≠ silme, zaman aşımı salt okuma anında, sınırlı
bağlam bütçesi, kimlik çakışmasında fail-closed, sır reddi, yol güvenliği ve
okumaların değişmezliği.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import Entity
from app.db import SessionLocal
from app.integrations.agent import hot_memory as hm
from app.integrations.agent.hot_memory_models import (
    HotMemoryRetireIn,
    HotMemoryStoreIn,
    HotMemoryUpdateIn,
)
from app.integrations.obsidian import hot_memory as storage
from tests.agent_test_utils import (
    capture_db_content_fingerprint,
    capture_vault_fingerprint,
    forbid_outbound_network,  # noqa: F401  (autouse: H2 de yereldir)
    legacy_notes_counts,
)

MEMORY_DIR = "90 Agent/Memory"


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "HotMemoryVault"
    path.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "HotMemoryVault")
    return path


async def _store(session, **overrides):
    payload = {
        "kind": "preference",
        "title": "Planning style",
        "text": "Prefers project-level plans over hourly schedules.",
        "importance": 2,
        "source_mode": "explicit_user",
    }
    payload.update(overrides)
    return await hm.store_memory(session, HotMemoryStoreIn(**payload), request_id="t")


def _memory_files(vault: Path) -> list[Path]:
    directory = vault / MEMORY_DIR
    return sorted(directory.glob("*.md")) if directory.is_dir() else []


# ---------------------------------------------------------------------------
# §101 — store
# ---------------------------------------------------------------------------


async def test_store_creates_one_file_without_touching_anything_else(
    db_session: AsyncSession, vault: Path
) -> None:
    unrelated = vault / "20 Projects" / "Note.md"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("kullanıcı içeriği", encoding="utf-8")

    db_before = await capture_db_content_fingerprint(db_session)
    legacy_before = await legacy_notes_counts(db_session)

    receipt = await _store(db_session)

    assert receipt.status == "executed"
    assert receipt.tool == "hot_memory_store"
    assert receipt.target_type == "hot_memory"
    assert uuid.UUID(receipt.target_id)
    assert receipt.after["relative_path"] == f"{MEMORY_DIR}/{receipt.target_id}.md"
    # §98: gövde makbuza kopyalanmaz.
    assert "hourly schedules" not in json.dumps(receipt.after)
    # §131: yalnızca GÖRELİ yol döner; mutlak yol ya da üst dizin gezinmesi yok.
    assert not receipt.after["relative_path"].startswith("/")
    assert ".." not in receipt.after["relative_path"]

    files = _memory_files(vault)
    assert len(files) == 1
    assert files[0].name == f"{receipt.target_id}.md"
    assert "hourly schedules" in files[0].read_text(encoding="utf-8")

    # Yalnızca hedef dosya oluştu; DB ve legacy arşiv DEĞİŞMEDİ.
    assert unrelated.read_text(encoding="utf-8") == "kullanıcı içeriği"
    assert await capture_db_content_fingerprint(db_session) == db_before
    assert await legacy_notes_counts(db_session) == legacy_before


# ---------------------------------------------------------------------------
# §102 — kesin tekrar
# ---------------------------------------------------------------------------


async def test_exact_duplicate_store_is_noop(db_session: AsyncSession, vault: Path) -> None:
    first = await _store(db_session)
    fingerprint = await capture_db_content_fingerprint(db_session)
    files_before = capture_vault_fingerprint(vault)

    # Aynı tür + aynı normalize edilmiş metin.
    second = await _store(db_session, title="Başka başlık")

    assert first.status == "executed"
    assert second.status == "noop"
    assert second.target_id == first.target_id
    assert second.warnings
    assert len(_memory_files(vault)) == 1
    assert capture_vault_fingerprint(vault) == files_before
    assert await capture_db_content_fingerprint(db_session) == fingerprint


# ---------------------------------------------------------------------------
# §103 — update
# ---------------------------------------------------------------------------


async def test_update_preserves_unknown_frontmatter_and_identity(
    db_session: AsyncSession, vault: Path
) -> None:
    created = await _store(db_session)
    path = vault / created.after["relative_path"]

    # Kullanıcı Obsidian'da kendi alanını ekledi.
    raw = path.read_text(encoding="utf-8")
    path.write_text(raw.replace("tags: []", "tags: []\nkullanici_alani: korunmali"), encoding="utf-8")

    snapshot = storage.scan_memories(vault.resolve())
    record = storage.find_memory(snapshot, created.target_id)
    assert record is not None

    receipt = await hm.update_memory(
        db_session,
        HotMemoryUpdateIn(
            memory_id=created.target_id,
            expected_revision=record.revision,
            title="Yeni başlık",
            importance=3,
        ),
    )

    assert receipt.status == "executed"
    assert receipt.target_id == created.target_id
    assert set(receipt.changed_fields) >= {"title", "importance", "revision"}
    final = path.read_text(encoding="utf-8")
    assert "kullanici_alani: korunmali" in final
    assert "hourly schedules" in final  # metin korundu
    assert len(_memory_files(vault)) == 1


async def test_update_omitted_field_preserved_and_null_clears(
    db_session: AsyncSession, vault: Path
) -> None:
    future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    created = await _store(db_session, expires_at=future, tags=["a", "b"])
    snapshot = storage.scan_memories(vault.resolve())
    record = storage.find_memory(snapshot, created.target_id)
    assert record is not None and record.expires_at == future

    # Yalnızca başlık: süre ve etiketler KORUNUR.
    only_title = await hm.update_memory(
        db_session,
        HotMemoryUpdateIn(
            memory_id=created.target_id, expected_revision=record.revision, title="Yalnızca başlık"
        ),
    )
    assert only_title.status == "executed"
    snapshot = storage.scan_memories(vault.resolve())
    record = storage.find_memory(snapshot, created.target_id)
    assert record is not None
    assert record.expires_at == future
    assert sorted(record.tags) == ["a", "b"]

    # Açık null: süre TEMİZLENİR.
    cleared = await hm.update_memory(
        db_session,
        HotMemoryUpdateIn(
            memory_id=created.target_id, expected_revision=record.revision, expires_at=None
        ),
    )
    assert cleared.status == "executed"
    snapshot = storage.scan_memories(vault.resolve())
    record = storage.find_memory(snapshot, created.target_id)
    assert record is not None and record.expires_at is None
    assert sorted(record.tags) == ["a", "b"]


async def test_update_with_no_effective_change_is_noop(
    db_session: AsyncSession, vault: Path
) -> None:
    created = await _store(db_session)
    snapshot = storage.scan_memories(vault.resolve())
    record = storage.find_memory(snapshot, created.target_id)
    assert record is not None
    before = capture_vault_fingerprint(vault)

    receipt = await hm.update_memory(
        db_session,
        HotMemoryUpdateIn(
            memory_id=created.target_id, expected_revision=record.revision, title=record.title
        ),
    )

    assert receipt.status == "noop"
    # §63: updated_at tazelemek için dosya YENİDEN YAZILMAZ.
    assert capture_vault_fingerprint(vault) == before


# ---------------------------------------------------------------------------
# §105 — bayat revizyon
# ---------------------------------------------------------------------------


async def test_stale_revision_blocks_update_and_preserves_human_edit(
    db_session: AsyncSession, vault: Path
) -> None:
    created = await _store(db_session)
    path = vault / created.after["relative_path"]
    snapshot = storage.scan_memories(vault.resolve())
    record = storage.find_memory(snapshot, created.target_id)
    assert record is not None
    stale_revision = record.revision

    # Kullanıcı elle düzenledi.
    human = path.read_text(encoding="utf-8").replace("hourly schedules", "elle düzenlenmiş")
    path.write_text(human, encoding="utf-8")
    db_before = await capture_db_content_fingerprint(db_session)

    with pytest.raises(hm.ActionError, match="HOT_MEMORY_STALE"):
        await hm.update_memory(
            db_session,
            HotMemoryUpdateIn(
                memory_id=created.target_id, expected_revision=stale_revision, title="Yazılmamalı"
            ),
        )

    assert path.read_text(encoding="utf-8") == human
    assert await capture_db_content_fingerprint(db_session) == db_before


# ---------------------------------------------------------------------------
# §106 — emeklilik
# ---------------------------------------------------------------------------


async def test_retire_removes_from_context_without_deleting_file(
    db_session: AsyncSession, vault: Path
) -> None:
    created = await _store(db_session)
    assert hm.get_context().returned_total == 1

    snapshot = storage.scan_memories(vault.resolve())
    record = storage.find_memory(snapshot, created.target_id)
    assert record is not None

    receipt = await hm.retire_memory(
        db_session,
        HotMemoryRetireIn(
            memory_id=created.target_id, expected_revision=record.revision, reason="geçersiz"
        ),
    )
    assert receipt.status == "executed"
    assert receipt.changed_fields == ["status"]
    assert any("silme değildir" in w for w in receipt.warnings)

    assert hm.get_context().returned_total == 0
    retired = hm.list_memories(effective_status="retired")
    assert [item.memory_id for item in retired.items] == [created.target_id]
    assert (vault / created.after["relative_path"]).is_file()

    # İkinci emeklilik: noop, yeniden yazma yok.
    before = capture_vault_fingerprint(vault)
    snapshot = storage.scan_memories(vault.resolve())
    record = storage.find_memory(snapshot, created.target_id)
    assert record is not None
    again = await hm.retire_memory(
        db_session,
        HotMemoryRetireIn(memory_id=created.target_id, expected_revision=record.revision),
    )
    assert again.status == "noop"
    assert capture_vault_fingerprint(vault) == before


# ---------------------------------------------------------------------------
# §107 — zaman aşımı
# ---------------------------------------------------------------------------


async def test_expiry_is_computed_at_read_time(
    db_session: AsyncSession, vault: Path
) -> None:
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    created = await _store(db_session, expires_at=past)
    path = vault / created.after["relative_path"]
    before = capture_vault_fingerprint(vault)

    assert hm.get_context().returned_total == 0
    listed = hm.list_memories(effective_status="expired")
    assert [item.memory_id for item in listed.items] == [created.target_id]
    assert listed.items[0].effective_status == "expired"
    assert listed.items[0].status == "active"

    # Okuma hiçbir şeyi değiştirmedi (arka plan zaman aşımı işçisi yok).
    assert capture_vault_fingerprint(vault) == before
    assert path.is_file()


# ---------------------------------------------------------------------------
# §108/§109 — bütçe, sıralama, türler
# ---------------------------------------------------------------------------


async def test_context_budget_truncates_deterministically(
    db_session: AsyncSession, vault: Path
) -> None:
    # preference için tür tavanı 6; 9 tane üretip tavanı test ediyoruz.
    for index in range(9):
        await _store(
            db_session,
            title=f"Tercih {index}",
            text=f"Tercih metni {index} " + "x" * 50,
            importance=1 + (index % 3),
        )

    context = hm.get_context()
    assert len(context.preferences) == hm.KIND_CAPS["preference"] == 6
    assert context.active_total == 9
    assert context.returned_total == 6
    assert context.omitted_total == 3
    assert context.truncated is True

    # Sıralama: importance ↓, sonra updated_at ↓.
    importances = [item.importance for item in context.preferences]
    assert importances == sorted(importances, reverse=True)

    # Ölçek küçük: metin bütçesi aşılmadı.
    assert sum(len(item.text) for item in context.preferences) <= hm.CONTEXT_CHAR_BUDGET


async def test_all_kinds_store_and_list(db_session: AsyncSession, vault: Path) -> None:
    for kind in ("profile", "preference", "goal", "constraint", "decision"):
        receipt = await _store(
            db_session, kind=kind, title=f"{kind} başlık", text=f"{kind} metni"
        )
        assert receipt.status == "executed"

    context = hm.get_context()
    assert len(context.profile) == 1
    assert len(context.preferences) == 1
    assert len(context.goals) == 1
    assert len(context.constraints) == 1
    assert len(context.decisions) == 1
    assert context.returned_total == 5

    with pytest.raises(ValidationError):
        HotMemoryStoreIn(
            kind="gecersiz_tur", title="x", text="y", source_mode="explicit_user"
        )


# ---------------------------------------------------------------------------
# §110/§111 — bozuk dosya ve kimlik çakışması
# ---------------------------------------------------------------------------


async def test_invalid_memory_file_is_reported_not_repaired(
    db_session: AsyncSession, vault: Path
) -> None:
    directory = vault / MEMORY_DIR
    directory.mkdir(parents=True)
    broken = directory / "bozuk.md"
    broken.write_text("---\nmemory_id: not-a-uuid\n---\ngövde\n", encoding="utf-8")
    original = broken.read_text(encoding="utf-8")

    await _store(db_session)  # geçerli kayıt yanında bozuk dosya uygulamayı düşürmemeli

    context = hm.get_context()
    assert context.returned_total == 1
    assert context.invalid_count == 1
    assert any("şema dışı" in w for w in context.warnings)

    listed = hm.list_memories(effective_status="all")
    assert listed.invalid_count == 1
    assert listed.invalid_paths == [f"{MEMORY_DIR}/bozuk.md"]
    # §32: okuma onarmaz.
    assert broken.read_text(encoding="utf-8") == original


async def test_duplicate_identity_fails_closed(db_session: AsyncSession, vault: Path) -> None:
    created = await _store(db_session)
    directory = vault / MEMORY_DIR
    path = vault / created.after["relative_path"]
    clone = directory / "kopya.md"
    clone.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    before = capture_vault_fingerprint(vault)
    db_before = await capture_db_content_fingerprint(db_session)

    with pytest.raises(hm.ActionError, match="HOT_MEMORY_CONFLICT"):
        hm.get_context()

    snapshot = storage.scan_memories(vault.resolve())
    record = snapshot.items[0] if snapshot.items else None

    with pytest.raises(hm.ActionError, match="HOT_MEMORY_CONFLICT"):
        await hm.retire_memory(
            db_session,
            HotMemoryRetireIn(
                memory_id=created.target_id,
                expected_revision=(record.revision if record else "0" * 64),
            ),
        )

    assert capture_vault_fingerprint(vault) == before
    assert await capture_db_content_fingerprint(db_session) == db_before


# ---------------------------------------------------------------------------
# §112 — sembolik link güvenliği
# ---------------------------------------------------------------------------


async def test_symlink_outside_vault_is_not_followed(
    db_session: AsyncSession, vault: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "gizli.md"
    secret.write_text("dışarıdaki içerik", encoding="utf-8")

    directory = vault / MEMORY_DIR
    directory.mkdir(parents=True)
    link = directory / "kacis.md"
    try:
        link.symlink_to(secret)
    except OSError:
        pytest.skip("sembolik link oluşturulamadı")

    snapshot = storage.scan_memories(vault.resolve())
    assert snapshot.items == []
    assert secret.read_text(encoding="utf-8") == "dışarıdaki içerik"

    listed = hm.list_memories(effective_status="all")
    assert listed.items == []


# ---------------------------------------------------------------------------
# §113 — apaçık sır reddi
# ---------------------------------------------------------------------------


async def test_obvious_secret_is_rejected(db_session: AsyncSession, vault: Path) -> None:
    before = capture_vault_fingerprint(vault)
    db_before = await capture_db_content_fingerprint(db_session)

    for text in (
        "-----BEGIN RSA PRIVATE KEY-----\nMIIE...",
        "api_key=sk-abcdefghijklmnopqrstuvwx",
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9longtokenvalue",
        "password=hunter2secret",
    ):
        with pytest.raises(hm.ActionError, match="HOT_MEMORY_POLICY_REJECTED"):
            await _store(db_session, text=text)

    assert capture_vault_fingerprint(vault) == before
    assert await capture_db_content_fingerprint(db_session) == db_before


# ---------------------------------------------------------------------------
# §114 — ilgili kayıtlar
# ---------------------------------------------------------------------------


async def test_related_entities_validated_read_only(
    db_session: AsyncSession, vault: Path
) -> None:
    project_id = uuid.uuid4()
    db_session.add(Entity(id=project_id, type="project", title="Proje", search_text=""))
    await db_session.commit()
    db_before = await capture_db_content_fingerprint(db_session)

    ok = await _store(db_session, related_forkos_ids=[str(project_id)])
    assert ok.status == "executed"
    assert await capture_db_content_fingerprint(db_session) == db_before  # Link/Entity yazılmadı

    snapshot = storage.scan_memories(vault.resolve())
    record = storage.find_memory(snapshot, ok.target_id)
    assert record is not None and record.related_forkos_ids == [str(project_id)]

    # Geçersiz kimlikler reddedilir.
    with pytest.raises(hm.ActionError, match="INVALID_RELATED_ENTITY"):
        await _store(db_session, related_forkos_ids=[str(uuid.uuid4())])
    with pytest.raises(ValidationError):
        await _store(db_session, related_forkos_ids=["uuid-degil"])


async def test_legacy_note_entity_cannot_be_related(
    db_session: AsyncSession, vault: Path
) -> None:
    """§40: dondurulmuş arşiv kayıtlarına bağlanmak reddedilir."""
    legacy_id = uuid.uuid4()
    db_session.add(Entity(id=legacy_id, type="note", title="Eski not", search_text=""))
    await db_session.commit()

    with pytest.raises(hm.ActionError, match="INVALID_RELATED_ENTITY"):
        await _store(db_session, related_forkos_ids=[str(legacy_id)])


# ---------------------------------------------------------------------------
# §115 — okumalar değişmezdir
# ---------------------------------------------------------------------------


async def test_memory_reads_are_immutable(db_session: AsyncSession, vault: Path) -> None:
    await _store(db_session)
    db_before = await capture_db_content_fingerprint(db_session)
    vault_before = capture_vault_fingerprint(vault)

    for _ in range(3):
        hm.get_context()
        hm.list_memories(effective_status="all")
        hm.list_memories(query="planning")

    assert await capture_db_content_fingerprint(db_session) == db_before
    assert capture_vault_fingerprint(vault) == vault_before


# ---------------------------------------------------------------------------
# §127 — Vault yok
# ---------------------------------------------------------------------------


async def test_vault_unavailable_fails_closed_everywhere(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "obsidian_vault_path", "")

    with pytest.raises(hm.ActionError, match="HOT_MEMORY_UNAVAILABLE"):
        hm.get_context()
    with pytest.raises(hm.ActionError, match="HOT_MEMORY_UNAVAILABLE"):
        hm.list_memories()
    with pytest.raises(hm.ActionError, match="HOT_MEMORY_UNAVAILABLE"):
        await _store(db_session)


# ---------------------------------------------------------------------------
# §122 — açılışta yazma yok
# ---------------------------------------------------------------------------


def test_scanning_empty_vault_creates_nothing(vault: Path) -> None:
    snapshot = storage.scan_memories(vault.resolve())
    assert snapshot.items == []
    # Dizin bile oluşturulmaz: oluşturma yalnızca onaylı yazmada (§122).
    assert not (vault / MEMORY_DIR).exists()
    assert list(vault.rglob("*")) == []
