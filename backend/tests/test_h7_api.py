"""H7 REST yüzeyi: karar uçları, yetki sınırı, canonical mutasyon denetimi."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.db import SessionLocal
from app.main import app
from app.modules.todo.models import Todo

NOW = datetime.now(UTC)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


def _steps(title: str = "ALES başvurusunu tamamla") -> list[dict]:
    return [{"step_id": "s1", "action": "todo_create", "arguments": {"title": title}}]


async def _prepare(client: AsyncClient, **overrides: object) -> dict:
    """API üzerinden plan hazırlama yolu yoktur; plan MCP/Hermes tarafından kurulur."""
    from app.modules.execution import service

    async with SessionLocal() as session:
        plan = await service.prepare(
            session,
            title="ALES planı",
            steps=_steps(),
            now=NOW,
            **overrides,  # type: ignore[arg-type]
        )
        return {"plan_row_id": plan.id, "revision": plan.revision, "state": plan.state}


async def test_list_and_get_plan(client: AsyncClient) -> None:
    prepared = await _prepare(client)
    listed = await client.get("/api/execution/plans", params={"limit": 10})
    assert listed.status_code == 200, listed.text
    assert any(item["plan_row_id"] == prepared["plan_row_id"] for item in listed.json())

    pending = await client.get(
        "/api/execution/plans", params={"states": "awaiting_approval,input_required"}
    )
    assert all(
        item["state"] in {"awaiting_approval", "input_required"} for item in pending.json()
    )

    single = await client.get(f"/api/execution/plans/{prepared['plan_row_id']}")
    assert single.status_code == 200
    body = single.json()
    assert body["state"] == "awaiting_approval"
    assert body["decision_required"] is True
    assert body["step_count"] == 1
    assert body["expires_at"]


async def test_decision_flow_over_api(client: AsyncClient) -> None:
    prepared = await _prepare(client)
    approve = await client.post(
        f"/api/execution/plans/{prepared['plan_row_id']}/approve",
        json={"revision": prepared["revision"]},
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["state"] == "approved"

    execute = await client.post(f"/api/execution/plans/{prepared['plan_row_id']}/execute", json={})
    assert execute.status_code == 200, execute.text
    result = execute.json()
    assert result["final_status"] == "completed"
    assert [item["status"] for item in result["receipts"]] == ["completed"]


async def test_unapproved_execution_is_refused(client: AsyncClient) -> None:
    prepared = await _prepare(client)
    response = await client.post(
        f"/api/execution/plans/{prepared['plan_row_id']}/execute", json={}
    )
    assert response.status_code == 422
    assert "APPROVAL_REQUIRED" in response.text


async def test_stale_revision_is_refused(client: AsyncClient) -> None:
    prepared = await _prepare(client)
    response = await client.post(
        f"/api/execution/plans/{prepared['plan_row_id']}/approve",
        json={"revision": "plan-v1:" + "0" * 64},
    )
    assert response.status_code == 422
    assert "APPROVAL_STALE" in response.text


async def test_respond_and_cancel(client: AsyncClient) -> None:
    prepared = await _prepare(client, input_questions=["Hangi CV?"])
    assert prepared["state"] == "input_required"

    blocked = await client.post(
        f"/api/execution/plans/{prepared['plan_row_id']}/approve", json={}
    )
    assert blocked.status_code == 422, "input_required planda onay SUNULMAZ"

    answered = await client.post(
        f"/api/execution/plans/{prepared['plan_row_id']}/respond",
        json={"answers": {"cv": "Backend CV"}},
    )
    assert answered.status_code == 200
    assert answered.json()["state"] == "draft"

    cancelled = await client.post(
        f"/api/execution/plans/{prepared['plan_row_id']}/cancel", json={}
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "cancelled"


async def test_unknown_plan_returns_404(client: AsyncClient) -> None:
    assert (await client.get("/api/execution/plans/987654")).status_code == 404


async def test_reject_flow(client: AsyncClient) -> None:
    prepared = await _prepare(client)
    rejected = await client.post(
        f"/api/execution/plans/{prepared['plan_row_id']}/reject", json={}
    )
    assert rejected.status_code == 200
    assert rejected.json()["state"] == "rejected"
    assert rejected.json()["decision_required"] is False


async def test_decision_endpoints_do_not_mutate_canonical_state(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """§68: karar uçları canonical yaşam durumuna DOKUNMAZ."""
    entity = Entity(type="todo", title="Dokunulmaz", search_text="")
    db_session.add(entity)
    await db_session.commit()

    prepared = await _prepare(client)
    await client.get("/api/execution/plans")
    await client.get(f"/api/execution/plans/{prepared['plan_row_id']}")
    await client.post(f"/api/execution/plans/{prepared['plan_row_id']}/approve", json={})
    await client.post(f"/api/execution/plans/{prepared['plan_row_id']}/cancel", json={})

    rows = list((await db_session.execute(select(Todo))).scalars())
    assert rows == []
    refreshed = await db_session.get(Entity, entity.id)
    assert refreshed is not None and refreshed.title == "Dokunulmaz"
