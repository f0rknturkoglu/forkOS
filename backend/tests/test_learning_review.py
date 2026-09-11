"""Faz 10: SRS kurallari (saf) + tekrar ucu ve kuyrugu."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.time import local_day_bounds, local_today
from app.db import SessionLocal, engine
from app.main import app
from app.modules.learning import service as learning_service
from app.modules.learning.review import GRADES, MAX_INTERVAL, next_review


async def _database_ready() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("select 1 from study_topic limit 1"))
        return True
    except Exception:
        return False


@pytest.fixture
async def client():
    if not await _database_ready():
        pytest.skip("Postgres yok veya migration calismamis")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def _topic(client: AsyncClient, title: str = "Konu", **extra) -> dict:
    area = (
        await client.post("/api/study/areas", json={"title": f"Alan {title}"})
    ).json()
    response = await client.post(
        "/api/study/topics", json={"title": title, "area_id": area["id"], **extra}
    )
    assert response.status_code == 201, response.text
    topic = response.json()
    topic["area_title"] = f"Alan {title}"
    return topic


# ── Saf fonksiyon ───────────────────────────────────────────────────────


@pytest.mark.no_database
@pytest.mark.parametrize(
    ("interval", "ease", "grade", "expected"),
    [
        (0, 2.5, "forgot", (0, 2.3)),
        (5, 2.5, "forgot", (0, 2.3)),
        (0, 2.5, "hard", (1, 2.35)),
        (5, 2.5, "hard", (6, 2.35)),
        (3, 2.5, "medium", (6, 2.5)),
        (3, 2.5, "easy", (8, 2.65)),
        (3, 2.5, "very_easy", (9, 2.8)),
        (400, 2.5, "medium", (365, 2.5)),
        (300, 2.5, "very_easy", (365, 2.8)),
        (0, 1.3, "forgot", (0, 1.3)),
        (0, 3.0, "very_easy", (1, 3.0)),
    ],
)
def test_next_review_rules(interval: int, ease: float, grade: str, expected: tuple) -> None:
    assert next_review(interval, ease, grade) == expected


@pytest.mark.no_database
def test_next_review_is_pure_and_rejects_unknown_grade() -> None:
    assert GRADES == ["forgot", "hard", "medium", "easy", "very_easy"]
    before = (7, 2.5)
    assert next_review(*before, "medium") == (14, 2.5)
    assert before == (7, 2.5)
    with pytest.raises(ValueError):
        next_review(7, 2.5, "mükemmel")
    # Ease tavani asilmaz.
    assert next_review(1, 2.95, "very_easy")[1] == 3.0
    # Aralik tavani asilmaz.
    assert next_review(MAX_INTERVAL, 2.5, "easy")[0] == MAX_INTERVAL


# ── Uc: tekrar ──────────────────────────────────────────────────────────


async def test_review_endpoint_updates_srs_and_queues_today(client: AsyncClient) -> None:
    topic = await _topic(client, "Tekrar")

    first = await client.post(
        f"/api/study/topics/{topic['id']}/review", json={"grade": "medium"}
    )
    assert first.status_code == 200, first.text
    body = first.json()
    # Ilk tekrarda aralik 0*2 -> taban 1 gune oturur.
    assert body["interval_days"] == 1
    assert body["ease"] == 2.5
    assert body["review_count"] == 1
    assert body["last_reviewed_at"] is not None
    assert body["next_review_at"] is not None
    assert body["due"] is False

    second = await client.post(
        f"/api/study/topics/{topic['id']}/review", json={"grade": "hard"}
    )
    assert second.json()["interval_days"] == 1
    assert second.json()["ease"] == 2.35
    assert second.json()["review_count"] == 2

    # mastery yalnizca govdede verilirse guncellenir; easy araligi buyutur.
    third = await client.post(
        f"/api/study/topics/{topic['id']}/review", json={"grade": "easy", "mastery": 65}
    )
    assert third.json()["interval_days"] == 2
    assert third.json()["ease"] == 2.5
    assert third.json()["mastery"] == 65

    # "forgot" konuyu AYNI GUNE geri koyar.
    fourth = await client.post(
        f"/api/study/topics/{topic['id']}/review", json={"grade": "forgot"}
    )
    assert fourth.json()["interval_days"] == 0
    assert fourth.json()["due"] is True

    detail = (await client.get(f"/api/study/topics/{topic['id']}")).json()
    assert detail["review"]["review_count"] == 4
    assert detail["topic"]["mastery"] == 65
    assert detail["review"]["next_review_at"] == fourth.json()["next_review_at"]

    # Event'ler yazildi.
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                text(
                    "select verb, payload->>'grade' from event"
                    " where entity_id = :id and verb = 'study.reviewed' order by id"
                ),
                {"id": topic["id"]},
            )
        ).all()
    assert [row[0] for row in rows] == ["study.reviewed"] * 4
    assert [row[1] for row in rows] == ["medium", "hard", "easy", "forgot"]

    assert (
        await client.post(f"/api/study/topics/{topic['id']}/review", json={"grade": "yok"})
    ).status_code == 422
    assert (
        await client.post(
            f"/api/study/topics/{UUID(int=0)}/review", json={"grade": "medium"}
        )
    ).status_code == 404


async def test_completing_a_topic_queues_the_first_review(client: AsyncClient) -> None:
    topic = await _topic(client, "Yeni biten")
    assert (
        await client.patch(f"/api/study/topics/{topic['id']}", json={"status": "done"})
    ).status_code == 200

    detail = (await client.get(f"/api/study/topics/{topic['id']}")).json()
    assert detail["review"]["next_review_at"] is not None
    assert detail["review"]["due"] is True
    assert detail["review"]["review_count"] == 0

    queue = (await client.get("/api/study/review")).json()
    assert topic["id"] in {row["id"] for row in queue["due_today"]}


async def test_review_queue_buckets_windows_and_weak(client: AsyncClient) -> None:
    today = local_today()
    due = await _topic(client, "Bugün")
    overdue = await _topic(client, "Gecikmiş")
    upcoming = await _topic(client, "Yaklaşan")
    fresh = await _topic(client, "Yeni")

    async def set_review(topic_id: str, at: datetime) -> None:
        async with SessionLocal() as session:
            await session.execute(
                text("update study_topic set next_review_at = :at where id = :id"),
                {"at": at, "id": topic_id},
            )
            await session.commit()

    await set_review(due["id"], datetime.now(UTC))
    await set_review(overdue["id"], local_day_bounds(today - timedelta(days=3))[0])
    await set_review(upcoming["id"], local_day_bounds(today + timedelta(days=5))[0])
    # Yeni: hic tekrar edilmemis ama calisiliyor.
    await client.patch(f"/api/study/topics/{fresh['id']}", json={"status": "in_progress"})
    # Zayif: dusuk mastery.
    await client.patch(f"/api/study/topics/{due['id']}", json={"mastery": 20})

    queue = (await client.get("/api/study/review", params={"window": 14})).json()
    assert {row["id"] for row in queue["due_today"]} == {due["id"]}
    assert {row["id"] for row in queue["overdue"]} == {overdue["id"]}
    assert {row["id"] for row in queue["upcoming"]} == {upcoming["id"], fresh["id"]} or {
        row["id"] for row in queue["upcoming"]
    } == {upcoming["id"]}
    assert fresh["id"] in {row["id"] for row in queue["new_topics"]}
    assert {row["id"] for row in queue["weak"]} >= {due["id"]}

    # Pencere daralinca yaklasanlar listeye girmez.
    narrow = (await client.get("/api/study/review", params={"window": 1})).json()
    assert upcoming["id"] not in {row["id"] for row in narrow["upcoming"]}
    assert due["id"] in {row["id"] for row in narrow["due_today"]}

    # Satirlar derin baglanti bilgisi tasir.
    row = queue["due_today"][0]
    assert row["title"] == "Bugün"
    assert row["area_id"] == due["area_id"]
    assert row["area_title"] == due["area_title"]
    assert row["mastery"] == 20

    # limit her listeye uygulanir.
    limited = (await client.get("/api/study/review", params={"limit": 1})).json()
    assert len(limited["due_today"]) <= 1


async def test_repeated_forgot_marks_topic_weak(client: AsyncClient) -> None:
    topic = await _topic(client, "Unutulan")
    for _ in range(3):
        response = await client.post(
            f"/api/study/topics/{topic['id']}/review", json={"grade": "forgot"}
        )
        assert response.status_code == 200
    assert response.json()["interval_days"] == 0
    assert response.json()["ease"] == 1.9

    queue = (await client.get("/api/study/review")).json()
    assert topic["id"] in {row["id"] for row in queue["weak"]}
    assert topic["id"] in {row["id"] for row in queue["due_today"]}


async def test_topic_review_queue_helper_exposes_today_lists(client: AsyncClient) -> None:
    """Main'in today entegrasyonu bu yardimciyi cagirir."""
    topic = await _topic(client, "Bugünkü")
    await client.post(f"/api/study/topics/{topic['id']}/review", json={"grade": "forgot"})

    async with SessionLocal() as session:
        queue = await learning_service.topic_review_queue(session, window_days=14, limit=5)
    assert set(queue) == {"due_today", "overdue", "upcoming", "new_topics", "weak"}
    row = next(item for item in queue["due_today"] if str(item["id"]) == topic["id"])
    assert {
        "id",
        "title",
        "area_id",
        "area_title",
        "next_review_at",
        "mastery",
    } <= set(row)
    assert row["title"] == "Bugünkü"
    assert row["area_title"] == topic["area_title"]


async def test_stale_uses_ancestor_chain_after_study(client: AsyncClient) -> None:
    """Alt konu calisilinca ust konular stale listesinden cikar (zincir)."""
    area = (await client.post("/api/study/areas", json={"title": "Zincir"})).json()
    root = (
        await client.post(
            "/api/study/topics", json={"title": "Kök", "area_id": area["id"]}
        )
    ).json()
    leaf = (
        await client.post(
            "/api/study/topics",
            json={"title": "Yaprak", "area_id": area["id"], "parent_id": root["id"]},
        )
    ).json()

    async with SessionLocal() as session:
        updated = await learning_service.touch_topic_chain(
            session, UUID(leaf["id"]), at=datetime.now(UTC)
        )
        assert updated == 2
        await session.commit()

    assert (await client.get("/api/study/stale", params={"days": 21})).json()["items"] == []
