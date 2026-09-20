"""H5 gözden geçirme modları: gün kapanışı, haftalık delta, dönem deltası."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import Entity
from app.db import SessionLocal
from app.integrations.review_intelligence import models as ri
from app.integrations.review_intelligence import service as ri_svc
from app.modules.review.models import Review
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

    for forbidden in ("productivity", "discipline", "alignment", "score", "grade", "mood"):
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
