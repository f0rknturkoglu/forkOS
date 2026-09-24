"""H5 süreklilik — "nerede kalmıştım?" (§18/§39/§165)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal
from app.integrations.review_intelligence import models as ri
from app.integrations.review_intelligence import service as ri_svc
from tests.agent_test_utils import forbid_outbound_network  # noqa: F401  (autouse)
from tests.h5_fixtures import (
    ANCHOR,
    NOW,
    build_continuity_fixture,
    make_event,
    make_project,
    make_todo,
)


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


async def test_continuity_acceptance_scenario(
    db_session: AsyncSession, vault: Path
) -> None:
    """§39/§196: iki günlük boşlukta dünyanın değiştiğini gösterebilmeli."""
    world = await build_continuity_fixture(db_session, vault)

    response = await ri_svc.review_intelligence(db_session, mode="continuity", now=NOW)
    payload = response.payload

    assert payload.anchor.kind == "last_meaningful_activity"
    assert payload.anchor.verb == "pomodoro.completed"
    assert 48 <= payload.activity_gap_hours <= 50  # ~2 gün
    assert payload.last_meaningful_activity["title"] == "ALES denemesi"

    assert payload.unread_accumulation.new_unread_since_anchor == 37
    assert payload.unread_accumulation.current_unread_total == 37

    assert [item.title for item in payload.newly_overdue] == ["Gecikmis gorev"]
    assert [item.title for item in payload.passed_plans_still_open] == ["Gecikmis gorev"]

    reasons = [item.reason for item in payload.attention_candidates]
    assert "overdue" in reasons
    assert "passed_plan_open" in reasons
    assert "unread_accumulation" in reasons
    assert reasons.index("overdue") < reasons.index("unread_accumulation")

    assert payload.learning_resume is not None
    assert payload.learning_resume.topic == "ALES"
    assert payload.learning_resume.minutes == 85

    assert str(world["project"].id) in {thread.entity_id for thread in payload.active_threads}


async def test_continuity_never_infers_why_activity_stopped(
    db_session: AsyncSession, vault: Path
) -> None:
    """§29: "yoruldun/motivasyonunu kaybettin" gibi bir çıkarım ÜRETİLMEZ."""
    await build_continuity_fixture(db_session, vault)

    response = await ri_svc.review_intelligence(db_session, mode="continuity", now=NOW)
    blob = response.model_dump_json().lower()

    for forbidden in ("yorul", "hasta", "motivasyon", "dinlen", "lazy", "sick", "tired"):
        assert forbidden not in blob


async def test_continuity_explicit_since_overrides_auto_anchor(
    db_session: AsyncSession, vault: Path
) -> None:
    await build_continuity_fixture(db_session, vault)
    explicit = (ANCHOR - timedelta(days=5)).isoformat()

    response = await ri_svc.review_intelligence(
        db_session, mode="continuity", since=explicit, now=NOW
    )

    assert response.payload.anchor.kind == "explicit"
    assert response.payload.anchor.timestamp == explicit


async def test_continuity_ignores_worker_noise(db_session: AsyncSession, vault: Path) -> None:
    """§24/§25: worker gürültüsü insan hareketi SAYILMAZ."""
    await build_continuity_fixture(db_session, vault)
    await make_event(
        db_session, verb="source.sync", occurred_at=NOW - timedelta(minutes=30), payload={"items": 40}
    )
    await make_event(
        db_session, verb="rss.fetch", occurred_at=NOW - timedelta(minutes=10), payload={"items": 12}
    )
    await db_session.commit()

    response = await ri_svc.review_intelligence(db_session, mode="continuity", now=NOW)

    assert response.payload.anchor.verb == "pomodoro.completed"
    assert response.payload.anchor.timestamp == ANCHOR.isoformat()


async def test_continuity_without_activity_warns_and_does_not_fabricate(
    db_session: AsyncSession, vault: Path
) -> None:
    await make_todo(db_session, title="Sessiz gorev")
    await db_session.commit()

    response = await ri_svc.review_intelligence(db_session, mode="continuity", now=NOW)

    assert response.payload.anchor.kind == "fallback"
    assert any("NO_MEANINGFUL_ACTIVITY" in warning for warning in response.warnings)


async def test_scoped_continuity_uses_entity_context(
    db_session: AsyncSession, vault: Path
) -> None:
    """§26/§197: proje kapsamlı süreklilik aynı motoru kullanır."""
    world = await build_continuity_fixture(db_session, vault)
    # Projeye bağlı görevde SAYILAN bir hareket: proje hareketi böyle türer.
    await make_event(
        db_session,
        verb="todo.completed",
        occurred_at=ANCHOR + timedelta(hours=1),
        entity=world["overdue"],
        payload={"title": "Gecikmis gorev"},
    )
    await db_session.commit()

    response = await ri_svc.review_intelligence(
        db_session,
        mode="continuity",
        focus_entity_id=str(world["project"].id),
        now=NOW,
    )

    assert response.payload.focus_entity is not None
    assert response.payload.focus_entity["title"] == "forkjob"
    # Projeye bağlı görevin hareketi projenin hareketidir (belongs_to).
    assert response.payload.anchor.kind == "last_meaningful_activity"
    assert response.payload.anchor.timestamp == (ANCHOR + timedelta(hours=1)).isoformat()


async def test_continuity_unknown_focus_entity_is_rejected(
    db_session: AsyncSession, vault: Path
) -> None:
    import uuid

    with pytest.raises(ri.ReviewIntelligenceError, match="INVALID_FOCUS_ENTITY"):
        await ri_svc.review_intelligence(
            db_session, mode="continuity", focus_entity_id=str(uuid.uuid4()), now=NOW
        )


async def test_continuity_orders_attention_deterministically(
    db_session: AsyncSession, vault: Path
) -> None:
    await build_continuity_fixture(db_session, vault)

    first = await ri_svc.review_intelligence(db_session, mode="continuity", now=NOW)
    second = await ri_svc.review_intelligence(db_session, mode="continuity", now=NOW)

    assert [item.reason for item in first.payload.attention_candidates] == [
        item.reason for item in second.payload.attention_candidates
    ]
    assert first.model_dump(mode="json")["payload"] == second.model_dump(mode="json")["payload"]


async def test_continuity_facts_carry_source_refs(db_session: AsyncSession, vault: Path) -> None:
    """§90/§157: olgusal çıkarımlar kaynaksız olamaz."""
    await build_continuity_fixture(db_session, vault)

    response = await ri_svc.review_intelligence(db_session, mode="continuity", now=NOW)

    for insight in response.payload.state_changes + response.payload.recent_completed:
        assert insight.support_refs
    for loop in response.payload.newly_overdue + response.payload.passed_plans_still_open:
        assert loop.support_refs
    assert response.payload.unread_accumulation.support_refs


async def test_continuity_upcoming_deadline_is_factual(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§35: yaklaşan son tarih olgu olarak döner; sıralama önerisi Hermes'e aittir."""
    from app.core.models import Entity
    from app.modules.opportunity import application as opp_app
    from app.modules.opportunity.models import Opportunity

    class MockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    monkeypatch.setattr(opp_app, "datetime", MockDatetime)

    await build_continuity_fixture(db_session, vault)
    opportunity_entity = Entity(type="opportunity", title="YLSY başvurusu", search_text="")
    db_session.add(opportunity_entity)
    await db_session.flush()
    db_session.add(
        Opportunity(
            id=opportunity_entity.id,
            kind="announcement",
            status="watching",
            organization="Kurgusal Kurum",
            found_at=ANCHOR + timedelta(hours=2),
            deadline_at=NOW + timedelta(days=4),
        )
    )
    await db_session.commit()

    response = await ri_svc.review_intelligence(db_session, mode="continuity", now=NOW)
    deadlines = [item for item in response.payload.upcoming_deadlines if item["title"] == "YLSY başvurusu"]

    assert deadlines
    assert deadlines[0]["remaining_days"] == 4
    reasons = {item.reason for item in response.payload.attention_candidates}
    assert "deadline_3d" in reasons or "deadline_7d" in reasons


async def test_anchor_falls_back_to_previous_review(
    db_session: AsyncSession, vault: Path
) -> None:
    """§26: sayılan hareket yoksa SON REVIEW gerçek bir çapadır — uydurma değil."""
    from app.core.models import Entity
    from app.modules.review.models import Review

    project = await make_project(db_session, title="Sessiz proje")
    entity = Entity(type="review", title="Weekly review · 2026-09-07", search_text="")
    db_session.add(entity)
    await db_session.flush()
    db_session.add(
        Review(
            id=entity.id,
            kind="weekly",
            period_start=date(2026, 9, 7),
            period_end=date(2026, 9, 14),
            stats={},
            decisions={},
            note=None,
        )
    )
    await db_session.commit()

    response = await ri_svc.review_intelligence(
        db_session,
        mode="continuity",
        focus_entity_id=str(project.id),
        now=NOW,
    )

    anchor = response.payload.anchor
    assert anchor.kind == "previous_review"
    assert anchor.source_ref and anchor.source_ref.startswith("review:")
    # Saat dilimli damga (§22) ve boşluk negatif olamaz.
    parsed = datetime.fromisoformat(anchor.timestamp)
    assert parsed.tzinfo is not None
    assert response.payload.activity_gap_hours >= 0
    assert response.payload.last_meaningful_activity is None
