"""H5 bilgi sağlığı: eskime, yerine geçme, yeniden yüzey, sınırlar, yazma yok."""

from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal
from app.integrations.review_intelligence import models as ri
from app.integrations.review_intelligence import service as ri_svc
from tests.agent_test_utils import (
    capture_db_content_fingerprint,
    capture_vault_fingerprint,
    forbid_outbound_network,  # noqa: F401  (autouse)
)
from tests.h5_fixtures import ANCHOR, NOW, make_project, write_managed_note
from tests.test_h5_consolidation import patch_h4  # noqa: F401  (yeniden kullanılan betik)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "H5Vault"
    path.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "H5Vault")
    return path


@pytest.fixture(autouse=True)
def reset_vault_index() -> AsyncIterator[None]:
    """Global yönetilen kasa indeksi testler arasında sızmasın (H1/H2/H3 deseni)."""
    from app.integrations.obsidian.service import vault_index

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


async def test_operational_state_newer_than_managed_note_is_stale_candidate(
    db_session: AsyncSession, vault: Path
) -> None:
    """§73/§155: olgusal sinyal; çelişki İDDİASI değil."""
    project = await make_project(db_session, title="forkjob")
    write_managed_note(
        vault,
        "20 Projects/forkjob.md",
        forkos_id=str(project.id),
        body="# forkjob\n\n## Karar\n\nReact ağırlıklı panel.\n",
    )
    # Not dosyası eskide kalsın, kayıt sonradan güncellensin.
    old = time.time() - 40 * 86400
    os.utime(vault / "20 Projects" / "forkjob.md", (old, old))
    project.updated_at = datetime.now(UTC)
    await db_session.commit()

    response = await ri_svc.review_intelligence(
        db_session,
        mode="consolidation_review",
        since=ANCHOR.isoformat(),
        focus_entity_id=str(project.id),
        now=NOW,
    )

    stale = [item for item in response.payload.knowledge_health if item.issue == "possibly_stale"]
    assert stale
    assert stale[0].reason == "operational_state_newer_than_managed_note"
    assert stale[0].support_refs
    assert stale[0].entity_id == str(project.id)


async def test_no_managed_note_means_no_knowledge_candidate(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await make_project(db_session, title="Notu olmayan proje")
    await db_session.commit()

    response = await ri_svc.review_intelligence(
        db_session,
        mode="consolidation_review",
        focus_entity_id=str(project.id),
        now=NOW,
    )

    assert [item for item in response.payload.knowledge_health if item.issue == "possibly_stale"] == []
    assert response.payload.resurface_candidates == []


async def test_supersession_is_bounded_and_candidate_only(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§76-§78/§154: yalnızca ADAY; otomatik geçersiz kılma YOK."""
    project = await make_project(db_session, title="forkjob")
    write_managed_note(
        vault,
        "20 Projects/forkjob.md",
        forkos_id=str(project.id),
        body="# forkjob\n\n## Karar\n\nReact ağırlıklı panel kullanılacak.\n",
    )
    (vault / "10 Daily").mkdir(parents=True, exist_ok=True)
    (vault / "10 Daily" / "2026-09-19.md").write_text(
        "# 19 Eylül\n\nminimum kaynak UI yaklaşımı benimsendi\n", encoding="utf-8"
    )
    await db_session.commit()
    calls = patch_h4(
        monkeypatch,
        candidates=[
            {
                "kind": "decision",
                "text": "minimum kaynak UI yaklaşımı",
                "source_excerpt": "minimum kaynak UI yaklaşımı benimsendi",
            }
        ],
        classify_label="possibly_superseded",
    )

    response = await ri_svc.review_intelligence(
        db_session,
        mode="consolidation_review",
        since=ANCHOR.isoformat(),
        focus_entity_id=str(project.id),
        now=NOW,
    )

    superseded = [item for item in response.payload.knowledge_health if item.issue == "possibly_superseded"]
    assert superseded
    assert superseded[0].reason == "h4_classify:possibly_superseded"
    assert any(ref.startswith("h3:") for ref in superseded[0].support_refs)
    assert len(calls["classify"]) <= ri.MAX_H5_SUPERSESSION_CHECKS
    assert response.source_manifest.h3_evidence_ids


async def test_resurfacing_is_structurally_scoped_and_bounded(
    db_session: AsyncSession, vault: Path
) -> None:
    """§83/§156: rastgele eski not değil; aktif entity'ye bağlı ve yaşlı olan."""
    project = await make_project(db_session, title="Aktif proje")
    write_managed_note(
        vault,
        "20 Projects/aktif.md",
        forkos_id=str(project.id),
        body="# Aktif proje\n\nEski karar notu.\n",
    )
    old = time.time() - 91 * 86400
    os.utime(vault / "20 Projects" / "aktif.md", (old, old))
    await db_session.commit()

    response = await ri_svc.review_intelligence(
        db_session,
        mode="consolidation_review",
        focus_entity_id=str(project.id),
        now=NOW,
    )

    candidates = response.payload.resurface_candidates
    assert candidates
    assert candidates[0].age_days >= ri.RESURFACE_AGE_DAYS
    assert candidates[0].related_entity_id == str(project.id)
    assert any("related_active_entity=true" in reason for reason in candidates[0].reasons)
    assert len(candidates) <= ri.MAX_H5_RESURFACE


async def test_fresh_managed_note_is_not_resurfaced(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await make_project(db_session, title="Taze proje")
    write_managed_note(
        vault, "20 Projects/taze.md", forkos_id=str(project.id), body="# Taze proje\n\nYeni not.\n"
    )
    await db_session.commit()

    response = await ri_svc.review_intelligence(
        db_session, mode="consolidation_review", focus_entity_id=str(project.id), now=NOW
    )

    assert response.payload.resurface_candidates == []


async def test_knowledge_modes_write_nothing(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§154: not yeniden yazılmaz, silinmez, geçersiz kılınmaz."""
    project = await make_project(db_session, title="forkjob")
    note_path = write_managed_note(
        vault,
        "20 Projects/forkjob.md",
        forkos_id=str(project.id),
        body="# forkjob\n\n## Karar\n\nReact ağırlıklı panel.\n",
    )
    (vault / "10 Daily").mkdir(parents=True, exist_ok=True)
    (vault / "10 Daily" / "2026-09-19.md").write_text(
        "# 19 Eylül\n\nminimum kaynak UI yaklaşımı benimsendi\n", encoding="utf-8"
    )
    await db_session.commit()
    patch_h4(
        monkeypatch,
        candidates=[
            {
                "kind": "decision",
                "text": "minimum kaynak UI yaklaşımı",
                "source_excerpt": "minimum kaynak UI yaklaşımı benimsendi",
            }
        ],
        classify_label="possibly_conflicting",
    )

    note_before = note_path.read_text(encoding="utf-8")
    db_before = await capture_db_content_fingerprint(db_session)
    vault_before = capture_vault_fingerprint(vault)

    response = await ri_svc.review_intelligence(
        db_session,
        mode="consolidation_review",
        since=ANCHOR.isoformat(),
        focus_entity_id=str(project.id),
        now=NOW,
    )

    assert note_path.read_text(encoding="utf-8") == note_before
    assert await capture_db_content_fingerprint(db_session) == db_before
    assert capture_vault_fingerprint(vault) == vault_before
    # Aday üretilmiş olabilir ama hiçbir şey DEĞİŞMEDİ.
    assert response.truncated in (True, False)


async def test_knowledge_health_is_bounded(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projects = []
    for index in range(ri.MAX_H5_KNOWLEDGE_HEALTH + 4):
        project = await make_project(db_session, title=f"Proje {index}")
        write_managed_note(
            vault,
            f"20 Projects/p{index}.md",
            forkos_id=str(project.id),
            body=f"# Proje {index}\n\nNot.\n",
        )
        project.updated_at = datetime.now(UTC) + timedelta(seconds=index)
        projects.append(project)
    await db_session.commit()
    patch_h4(monkeypatch, candidates=[])

    response = await ri_svc.review_intelligence(
        db_session, mode="consolidation_review", since=ANCHOR.isoformat(), now=NOW
    )

    assert len(response.payload.knowledge_health) <= ri.MAX_H5_KNOWLEDGE_HEALTH
    if len(response.payload.knowledge_health) >= ri.MAX_H5_KNOWLEDGE_HEALTH:
        assert any("KNOWLEDGE_HEALTH_TRUNCATED" in warning for warning in response.warnings)
