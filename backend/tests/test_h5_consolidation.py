"""H5 konsolidasyon: kaynaklı adaylar, yinelenme, açık döngü, bozulma."""

from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal
from app.integrations.local_cognition import models as lc_models
from app.integrations.review_intelligence import service as ri_svc
from tests.agent_test_utils import forbid_outbound_network  # noqa: F401  (autouse)
from tests.h5_fixtures import (
    ANCHOR,
    NOW,
    make_project,
    make_todo,
    write_daily_note,
    write_managed_note,
)

H4_RUN_PATH = "app.integrations.local_cognition.service.run_local_cognition"

NOTE_18 = "forkjob UI için minimum kaynak yaklaşımı benimsendi."
NOTE_18_B = "forkjob UI minimum kaynak yaklaşımı sürüyor."
NOTE_19 = "Yarın H4 modellerini karşılaştır."


def _decision(lane: str, *, input_chars: int = 10) -> lc_models.RouteDecision:
    return lc_models.RouteDecision(
        lane=lane,  # type: ignore[arg-type]
        selected_slot="local-small",
        selected_model="scripted",
        input_chars=input_chars,
        required_capabilities=["structured_extract", "structured_output"],
        reason_codes=["LANE_STRUCTURED_EXTRACT"],
        attempts=[],
        validation_status="valid",
    )


def patch_h4(
    monkeypatch: pytest.MonkeyPatch,
    *,
    candidates: list[dict] | None = None,
    classify_label: str = "unrelated",
    failure_code: str | None = None,
) -> dict[str, list]:
    """H4'ü betikler; çağrılan istekleri kaydeder."""
    calls: dict[str, list] = {"extract": [], "classify": []}

    async def fake_run(request, **_kwargs):
        if isinstance(request, lc_models.ClassifyRequest):
            calls["classify"].append(request)
            return lc_models.LocalCognitionResponse(
                status="success",
                lane="classify",
                result=lc_models.ClassificationResult(label=classify_label),
                route_decision=_decision("classify"),
            )
        calls["extract"].append(request)
        if failure_code is not None:
            return lc_models.LocalCognitionResponse(
                status="needs_escalation",
                lane="structured_extract",
                result=None,
                failure_code=failure_code,
                route_decision=_decision("structured_extract"),
            )
        return lc_models.LocalCognitionResponse(
            status="success",
            lane="structured_extract",
            result=lc_models.ExtractionResult(
                contract="consolidation_candidates_v1", items=list(candidates or [])
            ),
            route_decision=_decision("structured_extract"),
        )

    monkeypatch.setattr(H4_RUN_PATH, fake_run)
    return calls


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


async def test_consolidation_extracts_grounded_candidates_with_recurrence(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§152: aynı karar iki günde geçerse `recurrence_count=2` olur."""
    await make_project(db_session, title="forkjob")
    write_daily_note(vault, "2026-09-18", f"# 18 Eylül\n\n{NOTE_18}\n")
    write_daily_note(vault, "2026-09-19", f"# 19 Eylül\n\n{NOTE_18_B}\n{NOTE_19}\n")
    await db_session.commit()
    patch_h4(
        monkeypatch,
        candidates=[
            # AYNI aday metni, FARKLI alıntılar → iki kaynakta yinelenen karar.
            {"kind": "decision", "text": "forkjob UI minimum kaynak yaklaşımı", "source_excerpt": NOTE_18},
            {"kind": "decision", "text": "forkjob UI minimum kaynak yaklaşımı", "source_excerpt": NOTE_18_B},
            {"kind": "commitment", "text": "H4 modellerini karşılaştır", "source_excerpt": NOTE_19},
        ],
    )

    response = await ri_svc.review_intelligence(
        db_session, mode="consolidation_review", since=ANCHOR.isoformat(), now=NOW
    )
    payload = response.payload

    decision = next(item for item in payload.promotion_candidates if item.kind == "decision")
    assert decision.recurrence_count == 2
    assert len(decision.support_refs) == 2
    assert all(ref.startswith("vault:10 Daily/") for ref in decision.support_refs)
    assert decision.suggested_destination == "general_vault"  # entity kapsamı yok
    assert decision.candidate_id.startswith("cand_")

    assert payload.possible_open_loops
    assert payload.possible_open_loops[0].match_state == "no_exact_match"
    assert payload.daily_notes


async def test_consolidation_maps_candidates_to_entity_scoped_destination(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = await make_project(db_session, title="forkjob")
    await make_todo(db_session, title="forkjob UI", project=project)
    write_daily_note(vault, "2026-09-19", f"# 19 Eylül\n\n{NOTE_18}\n")
    await db_session.commit()
    patch_h4(
        monkeypatch,
        candidates=[{"kind": "decision", "text": "minimum kaynak UI", "source_excerpt": NOTE_18}],
    )

    response = await ri_svc.review_intelligence(
        db_session,
        mode="consolidation_review",
        since=ANCHOR.isoformat(),
        focus_entity_id=str(project.id),
        now=NOW,
    )

    decision = next(item for item in response.payload.promotion_candidates if item.kind == "decision")
    assert decision.suggested_destination == "project_vault"


async def test_commitment_becomes_possible_open_loop_only_on_exact_match(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§66/§67: yalnızca TAM başlık eşleşmesi kanonik Todo sayılır."""
    await make_todo(db_session, title="H4 modellerini karşılaştır")
    write_daily_note(vault, "2026-09-19", f"# 19 Eylül\n\n{NOTE_19}\n")
    await db_session.commit()
    patch_h4(
        monkeypatch,
        candidates=[{"kind": "commitment", "text": "H4 modellerini karşılaştır", "source_excerpt": NOTE_19}],
    )

    response = await ri_svc.review_intelligence(
        db_session, mode="consolidation_review", since=ANCHOR.isoformat(), now=NOW
    )

    loop = response.payload.possible_open_loops[0]
    assert loop.match_state == "exact_match"
    assert loop.matching_todo_id is not None


async def test_unsourced_or_ambiguous_candidates_are_skipped(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§57: kaynağa bağlanamayan veya birden fazla kaynakta geçen aday TAHMİN EDİLMEZ."""
    write_daily_note(vault, "2026-09-18", f"# 18 Eylül\n\n{NOTE_18}\n")
    write_daily_note(vault, "2026-09-19", f"# 19 Eylül\n\n{NOTE_18}\n")
    await db_session.commit()
    patch_h4(
        monkeypatch,
        candidates=[
            {"kind": "decision", "text": "kaynak dışı", "source_excerpt": "bu metin pakette yok"},
            {"kind": "decision", "text": "iki kaynakta geçen", "source_excerpt": NOTE_18},
        ],
    )

    response = await ri_svc.review_intelligence(
        db_session, mode="consolidation_review", since=ANCHOR.isoformat(), now=NOW
    )

    assert response.payload.promotion_candidates == []
    assert any("AMBIGUOUS_CANDIDATE_SOURCE" in warning for warning in response.warnings)


async def test_h4_unavailable_degrades_without_failing(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§79/§153: H4 yoksa H5 deterministik çıktıyı KORUR."""
    await make_project(db_session, title="forkjob", next_action="")
    write_daily_note(vault, "2026-09-19", f"# 19 Eylül\n\n{NOTE_18}\n")
    await db_session.commit()
    patch_h4(monkeypatch, failure_code="MODEL_PROVIDER_UNAVAILABLE")

    response = await ri_svc.review_intelligence(
        db_session, mode="consolidation_review", since=ANCHOR.isoformat(), now=NOW
    )

    assert any("H4_UNAVAILABLE" in warning for warning in response.warnings)
    assert response.payload.promotion_candidates == []
    assert response.payload.daily_notes  # deterministik kısım korunur
    assert response.source_manifest.h4_used is False


async def test_hot_memory_exact_duplicate_is_marked_not_recreated(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§81: yalnızca TAM (normalize) eşleşme `already_present` sayılır.

    Aktif hafıza indeksi ENJEKTE edilir: bu test dedupe KARARINI ölçer, H2'nin
    dosya biçimini değil (o H2 testlerinin işidir).
    """
    from app.integrations.review_intelligence import consolidation as consolidation_svc

    monkeypatch.setattr(
        consolidation_svc.source_svc,
        "active_hot_memories",
        lambda: [
            {
                "memory_id": "5b3e5f0e-0000-4000-8000-000000000001",
                "title": "Minimum kaynak",
                "text": "minimum kaynak yaklaşımı",
                "status": "active",
                "ref": "hot_memory:5b3e5f0e-0000-4000-8000-000000000001",
            }
        ],
    )
    write_daily_note(vault, "2026-09-19", "# 19 Eylül\n\nminimum kaynak yaklaşımı\n")
    await db_session.commit()
    patch_h4(
        monkeypatch,
        candidates=[
            {
                "kind": "constraint",
                "text": "minimum kaynak yaklaşımı",
                "source_excerpt": "minimum kaynak yaklaşımı",
            }
        ],
    )

    response = await ri_svc.review_intelligence(
        db_session, mode="consolidation_review", since=ANCHOR.isoformat(), now=NOW
    )

    candidates = response.payload.promotion_candidates
    assert candidates
    assert candidates[0].status == "already_present"
    assert "HOT_MEMORY_EXACT_DUPLICATE" in candidates[0].warnings
    assert response.source_manifest.hot_memory_checked == 1


async def test_consolidation_writes_nothing(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.agent_test_utils import capture_db_content_fingerprint, capture_vault_fingerprint

    project = await make_project(db_session, title="forkjob")
    write_daily_note(vault, "2026-09-19", f"# 19 Eylül\n\n{NOTE_18}\n")
    write_managed_note(vault, "20 Projects/forkjob.md", forkos_id=str(project.id), body="# forkjob\n")
    await db_session.commit()
    patch_h4(
        monkeypatch,
        candidates=[{"kind": "decision", "text": "minimum kaynak UI", "source_excerpt": NOTE_18}],
    )

    db_before = await capture_db_content_fingerprint(db_session)
    vault_before = capture_vault_fingerprint(vault)

    await ri_svc.review_intelligence(
        db_session, mode="consolidation_review", since=ANCHOR.isoformat(), now=NOW
    )

    assert await capture_db_content_fingerprint(db_session) == db_before
    assert capture_vault_fingerprint(vault) == vault_before


async def test_include_knowledge_false_suppresses_knowledge_signals(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§124: bayrak sessizce yok sayılmaz; kapatınca bilgi okuması YAPILMAZ."""
    project = await make_project(db_session, title="forkjob")
    write_managed_note(
        vault,
        "20 Projects/forkjob.md",
        forkos_id=str(project.id),
        body="# forkjob\n\nKarar.\n",
    )
    old = time.time() - 91 * 86400
    os.utime(vault / "20 Projects" / "forkjob.md", (old, old))
    await db_session.commit()

    with_knowledge = await ri_svc.review_intelligence(
        db_session,
        mode="consolidation_review",
        focus_entity_id=str(project.id),
        include_knowledge=True,
        now=NOW,
    )
    without = await ri_svc.review_intelligence(
        db_session,
        mode="consolidation_review",
        focus_entity_id=str(project.id),
        include_knowledge=False,
        now=NOW,
    )

    assert with_knowledge.payload.resurface_candidates  # kontrol: aksi halde test boş
    assert without.payload.knowledge_health == []
    assert without.payload.resurface_candidates == []
    assert all(
        source.domain != "vault" or "Daily" in source.ref
        for source in without.sources
    )
    step = next(item for item in without.trace if item.step == "knowledge_health_checked")
    assert step.considered == 0
