"""A4: Semantic Promotion & Durable Memory kapsamlı testleri.

Test edilen alanlar:
1. Gizlilik vetosu (opt-out kalıpları -> candidate oluşturulmaz)
2. Candidate key kararlılığı ve normalizasyon
3. Obsidian Vault kartı oluşturma, atomik yazma, sır koruması
4. Eklemeli (additive) supersession ve türetilmiş durum
5. Terfi kapıları (SEMANTIC_REVIEW_REQUIRED ve optimistik revizyon)
6. A2 önyükleme entegrasyonu ve kaynak tazeliği
7. MCP araçları (semantic_memory_candidates, semantic_memory_promote)
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.models import Event
from app.db import SessionLocal
from app.integrations.agent.mcp import mcp_server
from app.integrations.local_cognition.models import StructuredExtractRequest
from app.integrations.local_cognition.prompts import build_user_prompt
from app.integrations.obsidian import hot_memory as hot_storage
from app.integrations.obsidian import semantic_memory as sem_storage
from app.integrations.review_intelligence.sources import sealed_episode_items
from app.modules.agent_continuity.models import AgentSessionSource
from app.modules.agent_continuity.service import (
    _collect_identity,
    check_source_freshness,
)
from app.modules.agent_episode.models import (
    AgentSessionEpisode,
    AgentSessionEpisodeItem,
    AgentSessionEpisodeTurn,
)
from app.modules.agent_lifecycle.models import AgentSession
from app.modules.semantic_memory import service as sem_svc
from app.modules.semantic_memory.models import AgentSemanticCandidate
from app.modules.semantic_memory.policy import (
    compute_candidate_key,
    compute_candidate_revision,
    is_privacy_blocked,
    resolve_destination,
)
from app.modules.semantic_memory.schemas import (
    SemanticCandidateConfirmIn,
    SemanticCandidatePromoteIn,
    SemanticCandidateRefreshIn,
)


def _load_eval_fixture() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "a4_semantic_eval_v1.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_privacy_opt_out_eval():
    """Gizlilik opt-out kalıplarının deterministik olarak yakalandığını doğrular."""
    data = _load_eval_fixture()
    for case in data["privacy_opt_out_cases"]:
        assert is_privacy_blocked(case["input"]) == case["should_block"], (
            f"Failed for: {case['input']}"
        )


def test_candidate_key_stability():
    """Candidate key'in boşluk ve büyük/küçük harf değişimlerinden etkilenmediğini doğrular."""
    data = _load_eval_fixture()
    for case in data["candidate_key_stability_cases"]:
        k1 = compute_candidate_key(
            case["kind"],
            case["scope"],
            case["scope_project"],
            case["subject_key"],
            case["statement_1"],
        )
        k2 = compute_candidate_key(
            case["kind"],
            case["scope"],
            case["scope_project"],
            case["subject_key"],
            case["statement_2"],
        )
        if case["expected_match"]:
            assert k1 == k2, f"Keys should match: {case['statement_1']} vs {case['statement_2']}"
        else:
            assert k1 != k2, f"Keys should differ: {case['statement_1']} vs {case['statement_2']}"


@pytest.mark.no_database
def test_destination_eval():
    for case in _load_eval_fixture()["destination_routing_cases"]:
        assert resolve_destination(case["kind"], case["scope"], None) == case["expected"]


def test_semantic_card_atomic_creation_and_parse(tmp_path: Path):
    """30 Knowledge/Memory/ altına kart yazma, okuma ve non-overwrite kuralını doğrular."""
    card_id = str(uuid.uuid4())
    card = sem_storage.create_semantic_card(
        tmp_path,
        card_id=card_id,
        kind="preference",
        title="TypeScript Tercihi",
        statement="Projede TypeScript ve React tercih edilir.",
        scope="global",
        primary_evidence_class="explicit_user",
        evidence_refs=["event:123"],
    )

    assert card.card_id == card_id
    assert card.kind == "preference"
    assert card.effective_status == "active"
    assert "30 Knowledge/Memory" in card.relative_path

    # Okuma testi
    read_card = sem_storage.read_semantic_card(tmp_path, card_id)
    assert read_card is not None
    assert read_card.title == "TypeScript Tercihi"
    assert read_card.statement == "Projede TypeScript ve React tercih edilir."

    # Üzerine yazma yasağı: aynı card_id ile tekrar yazmaya çalışınca hata vermeli
    with pytest.raises(sem_storage.SemanticStorageError) as exc_info:
        sem_storage.create_semantic_card(
            tmp_path,
            card_id=card_id,
            kind="preference",
            title="TypeScript Tercihi 2",
            statement="Farklı metin.",
        )
    assert exc_info.value.code == "SEMANTIC_CARD_CONFLICT"


def test_secret_safety_rejection(tmp_path: Path):
    """Sır veya API anahtarı içeren kartların yazılmasının engellendiğini doğrular."""
    fake_secret = "sk-" + "a" * 25
    with pytest.raises(sem_storage.SemanticStorageError) as exc_info:
        sem_storage.create_semantic_card(
            tmp_path,
            title="Gizli Bilgi",
            statement=f"Burada bir OpenAI anahtarı var: {fake_secret}",
            kind="reference",
        )
    assert exc_info.value.code == "SECRET_LEAKAGE"


def test_additive_supersession_derived_status(tmp_path: Path):
    """Eski kartın yeni kart tarafından yerine geçildiğinde efektik durumunun 'superseded' olduğunu doğrular."""
    case = _load_eval_fixture()["supersession_cases"][0]
    old_id = case["card_old"]["card_id"]
    new_id = case["card_new"]["card_id"]

    sem_storage.create_semantic_card(
        tmp_path,
        card_id=old_id,
        kind="preference",
        title="Pages Router",
        statement=case["card_old"]["statement"],
    )

    sem_storage.create_semantic_card(
        tmp_path,
        card_id=new_id,
        kind="preference",
        title="App Router",
        statement=case["card_new"]["statement"],
        supersedes=case["card_new"]["supersedes"],
    )

    cards = sem_storage.scan_semantic_cards(tmp_path)
    cards_by_id = {c.card_id: c for c in cards}

    assert cards_by_id[old_id].effective_status == case["expected_old_status"]
    assert cards_by_id[new_id].effective_status == case["expected_new_status"]


@pytest.mark.no_database
def test_consolidation_prompt_uses_real_contract():
    prompt = build_user_prompt(
        StructuredExtractRequest(
            lane="structured_extract",
            contract="consolidation_candidates_v1",
            text="Kullanıcı açıkça bir tercih belirtti.",
        )
    )
    for kind in (
        "decision",
        "lesson",
        "commitment",
        "goal",
        "constraint",
        "project_knowledge",
        "reference",
        "identity",
        "preference",
        "correction",
    ):
        assert kind in prompt
    assert "verbatim" in prompt
    assert "untrusted" in prompt


@pytest.mark.no_database
def test_semantic_profile_project_isolation(tmp_path: Path):
    global_card = sem_storage.create_semantic_card(
        tmp_path,
        kind="preference",
        title="Global",
        statement="Genel tercih",
        scope="global",
    )
    project_a = sem_storage.create_semantic_card(
        tmp_path,
        kind="preference",
        title="A",
        statement="A tercihi",
        scope="project",
        scope_project="a",
    )
    project_b = sem_storage.create_semantic_card(
        tmp_path,
        kind="preference",
        title="B",
        statement="B tercihi",
        scope="project",
        scope_project="b",
    )
    by_scope = {"global": global_card.card_id, "a": project_a.card_id, "b": project_b.card_id}
    for case in _load_eval_fixture()["scope_isolation_cases"]:
        visible = {
            c.card_id
            for c in sem_storage.get_semantic_profile(tmp_path, case["session_project"]).preferences
        }
        assert visible == {by_scope[key] for key in case["visible"]}


@pytest.mark.asyncio
async def test_h5_sealed_episode_reads_real_item_text():
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        owner = AgentSession(
            session_key=f"h5-{uuid.uuid4().hex[:12]}",
            status="active",
            schema_version=1,
            platform="test",
            harness="hermes",
            first_seen_at=now,
            start_seen_at=now,
            last_seen_at=now,
        )
        session.add(owner)
        await session.flush()
        episode = AgentSessionEpisode(
            session_id=owner.id,
            status="sealed",
            turn_count=1,
            item_count=1,
            started_at=now,
            sealed_at=now,
            expires_at=now + timedelta(days=1),
        )
        session.add(episode)
        await session.flush()
        turn = AgentSessionEpisodeTurn(
            episode_id=episode.id,
            turn_key="h5-t1",
            status="extracted",
            turn_digest="d" * 64,
            item_count=1,
            delivered_at=now,
            semantic_memory_eligible=True,
        )
        session.add(turn)
        await session.flush()
        session.add(
            AgentSessionEpisodeItem(
                episode_id=episode.id,
                episode_turn_id=turn.id,
                ordinal=0,
                kind="session_decision",
                text="Gerçek model text alanı",
                evidence_class="turn_derived",
                support_refs=[],
                source_role="user",
                evidence_digest="a" * 64,
            )
        )
        await session.flush()
        rows = await sealed_episode_items(session)
        assert rows[0]["text"] == "Gerçek model text alanı"
        assert rows[0]["semantic_memory_eligible"] is True


@pytest.mark.asyncio
async def test_include_events_controls_canonical_candidate_generation(monkeypatch):
    from app.integrations.local_cognition import service as lc_svc

    async def h4_candidates(_request):
        return SimpleNamespace(
            status="success",
            result=SimpleNamespace(
                items=[
                    {
                        "kind": "decision",
                        "text": "Haftalık değerlendirme tamamlandı.",
                        "source_excerpt": "review.completed: Haftalık değerlendirme",
                    },
                ]
            ),
        )

    monkeypatch.setattr(lc_svc, "run_local_cognition", h4_candidates)
    async with SessionLocal() as session:
        session.add(
            Event(
                entity_id=None,
                entity_type=None,
                verb="review.completed",
                payload={"title": "Haftalık değerlendirme"},
                occurred_at=datetime.now(UTC),
            )
        )
        await session.commit()
        disabled = await sem_svc.refresh_candidates(
            session, SemanticCandidateRefreshIn(include_episodes=False, include_events=False)
        )
        assert disabled.created_count == 0
        enabled = await sem_svc.refresh_candidates(
            session, SemanticCandidateRefreshIn(include_episodes=False, include_events=True)
        )
        assert enabled.created_count == 1
        candidate = (await sem_svc.list_candidates(session)).items[0]
        assert candidate.primary_evidence_class == "canonical_source"
        assert candidate.evidence_refs[0]["ref"].startswith("event:")


@pytest.mark.asyncio
async def test_candidate_workflow_service(monkeypatch, tmp_path: Path):
    """Aday yaşam döngüsü: ingest -> confirm/reject -> promote ve güvenlik kapıları."""
    # Obsidian vault kökünü tmp_path'e bağla
    monkeypatch.setattr(sem_storage, "readable_root", lambda: tmp_path)
    monkeypatch.setattr(sem_storage, "writable_root", lambda: tmp_path)

    async with SessionLocal() as db_session:
        now = datetime.now(UTC)
        # 1. Oturum ve epizot hazırla
        session_row = AgentSession(
            session_key=f"sess_{uuid.uuid4().hex[:12]}",
            status="active",
            schema_version=1,
            platform="test",
            harness="hermes",
            first_seen_at=now,
            start_seen_at=now,
            last_seen_at=now,
        )
        db_session.add(session_row)
        await db_session.flush()

        episode = AgentSessionEpisode(
            session_id=session_row.id,
            status="sealed",
            turn_count=2,
            item_count=2,
            started_at=now,
            sealed_at=now,
            expires_at=now + timedelta(days=1),
        )
        db_session.add(episode)
        await db_session.flush()

        turn = AgentSessionEpisodeTurn(
            episode_id=episode.id,
            turn_key="turn-1",
            status="extracted",
            turn_digest="d" * 64,
            item_count=3,
            delivered_at=now,
            semantic_memory_eligible=True,
        )
        db_session.add(turn)
        await db_session.flush()

        # İki madde ekle: biri model-derived (onaysız terfi edemez), biri explicit-user
        item1 = AgentSessionEpisodeItem(
            episode_id=episode.id,
            episode_turn_id=turn.id,
            ordinal=1,
            kind="session_decision",
            text="Karar: SQLite yerine PostgreSQL kullanılacak.",
            evidence_class="turn_derived",
            support_refs=[],
            source_role="assistant",
            evidence_digest="a" * 64,
        )
        item2 = AgentSessionEpisodeItem(
            episode_id=episode.id,
            episode_turn_id=turn.id,
            ordinal=2,
            kind="next_focus",
            text="Kullanıcı şunu açıkça söyledi: make test ile doğrula.",
            evidence_class="canonical_supported",
            support_refs=[{"source_id": "project:1", "source_type": "project"}],
            source_role="user",
            evidence_digest="b" * 64,
        )
        # Bir de gizlilik vetolu madde ekle
        item3 = AgentSessionEpisodeItem(
            episode_id=episode.id,
            episode_turn_id=turn.id,
            ordinal=3,
            kind="session_decision",
            text="Bunu hafızaya alma: geçici token 12345.",
            evidence_class="turn_derived",
            support_refs=[],
            source_role="user",
            evidence_digest="c" * 64,
        )
        db_session.add_all([item1, item2, item3])
        await db_session.commit()

        from app.integrations.local_cognition import service as lc_svc

        async def h4_candidates(_request):
            return SimpleNamespace(
                status="success",
                result=SimpleNamespace(
                    items=[
                        {
                            "kind": "decision",
                            "text": "Karar: SQLite yerine PostgreSQL kullanılacak.",
                            "source_excerpt": "Karar: SQLite yerine PostgreSQL kullanılacak.",
                        },
                        {
                            "kind": "commitment",
                            "text": "make test ile doğrula.",
                            "source_excerpt": "Kullanıcı şunu açıkça söyledi: make test ile doğrula.",
                        },
                    ]
                ),
            )

        monkeypatch.setattr(lc_svc, "run_local_cognition", h4_candidates)

        # 2. Refresh çağrısı
        refresh_res = await sem_svc.refresh_candidates(
            db_session, SemanticCandidateRefreshIn(include_episodes=True, include_events=False)
        )
        # item3 gizlilik nedeniyle elenmeli, item1 ve item2 oluşturulmalı
        assert refresh_res.created_count == 2

        # Adayları listele
        cand_list = await sem_svc.list_candidates(db_session)
        assert cand_list.total == 2

        c_model = next(c for c in cand_list.items if "PostgreSQL" in c.statement)
        c_user = next(c for c in cand_list.items if "make test" in c.statement)

        assert c_model.status == "needs_review"
        assert c_user.status == "ready"

        # 3. Model-derived adayı direkt promote etmeyi dene -> SEMANTIC_REVIEW_REQUIRED hatası almalı!
        with pytest.raises(HTTPException) as exc_info:
            await sem_svc.promote_candidate(
                db_session,
                c_model.id,
                SemanticCandidatePromoteIn(expected_revision=c_model.revision),
            )
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "SEMANTIC_REVIEW_REQUIRED"

        # 4. Model-derived adayı önce kullanıcı olarak onayla (confirm)
        confirmed_c_model = await sem_svc.confirm_candidate(
            db_session, c_model.id, SemanticCandidateConfirmIn(expected_revision=c_model.revision)
        )
        assert confirmed_c_model.status == "ready"
        assert confirmed_c_model.reviewed_by == "user"

        # 5. Artık onaylı adayı promote et
        promote_res = await sem_svc.promote_candidate(
            db_session,
            c_model.id,
            SemanticCandidatePromoteIn(expected_revision=confirmed_c_model.revision),
        )
        assert promote_res.status == "promoted"
        assert promote_res.card_id is not None
        assert promote_res.destination == "durable_vault"

        # Diskte kart dosyasının gerçekten oluştuğunu kontrol et
        created_card = sem_storage.read_semantic_card(tmp_path, promote_res.card_id)
        assert created_card is not None
        assert "PostgreSQL" in created_card.statement

        # 6. Explicit-user adayı kullanıcı onayı gerektirmeden terfi edebilmeli
        promote_user_res = await sem_svc.promote_candidate(
            db_session,
            c_user.id,
            SemanticCandidatePromoteIn(expected_revision=c_user.revision),
        )
        assert promote_user_res.status == "owner_action_required"


@pytest.mark.asyncio
async def test_a2_bootstrap_semantic_profile_and_freshness(monkeypatch, tmp_path: Path):
    """A2 bootstrap identity toplama ve source freshness kontrolünün semantik kartları desteklediğini doğrular."""
    monkeypatch.setattr(sem_storage, "readable_root", lambda: tmp_path)

    # Bir düzeltme ve bir tercih kartı oluştur
    card1 = sem_storage.create_semantic_card(
        tmp_path,
        kind="correction",
        title="Düzeltme: port 5433",
        statement="PostgreSQL portu her zaman 5433 olmalıdır.",
    )
    sem_storage.create_semantic_card(
        tmp_path,
        kind="preference",
        title="Tercih: Ruff linter",
        statement="Linter olarak Ruff tercih edilir.",
    )
    sem_storage.create_semantic_card(
        tmp_path,
        kind="identity",
        title="Kimlik",
        statement="Yazılım geliştiricisiyim.",
    )
    sem_storage.create_semantic_card(
        tmp_path,
        kind="constraint",
        title="Kısıt",
        statement="Veriler yalnız yerelde kalmalı.",
    )
    sem_storage.create_semantic_card(
        tmp_path,
        kind="goal",
        title="Hedef",
        statement="Uygulamayı sürdürülebilir tut.",
    )

    # 1. Identity fonksiyonu kartları toplamalı
    identity, degraded, sem_cards = await _collect_identity(None)
    assert "PostgreSQL portu her zaman 5433 olmalıdır." in identity.explicit_corrections
    assert "Linter olarak Ruff tercih edilir." in identity.durable_preferences
    assert "Kimlik: Yazılım geliştiricisiyim." in identity.durable_preferences
    assert "Veriler yalnız yerelde kalmalı." in identity.interaction_conventions
    assert "Uygulamayı sürdürülebilir tut." in identity.long_running_goals
    assert len(identity.interaction_conventions) <= 3
    assert len(sem_cards) >= 2

    # 2. Source freshness kontrolü
    fresh_source = AgentSessionSource(
        session_id=1,
        source_id=f"semantic_memory:{card1.card_id}",
        source_type="semantic_memory",
        source_version=card1.revision,
        delivered_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
    )
    is_fresh, title = await check_source_freshness(None, fresh_source)
    assert is_fresh is True
    assert title == card1.title

    # Bayat revizyon testi
    stale_source = AgentSessionSource(
        session_id=1,
        source_id=f"semantic_memory:{card1.card_id}",
        source_type="semantic_memory",
        source_version="stale_revision_hash_12345",
        delivered_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
    )
    is_stale, _ = await check_source_freshness(None, stale_source)
    assert is_stale is False


@pytest.mark.asyncio
async def test_a2_semantic_supersession_expiry_and_correction_freshness(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setattr(sem_storage, "readable_root", lambda: tmp_path)
    monkeypatch.setattr(hot_storage, "readable_root", lambda: tmp_path)
    old = sem_storage.create_semantic_card(
        tmp_path,
        kind="preference",
        title="Eski",
        statement="Eski tercih",
    )
    expired = sem_storage.create_semantic_card(
        tmp_path,
        kind="preference",
        title="Süresi dolmuş",
        statement="Geçici tercih",
        valid_to=datetime(2020, 1, 1, tzinfo=UTC),
    )
    sem_storage.create_semantic_card(
        tmp_path,
        kind="preference",
        title="Yeni",
        statement="Yeni tercih",
        supersedes=[old.card_id],
    )
    for card in (old, expired):
        source = AgentSessionSource(
            session_id=1,
            source_id=f"semantic_memory:{card.card_id}",
            source_type="semantic_memory",
            source_version=card.revision,
            delivered_at=datetime.now(UTC),
            expires_at=datetime.now(UTC),
        )
        fresh, _ = await check_source_freshness(None, source)
        assert fresh is False

    correction = hot_storage.create_memory(
        tmp_path,
        kind="correction",
        title="Düzeltme",
        text="Doğru bilgi",
        importance=3,
        source_mode="explicit_user",
    )
    correction_source = AgentSessionSource(
        session_id=1,
        source_id=f"hot_memory:{correction.memory_id}",
        source_type="hot_memory",
        source_version=correction.revision,
        delivered_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
    )
    fresh, title = await check_source_freshness(None, correction_source)
    assert fresh is True and title == "Düzeltme"


@pytest.mark.asyncio
async def test_mcp_tools_semantic_memory(monkeypatch, tmp_path: Path):
    """MCP araçları: semantic_memory_candidates ve semantic_memory_promote."""
    monkeypatch.setattr(sem_storage, "readable_root", lambda: tmp_path)
    monkeypatch.setattr(sem_storage, "writable_root", lambda: tmp_path)

    # Doğrudan DB'ye bir aday ekle
    cand_id = uuid.uuid4()
    now = datetime.now(UTC)
    rev = compute_candidate_revision(cand_id, "test_cand_key_1", "needs_review", 1, now)
    async with SessionLocal() as db_session:
        cand = AgentSemanticCandidate(
            id=cand_id,
            candidate_key="test_cand_key_1",
            kind="preference",
            statement="Kullanıcı Vim tuş dizilimini tercih eder.",
            scope="global",
            suggested_destination="durable_vault",
            primary_evidence_class="model_derived",
            evidence_refs=[],
            observed_at=now,
            status="needs_review",
            recurrence_count=1,
            first_seen_at=now,
            last_seen_at=now,
            revision=rev,
        )
        db_session.add(cand)
        await db_session.commit()

    # 1. semantic_memory_candidates MCP aracını çağır
    registered = {tool.name: tool for tool in await mcp_server.list_tools()}
    assert "semantic_memory_candidates" in registered
    assert "semantic_memory_promote" in registered

    # semantic_memory_candidates testi
    result = await mcp_server.call_tool("semantic_memory_candidates", {"status": "needs_review"})
    assert result.is_error is False
    assert "Vim" in result.content[0].text

    # 2. semantic_memory_promote MCP aracını çağır (onaysız -> hata almalı)
    with pytest.raises(Exception) as exc_info:
        await mcp_server.call_tool(
            "semantic_memory_promote",
            {"candidate_id": str(cand_id), "expected_revision": rev},
        )
    assert "SEMANTIC_REVIEW_REQUIRED" in str(exc_info.value)


async def _candidate(
    session,
    *,
    status="ready",
    destination="durable_vault",
    statement="Kalıcı tercih",
    kind="preference",
    evidence="explicit_user",
    observed_at=None,
):
    now = datetime.now(UTC)
    cid = uuid.uuid4()
    key = uuid.uuid4().hex
    row = AgentSemanticCandidate(
        id=cid,
        candidate_key=key,
        kind=kind,
        statement=statement,
        scope="global",
        suggested_destination=destination,
        primary_evidence_class=evidence,
        evidence_refs=[],
        observed_at=observed_at or now,
        status=status,
        recurrence_count=1,
        first_seen_at=now,
        last_seen_at=now,
        revision=compute_candidate_revision(cid, key, status, 1, now),
    )
    session.add(row)
    await session.commit()
    return row


@pytest.mark.asyncio
async def test_missing_canonical_source_stales_candidate_before_promotion():
    async with SessionLocal() as session:
        row = await _candidate(
            session,
            evidence="canonical_source",
            statement="Kaynağı kaybolmuş kanonik iddia",
        )
        row.evidence_refs = [{"ref": "event:999999999"}]
        await session.commit()
        original_revision = row.revision
        with pytest.raises(HTTPException) as failure:
            await sem_svc.promote_candidate(
                session, row.id, SemanticCandidatePromoteIn(expected_revision=original_revision)
            )
        assert failure.value.detail["code"] == "SEMANTIC_SOURCE_STALE"
        await session.refresh(row)
        assert row.status == "stale"
        assert row.revision != original_revision


@pytest.mark.asyncio
async def test_promotion_state_and_destination_matrix(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sem_storage, "writable_root", lambda: tmp_path)
    monkeypatch.setattr(hot_storage, "writable_root", lambda: tmp_path)
    async with SessionLocal() as session:
        for case in _load_eval_fixture()["promotion_gate_cases"]:
            if case["can_promote"]:
                assert case["status"] == "ready"
            else:
                assert case["status"] != "ready"
        for status, evidence, expected in (
            ("proposed", "explicit_user", "SEMANTIC_REVIEW_REQUIRED"),
            ("needs_review", "episode_derived", "SEMANTIC_REVIEW_REQUIRED"),
            ("rejected", "explicit_user", "SEMANTIC_INVALID_STATE"),
            ("stale", "explicit_user", "SEMANTIC_INVALID_STATE"),
        ):
            row = await _candidate(
                session, status=status, evidence=evidence, statement=f"{status}-{evidence}"
            )
            with pytest.raises(HTTPException) as failure:
                await sem_svc.promote_candidate(
                    session, row.id, SemanticCandidatePromoteIn(expected_revision=row.revision)
                )
            assert failure.value.detail["code"] == expected
            if status in ("rejected", "stale"):
                with pytest.raises(HTTPException) as confirm_failure:
                    await sem_svc.confirm_candidate(
                        session, row.id, SemanticCandidateConfirmIn(expected_revision=row.revision)
                    )
                assert confirm_failure.value.detail["code"] == "SEMANTIC_INVALID_STATE"

        model = await _candidate(
            session,
            status="needs_review",
            evidence="model_derived",
            statement="Model destekli bilgi",
        )
        confirmed = await sem_svc.confirm_candidate(
            session, model.id, SemanticCandidateConfirmIn(expected_revision=model.revision)
        )
        assert confirmed.status == "ready"
        result = await sem_svc.promote_candidate(
            session, model.id, SemanticCandidatePromoteIn(expected_revision=confirmed.revision)
        )
        assert result.card_id and result.status == "promoted"
        again = await sem_svc.promote_candidate(
            session, model.id, SemanticCandidatePromoteIn(expected_revision=confirmed.revision)
        )
        assert again.status == "already_promoted"
        with pytest.raises(HTTPException):
            await sem_svc.confirm_candidate(
                session, model.id, SemanticCandidateConfirmIn(expected_revision=result.revision)
            )

        hot = await _candidate(session, destination="hot_memory", statement="Sıcak tercih")
        hot_result = await sem_svc.promote_candidate(
            session, hot.id, SemanticCandidatePromoteIn(expected_revision=hot.revision)
        )
        assert hot_result.card_id and (tmp_path / hot_result.relative_path).is_file()

        for destination, expected in (
            ("operational", "owner_action_required"),
            ("procedural_candidate", "owner_action_required"),
            ("discard", "rejected"),
        ):
            row = await _candidate(
                session, destination=destination, statement=f"{destination} routing"
            )
            response = await sem_svc.promote_candidate(
                session, row.id, SemanticCandidatePromoteIn(expected_revision=row.revision)
            )
            await session.refresh(row)
            assert response.status == expected
            assert row.status != "promoted"
            assert response.card_id is None


@pytest.mark.asyncio
async def test_temporal_duplicate_and_explicit_supersession(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sem_storage, "writable_root", lambda: tmp_path)
    temporal = _load_eval_fixture()["temporal_preservation_cases"][0]
    t1 = datetime.fromisoformat(temporal["observed_at"])
    t_from = datetime.fromisoformat(temporal["valid_from"])
    t_to = datetime.fromisoformat(temporal["valid_to"])
    async with SessionLocal() as session:
        first = await _candidate(session, statement="Eski teknik tercih", observed_at=t1)
        first.valid_from, first.valid_to = t_from, t_to
        first.subject_key, first.rationale = "editor", "Kullanıcı açıkladı"
        first.conditions, first.exceptions = ["projede"], ["eski depoda"]
        await session.commit()
        result = await sem_svc.promote_candidate(
            session, first.id, SemanticCandidatePromoteIn(expected_revision=first.revision)
        )
        card = sem_storage.read_semantic_card(tmp_path, result.card_id)
        assert card.observed_at == t1
        assert card.valid_from == t_from and card.valid_to == t_to
        assert card.subject_key == "editor" and card.rationale == "Kullanıcı açıkladı"
        assert card.conditions == ["projede"] and card.exceptions == ["eski depoda"]

        duplicate = await _candidate(session, statement="  ESKİ   teknik tercih  ", observed_at=t1)
        duplicate.subject_key = "editor"
        await session.commit()
        duplicate_result = await sem_svc.promote_candidate(
            session, duplicate.id, SemanticCandidatePromoteIn(expected_revision=duplicate.revision)
        )
        assert duplicate_result.status == "already_present"
        assert duplicate_result.card_id == card.card_id
        assert len(sem_storage.scan_semantic_cards(tmp_path)) == 1

        replacement = await _candidate(session, statement="Yeni teknik tercih")
        replacement.subject_key = "editor"
        await session.commit()
        with pytest.raises(HTTPException) as failure:
            await sem_svc.promote_candidate(
                session,
                replacement.id,
                SemanticCandidatePromoteIn(
                    expected_revision=replacement.revision,
                    supersedes=[str(uuid.uuid4())],
                ),
            )
        assert failure.value.detail["code"] == "SEMANTIC_INVALID_SUPERSESSION"
        new_result = await sem_svc.promote_candidate(
            session,
            replacement.id,
            SemanticCandidatePromoteIn(
                expected_revision=replacement.revision,
                supersedes=[card.card_id],
            ),
        )
        cards = {c.card_id: c for c in sem_storage.scan_semantic_cards(tmp_path)}
        assert cards[card.card_id].effective_status == "superseded"
        assert cards[new_result.card_id].supersedes == [card.card_id]
