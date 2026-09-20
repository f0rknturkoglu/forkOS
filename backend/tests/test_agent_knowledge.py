import os

import pytest

from app.config import settings
from app.integrations.agent.knowledge import (
    get_brain_status,
    read_vault_note,
    search_vault,
)

pytestmark = pytest.mark.no_database


@pytest.fixture
def mock_vault(tmp_path, monkeypatch):
    vault_dir = tmp_path / "MockVault"
    vault_dir.mkdir()

    # Create subfolders
    (vault_dir / "20 Projects").mkdir()
    (vault_dir / "10 Daily").mkdir()
    (vault_dir / "30 Knowledge").mkdir()
    (vault_dir / ".obsidian").mkdir()
    (vault_dir / ".git").mkdir()
    (vault_dir / ".forkos-migration").mkdir()

    # 1. Managed project note
    proj_md = """---
forkos_id: 3f6f99e0-1234-5678-9abc-def012345678
forkos_type: project
title: forkOS Projesi
tags: [forkos, core]
---

# forkOS Projesi

forkOS yerel bir işletim sistemidir.

## Kararlar

- Streamable HTTP MCP seçildi.
- SQLite yerine direkt tarama seçildi.

## Mimari

FastAPI ve React kullanılmaktadır.
"""
    (vault_dir / "20 Projects" / "forkOS.md").write_text(proj_md, encoding="utf-8")

    # 2. Unmanaged knowledge note
    rust_md = """# Rust Hafıza Güvenliği

Rust dilinde sahiplik (ownership) ve ödünç alma (borrowing) mekanizmaları bellek güvenliğini sağlar.

## Yaşam Süreleri

Lifetimes derleyici tarafından kontrol edilir.
"""
    (vault_dir / "30 Knowledge" / "Rust.md").write_text(rust_md, encoding="utf-8")

    # 3. Daily note
    daily_md = """# 2026-09-20

Bugün Hermes H0 Brain Interface mimarisi tamamlandı.

## Yapılacaklar

- [x] Modelleri yaz
- [ ] Testleri koş
"""
    (vault_dir / "10 Daily" / "2026-09-20.md").write_text(daily_md, encoding="utf-8")

    # 4. Hidden system file (must be ignored)
    (vault_dir / ".obsidian" / "app.json").write_text("{}", encoding="utf-8")
    (vault_dir / ".forkos-migration" / "report.md").write_text("# Secret migration report", encoding="utf-8")

    # Monkeypatch settings
    monkeypatch.setattr(settings, "obsidian_vault_path", str(vault_dir))
    monkeypatch.setattr(settings, "obsidian_vault_name", "TestVault")

    return vault_dir


def test_brain_status(mock_vault):
    status = get_brain_status()
    assert status.configured is True
    assert status.available is True
    assert status.readable is True
    assert status.vault_name == "TestVault"
    assert status.total_markdown_files == 3
    assert status.managed_files_count == 1


def test_search_vault_managed_and_unmanaged(mock_vault):
    # Managed search
    results = search_vault("Streamable")
    assert len(results) == 1
    assert results[0].locator == "3f6f99e0-1234-5678-9abc-def012345678"
    assert results[0].title == "forkOS Projesi"
    assert results[0].matched_heading == "Kararlar"
    assert "Streamable HTTP" in results[0].snippet

    # Unmanaged search
    rust_results = search_vault("sahiplik")
    assert len(rust_results) == 1
    assert rust_results[0].locator == "30 Knowledge/Rust.md"
    assert rust_results[0].title == "Rust Hafıza Güvenliği"
    assert rust_results[0].forkos_id is None
    assert "sahiplik" in rust_results[0].snippet.lower()


def test_search_vault_scope_filter(mock_vault):
    # Search for "FastAPI" in projects
    proj_results = search_vault("FastAPI", scope="projects")
    assert len(proj_results) == 1
    assert "20 Projects" in proj_results[0].relative_path

    # Search for "FastAPI" in daily scope -> empty
    daily_results = search_vault("FastAPI", scope="daily")
    assert len(daily_results) == 0


def test_search_vault_ignores_hidden_system_directories(mock_vault):
    # Search for secret in .forkos-migration
    results = search_vault("Secret migration")
    assert len(results) == 0


def test_read_vault_note_by_forkos_id(mock_vault):
    note = read_vault_note(forkos_id="3f6f99e0-1234-5678-9abc-def012345678")
    assert note.title == "forkOS Projesi"
    assert note.relative_path == "20 Projects/forkOS.md"
    assert note.forkos_id == "3f6f99e0-1234-5678-9abc-def012345678"
    assert "Kararlar" in note.headings
    assert "Streamable HTTP MCP" in note.content
    assert note.truncated is False


def test_read_vault_note_by_relative_path(mock_vault):
    note = read_vault_note(relative_path="30 Knowledge/Rust.md")
    assert note.title == "Rust Hafıza Güvenliği"
    assert note.forkos_id is None
    assert "sahiplik" in note.content


def test_read_vault_note_specific_heading(mock_vault):
    note = read_vault_note(relative_path="20 Projects/forkOS.md", heading="Kararlar")
    assert "Streamable HTTP MCP seçildi." in note.content
    # Content outside this section should not be in the extract
    assert "FastAPI ve React" not in note.content


def test_read_vault_note_path_traversal_rejected(mock_vault):
    with pytest.raises(ValueError, match="VAULT_PATH_ESCAPES|ACCESS_DENIED|KNOWLEDGE_NOT_FOUND"):
        read_vault_note(relative_path="../../etc/passwd")


def test_read_vault_note_system_and_hidden_paths_rejected(mock_vault):
    # Setup test directories & files
    (mock_vault / "Attachments").mkdir(exist_ok=True)
    (mock_vault / "Attachments" / "test.md").write_text("# Attachment Note", encoding="utf-8")
    (mock_vault / "95-ekler").mkdir(exist_ok=True)
    (mock_vault / "95-ekler" / "test.md").write_text("# Ek Note", encoding="utf-8")
    (mock_vault / ".obsidian" / "test.md").write_text("# Obsidian Note", encoding="utf-8")
    (mock_vault / "20 Projects" / ".hidden.md").write_text("# Hidden File", encoding="utf-8")

    # 1. .forkos-migration
    with pytest.raises(ValueError, match="ACCESS_DENIED"):
        read_vault_note(relative_path=".forkos-migration/report.md")

    # 2. .obsidian
    with pytest.raises(ValueError, match="ACCESS_DENIED"):
        read_vault_note(relative_path=".obsidian/test.md")

    # 3. Attachments (case-insensitive)
    with pytest.raises(ValueError, match="ACCESS_DENIED"):
        read_vault_note(relative_path="Attachments/test.md")

    # 4. 95-ekler
    with pytest.raises(ValueError, match="ACCESS_DENIED"):
        read_vault_note(relative_path="95-ekler/test.md")

    # 5. Dot-prefixed file
    with pytest.raises(ValueError, match="ACCESS_DENIED"):
        read_vault_note(relative_path="20 Projects/.hidden.md")

    # 6. Normal managed and unmanaged should still succeed
    managed = read_vault_note(relative_path="20 Projects/forkOS.md")
    assert managed.title == "forkOS Projesi"
    unmanaged = read_vault_note(relative_path="30 Knowledge/Rust.md")
    assert unmanaged.title == "Rust Hafıza Güvenliği"


def test_vault_immutability_during_read(mock_vault):
    target_file = mock_vault / "20 Projects" / "forkOS.md"
    mtime_before = os.path.getmtime(target_file)
    content_before = target_file.read_bytes()

    # Search and read
    search_vault("Streamable")
    read_vault_note(relative_path="20 Projects/forkOS.md")

    mtime_after = os.path.getmtime(target_file)
    content_after = target_file.read_bytes()

    assert mtime_before == mtime_after
    assert content_before == content_after
