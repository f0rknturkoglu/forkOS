"""Strategic progress, alignment and historical truth stay independent."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.core.entity import create_entity
from app.core.events import log_event
from app.core.models import Event, Link
from app.db import SessionLocal
from app.modules.goal import service, strategy
from app.modules.goal.metrics import MetricContext, numeric_progress, trajectory
from app.modules.goal.models import StrategicPlanRevision
from app.modules.goal.schemas import GoalIn, GoalMilestoneIn, GoalMilestonePatch, GoalPatch
from app.modules.goal.strategy_schemas import KeyResultIn, PillarIn, PlanIn

NOW = datetime(2026, 10, 1, tzinfo=UTC)


@pytest.mark.no_database
@pytest.mark.parametrize(
    "current,baseline,target,expected",
    [
        (25, 0, 100, ".25"),
        (75, 100, 0, ".25"),
        (-10, 0, 100, "0"),
        (150, 0, 100, "1"),
        (None, 0, 100, None),
    ],
)
def test_decimal_progress(current, baseline, target, expected):
    assert numeric_progress(current, baseline, target) == (
        Decimal(expected) if expected is not None else None
    )


@pytest.mark.no_database
@pytest.mark.parametrize(
    "values",
    [
        dict(target_value=0),
        dict(target_value=-1),
        dict(target_value=100, weight=0),
        dict(target_value="NaN"),
        dict(target_value=100, source_key="sql"),
        dict(target_value=100, source_config={"sql": "select 1"}),
        dict(target_value=100, trajectory_model="linear"),
    ],
)
def test_invalid_definitions_rejected(values):
    with pytest.raises(ValidationError):
        KeyResultIn(title="KR", **values)


@pytest.mark.no_database
def test_trajectory_uses_only_declared_clock():
    start, end = NOW - timedelta(days=5), NOW + timedelta(days=5)
    assert trajectory(Decimal(".5"), "linear", start, end, NOW)[0] == "on_track"
    assert trajectory(Decimal(".1"), "linear", start, end, NOW)[0] == "behind"
    assert trajectory(Decimal(".9"), "linear", start, end, NOW)[0] == "ahead"
    assert trajectory(None, "linear", start, end, NOW)[0] == "unknown"
    assert trajectory(Decimal(".1"), "none", start, end, NOW)[0] == "not_applicable"
    assert trajectory(Decimal(".1"), "deadline", None, end, NOW)[0] == "not_applicable"
    assert trajectory(Decimal(".1"), "deadline", None, NOW, NOW)[0] == "behind"


@pytest.mark.no_database
def test_skipped_interview_is_not_inferred():
    a = SimpleNamespace(id=uuid4(), opportunity_id=uuid4(), status="offer", created_at=NOW)
    kr = SimpleNamespace(
        id=uuid4(),
        source_key="applications_interview",
        source_config={},
        baseline_value=0,
        target_value=1,
        trajectory_model="none",
        start_at=None,
        target_at=None,
    )
    ctx = MetricContext([(a, None)], [], [], [])
    assert ctx.read(kr, NOW).current_value == 0
    ctx.histories = [SimpleNamespace(opportunity_id=a.opportunity_id, to_status="interview")]
    assert ctx.read(kr, NOW).current_value == 1
    ctx.truncated = True
    assert ctx.read(kr, NOW).progress_percent is None


async def test_legacy_steps_do_not_become_results_and_alignment_counts_once():
    async with SessionLocal() as s:
        g = await service.create_goal(s, GoalIn(title="Legacy objective"))
        m = await service.add_goal_milestone(s, g.id, GoalMilestoneIn(title="Execution step"))
        await service.update_goal_milestone(s, m.id, GoalMilestonePatch(completed=True))
        read = await strategy.overview(s)
        assert read.objectives[0].milestone_progress_percent == 100
        assert read.objectives[0].strategic_progress_percent is None
        kr = await strategy.save_kr(
            s, g.id, KeyResultIn(title="Outcome", target_value=100, manual_value=10)
        )
        todo = await create_entity(s, type="todo", title="Synthetic execution")
        s.add(Link(from_id=todo.id, to_id=g.id, relation="advances_goal"))
        s.add(Link(from_id=todo.id, to_id=m.id, relation="advances_goal_milestone"))
        completed = await log_event(s, verb="todo.completed", entity_id=todo.id, entity_type="todo", payload={})
        await s.commit()
        # The upper bound must be after the DB-generated event time; host and VM
        # clocks need not agree to the millisecond. Keep the assertion deterministic.
        read = await strategy.overview(s, now=completed.occurred_at + timedelta(seconds=1))
        assert read.objectives[0].strategic_progress_percent == 10
        assert read.objectives[0].milestone_progress_percent == 100
        assert read.alignment.linked_count == 1
        assert read.alignment.percent == 100
        assert read.objectives[0].confidence == "medium"
        assert kr.measurement.progress_percent == 10


async def test_plan_revisions_and_graph_validation():
    async with SessionLocal() as s:
        plan = await strategy.save_plan(
            s, PlanIn(title="Plan", start_at=NOW, end_at=NOW + timedelta(days=90))
        )
        pillar = await strategy.save_pillar(s, plan.id, PillarIn(title="Career"))
        g = await service.create_goal(
            s, GoalIn(title="Objective", strategic_plan_id=plan.id, pillar_id=pillar.id)
        )
        with pytest.raises(ValueError):
            await service.update_goal(s, g.id, GoalPatch(parent_goal_id=g.id))
        await s.rollback()
        revisions = list(
            (
                await s.scalars(
                    select(StrategicPlanRevision).order_by(StrategicPlanRevision.revision)
                )
            ).all()
        )
        assert [r.revision for r in revisions] == [1, 2]
        assert revisions[0].state["pillars"] == []
        assert revisions[1].state["pillars"][0]["title"] == "Career"
        h = await strategy.history(s)
        assert len(h.items) == 2 and not h.comparable


@pytest.mark.no_database
@pytest.mark.parametrize(
    "path", ["../secret.md", "/tmp/secret.md", ".obsidian/passwords.md", "note.txt"]
)
def test_unsafe_narrative_rejected(path):
    with pytest.raises(ValueError):
        strategy.validate_narrative(path)


async def test_busy_low_confidence_and_immutable_history(monkeypatch):
    from app.modules.goal.models import KeyResult
    from app.modules.review.models import Review

    async with SessionLocal() as s:
        g = await service.create_goal(s, GoalIn(title="Outcome remains small"))
        kr = await strategy.save_kr(
            s, g.id, KeyResultIn(title="Result", target_value=100, manual_value=10)
        )
        for i in range(5):
            todo = await create_entity(s, type="todo", title=f"Execution {i}")
            s.add(Link(from_id=todo.id, to_id=g.id, relation="advances_goal"))
            await log_event(
                s, verb="todo.completed", entity_id=todo.id, entity_type="todo", payload={}
            )
        await s.commit()
        last_event = await s.scalar(select(Event.occurred_at).order_by(Event.occurred_at.desc()).limit(1))
        read = await strategy.overview(s, now=last_event + timedelta(seconds=1))
        assert read.alignment.percent == 100 and read.objectives[0].strategic_progress_percent == 10
        assert "BUSY_NOT_PROGRESSING" in {f.code for f in read.findings}
        saved = strategy.snapshot(read)
        entity = await create_entity(s, type="review", title="Accepted synthetic review")
        s.add(
            Review(
                id=entity.id,
                kind="weekly",
                period_start=NOW.date(),
                period_end=NOW.date(),
                stats={"strategy_snapshot": saved},
            )
        )
        await s.commit()
        row = await s.get(KeyResult, kr.id)
        row.manual_value = 100
        row.measured_at = datetime.now(UTC) - timedelta(days=31)
        await s.commit()
        fresh = await strategy.overview(s)
        assert fresh.objectives[0].strategic_progress_percent == 100
        assert fresh.objectives[0].confidence == "low"
        h = await strategy.history(s)
        assert h.items[0].state["objectives"][0]["strategic_progress_percent"] == 10
        assert h.items[0].state["alignment"]["percent"] == 100


async def test_mcp_strategy_is_typed_and_read_only():
    from app.integrations.agent.mcp import mcp_server
    from tests.agent_test_utils import capture_db_content_fingerprint

    tools = {tool.name: tool for tool in await mcp_server.list_tools()}
    assert tools["forkos_strategy"].annotations.read_only_hint is True
    async with SessionLocal() as session:
        before = await capture_db_content_fingerprint(session)
    result = await mcp_server.call_tool("forkos_strategy", {"mode": "overview", "days": 7})
    assert result is not None
    async with SessionLocal() as session:
        assert await capture_db_content_fingerprint(session) == before


async def test_overview_query_window_accepts_http_strings():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for days in (7, 30, 90):
            response = await client.get(f"/api/goals/strategy/overview?days={days}")
            assert response.status_code == 200
            assert response.json()["alignment"]["window_days"] == days
        assert (await client.get("/api/goals/strategy/overview?days=8")).status_code == 422


async def test_weighted_progress_and_revision_comparison():
    from app.modules.review.models import Review

    async with SessionLocal() as s:
        g = await service.create_goal(s, GoalIn(title="Weighted objective"))
        kr = await strategy.save_kr(
            s,
            g.id,
            KeyResultIn(title="Heavy outcome", target_value=100, manual_value=100, weight=3),
        )
        await strategy.save_kr(
            s, g.id, KeyResultIn(title="Other outcome", target_value=100, manual_value=0, weight=1)
        )
        assert (await strategy.overview(s)).objectives[0].strategic_progress_percent == 75

        snapshot_index = 0
        async def save_snapshot():
            nonlocal snapshot_index
            snapshot_index += 1
            e = await create_entity(s, type="review", title="Accepted comparison")
            s.add(
                Review(
                    id=e.id,
                    kind="weekly",
                    period_start=(NOW+timedelta(days=snapshot_index*7)).date(),
                    period_end=NOW.date(),
                    stats={"strategy_snapshot": strategy.snapshot(await strategy.overview(s))},
                )
            )
            await s.commit()

        await save_snapshot()
        await strategy.save_kr(
            s,
            g.id,
            KeyResultIn(title="Heavy outcome", target_value=100, manual_value=80, weight=3),
            kr.id,
        )
        await save_snapshot()
        h = await strategy.history(s)
        assert h.comparable and h.progress_deltas[str(g.id)] == -15
        await strategy.save_kr(
            s,
            g.id,
            KeyResultIn(title="Heavy outcome", target_value=200, manual_value=80, weight=3),
            kr.id,
        )
        await save_snapshot()
        assert not (await strategy.history(s)).comparable
