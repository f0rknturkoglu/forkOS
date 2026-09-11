"""Faz 9: ice aktarma onizlemesi, guncelleme semantigi, prune ve atomiklik."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import SessionLocal, engine
from app.main import app
from app.modules.learning import service as learning_service


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


TREE = {
    "area": "Makine Öğrenmesi",
    "topics": [
        {
            "title": "Doğrusal Modeller",
            "status": "in_progress",
            "resources": [
                {"title": "ISLR bölüm 3", "url": "https://example.com/islr3", "kind": "book"},
                {"title": "Ders videosu", "url": "https://example.com/v1", "kind": "video"},
            ],
            "children": [
                {
                    "title": "Regularizasyon",
                    "resources": [{"title": "Ridge & Lasso", "url": "https://example.com/ridge"}],
                }
            ],
        },
        {"title": "Ağaç Tabanlı Modeller"},
    ],
}


# ── Onizleme (yazma YOK) ────────────────────────────────────────────────


async def test_preview_classifies_without_writing(client: AsyncClient) -> None:
    response = await client.post("/api/study/import/preview", json=TREE)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["area"]["exists"] is False
    assert body["area"]["id"] is None
    assert [node["title"] for node in body["creates"]] == [
        "Doğrusal Modeller",
        "Regularizasyon",
        "Ağaç Tabanlı Modeller",
    ]
    assert body["updates"] == []
    assert body["matches"] == []
    assert body["resources_new"] == 3
    assert body["resources_duplicate"] == 0
    assert body["totals"] == {"nodes": 3, "depth": 2, "creates": 3, "updates": 0, "matches": 0}
    assert body["creates"][1]["path"] == "Doğrusal Modeller / Regularizasyon"

    # Onizleme hicbir sey yazmadi: alan da konu da olusmadi.
    assert (await client.get("/api/study/areas")).json() == []
    async with SessionLocal() as session:
        count = (
            await session.execute(text("select count(*) from study_topic"))
        ).scalar_one()
    assert count == 0


async def test_preview_marks_updates_and_matches(client: AsyncClient) -> None:
    applied = (await client.post("/api/study/import", json=TREE)).json()
    preview = (
        await client.post(
            "/api/study/import/preview",
            json={
                "area_id": applied["area_id"],
                "topics": [
                    # Ayni konu, durum/konum farkli -> update.
                    {"title": "Doğrusal Modeller", "status": "done", "target_min": 90},
                    # Ayni konu, hicbir sey degismedi -> match.
                    {"title": "Ağaç Tabanlı Modeller"},
                ],
            },
        )
    ).json()
    assert [node["title"] for node in preview["updates"]] == ["Doğrusal Modeller"]
    assert preview["updates"][0]["changes"] == ["status", "target_min"]
    assert [node["title"] for node in preview["matches"]] == ["Ağaç Tabanlı Modeller"]
    assert preview["creates"] == []
    assert preview["totals"]["updates"] == 1
    assert preview["area"]["exists"] is True

    # update_existing=false iken hicbir guncelleme onerilmez.
    frozen = (
        await client.post(
            "/api/study/import/preview",
            json={
                "area_id": applied["area_id"],
                "topics": [{"title": "Doğrusal Modeller", "status": "done", "target_min": 90}],
                "update_existing": False,
            },
        )
    ).json()
    assert frozen["updates"] == []
    assert frozen["matches"][0]["title"] == "Doğrusal Modeller"


async def test_preview_reports_conflicts_for_duplicate_titles(client: AsyncClient) -> None:
    preview = (
        await client.post(
            "/api/study/import/preview",
            json={"area": "Çakışma", "topics": [{"title": "A"}, {"title": " a "}]},
        )
    ).json()
    assert preview["conflicts"] == [
        {"path": "a", "reason": "ayni ebeveyn altinda yinelenen konu basligi"}
    ]


# ── Uygulama (update / dedupe / prune) ──────────────────────────────────


async def test_import_updates_matched_topics_and_resources(client: AsyncClient) -> None:
    first = (await client.post("/api/study/import", json=TREE)).json()
    assert first["topics_created"] == 3
    assert first["resources_created"] == 3

    grown = {
        "area_id": first["area_id"],
        "topics": [
            {
                "title": "  doğrusal   modeller ",
                "status": "done",
                "target_min": 120,
                "resources": [
                    # Ayni URL (buyuk harf + izleme parametresi + fragment farki) -> eslesir.
                    {
                        "title": "ISLR bölüm 3",
                        "url": "https://Example.com/islr3/?utm_source=x#bolum",
                        "kind": "article",
                        "note": "yeni not",
                        "estimated_min": 45,
                    },
                    {"title": "Yeni makale", "url": "https://example.com/yeni"},
                ],
            }
        ],
    }
    result = (await client.post("/api/study/import", json=grown)).json()
    assert result["topics_matched"] == 1
    assert result["topics_updated"] == 1
    assert result["resources_skipped"] == 1
    assert result["resources_updated"] == 1
    assert result["resources_created"] == 1

    tree = (await client.get(f"/api/study/topics?area_id={first['area_id']}")).json()
    root = next(node for node in tree if node["title"] == "Doğrusal Modeller")
    assert root["status"] == "done"
    assert root["target_min"] == 120

    resources = (await client.get(f"/api/study/topics/{root['id']}/resources")).json()
    matched = next(row for row in resources if row["title"] == "ISLR bölüm 3")
    # Eşleşen kaynak güncellendi (izleme parametresi kanonik URL'de yok).
    assert matched["kind"] == "article"
    assert matched["note"] == "yeni not"
    assert matched["estimated_min"] == 45
    assert matched["url"] == "https://Example.com/islr3/?utm_source=x#bolum"

    # update_existing=false iken eslesen konu/kaynak DOKUNULMAZ.
    frozen = (
        await client.post(
            "/api/study/import",
            json={
                "area_id": first["area_id"],
                "topics": [
                    {
                        "title": "Doğrusal Modeller",
                        "status": "not_started",
                        "target_min": 5,
                        "resources": [{"title": "ISLR bölüm 3", "url": "https://example.com/islr3", "kind": "video"}],
                    }
                ],
                "update_existing": False,
            },
        )
    ).json()
    assert frozen["topics_updated"] == 0
    assert frozen["resources_updated"] == 0
    after = (
        await client.get(f"/api/study/topics/{root['id']}/resources")
    ).json()
    assert next(row for row in after if row["id"] == matched["id"])["kind"] == "article"


async def test_prune_archives_missing_nodes_instead_of_deleting(client: AsyncClient) -> None:
    first = (await client.post("/api/study/import", json=TREE)).json()
    pruned = (
        await client.post(
            "/api/study/import",
            json={
                "area_id": first["area_id"],
                "topics": [{"title": "Doğrusal Modeller"}],
                "prune": True,
            },
        )
    ).json()
    # "Ağaç Tabanlı Modeller" ve "Regularizasyon" arşivlenir; kaynaklari da.
    assert pruned["topics_archived"] == 2
    assert pruned["resources_archived"] == 3

    tree = (await client.get(f"/api/study/topics?area_id={first['area_id']}")).json()
    assert [node["title"] for node in tree] == ["Doğrusal Modeller"]

    # Kayitlar SILINMEDI: yalnizca arsivlendi.
    async with SessionLocal() as session:
        archived = (
            await session.execute(
                text(
                    "select count(*) from entity where type = 'study_topic'"
                    " and archived_at is not null"
                )
            )
        ).scalar_one()
    assert archived == 2

    # prune=false (varsayilan) hicbir seyi arsivlemez.
    plain = (
        await client.post(
            "/api/study/import",
            json={"area_id": first["area_id"], "topics": [{"title": "Yepyeni"}]},
        )
    ).json()
    assert plain["topics_archived"] == 0
    assert plain["resources_archived"] == 0


async def test_strip_common_prefix_is_suggested_and_applied(client: AsyncClient) -> None:
    payload = {
        "area": "ALES",
        "topics": [
            {"title": "ilk90_ales - Türev"},
            {"title": "ilk90_ales - Limit"},
            {"title": "ilk90_ales - Integral"},
        ],
    }
    preview = (await client.post("/api/study/import/preview", json=payload)).json()
    assert preview["suggested_prefix"] == "ilk90_ales - "
    assert [node["title"] for node in preview["creates"]] == [
        "ilk90_ales - Türev",
        "ilk90_ales - Limit",
        "ilk90_ales - Integral",
    ]

    stripped_preview = (
        await client.post(
            "/api/study/import/preview",
            json={**payload, "strip_common_prefix": True},
        )
    ).json()
    assert [node["title"] for node in stripped_preview["creates"]] == [
        "Türev",
        "Limit",
        "Integral",
    ]

    result = (
        await client.post("/api/study/import", json={**payload, "strip_common_prefix": True})
    ).json()
    tree = (await client.get(f"/api/study/topics?area_id={result['area_id']}")).json()
    assert [node["title"] for node in tree] == ["Türev", "Limit", "Integral"]


async def test_import_is_atomic_when_a_step_fails(client: AsyncClient, monkeypatch) -> None:
    original = learning_service.create_entity

    async def flaky(session, *, type, title, search_text=""):
        if title == "Patlat":
            raise RuntimeError("boom")
        return await original(session, type=type, title=title, search_text=search_text)

    monkeypatch.setattr(learning_service, "create_entity", flaky)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as raw:
        response = await raw.post(
            "/api/study/import",
            json={
                "area": "Atomik",
                "topics": [
                    {"title": "İlk", "resources": [{"title": "kaynak"}]},
                    {"title": "Patlat"},
                ],
            },
        )
    assert response.status_code == 500

    # Yarim veri yok: alan da konu da kaynak da yazilmadi.
    assert (await client.get("/api/study/areas")).json() == []
    async with SessionLocal() as session:
        for table in ("study_area", "study_topic", "learning_resource"):
            count = (
                await session.execute(text(f"select count(*) from {table}"))
            ).scalar_one()
            assert count == 0, f"{table} yarim kaldi"
