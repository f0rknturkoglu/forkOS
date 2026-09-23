"""H6.1 — son tarih KOŞUL kimliği: aynı entity'nin bağımsız son tarihleri.

Bir fırsatın üzerinde birden fazla bağımsız temporal koşul olabilir:
ilan son tarihi, takip tarihi ve N görüşme. `entity_id` tek başına KİMLİK
DEĞİLDİR; bu testler kimlik çakışmasının yol açtığı yanlış iptal, yanlış
yeniden doğrulama, yanlış metin ve yanlış snooze yayılımını kilitler.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.db import SessionLocal
from app.modules.opportunity.models import Application, Interview, Opportunity
from app.modules.proactivity import rules, service
from app.modules.proactivity.models import ProactivityRun

# Deadline provider filters future interviews against wall-clock time; keep
# this test's synthetic timeline ahead of that boundary on every CI run.
NOW = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def _enable(session: AsyncSession, **overrides: object) -> None:
    await service.configure(session, enabled=True, **overrides)  # type: ignore[arg-type]
    await session.commit()


async def _opportunity(
    session: AsyncSession,
    *,
    title: str,
    deadline_days: int | None = None,
    follow_up_days: int | None = None,
    interviews: list[tuple[str, int, int]] | None = None,
) -> Entity:
    """Fırsat + (isteğe bağlı) başvuru/takiP + görüşmeler."""
    entity = Entity(type="opportunity", title=title, search_text="")
    session.add(entity)
    await session.flush()
    session.add(
        Opportunity(
            id=entity.id,
            kind="job",
            status="shortlisted",
            priority=2,
            found_at=NOW - timedelta(days=10),
            deadline_at=None if deadline_days is None else NOW + timedelta(days=deadline_days),
            follow_up_at=None
            if follow_up_days is None
            else NOW + timedelta(days=follow_up_days),
        )
    )
    if follow_up_days is not None:
        # Basvuru 1:1'dir ve PK'sini firsat entity'siyle PAYLASIR.
        session.add(Application(opportunity_id=entity.id, status="applied"))
    # FK sirasi: firsat/basvuru satirlari gorusmelerden ONCE yazilmalidir.
    await session.flush()
    for stage, days, hour in interviews or []:
        session.add(
            Interview(
                id=uuid.uuid4(),
                opportunity_id=entity.id,
                stage=stage,
                scheduled_at=NOW + timedelta(days=days, hours=hour),
            )
        )
    await session.flush()
    return entity


async def _candidates(session: AsyncSession) -> list[rules.Candidate]:
    await service.seed_rules(session)
    rule = next(
        item for item in await service.list_rules(session) if item.kind == "deadline_staircase"
    )
    return await rules.evaluate_rule(session, rule, now=NOW)  # type: ignore[arg-type]


async def _notifications(session: AsyncSession) -> list[object]:
    from app.core.models import Notification

    return list((await session.execute(select(Notification))).scalars())


async def _runs(session: AsyncSession) -> list[ProactivityRun]:

    return list(
        (
            await session.execute(select(ProactivityRun).order_by(ProactivityRun.id.asc()))
        ).scalars()
    )


# ---------------------------------------------------------------------------
# B1 — ilan son tarihi + görüşme
# ---------------------------------------------------------------------------


async def test_interview_and_job_deadline_get_distinct_identities(
    db_session: AsyncSession,
) -> None:
    """§B1: aynı fırsatta T-20 ilan + T-2 görüşme ayrı koşullardır."""
    await _enable(db_session)
    await _opportunity(
        db_session,
        title="forkjob",
        deadline_days=20,
        interviews=[("teknik", 2, 3)],
    )
    await db_session.commit()

    candidates = await _candidates(db_session)

    identities = {rules.identity_of_key(item.logical_trigger_key) for item in candidates}
    assert len(identities) == 2, identities
    assert any(identity and identity.startswith("opportunity.interview.") for identity in identities)
    assert any(identity and identity.startswith("opportunity.job") for identity in identities)
    # Aynı entity'ye bağlı iki AYRI koşul aynı anahtarı ÜRETEMEZ.
    keys = {item.logical_trigger_key for item in candidates}
    assert len(keys) == 2


async def test_interview_delivery_uses_its_own_row(db_session: AsyncSession) -> None:
    """§B1: görüşme koşusu görüşme metnini üretir, ilan metnini DEĞİL."""
    await _enable(db_session, quiet_hours_start="23:00", quiet_hours_end="08:00")
    # Kuit penceresi dışında kalması için yerel saat 15:00 → pencere 23:00-08:00.
    await _opportunity(
        db_session,
        title="forkjob",
        deadline_days=20,
        interviews=[("teknik", 2, 3)],
    )
    await db_session.commit()

    await service.tick(db_session, now=NOW)
    runs = await _runs(db_session)
    interview_run = next(
        run for run in runs if rules.identity_of_key(run.logical_trigger_key).startswith("opportunity.interview")  # type: ignore[union-attr]
    )
    assert interview_run.state == "delivered"

    from app.core.models import Notification

    notification = (
        await db_session.execute(
            select(Notification).where(Notification.id == interview_run.notification_id)
        )
    ).scalar_one()
    assert "Görüşme" in notification.title
    assert "teknik" in notification.title


# ---------------------------------------------------------------------------
# B2 — ilan son tarihi + takip tarihi
# ---------------------------------------------------------------------------


async def test_deadline_and_follow_up_are_independent(db_session: AsyncSession) -> None:
    """§B2: takip tarihi ile ilan son tarihi birbirini bozmaz."""
    await _enable(db_session)
    await _opportunity(db_session, title="forkjob", deadline_days=7, follow_up_days=3)
    await db_session.commit()

    candidates = await _candidates(db_session)
    identities = {rules.identity_of_key(item.logical_trigger_key) for item in candidates}

    assert len(identities) == 2, identities
    assert "opportunity.follow_up" in " ".join(str(item) for item in identities)
    assert any(str(identity).startswith("opportunity.job") for identity in identities)


# ---------------------------------------------------------------------------
# B3 — iki görüşme
# ---------------------------------------------------------------------------


async def test_two_interviews_are_separate_conditions(db_session: AsyncSession) -> None:
    """§B3: aynı ilanın iki görüşmesi ayrı koşullardır."""
    await _enable(db_session)
    await _opportunity(
        db_session,
        title="forkjob",
        interviews=[("ön görüşme", 2, 1), ("teknik", 6, 2)],
    )
    await db_session.commit()

    candidates = await _candidates(db_session)

    identities = sorted(
        str(rules.identity_of_key(item.logical_trigger_key)) for item in candidates
    )
    assert len(identities) == 2
    assert len(set(identities)) == 2
    assert all(identity.startswith("opportunity.interview.") for identity in identities)


# ---------------------------------------------------------------------------
# B4 — yalnız bir görüşmenin tarihi değişir
# ---------------------------------------------------------------------------


async def test_rescheduled_interview_supersedes_only_itself(db_session: AsyncSession) -> None:
    """§B4: bir görüşme taşınınca kardeşleri (ilan/takip/diğer görüşme) yaşar."""

    # Hepsi BEKLEYEN episod olsun (digest kuyruğu): iptal yolu kanıtlanır.
    await _enable(db_session, digest_time="23:55")
    entity = await _opportunity(
        db_session,
        title="forkjob",
        deadline_days=20,
        follow_up_days=10,
        interviews=[("ön görüşme", 5, 1), ("teknik", 6, 2)],
    )
    await db_session.commit()

    await service.tick(db_session, now=NOW)
    before = {
        run.logical_trigger_key: run.state for run in await _runs(db_session)
    }
    assert len(before) == 4  # ilan + takip + 2 görüşme
    assert all(state == "digest_queued" for state in before.values()), before

    interview = (
        await db_session.execute(
            select(Interview).where(Interview.stage == "ön görüşme")
        )
    ).scalar_one()
    interview.scheduled_at = NOW + timedelta(days=4, hours=5)  # yeni revizyon

    await service.tick(db_session, now=NOW)

    after = {run.logical_trigger_key: run for run in await _runs(db_session)}
    old_key = next(
        key for key in before if f"interview.{interview.id}" in key
    )
    assert after[old_key].state == "cancelled"
    assert after[old_key].reason_codes == ["STALE_TRIGGER"]
    # Yeni revizyon ayrı bir koşu açar (aynı basamak, yeni tarih).
    assert any(
        f"interview.{interview.id}" in key and key != old_key for key in after
    )
    # Kardeşler DOKUNULMAMIŞ olmalı.
    for key, state in before.items():
        if key == old_key:
            continue
        assert after[key].state == state, key
    assert entity.id is not None


# ---------------------------------------------------------------------------
# B5 — aynı gün içinde saat değişikliği revizyonu değiştirir
# ---------------------------------------------------------------------------


async def test_same_day_interview_time_change_changes_revision(
    db_session: AsyncSession,
) -> None:
    """§9: date-only revizyon yeterli değil — saat değişimi de revizyonu değiştirir."""

    # T-5 (rung 7 → digest kuyruğu) ve AYNI GÜN içinde saat değişimi.
    interview_day = NOW + timedelta(days=5)
    nine = interview_day.replace(hour=9)
    four = interview_day.replace(hour=16)
    assert rules.temporal_revision(nine) != rules.temporal_revision(four)
    assert rules.temporal_revision(nine.date()) == rules.temporal_revision(nine.date())

    await _enable(db_session, digest_time="23:55")
    entity = await _opportunity(db_session, title="forkjob", interviews=[("teknik", 5, 0)])
    await db_session.commit()
    interview = (
        await db_session.execute(select(Interview).where(Interview.opportunity_id == entity.id))
    ).scalar_one()
    interview.scheduled_at = nine
    await db_session.commit()

    await service.tick(db_session, now=NOW)
    first_key = (await _runs(db_session))[0].logical_trigger_key
    assert (await _runs(db_session))[0].state == "digest_queued"

    interview.scheduled_at = four  # AYNI GÜN, farklı saat
    await db_session.commit()
    await service.tick(db_session, now=NOW)

    runs = {run.logical_trigger_key: run for run in await _runs(db_session)}
    assert first_key in runs
    assert runs[first_key].state == "cancelled"
    assert runs[first_key].reason_codes == ["STALE_TRIGGER"]
    new_key = next(key for key in runs if key != first_key)
    assert rules.revision_of_key(new_key) == rules.temporal_revision(four)


# ---------------------------------------------------------------------------
# B5b — koşul ortadan kalkarsa yalnız o koşu çözülür
# ---------------------------------------------------------------------------


async def test_resolved_condition_leaves_siblings_alive(db_session: AsyncSession) -> None:
    """§B5/B6: bir koşul silinirse yalnız o koşu çözülür."""

    await _enable(db_session, digest_time="23:55")
    entity = await _opportunity(
        db_session,
        title="forkjob",
        deadline_days=20,
        interviews=[("teknik", 5, 3)],
    )
    await db_session.commit()

    await service.tick(db_session, now=NOW)
    before = {run.logical_trigger_key: run.state for run in await _runs(db_session)}
    assert len(before) == 2
    assert all(state == "digest_queued" for state in before.values()), before

    interview = (
        await db_session.execute(select(Interview).where(Interview.opportunity_id == entity.id))
    ).scalar_one()
    interview.scheduled_at = None  # görüşme iptal edildi
    await db_session.commit()

    # Aynı tur: yeni aday yok, bekleyen üye henüz dokunulmaz (bayat teslim YOK).
    await service.tick(db_session, now=NOW)
    mid = {run.logical_trigger_key: run for run in await _runs(db_session)}
    interview_key = next(key for key in before if f"interview.{interview.id}" in key)
    job_key = next(key for key in before if key != interview_key)
    assert mid[interview_key].state == "digest_queued"

    # Digest penceresi açıldığında üye yeniden doğrulanır ve ÇÖZÜLÜR.
    await _enable(db_session, digest_time="00:05")
    await service.tick(db_session, now=NOW + timedelta(minutes=1))

    after = {run.logical_trigger_key: run for run in await _runs(db_session)}
    assert after[interview_key].state == "resolved"
    assert after[interview_key].reason_codes == ["CONDITION_RESOLVED"]
    # Kardeş koşul YAŞAR: çözülmedi, iptal edilmedi, bayat sayılmadı.
    assert after[job_key].state in {"digest_queued", "delivered"}
    assert after[job_key].reason_codes != ["CONDITION_RESOLVED"]
    # İptal edilen görüşme için kullanıcıya HİÇBİR şey gösterilmedi.
    notifications = await _notifications(db_session)
    assert all("Görüşme" not in (item.title or "") for item in notifications)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# S1/S2 — snooze kapsamı koşul kimliğidir
# ---------------------------------------------------------------------------


async def test_snooze_is_inherited_across_rung_change_only_for_same_condition(
    db_session: AsyncSession,
) -> None:
    """§S1: aynı koşulun yeni basamağı snooze'u devralır."""
    await _enable(db_session)
    await _opportunity(db_session, title="forkjob", deadline_days=2, interviews=[("teknik", 2, 3)])
    await db_session.commit()

    await service.tick(db_session, now=NOW)
    runs = await _runs(db_session)
    interview_run = next(
        run
        for run in runs
        if str(rules.identity_of_key(run.logical_trigger_key)).startswith("opportunity.interview")
    )
    await service.snooze(
        db_session, until=NOW + timedelta(days=2), run_id=interview_run.id
    )
    await db_session.commit()

    # Bir gün sonra basamak T-3'ten T-1'e iner: aynı koşul, yeni anahtar.
    await service.tick(db_session, now=NOW + timedelta(days=1))
    refreshed = await _runs(db_session)
    interview_runs = [
        run
        for run in refreshed
        if str(rules.identity_of_key(run.logical_trigger_key)).startswith("opportunity.interview")
    ]
    newest = interview_runs[-1]
    assert newest.logical_trigger_key != interview_run.logical_trigger_key
    assert newest.snoozed_until is not None, "aynı koşulun yeni basamağı snooze devralmalı"


async def test_snooze_does_not_leak_to_sibling_condition(db_session: AsyncSession) -> None:
    """§S2: aynı entity'nin BAŞKA son tarihi snooze'u DEVRALMAZ."""
    await _enable(db_session)
    await _opportunity(db_session, title="forkjob", deadline_days=20, interviews=[("teknik", 2, 3)])
    await db_session.commit()

    await service.tick(db_session, now=NOW)
    runs = await _runs(db_session)
    interview_run = next(
        run
        for run in runs
        if str(rules.identity_of_key(run.logical_trigger_key)).startswith("opportunity.interview")
    )
    await service.snooze(db_session, until=NOW + timedelta(days=5), run_id=interview_run.id)
    await db_session.commit()

    # İlan son tarihi T-20 → T-14 basamağına iner: kardeş koşul, snooze YOK.
    await service.tick(db_session, now=NOW + timedelta(days=6))
    job_runs = [
        run
        for run in await _runs(db_session)
        if str(rules.identity_of_key(run.logical_trigger_key)).startswith("opportunity.job")
    ]
    assert job_runs
    assert all(run.snoozed_until is None for run in job_runs), (
        "kardeş koşul snooze devralmamalı"
    )


# ---------------------------------------------------------------------------
# Kimlik determinizmi
# ---------------------------------------------------------------------------


def test_identity_is_deterministic_and_text_free() -> None:
    """Kimlik gosterim metnine ya da sıraya BAĞLI DEĞİLDİR."""
    base = {
        "module": "opportunity",
        "type": "opportunity",
        "entity_id": "6f1c9f3e-0000-4000-8000-000000000001",
        "sub_kind": "interview",
        "condition_id": "6f1c9f3e-0000-4000-8000-000000000002",
        "title": "Bir başlık",
        "due_at": NOW,
    }
    other = {**base, "title": "TAMAMEN FARKLI BAŞLIK"}
    assert rules.condition_identity(base) == rules.condition_identity(other)

    no_child = {**base, "condition_id": None}
    assert rules.condition_identity(base) != rules.condition_identity(no_child)

    different_child = {**base, "condition_id": "6f1c9f3e-0000-4000-8000-000000000003"}
    assert rules.condition_identity(base) != rules.condition_identity(different_child)
    # Kimlik ve revizyon ":" içermez: anahtar ayrıştırması belirsiz kalmaz.
    assert ":" not in rules.condition_identity(base)  # type: ignore[operator]
    assert ":" not in rules.temporal_revision(NOW)
