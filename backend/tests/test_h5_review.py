"""H5 gözden geçirme modları: gün kapanışı, haftalık delta, dönem deltası."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import Entity, Event
from app.db import SessionLocal
from app.integrations.review_intelligence import models as ri
from app.integrations.review_intelligence import service as ri_svc
from app.modules.review.models import Review
from app.modules.todo.models import Todo
from tests.agent_test_utils import forbid_outbound_network  # noqa: F401  (autouse)
from tests.h5_fixtures import ANCHOR, NOW, make_event, make_project, make_todo


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


async def _previous_weekly_review(
    session: AsyncSession, *, period_start: date, priorities: list[str], receipts: list[dict] | None
) -> Review:
    entity = Entity(type="review", title=f"Weekly review · {period_start}", search_text="")
    session.add(entity)
    await session.flush()
    decisions: dict = {"priorities": priorities}
    if receipts is not None:
        decisions["_receipts"] = {"priorities": receipts}
    review = Review(
        id=entity.id,
        kind="weekly",
        period_start=period_start,
        period_end=period_start + timedelta(days=7),
        stats={"todos": {"completed": 4}, "focus": {"minutes": 300}},
        decisions=decisions,
        note=None,
    )
    session.add(review)
    await session.flush()
    return review


async def test_daily_close_reuses_review_preview_and_reports_focus(
    db_session: AsyncSession, vault: Path
) -> None:
    todo = await make_todo(db_session, title="Bugun biten gorev", status="done")
    await make_event(
        db_session,
        verb="todo.completed",
        occurred_at=datetime(2026, 9, 18, 10, 0, tzinfo=UTC),
        entity=todo,
        payload={"title": "Bugun biten gorev"},
    )
    await make_event(
        db_session,
        verb="pomodoro.completed",
        occurred_at=datetime(2026, 9, 18, 11, 0, tzinfo=UTC),
        entity=todo,
        payload={"minutes": 50, "topic": "ALES"},
    )
    await db_session.commit()

    response = await ri_svc.review_intelligence(
        db_session, mode="daily_close", reference_date="2026-09-18", now=NOW
    )
    payload = response.payload

    assert payload.day == "2026-09-18"
    assert payload.review_preview is not None  # mevcut Review önizlemesi yeniden kullanıldı
    assert payload.focus_summary["focus"]["minutes"] == 50
    assert payload.focus_summary["topics"][0]["topic"] == "ALES"
    assert any("Bugun biten gorev" in item.text for item in payload.completed_outcomes)


async def test_daily_close_rejects_since(db_session: AsyncSession, vault: Path) -> None:
    with pytest.raises(ri.ReviewIntelligenceError, match="INVALID_ARGUMENT"):
        await ri_svc.review_intelligence(
            db_session, mode="daily_close", since=ANCHOR.isoformat(), now=NOW
        )


async def test_weekly_review_resolves_priorities_through_receipts(
    db_session: AsyncSession, vault: Path
) -> None:
    """§43/§150: öncelik sonucu Todo KİMLİĞİ üzerinden belirlenir."""
    completed = await make_todo(db_session, title="ALES denemesi", status="done")
    open_todo = await make_todo(db_session, title="forkjob UI", status="open")
    await _previous_weekly_review(
        db_session,
        period_start=date(2026, 9, 7),
        priorities=["ALES denemesi", "forkjob UI"],
        receipts=[
            {"title": "ALES denemesi", "todo_id": str(completed.id), "scheduled_day": "2026-09-14"},
            {"title": "forkjob UI", "todo_id": str(open_todo.id), "scheduled_day": "2026-09-14"},
        ],
    )
    await db_session.commit()

    response = await ri_svc.review_intelligence(
        db_session, mode="weekly_review", reference_date="2026-09-20", now=NOW
    )
    payload = response.payload

    assert payload.previous_review is not None
    assert [item["title"] for item in payload.declared_priorities] == ["ALES denemesi", "forkjob UI"]
    outcomes = {item["title"]: item["outcome"] for item in payload.priority_outcomes}
    assert outcomes == {"ALES denemesi": "completed", "forkjob UI": "open"}
    assert "PRIORITY_RECEIPTS_UNAVAILABLE" not in " ".join(response.warnings)


async def test_historical_review_without_receipts_is_honest(
    db_session: AsyncSession, vault: Path
) -> None:
    """§45/§151: başlık eşleştirmesi KANONİK KİMLİK sayılmaz."""
    await make_todo(db_session, title="English", status="done")
    await _previous_weekly_review(
        db_session, period_start=date(2026, 9, 7), priorities=["English"], receipts=None
    )
    await db_session.commit()

    response = await ri_svc.review_intelligence(
        db_session, mode="weekly_review", reference_date="2026-09-20", now=NOW
    )

    assert any("PRIORITY_RECEIPTS_UNAVAILABLE" in warning for warning in response.warnings)
    outcomes = response.payload.priority_outcomes
    assert outcomes and outcomes[0]["outcome"] == "unknown"
    assert outcomes[0]["title"] == "English"


async def test_partial_week_is_not_compared_numerically(
    db_session: AsyncSession, vault: Path
) -> None:
    """§47/§159: yarım hafta tam haftayla karşılaştırılmaz."""
    await _previous_weekly_review(
        db_session, period_start=date(2026, 9, 7), priorities=["ALES"], receipts=[]
    )
    await db_session.commit()

    response = await ri_svc.review_intelligence(
        db_session, mode="weekly_review", reference_date="2026-09-20", now=NOW
    )

    assert response.coverage.partial is True
    assert response.payload.comparison["comparable"] is False
    assert response.payload.comparison["reason"] == "PARTIAL_PERIOD"
    assert "PARTIAL_PERIOD" in " ".join(response.warnings)


async def test_weekly_review_reports_stalled_project_and_body_of_work(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await make_project(db_session, title="Sessiz proje", next_action="")
    await make_event(
        db_session,
        verb="todo.completed",
        occurred_at=datetime(2026, 9, 16, 10, 0, tzinfo=UTC),
        entity=project,
        payload={"title": "Kilometre tamam"},
    )
    await db_session.commit()

    response = await ri_svc.review_intelligence(
        db_session, mode="weekly_review", reference_date="2026-09-20", now=NOW
    )

    assert any(loop.kind == "project_next_action" for loop in response.payload.open_loops)
    assert response.payload.body_of_work
    assert all(item.support_refs for item in response.payload.body_of_work)


async def test_weekly_review_has_no_productivity_score(
    db_session: AsyncSession, vault: Path
) -> None:
    await make_todo(db_session, title="Gorev")
    await db_session.commit()

    response = await ri_svc.review_intelligence(
        db_session, mode="weekly_review", reference_date="2026-09-20", now=NOW
    )
    blob = response.model_dump_json().lower()

    # Canonical Goals alignment is factual allocation, not a productivity rating.
    for forbidden in ("productivity", "discipline", "score", "grade", "mood"):
        assert forbidden not in blob


async def test_period_delta_reports_focus_and_scoped_activity(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await make_project(db_session, title="forkjob")
    todo = await make_todo(db_session, title="Kapsamli gorev", project=project)
    await make_event(
        db_session,
        verb="todo.completed",
        occurred_at=ANCHOR + timedelta(hours=2),
        entity=todo,
        payload={"title": "Kapsamli gorev"},
    )
    await make_event(
        db_session,
        verb="pomodoro.completed",
        occurred_at=ANCHOR + timedelta(hours=3),
        entity=todo,
        payload={"minutes": 40, "topic": "forkOS"},
    )
    await db_session.commit()

    response = await ri_svc.review_intelligence(
        db_session,
        mode="period_delta",
        since=ANCHOR.isoformat(),
        focus_entity_id=str(project.id),
        now=NOW,
    )

    assert response.payload.focus_entity["title"] == "forkjob"
    assert response.payload.focus["minutes"] == 40
    assert [item.text for item in response.payload.completed] == ["todo.completed: Kapsamli gorev"]


async def test_period_delta_requires_since(db_session: AsyncSession, vault: Path) -> None:
    with pytest.raises(ri.ReviewIntelligenceError, match="INVALID_ARGUMENT"):
        await ri_svc.review_intelligence(db_session, mode="period_delta", now=NOW)


async def test_completed_history_survives_entity_deletion(
    db_session: AsyncSession, vault: Path
) -> None:
    """§H5.1: tamamlanma kanıtı append-only Event'tır, güncel Entity DEĞİLDİR.

    Todo silinip `event.entity_id` NULL kalsa bile tamamlanma olgusu
    kaynağıyla birlikte YAŞAMAYA DEVAM EDER ve `support_refs` boş kalmaz.
    """
    todo = await make_todo(db_session, title="Silinecek görev", status="done")
    await make_event(
        db_session,
        verb="todo.completed",
        occurred_at=datetime(2026, 9, 18, 10, 0, tzinfo=UTC),
        entity=todo,
        payload={"title": "Silinecek görev"},
    )
    await db_session.commit()

    await db_session.execute(delete(Todo).where(Todo.id == todo.id))
    await db_session.execute(delete(Entity).where(Entity.id == todo.id))
    await db_session.commit()
    db_session.expire_all()

    surviving = (
        await db_session.execute(
            select(Event.id).where(
                Event.verb == "todo.completed", Event.entity_id.is_(None)
            )
        )
    ).scalars().all()
    assert surviving, "append-only tamamlanma Event'ı silinmemeli"

    daily = await ri_svc.review_intelligence(
        db_session, mode="daily_close", reference_date="2026-09-18", now=NOW
    )
    weekly = await ri_svc.review_intelligence(
        db_session, mode="weekly_review", reference_date="2026-09-20", now=NOW
    )

    for label, insights in (
        ("completed_outcomes", daily.payload.completed_outcomes),
        ("body_of_work", weekly.payload.body_of_work),
    ):
        matched = [item for item in insights if "Silinecek görev" in item.text]
        assert matched, f"{label}: tarihsel tamamlanma kaybolmamalı"
        insight = matched[0]
        assert insight.status == "fact"
        assert insight.support_refs, f"{label}: olgu kaynaksız kalamaz"
        assert insight.support_refs[0] == f"event:{surviving[0]}"
        # Entity artık yok: uydurma entity referansı eklenmez.
        assert not [ref for ref in insight.support_refs if ref.startswith("entity:")]


async def test_completed_history_keeps_entity_ref_while_entity_exists(
    db_session: AsyncSession, vault: Path
) -> None:
    """Entity duruyorsa `entity:<id>` bağlam olarak EKLENİR; kanıt yine Event'tır."""
    todo = await make_todo(db_session, title="Duran görev", status="done")
    event = await make_event(
        db_session,
        verb="todo.completed",
        occurred_at=datetime(2026, 9, 18, 11, 0, tzinfo=UTC),
        entity=todo,
        payload={"title": "Duran görev"},
    )
    await db_session.commit()

    response = await ri_svc.review_intelligence(
        db_session, mode="daily_close", reference_date="2026-09-18", now=NOW
    )

    insight = next(
        item for item in response.payload.completed_outcomes if "Duran görev" in item.text
    )
    assert insight.support_refs == [f"event:{event.id}", f"entity:{todo.id}"]
    assert insight.source_count == 2
    assert any(
        source.ref == f"event:{event.id}" and source.domain == "operational"
        for source in response.sources
    )


async def test_priority_receipt_target_deletion_is_unknown_not_open(
    db_session: AsyncSession, vault: Path
) -> None:
    """§H5.1: makbuz KİMLİKTİR, güncel varlık değildir.

    Silinen hedef "açık" DEĞİLDİR: mevcut durum yokluğu kanıt değildir.
    """
    todo = await make_todo(db_session, title="Silinecek öncelik", status="open")
    await _previous_weekly_review(
        db_session,
        period_start=date(2026, 9, 7),
        priorities=["Silinecek öncelik"],
        receipts=[
            {
                "title": "Silinecek öncelik",
                "todo_id": str(todo.id),
                "scheduled_day": "2026-09-14",
            }
        ],
    )
    await db_session.commit()

    await db_session.execute(delete(Todo).where(Todo.id == todo.id))
    await db_session.execute(delete(Entity).where(Entity.id == todo.id))
    await db_session.commit()
    db_session.expire_all()

    response = await ri_svc.review_intelligence(
        db_session, mode="weekly_review", reference_date="2026-09-20", now=NOW
    )
    payload = response.payload

    assert [item["title"] for item in payload.declared_priorities] == ["Silinecek öncelik"]
    outcome = payload.priority_outcomes[0]
    assert outcome["todo_id"] == str(todo.id), "makbuz kimliği tarihsel kalmalı"
    assert outcome["status"] == "missing"
    assert outcome["outcome"] == "unknown"
    assert outcome["outcome"] != "open"
