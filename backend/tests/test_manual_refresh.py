"""Manuel yenileme: kapsam secimi, cift baslatma engeli ve kilit acilmasi."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import ASGITransport, AsyncClient

from app.db import SessionLocal
from app.main import app
from app.modules.system import refresh
from app.modules.system.models import Setting


async def _set_status(value: dict) -> None:
    async with SessionLocal() as session:
        row = await session.get(Setting, refresh.STATUS_KEY)
        if row is None:
            session.add(Setting(key=refresh.STATUS_KEY, value=value))
        else:
            row.value = value
        await session.commit()


async def _clear_status() -> None:
    async with SessionLocal() as session:
        row = await session.get(Setting, refresh.STATUS_KEY)
        if row is not None:
            await session.delete(row)
            await session.commit()


async def test_critical_scope_queues_only_critical_sources():
    await _clear_status()
    async with SessionLocal() as session:
        value, started = await refresh.queue(session, scope="critical")

    assert started is True
    assert value["scope"] == "critical"
    assert value["results"]["opportunity_sources"] > 0

    from app.modules.opportunity.worker import critical_source_ids
    from app.core import source_sync

    async with SessionLocal() as session:
        status = await source_sync.current_status(session)
    queued = set(status["active"]["source_ids"])
    assert queued == set(critical_source_ids())
    assert "jobhunter:linkedin" not in queued


async def test_second_start_is_rejected_while_a_refresh_is_running():
    await _clear_status()
    async with SessionLocal() as session:
        first, started_first = await refresh.queue(session, scope="critical")
    assert started_first is True

    async with SessionLocal() as session:
        second, started_second = await refresh.queue(session, scope="full")

    assert started_second is False
    assert second["status"] == "running"
    assert second["scope"] == "critical", "calisan yenileme kapsami degismemeli"


async def test_stale_running_refresh_releases_the_lock():
    """Sureci olmus bir yenileme butonu saatlerce kilitlememeli."""
    await _set_status(
        {
            "status": "running",
            "scope": "standard",
            "started_at": (datetime.now(UTC) - timedelta(hours=3)).isoformat(),
            "finished_at": None,
            "results": {},
            "errors": [],
        }
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        status = (await http.get("/api/system/refresh")).json()
    assert status["status"] == "interrupted"

    async with SessionLocal() as session:
        value, started = await refresh.queue(session, scope="critical")
    assert started is True
    assert value["status"] == "running"
    await _clear_status()


async def test_refresh_endpoint_accepts_and_reports_scope(monkeypatch):
    """Uctan uca sozlesme: kapsam govdesi kabul edilir, gecersiz kapsam reddedilir.

    Gercek cekim CALISTIRILMAZ: yalnizca kuyruk sozlesmesi sinanir.
    """
    async def no_op() -> None:
        return None

    monkeypatch.setattr(refresh, "run", no_op)
    await _clear_status()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        response = await http.post("/api/system/refresh", json={"scope": "critical"})
        assert response.status_code == 200, response.text
        assert response.json()["scope"] == "critical"

        # Govdesiz cagri da calisir (eski istemciler) ve calisan yenilemeyi bozmaz.
        empty = await http.post("/api/system/refresh")
        assert empty.status_code == 200
        assert empty.json()["status"] == "running"

        invalid = await http.post("/api/system/refresh", json={"scope": "everything"})
        assert invalid.status_code == 422
    await _clear_status()


async def test_jobhunter_env_reports_the_corrected_field_name(monkeypatch):
    """`linkein_allow_direct` yazim hatasi duzeltildi; eski alan da ayni degeri tasir."""
    monkeypatch.setenv("FORKJOB_LINKEDIN_ALLOW_DIRECT", "0")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        payload = (await http.get("/api/sources/jobhunter/env")).json()
    assert payload["linkedin_allow_direct"] is False
    assert payload["linkein_allow_direct"] is False

    monkeypatch.setenv("FORKJOB_LINKEDIN_ALLOW_DIRECT", "1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        payload = (await http.get("/api/sources/jobhunter/env")).json()
    assert payload["linkedin_allow_direct"] is True
    assert payload["linkein_allow_direct"] is True

    # Taninmayan deger guvenli tarafa duser: direct scraping yanlislikla acilmaz.
    monkeypatch.setenv("FORKJOB_LINKEDIN_ALLOW_DIRECT", "evet")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        payload = (await http.get("/api/sources/jobhunter/env")).json()
    assert payload["linkedin_allow_direct"] is False


def test_startup_catch_up_is_bounded():
    """Açılış catch-up'ı kritik katalogun tamamını değil, sınırlı bir kümeyi alır."""
    from app.modules.opportunity.worker import critical_source_ids
    from app.worker.jobs import CRITICAL_CATCH_UP_LIMIT

    ids = critical_source_ids()
    assert len(ids) > CRITICAL_CATCH_UP_LIMIT, "sinir anlamli olmali"
    assert len(ids[:CRITICAL_CATCH_UP_LIMIT]) == CRITICAL_CATCH_UP_LIMIT
    # Resmi/canonical kaynaklar ilk sıradadır: sınır onları dışarıda bırakmaz.
    assert {"osym", "ylsy"} <= set(ids[:CRITICAL_CATCH_UP_LIMIT])
