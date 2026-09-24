"""H6 — gerçek `/mcp` taşıması: inceleme, konfigürasyon, override, red."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Notification
from app.core.time import local_zone
from app.db import SessionLocal
from app.modules.proactivity import service
from app.modules.proactivity.models import ProactivityRun
from tests.agent_test_utils import mcp_session, tool_payload
from tests.h5_fixtures import make_todo

NOW = datetime.now(UTC)


def _quiet_window_away_from_now() -> tuple[str, str]:
    """Gerçek saate göre kuit penceresi — MCP yolu saati DIŞARIDAN almaz."""
    local_now = datetime.now(UTC).astimezone(local_zone())
    start = (local_now + timedelta(hours=2)).strftime("%H:%M")
    end = (local_now + timedelta(hours=4)).strftime("%H:%M")
    return start, end


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def test_status_over_transport() -> None:
    async with mcp_session() as session:
        result = await session.call_tool("forkos_proactivity", {"operation": "status"})

    assert result.is_error is False, result.content
    payload = tool_payload(result)
    assert payload["enabled"] is False
    assert {rule["kind"] for rule in payload["rules"]} == set(service.RULE_KINDS)
    assert payload["immediate_budget"] == 3


async def test_configure_and_rule_set_over_transport() -> None:
    async with mcp_session() as session:
        configured = await session.call_tool(
            "forkos_proactivity",
            {
                "operation": "configure",
                "enabled": True,
                "config": {"quiet_hours_start": "22:00", "digest_time": "19:30"},
            },
        )
        rule = await session.call_tool(
            "forkos_proactivity",
            {
                "operation": "rule_set",
                "kind": "continuity_gap",
                "enabled": True,
                "config": {"threshold_hours": 60},
            },
        )

    assert configured.is_error is False, configured.content
    # Aynı işlem TEK şema döner (REST ile aynı): time nesnesi sızmaz.
    payload = tool_payload(configured)
    assert payload["enabled"] is True
    assert payload["quiet_hours_start"] == "22:00"
    assert payload["digest_time"] == "19:30"

    assert rule.is_error is False, rule.content
    rule_payload = tool_payload(rule)
    assert rule_payload["enabled"] is True
    assert rule_payload["config"]["threshold_hours"] == 60


async def test_unknown_operation_and_kind_are_rejected() -> None:
    async with mcp_session() as session:
        bad_op = await session.call_tool(
            "forkos_proactivity", {"operation": "execute_prompt", "kind": "x"}
        )
        bad_kind = await session.call_tool(
            "forkos_proactivity", {"operation": "rule_set", "kind": "run_my_prompt"}
        )
        unknown_field = await session.call_tool(
            "forkos_proactivity",
            {
                "operation": "rule_set",
                "kind": "continuity_gap",
                "config": {"threshold_hours": 48, "shell": "rm -rf /"},
            },
        )
        unknown_config = await session.call_tool(
            "forkos_proactivity",
            {"operation": "configure", "enabled": True, "config": {"prompt": "her saat çalış"}},
        )

    assert bad_op.is_error is True
    assert bad_kind.is_error is True and "UNKNOWN_RULE_KIND" in bad_kind.content[0].text
    assert unknown_field.is_error is True
    assert "UNKNOWN_CONFIG_FIELD" in unknown_field.content[0].text
    assert unknown_config.is_error is True
    assert "UNKNOWN_CONFIG_FIELD" in unknown_config.content[0].text


async def test_naive_snooze_timestamp_is_rejected() -> None:
    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_proactivity",
            {"operation": "snooze", "kind": "project_stalled", "until": "2026-10-01T09:00:00"},
        )

    assert result.is_error is True
    assert "INVALID_SNOOZE" in result.content[0].text


async def test_snooze_and_unsnooze_over_transport(db_session: AsyncSession) -> None:
    await service.seed_rules(db_session)
    rule = (await service.list_rules(db_session))[0]
    run = ProactivityRun(
        rule_id=rule.id,
        logical_trigger_key="k:v1:transport-snooze",
        state="delivered",
        reason_codes=[],
        triggered_at=NOW,
        delivery_count=1,
    )
    db_session.add(run)
    await db_session.commit()

    until = (NOW + timedelta(days=3)).isoformat()
    async with mcp_session() as session:
        snoozed = await session.call_tool(
            "forkos_proactivity", {"operation": "snooze", "run_id": run.id, "until": until}
        )
        cleared = await session.call_tool(
            "forkos_proactivity", {"operation": "unsnooze", "run_id": run.id}
        )

    assert snoozed.is_error is False, snoozed.content
    assert tool_payload(snoozed)["snoozed"] is True
    assert cleared.is_error is False
    assert tool_payload(cleared)["snoozed"] is False


async def test_history_over_transport_is_bounded(db_session: AsyncSession) -> None:
    await service.seed_rules(db_session)
    rule = (await service.list_rules(db_session))[0]
    for index in range(4):
        db_session.add(
            ProactivityRun(
                rule_id=rule.id,
                logical_trigger_key=f"k:v1:transport-hist-{index}",
                state="delivered",
                reason_codes=["DEADLINE_3D"],
                why_now="son tarih 3 gün içinde",
                triggered_at=NOW,
                delivery_count=1,
            )
        )
    await db_session.commit()

    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_proactivity", {"operation": "history", "limit": 2}
        )

    assert result.is_error is False, result.content
    payload = tool_payload(result)
    assert len(payload["runs"]) == 2
    assert payload["runs"][0]["why_now"] == "son tarih 3 gün içinde"


async def test_evaluate_now_produces_a_real_delivery(db_session: AsyncSession) -> None:
    """§217: tur, son tarih adayını bulup TEK bildirim üretir; ikinci tur tekrarlamaz."""
    start, end = _quiet_window_away_from_now()
    await service.configure(db_session, enabled=True, quiet_hours_start=start, quiet_hours_end=end)
    await make_todo(db_session, title="YLSY", due_at=datetime.now(UTC) + timedelta(days=2, hours=1))
    await db_session.commit()

    async with mcp_session() as session:
        first = await session.call_tool("forkos_proactivity", {"operation": "evaluate_now"})
        second = await session.call_tool("forkos_proactivity", {"operation": "evaluate_now"})

    assert first.is_error is False, first.content
    assert tool_payload(first)["surfaced"] == 1
    assert tool_payload(second)["surfaced"] == 0

    notifications = list((await db_session.execute(select(Notification))).scalars())
    assert len(notifications) == 1
    assert notifications[0].kind == "proactivity"


async def test_h6_tool_never_mutates_canonical_state(db_session: AsyncSession) -> None:
    """§104: yazmalar YALNIZCA H6 konfigürasyon/override durumuna sınırlıdır."""
    from app.core.models import Entity, Event, Link
    from app.modules.project.models import Project
    from app.modules.todo.models import Todo

    async def canonical() -> str:
        parts: list[str] = []
        for model in (Entity, Event, Link, Todo, Project):
            table = model.__table__  # type: ignore[attr-defined]
            columns = sorted(table.columns, key=lambda column: column.name)
            pk = next(iter(table.primary_key.columns))
            rows = (await db_session.execute(select(*columns).order_by(pk))).all()
            parts.append(str(rows))
        return "|".join(parts)

    todo = await make_todo(db_session, title="Dokunulmaz", due_at=NOW + timedelta(days=2))
    await db_session.commit()
    before = await canonical()

    async with mcp_session() as session:
        await session.call_tool("forkos_proactivity", {"operation": "status"})
        await session.call_tool(
            "forkos_proactivity", {"operation": "configure", "enabled": True}
        )
        await session.call_tool(
            "forkos_proactivity", {"operation": "rule_set", "kind": "project_stalled", "enabled": True}
        )
        await session.call_tool("forkos_proactivity", {"operation": "evaluate_now"})

    assert await canonical() == before
    assert (await db_session.get(Entity, todo.id)) is not None
