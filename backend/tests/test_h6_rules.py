"""H6 kural aileleri: basamaklar, ritüel pencereleri, sessizlik kapıları."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.modules.proactivity import rules, service
from tests.h5_fixtures import make_todo

#: 2026-09-21 12:00 UTC = yerel 15:00.
NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def _rule(db_session: AsyncSession, kind: str) -> object:
    await service.seed_rules(db_session)
    await db_session.commit()
    return next(item for item in await service.list_rules(db_session) if item.kind == kind)


@pytest.mark.parametrize(
    ("days", "expected_rung"),
    [(0, 0), (1, 1), (2, 3), (3, 3), (4, 7), (7, 7), (8, 14), (14, 14), (15, 30), (30, 30), (31, None)],
)
def test_deadline_rungs_pick_the_nearest_threshold(days: int, expected_rung: int | None) -> None:
    """Kabul edilmiş merdiven (1,3,7,14,30) + T-0; hepsi 30'a yığılmaz."""
    assert rules._rung(days, rules.DEADLINE_RUNGS) == expected_rung


def test_follow_up_ladder_has_no_30_day_rung() -> None:
    assert rules._rung(30, rules.FOLLOW_UP_RUNGS) is None
    assert rules._rung(14, rules.FOLLOW_UP_RUNGS) == 14


async def test_deadline_candidate_key_carries_the_revision(db_session: AsyncSession) -> None:
    """§46: anahtar, değişen son tarihi eski episoddan AYIRIR."""
    rule = await _rule(db_session, "deadline_staircase")
    todo_due = NOW + timedelta(days=2, hours=1)
    todo = await make_todo(db_session, title="Mülakat", due_at=todo_due)
    await db_session.commit()

    first = await rules.evaluate_rule(db_session, rule, now=NOW)  # type: ignore[arg-type]
    assert len(first) == 1
    key = first[0].logical_trigger_key
    # v2: kimlik KOSULA aittir (entity tek basina kimlik degildir).
    assert key.startswith(f"deadline:v2:todo.due.{todo.id}:")
    assert key.endswith(":3d")
    assert first[0].subject_id == todo.id
    assert rules.identity_of_key(key) == f"todo.due.{todo.id}"
    assert rules.revision_of_key(key) == rules.temporal_revision(todo_due)

    # Aynı gün içinde başka bir tur: AYNI anahtar (idempotansın ön koşulu).
    again = await rules.evaluate_rule(db_session, rule, now=NOW + timedelta(minutes=5))  # type: ignore[arg-type]
    assert [item.logical_trigger_key for item in again] == [key]

    # Son tarih 10 gün ileri: revizyon değişir, anahtar değişir.
    from app.modules.todo.models import Todo

    row = await db_session.get(Todo, todo.id)
    assert row is not None
    row.due_at = NOW + timedelta(days=10)
    await db_session.commit()
    moved = await rules.evaluate_rule(db_session, rule, now=NOW)  # type: ignore[arg-type]
    assert moved and moved[0].logical_trigger_key != key


async def test_deadline_candidate_skips_rows_without_canonical_identity(
    db_session: AsyncSession,
) -> None:
    """Kanonik kimliği olmayan satır için aday ÜRETİLMEZ (uydurma ref yok)."""
    rule = await _rule(db_session, "deadline_staircase")
    candidates = await rules.evaluate_rule(db_session, rule, now=NOW)  # type: ignore[arg-type]
    assert all(item.subject_id is not None for item in candidates)


async def test_ritual_window_has_bounded_grace() -> None:
    """Misfire politikası `run_once_if_still_relevant`: pencere dışına taşmaz."""

    class FakeRule:
        config = {"time": "08:05", "grace_hours": 4}

    # Yerel 08:05–12:05 arası pencere; öncesi ve sonrası DEĞİL.
    assert rules._ritual_due(FakeRule(), now=datetime(2026, 9, 21, 5, 5, tzinfo=UTC), default_time="08:05") is True
    assert rules._ritual_due(FakeRule(), now=datetime(2026, 9, 21, 4, 5, tzinfo=UTC), default_time="08:05") is False
    assert rules._ritual_due(FakeRule(), now=datetime(2026, 9, 21, 9, 4, tzinfo=UTC), default_time="08:05") is True
    assert rules._ritual_due(FakeRule(), now=datetime(2026, 9, 21, 9, 6, tzinfo=UTC), default_time="08:05") is False


def test_weekly_due_respects_weekday_and_time() -> None:
    class FakeRule:
        config = {"weekday": 6, "time": "18:00", "grace_hours": 24}

    sunday = datetime(2026, 9, 20, 15, 30, tzinfo=UTC)  # Pazar 18:30 yerel
    monday = datetime(2026, 9, 21, 15, 30, tzinfo=UTC)
    assert rules._weekly_due(FakeRule(), now=sunday) is True
    assert rules._weekly_due(FakeRule(), now=monday) is False


def test_hhmm_parser_falls_back_deterministically() -> None:
    assert rules._parse_hhmm("07:30", "08:05") == (7, 30)
    assert rules._parse_hhmm("bozuk", "08:05") == (8, 5)
    assert rules._parse_hhmm("99:99", "08:05") == (8, 5)


async def test_morning_ritual_is_silent_without_meaningful_content(
    db_session: AsyncSession,
) -> None:
    """§42: sabah ritüeli boş içerikle bildirim üretmez."""
    rule = await _rule(db_session, "morning_continuity")
    rule.enabled = True  # type: ignore[attr-defined]
    rule.config = {"time": "08:05", "grace_hours": 12}  # type: ignore[attr-defined]
    await db_session.commit()

    morning = datetime(2026, 9, 21, 5, 30, tzinfo=UTC)  # yerel 08:30
    assert await rules.evaluate_rule(db_session, rule, now=morning) == []  # type: ignore[arg-type]


async def test_morning_ritual_reports_meaningful_content(db_session: AsyncSession) -> None:
    rule = await _rule(db_session, "morning_continuity")
    rule.enabled = True  # type: ignore[attr-defined]
    rule.config = {"time": "08:05", "grace_hours": 12}  # type: ignore[attr-defined]
    await make_todo(
        db_session, title="Gecikmiş", status="open", due_at=NOW - timedelta(days=1)
    )
    await db_session.commit()

    morning = datetime(2026, 9, 21, 5, 30, tzinfo=UTC)
    candidates = await rules.evaluate_rule(db_session, rule, now=morning)  # type: ignore[arg-type]
    assert len(candidates) == 1
    assert candidates[0].category == "ritual"
    assert candidates[0].logical_trigger_key.endswith("2026-09-21")


async def test_weekly_ritual_is_silent_without_delta(db_session: AsyncSession) -> None:
    """§62: anlamlı delta yoksa haftalık ritüel sessiz kalır."""
    rule = await _rule(db_session, "weekly_review")
    rule.enabled = True  # type: ignore[attr-defined]
    rule.config = {"weekday": 6, "time": "18:00", "grace_hours": 24}  # type: ignore[attr-defined]
    await db_session.commit()

    sunday = datetime(2026, 9, 20, 15, 30, tzinfo=UTC)
    assert await rules.evaluate_rule(db_session, rule, now=sunday) == []  # type: ignore[arg-type]


async def test_evaluate_all_isolates_failures(db_session: AsyncSession) -> None:
    """Bir kural çökerse diğerleri değerlendirilmeye devam eder."""
    await service.seed_rules(db_session)
    for kind in service.RULE_KINDS:
        await service.rule_set(db_session, kind=kind, enabled=True)
    await db_session.commit()
    all_rules = await service.list_rules(db_session)

    async def boom(*args: object, **kwargs: object) -> list[rules.Candidate]:
        raise RuntimeError("patladı")

    original = rules._EVALUATORS["weekly_review"]
    rules._EVALUATORS["weekly_review"] = boom  # type: ignore[assignment]
    try:
        candidates, failures = await rules.evaluate_all(db_session, all_rules, now=NOW)
    finally:
        rules._EVALUATORS["weekly_review"] = original  # type: ignore[assignment]

    assert [failure.rule_kind for failure in failures] == ["weekly_review"]
    assert [failure.failure_code for failure in failures] == ["RULE_EVALUATION_FAILED"]
    assert isinstance(candidates, list)


async def test_no_event_cursor_is_needed(db_session: AsyncSession) -> None:
    """§129: tüm H6 v1 özellikleri durum yoklamasıyla çalışır — olay imleci YOK."""
    import pathlib

    source = "\n".join(
        item.read_text(encoding="utf-8")
        for item in pathlib.Path("app/modules/proactivity").glob("*.py")
    )
    assert "event_watermark" not in source
    assert "Event.id >" not in source


# ---------------------------------------------------------------------------
# H6.1 — A: aralık dışı son tarihler ADAY DEĞİLDİR
# ---------------------------------------------------------------------------


async def test_far_future_deadline_produces_no_candidate_and_no_crash(
    db_session: AsyncSession,
) -> None:
    """T-31+ son tarih basamak dışıdır: aday yok, çökme yok."""
    rule = await _rule(db_session, "deadline_staircase")
    await make_todo(db_session, title="Uzak T-31", due_at=NOW + timedelta(days=31, hours=1))
    await make_todo(db_session, title="Uzak T-60", due_at=NOW + timedelta(days=60))
    await db_session.commit()

    candidates = await rules.evaluate_rule(db_session, rule, now=NOW)  # type: ignore[arg-type]

    assert candidates == []


async def test_out_of_range_deadline_does_not_abort_the_whole_rule(
    db_session: AsyncSession,
) -> None:
    """Aralık dışı satır, aynı turdaki GEÇERLİ adayları da düşürmemeli."""
    rule = await _rule(db_session, "deadline_staircase")
    await make_todo(db_session, title="Uzak T-45", due_at=NOW + timedelta(days=45))
    near = await make_todo(db_session, title="Yakın T-2", due_at=NOW + timedelta(days=2, hours=1))
    await db_session.commit()

    candidates = await rules.evaluate_rule(db_session, rule, now=NOW)  # type: ignore[arg-type]

    assert [item.subject_id for item in candidates] == [near.id]
    assert all(item is not None for item in candidates)


async def test_follow_up_out_of_range_produces_no_candidate(
    db_session: AsyncSession,
) -> None:
    """Takip merdiveni 14 günden sonrasını taşımaz: aday yok, çökme yok."""
    rule = await _rule(db_session, "deadline_staircase")
    candidates = await rules.evaluate_rule(db_session, rule, now=NOW)  # type: ignore[arg-type]
    assert all(item.rule_kind == "deadline_staircase" for item in candidates)
    # Doğrudan üretici seviyesinde de aynı sözleşme geçerli olmalı.
    assert all(isinstance(item, rules.Candidate) for item in candidates)


@pytest.mark.parametrize(
    ("kind", "days", "expected_rung"),
    [("deadline", 30, 30), ("follow_up", 14, 14)],
)
def test_boundary_rungs_are_still_produced(kind: str, days: int, expected_rung: int) -> None:
    """Sınır değerleri KORUNUR: T-30 normal ve T-14 takip hâlâ basamak üretir."""
    rungs = rules.FOLLOW_UP_RUNGS if kind == "follow_up" else rules.DEADLINE_RUNGS
    assert rules._rung(days, rungs) == expected_rung
