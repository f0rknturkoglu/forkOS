"""H2 sıcak hafıza: depolama ve adaptör doğruluğu.

Kanıtlanan sözleşmeler: öğe başına tek dosya, sunucu üretimi UUID kimliği,
içerik revizyonu, emeklilik ≠ silme, zaman aşımı salt okuma anında, sınırlı
bağlam bütçesi, kimlik çakışmasında fail-closed, sır reddi, yol güvenliği ve
okumaların değişmezliği.
"""

from __future__ import annotations

import errno
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


# ===========================================================================
# H2.1 — eşzamanlılık, yaşam döngüsü ve gizlilik sağlamlaştırması
# ===========================================================================


def _manual_memory_file(
    vault: Path,
    *,
    memory_id: str | None = None,
    kind: str = "preference",
    title: str = "Elle yazılmış tercih",
    text: str = "Elle yazılmış gövde.",
    status: str = "active",
    importance: int = 2,
    updated_at: str = "2026-09-20T12:00:00+00:00",
    expires_at: str | None = None,
) -> Path:
    """Obsidian'da ELLE yazılmış, şeması geçerli bir sıcak hafıza dosyası üretir.

    H2.1'in kritik senaryosu budur: kullanıcı dosyayı sistemin dışında
    değiştirir. Bu yüzden dosya kanonik yazıcıyla değil, doğrudan metinle
    üretilir.
    """
    memory_id = memory_id or str(uuid.uuid4())
    directory = vault / MEMORY_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{memory_id}.md"
    # Damgalar TEK TIRNAK içinde yazılır: kanonik yazıcı da öyle yapar, çünkü
    # YAML tırnaksız ISO damgasını `datetime` nesnesine çevirir ve şema onu
    # "metin değil" diye reddeder.
    expires_line = "" if expires_at is None else f"expires_at: '{expires_at}'\n"
    path.write_text(
        "---\n"
        "agent_memory_version: 1\n"
        f"memory_id: {memory_id}\n"
        f"memory_kind: {kind}\n"
        f"title: {title}\n"
        f"status: {status}\n"
        f"importance: {importance}\n"
        "source_mode: explicit_user\n"
        f"created_at: '{updated_at}'\n"
        f"updated_at: '{updated_at}'\n"
        f"{expires_line}"
        "related_forkos_ids: []\n"
        "tags: []\n"
        "---\n\n"
        f"{text}\n",
        encoding="utf-8",
    )
    return path


def _scanned_record(vault: Path, memory_id: str) -> storage.MemoryRecord:
    record = storage.find_memory(storage.scan_memories(vault.resolve()), memory_id)
    assert record is not None
    return record


# ---------------------------------------------------------------------------
# §3/§70 — dosya sistemi compare-and-swap
# ---------------------------------------------------------------------------


async def test_hot_memory_update_rechecks_actual_revision_before_replace(
    db_session: AsyncSession, vault: Path
) -> None:
    """Tarama ile yazma arasındaki kullanıcı düzenlemesi EZİLMEZ.

    Kaydın revizyonu ile `expected_revision` AYNI (A) tutulur, böylece yalnızca
    erken karşılaştırma yapan bir uygulama bu testi geçemez: fark yalnızca
    DİSKTEKİ güncel baytlarda görünür.
    """
    created = await _store(db_session)
    record = _scanned_record(vault, created.target_id)
    path = vault / record.relative_path

    human_edit = path.read_text(encoding="utf-8").replace(
        "Prefers project-level plans over hourly schedules.",
        "Kullanıcının elle yazdığı yeni gövde.",
    )
    path.write_text(human_edit, encoding="utf-8")
    revision_after_edit = storage.revision_of(path.read_bytes())
    assert revision_after_edit != record.revision

    with pytest.raises(storage.HotMemoryError, match="HOT_MEMORY_STALE"):
        storage.rewrite_memory(
            vault.resolve(),
            record,
            expected_revision=record.revision,  # A == record.revision → erken kontrol geçer
            title="Ajan başlığı",
        )

    assert path.read_text(encoding="utf-8") == human_edit
    assert storage.revision_of(path.read_bytes()) == revision_after_edit
    # §84: başarısız yazma geçici dosya BIRAKMAZ.
    assert not [item for item in path.parent.iterdir() if item.name.endswith(".tmp")]


async def test_hot_memory_retire_rechecks_actual_revision_before_replace(
    db_session: AsyncSession, vault: Path
) -> None:
    created = await _store(db_session)
    record = _scanned_record(vault, created.target_id)
    path = vault / record.relative_path
    human_edit = path.read_text(encoding="utf-8").replace(
        "Prefers project-level plans over hourly schedules.", "Kullanıcı gövdesi."
    )
    path.write_text(human_edit, encoding="utf-8")

    with pytest.raises(hm.ActionError, match="HOT_MEMORY_STALE"):
        await hm.retire_memory(
            db_session,
            HotMemoryRetireIn(memory_id=created.target_id, expected_revision=record.revision),
            request_id="t",
        )

    assert path.read_text(encoding="utf-8") == human_edit


async def test_two_writers_from_same_revision_cannot_both_succeed(
    db_session: AsyncSession, vault: Path
) -> None:
    """§53: ikisi de A revizyonuna dayanan iki yazmadan yalnızca BİRİ başarılı."""
    created = await _store(db_session)
    record = _scanned_record(vault, created.target_id)

    first = await hm.update_memory(
        db_session,
        HotMemoryUpdateIn(
            memory_id=created.target_id,
            expected_revision=record.revision,
            importance=3,
        ),
        request_id="t1",
    )
    assert first.status == "executed"

    with pytest.raises(hm.ActionError, match="HOT_MEMORY_STALE"):
        await hm.update_memory(
            db_session,
            HotMemoryUpdateIn(
                memory_id=created.target_id,
                expected_revision=record.revision,
                importance=1,
            ),
            request_id="t2",
        )

    assert _scanned_record(vault, created.target_id).importance == 3


async def test_retire_after_update_with_old_revision_is_stale(
    db_session: AsyncSession, vault: Path
) -> None:
    """§54: update başarılı olduktan sonra eski revizyonla emeklilik GEÇERSİZ."""
    created = await _store(db_session)
    record = _scanned_record(vault, created.target_id)

    await hm.update_memory(
        db_session,
        HotMemoryUpdateIn(
            memory_id=created.target_id,
            expected_revision=record.revision,
            importance=3,
        ),
        request_id="t1",
    )

    with pytest.raises(hm.ActionError, match="HOT_MEMORY_STALE"):
        await hm.retire_memory(
            db_session,
            HotMemoryRetireIn(memory_id=created.target_id, expected_revision=record.revision),
            request_id="t2",
        )

    assert _scanned_record(vault, created.target_id).status == "active"


# ---------------------------------------------------------------------------
# §18/§19 — bayat revizyon noop'tan önce kazanır
# ---------------------------------------------------------------------------


async def test_stale_revision_beats_update_noop(
    db_session: AsyncSession, vault: Path
) -> None:
    """İstenen değerler mevcut duruma EŞİT olsa bile bayat revizyon hatadır."""
    created = await _store(db_session, title="İlk başlık")
    record = _scanned_record(vault, created.target_id)  # revizyon A
    path = vault / record.relative_path

    # Kullanıcı başlığı elle değiştirdi (revizyon B). İstenen değer B ile aynı:
    # eski uygulama bunu "değişiklik yok" sayıp noop dönerdi.
    edited = path.read_text(encoding="utf-8").replace("title: İlk başlık", "title: Elle başlık")
    path.write_text(edited, encoding="utf-8")
    revision_b = storage.revision_of(path.read_bytes())

    with pytest.raises(hm.ActionError, match="HOT_MEMORY_STALE"):
        await hm.update_memory(
            db_session,
            HotMemoryUpdateIn(
                memory_id=created.target_id,
                expected_revision=record.revision,
                title="Elle başlık",
            ),
            request_id="t",
        )

    assert storage.revision_of(path.read_bytes()) == revision_b


async def test_stale_revision_beats_retire_noop(
    db_session: AsyncSession, vault: Path
) -> None:
    """Zaten emekli olsa bile eski revizyon STALE verir; güncel revizyon noop."""
    created = await _store(db_session)
    first = _scanned_record(vault, created.target_id)
    retired = await hm.retire_memory(
        db_session,
        HotMemoryRetireIn(memory_id=created.target_id, expected_revision=first.revision),
        request_id="t1",
    )
    assert retired.status == "executed"
    assert retired.after["revision"] != first.revision

    with pytest.raises(hm.ActionError, match="HOT_MEMORY_STALE"):
        await hm.retire_memory(
            db_session,
            HotMemoryRetireIn(memory_id=created.target_id, expected_revision=first.revision),
            request_id="t2",
        )

    current = _scanned_record(vault, created.target_id)
    again = await hm.retire_memory(
        db_session,
        HotMemoryRetireIn(memory_id=created.target_id, expected_revision=current.revision),
        request_id="t3",
    )
    assert again.status == "noop"
    assert _scanned_record(vault, created.target_id).revision == current.revision


# ---------------------------------------------------------------------------
# §9/§10/§11 — yeniden hatırlama
# ---------------------------------------------------------------------------


async def test_active_exact_duplicate_remains_noop(
    db_session: AsyncSession, vault: Path
) -> None:
    """Yaşam döngüsü matrisinin AKTİF dalı: yeni dosya açılmaz."""
    first = await _store(db_session)
    files_before = _memory_files(vault)

    second = await _store(db_session, title="Farklı başlık")

    assert second.status == "noop"
    assert second.target_id == first.target_id
    assert _memory_files(vault) == files_before


async def test_retired_duplicate_can_be_remembered_again_as_new_active_item(
    db_session: AsyncSession, vault: Path
) -> None:
    """§41: emekli kayıt YENİDEN CANLANDIRILMAZ; yeni bir aktif kayıt doğar."""
    created = await _store(db_session)
    record = _scanned_record(vault, created.target_id)
    await hm.retire_memory(
        db_session,
        HotMemoryRetireIn(memory_id=created.target_id, expected_revision=record.revision),
        request_id="t",
    )
    retired_path = vault / record.relative_path
    retired_bytes = retired_path.read_bytes()

    again = await _store(db_session)

    assert again.status == "executed"
    assert again.target_id != created.target_id
    files = {path.name: path for path in _memory_files(vault)}
    assert len(files) == 2
    # Eski kayıt DEĞİŞMEDİ: emekli kalır ve tarihsel kanıt korunur.
    assert retired_path.read_bytes() == retired_bytes
    assert _scanned_record(vault, created.target_id).status == "retired"
    assert _scanned_record(vault, again.target_id).status == "active"

    context = hm.get_context()
    returned = [item.memory_id for group in (context.preferences,) for item in group]
    assert returned == [again.target_id]


async def test_expired_duplicate_can_be_remembered_again_as_new_active_item(
    db_session: AsyncSession, vault: Path
) -> None:
    """§42: süresi geçmiş kayıt DÜZENLENMEZ; yeni aktif kayıt doğar."""
    past = (datetime.now(UTC) - timedelta(days=1)).replace(microsecond=0).isoformat()
    created = await _store(db_session, expires_at=past)
    record = _scanned_record(vault, created.target_id)
    assert record.effective_status() == "expired"
    expired_bytes = (vault / record.relative_path).read_bytes()

    again = await _store(db_session)

    assert again.status == "executed"
    assert again.target_id != created.target_id
    assert (vault / record.relative_path).read_bytes() == expired_bytes
    assert _scanned_record(vault, created.target_id).effective_status() == "expired"

    context = hm.get_context()
    assert [item.memory_id for item in context.preferences] == [again.target_id]


# ---------------------------------------------------------------------------
# §13/§14/§72 — elle düzenlenen sır politikası
# ---------------------------------------------------------------------------

_SECRET_BODY = "api_key=sk-abcdefghijklmnopqrstuvwx"
_PRIVATE_KEY_BODY = (
    "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----"
)


async def test_manual_secret_edit_is_excluded_from_hot_memory_context(
    db_session: AsyncSession, vault: Path
) -> None:
    """Yazma anındaki kontrol yetmez: gövde Obsidian'da elle değiştirilebilir."""
    created = await _store(db_session)
    path = vault / created.after["relative_path"]
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "Prefers project-level plans over hourly schedules.", _SECRET_BODY
        ),
        encoding="utf-8",
    )
    before = capture_vault_fingerprint(vault)
    db_before = await capture_db_content_fingerprint(db_session)

    context = hm.get_context()
    listed = hm.list_memories(effective_status="all")

    serialized = json.dumps(context.model_dump()) + json.dumps(listed.model_dump())
    assert _SECRET_BODY not in serialized
    assert "sk-abcdefghijklmnopqrstuvwx" not in serialized
    assert context.preferences == []
    assert listed.items == []
    # §47: geçerli kayıtlar akmaya devam eder, sayaç ve uyarı dürüsttür.
    assert context.invalid_count == 1
    assert any("politika" in warning for warning in context.warnings)
    # §14: kullanıcının dosyası DEĞİŞTİRİLMEZ.
    assert capture_vault_fingerprint(vault) == before
    assert await capture_db_content_fingerprint(db_session) == db_before


async def test_manual_private_key_edit_is_excluded_from_hot_memory_list(
    db_session: AsyncSession, vault: Path
) -> None:
    created = await _store(db_session)
    path = vault / created.after["relative_path"]
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "Prefers project-level plans over hourly schedules.", _PRIVATE_KEY_BODY
        ),
        encoding="utf-8",
    )

    listed = hm.list_memories(effective_status="all")

    serialized = json.dumps(listed.model_dump())
    assert "PRIVATE KEY" not in serialized
    assert "MIIEvQIBADANBgkqhkiG9w0BAQEFAASC" not in serialized
    assert listed.items == []
    assert listed.invalid_count == 1


async def test_policy_rejected_manual_file_is_not_modified(
    db_session: AsyncSession, vault: Path
) -> None:
    """§14: politika yalnızca YÜKLEMEYİ reddeder; dosyaya dokunmaz."""
    path = _manual_memory_file(vault, text=_SECRET_BODY)
    before = capture_vault_fingerprint(vault)
    stat_before = path.stat()

    with pytest.raises(storage.HotMemoryError, match="HOT_MEMORY_POLICY_REJECTED"):
        storage.parse_memory_file(path, vault.resolve())

    hm.get_context()
    hm.list_memories(effective_status="all")

    after = path.stat()
    assert capture_vault_fingerprint(vault) == before
    assert after.st_mtime_ns == stat_before.st_mtime_ns
    assert path.read_text(encoding="utf-8").find(_SECRET_BODY) != -1


# ---------------------------------------------------------------------------
# §24/§25/§77 — atomik oluşturma
# ---------------------------------------------------------------------------


async def test_hot_memory_create_never_exposes_partial_target_on_failure(
    vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise OSError(errno.EIO, "yayın başarısız")

    monkeypatch.setattr(storage.os, "link", _boom)

    with pytest.raises(OSError):
        storage.create_memory(
            vault.resolve(),
            kind="preference",
            title="Başlık",
            text="Gövde.",
            importance=2,
            source_mode="explicit_user",
        )

    directory = vault / MEMORY_DIR
    assert list(directory.iterdir()) == []


async def test_hot_memory_create_collision_never_overwrites_existing_file(
    vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixed = uuid.uuid4()
    monkeypatch.setattr(storage.uuid, "uuid4", lambda: fixed)
    directory = vault / MEMORY_DIR
    directory.mkdir(parents=True)
    target = directory / f"{fixed}.md"
    target.write_text("kullanıcının kendi dosyası", encoding="utf-8")

    with pytest.raises(storage.HotMemoryError, match="HOT_MEMORY_CONFLICT"):
        storage.create_memory(
            vault.resolve(),
            kind="preference",
            title="Başlık",
            text="Gövde.",
            importance=2,
            source_mode="explicit_user",
        )

    assert target.read_text(encoding="utf-8") == "kullanıcının kendi dosyası"
    assert [path.name for path in directory.iterdir()] == [target.name]


async def test_hot_memory_create_leaves_no_temporary_files(vault: Path) -> None:
    created = storage.create_memory(
        vault.resolve(),
        kind="preference",
        title="Başlık",
        text="Gövde.",
        importance=2,
        source_mode="explicit_user",
    )

    directory = vault / MEMORY_DIR
    names = sorted(path.name for path in directory.iterdir())
    assert names == [f"{created.memory_id}.md"]
    assert not any(name.endswith(".tmp") for name in names)
    # Kısmi değil TAM dosya yayınlandı: ayrıştırma başarılı ve revizyon sabit.
    assert storage.revision_of((directory / names[0]).read_bytes()) == created.revision


# ---------------------------------------------------------------------------
# §28/§30/§76 — okunamayan Vault
# ---------------------------------------------------------------------------


def test_unreadable_hot_memory_vault_returns_hot_memory_unavailable(
    vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(storage, "readable_root", lambda: None)

    for call in (hm.get_context, hm.list_memories):
        with pytest.raises(hm.ActionError) as excinfo:
            call()
        message = str(excinfo.value)
        assert "HOT_MEMORY_UNAVAILABLE" in message
        # §30: mutlak yol, kullanıcı adı, yığın izi SIZMAZ.
        assert str(vault) not in message
        assert "Traceback" not in message


def test_scan_oserror_becomes_unavailable_without_path_leak(
    vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    leak = f"gizli mutlak yol: {vault}/alt"

    def _boom(root: Path) -> storage.MemorySnapshot:
        raise PermissionError(leak)

    monkeypatch.setattr(storage, "readable_root", lambda: vault.resolve())
    monkeypatch.setattr(storage, "scan_memories", _boom)

    for call in (hm.get_context, hm.list_memories):
        with pytest.raises(hm.ActionError) as excinfo:
            call()
        message = str(excinfo.value)
        assert "HOT_MEMORY_UNAVAILABLE" in message
        assert leak not in message
        assert "Traceback" not in message


# ---------------------------------------------------------------------------
# §32/§33/§73 — tanılama sayaçları
# ---------------------------------------------------------------------------


def test_invalid_count_reports_all_invalid_files_while_paths_are_bounded(
    vault: Path,
) -> None:
    directory = vault / MEMORY_DIR
    directory.mkdir(parents=True)
    invalid_total = storage.MAX_INVALID_REPORTED + 5
    for index in range(invalid_total):
        (directory / f"bozuk-{index:03d}.md").write_text("frontmatter yok", encoding="utf-8")
    _manual_memory_file(vault, title="Geçerli kayıt")

    before = capture_vault_fingerprint(vault)
    snapshot = storage.scan_memories(vault.resolve())

    assert snapshot.invalid_count == invalid_total
    assert len(snapshot.invalid_relative_paths) == storage.MAX_INVALID_REPORTED
    assert len(snapshot.items) == 1

    listed = hm.list_memories(effective_status="all")
    assert listed.invalid_count == invalid_total
    assert len(listed.invalid_paths) == storage.MAX_INVALID_REPORTED
    # Okuma hiçbir bozuk dosyayı DEĞİŞTİRMEZ.
    assert capture_vault_fingerprint(vault) == before


# ---------------------------------------------------------------------------
# §34/§36/§74 — dondurulmuş aile
# ---------------------------------------------------------------------------


async def test_note_attachment_entity_cannot_be_related_to_hot_memory(
    db_session: AsyncSession, vault: Path
) -> None:
    attachment_id = uuid.uuid4()
    db_session.add(
        Entity(id=attachment_id, type="note_attachment", title="Ek", search_text="")
    )
    await db_session.commit()

    with pytest.raises(hm.ActionError, match="INVALID_RELATED_ENTITY"):
        await _store(db_session, related_forkos_ids=[str(attachment_id)])

    created = await _store(db_session)
    record = _scanned_record(vault, created.target_id)
    with pytest.raises(hm.ActionError, match="INVALID_RELATED_ENTITY"):
        await hm.update_memory(
            db_session,
            HotMemoryUpdateIn(
                memory_id=created.target_id,
                expected_revision=record.revision,
                related_forkos_ids=[str(attachment_id)],
            ),
            request_id="t",
        )


# ---------------------------------------------------------------------------
# §38/§40/§75 — kronolojik sıralama
# ---------------------------------------------------------------------------


def test_hot_memory_ranking_uses_chronological_updated_at_not_raw_string_order(
    vault: Path,
) -> None:
    """Farklı UTC ofsetleri metinsel sırayla YANLIŞ sıralanır.

    A = 2026-09-20T23:00:00+00:00  → 23:00Z
    B = 2026-09-21T01:00:00+03:00  → 22:00Z

    Kronolojik olarak A daha yeni; metinsel olarak ("2026-09-21" > "2026-09-20")
    B önce gelirdi. Sıralama kronolojik olmalı: [A, B].
    """
    later_earlier_offset = _manual_memory_file(
        vault,
        title="A kaydı",
        text="A gövdesi.",
        updated_at="2026-09-20T23:00:00+00:00",
    )
    earlier_later_offset = _manual_memory_file(
        vault,
        title="B kaydı",
        text="B gövdesi.",
        updated_at="2026-09-21T01:00:00+03:00",
    )

    listed = hm.list_memories(effective_status="all")
    by_title = {item.title: item.memory_id for item in listed.items}
    assert [item.title for item in listed.items] == ["A kaydı", "B kaydı"]

    context = hm.get_context()
    assert [item.memory_id for item in context.preferences] == [
        by_title["A kaydı"],
        by_title["B kaydı"],
    ]
    assert later_earlier_offset != earlier_later_offset


# ===========================================================================
# H2.2 — metadata gizliliği, sınırlı sözleşmeler ve tanılama redaksiyonu
# ===========================================================================

_SECRET_TAG = "api_key=sk-abcdefghijklmnopqrstuvwx"
_SECRET_NAME = f"{_SECRET_TAG}.md"


def _assert_secret_absent(payload: object, secret: str) -> None:
    """Serileştirilmiş bir yükün HİÇBİR yerinde sır bulunmadığını doğrular (§65).

    Tek bir alanı kontrol etmek yetmez: sır, tanılama yollarında, uyarılarda ya
    da makbuz künyesinde de görünebilir.
    """
    serialized = payload if isinstance(payload, str) else json.dumps(payload, default=str)
    assert secret not in serialized
    assert "sk-abcdefghijklmnopqrstuvwx" not in serialized


# ---------------------------------------------------------------------------
# §7/§64 — store ve update: metadata'daki sır
# ---------------------------------------------------------------------------


async def test_hot_memory_store_rejects_secret_in_tags(
    db_session: AsyncSession, vault: Path
) -> None:
    db_before = await capture_db_content_fingerprint(db_session)

    with pytest.raises(hm.ActionError, match="HOT_MEMORY_POLICY_REJECTED"):
        await _store(db_session, tags=[_SECRET_TAG])

    assert _memory_files(vault) == []
    # Reddedilen aday dizini bile yaratmaz (§39).
    assert not (vault / MEMORY_DIR).exists()
    assert await capture_db_content_fingerprint(db_session) == db_before


async def test_hot_memory_update_rejects_secret_in_tags_without_mutation(
    db_session: AsyncSession, vault: Path
) -> None:
    """§41: reddedilen metadata güncellemesi hedefi HİÇ değiştirmez."""
    created = await _store(db_session, tags=["planning"])
    record = _scanned_record(vault, created.target_id)
    path = vault / record.relative_path
    bytes_before = path.read_bytes()
    stat_before = path.stat()
    db_before = await capture_db_content_fingerprint(db_session)

    with pytest.raises(hm.ActionError, match="HOT_MEMORY_POLICY_REJECTED"):
        await hm.update_memory(
            db_session,
            HotMemoryUpdateIn(
                memory_id=created.target_id,
                expected_revision=record.revision,
                tags=[_SECRET_TAG],
            ),
            request_id="t",
        )

    assert path.read_bytes() == bytes_before
    assert storage.revision_of(path.read_bytes()) == record.revision
    assert path.stat().st_mtime_ns == stat_before.st_mtime_ns
    assert await capture_db_content_fingerprint(db_session) == db_before


# ---------------------------------------------------------------------------
# §9/§42/§64 — elle düzenlenmiş metadata
# ---------------------------------------------------------------------------


async def test_manual_secret_in_tags_is_policy_rejected(
    db_session: AsyncSession, vault: Path
) -> None:
    """Başlık ve gövde TEMİZ; yalnızca etiket sır taşıyor."""
    path = _manual_memory_file(vault, title="Temiz başlık", text="Temiz gövde.")
    edited = path.read_text(encoding="utf-8").replace("tags: []", f"tags:\n  - {_SECRET_TAG}")
    path.write_text(edited, encoding="utf-8")
    stat_before = path.stat()

    context = hm.get_context()
    listed = hm.list_memories(effective_status="all")

    assert context.preferences == []
    assert listed.items == []
    assert context.invalid_count == 1
    _assert_secret_absent(context.model_dump(), _SECRET_TAG)
    _assert_secret_absent(listed.model_dump(), _SECRET_TAG)
    assert path.read_text(encoding="utf-8") == edited
    assert path.stat().st_mtime_ns == stat_before.st_mtime_ns


async def test_manual_secret_in_extra_frontmatter_is_policy_rejected(
    db_session: AsyncSession, vault: Path
) -> None:
    """Bilinmeyen/ek frontmatter anahtarı politika kapısını ATLAYAMAZ."""
    path = _manual_memory_file(vault, title="Temiz", text="Temiz gövde.")
    edited = path.read_text(encoding="utf-8").replace(
        "tags: []", f"tags: []\nsource: {_SECRET_TAG}"
    )
    path.write_text(edited, encoding="utf-8")

    context = hm.get_context()
    listed = hm.list_memories(effective_status="all")

    assert context.preferences == []
    assert listed.items == []
    _assert_secret_absent(context.model_dump(), _SECRET_TAG)
    _assert_secret_absent(listed.model_dump(), _SECRET_TAG)
    assert path.read_text(encoding="utf-8") == edited


async def test_secret_like_memory_filename_is_not_exposed(
    db_session: AsyncSession, vault: Path
) -> None:
    """§10: dosya adı da kullanıcı denetimindedir; ajan yüzeyine çıkamaz."""
    created = await _store(db_session)
    record = _scanned_record(vault, created.target_id)
    original = vault / record.relative_path
    renamed = original.parent / _SECRET_NAME
    original.rename(renamed)
    stat_before = renamed.stat()

    context = hm.get_context()
    listed = hm.list_memories(effective_status="all")

    assert context.preferences == []
    assert listed.items == []
    assert listed.invalid_count == 1
    assert listed.invalid_paths
    _assert_secret_absent(context.model_dump(), _SECRET_TAG)
    _assert_secret_absent(listed.model_dump(), _SECRET_TAG)
    # Dosya olduğu gibi bırakılır: yeniden adlandırma ya da redaksiyon YOK (§56).
    assert renamed.is_file()
    assert renamed.stat().st_mtime_ns == stat_before.st_mtime_ns


# ---------------------------------------------------------------------------
# §18-§22/§66 — elle düzenlenen metadata sınırları
# ---------------------------------------------------------------------------


def test_manual_hot_memory_tag_over_50_chars_is_invalid(vault: Path) -> None:
    too_long = "t" * (storage.MAX_TAG_LENGTH + 1)
    path = _manual_memory_file(vault)
    path.write_text(
        path.read_text(encoding="utf-8").replace("tags: []", f"tags:\n  - {too_long}"),
        encoding="utf-8",
    )
    before = capture_vault_fingerprint(vault)
    stat_before = path.stat()

    snapshot = storage.scan_memories(vault.resolve())
    listed = hm.list_memories(effective_status="all")

    assert snapshot.items == []
    assert snapshot.invalid_count == 1
    assert listed.items == []
    assert listed.invalid_count == 1
    # §19/§57: okuma yolu dosyayı DÜZELTMEZ.
    assert capture_vault_fingerprint(vault) == before
    assert path.stat().st_mtime_ns == stat_before.st_mtime_ns


def test_manual_hot_memory_blank_tag_is_invalid(vault: Path) -> None:
    path = _manual_memory_file(vault)
    path.write_text(
        path.read_text(encoding="utf-8").replace("tags: []", 'tags:\n  - "   "'),
        encoding="utf-8",
    )
    before = capture_vault_fingerprint(vault)

    snapshot = storage.scan_memories(vault.resolve())

    assert snapshot.items == []
    assert snapshot.invalid_count == 1
    assert capture_vault_fingerprint(vault) == before


def test_manual_oversized_tag_cannot_bloat_output(vault: Path) -> None:
    """§21: birkaç KB'lik etiket çıktıyı şişiremez."""
    huge = "x" * 4096
    path = _manual_memory_file(vault)
    path.write_text(
        path.read_text(encoding="utf-8").replace("tags: []", f"tags:\n  - {huge}"),
        encoding="utf-8",
    )

    listed = hm.list_memories(effective_status="all")

    assert listed.items == []
    assert huge not in json.dumps(listed.model_dump())


# ---------------------------------------------------------------------------
# §45 — sayaçlar dürüst kalır
# ---------------------------------------------------------------------------


def test_policy_counters_stay_truthful_with_mixed_invalid_files(vault: Path) -> None:
    directory = vault / MEMORY_DIR
    directory.mkdir(parents=True)
    # 2 şema dışı (sır yok) + 3 politika dışı (gövdede sır).
    for index in range(2):
        (directory / f"bozuk-{index}.md").write_text("frontmatter yok", encoding="utf-8")
    for index in range(3):
        _manual_memory_file(vault, text=f"api_key=sk-secret{index}0000000000000")

    snapshot = storage.scan_memories(vault.resolve())

    assert snapshot.invalid_count == 5
    assert snapshot.policy_rejected_count == 3
    assert len(snapshot.invalid_relative_paths) == 5
    assert len(snapshot.policy_rejected_relative_paths) == 3
    # Sır taşıyan tanılama yolu redakte edilir (§11).
    assert all("sk-secret" not in path for path in snapshot.invalid_relative_paths)


# ---------------------------------------------------------------------------
# §20 — şema = belge = çalışma zamanı
# ---------------------------------------------------------------------------


def test_hot_memory_bounds_match_between_models_and_storage() -> None:
    """Aynı sınır iki katmanda ayrışırsa sessizce gevşer; burada kilitlenir."""
    from app.integrations.agent import hot_memory_models as models

    for name in (
        "MAX_TITLE",
        "MAX_TEXT",
        "MAX_TAGS",
        "MAX_TAG_LENGTH",
        "MAX_RELATED",
        "MAX_RETIRED_REASON",
    ):
        assert getattr(models, name) == getattr(storage, name), name


# ---------------------------------------------------------------------------
# §23-§27/§67 — sorgu sınırı (çalışma zamanı = yetki)
# ---------------------------------------------------------------------------


def test_hot_memory_list_query_200_chars_allowed(vault: Path) -> None:
    _manual_memory_file(vault, title="Kayıt", text="Gövde.")

    listed = hm.list_memories(query="a" * storage.MAX_TAG_LENGTH * 4, effective_status="all")

    assert listed.total == 0  # eşleşme yok ama istek GEÇERLİ


def test_hot_memory_list_query_201_chars_rejected(vault: Path) -> None:
    from app.integrations.agent.hot_memory_models import MAX_QUERY_LENGTH

    _manual_memory_file(vault, title="Kayıt", text="Gövde.")

    with pytest.raises(hm.ActionError, match="QUERY_TOO_LONG"):
        hm.list_memories(query="a" * (MAX_QUERY_LENGTH + 1))

    # Sınır tam 200'de durur.
    assert hm.list_memories(query="a" * MAX_QUERY_LENGTH).total == 0


# ---------------------------------------------------------------------------
# §38/§68 — sert bağ desteklemeyen dosya sistemi yolu
# ---------------------------------------------------------------------------


def _disable_hardlinks(monkeypatch: pytest.MonkeyPatch) -> None:
    def _unsupported(*args: object, **kwargs: object) -> None:
        raise OSError(errno.EPERM, "sert bağ desteklenmiyor")

    monkeypatch.setattr(storage.os, "link", _unsupported)


def test_hot_memory_create_fallback_preserves_no_overwrite(
    vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _disable_hardlinks(monkeypatch)

    created = storage.create_memory(
        vault.resolve(),
        kind="preference",
        title="Yedek yol",
        text="Gövde.",
        importance=2,
        source_mode="explicit_user",
    )

    directory = vault / MEMORY_DIR
    assert [path.name for path in directory.iterdir()] == [f"{created.memory_id}.md"]
    assert storage.find_memory(storage.scan_memories(vault.resolve()), created.memory_id)


def test_hot_memory_create_fallback_collision_preserves_existing_bytes(
    vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _disable_hardlinks(monkeypatch)
    fixed = uuid.uuid4()
    monkeypatch.setattr(storage.uuid, "uuid4", lambda: fixed)
    directory = vault / MEMORY_DIR
    directory.mkdir(parents=True)
    target = directory / f"{fixed}.md"
    target.write_text("kullanıcının dosyası", encoding="utf-8")

    with pytest.raises(storage.HotMemoryError, match="HOT_MEMORY_CONFLICT"):
        storage.create_memory(
            vault.resolve(),
            kind="preference",
            title="Başlık",
            text="Gövde.",
            importance=2,
            source_mode="explicit_user",
        )

    assert target.read_text(encoding="utf-8") == "kullanıcının dosyası"
    assert [path.name for path in directory.iterdir()] == [target.name]


async def test_fallback_path_also_enforces_full_artifact_policy(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§39: politika HER iki yayın yolundan da önce çalışır."""
    _disable_hardlinks(monkeypatch)

    with pytest.raises(hm.ActionError, match="HOT_MEMORY_POLICY_REJECTED"):
        await _store(db_session, tags=[_SECRET_TAG])

    assert not (vault / MEMORY_DIR).exists()
