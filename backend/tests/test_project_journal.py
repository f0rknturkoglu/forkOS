"""Proje günlüğü: operasyonel zaman çizelgesi + Vault köprüsü (PHASE 3).

Günlük METNİ artık forkOS'un değil. Bu testler iki sınırı birlikte korur:

  1. forkOS yalnızca operasyonel olayları gösterir; günlük gövdesini tutmaz.
  2. Günlük dosyası Vault'ta üretilir/çözülür ve PHASE 2 ile taşınmış
     günlükler `forkos_id`'leriyle YENİDEN KULLANILIR (ikinci dosya çıkmaz).
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.config import settings
from app.core.time import local_today
from app.db import SessionLocal
from app.integrations.obsidian.frontmatter import parse_frontmatter
from app.integrations.obsidian.service import vault_index
from app.main import app


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
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "vault"
    path.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "TestVault")
    return path


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def count_legacy_notes() -> int:
    """Dondurulmuş arşivdeki satır sayısı — PHASE 3 boyunca ARTMAZMALIDIR."""
    async with SessionLocal() as session:
        return int((await session.execute(text("select count(*) from note"))).scalar_one())


async def make_project(client: AsyncClient, title: str) -> dict:
    response = await client.post("/api/projects", json={"title": title})
    assert response.status_code == 201, response.text
    return response.json()


async def test_journal_is_operational_timeline_without_note_bodies(
    client: AsyncClient, vault: Path
) -> None:
    """Günlük görünümü olay gruplarıdır; gövde alanı YOKTUR."""
    project = await make_project(client, "Zaman çizelgesi")

    journal = (await client.get(f"/api/projects/{project['id']}/journal")).json()
    assert journal, journal
    assert all("note" not in group for group in journal)
    assert all(set(group) == {"day", "events"} for group in journal)
    verbs = {event["verb"] for group in journal for event in group["events"]}
    assert "project.created" in verbs
    assert not any(verb.startswith("note.") for verb in verbs)


async def test_journal_bridge_creates_one_managed_vault_file(
    client: AsyncClient, vault: Path
) -> None:
    project = await make_project(client, "Günlük projesi")
    day = local_today().isoformat()

    created = await client.post(f"/api/projects/{project['id']}/journal/{day}/obsidian")
    assert created.status_code == 200, created.text
    item = created.json()

    assert item["forkos_type"] == "note"
    assert item["note_kind"] == "project_journal"
    assert item["project_id"] == project["id"]
    assert item["journal_day"] == day
    assert item["relative_path"] == f"20 Projects/Günlük projesi/Journal/{day}.md"
    assert item["open_uri"] == (
        f"obsidian://open?vault=TestVault&file=20%20Projects/G%C3%BCnl%C3%BCk%20projesi/Journal/{day}"
    )

    metadata, _ = parse_frontmatter((vault / item["relative_path"]).read_text(encoding="utf-8"))
    assert metadata is not None
    assert metadata["forkos_id"] == item["forkos_id"]
    assert metadata["forkos_type"] == "note"
    assert metadata["forkos_note_kind"] == "project_journal"
    assert metadata["forkos_project_id"] == project["id"]
    assert metadata["forkos_journal_day"] == day
    # İlişki SUNUCUDA çözülür; proje başlığı frontmatter'a yazılır.
    assert metadata["forkos_relations"] == [
        {
            "relation": "notes_about",
            "target_id": project["id"],
            "target_type": "project",
            "target_title": "Günlük projesi",
        }
    ]

    # İkinci çağrı yeni dosya ÜRETMEZ: kimlik korunur.
    again = await client.post(f"/api/projects/{project['id']}/journal/{day}/obsidian")
    assert again.status_code == 200
    assert again.json()["forkos_id"] == item["forkos_id"]
    assert sorted(p.name for p in (vault / "20 Projects/Günlük projesi/Journal").iterdir()) == [
        f"{day}.md"
    ]

    # Günlük yazmak dondurulmuş arşive satır EKLEMEZ.
    assert await count_legacy_notes() == 0


async def test_journal_bridge_reuses_migrated_journal_file(
    client: AsyncClient, vault: Path
) -> None:
    """PHASE 2 ile taşınmış günlük, kimliğiyle yeniden kullanılır."""
    project = await make_project(client, "Devralan proje")
    day = local_today().isoformat()
    legacy_id = str(uuid.uuid4())

    journal_dir = vault / "00 Inbox/Imported/eski-proje/Journal"
    journal_dir.mkdir(parents=True)
    migrated = journal_dir / f"{day}.md"
    migrated.write_text(
        "---\n"
        f"forkos_id: {legacy_id}\n"
        "forkos_type: note\n"
        "forkos_note_kind: project_journal\n"
        f"forkos_project_id: {project['id']}\n"
        f"forkos_journal_day: '{day}'\n"
        "---\n\nKullanıcının kendi günlük metni.\n",
        encoding="utf-8",
    )

    resolved = await client.post(f"/api/projects/{project['id']}/journal/{day}/obsidian")
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["forkos_id"] == legacy_id
    assert resolved.json()["relative_path"] == "00 Inbox/Imported/eski-proje/Journal/" + f"{day}.md"
    # Kullanıcı metni korunur; dosya yeniden yazılmaz.
    assert "Kullanıcının kendi günlük metni." in migrated.read_text(encoding="utf-8")
    assert len(list(vault.rglob("*.md"))) == 1


async def test_new_journal_follows_existing_project_knowledge_folder(
    client: AsyncClient, vault: Path
) -> None:
    """Proje klasörü yeniden adlandırılmışsa yeni günlük ONUN altına yazılır (§24)."""
    project = await make_project(client, "Taşınmış proje")

    from app.integrations.obsidian.service import create_managed_note

    knowledge = create_managed_note(
        forkos_id=project["id"],
        forkos_type="project",
        title="Taşınmış proje",
    )
    # Kullanıcı klasörü Obsidian'da yeniden adlandırdı: kimlik aynı kalır.
    original_dir = (vault / knowledge.relative_path).parent
    renamed_dir = vault / "20 Projects/Elle Adlandırılmış"
    original_dir.rename(renamed_dir)
    await client.post("/api/obsidian/index/refresh")

    day = local_today().isoformat()
    created = await client.post(f"/api/projects/{project['id']}/journal/{day}/obsidian")
    assert created.status_code == 200, created.text
    assert created.json()["relative_path"] == f"20 Projects/Elle Adlandırılmış/Journal/{day}.md"
    assert (renamed_dir / "Journal" / f"{day}.md").is_file()


async def test_journal_bridge_rejects_future_day_and_unknown_project(
    client: AsyncClient, vault: Path
) -> None:
    project = await make_project(client, "Sınır kontrolü")
    today = local_today()
    future = (today + timedelta(days=1)).isoformat()

    rejected = await client.post(f"/api/projects/{project['id']}/journal/{future}/obsidian")
    assert rejected.status_code == 400

    missing = uuid.uuid4()
    assert (
        await client.post(f"/api/projects/{missing}/journal/{today.isoformat()}/obsidian")
    ).status_code == 404
    assert (await client.get(f"/api/projects/{missing}/journal")).status_code == 404
    assert not list(vault.rglob("*.md"))


async def test_journal_bridge_fails_closed_when_vault_unavailable(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Vault yoksa günlük yazılamaz — legacy DB'ye DÜŞÜLMEZ."""
    monkeypatch.setattr(settings, "obsidian_vault_path", "")
    project = await make_project(client, "Vaultsuz proje")

    response = await client.post(
        f"/api/projects/{project['id']}/journal/{local_today().isoformat()}/obsidian"
    )
    assert response.status_code == 503
    assert await count_legacy_notes() == 0
