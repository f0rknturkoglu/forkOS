"""Son tarih toplayicisi (kural 16) regresyonlari.

Iki sessiz hata sinifini kilitler:
1) `ScalarResult` tek gezinmelidir; iki kez gezmek id/due haritalarini bosaltir
   ve modulun TUM satirlari `/api/deadlines`'tan duser (todo/calendar/opportunity
   bu yuzden gorunmuyordu).
2) Medya `release_date` bir `date` tasir; digerleri tz-aware `datetime`. Ayni
   listede karisirsa siralama `TypeError` ile 500 verirdi.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.deadlines import collect_deadlines
from app.db import SessionLocal
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value


async def test_collects_todo_and_media_rows_together(client):
    due = datetime.now(UTC) + timedelta(days=3)
    todo = await client.post(
        "/api/todos",
        json={"title": "Deadline regresyonu", "due_at": due.isoformat()},
    )
    assert todo.status_code == 201, todo.text
    media = await client.post(
        "/api/media",
        json={"title": "Deadline Filmi", "kind": "movie", "status": "planned", "release_date": "2026-10-01"},
    )
    assert media.status_code == 201, media.text

    async with SessionLocal() as session:
        rows = await collect_deadlines(session)

    modules = {row["module"] for row in rows}
    titles = {row["title"] for row in rows}
    # Ikisi de gorunmeli: ScalarResult erken tuketilirse todo satiri kaybolurdu.
    assert "todo" in modules
    assert "media" in modules
    assert "Deadline regresyonu" in titles
    assert "Deadline Filmi" in titles

    # Siralama date/datetime karisiminda da calisir ve medya satiri tz-aware
    # datetime tasir (ciplak date ICS export'unu de patlatirdi).
    for row in rows:
        assert isinstance(row["due_at"], datetime)
        assert row["due_at"].tzinfo is not None
    ordered = [row["due_at"] for row in rows]
    assert ordered == sorted(ordered)


async def test_media_item_row_drops_when_unit_release_exists(client):
    media = await client.post(
        "/api/media",
        json={
            "title": "Sezonluk Dizi",
            "kind": "show",
            "status": "planned",
            "release_date": "2026-10-01",
        },
    )
    assert media.status_code == 201, media.text
    item_id = media.json()["id"]

    # Unit yayini item yayinindan once: ayni medya icin iki deadline uretilmemeli.
    from app.modules.media.progress import upsert_unit_in_transaction
    from app.modules.media.schemas import MediaUnitUpsert

    async with SessionLocal() as session:
        await upsert_unit_in_transaction(
            session,
            uuid.UUID(item_id),
            MediaUnitUpsert(
                unit_type="episode",
                number=1,
                title="Pilot",
                provider="test",
                provider_id="pilot-1",
                release_at=datetime.now(UTC) + timedelta(days=2),
            ),
        )
        await session.commit()

    async with SessionLocal() as session:
        rows = await collect_deadlines(session)

    media_rows = [row for row in rows if row["module"] == "media"]
    assert media_rows, "unit yayini deadline olarak gorunmeli"
    assert all(row["type"] == "media_unit" for row in media_rows)


# ---------------------------------------------------------------------------
# Faz 5: merdiven ve dislama kurallari
# ---------------------------------------------------------------------------


@pytest.mark.no_database
def test_deadline_rung_picks_the_nearest_threshold():
    """Her kalan sure EN YAKIN basamaga duser; hepsi 30'a yigilmaz."""
    from app.modules.opportunity.service import FOLLOWUP_LADDER_DAYS, deadline_rung

    assert deadline_rung(45) is None
    assert deadline_rung(30) == 30
    assert deadline_rung(29) == 30
    assert deadline_rung(14) == 14
    assert deadline_rung(13) == 14
    assert deadline_rung(7) == 7
    assert deadline_rung(6) == 7
    assert deadline_rung(3) == 3
    assert deadline_rung(2) == 3
    assert deadline_rung(1) == 1
    assert deadline_rung(0) == 1

    # Takip merdiveni 30 gunluk basamak tasimaz.
    assert deadline_rung(30, FOLLOWUP_LADDER_DAYS) is None
    assert deadline_rung(14, FOLLOWUP_LADDER_DAYS) == 14


async def test_deadline_ladder_notifies_once_per_rung(client):
    """Ayni esik icin tekrar tekrar bildirim uretilmez."""
    from sqlalchemy import select

    from app.core.models import Notification
    from app.modules.opportunity.service import deadline_ladder

    created = await client.post(
        "/api/opportunities", json={"title": "Merdiven testi", "kind": "job"}
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    due = datetime.now(UTC) + timedelta(days=6, hours=1)
    assert (
        await client.patch(f"/api/opportunities/{item_id}", json={"deadline_at": due.isoformat()})
    ).status_code == 200

    async with SessionLocal() as session:
        first = await deadline_ladder(session)
    async with SessionLocal() as session:
        second = await deadline_ladder(session)

    async with SessionLocal() as session:
        rows = list(
            (
                await session.execute(
                    select(Notification).where(Notification.dedup_key == f"deadline:{item_id}:7")
                )
            ).scalars()
        )
    assert first >= 1
    assert second == 0
    assert len(rows) == 1


async def test_deadline_provider_drops_past_and_terminal_records(client):
    """Gecmis, arsivlenmis ve terminal kayitlar deadline uretmez."""
    from sqlalchemy import text

    from app.core.deadlines import collect_deadlines
    from app.db import engine

    async def seed(title: str, *, status: str, offset_days: int) -> str:
        item_id = uuid.uuid4()
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "insert into entity (id, type, title, search_text) values "
                    "(:id, 'opportunity', :title, '')"
                ),
                {"id": item_id, "title": title},
            )
            await connection.execute(
                text(
                    "insert into opportunity (id, kind, status, found_at, source, deadline_at) "
                    "values (:id, 'job', :status, now(), 'test', :due)"
                ),
                {"id": item_id, "status": status, "due": datetime.now(UTC) + timedelta(days=offset_days)},
            )
        return str(item_id)

    live_id = await seed("Yaklasan son tarih", status="shortlisted", offset_days=4)
    past_id = await seed("Gecmis son tarih", status="shortlisted", offset_days=-4)
    archived_id = await seed("Arsivlenmis ilan", status="archived", offset_days=4)
    closed_id = await seed("Kapanmis ilan", status="closed", offset_days=4)

    try:
        async with SessionLocal() as session:
            rows = await collect_deadlines(session)
        ids = {row["entity_id"] for row in rows if row["type"] == "opportunity"}
        assert live_id in ids
        assert past_id not in ids, "gecmis son tarih hatirlatma uretmemeli"
        assert archived_id not in ids
        assert closed_id not in ids
    finally:
        async with engine.begin() as connection:
            for item_id in (live_id, past_id, archived_id, closed_id):
                await connection.execute(
                    text("delete from entity where id = :id"), {"id": item_id}
                )
