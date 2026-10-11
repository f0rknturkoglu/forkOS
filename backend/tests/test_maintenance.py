"""Gunluk hafif bakim: gun kapisi, adim bagimsizligi ve kapsam.

Bakim worker'dan bagimsiz calisir (gunluk kullanimda worker kapali), bu
yuzden kapi ve kurtarma davranisi guardrail'dir: yanlis kurulursa ya her
acilista agir is kosar ya da hic kosmaz ve veritabani sessizce buyur.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text

from app.core.models import Event, SourceRun
from app.db import SessionLocal
from app.main import app
from app.modules.system import maintenance

DAY_SECONDS = 24 * 60 * 60


def _age(path: Path, days: float) -> None:
    stamp = time.time() - days * DAY_SECONDS
    os.utime(path, (stamp, stamp))




@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def test_maintenance_runs_at_most_once_per_day(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gun kapisi: ayni gun ikinci cagri hicbir adim kosmadan None doner."""
    calls: list[datetime] = []

    async def probe(session, moment: datetime) -> dict[str, int]:
        calls.append(moment)
        return {"pruned": 1}

    monkeypatch.setattr(maintenance, "STEPS", (("probe", probe),))

    async with SessionLocal() as session:
        first = await maintenance.run_maintenance(session)
        calls_after_first = len(calls)
        second = await maintenance.run_maintenance(session)
        calls_after_second = len(calls)
        day = (await maintenance.last_run(session))["day"]
        forced = await maintenance.run_maintenance(session, force=True)
        stored = await maintenance.last_run(session)

    assert first is not None
    assert first["status"] == "completed"
    assert first["results"] == {"probe": {"pruned": 1}}
    assert calls_after_first == 1
    assert second is None
    assert calls_after_second == 1, "gun kapisi kapaliyken adim kosmamali"
    assert day == first["day"]
    # Elle tetikleme gun kapisini atlar.
    assert forced is not None
    assert len(calls) == 2
    assert stored is not None and stored["day"] == first["day"]


async def test_failing_step_does_not_stop_the_others(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bir adim patlarsa transaction kurtarilir ve kalan adimlar kosar."""

    async def boom(session, moment: datetime) -> dict[str, int]:
        # Gercek bir SQL hatasi: transaction'i iptal eder.
        await session.execute(text("select * from bakim_testi_olmayan_tablo"))
        return {"unreachable": 1}

    async def ok(session, moment: datetime) -> dict[str, int]:
        count = (await session.execute(select(func.count()).select_from(Event))).scalar_one()
        return {"events": count}

    monkeypatch.setattr(maintenance, "STEPS", (("boom", boom), ("ok", ok)))

    async with SessionLocal() as session:
        summary = await maintenance.run_maintenance(session)

    assert summary is not None
    assert summary["status"] == "completed_with_errors"
    assert summary["results"] == {"ok": {"events": 0}}
    assert len(summary["errors"]) == 1 and "boom" in summary["errors"][0]


async def test_maintenance_steps_are_transaction_isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    """Step A DB degistirir ve basarili olur; Step B exception verir; Step C uygulanir.
    Run tamamlandiktan sonra:
      - A'nin degisikligi DB'de gercekten kalir
      - B error listesine girer ve results'a girmez
      - C basariyla uygulanir ve DB'ye yazilir
    """
    async def step_a(session, moment: datetime) -> dict[str, int]:
        session.add(Event(verb="maintenance.step_a", payload={"ok": True}))
        return {"step_a": 1}

    async def step_b(session, moment: datetime) -> dict[str, int]:
        session.add(Event(verb="maintenance.step_b", payload={"should_rollback": True}))
        raise ValueError("simule edilmis step B hatasi")

    async def step_c(session, moment: datetime) -> dict[str, int]:
        session.add(Event(verb="maintenance.step_c", payload={"ok": True}))
        return {"step_c": 1}

    monkeypatch.setattr(maintenance, "STEPS", (("step_a", step_a), ("step_b", step_b), ("step_c", step_c)))

    async with SessionLocal() as session:
        summary = await maintenance.run_maintenance(session, force=True)

    assert summary is not None
    assert summary["status"] == "completed_with_errors"
    assert "step_a" in summary["results"]
    assert "step_c" in summary["results"]
    assert "step_b" not in summary["results"]
    assert any("step_b" in err for err in summary["errors"])

    async with SessionLocal() as session:
        verbs = (
            await session.execute(
                select(Event.verb).where(
                    Event.verb.in_(["maintenance.step_a", "maintenance.step_b", "maintenance.step_c"])
                )
            )
        ).scalars().all()

    assert "maintenance.step_a" in verbs, "Step A degisikligi DB'de kalmali"
    assert "maintenance.step_c" in verbs, "Step C degisikligi DB'de kalmali"
    assert "maintenance.step_b" not in verbs, "Step B degisikligi rollback olmali"


async def test_maintenance_prunes_operational_rows_and_keeps_events() -> None:
    """Gercek adimlar bagli: kaynak kosulari budanir, `event` dokunulmaz."""
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        session.add(
            Event(verb="note.created", payload={"keep": True}, occurred_at=now - timedelta(days=900))
        )
        # Kaynak basina son 20 kosu korunur: eski kosunun gitmesi icin
        # onunde 20 taze kosu olmali.
        session.add(SourceRun(source="feed", status="ok", started_at=now - timedelta(days=400)))
        for _ in range(20):
            session.add(SourceRun(source="feed", status="ok", started_at=now - timedelta(days=1)))
        await session.commit()

        summary = await maintenance.run_maintenance(session, now=now, force=True)

        runs = (await session.execute(select(func.count()).select_from(SourceRun))).scalar_one()
        kept = (
            await session.execute(
                select(func.count()).select_from(Event).where(Event.verb == "note.created")
            )
        ).scalar_one()
        audited = (
            await session.execute(
                select(func.count()).select_from(Event).where(Event.verb == "system.maintenance")
            )
        ).scalar_one()

    assert summary is not None and summary["status"] == "completed"
    assert summary["results"]["retention"]["source_run"] == 1
    assert runs == 20
    assert kept == 1, "event kisisel aktivite hafizasi: bakim dokunmamali"
    assert audited == 1, "bakim kendi kosumunu event olarak kaydetmeli"
