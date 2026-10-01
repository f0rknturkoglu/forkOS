"""H6 modelleri: kural/kosu sözleşmesi, sınırlar, veritabanı kısıtları."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.modules.proactivity import service
from app.modules.proactivity.models import (
    ACTIVE_RUN_STATES,
    RULE_KINDS,
    RULE_VERSION,
    RUN_STATES,
    TERMINAL_RUN_STATES,
    ProactivityRule,
    ProactivityRun,
)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


def test_rule_kinds_are_a_closed_set() -> None:
    """Genel bir kural DSL'i YOK: davranış eklemek kod yazmaktır."""
    assert RULE_KINDS == (
        "morning_continuity",
        "daily_close",
        "weekly_review",
        "deadline_staircase",
        "continuity_gap",
        "project_stalled",
        "strategy_attention",
    )
    assert RULE_VERSION == 1


def test_run_state_sets_are_disjoint_and_cover_every_state() -> None:
    assert set() == ACTIVE_RUN_STATES & TERMINAL_RUN_STATES
    assert ACTIVE_RUN_STATES | TERMINAL_RUN_STATES | {"delivered", "suppressed"} == RUN_STATES
    # §23: ayırt edilmesi ZORUNLU durumlar.
    assert {"dismissed", "resolved", "cancelled", "snoozed"} <= RUN_STATES


def test_rule_config_rejects_unknown_fields() -> None:
    """§154: kapalı şema — serbest anahtar-değer yazılamaz."""
    with pytest.raises(service.ProactivityError, match="UNKNOWN_CONFIG_FIELD"):
        service.validate_rule_config("continuity_gap", {"threshold_hours": 48, "shell": "rm -rf /"})


@pytest.mark.parametrize(
    ("kind", "config", "code"),
    [
        ("continuity_gap", {"threshold_hours": 0}, "INVALID_CONFIG"),
        ("continuity_gap", {"threshold_hours": 10_000}, "INVALID_CONFIG"),
        ("project_stalled", {"days": -1}, "INVALID_CONFIG"),
        ("project_stalled", {"cooldown_days": 365}, "INVALID_CONFIG"),
        ("weekly_review", {"weekday": 9}, "INVALID_CONFIG"),
        ("morning_continuity", {"time": "25:00"}, "INVALID_CONFIG"),
        ("morning_continuity", {"time": "sabah"}, "INVALID_CONFIG"),
        ("morning_continuity", {"grace_hours": 0}, "INVALID_CONFIG"),
    ],
)
def test_rule_config_values_fail_closed(kind: str, config: dict, code: str) -> None:
    with pytest.raises(service.ProactivityError, match=code):
        service.validate_rule_config(kind, config)


def test_rule_config_accepts_valid_values() -> None:
    assert service.validate_rule_config("continuity_gap", {"threshold_hours": 48}) == {
        "threshold_hours": 48
    }
    assert service.validate_rule_config("weekly_review", {"weekday": 6, "time": "18:00"}) == {
        "weekday": 6,
        "time": "18:00",
    }
    assert service.validate_rule_config("deadline_staircase", {}) == {}


def test_hhmm_validation() -> None:
    assert service.parse_hhmm("08:05", field_name="x").hour == 8
    assert service.parse_hhmm("23:30", field_name="x").minute == 30
    for bad in ("8:5", "24:00", "12:60", "", None, "12"):
        with pytest.raises(service.ProactivityError, match="INVALID_CONFIG"):
            service.parse_hhmm(bad, field_name="x")


async def test_seeding_is_idempotent(db_session: AsyncSession) -> None:
    """§21: her açılışta yeni kural satırı üretilmez."""
    await service.seed_rules(db_session)
    await service.seed_rules(db_session)
    await db_session.commit()
    rules = await service.list_rules(db_session)
    assert len(rules) == len(RULE_KINDS)
    assert {rule.kind for rule in rules} == set(RULE_KINDS)
    for rule in rules:
        assert rule.logical_key == service.rule_logical_key(rule.kind)
        assert rule.version == RULE_VERSION


async def test_master_switch_defaults_to_disabled(db_session: AsyncSession) -> None:
    """§28: H6 kullanıcıyı kendiliğinden dürtmez."""
    config = await service.load_config(db_session)
    assert config["enabled"] is False
    assert config["focus_deferral_enabled"] is True
    assert config["quiet_hours"][0].strftime("%H:%M") == "23:30"


async def test_logical_trigger_key_is_unique_in_the_database(db_session: AsyncSession) -> None:
    """§71/§161: idempotans yalnızca zamanlayıcıya bırakılmaz."""
    await service.seed_rules(db_session)
    rule = (await service.list_rules(db_session))[0]
    now = datetime.now(UTC)
    for _ in range(2):
        db_session.add(
            ProactivityRun(
                rule_id=rule.id,
                logical_trigger_key="deadline:v1:x:2026-10-10:3d",
                state="candidate",
                reason_codes=[],
                triggered_at=now,
            )
        )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_invalid_run_state_is_rejected_by_the_database(db_session: AsyncSession) -> None:
    await service.seed_rules(db_session)
    rule = (await service.list_rules(db_session))[0]
    db_session.add(
        ProactivityRun(
            rule_id=rule.id,
            logical_trigger_key="k:v1:state-check",
            state="nope",
            reason_codes=[],
            triggered_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_run_history_survives_notification_deletion(db_session: AsyncSession) -> None:
    """§98: bildirim budansa da "neden dürtüldü" kaydı okunabilir kalır."""
    from app.core.models import Notification

    await service.seed_rules(db_session)
    rule = (await service.list_rules(db_session))[0]
    notification = Notification(
        kind="proactivity",
        title="t",
        body=None,
        dedup_key="proactivity:test:1",
        created_at=datetime.now(UTC),
    )
    db_session.add(notification)
    await db_session.flush()
    db_session.add(
        ProactivityRun(
            rule_id=rule.id,
            logical_trigger_key="k:v1:notification-fk",
            state="delivered",
            reason_codes=[],
            triggered_at=datetime.now(UTC),
            notification_id=notification.id,
        )
    )
    await db_session.commit()

    await db_session.delete(notification)
    await db_session.commit()

    run = (
        await db_session.execute(
            select(ProactivityRun).where(ProactivityRun.logical_trigger_key == "k:v1:notification-fk")
        )
    ).scalar_one()
    assert run.notification_id is None
    assert run.state == "delivered"


async def test_rule_snooze_is_absolute_and_timezone_aware(db_session: AsyncSession) -> None:
    """§108: naif veya geçmiş zaman kabul edilmez."""
    with pytest.raises(service.ProactivityError, match="INVALID_SNOOZE"):
        await service.snooze(
            db_session, until=datetime(2026, 10, 1, 9, 0), kind="project_stalled"
        )
    with pytest.raises(service.ProactivityError, match="INVALID_SNOOZE"):
        await service.snooze(
            db_session,
            until=datetime.now(UTC) - timedelta(hours=1),
            kind="project_stalled",
        )
    with pytest.raises(service.ProactivityError, match="INVALID_SNOOZE"):
        await service.snooze(db_session, until=datetime.now(UTC) + timedelta(days=1))

    await service.snooze(
        db_session,
        until=datetime.now(UTC) + timedelta(days=3),
        kind="project_stalled",
    )
    rule = next(
        item for item in await service.list_rules(db_session) if item.kind == "project_stalled"
    )
    assert rule.snoozed_until is not None


async def test_unknown_rule_kind_is_rejected(db_session: AsyncSession) -> None:
    with pytest.raises(service.ProactivityError, match="UNKNOWN_RULE_KIND"):
        await service.rule_set(db_session, kind="run_my_prompt")
    with pytest.raises(service.ProactivityError, match="UNKNOWN_RULE_KIND"):
        await service.unsnooze(db_session, kind="run_my_prompt")


async def test_rules_have_no_entity_foreign_key(db_session: AsyncSession) -> None:
    """Bu tablolar operasyonel kayıttır; entity FK'si bilinçli olarak YOK."""
    rule_table = ProactivityRule.__table__
    # PK entity FK'si DEĞİLDİR: bu motorun operasyonel kaydı (kural 1 istisnası).
    assert not rule_table.columns["id"].foreign_keys
    # Entity kapsamlı kural yalnızca `scope_entity_id` ile bağlanır ve o
    # entity silinirse kural da gider (yetim override kalmaz).
    scope_fks = rule_table.columns["scope_entity_id"].foreign_keys
    assert [fk.target_fullname for fk in scope_fks] == ["entity.id"]

    run_table = ProactivityRun.__table__
    assert not run_table.columns["id"].foreign_keys
    # `subject_id` FK'sizdir: entity silinse de tarih okunabilir kalmalı.
    assert not run_table.columns["subject_id"].foreign_keys
