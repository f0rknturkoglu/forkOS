from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.config import settings
from app.db import SessionLocal, engine
from app.integrations.obsidian.frontmatter import (
    extract_title,
    parse_frontmatter,
    render_markdown_with_frontmatter,
)
from app.integrations.obsidian.index import VaultIndex
from app.integrations.obsidian.security import resolve_safe_vault_path, sanitize_filename
from app.integrations.obsidian.service import (
    VaultConflictError,
    create_managed_note,
    get_vault_status,
    resolve_managed_item,
    vault_index,
)
from app.integrations.obsidian.uri import create_note_uri, open_file_uri, search_uri
from app.main import app
from app.scripts.plan_note_vault_migration import (
    format_markdown_report,
    plan_notes_migration,
    resolve_folder_path,
)


@pytest.fixture(autouse=True)
def reset_vault_index():
    """Her test öncesinde global vault_index durumunu sıfırla."""
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


# =====================================================================
# 1. Security & Paths
# =====================================================================

def test_sanitize_filename_removes_illegal_characters():
    dirty = 'Project: Alpha / Beta * Gamma ? <Delta> "Epsilon" | Zeta'
    clean = sanitize_filename(dirty)
    for illegal in [":", "/", "*", "?", "<", ">", '"', "|", "\\"]:
        assert illegal not in clean
    assert "Alpha" in clean
    assert "Beta" in clean


def test_sanitize_filename_preserves_turkish_characters():
    turkish = "Şiir Örneği - Çiçek ve Ilık Bahar Günü"
    clean = sanitize_filename(turkish)
    assert clean == turkish


def test_sanitize_filename_empty_fallback():
    assert sanitize_filename("") == "Untitled"
    assert sanitize_filename("   ") == "Untitled"
    assert sanitize_filename("???///") == "Untitled"


def test_sanitize_filename_length_limit():
    long_name = "A" * 200
    clean = sanitize_filename(long_name, max_length=120)
    assert len(clean) <= 120


def test_resolve_safe_vault_path_valid(tmp_path: Path):
    target = resolve_safe_vault_path(tmp_path, "20 Projects/Subfolder/note.md")
    assert target == (tmp_path / "20 Projects/Subfolder/note.md").resolve()


def test_resolve_safe_vault_path_rejects_absolute_path(tmp_path: Path):
    with pytest.raises(ValueError, match="Mutlak yol"):
        resolve_safe_vault_path(tmp_path, "/etc/passwd")


def test_resolve_safe_vault_path_rejects_traversal(tmp_path: Path):
    with pytest.raises(ValueError, match="Üst dizin"):
        resolve_safe_vault_path(tmp_path, "../../outside.md")

    with pytest.raises(ValueError, match="Üst dizin"):
        resolve_safe_vault_path(tmp_path, "sub/../../../etc/passwd")


def test_resolve_safe_vault_path_rejects_symlink_escape(tmp_path: Path):
    outside_file = tmp_path.parent / "secret_outside.md"
    outside_file.write_text("secret", encoding="utf-8")

    link_inside = tmp_path / "symlink_note.md"
    os.symlink(outside_file, link_inside)

    with pytest.raises(PermissionError, match="Vault dizini dışına"):
        resolve_safe_vault_path(tmp_path, "symlink_note.md")


# =====================================================================
# 2. URI Builder
# =====================================================================

def test_uri_builders():
    open_uri = open_file_uri("My Vault", "20 Projects/Alpha.md")
    assert open_uri == "obsidian://open?vault=My%20Vault&file=20%20Projects/Alpha"

    new_uri = create_note_uri("Work Vault", "Notes/Idea.md", "Initial text")
    assert "obsidian://new?vault=Work%20Vault" in new_uri
    assert "file=Notes/Idea" in new_uri
    assert "content=Initial%20text" in new_uri

    search = search_uri("My Vault", "tag:project")
    assert search == "obsidian://search?vault=My%20Vault&query=tag%3Aproject"


# =====================================================================
# 3. Frontmatter & Markdown
# =====================================================================

def test_frontmatter_parsing_and_rendering():
    raw = (
        "---\n"
        "forkos_id: d3b07384-d113-4603-bb9b-b5a8409f5848\n"
        "forkos_type: project\n"
        "title: My Project\n"
        "created_at: 2026-09-20T00:00:00Z\n"
        "updated_at: 2026-09-20T00:00:00Z\n"
        "---\n"
        "# My Project\n"
        "Body goes here."
    )
    metadata, body = parse_frontmatter(raw)
    assert metadata is not None
    assert metadata["forkos_id"] == "d3b07384-d113-4603-bb9b-b5a8409f5848"
    assert metadata["forkos_type"] == "project"
    assert metadata["title"] == "My Project"
    assert "# My Project\nBody goes here." in body.strip()

    rendered = render_markdown_with_frontmatter(metadata, body)
    assert rendered.startswith("---\n")
    assert "forkos_id: d3b07384-d113-4603-bb9b-b5a8409f5848" in rendered


def test_frontmatter_resilient_to_malformed_yaml():
    malformed = "---\n[this is: invalid: yaml: {{}\n---\nSome body text\n"
    metadata, body = parse_frontmatter(malformed)
    assert metadata is None
    assert "Some body text" in body


def test_extract_title():
    # From frontmatter
    assert extract_title({"title": "Frontmatter Title"}, "content", fallback="Fallback") == "Frontmatter Title"

    # From markdown heading
    assert extract_title({}, "# Heading Title\n\nSome text", fallback="Fallback") == "Heading Title"

    # Fallback
    assert extract_title({}, "No heading, just text", fallback="My Document") == "My Document"


# =====================================================================
# 4. Vault Index & Conflict Detection
# =====================================================================

def test_vault_index_scan_and_conflict_detection(tmp_path: Path):
    vault = tmp_path / "test_vault"
    vault.mkdir()
    projects_dir = vault / "20 Projects"
    projects_dir.mkdir()

    # Valid managed note
    valid_id = str(uuid.uuid4())
    valid_note = projects_dir / "Alpha.md"
    valid_note.write_text(
        f"---\nforkos_id: {valid_id}\nforkos_type: project\ntitle: Alpha\n---\n# Alpha",
        encoding="utf-8",
    )

    # Non-forkos note (should be ignored)
    unrelated_note = vault / "random.md"
    unrelated_note.write_text("# Just a note without frontmatter", encoding="utf-8")

    # Ignored directory content
    obsidian_dir = vault / ".obsidian"
    obsidian_dir.mkdir()
    (obsidian_dir / "workspace.json").write_text("{}", encoding="utf-8")

    # Duplicate forkos_id in two files -> conflict
    duplicate_id = str(uuid.uuid4())
    dup_note1 = projects_dir / "Beta1.md"
    dup_note1.write_text(
        f"---\nforkos_id: {duplicate_id}\nforkos_type: project\ntitle: Beta 1\n---\n# Beta 1",
        encoding="utf-8",
    )
    dup_note2 = projects_dir / "Beta2.md"
    dup_note2.write_text(
        f"---\nforkos_id: {duplicate_id}\nforkos_type: project\ntitle: Beta 2\n---\n# Beta 2",
        encoding="utf-8",
    )

    index = VaultIndex()
    status = index.scan(vault, "TestVault")
    assert status.available is True

    assert index.get_managed_count() == 1
    assert valid_id in index.items
    assert index.items[valid_id].title == "Alpha"
    assert index.items[valid_id].relative_path == "20 Projects/Alpha.md"

    # Conflict check
    assert index.get_conflict_count() == 1
    assert duplicate_id in index.conflicts
    assert len(index.conflicts[duplicate_id]) == 2
    assert duplicate_id not in index.items  # Disputed item excluded from unique index


# =====================================================================
# 5. Vault Service & Managed Note Creation
# =====================================================================

def test_vault_service_status_unconfigured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "obsidian_vault_path", "")
    status = get_vault_status()
    assert not status.configured
    assert not status.available
    assert status.diagnostic is not None


def test_vault_service_status_missing_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    missing_dir = tmp_path / "does_not_exist"
    monkeypatch.setattr(settings, "obsidian_vault_path", str(missing_dir))
    monkeypatch.setattr(settings, "obsidian_vault_name", "MissingVault")

    status = get_vault_status()
    assert status.configured
    assert not status.available
    assert "mevcut değil" in (status.diagnostic or "")


def test_vault_service_create_managed_note_lifecycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(vault))
    monkeypatch.setattr(settings, "obsidian_vault_name", "TestVault")

    status = get_vault_status()
    assert status.configured
    assert status.available
    assert status.writable
    assert status.vault_name == "TestVault"

    project_id = uuid.uuid4()

    # 1. Create note
    item = create_managed_note(
        forkos_id=project_id,
        forkos_type="project",
        title="Yeni Web Sitesi",
        initial_body="Proje detayları burada yer alacak.",
    )
    assert item.forkos_id == str(project_id)
    assert item.forkos_type == "project"
    assert item.title == "Yeni Web Sitesi"
    assert item.relative_path == "20 Projects/Yeni Web Sitesi/Yeni Web Sitesi.md"
    assert "obsidian://open?vault=TestVault" in item.open_uri

    # Verify file content
    created_file = vault / "20 Projects/Yeni Web Sitesi/Yeni Web Sitesi.md"
    assert created_file.exists()
    content = created_file.read_text(encoding="utf-8")
    assert str(project_id) in content
    assert "Proje detayları burada yer alacak." in content

    # 2. Idempotent call with same ID
    item_again = create_managed_note(
        forkos_id=project_id,
        forkos_type="project",
        title="Yeni Web Sitesi",
    )
    assert item_again.relative_path == item.relative_path

    # 3. Collision handling: different ID, same title
    other_id = uuid.uuid4()
    collision_item = create_managed_note(
        forkos_id=other_id,
        forkos_type="project",
        title="Yeni Web Sitesi",
    )
    assert collision_item.forkos_id == str(other_id)
    assert collision_item.relative_path == "20 Projects/Yeni Web Sitesi/Yeni Web Sitesi (1).md"

    # 4. Resolve item
    resolved = resolve_managed_item(str(project_id))
    assert resolved is not None
    assert resolved.title == "Yeni Web Sitesi"

    # 5. Invalid forkos_type
    with pytest.raises(ValueError, match="Desteklenmeyen forkos_type"):
        create_managed_note(
            forkos_id=uuid.uuid4(),
            forkos_type="invalid_type",
            title="Bad Type",
        )


# =====================================================================
# 6. API Endpoints
# =====================================================================

@pytest.mark.no_database
async def test_obsidian_api_endpoints(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    vault = tmp_path / "api_vault"
    vault.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(vault))
    monkeypatch.setattr(settings, "obsidian_vault_name", "ApiVault")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # GET status
        res = await client.get("/api/obsidian/status")
        assert res.status_code == 200
        data = res.json()
        assert data["configured"] is True
        assert data["available"] is True
        assert data["managed_files"] == 0

        # POST create note
        test_id = str(uuid.uuid4())
        create_payload = {
            "forkos_id": test_id,
            "forkos_type": "project",
            "title": "API Test Projesi",
            "initial_body": "API üzerinden oluşturuldu.",
        }
        res = await client.post("/api/obsidian/items", json=create_payload)
        assert res.status_code == 201
        created_data = res.json()
        assert created_data["forkos_id"] == test_id
        assert created_data["relative_path"] == "20 Projects/API Test Projesi/API Test Projesi.md"

        # GET item by ID
        res = await client.get(f"/api/obsidian/items/{test_id}")
        assert res.status_code == 200
        assert res.json()["title"] == "API Test Projesi"

        # GET unknown item
        res = await client.get(f"/api/obsidian/items/{uuid.uuid4()}")
        assert res.status_code == 404

        # POST refresh index
        res = await client.post("/api/obsidian/index/refresh")
        assert res.status_code == 200
        refreshed_data = res.json()
        assert refreshed_data["managed_files"] == 1


# =====================================================================
# 7. Dry-Run Notes Migration Planner
# =====================================================================

def test_dry_run_migration_report_formatting():
    result = {
        "metrics": {
            "total_notes": 10,
            "personal_notes": 5,
            "daily_notes": 3,
            "project_journals": 2,
            "archived_notes": 2,
            "trashed_notes": 1,
            "notes_with_canvas": 1,
            "notes_with_attachments": 4,
            "total_attachment_files": 4,
            "notes_with_wikilinks": 12,
            "potential_filename_collisions": 1,
        },
        "collisions": {
            "00 Inbox/Imported/Duplicate.md": ["id-1", "id-2"],
        },
        "plan": [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "title": "Test Notu",
                "forkos_type": "note",
                "target_path": "00 Inbox/Imported/Test Notu.md",
                "attachments_count": 1,
                "warnings": ["canvas_content"],
            }
        ],
    }

    md = format_markdown_report(result)
    assert "# forkOS Notes -> Obsidian Vault Migration Dry-Run Report" in md
    assert "Toplam Not Sayısı" in md
    assert "10" in md
    assert "00 Inbox/Imported/Test Notu.md" in md
    assert "00 Inbox/Imported/Duplicate.md" in md
    assert "canvas_content" in md


async def _database_available() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("select 1 from note limit 1"))
        return True
    except Exception:
        return False


async def test_plan_notes_migration_database_execution():
    if not await _database_available():
        pytest.skip("Test veritabanı aktif değil")

    note_id = uuid.uuid4()
    async with SessionLocal() as session:
        await session.execute(
            text(
                "insert into entity (id, type, title, search_text) "
                "values (:id, 'note', 'Günlük Notum', '')"
            ),
            {"id": note_id},
        )
        await session.execute(
            text(
                "insert into note (id, body, journal_day, pinned) "
                "values (:id, 'Bugün harika bir gün [[İkinci Not]]', '2026-09-20', false)"
            ),
            {"id": note_id},
        )
        await session.commit()

        # Run dry-run plan
        plan = await plan_notes_migration(session)

        # Assert metrics
        assert plan["metrics"]["total_notes"] >= 1
        assert plan["metrics"]["daily_notes"] >= 1
        assert plan["metrics"]["notes_with_wikilinks"] >= 1

        # Assert target path
        found = [p for p in plan["plan"] if p["note_id"] == str(note_id)]
        assert len(found) == 1
        assert found[0]["target_path"] == "10 Daily/2026-09-20.md"

        # Assert zero mutation: count remains 1
        count_res = await session.execute(text("select count(*) from note where id = :id"), {"id": note_id})
        assert count_res.scalar() == 1


# =====================================================================
# 8. Fix 2: Conflict Fail-Closed Tests
# =====================================================================

@pytest.mark.no_database
async def test_vault_conflict_fail_closed_get_and_post(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    vault = tmp_path / "conflict_vault"
    vault.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(vault))
    monkeypatch.setattr(settings, "obsidian_vault_name", "ConflictVault")

    dup_id = str(uuid.uuid4())
    projects_dir = vault / "20 Projects" / "DuplicateProj"
    projects_dir.mkdir(parents=True)

    file1 = projects_dir / "FileOne.md"
    file1.write_text(
        f"---\nforkos_id: {dup_id}\nforkos_type: project\ntitle: File One\n---\n# One",
        encoding="utf-8",
    )
    file2 = projects_dir / "FileTwo.md"
    file2.write_text(
        f"---\nforkos_id: {dup_id}\nforkos_type: project\ntitle: File Two\n---\n# Two",
        encoding="utf-8",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Refresh to scan the conflict
        res = await client.post("/api/obsidian/index/refresh")
        assert res.status_code == 200
        assert res.json()["conflicts"] == 1
        assert dup_id in res.json()["conflict_details"]

        # 1. Direct service call raises VaultConflictError
        with pytest.raises(VaultConflictError) as exc_info:
            resolve_managed_item(dup_id)
        assert exc_info.value.forkos_id == dup_id
        assert len(exc_info.value.conflicting_paths) == 2

        with pytest.raises(VaultConflictError):
            create_managed_note(forkos_id=dup_id, forkos_type="project", title="Third Try")

        # 2. GET item returns 409 Conflict, not 404
        get_res = await client.get(f"/api/obsidian/items/{dup_id}")
        assert get_res.status_code == 409
        detail = get_res.json()["detail"]
        assert detail["error"] == "conflict"
        assert detail["forkos_id"] == dup_id
        assert len(detail["conflicting_paths"]) == 2

        # 3. POST create returns 409 Conflict and creates NO new file
        files_before = list(vault.rglob("*.md"))
        post_res = await client.post(
            "/api/obsidian/items",
            json={"forkos_id": dup_id, "forkos_type": "project", "title": "Third Try"},
        )
        assert post_res.status_code == 409
        assert post_res.json()["detail"]["error"] == "conflict"

        files_after = list(vault.rglob("*.md"))
        assert len(files_before) == len(files_after) == 2

        # 4. Conflict remains until resolved by user
        res = await client.get("/api/obsidian/status")
        assert res.json()["conflicts"] == 1

        # 5. Resolve conflict by removing file2 and refreshing index
        file2.unlink()
        refresh_res = await client.post("/api/obsidian/index/refresh")
        assert refresh_res.status_code == 200
        assert refresh_res.json()["conflicts"] == 0

        # Now GET returns 200 normally
        resolved_res = await client.get(f"/api/obsidian/items/{dup_id}")
        assert resolved_res.status_code == 200
        assert resolved_res.json()["forkos_id"] == dup_id
        assert resolved_res.json()["title"] == "File One"


# =====================================================================
# 9. Fix 3: Symlink Boundary Containment Tests
# =====================================================================

def test_vault_scanner_symlink_containment(tmp_path: Path):
    vault = tmp_path / "symlink_vault"
    vault.mkdir()

    outside_dir = tmp_path / "outside_dir"
    outside_dir.mkdir()

    # Normal inside file
    normal_id = str(uuid.uuid4())
    normal_file = vault / "normal.md"
    normal_file.write_text(
        f"---\nforkos_id: {normal_id}\nforkos_type: note\ntitle: Normal\n---\n# Normal",
        encoding="utf-8",
    )

    # Outside file with valid forkOS frontmatter
    outside_id = str(uuid.uuid4())
    outside_file = outside_dir / "secret_outside.md"
    outside_file.write_text(
        f"---\nforkos_id: {outside_id}\nforkos_type: note\ntitle: Secret Outside\n---\n# Secret",
        encoding="utf-8",
    )

    # 1. Symlinked file escaping vault
    link_file = vault / "escaped_link.md"
    os.symlink(outside_file, link_file)

    # 2. Symlinked directory escaping vault
    link_dir = vault / "escaped_folder"
    os.symlink(outside_dir, link_dir)

    index = VaultIndex()
    status = index.scan(vault, "TestVault")

    # Only normal_file should be indexed!
    assert status.managed_files == 1
    assert normal_id in index.items
    assert outside_id not in index.items
    assert "escaped_link.md" not in [item.relative_path for item in index.items.values()]


# =====================================================================
# 10. Hardening 1: Metadata Validation Tests
# =====================================================================

def test_vault_metadata_validation_hardening(tmp_path: Path):
    vault = tmp_path / "meta_vault"
    vault.mkdir()

    # 1. Invalid forkos_id (not a valid UUID)
    bad_id_file = vault / "bad_id.md"
    bad_id_file.write_text(
        "---\nforkos_id: not-a-valid-uuid\nforkos_type: note\ntitle: Bad ID\n---\n# Bad ID",
        encoding="utf-8",
    )

    # 2. Invalid forkos_type (typo, e.g. 'porject')
    bad_type_file = vault / "bad_type.md"
    bad_type_file.write_text(
        f"---\nforkos_id: {uuid.uuid4()}\nforkos_type: porject\ntitle: Typo Type\n---\n# Typo",
        encoding="utf-8",
    )

    # 3. Valid note
    valid_id = str(uuid.uuid4())
    valid_file = vault / "valid.md"
    valid_file.write_text(
        f"---\nforkos_id: {valid_id}\nforkos_type: note\ntitle: Valid Note\n---\n# Valid",
        encoding="utf-8",
    )

    index = VaultIndex()
    status = index.scan(vault, "TestVault")

    assert status.managed_files == 1
    assert valid_id in index.items
    assert len(status.invalid_files) == 2
    assert any("geçersiz forkos_id" in err for err in status.invalid_files)
    assert any("geçersiz forkos_type" in err for err in status.invalid_files)
    assert "geçersiz forkOS metaverisi" in (status.diagnostic or "")


# =====================================================================
# 11. Hardening 2: Atomic Creation & No Overwrite Tests
# =====================================================================

def test_create_managed_note_atomic_no_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    vault = tmp_path / "atomic_vault"
    vault.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(vault))
    monkeypatch.setattr(settings, "obsidian_vault_name", "AtomicVault")

    proj_dir = vault / "20 Projects" / "Existing Proj"
    proj_dir.mkdir(parents=True)
    existing_file = proj_dir / "Existing Proj.md"
    existing_file.write_text("# User hand-written notes that must never be overwritten", encoding="utf-8")

    new_id = uuid.uuid4()
    item = create_managed_note(
        forkos_id=new_id,
        forkos_type="project",
        title="Existing Proj",
        initial_body="New forkOS generated body",
    )

    # Existing file must NOT be overwritten
    assert existing_file.read_text(encoding="utf-8") == "# User hand-written notes that must never be overwritten"

    # New note should be created at collision path (1)
    assert item.relative_path == "20 Projects/Existing Proj/Existing Proj (1).md"
    assert (proj_dir / "Existing Proj (1).md").exists()


# =====================================================================
# 12. Fix 5: Migration Planner Folder Hierarchy Tests
# =====================================================================

def test_plan_note_vault_migration_folder_hierarchy():
    f1 = uuid.uuid4()
    f2 = uuid.uuid4()
    f3 = uuid.uuid4()
    f4 = uuid.uuid4()

    folder_map = {
        f1: ("Programming", None),
        f2: ("Backend", f1),
        f3: ("ASP.NET", f2),
        f4: ("Authentication", f3),
    }

    # Root folder
    p1, w1 = resolve_folder_path(f1, folder_map)
    assert p1 == "Programming/"
    assert w1 == []

    # Two-level
    p2, w2 = resolve_folder_path(f2, folder_map)
    assert p2 == "Programming/Backend/"
    assert w2 == []

    # Deep 4-level
    p4, w4 = resolve_folder_path(f4, folder_map)
    assert p4 == "Programming/Backend/ASP.NET/Authentication/"
    assert w4 == []

    # Missing parent
    orphan = uuid.uuid4()
    missing_parent_id = uuid.uuid4()
    folder_map[orphan] = ("OrphanChild", missing_parent_id)
    po, wo = resolve_folder_path(orphan, folder_map)
    assert po == "OrphanChild/"
    assert any("eksik üst klasör" in w for w in wo)

    # Cycle protection (c1 -> c2 -> c1)
    c1 = uuid.uuid4()
    c2 = uuid.uuid4()
    folder_map[c1] = ("Cycle1", c2)
    folder_map[c2] = ("Cycle2", c1)
    pc, wc = resolve_folder_path(c1, folder_map)
    assert any("döngü" in w for w in wc)

    # Turkish / Unicode preservation
    t_id = uuid.uuid4()
    folder_map[t_id] = ("Geliştirme & Araştırma", None)
    pt, wt = resolve_folder_path(t_id, folder_map)
    assert pt == "Geliştirme & Araştırma/"
