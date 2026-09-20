"""Faz 1-2/5-8: dogrulama, N+1'siz agac, stale/istatistik, kaynak+yer imi, kurs.

Veritabani gerektirir; Postgres yoksa dosya atlanir (test_api.py deseni).
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text

from app.core.entity import create_entity
from app.core.links import link as create_link
from app.core.time import local_today
from app.db import SessionLocal, engine
from app.main import app
from app.modules.learning import MODULE
from app.modules.learning.models import StudyTopic

APP_DIR = Path(__file__).resolve().parents[1] / "app"


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


async def _area(client: AsyncClient, title: str = "Alan", **extra) -> dict:
    response = await client.post("/api/study/areas", json={"title": title, **extra})
    assert response.status_code == 201, response.text
    return response.json()


async def _topic(client: AsyncClient, area_id: str, title: str, **extra) -> dict:
    response = await client.post(
        "/api/study/topics", json={"title": title, "area_id": area_id, **extra}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _resource(client: AsyncClient, topic_id: str, title: str, **extra) -> dict:
    response = await client.post(
        f"/api/study/topics/{topic_id}/resources", json={"title": title, **extra}
    )
    assert response.status_code == 201, response.text
    return response.json()


# ── Faz 1: parent dogrulama + cycle guard ───────────────────────────────


async def test_parent_validation_rejects_self_cross_area_and_descendant(
    client: AsyncClient,
) -> None:
    area = await _area(client, "Matematik")
    other = await _area(client, "Fizik")
    root = await _topic(client, area["id"], "Kök")
    child = await _topic(client, area["id"], "Çocuk", parent_id=root["id"])
    stranger = await _topic(client, other["id"], "Yabancı")

    # Kendi ebeveyni olamaz.
    assert (
        await client.patch(f"/api/study/topics/{root['id']}", json={"parent_id": root["id"]})
    ).status_code == 422
    # Baska alandaki konu ebeveyn olamaz.
    assert (
        await client.patch(f"/api/study/topics/{child['id']}", json={"parent_id": stranger["id"]})
    ).status_code == 422
    # Kendi alt agacinin altina tasinamaz (descendant cycle).
    cycle = await client.patch(
        f"/api/study/topics/{root['id']}", json={"parent_id": child["id"]}
    )
    assert cycle.status_code == 422
    assert (
        await client.post(
            f"/api/study/topics/{root['id']}/move", json={"parent_id": child["id"]}
        )
    ).status_code == 422
    # create akisi da ayni kurali uygular.
    assert (
        await client.post(
            "/api/study/topics",
            json={"title": "X", "area_id": area["id"], "parent_id": stranger["id"]},
        )
    ).status_code == 422
    # Gecerli tasima gecer: cocuk koke cikar.
    moved = await client.post(f"/api/study/topics/{child['id']}/move", json={"parent_id": None})
    assert moved.status_code == 200
    assert moved.json()["parent_id"] is None


async def test_existing_cycle_data_does_not_hang_reads(client: AsyncClient) -> None:
    """Bozuk (cycle'li) veri recursive CTE'leri kilitleyemez."""
    area = await _area(client, "Döngü")
    first = await _topic(client, area["id"], "A")
    second = await _topic(client, area["id"], "B", parent_id=first["id"])
    async with SessionLocal() as session:
        await session.execute(
            text("update study_topic set parent_id = :b where id = :a"),
            {"a": first["id"], "b": second["id"]},
        )
        await session.commit()

    tree = await client.get(f"/api/study/areas/{area['id']}/tree")
    assert tree.status_code == 200
    body = tree.json()
    assert {node["id"] for node in body["nodes"]} == {first["id"], second["id"]}
    assert body["orphan_count"] == 1

    assert (await client.get(f"/api/study/topics/{first['id']}")).status_code == 200
    assert (await client.get(f"/api/study/topics?area_id={area['id']}")).status_code == 200
    assert (await client.get(f"/api/study/topics/{first['id']}/impact")).status_code == 200


# ── Faz 2: agac sekli, N+1 yok, sorgu sayisi sabit ──────────────────────


async def test_area_tree_is_flat_with_rollup_and_totals(client: AsyncClient) -> None:
    area = await _area(client, "Ağaç")
    root = await _topic(client, area["id"], "Kök")
    child = await _topic(client, area["id"], "Çocuk", parent_id=root["id"])
    await _resource(client, root["id"], "Kök kaynağı")
    done = await _resource(client, child["id"], "Alt kaynak")
    await _resource(client, child["id"], "İkinci alt kaynak")
    assert (
        await client.patch(f"/api/learning/resources/{done['id']}", json={"completed": True})
    ).status_code == 200
    # Odak seansi alt konuya baglanir; ust dugume toplanir.
    pomo = (
        await client.post(
            "/api/pomodoro/start", json={"planned_min": 1, "context_entity_id": child["id"]}
        )
    ).json()
    await client.post(f"/api/pomodoro/{pomo['id']}/stop", json={})

    body = (await client.get(f"/api/study/areas/{area['id']}/tree")).json()
    by_id = {node["id"]: node for node in body["nodes"]}
    assert by_id[root["id"]]["depth"] == 0
    assert by_id[child["id"]]["depth"] == 1
    assert by_id[child["id"]]["path"] == [root["id"]]
    assert by_id[root["id"]]["child_count"] == 1
    # Alt agac toplami ust dugumde birikir.
    assert by_id[root["id"]]["resource_total"] == 3
    assert by_id[root["id"]]["resource_done"] == 1
    assert by_id[root["id"]]["progress_pct"] == 33
    assert by_id[child["id"]]["resource_total"] == 2
    assert by_id[child["id"]]["focus_minutes"] == 1
    assert by_id[child["id"]]["focus_sessions"] == 1
    assert by_id[root["id"]]["focus_minutes"] == 1
    assert body["totals"] == {
        "topics": 2,
        "done": 0,
        "in_progress": 0,
        "review_due": 0,
        "resource_total": 3,
        "resource_done": 1,
        "focus_minutes": 1,
        "focus_sessions": 1,
    }
    assert body["orphan_count"] == 0
    assert body["area"]["topic_count"] == 2
    assert body["area"]["resource_count"] == 3

    # q aramasi dali acar: eslesen cocugun atasi da doner.
    filtered = (
        await client.get(f"/api/study/areas/{area['id']}/tree", params={"q": "çocuk"})
    ).json()
    assert {node["id"] for node in filtered["nodes"]} == {root["id"], child["id"]}
    assert filtered["totals"]["topics"] == 2

    # durum filtresi yalniz eslesenleri doner.
    none_done = (
        await client.get(f"/api/study/areas/{area['id']}/tree", params={"status": "done"})
    ).json()
    assert none_done["nodes"] == []

    # include_resources kaynaklari dugume ekler.
    with_resources = (
        await client.get(
            f"/api/study/areas/{area['id']}/tree", params={"include_resources": True}
        )
    ).json()
    node = next(n for n in with_resources["nodes"] if n["id"] == child["id"])
    assert [r["title"] for r in node["resources"]] == ["Alt kaynak", "İkinci alt kaynak"]


async def test_tree_query_count_does_not_grow_with_topics(client: AsyncClient) -> None:
    """256 konuluk alanda agac sabit sayida SQL ifadesi kullanir."""
    area = await _area(client, "Git ve GitHub")
    area_id = UUID(area["id"])
    async with SessionLocal() as session:
        for index in range(256):
            entity = await create_entity(session, type="study_topic", title=f"Konu {index:03d}")
            session.add(
                StudyTopic(id=entity.id, area_id=area_id, position=index, status="in_progress")
            )
        await session.commit()

    statements: list[str] = []

    def counter(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", counter)
    try:
        response = await client.get(f"/api/study/areas/{area['id']}/tree")
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", counter)

    assert response.status_code == 200
    assert len(response.json()["nodes"]) == 256
    assert response.json()["totals"]["in_progress"] == 256
    assert len(statements) <= 6, f"{len(statements)} sorgu atildi: {statements}"


# ── Faz 1: bilinmeyen id 404 ────────────────────────────────────────────


async def test_unknown_ids_return_404_instead_of_empty(client: AsyncClient) -> None:
    missing = uuid.uuid4()
    assert (await client.get(f"/api/study/topics/{missing}")).status_code == 404
    assert (await client.get(f"/api/study/topics/{missing}")).status_code == 404
    assert (await client.get(f"/api/study/topics/{missing}/progress")).status_code == 404
    assert (await client.get(f"/api/study/topics/{missing}/resources")).status_code == 404
    assert (await client.get(f"/api/study/topics/{missing}/impact")).status_code == 404
    assert (await client.get(f"/api/learning/resources/{missing}")).status_code == 404
    assert (await client.get(f"/api/study/areas/{missing}/tree")).status_code == 404
    assert (await client.get(f"/api/study/topics?area_id={missing}")).status_code == 404
    assert (await client.post(f"/api/study/topics/{missing}/todos")).status_code == 404


# ── Faz 1: sema sinirlari ───────────────────────────────────────────────


async def test_schema_rejects_blank_titles_bad_urls_and_bad_values(client: AsyncClient) -> None:
    area = await _area(client, "Şema")
    assert (
        await client.post("/api/study/topics", json={"title": "   ", "area_id": area["id"]})
    ).status_code == 422
    assert (await client.post("/api/study/areas", json={"title": " "})).status_code == 422
    assert (
        await client.post(
            "/api/study/topics",
            json={"title": "Konu", "area_id": area["id"], "status": "bitmis"},
        )
    ).status_code == 422
    assert (
        await client.post(
            "/api/study/topics", json={"title": "x" * 301, "area_id": area["id"]}
        )
    ).status_code == 422
    topic = await _topic(client, area["id"], "  Fazla   boşluk  ")
    # Baslik kirpilir ve ic bosluklar sadelesir.
    assert topic["title"] == "Fazla boşluk"
    assert (
        await client.post(
            f"/api/study/topics/{topic['id']}/resources",
            json={"title": "Kaynak", "url": "ftp://example.com/x"},
        )
    ).status_code == 422
    assert (
        await client.post(
            f"/api/study/topics/{topic['id']}/resources",
            json={"title": "Kaynak", "url": "https://example.com/" + "a" * 2100},
        )
    ).status_code == 422


# ── Faz 2: stale ────────────────────────────────────────────────────────


async def test_stale_filters_pagination_and_archived_areas(client: AsyncClient) -> None:
    first_area = await _area(client, "Stale A")
    second_area = await _area(client, "Stale B")
    stale_topic = await _topic(client, first_area["id"], "Hiç çalışılmamış")
    done_topic = await _topic(client, first_area["id"], "Bitmiş")
    fresh = await _topic(client, first_area["id"], "Taze")
    await _topic(client, second_area["id"], "Pasif alanda")
    await client.patch(f"/api/study/topics/{done_topic['id']}", json={"status": "done"})
    async with SessionLocal() as session:
        await session.execute(
            text("update study_topic set last_studied_at = :at where id = :id"),
            {"at": datetime.now(UTC), "id": fresh["id"]},
        )
        await session.commit()
    # Alan kapatilinca konulari listeden duser (active=false).
    assert (
        await client.patch(f"/api/study/areas/{second_area['id']}", json={"active": False})
    ).status_code == 200

    page = (await client.get("/api/study/stale", params={"days": 21})).json()
    assert [row["id"] for row in page["items"]] == [stale_topic["id"]]
    assert page["total"] == 1 and page["limit"] == 20 and page["offset"] == 0

    # include_done=false varsayilani; true iken bitmis konu da gelir.
    with_done = (await client.get("/api/study/stale", params={"include_done": True})).json()
    assert {row["id"] for row in with_done["items"]} == {stale_topic["id"], done_topic["id"]}

    # Alan filtresi + sayfalama.
    assert (await client.get("/api/study/stale", params={"area_id": uuid.uuid4()})).json()[
        "items"
    ] == []
    empty_page = (await client.get("/api/study/stale", params={"limit": 1, "offset": 5})).json()
    assert empty_page["items"] == [] and empty_page["offset"] == 5

    # days sinirli: 7-365 disi reddedilir.
    assert (await client.get("/api/study/stale", params={"days": 3})).status_code == 422
    assert (await client.get("/api/study/stale", params={"days": 400})).status_code == 422
    assert (await client.get("/api/study/stale", params={"limit": 500})).status_code == 422

    # Arsivlenen alan da varsayilan listede yok.
    archived_area = await _area(client, "Arşiv")
    archived_topic = await _topic(client, archived_area["id"], "Arşiv konusu")
    assert (
        await client.patch(f"/api/study/areas/{archived_area['id']}", json={"archived": True})
    ).status_code == 200
    ids = {row["id"] for row in (await client.get("/api/study/stale")).json()["items"]}
    assert archived_topic["id"] not in ids


async def test_area_patch_archive_and_restore(client: AsyncClient) -> None:
    area = await _area(client, "Yönetim")
    archived = await client.patch(f"/api/study/areas/{area['id']}", json={"archived": True})
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    assert archived.json()["active"] is False

    restored = await client.patch(f"/api/study/areas/{area['id']}", json={"archived": False})
    assert restored.json()["archived_at"] is None
    assert restored.json()["active"] is True

    renamed = await client.patch(
        f"/api/study/areas/{area['id']}", json={"title": "Yeni ad", "color": "#ff0000"}
    )
    assert renamed.json()["title"] == "Yeni ad"
    # Arama yenilenen basligi bulur.
    assert {row["id"] for row in (await client.get("/api/search", params={"q": "Yeni ad"})).json()} >= {
        area["id"]
    }


async def test_area_list_with_stats(client: AsyncClient) -> None:
    area = await _area(client, "İstatistik")
    topic = await _topic(client, area["id"], "Konu")
    await _topic(client, area["id"], "Bitmiş", status="done")
    resource = await _resource(client, topic["id"], "Kaynak", url="https://example.com/a")
    await client.patch(f"/api/learning/resources/{resource['id']}", json={"completed": True})

    rows = (await client.get("/api/study/areas", params={"include_stats": True})).json()
    row = next(item for item in rows if item["id"] == area["id"])
    assert row["topic_count"] == 2
    assert row["done_count"] == 1
    assert row["resource_count"] == 1
    assert row["resource_done"] == 1
    assert row["stale_count"] == 2
    assert row["focus_minutes"] == 0

    # Varsayilan (include_stats yok) ayni yanitta sifir sayaclarla gelir.
    plain = (await client.get("/api/study/areas")).json()
    assert next(item for item in plain if item["id"] == area["id"])["topic_count"] == 0


# ── Faz 5: konu detayi, kaynak, yer imi ─────────────────────────────────


async def test_topic_detail_bundles_everything_the_ui_needs(client: AsyncClient) -> None:
    area = await _area(client, "Detay")
    area2 = await _area(client, "Baska")
    assert area2["id"] != area["id"]
    root = await _topic(client, area["id"], "Kök")
    child = await _topic(client, area["id"], "Alt", parent_id=root["id"], confidence=3)
    resource = await _resource(
        client, child["id"], "Kaynak", url="https://example.com/x", note="not"
    )
    await client.patch(f"/api/learning/resources/{resource['id']}", json={"completed": True})
    todo = (
        await client.post(f"/api/study/topics/{child['id']}/todos", json={"priority": 1})
    ).json()["todo"]
    async with SessionLocal() as session:
        deck = await create_entity(session, type="flashcard_deck", title="Deste")
        await create_link(session, deck.id, UUID(child["id"]), "studies")
        await session.commit()

    body = (await client.get(f"/api/study/topics/{child['id']}")).json()
    assert body["topic"]["id"] == child["id"]
    assert body["topic"]["title"] == "Alt"
    assert body["ancestors"] == [{"id": root["id"], "title": "Kök"}]
    assert body["resources"][0]["title"] == "Kaynak"
    assert body["progress"] == {"total": 1, "done": 1, "pct": 100}
    assert body["stats"]["sessions"] == 0
    assert body["open_todo"]["id"] == todo["id"]
    assert body["open_todo"]["priority"] == 1
    # PHASE 3: `note_count` KALDIRILDI -- konu bilgisi artık Vault'ta yaşar ve
    # forkOS tarafında sayılacak bir not kaydı yoktur.
    assert body["flashcard_deck_count"] == 1
    assert body["review"]["review_count"] == 0
    assert body["review"]["due"] is False

    # Deep-link: kaynak tekil ucundan cozulur ve acilma damgasi basar.
    fetched = await client.get(f"/api/learning/resources/{resource['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["topic_id"] == child["id"]
    assert fetched.json()["last_opened_at"] is not None


async def test_attach_bookmark_is_idempotent_and_reads_fresh_data(client: AsyncClient) -> None:
    area = await _area(client, "Yer imi")
    topic = await _topic(client, area["id"], "Konu")
    other = await _topic(client, area["id"], "Diger konu")
    captured = (
        await client.post(
            "/api/capture",
            json={"url": "https://example.com/makale", "title": "İlk başlık"},
        )
    ).json()

    first = await client.post(
        "/api/study/resources/attach-bookmark",
        json={"topic_id": topic["id"], "bookmark_id": captured["id"]},
    )
    assert first.status_code == 200, first.text
    assert first.json()["source"] == "bookmark"
    assert first.json()["bookmark_id"] == captured["id"]
    assert first.json()["title"] == "İlk başlık"

    # Ayni bookmark ayni konuya: yeni kayit ACILMAZ.
    again = await client.post(
        "/api/study/resources/attach-bookmark",
        json={"topic_id": topic["id"], "bookmark_id": captured["id"]},
    )
    assert again.json()["id"] == first.json()["id"]
    listed = (await client.get(f"/api/study/topics/{topic['id']}/resources")).json()
    assert len(listed) == 1

    # Yer imi yeniden adlandirilinca gosterim tazelenir (kopya tutulmaz).
    await client.patch(f"/api/bookmarks/{captured['id']}", json={"title": "Yeni başlık"})
    refreshed = (await client.get(f"/api/learning/resources/{first.json()['id']}")).json()
    assert refreshed["title"] == "Yeni başlık"

    # Baska konuya da baglanabilir.
    third = await client.post(
        "/api/study/resources/attach-bookmark",
        json={"topic_id": other["id"], "bookmark_id": captured["id"]},
    )
    assert third.status_code == 200
    assert third.json()["id"] != first.json()["id"]

    # Yer imine bagli kaynagin basligi yer iminden gelir: PATCH reddedilir.
    rejected = await client.patch(
        f"/api/learning/resources/{first.json()['id']}", json={"title": "Elle"}
    )
    assert rejected.status_code == 422
    # note/estimated_min serbest.
    assert (
        await client.patch(
            f"/api/learning/resources/{first.json()['id']}",
            json={"note": "notum", "estimated_min": 30},
        )
    ).status_code == 200

    # Bilinmeyen yer imi 422, bilinmeyen konu 404.
    assert (
        await client.post(
            "/api/study/resources/attach-bookmark",
            json={"topic_id": topic["id"], "bookmark_id": str(uuid.uuid4())},
        )
    ).status_code == 422
    assert (
        await client.post(
            "/api/study/resources/attach-bookmark",
            json={"topic_id": str(uuid.uuid4()), "bookmark_id": captured["id"]},
        )
    ).status_code == 404


async def test_search_text_stays_in_sync_on_rename_and_url_change(client: AsyncClient) -> None:
    area = await _area(client, "Arama")
    topic = await _topic(client, area["id"], "Lineer Cebir")
    resource = await _resource(
        client,
        topic["id"],
        "Kaynak",
        url="https://alpha.example.com/kurs",
        note="gizli not",
    )

    async def hits(query: str) -> set[str]:
        return {row["id"] for row in (await client.get("/api/search", params={"q": query})).json()}

    assert topic["id"] in await hits("Lineer Cebir")
    assert resource["id"] in await hits("alpha.example.com")
    assert resource["id"] in await hits("gizli not")

    await client.patch(f"/api/study/topics/{topic['id']}", json={"title": "Matris Teorisi"})
    assert topic["id"] not in await hits("Lineer Cebir")
    assert topic["id"] in await hits("Matris Teorisi")

    await client.patch(
        f"/api/learning/resources/{resource['id']}",
        json={"url": "https://beta.example.com/kurs"},
    )
    assert resource["id"] not in await hits("alpha.example.com")
    assert resource["id"] in await hits("beta.example.com")


async def test_topic_todo_is_idempotent_without_force(client: AsyncClient) -> None:
    area = await _area(client, "Görev")
    topic = await _topic(client, area["id"], "Konu")

    first = await client.post(f"/api/study/topics/{topic['id']}/todos", json={"priority": 1})
    assert first.status_code == 201
    assert first.json()["created"] is True

    second = await client.post(f"/api/study/topics/{topic['id']}/todos")
    assert second.status_code == 201
    assert second.json()["created"] is False
    assert second.json()["todo"]["id"] == first.json()["todo"]["id"]

    forced = await client.post(
        f"/api/study/topics/{topic['id']}/todos", json={"force": True}
    )
    assert forced.json()["created"] is True
    assert forced.json()["todo"]["id"] != first.json()["todo"]["id"]

    # Acik gorev kapaninca yenisi uretilir.
    await client.patch(f"/api/todos/{first.json()['todo']['id']}", json={"status": "done"})
    await client.patch(f"/api/todos/{forced.json()['todo']['id']}", json={"status": "done"})
    third = await client.post(f"/api/study/topics/{topic['id']}/todos")
    assert third.json()["created"] is True


async def test_touch_topic_chain_updates_ancestors(client: AsyncClient) -> None:
    """Main'in pomodoro entegrasyonu bu yardimciyi cagirir (kaynak baglami)."""
    from app.modules.learning import service as learning_service

    area = await _area(client, "Zincir")
    root = await _topic(client, area["id"], "Kök")
    mid = await _topic(client, area["id"], "Orta", parent_id=root["id"])
    leaf = await _topic(client, area["id"], "Yaprak", parent_id=mid["id"])

    moment = datetime.now(UTC)
    async with SessionLocal() as session:
        updated = await learning_service.touch_topic_chain(
            session, UUID(leaf["id"]), at=moment
        )
        await session.commit()
    assert updated == 3

    for topic_id in (leaf["id"], mid["id"], root["id"]):
        detail = (await client.get(f"/api/study/topics/{topic_id}")).json()
        assert detail["topic"]["last_studied_at"] is not None
    # Komsu dal etkilenmez ve stale listesinden cikar.
    page = (await client.get("/api/study/stale")).json()
    assert {row["id"] for row in page["items"]} == set()


# ── Faz 8: kurslar ──────────────────────────────────────────────────────


async def test_course_lifecycle_dates_links_and_archive(client: AsyncClient) -> None:
    area = await _area(client, "Kurs alanı")
    topic = await _topic(client, area["id"], "Kurs konusu")
    created = await client.post(
        "/api/courses",
        json={
            "title": "İleri Python",
            "platform": "Udemy",
            "url": "https://udemy.com/python",
            "area_ids": [area["id"]],
            "topic_ids": [topic["id"]],
        },
    )
    assert created.status_code == 201, created.text
    course = created.json()
    assert course["status"] == "planned"
    assert course["started_at"] is None
    assert course["area_ids"] == [area["id"]]
    assert course["topic_ids"] == [topic["id"]]
    assert course["resource_count"] == 0

    started = await client.patch(f"/api/courses/{course['id']}", json={"status": "in_progress"})
    assert started.json()["started_at"] == local_today().isoformat()
    assert started.json()["completed_at"] is None

    # progress_pct==100 durumu 'done'a senkronlar ve bitis tarihini yazar.
    finished = await client.patch(f"/api/courses/{course['id']}", json={"progress_pct": 100})
    assert finished.json()["status"] == "done"
    assert finished.json()["completed_at"] == local_today().isoformat()

    # Yeniden acma: bitis tarihi temizlenir.
    reopened = await client.patch(f"/api/courses/{course['id']}", json={"status": "in_progress"})
    assert reopened.json()["completed_at"] is None
    assert reopened.json()["started_at"] == local_today().isoformat()

    # Alan filtresi ve arsiv gorunurlugu.
    listed = (await client.get("/api/courses", params={"area_id": area["id"]})).json()
    assert [row["id"] for row in listed] == [course["id"]]
    assert (await client.get("/api/courses", params={"area_id": str(uuid.uuid4())})).json() == []
    await client.patch(f"/api/courses/{course['id']}", json={"archived": True})
    assert (await client.get("/api/courses")).json() == []
    assert len((await client.get("/api/courses", params={"include_archived": True})).json()) == 1

    # Sertifika yalnizca document olabilir (note artik canli bir tip degil).
    assert (
        await client.patch(
            f"/api/courses/{course['id']}", json={"certificate_entity_id": area["id"]}
        )
    ).status_code == 422
    async with SessionLocal() as session:
        certificate = await create_entity(session, type="document", title="Sertifika")
        await session.commit()
        certificate_id = str(certificate.id)
    ok = await client.patch(
        f"/api/courses/{course['id']}", json={"certificate_entity_id": certificate_id}
    )
    assert ok.status_code == 200
    assert ok.json()["certificate_entity_id"] == certificate_id

    # Bilinmeyen durum reddedilir.
    assert (
        await client.patch(f"/api/courses/{course['id']}", json={"status": "yarim"})
    ).status_code == 422

    assert (await client.delete(f"/api/courses/{course['id']}")).status_code == 204
    assert (await client.delete(f"/api/courses/{course['id']}")).status_code == 404


# ── Faz 2: istatistik ───────────────────────────────────────────────────


async def test_study_stats_endpoint_reports_focus_and_counters(client: AsyncClient) -> None:
    area = await _area(client, "Stat")
    topic = await _topic(client, area["id"], "Konu")
    pomo = (
        await client.post(
            "/api/pomodoro/start", json={"planned_min": 1, "context_entity_id": topic["id"]}
        )
    ).json()
    await client.post(f"/api/pomodoro/{pomo['id']}/stop", json={})
    await client.patch(f"/api/study/topics/{topic['id']}", json={"status": "done"})

    body = (await client.get("/api/study/stats", params={"range": "week"})).json()
    assert body["focus_minutes"] >= 1
    assert body["focus_sessions"] >= 1
    assert body["actual_minutes"] == body["focus_minutes"]
    assert body["topics_done"] == 1
    assert body["active_days"] >= 1
    assert (body["by_area"][0]["area_id"]) == area["id"]
    assert body["by_topic"][0]["topic_id"] == topic["id"]
    assert body["courses"] == {"total": 0, "done": 0, "in_progress": 0}

    assert (await client.get("/api/study/stats", params={"range": "çöp"})).status_code == 422
    assert (await client.get("/api/study/stats", params={"range": "all"})).status_code == 200


# ── Event kayit defteri sozlesmesi (DB'siz) ─────────────────────────────


DECLARED_VERBS = {
    "study.area_created",
    "study.area_archived",
    "study.area_reopened",
    "study.area_deleted",
    "study.topic_created",
    "study.topic_renamed",
    "study.topic_moved",
    "study.topic_started",
    "study.topic_reopened",
    "study.topic_completed",
    "study.topic_deleted",
    "study.confidence_changed",
    "study.mastery_changed",
    "study.reviewed",
    "course.created",
    "course.started",
    "course.progressed",
    "course.completed",
    "course.reopened",
    "course.deleted",
    "learning.resource_added",
    "learning.resource_updated",
    "learning.resource_completed",
    "learning.resource_reopened",
    "learning.resource_deleted",
    "learning.imported",
}


def _logged_verbs(source: str) -> set[str]:
    """Her `log_event(...)` cagrisinin icindeki tum fiil dizeleri."""
    verbs: set[str] = set()
    start = 0
    while True:
        index = source.find("log_event(", start)
        if index == -1:
            return verbs
        depth = 0
        cursor = index + len("log_event")
        end = len(source)
        while cursor < len(source):
            char = source[cursor]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    end = cursor
                    break
            cursor += 1
        verbs.update(re.findall(r'"([a-z][a-z_]*\.[a-z_.]+)"', source[index:end]))
        start = end + 1


@pytest.mark.no_database
def test_learning_registers_complete_event_contract() -> None:
    assert set(MODULE.event_verbs) == DECLARED_VERBS

    source = (APP_DIR / "modules" / "learning" / "service.py").read_text(encoding="utf-8")
    logged = _logged_verbs(source)
    # Deklare edilmeyen fiil uretilmez; deklare edilen her fiil bir cagride gecer.
    assert logged <= DECLARED_VERBS, f"kayitsiz event: {sorted(logged - DECLARED_VERBS)}"
    referenced = set(re.findall(r'"([a-z][a-z_]*\.[a-z_.]+)"', source))
    assert referenced >= DECLARED_VERBS, f"hic gecmeyen event: {sorted(DECLARED_VERBS - referenced)}"


@pytest.mark.no_database
def test_learning_resource_route_resolves_deep_link() -> None:
    spec = next(item for item in MODULE.entity_types if item.type == "learning_resource")
    assert spec.route == "/learning?resource={id}"
