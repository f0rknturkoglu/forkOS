"""H6 tur döngüsü: sessizlik, idempotans, yeniden doğrulama, override'lar."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity, Event, Link, Notification
from app.db import SessionLocal
from app.modules.proactivity import rules, service
from app.modules.proactivity.models import ProactivityRun
from tests.h5_fixtures import make_todo

#: 2026-09-21 12:00 UTC = yerel 15:00 (Europe/Istanbul).
NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def _enable(session: AsyncSession, **overrides: object) -> None:
    await service.configure(session, enabled=True, **overrides)  # type: ignore[arg-type]
    await session.commit()


async def _rule(session: AsyncSession, kind: str) -> object:
    await service.seed_rules(session)
    return next(item for item in await service.list_rules(session) if item.kind == kind)


async def _notifications(session: AsyncSession) -> list[Notification]:
    return list(
        (
            await session.execute(select(Notification).order_by(Notification.id.asc()))
        ).scalars()
    )


async def _runs(session: AsyncSession) -> list[ProactivityRun]:
    return list(
        (
            await session.execute(select(ProactivityRun).order_by(ProactivityRun.id.asc()))
        ).scalars()
    )


async def _deadline_todo(session: AsyncSession, *, title: str, days: int) -> Entity:
    return await make_todo(
        session, title=title, due_at=NOW + timedelta(days=days, hours=1)
    )


# ---------------------------------------------------------------------------
# Sessizlik birincil sınıftır
# ---------------------------------------------------------------------------


async def test_master_switch_off_produces_no_notification(db_session: AsyncSession) -> None:
    """§148: T-1 son tarih bile ana anahtar kapalıyken dürtmez."""
    await _deadline_todo(db_session, title="YLSY başvurusu", days=0)
    await db_session.commit()

    result = await service.tick(db_session, now=NOW)

    assert result.delivered == 0
    assert await _notifications(db_session) == []
    assert await _runs(db_session) == []


async def test_silent_tick_writes_nothing(db_session: AsyncSession) -> None:
    """§17/§220: değerlendirilecek bir şey yoksa tek satır bile yazılmaz."""
    await _enable(db_session)

    result = await service.tick(db_session, now=NOW)

    assert result.evaluated == len(service.RULE_KINDS)
    assert result.candidates == 0
    assert await _notifications(db_session) == []
    assert await _runs(db_session) == []


async def test_continuity_gap_needs_meaningful_state(db_session: AsyncSession) -> None:
    """§58: 48 saat sessizlik TEK BAŞINA bildirim sebebi değildir."""
    await _enable(db_session)
    await service.rule_set(db_session, kind="continuity_gap", enabled=True)
    # 60 saat önce sayılan hareket; ama dikkat çeken hiçbir şey yok.
    db_session.add(
        Event(
            entity_id=None,
            entity_type=None,
            verb="pomodoro.completed",
            payload={"minutes": 25},
            occurred_at=NOW - timedelta(hours=60),
        )
    )
    await db_session.commit()

    result = await service.tick(db_session, now=NOW)

    assert result.candidates == 0
    assert await _notifications(db_session) == []


async def test_continuity_comeback_reports_current_facts(db_session: AsyncSession) -> None:
    """§57: sessizlik + ANLAMLI değişim → gerçek bağlamla tek hatırlatma."""
    await _enable(db_session)
    await service.rule_set(db_session, kind="continuity_gap", enabled=True)
    db_session.add(
        Event(
            entity_id=None,
            entity_type=None,
            verb="pomodoro.completed",
            payload={"minutes": 25, "topic": "ALES"},
            occurred_at=NOW - timedelta(hours=60),
        )
    )
    await make_todo(
        db_session, title="Gecikmiş görev", status="open", due_at=NOW - timedelta(days=2)
    )
    await db_session.commit()

    result = await service.tick(db_session, now=NOW)

    assert result.surfaced == 1
    notifications = await _notifications(db_session)
    assert len(notifications) == 1
    assert notifications[0].kind == "proactivity"
    assert "Nerede kalmıştın" in notifications[0].title
    assert notifications[0].body and "gecik" in notifications[0].body.lower()
    # Suçlayıcı dil yok.
    assert "gelmedin" not in notifications[0].body.lower()


# ---------------------------------------------------------------------------
# Son tarih basamakları
# ---------------------------------------------------------------------------


async def test_deadline_threshold_delivers_once(db_session: AsyncSession) -> None:
    """§47/§145: 100 tur değerlendirme = 1 mantıksal teslim."""
    await _enable(db_session)
    todo = await _deadline_todo(db_session, title="ALES denemesi", days=2)
    await db_session.commit()

    first = await service.tick(db_session, now=NOW)
    for _ in range(3):
        await service.tick(db_session, now=NOW + timedelta(minutes=1))

    assert first.surfaced == 1
    notifications = await _notifications(db_session)
    assert len(notifications) == 1
    assert notifications[0].importance == 2  # T-3 kategorisi
    runs = await _runs(db_session)
    assert len(runs) == 1
    assert runs[0].state == "delivered"
    assert runs[0].subject_id == todo.id
    assert runs[0].logical_trigger_key.endswith(":3d")


async def test_deadline_revision_change_supersedes_old_episode(db_session: AsyncSession) -> None:
    """§146: son tarih değişirse eski kosu iptal, yeni tarih bağımsız."""
    await _enable(db_session)
    todo = await _deadline_todo(db_session, title="Mülakat", days=6)
    await db_session.commit()

    await service.tick(db_session, now=NOW)  # T-7 → digest kuyruğu
    old_run = (await _runs(db_session))[0]
    assert old_run.state == "digest_queued"

    # Son tarih 20 gün ileri alındı: eski basamak anlamsızlaştı.
    todo_row = await db_session.get(Entity, todo.id)
    assert todo_row is not None
    from app.modules.todo.models import Todo

    row = await db_session.get(Todo, todo.id)
    assert row is not None
    row.due_at = NOW + timedelta(days=25)
    await db_session.commit()

    await service.tick(db_session, now=NOW)

    superseded = await db_session.get(ProactivityRun, old_run.id)
    assert superseded is not None
    assert superseded.state == "cancelled"
    # Eski tarih REVIZYONU geçersizleşti: "koşul çözüldü" değil "tetik bayat".
    assert superseded.reason_codes == ["STALE_TRIGGER"]


async def test_completed_condition_cancels_pending_delivery(db_session: AsyncSession) -> None:
    """§48/§140: ertelenen teslim, koşul ortadan kalkınca İPTAL edilir."""
    await _enable(db_session, quiet_hours_start="14:00", quiet_hours_end="16:00")
    todo = await _deadline_todo(db_session, title="Başvuruyu bitir", days=2)
    await db_session.commit()

    deferred = await service.tick(db_session, now=NOW)  # yerel 15:00 → kuit
    assert deferred.deferred == 1
    run = (await _runs(db_session))[0]
    assert run.state == "deferred"

    from app.modules.todo.models import Todo

    row = await db_session.get(Todo, todo.id)
    assert row is not None
    row.status = "done"
    await db_session.commit()

    await service.tick(db_session, now=NOW + timedelta(hours=2))

    assert await _notifications(db_session) == []
    resolved = await db_session.get(ProactivityRun, run.id)
    assert resolved is not None
    assert resolved.state == "resolved"
    assert resolved.reason_codes == ["CONDITION_RESOLVED"]


# ---------------------------------------------------------------------------
# Kuit saatleri, odak, snooze
# ---------------------------------------------------------------------------


async def test_quiet_hours_defer_then_deliver_after_window(db_session: AsyncSession) -> None:
    """§141/§218: 02:30'da T-1 dürtmez; pencere kapanınca GÜNCEL durumla teslim."""
    night = datetime(2026, 9, 21, 23, 30, tzinfo=UTC)  # yerel 02:30
    await _enable(db_session, quiet_hours_start="23:00", quiet_hours_end="08:00")
    # Son tarih, kuit penceresi kapandiktan SONRA da gecerli kalmali.
    await make_todo(db_session, title="YLSY", due_at=night + timedelta(hours=20))
    await db_session.commit()

    deferred = await service.tick(db_session, now=night)
    assert deferred.deferred == 1
    assert deferred.surfaced == 0
    run = (await _runs(db_session))[0]
    assert "QUIET_HOURS" in run.reason_codes

    after = await service.tick(db_session, now=night + timedelta(hours=9))
    assert after.surfaced == 1
    notifications = await _notifications(db_session)
    assert len(notifications) == 1
    assert notifications[0].importance == 3  # T-0


async def test_focus_defers_until_focus_ends(db_session: AsyncSession) -> None:
    """§139: odak sürerken ertele, bittiğinde güncel durumla yüzeye çıkar."""
    from app.modules.pomodoro.models import PomodoroSession

    await _enable(db_session)
    await _deadline_todo(db_session, title="forkjob UI", days=2)
    focus_entity = Entity(type="pomodoro", title="Odak", search_text="")
    db_session.add(focus_entity)
    await db_session.flush()
    session_row = PomodoroSession(
        id=focus_entity.id,
        kind="focus",
        started_at=NOW - timedelta(minutes=10),
        planned_min=25,
    )
    db_session.add(session_row)
    await db_session.commit()

    deferred = await service.tick(db_session, now=NOW)
    assert deferred.deferred == 1
    run = (await _runs(db_session))[0]
    assert "FOCUS_ACTIVE" in run.reason_codes

    session_row.ended_at = NOW + timedelta(minutes=5)
    await db_session.commit()

    after = await service.tick(db_session, now=NOW + timedelta(minutes=6))
    assert after.surfaced == 1


async def test_break_is_not_focus(db_session: AsyncSession) -> None:
    """§35: mola odak SAYILMAZ; uydurma FOCUS_ACTIVE üretilmez."""
    from app.modules.pomodoro.models import PomodoroSession

    await _enable(db_session)
    await _deadline_todo(db_session, title="forkjob UI", days=2)
    entity = Entity(type="pomodoro", title="Mola", search_text="")
    db_session.add(entity)
    await db_session.flush()
    db_session.add(
        PomodoroSession(
            id=entity.id, kind="short_break", started_at=NOW, planned_min=5
        )
    )
    await db_session.commit()

    result = await service.tick(db_session, now=NOW)

    assert result.surfaced == 1


async def test_snooze_blocks_then_re_evaluates(db_session: AsyncSession) -> None:
    """§144: snooze süresince sessiz; süre bitince GÜNCEL durum yeniden değerlendirilir."""
    await _enable(db_session)
    await _deadline_todo(db_session, title="YLSY", days=0)
    await db_session.commit()

    first = await service.tick(db_session, now=NOW)
    assert first.surfaced == 1
    run = (await _runs(db_session))[0]

    until = NOW + timedelta(days=3)
    await service.snooze(db_session, until=until, run_id=run.id, now=NOW)
    await db_session.commit()

    blocked = await service.tick(db_session, now=NOW + timedelta(hours=1))
    assert blocked.delivered == 0
    assert len(await _notifications(db_session)) == 1

    after = await service.tick(db_session, now=until + timedelta(minutes=1))
    # §144: otomatik replay YOK — teslim edilmiş tek seferlik koşu tekrar gitmez.
    assert after.delivered == 0
    assert len(await _notifications(db_session)) == 1


async def test_snooze_of_pending_run_resumes_after_expiry(db_session: AsyncSession) -> None:
    """§144: bekleyen kosu, snooze bitince GÜNCEL durumla yeniden değerlendirilir."""
    await _enable(db_session, quiet_hours_start="14:00", quiet_hours_end="16:00")
    # Basamak sabit kalsin (5 gun → T-7): iki tur arasinda esik degismesin.
    await make_todo(db_session, title="YLSY", due_at=NOW + timedelta(days=5))
    await db_session.commit()

    deferred = await service.tick(db_session, now=NOW)  # yerel 15:00 → kuit
    assert deferred.deferred == 1
    run = (await _runs(db_session))[0]

    until = NOW + timedelta(hours=6)
    await service.snooze(db_session, until=until, run_id=run.id, now=NOW)
    await db_session.commit()

    blocked = await service.tick(db_session, now=NOW + timedelta(hours=2))
    assert blocked.delivered == 0
    # §23: `snoozed` ayrı bir durumdur — "ertelendi" ya da "çözüldü" DEĞİL.
    assert (await db_session.get(ProactivityRun, run.id)).state == "snoozed"  # type: ignore[union-attr]

    after = await service.tick(db_session, now=until + timedelta(minutes=1))
    # T-7 kategorisi sindirilir; teslim yolu önemli değil, GÜNCEL durumla oldu.
    assert after.delivered == 1
    assert len(await _notifications(db_session)) == 1


async def test_rule_snooze_is_respected(db_session: AsyncSession) -> None:
    """§26: kullanıcı override'ı otomasyondan ÜSTÜNDÜR."""
    await _enable(db_session)
    await service.rule_set(
        db_session,
        kind="deadline_staircase",
        config={},
    )
    rule = await _rule(db_session, "deadline_staircase")
    rule.snoozed_until = NOW + timedelta(days=2)  # type: ignore[attr-defined]
    await _deadline_todo(db_session, title="YLSY", days=0)
    await db_session.commit()

    result = await service.tick(db_session, now=NOW)

    assert result.delivered == 0
    assert await _notifications(db_session) == []


# ---------------------------------------------------------------------------
# Digest ve bütçe
# ---------------------------------------------------------------------------


async def test_digest_groups_low_attention_candidates(db_session: AsyncSession) -> None:
    """§75: dört ayrı düşük değerli kesinti yerine TEK bildirim."""
    await _enable(db_session, digest_time="00:05")
    for index in range(3):
        await _deadline_todo(db_session, title=f"Kayıt {index}", days=6)
    await db_session.commit()

    result = await service.tick(db_session, now=NOW)

    notifications = await _notifications(db_session)
    assert len(notifications) == 1
    assert notifications[0].kind == "proactivity.digest"
    assert notifications[0].body is not None
    assert notifications[0].body.count("•") == 3
    assert result.digested == 1


async def test_immediate_budget_pushes_extra_surfaces_to_digest(db_session: AsyncSession) -> None:
    """§120: günlük anlık bütçe dolunca bilgi KAYBOLMAZ, digest'e düşer."""
    await _enable(db_session, digest_time="00:05")
    for index in range(4):
        await _deadline_todo(db_session, title=f"Yakın {index}", days=2)
    await db_session.commit()

    result = await service.tick(db_session, now=NOW)

    surfaced = [n for n in await _notifications(db_session) if n.kind == "proactivity"]
    assert len(surfaced) == service.policy.MAX_IMMEDIATE_SURFACES_PER_DAY
    assert result.surfaced == 3
    assert result.digested >= 1


# ---------------------------------------------------------------------------
# İzolasyon, kural kapatma, değişmezlik
# ---------------------------------------------------------------------------


async def test_rule_failure_is_isolated(db_session: AsyncSession) -> None:
    """§152: bir kural çökerse diğerleri çalışmaya devam eder."""
    await _enable(db_session)
    await _deadline_todo(db_session, title="YLSY", days=2)
    await service.rule_set(db_session, kind="project_stalled", enabled=True)
    await db_session.commit()

    async def boom(*args: object, **kwargs: object) -> list[rules.Candidate]:
        raise RuntimeError("kural çöktü")

    original = rules._EVALUATORS["project_stalled"]
    rules._EVALUATORS["project_stalled"] = boom  # type: ignore[assignment]
    try:
        result = await service.tick(db_session, now=NOW)
    finally:
        rules._EVALUATORS["project_stalled"] = original  # type: ignore[assignment]

    assert result.surfaced == 1
    assert result.failed == ["project_stalled"]
    failed = [run for run in await _runs(db_session) if run.state == "failed"]
    assert failed and failed[0].failure_code == "RULE_EVALUATION_FAILED"
    # Hata kullanıcıya bildirim olarak GİTMEZ.
    assert all(item.kind != "proactivity" or "çöktü" not in (item.title or "") for item in await _notifications(db_session))


async def test_rule_disable_cancels_pending_runs(db_session: AsyncSession) -> None:
    """§188: kapatılan kuralın bekleyen teslimi sonradan yüzeye çıkamaz."""
    await _enable(db_session)
    await _deadline_todo(db_session, title="YLSY", days=6)
    await db_session.commit()

    await service.tick(db_session, now=NOW)
    run = (await _runs(db_session))[0]
    assert run.state == "digest_queued"

    await service.rule_set(db_session, kind="deadline_staircase", enabled=False)
    await db_session.commit()

    cancelled = await db_session.get(ProactivityRun, run.id)
    assert cancelled is not None
    assert cancelled.state == "cancelled"
    assert cancelled.reason_codes == ["RULE_DISABLED"]


async def test_h6_activity_does_not_reset_continuity(db_session: AsyncSession) -> None:
    """§56/§147: H6'nın kendi bildirimi kullanıcı hareketi SAYILMAZ."""
    from app.integrations.review_intelligence import service as h5_svc

    await _enable(db_session)
    await _deadline_todo(db_session, title="YLSY", days=0)
    await db_session.commit()

    before = await h5_svc.review_intelligence(db_session, mode="continuity", now=NOW)
    await service.tick(db_session, now=NOW)
    after = await h5_svc.review_intelligence(
        db_session, mode="continuity", now=NOW + timedelta(minutes=5)
    )

    assert before.payload.last_meaningful_activity == after.payload.last_meaningful_activity
    assert after.payload.last_meaningful_activity is None
    counted = (
        await db_session.execute(
            select(func.count()).select_from(Event).where(Event.verb.like("proactivity%"))
        )
    ).scalar_one()
    assert counted == 0


async def test_h6_does_not_mutate_canonical_state(db_session: AsyncSession) -> None:
    """§221: canonical içerik DEĞİŞMEZ; yalnızca H6'nın kendi kayıtları değişir."""
    from app.modules.opportunity.models import Application, Interview, Opportunity
    from app.modules.project.models import Project
    from app.modules.review.models import Review
    from app.modules.todo.models import Todo

    async def canonical(session: AsyncSession) -> str:
        """Secilmis canonical alanlar — nesne kimligi DEGIL, icerik ozeti."""
        parts: list[str] = []
        for model in (Entity, Event, Link, Todo, Project, Opportunity, Application, Interview, Review):
            table = model.__table__  # type: ignore[attr-defined]
            columns = sorted(table.columns, key=lambda column: column.name)
            # PK adi modele gore degisir (or. Application.opportunity_id).
            pk = next(iter(table.primary_key.columns))
            rows = (
                await session.execute(select(*columns).order_by(pk))
            ).all()
            parts.append(str(rows))
        return "|".join(parts)

    await _enable(db_session, digest_time="00:05")
    await _deadline_todo(db_session, title="YLSY", days=2)
    await _deadline_todo(db_session, title="forkjob", days=6)
    await db_session.commit()

    before = await canonical(db_session)
    await service.tick(db_session, now=NOW)
    await service.tick(db_session, now=NOW + timedelta(minutes=1))

    assert await canonical(db_session) == before
    # Bildirimler H6'ya aittir ve yalnızca H6 türlerini taşır.
    kinds = {item.kind for item in await _notifications(db_session)}
    assert kinds and kinds <= {"proactivity", "proactivity.digest"}


async def test_project_stalled_respects_cooldown_and_reopens(db_session: AsyncSession) -> None:
    """§143/§66: cooldown boyunca susar; süre dolunca yeniden değerlendirir."""
    from app.modules.project.models import Project

    await _enable(db_session, digest_time="00:05")
    project_entity = Entity(type="project", title="forkjob", search_text="")
    db_session.add(project_entity)
    await db_session.flush()
    db_session.add(Project(id=project_entity.id, status="active", next_action="", stack=[]))
    db_session.add(
        Event(
            entity_id=project_entity.id,
            entity_type="project",
            verb="pomodoro.completed",
            payload={"minutes": 25},
            occurred_at=NOW - timedelta(days=20),
        )
    )
    await service.rule_set(db_session, kind="project_stalled", enabled=True)
    await db_session.commit()

    first = await service.tick(db_session, now=NOW)
    assert first.digested == 1
    run = (await _runs(db_session))[0]
    assert run.delivery_count == 1

    again = await service.tick(db_session, now=NOW + timedelta(days=1))
    assert again.digested == 0  # cooldown: aynı koşul tekrar dürtmez

    reopened = await service.tick(db_session, now=NOW + timedelta(days=9))
    assert reopened.digested == 1
    refreshed = await db_session.get(ProactivityRun, run.id)
    assert refreshed is not None
    assert refreshed.delivery_count == 2
    assert refreshed.state == "delivered"


async def test_unknown_focus_entity_scope_is_rejected(db_session: AsyncSession) -> None:
    with pytest.raises(service.ProactivityError, match="INVALID_ENTITY_SCOPE"):
        await service.rule_set(
            db_session, kind="project_stalled", scope_entity_id=uuid.uuid4()
        )


async def test_linked_todo_activity_keeps_project_alive(db_session: AsyncSession) -> None:
    """Proje hareketi = sayılan insan hareketi; bağlı görev de sayılır."""
    from app.modules.project.models import Project

    await _enable(db_session, digest_time="00:05")
    project_entity = Entity(type="project", title="forkjob", search_text="")
    db_session.add(project_entity)
    await db_session.flush()
    db_session.add(Project(id=project_entity.id, status="active", next_action="", stack=[]))
    todo = await make_todo(db_session, title="Bağlı görev")
    db_session.add(
        Link(from_id=todo.id, to_id=project_entity.id, relation="belongs_to")
    )
    db_session.add(
        Event(
            entity_id=todo.id,
            entity_type="todo",
            verb="todo.completed",
            payload={},
            occurred_at=NOW - timedelta(days=20),
        )
    )
    await service.rule_set(db_session, kind="project_stalled", enabled=True)
    await db_session.commit()

    # Projenin KENDİ üzerinde hareket yok ama bağlı görev 20 gün önce hareketli:
    # ikisi de "son hareket" tanımına girer, dolayısıyla durağanlık eşiği aşılır.
    result = await service.tick(db_session, now=NOW)
    assert result.digested == 1


async def test_snooze_survives_a_threshold_change(db_session: AsyncSession) -> None:
    """§25: kullanıcı override'i KOŞULA verilir — yeni basamak onu delmez."""
    await _enable(db_session)
    await make_todo(db_session, title="YLSY", due_at=NOW + timedelta(days=2, hours=2))
    await db_session.commit()

    first = await service.tick(db_session, now=NOW)
    assert first.surfaced == 1
    run = (await _runs(db_session))[0]
    until = NOW + timedelta(days=2)
    await service.snooze(db_session, until=until, run_id=run.id, now=NOW)
    await db_session.commit()

    # Bir gun sonra esik T-3'ten T-1'e iner: yeni mantiksal kosu acilir ama
    # snooze hala gecerli oldugu icin kullanici durtulmez.
    later = await service.tick(db_session, now=NOW + timedelta(days=1))
    assert later.delivered == 0
    assert len(await _notifications(db_session)) == 1
    new_run = (await _runs(db_session))[-1]
    assert new_run.logical_trigger_key.endswith(":1d")
    assert new_run.snoozed_until is not None


# ---------------------------------------------------------------------------
# H6.1 — C: digest üyeliği = GERÇEKTEN gösterilen öğe
# ---------------------------------------------------------------------------


async def test_digest_overflow_never_silently_loses_members(db_session: AsyncSession) -> None:
    """§C1: 15 aday → bildirimde ≤10; yalnız GÖRÜNEN üyeler delivered olur."""
    from app.modules.proactivity.delivery import MAX_DIGEST_ITEMS

    await _enable(db_session, digest_time="00:05")
    for index in range(15):
        await _deadline_todo(db_session, title=f"Yığın {index:02d}", days=6)
    await db_session.commit()

    first = await service.tick(db_session, now=NOW)

    notifications = await _notifications(db_session)
    assert len(notifications) == 1
    assert notifications[0].body is not None
    visible = notifications[0].body.count("•")
    assert 0 < visible <= MAX_DIGEST_ITEMS
    assert first.digested == 1

    runs = await _runs(db_session)
    assert len(runs) == 15
    delivered = [run for run in runs if run.state == "delivered"]
    queued = [run for run in runs if run.state == "digest_queued"]
    assert len(delivered) == visible, "yalnız gösterilen üyeler delivered sayılmalı"
    assert len(queued) == 15 - visible, "gösterilmeyen üyeler kuyrukta KALMALI"

    # Sonraki geçerli digest turu kalanları teslim eder: sessiz kayıp YOK.
    second = await service.tick(db_session, now=NOW + timedelta(minutes=2))

    assert second.digested == 1
    notifications = await _notifications(db_session)
    assert len(notifications) == 2
    runs = await _runs(db_session)
    assert all(run.state == "delivered" for run in runs)
    assert sum(run.delivery_count for run in runs) == 15


async def test_digest_member_without_facts_is_not_marked_delivered(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§C2: olgusuz üye bildirime girmez ve delivered SAYILMAZ."""
    original = service._compose

    async def fake_compose(session, *, run, rule, candidate, now):  # type: ignore[no-untyped-def]
        title, facts = await original(
            session, run=run, rule=rule, candidate=candidate, now=now
        )
        # Bir üyeyi olgusuz bırak: bildirime girmemeli ve teslim SAYILMAMALI.
        if run.logical_trigger_key.endswith(tuple(f"{rung}d" for rung in (7,))):
            return "", []
        return title, facts

    await _enable(db_session, digest_time="23:55")
    await _deadline_todo(db_session, title="Olgusuz", days=6)
    await db_session.commit()
    await service.tick(db_session, now=NOW)
    run = (await _runs(db_session))[0]
    assert run.state == "digest_queued"

    monkeypatch.setattr(service, "_compose", fake_compose)
    await _enable(db_session, digest_time="00:05")
    await service.tick(db_session, now=NOW + timedelta(minutes=1))

    refreshed = await db_session.get(ProactivityRun, run.id)
    assert refreshed is not None
    assert refreshed.state != "delivered", "gösterilmeyen üye delivered olamaz"
    assert refreshed.state == "resolved"
    assert refreshed.reason_codes == ["NO_MEANINGFUL_CONTENT"]
    # Olgusuz üye için boş bir bildirim de üretilmez.
    assert await _notifications(db_session) == []


async def test_digest_batch_is_idempotent_across_restarts(db_session: AsyncSession) -> None:
    """§C3: aynı yığın için ikinci bildirim üretilmez (tick/restart)."""
    await _enable(db_session, digest_time="00:05")
    for index in range(8):
        await _deadline_todo(db_session, title=f"Tekrar {index:02d}", days=6)
    await db_session.commit()

    await service.tick(db_session, now=NOW)
    count_after_first = len(await _notifications(db_session))
    assert count_after_first == 1

    # Aynı yığın, tekrar turlar ve gecikmiş tur: İKİNCİ bildirim YOK.
    await service.tick(db_session, now=NOW)
    await service.tick(db_session, now=NOW + timedelta(seconds=30))
    await service.tick(db_session, now=NOW + timedelta(hours=3))
    assert len(await _notifications(db_session)) == count_after_first
    runs = await _runs(db_session)
    assert all(run.state == "delivered" for run in runs)
    assert all(run.delivery_count == 1 for run in runs)


async def test_digest_overflow_is_delivered_in_bounded_batches(
    db_session: AsyncSession,
) -> None:
    """10'dan fazla birikim kaybolmaz: parti parti, her parti tek bildirim."""
    from app.modules.proactivity.delivery import MAX_DIGEST_ITEMS

    await _enable(db_session, digest_time="00:05")
    for index in range(12):
        await _deadline_todo(db_session, title=f"Parti {index:02d}", days=6)
    await db_session.commit()

    await service.tick(db_session, now=NOW)
    assert len(await _notifications(db_session)) == 1
    queued = [run for run in await _runs(db_session) if run.state == "digest_queued"]
    assert len(queued) == 12 - MAX_DIGEST_ITEMS

    await service.tick(db_session, now=NOW + timedelta(minutes=2))

    notifications = await _notifications(db_session)
    assert len(notifications) == 2
    assert all(run.state == "delivered" for run in await _runs(db_session))
    # Her iki bildirim de gerçekten içerik taşır.
    assert all((item.body or "").count("•") > 0 for item in notifications)


async def test_digest_stale_member_is_resolved_before_delivery(
    db_session: AsyncSession,
) -> None:
    """§C4: teslim öncesi bayatlayan üye resolved olur, diğerleri teslim edilir."""
    from app.modules.todo.models import Todo

    await _enable(db_session, digest_time="23:55")
    stale = await _deadline_todo(db_session, title="Bayatlayacak", days=6)
    await _deadline_todo(db_session, title="Kalacak", days=6)
    await db_session.commit()

    await service.tick(db_session, now=NOW)
    runs = {run.subject_id: run for run in await _runs(db_session)}
    assert len(runs) == 2

    row = await db_session.get(Todo, stale.id)
    assert row is not None
    row.status = "done"
    await db_session.commit()

    await _enable(db_session, digest_time="00:05")
    await service.tick(db_session, now=NOW + timedelta(minutes=1))

    refreshed = await db_session.get(ProactivityRun, runs[stale.id].id)
    assert refreshed is not None
    assert refreshed.state == "resolved"
    assert refreshed.reason_codes == ["CONDITION_RESOLVED"]
    delivered = [run for run in await _runs(db_session) if run.state == "delivered"]
    assert len(delivered) == 1
