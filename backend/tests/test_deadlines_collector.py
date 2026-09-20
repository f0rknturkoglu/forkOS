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
# Faz 5 / H6: takip satirlari ve dislama kurallari
# ---------------------------------------------------------------------------


async def test_follow_up_rows_are_the_canonical_take_over_source(client):
    """Takip tarihleri artik TEK kaynaktan gelir: `pending_follow_up_rows`.

    Son tarih merdiveni H6'ya tasindi; takip satirlari ayni fonksiyon
    uzerinden H6 kuralina beslenir (ikinci bir uretici yok).
    """
    from app.modules.opportunity.service import pending_follow_up_rows

    created = await client.post(
        "/api/opportunities", json={"title": "Takip testi", "kind": "job"}
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    assert (
        await client.put(
            f"/api/opportunities/{item_id}/application", json={"status": "applied"}
        )
    ).status_code in (200, 201)
    follow_up = datetime.now(UTC) + timedelta(days=6, hours=1)
    assert (
        await client.patch(
            f"/api/opportunities/{item_id}", json={"follow_up_at": follow_up.isoformat()}
        )
    ).status_code == 200

    async with SessionLocal() as session:
        rows = await pending_follow_up_rows(session)

    matching = [row for row in rows if str(row["entity_id"]) == item_id]
    assert matching, "takip tarihi yaklasan basvuru kanonik kaynakta gorunmeli"
    assert matching[0]["sub_kind"] == "follow_up"
    assert matching[0]["module"] == "opportunity"


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
