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
