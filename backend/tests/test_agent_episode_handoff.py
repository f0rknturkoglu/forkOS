"""A3 devir seçimi (§19/§36/§37/§22/§38/§39).

Kim, hangi koşulda önceki oturumun devrini alır — ve almaz. Devir seçimi
"yanlış devir, devirsizlikten kötüdür" ilkesiyle çalışır; bu dosya o ilkenin
sınırlarını (kendi devri, süre, kapsam, boş mühür, tur sırası, bayat kanıt,
H7 dokunulmazlığı, birleşik bütçe) kanıtlar.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.main import app
from app.modules.agent_episode import service as a3
from app.modules.agent_episode.models import AgentSessionEpisode
from app.modules.agent_episode.renderer import CLOSE_TAG, OPEN_TAG, SECURITY_NOTE
from app.modules.agent_lifecycle.service import session_key
from app.modules.execution.models import ExecutionDecision, ExecutionPlan, ExecutionReceipt
from tests.a3_fixtures import (
    Source,
    age_episode,
    deliver,
    ingest,
    items_json,
    patch_provider,
    seal,
    start_session,
)
from tests.h4_test_provider import ScriptedProvider
from tests.h5_fixtures import make_project

USER_TEXT = "Kullanıcı A3 epizodik devir akışını sordu"
ASSISTANT_TEXT = "Asistan A3 epizodik devir akışını özetledi"
DEFAULT_ITEM = ("open_thread", "A3 epizodik devir akışı özetlendi", "A3 epizodik devir akışını özetledi")


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


def _scope_source(scope: str) -> Source:
    return Source(
        f"entity:{uuid.uuid4()}",
        "project",
        source_version="v1",
        scope_project=scope,
        title=f"Kapsamlı proje {scope}",
    )


async def _sealed_episode(
    session: AsyncSession,
    raw_session_id: str,
    *,
    response: str,
    user: str = USER_TEXT,
    assistant: str = ASSISTANT_TEXT,
    sources: list[Source] | None = None,
    turn_id: str = "t1",
):
    """Bir oturumda tur üretir, mühürler; (A1 satırı, finalize çıktısı, devir satırı) döner."""
    row = await start_session(session, raw_session_id, turn_id=turn_id)
    await deliver(session, row, raw_turn_id=turn_id, sources=list(sources or []))
    await ingest(session, raw_session_id, turn_id=turn_id, user=user, assistant=assistant)
    sealed = await seal(session, raw_session_id)
    episode = (
        await session.execute(
            select(AgentSessionEpisode).where(AgentSessionEpisode.id == sealed.episode_id)
        )
    ).scalar_one()
    return row, sealed, episode


async def _new_session(session: AsyncSession, raw_session_id: str):
    return await start_session(session, raw_session_id, turn_id="t1")


async def test_next_session_receives_the_sealed_handoff(h4_ready: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sonraki oturum ilk turunda önceki mühürlü oturumun devrini alır."""
    patch_provider(monkeypatch, ScriptedProvider(responses=[items_json([DEFAULT_ITEM])]))

    async with SessionLocal() as session:
        _, sealed, _ = await _sealed_episode(session, "a3_src_session", response=items_json([DEFAULT_ITEM]))
        follower = await _new_session(session, "a3_dst_session")
        handoff = await a3.select_recent_handoff(
            session, current_session_id=follower.id, current_scope=None
        )

    assert handoff is not None
    assert handoff.episode_id == sealed.episode_id
    assert handoff.source_session_key == session_key("hermes", "a3_src_session")
    assert [item.text for item in handoff.items] == [DEFAULT_ITEM[1]]
    # §8: saklanan her ifade kökenini doğrulayan bir digest taşır.
    assert all(item.turn_digest for item in handoff.items)
    assert handoff.items[0].evidence_class == "turn_derived"
    assert handoff.items[0].support_refs == []


async def test_session_never_receives_its_own_handoff(h4_ready: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Bir oturum kendi devrini almaz: bu kendi kendini besleyen bir döngü olurdu."""
    patch_provider(monkeypatch, ScriptedProvider(responses=[items_json([DEFAULT_ITEM])]))

    async with SessionLocal() as session:
        source_row, _, _ = await _sealed_episode(session, "a3_self_session", response=items_json([DEFAULT_ITEM]))
        handoff = await a3.select_recent_handoff(
            session, current_session_id=source_row.id, current_scope=None
        )

    assert handoff is None


async def test_expired_handoff_is_not_delivered(h4_ready: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Süresi geçmiş devir verilmez; tarihsel kayıt silinse de seçilmez."""
    patch_provider(monkeypatch, ScriptedProvider(responses=[items_json([DEFAULT_ITEM])]))

    async with SessionLocal() as session:
        _, _, episode = await _sealed_episode(session, "a3_expired_session", response=items_json([DEFAULT_ITEM]))
        age_episode(session, episode, days=20)
        await session.commit()
        follower = await _new_session(session, "a3_expired_dst")
        handoff = await a3.select_recent_handoff(
            session, current_session_id=follower.id, current_scope=None
        )

    assert handoff is None


async def test_conflicting_scopes_never_match(h4_ready: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """İki dolu ve farklı kapsam eşleşmez: belirsiz eşleşme kurulmaz."""
    patch_provider(monkeypatch, ScriptedProvider(responses=[items_json([DEFAULT_ITEM])]))

    async with SessionLocal() as session:
        await _sealed_episode(
            session, "a3_scope_src", response=items_json([DEFAULT_ITEM]), sources=[_scope_source("projX")]
        )
        follower = await _new_session(session, "a3_scope_dst")
        handoff = await a3.select_recent_handoff(
            session, current_session_id=follower.id, current_scope="projY"
        )

    assert handoff is None


async def test_scoped_handoff_is_not_given_to_an_unscoped_session(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kapsamlı devir kapsamsız oturuma verilmez: kapsam iddiası kaybolurdu."""
    patch_provider(monkeypatch, ScriptedProvider(responses=[items_json([DEFAULT_ITEM])]))

    async with SessionLocal() as session:
        await _sealed_episode(
            session, "a3_scope_src2", response=items_json([DEFAULT_ITEM]), sources=[_scope_source("projX")]
        )
        follower = await _new_session(session, "a3_scope_dst2")
        handoff = await a3.select_recent_handoff(
            session, current_session_id=follower.id, current_scope=None
        )

    assert handoff is None


async def test_unscoped_handoff_matches_any_scope(h4_ready: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Kapsamsız devir herkese uyar: kapsam iddiası olmadığı için çelişki de yoktur."""
    patch_provider(monkeypatch, ScriptedProvider(responses=[items_json([DEFAULT_ITEM])]))

    async with SessionLocal() as session:
        _, sealed, _ = await _sealed_episode(session, "a3_noscope_src", response=items_json([DEFAULT_ITEM]))
        follower = await _new_session(session, "a3_noscope_dst")
        handoff = await a3.select_recent_handoff(
            session, current_session_id=follower.id, current_scope="projZ"
        )

    assert handoff is not None
    assert handoff.episode_id == sealed.episode_id
    assert handoff.scope_project is None


async def test_sealed_empty_episode_is_never_delivered(h4_ready: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """İfadesiz mühür devir olarak verilmez: taşıyacak bir şey yoktur."""
    patch_provider(monkeypatch, ScriptedProvider(responses=[items_json([])]))

    async with SessionLocal() as session:
        _, sealed, _ = await _sealed_episode(session, "a3_empty_src", response=items_json([]))
        assert sealed.status == "sealed_empty"
        assert sealed.item_count == 0
        follower = await _new_session(session, "a3_empty_dst")
        handoff = await a3.select_recent_handoff(
            session, current_session_id=follower.id, current_scope=None
        )

    assert handoff is None


async def test_handoff_is_injected_on_the_first_turn_only(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """İkinci turda devir tekrar enjekte edilmez; defter yine de yazılır."""
    patch_provider(monkeypatch, ScriptedProvider(responses=[items_json([DEFAULT_ITEM])]))

    async with SessionLocal() as session:
        await _sealed_episode(session, "a3_turn_src", response=items_json([DEFAULT_ITEM]))
        follower = await _new_session(session, "a3_turn_dst")
        first = await a3.observe_turn_delivery(
            session,
            session_row=follower,
            raw_turn_id="t1",
            turn_db_id=None,
            sources=[],
            is_first_turn=True,
        )
        later = await a3.observe_turn_delivery(
            session,
            session_row=follower,
            raw_turn_id="t2",
            turn_db_id=None,
            sources=[],
            is_first_turn=False,
        )

    assert first[0] is not None and first[1] is not None
    assert later == (None, None, [])


async def test_turn_endpoint_injects_handoff_on_first_turn_only(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch, client: AsyncClient
) -> None:
    """Uçtan uca: ilk turda A2 + A3 birlikte, ikinci turda devir YOK."""
    patch_provider(monkeypatch, ScriptedProvider(responses=[items_json([DEFAULT_ITEM])]))

    async with SessionLocal() as session:
        await _sealed_episode(session, "a3_http_src", response=items_json([DEFAULT_ITEM]))

    first = await client.post(
        "/api/agent/lifecycle/turn",
        json={
            "schema_version": 1,
            "harness": "hermes",
            "session_id": "a3_http_dst",
            "turn_id": "t1",
            "platform": "cli",
            "is_first_turn": True,
            "user_message": "merhaba",
        },
    )
    assert first.status_code == 200
    first_data = first.json()
    rendered = first_data["rendered_context"]
    assert first_data["handoff"] is not None
    assert "<forkos-context" in rendered
    assert OPEN_TAG in rendered
    assert CLOSE_TAG in rendered
    assert DEFAULT_ITEM[1] in rendered

    second = await client.post(
        "/api/agent/lifecycle/turn",
        json={
            "schema_version": 1,
            "harness": "hermes",
            "session_id": "a3_http_dst",
            "turn_id": "t2",
            "platform": "cli",
            "is_first_turn": False,
            "user_message": "devam",
        },
    )
    assert second.status_code == 200
    second_data = second.json()
    assert second_data["handoff"] is None
    assert "<forkos-handoff" not in (second_data["rendered_context"] or "")


async def test_combined_first_turn_injection_stays_bounded(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch, client: AsyncClient
) -> None:
    """§39: A2 (≤4000) + A3 (≤1800) birleşik ilk tur enjeksiyonu sınırlı kalır."""
    patch_provider(monkeypatch, ScriptedProvider(responses=[items_json([DEFAULT_ITEM])]))

    async with SessionLocal() as session:
        await _sealed_episode(session, "a3_budget_src", response=items_json([DEFAULT_ITEM]))

    response = await client.post(
        "/api/agent/lifecycle/turn",
        json={
            "schema_version": 1,
            "harness": "hermes",
            "session_id": "a3_budget_dst",
            "turn_id": "t1",
            "platform": "cli",
            "is_first_turn": True,
            "user_message": "merhaba",
        },
    )
    assert response.status_code == 200
    rendered = response.json()["rendered_context"]
    assert rendered is not None
    assert len(rendered) <= 6000
    # Bütçe kırpması wrapper'ları KESMEZ: iki kapanış etiketi de yerinde olmalı.
    assert "</forkos-context>" in rendered
    assert CLOSE_TAG in rendered


async def test_historical_handoff_is_not_presented_as_current_state(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch, client: AsyncClient
) -> None:
    """§37: devir tarihsel ifadeyi taşır; güncel durumu A2 tarafı taşır."""
    patch_provider(monkeypatch, ScriptedProvider(responses=[items_json([("next_focus", "sonraki adım A", "sonraki adım A")])]))

    async with SessionLocal() as session:
        await make_project(session, title="forkjob", next_action="B")
        await session.commit()
        await _sealed_episode(
            session,
            "a3_hist_src",
            response=items_json([("next_focus", "sonraki adım A", "sonraki adım A")]),
            user="sonraki adım neydi",
            assistant="Konuşmada sonraki adım A olarak not edildi",
        )

    response = await client.post(
        "/api/agent/lifecycle/turn",
        json={
            "schema_version": 1,
            "harness": "hermes",
            "session_id": "a3_hist_dst",
            "turn_id": "t1",
            "platform": "cli",
            "is_first_turn": True,
            "user_message": "merhaba",
        },
    )
    assert response.status_code == 200
    rendered = response.json()["rendered_context"]
    assert OPEN_TAG in rendered
    handoff_section = rendered.split(OPEN_TAG, 1)[1]
    current_section = rendered.split(OPEN_TAG, 1)[0]

    # A3: tarihsel ifade + açık güvenlik semantiği.
    assert "sonraki adım A" in handoff_section
    assert SECURITY_NOTE in handoff_section
    # Hiçbir OLUMLU güncellik iddiası yok: her "current state" ifadesi olumsuzlanmış.
    assert handoff_section.count("current state") == handoff_section.count("not canonical current state")
    assert "güncel durum" not in handoff_section.lower()

    # A2: güncel kanonik veriyi yansıtır (tarihsel ifadeyi değil).
    assert "Sonraki adım: B" in current_section
    assert "sonraki adım A" not in current_section


async def test_stale_support_ref_is_marked_but_item_survives(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§22: kanıtı tazeliğini yitirmiş ifade SİLİNMEZ, işaretlenir."""
    patch_provider(
        monkeypatch,
        ScriptedProvider(
            responses=[
                items_json(
                    [("outcome", "Taze Olmayan Proje için kayıt açıldı", "Taze Olmayan Proje")]
                )
            ]
        ),
    )
    stale_id = f"entity:{uuid.uuid4()}"

    async with SessionLocal() as session:
        await _sealed_episode(
            session,
            "a3_stale_src",
            response=items_json(
                [("outcome", "Taze Olmayan Proje için kayıt açıldı", "Taze Olmayan Proje")]
            ),
            user="Taze Olmayan Proje nedir",
            assistant="Taze Olmayan Proje için kayıt açıldı",
            sources=[
                Source(stale_id, "project", source_version="v1", title="Taze Olmayan Proje")
            ],
        )
        follower = await _new_session(session, "a3_stale_dst")
        handoff = await a3.select_recent_handoff(
            session, current_session_id=follower.id, current_scope=None
        )

    assert handoff is not None
    assert "SOURCE_STALE" in handoff.degraded_reasons
    assert len(handoff.items) == 1
    item = handoff.items[0]
    assert item.evidence_class == "canonical_supported"
    assert item.historical_support_stale is True
    assert [ref.source_id for ref in item.support_refs] == [stale_id]


async def _h7_rows(session: AsyncSession) -> dict[str, list[tuple]]:
    """Üç H7 tablosunun satır satır parmak izi."""
    out: dict[str, list[tuple]] = {}
    for model in (ExecutionPlan, ExecutionDecision, ExecutionReceipt):
        table = model.__table__
        rows = (
            await session.execute(select(*table.c).order_by(*table.primary_key.columns))
        ).mappings().all()
        out[table.name] = [
            tuple(
                sorted(
                    (
                        name,
                        json.dumps(value, sort_keys=True, default=str)
                        if isinstance(value, (dict, list))
                        else str(value),
                    )
                    for name, value in row.items()
                )
            )
            for row in rows
        ]
    return out


async def test_handoff_never_touches_h7_execution_state(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§38: devir mühürleme ve okuma H7 yürütme durumunu değiştirmez."""
    patch_provider(
        monkeypatch,
        ScriptedProvider(
            responses=[items_json([("outcome", "deployment approved", "deployment approved")])]
        ),
    )
    plan_id = uuid.uuid4()

    async with SessionLocal() as session:
        plan = ExecutionPlan(
            plan_id=plan_id,
            revision="plan-v1:deadbeef",
            state="approved",
            title="deployment approved",
        )
        session.add(plan)
        await session.flush()
        session.add(
            ExecutionDecision(
                plan_id=plan_id, plan_row_id=plan.id, kind="approved", detail={"by": "user"}
            )
        )
        session.add(
            ExecutionReceipt(
                plan_row_id=plan.id,
                step_id="step-1",
                ordinal=0,
                action="note.create",
                idempotency_key="idem-1",
                status="completed",
                started_at=datetime.now(UTC),
            )
        )
        await session.commit()

        before = await _h7_rows(session)
        assert {name: len(rows) for name, rows in before.items()} == {
            "execution_plan": 1,
            "execution_decision": 1,
            "execution_receipt": 1,
        }

        await _sealed_episode(
            session,
            "a3_h7_src",
            response=items_json([("outcome", "deployment approved", "deployment approved")]),
            user="deployment approved mı",
            assistant="deployment approved olarak işaretlendi",
        )
        follower = await _new_session(session, "a3_h7_dst")
        handoff = await a3.select_recent_handoff(
            session, current_session_id=follower.id, current_scope=None
        )
        after = await _h7_rows(session)

    assert handoff is not None
    assert any(item.text == "deployment approved" for item in handoff.items)
    assert after == before


# ---------------------------------------------------------------------------
# Kapsam belirsizliği vs Kapsamsızlık testleri (A3.1)
# ---------------------------------------------------------------------------


@pytest.mark.no_database
def test_scope_resolution_deterministic_rules() -> None:
    """A3.1 Kapsam çözümleme kuralları matrisi."""
    ref_a = {"scope_project": "projA", "source_id": "1"}
    ref_b = {"scope_project": "projB", "source_id": "2"}
    ref_empty = {"scope_project": None, "source_id": "3"}

    # Delivered A, explicit None -> A
    res = a3.resolve_scope([ref_a])
    assert res.scope_project == "projA" and not res.ambiguous

    # Delivered [], explicit None -> genuinely unscoped
    res = a3.resolve_scope([ref_empty])
    assert res.scope_project is None and not res.ambiguous

    res = a3.resolve_scope([])
    assert res.scope_project is None and not res.ambiguous

    # Delivered A + B, explicit None -> ambiguous
    res = a3.resolve_scope([ref_a, ref_b])
    assert res.scope_project is None and res.ambiguous

    # Explicit A, delivered A -> A
    res = a3.resolve_scope([ref_a], explicit_scope="projA")
    assert res.scope_project == "projA" and not res.ambiguous

    # Explicit A, delivered [] -> A
    res = a3.resolve_scope([], explicit_scope="projA")
    assert res.scope_project == "projA" and not res.ambiguous

    # Explicit A, delivered B -> conflict / fail closed
    res = a3.resolve_scope([ref_b], explicit_scope="projA")
    assert res.scope_project is None and res.ambiguous

    # Explicit A, delivered A + B -> ambiguous / fail closed
    res = a3.resolve_scope([ref_a, ref_b], explicit_scope="projA")
    assert res.scope_project is None and res.ambiguous


async def test_mixed_scope_sources_yield_ambiguous_episode_and_no_handoff(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test A: delivered refs = [scope A, scope B] -> episode ambiguous -> not eligible for handoff."""
    patch_provider(monkeypatch, ScriptedProvider(responses=[items_json([DEFAULT_ITEM])]))

    async with SessionLocal() as session:
        _, sealed, episode = await _sealed_episode(
            session,
            "a3_ambiguous_src",
            response=items_json([DEFAULT_ITEM]),
            sources=[_scope_source("projA"), _scope_source("projB")],
        )

        assert "SCOPE_AMBIGUOUS" in sealed.degraded_reasons
        assert sealed.status == "sealed_degraded"
        assert episode.scope_project is None

        # Hiçbir takipçi (unscoped veya herhangi bir projeye bağlı) bu devri alamaz
        follower_unscoped = await _new_session(session, "a3_ambig_dst_unscoped")
        handoff = await a3.select_recent_handoff(
            session, current_session_id=follower_unscoped.id, current_scope=None
        )
        assert handoff is None

        follower_a = await _new_session(session, "a3_ambig_dst_a")
        handoff = await a3.select_recent_handoff(
            session, current_session_id=follower_a.id, current_scope="projA"
        )
        assert handoff is None


async def test_unscoped_sources_remain_eligible_for_handoff(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test B: delivered refs = [] -> genuine unscoped episode -> handoff works."""
    patch_provider(monkeypatch, ScriptedProvider(responses=[items_json([DEFAULT_ITEM])]))

    async with SessionLocal() as session:
        _, sealed, _ = await _sealed_episode(
            session, "a3_genuine_unscoped_src", response=items_json([DEFAULT_ITEM]), sources=[]
        )
        assert "SCOPE_AMBIGUOUS" not in sealed.degraded_reasons

        follower = await _new_session(session, "a3_genuine_unscoped_dst")
        handoff = await a3.select_recent_handoff(
            session, current_session_id=follower.id, current_scope=None
        )
        assert handoff is not None
        assert handoff.episode_id == sealed.episode_id


async def test_scoped_episode_does_not_handoff_to_different_scoped_session(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test C: delivered refs = [scope A] -> episode A -> new session B -> handoff none."""
    patch_provider(monkeypatch, ScriptedProvider(responses=[items_json([DEFAULT_ITEM])]))

    async with SessionLocal() as session:
        _, sealed, _ = await _sealed_episode(
            session,
            "a3_scope_a_src",
            response=items_json([DEFAULT_ITEM]),
            sources=[_scope_source("projA")],
        )
        assert sealed.scope_project == "projA"

        follower_b = await _new_session(session, "a3_scope_b_dst")
        handoff = await a3.select_recent_handoff(
            session, current_session_id=follower_b.id, current_scope="projB"
        )
        assert handoff is None


async def test_mixed_source_delivery_to_new_session_prevents_accidental_global_handoff(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch, client: AsyncClient
) -> None:
    """Integration test: Yeni oturuma A2 iki farklı proje teslim ettiğinde rastgele global devir almaz."""
    patch_provider(monkeypatch, ScriptedProvider(responses=[items_json([DEFAULT_ITEM])]))

    async with SessionLocal() as session:
        # 1. Genel (kapsamsız) bir oturum mühürle
        await _sealed_episode(
            session, "a3_global_src", response=items_json([DEFAULT_ITEM]), sources=[]
        )

        # 2. Yeni oturum için iki farklı proje kaynağı ile observe_turn_delivery çağır
        new_sess = await _new_session(session, "a3_mixed_delivery_session")
        mixed_sources = [_scope_source("projAlpha"), _scope_source("projBeta")]

        handoff, _, degraded = await a3.observe_turn_delivery(
            session,
            session_row=new_sess,
            raw_turn_id="t1",
            turn_db_id=None,
            sources=mixed_sources,
            is_first_turn=True,
        )

        assert handoff is None
