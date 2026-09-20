"""Notes → Obsidian Vault kopya+doğrulama migration testleri.

Kapsam: kimlik/tür önceliği, durum (aktif/arşiv/çöp), etiketler, iki kuşak ek
depolama, ek referans yeniden yazımı, wikilink çözümlemesi, canvas yan dosyası,
çakışma politikası, idempotent tekrar çalıştırma ve KAYNAK DEĞİŞMEZLİĞİ.
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import text

from app.config import settings
from app.core.entity import create_entity
from app.db import SessionLocal
from app.integrations.obsidian.frontmatter import parse_frontmatter
from app.integrations.obsidian.migration import engine
from app.integrations.obsidian.migration.engine import (
    DRY_RUN,
    MigrationOutcome,
    run_apply,
    run_dry_run,
    run_verify,
)
from app.integrations.obsidian.migration.manifest import (
    DIVERGED,
    FAILED,
    MANIFEST_DIR,
    VERIFIED,
    load_manifest,
)
from app.integrations.obsidian.migration.plan import (
    BOOKMARK_NOTE,
    DAILY,
    PERSONAL,
    PROJECT_JOURNAL,
    classify_note_kind,
    sanitize_attachment_name,
    suffixed_path,
)
from app.integrations.obsidian.migration.render import (
    UNPLACED_MARKER,
    build_body,
    canonical_tags,
    rewrite_attachment_refs,
    rewrite_wikilinks,
)
from app.integrations.obsidian.migration.source import load_snapshot, read_only_session
from app.integrations.obsidian.service import create_managed_note, vault_index
from app.modules.bookmark.models import Bookmark
from app.modules.bookmark.service import url_hash
from app.modules.note import service as note_service
from app.modules.note import storage as attachment_storage
from app.modules.note.schemas import NoteFolderIn, NoteIn, NoteUpdate
from app.modules.project import service as project_service
from app.modules.project.schemas import ProjectIn

PNG = b"\x89PNG\r\n\x1a\n-fake-image-bytes"
NOTE_SQL = (
    "select id, body, pinned, folder_id, journal_day, trashed_at, "
    "coalesce(attachments::text, '[]') as att, coalesce(canvas_state::text, '{}') as canvas "
    "from note order by id"
)


@pytest.fixture(autouse=True)
def reset_vault_index():
    vault_index._items.clear()
    vault_index._conflicts.clear()
    vault_index._invalid_files.clear()
    vault_index._last_scanned = None
    vault_index._last_status = None
    vault_index._last_root = None
    yield
    vault_index._items.clear()
    vault_index._conflicts.clear()
    vault_index._invalid_files.clear()
    vault_index._last_scanned = None
    vault_index._last_status = None
    vault_index._last_root = None


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "vault"
    path.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "TestVault")
    return path


# ---------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------


#: `NoteIn` gövdesine ait alanlar; kalanlar `note_service.create` anahtar kelimeleridir.
NOTE_IN_FIELDS = {"pinned", "relate_to", "tags", "canvas_state", "default_view", "folder_id"}


async def make_note(body: str, **kwargs) -> dict:
    data_kwargs = {key: value for key, value in kwargs.items() if key in NOTE_IN_FIELDS}
    create_kwargs = {key: value for key, value in kwargs.items() if key not in NOTE_IN_FIELDS}
    async with SessionLocal() as session:
        note = await note_service.create(
            session, NoteIn(body=body, **data_kwargs), **create_kwargs
        )
    return note.model_dump(mode="json")


async def set_body(note_id: str, body: str) -> None:
    async with SessionLocal() as session:
        await note_service.update(session, uuid.UUID(note_id), NoteUpdate(body=body))


async def make_journal_note(project_id: uuid.UUID, day: date, body: str) -> dict:
    """Göç KAYNAĞINI üretir: legacy proje günlüğü satırı.

    Ürün akışı artık proje günlüğünü veritabanına yazmaz (sahibi Vault).
    Bu yardımcı dondurulmuş arşiv yazıcısını kullanır; göç testinin kaynak
    verisini kurmaktan başka bir amacı yoktur.
    """
    return await make_note(
        body, relate_to=project_id, project_id=project_id, journal_day=day
    )


async def make_folder(name: str, parent_id: uuid.UUID | None = None) -> uuid.UUID:
    async with SessionLocal() as session:
        folder = await note_service.create_folder(
            session, NoteFolderIn(name=name, parent_id=parent_id)
        )
    return folder.id


async def make_project(title: str) -> uuid.UUID:
    async with SessionLocal() as session:
        project = await project_service.create(session, ProjectIn(title=title))
    return uuid.UUID(str(project["id"]))


async def make_bookmark(url: str, title: str) -> uuid.UUID:
    async with SessionLocal() as session:
        entity = await create_entity(session, type="bookmark", title=title, search_text=url)
        session.add(Bookmark(id=entity.id, url=url, url_hash=url_hash(url)))
        await session.commit()
        return entity.id


async def attach(note_id: str, name: str, content: bytes, mime: str = "image/png"):
    async with SessionLocal() as session:
        return await note_service.add_attachment(
            session, uuid.UUID(note_id), filename=name, mime=mime, content=content
        )


async def insert_attachment_row(note_id: str, name: str, size: int, sha256: str) -> None:
    async with SessionLocal() as session:
        await session.execute(
            text(
                "insert into note_attachment (id, note_id, name, mime, size, sha256) "
                "values (:id, :note_id, :name, 'image/png', :size, :sha)"
            ),
            {
                "id": uuid.uuid4(),
                "note_id": note_id,
                "name": name,
                "size": size,
                "sha": sha256,
            },
        )
        await session.commit()


def vault_files(vault: Path, suffix: str = "") -> list[str]:
    """Vault içindeki kullanıcı dosyaları (manifest dizini hariç)."""
    return sorted(
        str(path.relative_to(vault))
        for path in vault.rglob(f"*{suffix}")
        if path.is_file() and path.relative_to(vault).parts[0] != ".forkos-migration"
    )


def target_of(outcome: MigrationOutcome, note_id: str) -> str:
    return outcome.manifest.notes[note_id].target_path


def read_written(vault: Path, outcome: MigrationOutcome, note_id: str) -> tuple[dict, str]:
    content = (vault / target_of(outcome, note_id)).read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(content)
    assert metadata is not None
    return metadata, body


async def source_fingerprint() -> str:
    async with read_only_session() as session:
        snapshot = await load_snapshot(session)
    return snapshot.fingerprint


async def db_rows(sql: str, **params) -> list:
    async with SessionLocal() as session:
        return list((await session.execute(text(sql), params)).all())


# =====================================================================
# 1. Temel migration: kişisel, klasörlü, günlük, proje günlüğü, yer imi
# =====================================================================


async def test_personal_note_migrates_to_inbox_imported(vault: Path) -> None:
    note = await make_note("# Başlıksız fikir\n\nBu bir kişisel not.")

    outcome = await run_apply(vault, "TestVault")

    assert outcome.ready_for_cutover is True
    path = "00 Inbox/Imported/Başlıksız fikir.md"
    assert target_of(outcome, note["id"]) == path
    metadata, body = read_written(vault, outcome, note["id"])
    assert metadata["forkos_id"] == note["id"]
    assert metadata["forkos_type"] == "note"
    assert metadata["forkos_note_kind"] == PERSONAL
    assert metadata["forkos_state"] == "active"
    assert metadata["forkos_pinned"] is False
    assert metadata["forkos_migration_version"] == 1
    assert metadata["forkos_source_body_sha256"] == hashlib.sha256(
        note["body"].encode()
    ).hexdigest()
    assert "Bu bir kişisel not." in body

    entry = outcome.manifest.notes[note["id"]]
    assert entry.status == VERIFIED
    assert entry.created_this_run is True
    assert entry.migrated_body_sha256 == hashlib.sha256(body.strip().encode()).hexdigest()


async def test_nested_folder_hierarchy_is_preserved(vault: Path) -> None:
    programming = await make_folder("Programming")
    backend = await make_folder("Backend", programming)
    note = await make_note("ASP.NET pipeline notları", folder_id=backend)

    outcome = await run_apply(vault, "TestVault")

    assert target_of(outcome, note["id"]) == (
        "00 Inbox/Imported/Programming/Backend/ASP.NET pipeline notları.md"
    )
    assert (vault / target_of(outcome, note["id"])).is_file()
    metadata, _ = read_written(vault, outcome, note["id"])
    assert metadata["forkos_legacy_folder_id"] == str(backend)


async def test_daily_note_migrates_to_daily_folder(vault: Path) -> None:
    async with SessionLocal() as session:
        daily = await note_service.ensure_daily_note(session, date(2026, 3, 4))

    outcome = await run_apply(vault, "TestVault")

    assert target_of(outcome, str(daily.id)) == "10 Daily/2026-03-04.md"
    metadata, _ = read_written(vault, outcome, str(daily.id))
    assert metadata["forkos_note_kind"] == DAILY
    assert metadata["forkos_journal_day"] == "2026-03-04"
    assert metadata["forkos_type"] == "note"


async def test_project_journal_keeps_note_type_and_project_folder(vault: Path) -> None:
    project_id = await make_project("forkOS")
    created = await make_journal_note(project_id, date(2026, 3, 5), "Bugün migration planı çıkarıldı.")
    note_id = str(created["id"])

    outcome = await run_apply(vault, "TestVault")

    assert target_of(outcome, note_id) == "20 Projects/forkOS/Journal/2026-03-05.md"
    metadata, body = read_written(vault, outcome, note_id)
    # Proje günlüğü bir NOT'tur: forkos_type asla "project" olmaz.
    assert metadata["forkos_type"] == "note"
    assert metadata["forkos_note_kind"] == PROJECT_JOURNAL
    assert metadata["forkos_project_id"] == str(project_id)
    assert "migration planı" in body
    assert outcome.metrics["kind_project_journal"] == 1


async def test_bookmark_note_migrates_to_sources_with_context(vault: Path) -> None:
    bookmark_id = await make_bookmark("https://example.com/http2", "HTTP Notları")
    note = await make_note("Sunucu itmesi", source_bookmark_id=bookmark_id)

    outcome = await run_apply(vault, "TestVault")

    assert target_of(outcome, note["id"]) == "60 Sources/Imported/Sunucu itmesi.md"
    metadata, _ = read_written(vault, outcome, note["id"])
    assert metadata["forkos_note_kind"] == BOOKMARK_NOTE
    assert metadata["forkos_source_bookmark_id"] == str(bookmark_id)
    assert metadata["source"] == "https://example.com/http2"
    assert metadata["source_title"] == "HTTP Notları"


def test_kind_precedence_is_deterministic() -> None:
    assert classify_note_kind(_FakeNote(project_id=uuid.uuid4(), journal_day=date(2026, 1, 1))) == (
        PROJECT_JOURNAL
    )
    assert classify_note_kind(_FakeNote(journal_day=date(2026, 1, 1))) == DAILY
    assert classify_note_kind(_FakeNote(source_bookmark_id=uuid.uuid4())) == BOOKMARK_NOTE
    assert classify_note_kind(_FakeNote()) == PERSONAL


class _FakeNote:
    def __init__(self, **values) -> None:
        self.project_id = values.get("project_id")
        self.journal_day = values.get("journal_day")
        self.source_bookmark_id = values.get("source_bookmark_id")


# =====================================================================
# 2. Kimlik ve mevcut proje bilgi notu
# =====================================================================


async def test_project_knowledge_note_is_not_rewritten_as_note(vault: Path) -> None:
    project_id = await make_project("Kariyer")
    await make_journal_note(project_id, date(2026, 4, 1), "Nisan planı")
    knowledge = create_managed_note(
        forkos_id=project_id,
        forkos_type="project",
        title="Kariyer",
        initial_body="# Kariyer\n\nProje bilgi notu.",
    )
    before = (vault / knowledge.relative_path).read_bytes()

    outcome = await run_apply(vault, "TestVault")

    assert (vault / knowledge.relative_path).read_bytes() == before
    knowledge_metadata, _ = parse_frontmatter(
        (vault / knowledge.relative_path).read_text(encoding="utf-8")
    )
    assert knowledge_metadata["forkos_type"] == "project"

    journal = [
        entry for entry in outcome.manifest.notes.values() if entry.note_kind == PROJECT_JOURNAL
    ]
    assert len(journal) == 1
    journal_metadata, _ = parse_frontmatter(
        (vault / journal[0].target_path).read_text(encoding="utf-8")
    )
    assert journal_metadata["forkos_type"] == "note"


async def test_existing_managed_file_with_same_id_is_reused(vault: Path) -> None:
    note = await make_note("Zaten aktarılmış")
    await run_apply(vault, "TestVault")
    original = (vault / "00 Inbox/Imported/Zaten aktarılmış.md").read_bytes()

    # Manifest silinse bile aynı forkos_id'li managed dosya yeniden YAZILMAZ.
    (vault / MANIFEST_DIR / "manifest.json").unlink()

    outcome = await run_apply(vault, "TestVault")

    assert outcome.ready_for_cutover is True
    assert outcome.metrics["notes_copied"] == 0
    assert outcome.metrics["notes_already_migrated"] == 1
    assert (vault / "00 Inbox/Imported/Zaten aktarılmış.md").read_bytes() == original
    assert outcome.manifest.notes[note["id"]].collision == "managed_reuse"


# =====================================================================
# 3. Durum: aktif / arşiv / çöp / pin
# =====================================================================


async def test_archived_and_trashed_notes_are_copied_with_state(vault: Path) -> None:
    archived = await make_note("Arşivlenmiş not")
    trashed = await make_note("Çöpteki not")
    pinned = await make_note("Sabitlenmiş not", pinned=True)

    async with SessionLocal() as session:
        await note_service.archive(session, uuid.UUID(archived["id"]))
    async with SessionLocal() as session:
        await note_service.delete(session, uuid.UUID(trashed["id"]))

    outcome = await run_apply(vault, "TestVault")

    assert outcome.metrics["source_archived"] == 1
    assert outcome.metrics["source_trashed"] == 1
    archived_metadata, _ = read_written(vault, outcome, archived["id"])
    trashed_metadata, _ = read_written(vault, outcome, trashed["id"])
    pinned_metadata, _ = read_written(vault, outcome, pinned["id"])
    assert archived_metadata["forkos_state"] == "archived"
    assert trashed_metadata["forkos_state"] == "trashed"
    assert pinned_metadata["forkos_pinned"] is True
    assert outcome.metrics["notes_verified"] == 3


async def test_trashed_from_archive_state_wins(vault: Path) -> None:
    note = await make_note("Önce arşiv sonra çöp")
    async with SessionLocal() as session:
        await note_service.archive(session, uuid.UUID(note["id"]))
    async with SessionLocal() as session:
        await note_service.delete(session, uuid.UUID(note["id"]))

    outcome = await run_apply(vault, "TestVault")

    metadata, _ = read_written(vault, outcome, note["id"])
    assert metadata["forkos_state"] == "trashed"
    assert metadata["forkos_trashed_from_archive"] is True


# =====================================================================
# 4. Etiketler
# =====================================================================


async def test_tags_are_written_to_frontmatter_and_deduped(vault: Path) -> None:
    note = await make_note("Gövde metni", tags=["Backend", "backend"])
    await set_body(note["id"], "Gövde metni #python")

    outcome = await run_apply(vault, "TestVault")

    metadata, body = read_written(vault, outcome, note["id"])
    assert metadata["tags"] == ["Backend", "python"]
    # Gövdeye etiket metni ENJEKTE EDİLMEZ
    assert body.count("#python") == 1


def test_canonical_tags_dedupes_case_insensitively() -> None:
    assert canonical_tags(["Rust", "rust", " RUST ", "backend"]) == ["backend", "RUST"]


# =====================================================================
# 5. Ekler: iki depolama kuşağı, yeniden yazım, yerleşmemiş ekler
# =====================================================================


async def test_modern_attachment_is_copied_and_image_reference_rewritten(vault: Path) -> None:
    note = await make_note("Şema notu")
    attachment = await attach(note["id"], "architecture.png", PNG)
    await set_body(
        note["id"],
        f"Şema notu\n\n![mimari](/api/notes/{note['id']}/attachments/{attachment['id']})",
    )

    outcome = await run_apply(vault, "TestVault")

    assert (vault / "Attachments/architecture.png").read_bytes() == PNG
    _metadata, written = read_written(vault, outcome, note["id"])
    assert "![[Attachments/architecture.png]]" in written
    assert "/api/notes/" not in written
    assert outcome.metrics["attachments_copied"] == 1
    assert outcome.metrics["attachment_bytes"] == len(PNG)


async def test_normal_link_reference_becomes_aliased_wikilink(vault: Path) -> None:
    note = await make_note("Rapor notu")
    attachment = await attach(note["id"], "report.pdf", b"%PDF-1.4 fake", mime="application/pdf")
    await set_body(
        note["id"], f"[PDF](/api/notes/{note['id']}/attachments/{attachment['id']})"
    )

    outcome = await run_apply(vault, "TestVault")

    _metadata, written = read_written(vault, outcome, note["id"])
    assert "[[Attachments/report.pdf|PDF]]" in written
    assert "![[Attachments/report.pdf]]" not in written


async def test_legacy_jsonb_attachment_is_migrated_without_conversion(vault: Path) -> None:
    note = await make_note("Eski ek notu")
    legacy_id = uuid.uuid4()
    payload = [
        {
            "id": str(legacy_id),
            "name": "ses.m4a",
            "mime": "audio/mp4",
            "size": len(b"legacy-audio"),
            "data": base64.b64encode(b"legacy-audio").decode(),
        }
    ]
    async with SessionLocal() as session:
        await session.execute(
            text("update note set attachments = cast(:payload as jsonb) where id = :id"),
            {"payload": json.dumps(payload), "id": note["id"]},
        )
        await session.commit()
    await set_body(
        note["id"],
        f"Eski ek notu\n\n[kayıt](/api/notes/{note['id']}/attachments/{legacy_id})",
    )

    outcome = await run_apply(vault, "TestVault")

    assert (vault / "Attachments/ses.m4a").read_bytes() == b"legacy-audio"
    _metadata, written = read_written(vault, outcome, note["id"])
    assert "[[Attachments/ses.m4a|kayıt]]" in written
    assert outcome.metrics["attachment_count"] == 1
    # Kaynaktaki legacy JSONB DOKUNULMADAN kalır (dönüşüm çağrılmaz).
    rows = await db_rows("select attachments::text from note where id = :id", id=note["id"])
    assert json.loads(rows[0][0]) == payload


async def test_identical_attachment_content_creates_one_file(vault: Path) -> None:
    first = await make_note("Birinci not")
    second = await make_note("İkinci not")
    await attach(first["id"], "shared.png", PNG)
    await attach(second["id"], "shared.png", PNG)

    outcome = await run_apply(vault, "TestVault")

    files = sorted(path.name for path in (vault / "Attachments").iterdir())
    assert len(files) == 1
    assert outcome.metrics["attachment_count"] == 2
    assert outcome.metrics["attachments_copied"] + outcome.metrics["attachments_reused"] == 2


async def test_same_name_different_content_gets_deterministic_suffix(vault: Path) -> None:
    first = await make_note("Birinci not")
    second = await make_note("İkinci not")
    await attach(first["id"], "ek.png", PNG)
    await attach(second["id"], "ek.png", b"other-bytes")

    outcome = await run_apply(vault, "TestVault")

    names = sorted(path.name for path in (vault / "Attachments").iterdir())
    assert len(names) == 2
    assert all(name.startswith("ek--") for name in names)
    assert outcome.ready_for_cutover is True

    rerun = await run_apply(vault, "TestVault")
    assert sorted(path.name for path in (vault / "Attachments").iterdir()) == names
    assert rerun.metrics["attachments_copied"] == 0
    assert rerun.metrics["attachments_reused"] == 2


async def test_unplaced_attachment_gets_marked_section(vault: Path) -> None:
    note = await make_note("Eki gövdeye koymadım")
    await attach(note["id"], "screenshot.png", PNG)

    outcome = await run_apply(vault, "TestVault")

    _metadata, written = read_written(vault, outcome, note["id"])
    assert UNPLACED_MARKER in written
    assert "## Ekler" in written
    assert "- [[Attachments/screenshot.png]]" in written


async def test_referenced_attachment_is_not_duplicated_in_unplaced_section(vault: Path) -> None:
    note = await make_note("Gövdeye gömülü")
    attachment = await attach(note["id"], "inline.png", PNG)
    await set_body(
        note["id"],
        f"Gövdeye gömülü\n\n![alt](/api/notes/{note['id']}/attachments/{attachment['id']})",
    )

    outcome = await run_apply(vault, "TestVault")

    _metadata, written = read_written(vault, outcome, note["id"])
    assert UNPLACED_MARKER not in written


async def test_missing_blob_fails_note_without_touching_source(vault: Path) -> None:
    note = await make_note("Blob'u kayıp not")
    await insert_attachment_row(note["id"], "kayip.png", 12, "a" * 64)
    before = await source_fingerprint()

    outcome = await run_apply(vault, "TestVault")

    assert outcome.ready_for_cutover is False
    assert outcome.metrics["attachments_failed"] == 1
    assert outcome.metrics["notes_failed"] == 1
    entry = outcome.manifest.notes[note["id"]]
    assert entry.status == FAILED
    assert any("blob bulunamadi" in error for error in entry.errors)
    assert await source_fingerprint() == before


async def test_corrupt_blob_hash_fails_note(vault: Path) -> None:
    note = await make_note("Bozuk blob notu")
    digest = hashlib.sha256(b"expected-content").hexdigest()
    blob = attachment_storage.blob_path(digest)
    blob.parent.mkdir(parents=True, exist_ok=True)
    blob.write_bytes(b"tampered-content")
    await insert_attachment_row(note["id"], "bozuk.png", 16, digest)

    outcome = await run_apply(vault, "TestVault")

    assert outcome.ready_for_cutover is False
    entry = outcome.manifest.notes[note["id"]]
    assert entry.status == FAILED
    assert any("sha256 ile tutmuyor" in error for error in entry.errors)


async def test_source_blobs_and_rows_are_not_deleted(vault: Path) -> None:
    note = await make_note("Kaynak korunmalı")
    await attach(note["id"], "keep.png", PNG)
    digest = hashlib.sha256(PNG).hexdigest()
    before_rows = await db_rows(
        "select id, note_id, name, size, sha256 from note_attachment order by id"
    )

    await run_apply(vault, "TestVault")

    assert attachment_storage.read_blob(digest) == PNG
    assert (
        await db_rows("select id, note_id, name, size, sha256 from note_attachment order by id")
        == before_rows
    )


# =====================================================================
# 6. Wikilink çözümlemesi
# =====================================================================


def test_attachment_ref_rewrite_forms() -> None:
    url = "/api/notes/2f0a9a70-0000-4000-8000-000000000001/attachments/aa11"
    paths = {"aa11": "Attachments/diagram.png"}

    assert rewrite_attachment_refs(f"![d]({url})", paths)[0] == "![[Attachments/diagram.png]]"
    assert rewrite_attachment_refs(f"[PDF]({url})", paths)[0] == "[[Attachments/diagram.png|PDF]]"
    assert rewrite_attachment_refs(f"![d]({url} \"başlık\")", paths)[0] == (
        "![[Attachments/diagram.png]]"
    )
    assert rewrite_attachment_refs(f"bak: {url}", paths)[0] == (
        "bak: [[Attachments/diagram.png]]"
    )
    assert rewrite_attachment_refs(f"`{url}`", paths)[0] == f"`{url}`"
    assert rewrite_attachment_refs("![d](/api/notes/x/attachments/unknown)", paths)[0] == (
        "![d](/api/notes/x/attachments/unknown)"
    )


async def test_wikilink_to_unique_note_stays_simple(vault: Path) -> None:
    await make_note("Hedef not")
    source = await make_note("Kaynakta [[Hedef not]] geçiyor")

    outcome = await run_apply(vault, "TestVault")

    _metadata, written = read_written(vault, outcome, source["id"])
    assert "[[Hedef not]]" in written
    assert outcome.manifest.notes[source["id"]].wikilinks["rewritten"] == 0


async def test_wikilink_alias_is_preserved(vault: Path) -> None:
    await make_note("Kimlik doğrulama")
    source = await make_note("Bkz [[Kimlik doğrulama|auth notu]]")

    outcome = await run_apply(vault, "TestVault")

    _metadata, written = read_written(vault, outcome, source["id"])
    assert "[[Kimlik doğrulama|auth notu]]" in written


async def test_duplicate_title_wikilink_is_expanded_to_path(vault: Path) -> None:
    await make_note("Yinelenen başlık")
    await make_note("Yinelenen başlık")
    source = await make_note("Link: [[Yinelenen başlık]]")

    outcome = await run_apply(vault, "TestVault")

    targets = [
        entry.target_path
        for entry in outcome.manifest.notes.values()
        if entry.title == "Yinelenen başlık"
    ]
    assert len(targets) == 2
    assert targets[0] != targets[1]
    _metadata, written = read_written(vault, outcome, source["id"])
    # İki farklı dosya aynı başlığı taşıdığı için link TAM YOLA genişletilir.
    assert "Link: [[Yinelenen başlık]]" not in written
    assert any(f"[[{path[:-3]}|Yinelenen başlık]]" in written for path in targets)
    assert outcome.manifest.notes[source["id"]].wikilinks["rewritten"] == 1


async def test_unresolved_duplicate_title_link_is_retained(vault: Path) -> None:
    await make_note("Başka not")
    source = await make_note("Link: [[Hiç olmayan başlık]]")

    outcome = await run_apply(vault, "TestVault")

    _metadata, written = read_written(vault, outcome, source["id"])
    assert "[[Hiç olmayan başlık]]" in written
    assert outcome.manifest.notes[source["id"]].wikilinks["unresolved"] == ["Hiç olmayan başlık"]


def test_unresolved_and_non_note_wikilinks_are_retained() -> None:
    note_id = uuid.uuid4()
    body = "[[Hiç olmayan not]] ve [[İş Fırsatı]] ve [[Hedef]]"
    written, stats = rewrite_wikilinks(
        body,
        resolution={"İş Fırsatı": (uuid.uuid4(), "opportunity"), "Hedef": (note_id, "note")},
        note_paths={note_id: "00 Inbox/Imported/Hedef.md"},
        stem_index={"hedef": ("00 Inbox/Imported/Hedef.md",)},
    )
    assert written == body
    assert stats.unresolved == ["Hiç olmayan not"]
    assert stats.non_note == ["İş Fırsatı"]
    assert stats.retained == 1


def test_wikilink_expanded_when_target_filename_differs() -> None:
    note_id = uuid.uuid4()
    written, stats = rewrite_wikilinks(
        "[[Günlük hedefi]]",
        resolution={"Günlük hedefi": (note_id, "note")},
        note_paths={note_id: "10 Daily/2026-01-05.md"},
        stem_index={"2026-01-05": ("10 Daily/2026-01-05.md",)},
    )
    assert written == "[[10 Daily/2026-01-05|Günlük hedefi]]"
    assert stats.rewritten == 1


async def test_note_relations_preserved_as_metadata(vault: Path) -> None:
    project_id = await make_project("İlişkili proje")
    note = await make_note("Projeyle ilgili not", relate_to=project_id)

    outcome = await run_apply(vault, "TestVault")

    metadata, _ = read_written(vault, outcome, note["id"])
    assert metadata["forkos_relations"] == [
        {
            "relation": "notes_about",
            "target_id": str(project_id),
            "target_type": "project",
            "target_title": "İlişkili proje",
        }
    ]


# =====================================================================
# 7. Canvas
# =====================================================================


async def test_empty_canvas_produces_no_sidecar(vault: Path) -> None:
    note = await make_note("Canvas yok")

    outcome = await run_apply(vault, "TestVault")

    assert not (vault / "Attachments/Legacy Canvas").exists()
    metadata, _ = read_written(vault, outcome, note["id"])
    assert "forkos_canvas_sidecar" not in metadata


async def test_populated_canvas_sidecar_is_lossless(vault: Path) -> None:
    scene = {
        "type": "excalidraw",
        "version": 2,
        "elements": [
            {"id": "rect-1", "type": "rectangle", "x": 10, "y": 20, "custom": {"a": 1}}
        ],
        "appState": {"viewBackgroundColor": "#ffffff", "gridSize": 20},
        "files": {"file-1": {"id": "file-1", "dataURL": "data:image/png;base64,AAAA"}},
        "extraField": [1, 2, {"nested": True}],
    }
    note = await make_note("Tuval notu", canvas_state=scene)

    outcome = await run_apply(vault, "TestVault")

    relative = f"Attachments/Legacy Canvas/{note['id']}.excalidraw.json"
    assert json.loads((vault / relative).read_text(encoding="utf-8")) == scene
    metadata, _ = read_written(vault, outcome, note["id"])
    assert metadata["forkos_canvas_sidecar"] == relative

    entry = outcome.manifest.notes[note["id"]]
    canonical = json.dumps(scene, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert entry.canvas["canonical_sha256"] == hashlib.sha256(canonical.encode()).hexdigest()
    assert outcome.metrics["canvas_verified"] == 1


# =====================================================================
# 8. Güvenlik: çakışma, idempotentlik, diverged, bloklar
# =====================================================================


async def test_existing_unmanaged_file_is_never_overwritten(vault: Path) -> None:
    target = vault / "00 Inbox/Imported/Elle yazılmış.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Kullanıcının kendi notu\n", encoding="utf-8")
    note = await make_note("Elle yazılmış")

    outcome = await run_apply(vault, "TestVault")

    assert target.read_text(encoding="utf-8") == "# Kullanıcının kendi notu\n"
    expected = suffixed_path("00 Inbox/Imported/Elle yazılmış.md", uuid.UUID(note["id"]))
    assert target_of(outcome, note["id"]) == expected
    assert (vault / expected).is_file()
    assert outcome.manifest.notes[note["id"]].collision == "unmanaged_file"
    assert outcome.ready_for_cutover is True


async def test_rerun_is_idempotent(vault: Path) -> None:
    await make_note("Tekrar çalıştır")
    attached = await make_note("Ekli tekrar")
    await attach(attached["id"], "tek.png", PNG)

    first = await run_apply(vault, "TestVault")
    files_after_first = vault_files(vault)
    contents = {path: (vault / path).read_bytes() for path in files_after_first}

    second = await run_apply(vault, "TestVault")

    assert first.metrics["notes_copied"] == 2
    assert second.ready_for_cutover is True
    assert second.metrics["notes_copied"] == 0
    assert second.metrics["notes_already_migrated"] == 2
    assert second.metrics["notes_verified"] == 2
    assert vault_files(vault) == files_after_first
    assert all((vault / path).read_bytes() == data for path, data in contents.items())


async def test_user_edit_in_vault_is_flagged_diverged(vault: Path) -> None:
    note = await make_note("Diverged not")
    await run_apply(vault, "TestVault")

    path = vault / "00 Inbox/Imported/Diverged not.md"
    edited = path.read_text(encoding="utf-8") + "\n\nObsidian'da elle ekledim.\n"
    path.write_text(edited, encoding="utf-8")

    rerun = await run_apply(vault, "TestVault")

    assert rerun.ready_for_cutover is False
    assert rerun.manifest.notes[note["id"]].status == DIVERGED
    assert path.read_text(encoding="utf-8") == edited


async def test_duplicate_managed_id_blocks_apply_before_writing(vault: Path) -> None:
    await make_note("Bloklanacak not")
    duplicate_id = str(uuid.uuid4())
    for name in ("A.md", "B.md"):
        (vault / name).write_text(
            f"---\nforkos_id: {duplicate_id}\nforkos_type: note\ntitle: {name}\n---\n# {name}\n",
            encoding="utf-8",
        )

    outcome = await run_apply(vault, "TestVault")

    assert outcome.ready_for_cutover is False
    assert any("vault_identity_conflicts" in blocker for blocker in outcome.blockers)
    assert not (vault / "00 Inbox/Imported/Bloklanacak not.md").exists()
    assert not (vault / MANIFEST_DIR).exists()


async def test_invalid_managed_metadata_blocks_apply(vault: Path) -> None:
    await make_note("Bloklanacak not 2")
    (vault / "bozuk.md").write_text(
        "---\nforkos_id: not-a-uuid\nforkos_type: note\ntitle: Bozuk\n---\n# Bozuk\n",
        encoding="utf-8",
    )

    outcome = await run_apply(vault, "TestVault")

    assert outcome.ready_for_cutover is False
    assert any("vault_managed_metadata" in blocker for blocker in outcome.blockers)
    assert not (vault / "00 Inbox/Imported/Bloklanacak not 2.md").exists()


async def test_interrupted_run_resumes_without_duplicates(
    vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for index in range(3):
        await make_note(f"Kesinti notu {index}")

    original = engine.write_note
    calls = {"count": 0}

    def flaky(vault_root: Path, relative_path: str, content: str):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("kesinti simülasyonu")
        return original(vault_root, relative_path, content)

    monkeypatch.setattr(engine, "write_note", flaky)
    with pytest.raises(RuntimeError):
        await run_apply(vault, "TestVault")

    partial = load_manifest(vault)
    assert partial is not None
    assert len(partial.notes) == 3
    assert len(vault_files(vault, ".md")) == 1

    monkeypatch.setattr(engine, "write_note", original)
    resumed = await run_apply(vault, "TestVault")

    assert resumed.ready_for_cutover is True
    assert resumed.metrics["notes_verified"] == 3
    assert resumed.metrics["notes_already_migrated"] == 1
    assert len(vault_files(vault, ".md")) == 3


async def test_dry_run_writes_nothing(vault: Path) -> None:
    note = await make_note("Kuru çalıştırma")
    await attach(note["id"], "kuru.png", PNG)

    outcome = await run_dry_run(vault, "TestVault")

    assert outcome.mode == DRY_RUN
    assert outcome.ready_for_cutover is False
    assert outcome.metrics["source_total_notes"] == 1
    assert outcome.metrics["notes_planned"] == 1
    assert outcome.metrics["attachment_count"] == 1
    assert target_of(outcome, note["id"]) == "00 Inbox/Imported/Kuru çalıştırma.md"
    assert list(vault.rglob("*")) == []
    assert not (vault / MANIFEST_DIR).exists()


# =====================================================================
# 9. Doğrulama modu
# =====================================================================


async def test_verify_reports_clean_after_apply(vault: Path) -> None:
    await make_note("Doğrulanacak not")
    await run_apply(vault, "TestVault")

    outcome = await run_verify(vault, "TestVault")

    assert outcome.ready_for_cutover is True
    assert outcome.metrics["notes_verified"] == 1
    assert outcome.errors == []


async def test_verify_detects_body_tampering(vault: Path) -> None:
    note = await make_note("Kurcalanacak not")
    await run_apply(vault, "TestVault")

    path = vault / target_of(await run_dry_run(vault, "TestVault"), note["id"])
    path.write_text(
        f"---\nforkos_id: {note['id']}\nforkos_type: note\n"
        "forkos_note_kind: personal\ntitle: Kurcalanacak not\n---\n\nBaşka bir gövde\n",
        encoding="utf-8",
    )

    outcome = await run_verify(vault, "TestVault")

    assert outcome.ready_for_cutover is False
    assert outcome.metrics["notes_failed"] == 1
    assert any("gövde" in error["error"] for error in outcome.errors)


async def test_verify_without_manifest_is_blocked(vault: Path) -> None:
    await make_note("Manifest yok")

    outcome = await run_verify(vault, "TestVault")

    assert outcome.ready_for_cutover is False
    assert any("manifest_exists" in blocker for blocker in outcome.blockers)


# =====================================================================
# 10. Kaynak değişmezliği
# =====================================================================


async def test_migration_never_mutates_source_database(vault: Path) -> None:
    await make_note("Değişmemeli", tags=["korunacak"])
    await make_note("Tuval değişmemeli", canvas_state={"elements": [{"id": "e1"}], "files": {}})
    project_id = await make_project("Değişmez proje")
    await make_journal_note(project_id, date(2026, 5, 1), "Proje günlüğü korunmalı")
    attached = await make_note("Ekli değişmez")
    await attach(attached["id"], "korunacak.png", PNG)
    digest = hashlib.sha256(PNG).hexdigest()

    before = await source_fingerprint()
    before_notes = await db_rows(NOTE_SQL)
    before_events = await db_rows("select count(*) from event")
    before_tags = await db_rows("select entity_id, tag_id from entity_tag order by entity_id, tag_id")
    before_links = await db_rows("select from_id, to_id, relation from link order by from_id, to_id")

    outcome = await run_apply(vault, "TestVault")

    assert outcome.ready_for_cutover is True
    assert outcome.fingerprint_before == outcome.fingerprint_after
    assert await source_fingerprint() == before
    assert await db_rows(NOTE_SQL) == before_notes
    assert await db_rows("select count(*) from event") == before_events
    assert await db_rows(
        "select entity_id, tag_id from entity_tag order by entity_id, tag_id"
    ) == before_tags
    assert await db_rows(
        "select from_id, to_id, relation from link order by from_id, to_id"
    ) == before_links
    assert attachment_storage.read_blob(digest) == PNG


async def test_read_only_session_rejects_writes() -> None:
    with pytest.raises(Exception) as excinfo:
        async with read_only_session() as session:
            await session.execute(text("insert into tag (name) values ('yasak')"))
    assert "read-only" in str(excinfo.value).lower()


# =====================================================================
# 11. Yardımcı birimler
# =====================================================================


def test_sanitize_attachment_name_keeps_valid_extension() -> None:
    assert sanitize_attachment_name("rapor:v2.PDF") == ("rapor-v2.pdf", "rapor-v2", ".pdf")
    assert sanitize_attachment_name("arşiv") == ("arşiv", "arşiv", "")
    assert sanitize_attachment_name("../../etc/passwd") == ("passwd", "passwd", "")


def test_build_body_section_order_is_deterministic() -> None:
    result = build_body(
        _BodyNote("gövde"),
        attachment_paths={"b": "Attachments/b.png", "a": "Attachments/a.png"},
        resolution={},
        note_paths={},
        stem_index={},
    )
    assert result.body.endswith(
        f"{UNPLACED_MARKER}\n\n## Ekler\n\n- [[Attachments/a.png]]\n- [[Attachments/b.png]]"
    )


class _BodyNote:
    def __init__(self, body: str) -> None:
        self.body = body
        self.tags: tuple[str, ...] = ()
