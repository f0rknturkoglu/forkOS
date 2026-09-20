"""H6 kontrol yüzeyi: durum, konfigürasyon, kural, snooze, geçmiş."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.db import SessionLocal
from app.main import app
from app.modules.proactivity import service
from app.modules.proactivity.models import ProactivityRun

NOW = datetime.now(UTC)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def test_status_reports_defaults(client: AsyncClient) -> None:
    response = await client.get("/api/proactivity/status")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["enabled"] is False
    assert body["quiet_hours_start"] == "23:30"
    assert body["quiet_hours_end"] == "08:30"
    assert body["digest_time"] == "18:30"
    assert body["immediate_budget"] == 3
    assert body["pending_deferred"] == 0
    assert {rule["kind"] for rule in body["rules"]} == set(service.RULE_KINDS)


async def test_config_roundtrip_and_validation(client: AsyncClient) -> None:
    ok = await client.put(
        "/api/proactivity/config",
        json={
            "enabled": True,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "07:15",
            "focus_deferral_enabled": False,
            "digest_time": "19:00",
        },
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["enabled"] is True
    assert body["quiet_hours_start"] == "22:00"
    assert body["focus_deferral_enabled"] is False
    assert body["digest_time"] == "19:00"

    for bad in ("25:00", "7:15", "aksam", ""):
        response = await client.put("/api/proactivity/config", json={"quiet_hours_start": bad})
        assert response.status_code == 422, bad


async def test_rule_set_rejects_unknown_kind_and_fields(client: AsyncClient) -> None:
    unknown_kind = await client.put(
        "/api/proactivity/rules/run_my_prompt", json={"enabled": True}
    )
    assert unknown_kind.status_code == 422
    assert "UNKNOWN_RULE_KIND" in unknown_kind.text

    unknown_field = await client.put(
        "/api/proactivity/rules/continuity_gap",
        json={"config": {"threshold_hours": 48, "shell_command": "rm -rf /"}},
    )
    assert unknown_field.status_code == 422
    assert "UNKNOWN_CONFIG_FIELD" in unknown_field.text


async def test_rule_set_updates_threshold(client: AsyncClient) -> None:
    response = await client.put(
        "/api/proactivity/rules/continuity_gap",
        json={"enabled": True, "config": {"threshold_hours": 72}},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["enabled"] is True
    assert body["config"]["threshold_hours"] == 72
    assert body["logical_key"] == "continuity_gap:v1:global"


async def test_rule_set_rejects_invalid_entity_scope(client: AsyncClient) -> None:
    response = await client.put(
        "/api/proactivity/rules/project_stalled",
        json={"scope_entity_id": "00000000-0000-4000-8000-000000000000"},
    )
    assert response.status_code == 422
    assert "INVALID_ENTITY_SCOPE" in response.text


async def test_snooze_and_unsnooze_a_run(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await service.seed_rules(db_session)
    rule = (await service.list_rules(db_session))[0]
    run = ProactivityRun(
        rule_id=rule.id,
        logical_trigger_key="k:v1:snooze-api",
        state="delivered",
        reason_codes=[],
        triggered_at=NOW,
    )
    db_session.add(run)
    await db_session.commit()

    until = (NOW + timedelta(days=3)).isoformat()
    snoozed = await client.post(f"/api/proactivity/runs/{run.id}/snooze", json={"until": until})
    assert snoozed.status_code == 200, snoozed.text
    assert any(item["snoozed_until"] for item in snoozed.json())

    cleared = await client.delete(f"/api/proactivity/runs/{run.id}/snooze")
    assert cleared.status_code == 200
    assert all(item["snoozed_until"] is None for item in cleared.json())


async def test_snooze_rejects_naive_and_past_timestamps(client: AsyncClient) -> None:
    naive = await client.post(
        "/api/proactivity/rules/project_stalled/snooze",
        json={"until": "2026-10-01T09:00:00"},
    )
    assert naive.status_code == 422
    assert "INVALID_SNOOZE" in naive.text

    past = await client.post(
        "/api/proactivity/rules/project_stalled/snooze",
        json={"until": (NOW - timedelta(days=1)).isoformat()},
    )
    assert past.status_code == 422
    assert "INVALID_SNOOZE" in past.text


async def test_history_is_bounded_and_carries_why_now(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await service.seed_rules(db_session)
    rule = (await service.list_rules(db_session))[0]
    for index in range(5):
        db_session.add(
            ProactivityRun(
                rule_id=rule.id,
                logical_trigger_key=f"k:v1:hist-{index}",
                state="delivered",
                reason_codes=["DEADLINE_3D"],
                why_now="son tarih 3 gün içinde",
                triggered_at=NOW,
                delivery_count=1,
            )
        )
    await db_session.commit()

    response = await client.get("/api/proactivity/history", params={"limit": 3})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    assert body[0]["why_now"] == "son tarih 3 gün içinde"
    assert body[0]["reason_codes"] == ["DEADLINE_3D"]

    too_many = await client.get("/api/proactivity/history", params={"limit": 999})
    assert too_many.status_code == 422


async def test_control_surface_cannot_mutate_canonical_state(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """§104: araç Todo/Project/Opportunity/Vault/Review'a DOKUNMAZ."""
    entity = Entity(type="todo", title="Dokunulmaz", search_text="")
    db_session.add(entity)
    await db_session.commit()
    before = (entity.title, entity.type)

    await client.put("/api/proactivity/config", json={"enabled": True})
    await client.put("/api/proactivity/rules/deadline_staircase", json={"enabled": True})

    await db_session.refresh(entity)
    assert (entity.title, entity.type) == before


async def test_notification_dismiss_closes_the_linked_run(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """§185/§186: "bildirim kapatıldı, koşu hâlâ teslim edildi" durumu KALMAZ."""
    from app.core.models import Notification

    await service.seed_rules(db_session)
    rule = (await service.list_rules(db_session))[0]
    notification = Notification(
        kind="proactivity", title="t", body=None, dedup_key="proactivity:x:1", created_at=NOW
    )
    db_session.add(notification)
    await db_session.flush()
    run = ProactivityRun(
        rule_id=rule.id,
        logical_trigger_key="k:v1:dismiss-sync",
        state="delivered",
        reason_codes=[],
        triggered_at=NOW,
        notification_id=notification.id,
        delivery_count=1,
    )
    db_session.add(run)
    await db_session.commit()

    dismissed = await client.post(f"/api/notifications/{notification.id}/dismiss")
    assert dismissed.status_code == 200

    await db_session.refresh(run)
    assert run.state == "dismissed"
    # Kapatmak ÇÖZMEK DEĞİLDİR.
    assert run.resolved_at is None


async def test_dismiss_all_also_closes_linked_runs(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.core.models import Notification

    await service.seed_rules(db_session)
    rule = (await service.list_rules(db_session))[0]
    runs = []
    for index in range(2):
        notification = Notification(
            kind="proactivity",
            title="t",
            body=None,
            dedup_key=f"proactivity:all:{index}",
            created_at=NOW,
        )
        db_session.add(notification)
        await db_session.flush()
        run = ProactivityRun(
            rule_id=rule.id,
            logical_trigger_key=f"k:v1:dismiss-all-{index}",
            state="delivered",
            reason_codes=[],
            triggered_at=NOW,
            notification_id=notification.id,
            delivery_count=1,
        )
        db_session.add(run)
        runs.append(run)
    await db_session.commit()

    response = await client.post("/api/notifications/dismiss-all")
    assert response.status_code == 200
    for run in runs:
        await db_session.refresh(run)
        assert run.state == "dismissed"


async def test_config_rejects_unknown_keys(client: AsyncClient) -> None:
    """§106: bilinmeyen ayar anahtarı SESSİZCE düşmez."""
    response = await client.put(
        "/api/proactivity/config", json={"enabled": True, "prompt": "her saat başı çalış"}
    )
    assert response.status_code == 422
    assert "prompt" in response.text


async def test_rule_set_rejects_unknown_top_level_keys(client: AsyncClient) -> None:
    response = await client.put(
        "/api/proactivity/rules/continuity_gap", json={"enabled": True, "cron": "* * * * *"}
    )
    assert response.status_code == 422
    assert "cron" in response.text
