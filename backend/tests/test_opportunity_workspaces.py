"""Fırsat çalışma alanları: durum makineleri, tür sınırları, CRM, prune, takvim.

Bu dosya Faz 1–4'ün sözleşmesini korur:
  * keşif / başvuru / duyuru yaşam döngüleri birbirine karışmaz
  * duyurular iş ilanı uçlarını kullanamaz
  * CRM yalnızca gerçek başvuruları sayar
  * prune kullanıcı verisine dokunmaz
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import engine
from app.main import app


async def _database_ready() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("select 1 from application limit 1"))
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


async def _seed(*, kind: str = "job", status: str = "discovered", found_days_ago: int = 0) -> uuid.UUID:
    item_id = uuid.uuid4()
    title = f"Workspace {kind} {item_id.hex[:6]}"
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
                "insert into opportunity (id, kind, status, found_at, published_at, source, "
                "organization) values (:id, :kind, :status, :found_at, :found_at, 'test', 'Acme')"
            ),
            {
                "id": item_id,
                "kind": kind,
                "status": status,
                "found_at": datetime.now(UTC) - timedelta(days=found_days_ago),
            },
        )
    return item_id


async def _delete_entities(*entity_ids: uuid.UUID) -> None:
    async with engine.begin() as connection:
        for entity_id in entity_ids:
            await connection.execute(text("delete from entity where id = :id"), {"id": entity_id})


async def test_lifecycle_endpoint_exposes_all_three_machines(client: AsyncClient):
    response = await client.get("/api/opportunities/lifecycle")
    assert response.status_code == 200
    body = response.json()
    assert body["job_discovery"]["flow"] == [
        "discovered",
        "shortlisted",
        "dismissed",
        "archived",
        "closed",
    ]
    assert "interview" not in body["announcement"]["flow"]
    assert "offer" not in body["announcement"]["flow"]
    assert body["application"]["flow"][:3] == ["preparing", "applied", "interview"]
    assert body["application"]["terminal"] == ["accepted", "closed", "rejected"]
    # İzinli geçişler yalnızca mevcut durumdan gösterilir.
    assert body["application"]["transitions"]["accepted"] == []


async def test_job_discovery_transitions_are_validated(client: AsyncClient):
    item_id = await _seed(status="discovered")
    try:
        invalid = await client.post(
            f"/api/opportunities/{item_id}/transition", json={"to": "closed"}
        )
        assert invalid.status_code == 409

        ok = await client.post(
            f"/api/opportunities/{item_id}/transition", json={"to": "shortlisted"}
        )
        assert ok.status_code == 200
        assert ok.json()["status"] == "shortlisted"
        assert ok.json()["allowed_transitions"] == ["archived", "discovered", "dismissed"]

        same = await client.post(
            f"/api/opportunities/{item_id}/transition", json={"to": "shortlisted"}
        )
        assert same.status_code == 409
    finally:
        await _delete_entities(item_id)


async def test_announcement_cannot_use_job_statuses(client: AsyncClient):
    item_id = await _seed(kind="scholarship", status="new")
    try:
        for status in ("interview", "offer", "applied"):
            response = await client.post(
                f"/api/opportunities/{item_id}/transition", json={"to": status}
            )
            if status == "applied":
                # Duyuruda "başvuru yapıldı" anlamlıdır ve izinlidir.
                continue
            assert response.status_code == 409, f"{status} duyuruda kabul edildi"

        watching = await client.post(
            f"/api/opportunities/{item_id}/transition", json={"to": "watching"}
        )
        assert watching.status_code == 200
        assert watching.json()["status"] == "watching"
    finally:
        await _delete_entities(item_id)


async def test_job_only_endpoints_reject_announcements(client: AsyncClient):
    item_id = await _seed(kind="exam", status="new")
    try:
        assert (
            await client.post(f"/api/opportunities/{item_id}/apply", json={})
        ).status_code == 409
        assert (
            await client.post(
                f"/api/opportunities/{item_id}/interviews", json={"stage": "teknik"}
            )
        ).status_code == 409
        assert (
            await client.get(f"/api/opportunities/{item_id}/interviews")
        ).status_code == 409
        assert (
            await client.post(f"/api/opportunities/{item_id}/evaluation")
        ).status_code == 409
        assert (
            await client.post(
                f"/api/opportunities/{item_id}/requirements", json={"name": "Kılavuz"}
            )
        ).status_code == 201
        assert (
            await client.get(f"/api/opportunities/{item_id}/connections")
        ).status_code == 409
        assert (
            await client.get(f"/api/opportunities/{item_id}/salary-consistency")
        ).status_code == 409
        assert (
            await client.post(
                f"/api/opportunities/{item_id}/reply-analysis", json={"text": "x" * 10}
            )
        ).status_code == 409
    finally:
        await _delete_entities(item_id)


async def test_apply_rejects_announcements_at_service_level(client: AsyncClient):
    item_id = await _seed(kind="msc", status="new")
    try:
        response = await client.post(f"/api/opportunities/{item_id}/apply", json={})
        assert response.status_code == 409
        assert "iş ilanları" in response.json()["detail"]
    finally:
        await _delete_entities(item_id)


async def test_crm_counts_only_real_applications(client: AsyncClient):
    """19 bin keşfedilmiş ilan CRM hunsine girmez."""
    discovered = [await _seed(status="discovered") for _ in range(5)]
    shortlisted = await _seed(status="shortlisted")
    applied = await _seed(status="discovered")
    try:
        before = (await client.get("/api/applications/funnel")).json()
        await client.post(f"/api/opportunities/{applied}/apply", json={})

        after = (await client.get("/api/applications/funnel")).json()
        assert after["total"] == before["total"] + 1
        assert after["tracked"] >= 1
        by_status = {row["status"]: row["count"] for row in after["by_status"]}
        assert by_status.get("applied", 0) >= 1
        # Keşif durumları funnel'da hiç görünmez.
        assert "discovered" not in by_status
        assert "shortlisted" not in by_status
    finally:
        await _delete_entities(*discovered, shortlisted, applied)


async def test_funnel_conversions_use_null_for_zero_denominators(client: AsyncClient):
    funnel = (await client.get("/api/applications/funnel")).json()
    assert funnel["avg_first_response_days"] is None or isinstance(
        funnel["avg_first_response_days"], float
    )
    for row in funnel["by_source"]:
        if row["total"] == 0:
            assert row["response_rate"] is None


async def test_application_timeline_is_deterministic(client: AsyncClient):
    item_id = await _seed()
    try:
        await client.post(f"/api/opportunities/{item_id}/apply", json={"cover_letter": "hi"})
        await client.post(f"/api/applications/{item_id}/transition", json={"to": "interview"})
        scheduled = datetime.now(UTC) + timedelta(days=3)
        await client.post(
            f"/api/opportunities/{item_id}/interviews",
            json={"stage": "teknik", "scheduled_at": scheduled.isoformat()},
        )

        first = (await client.get(f"/api/opportunities/{item_id}/timeline")).json()
        second = (await client.get(f"/api/opportunities/{item_id}/timeline")).json()
        assert first == second
        kinds = [entry["kind"] for entry in first["entries"]]
        # Keşif kaydı her zaman temsil edilir; tam sıra eşzamanlı damgalara
        # bağlı olduğu için "ilk eleman" iddiası kırılgandır.
        assert "discovered" in kinds
        assert "status" in kinds
        assert "interview" in kinds
        # Kronolojik sıra korunur.
        timestamps = [entry["at"] for entry in first["entries"]]
        assert timestamps == sorted(timestamps)
    finally:
        await _delete_entities(item_id)


async def test_prune_requires_preview_token_and_protects_user_data(client: AsyncClient):
    untouched = await _seed(status="discovered", found_days_ago=400)
    has_note = await _seed(status="discovered", found_days_ago=400)
    applied = await _seed(status="discovered", found_days_ago=400)
    manual = await _seed(status="discovered", found_days_ago=400)
    try:
        async with engine.begin() as connection:
            note_id = uuid.uuid4()
            await connection.execute(
                text(
                    "insert into entity (id, type, title, search_text) values "
                    "(:id, 'note', 'Not', '')"
                ),
                {"id": note_id},
            )
            await connection.execute(
                text("insert into note (id, body) values (:id, 'not')"), {"id": note_id}
            )
            await connection.execute(
                text(
                    "insert into link (from_id, to_id, relation) "
                    "values (:note, :opp, 'notes_about')"
                ),
                {"note": note_id, "opp": has_note},
            )
            await connection.execute(
                text("update opportunity set source = 'manual' where id = :id"),
                {"id": manual},
            )
        await client.post(f"/api/opportunities/{applied}/apply", json={})

        preview = await client.get("/api/opportunities/prune/preview", params={"days": 90})
        assert preview.status_code == 200
        body = preview.json()
        assert body["candidates"] >= 1
        assert body["protected"] >= 1
        token = body["confirm_token"]

        # Yanlış token kabul edilmez.
        wrong = await client.post(
            "/api/opportunities/prune",
            params={"days": 90, "confirm_token": "deadbeefdeadbeef"},
        )
        assert wrong.status_code == 409

        result = await client.post(
            "/api/opportunities/prune",
            params={"days": 90, "confirm_token": token},
        )
        assert result.status_code == 200, result.text
        assert result.json()["pruned"] >= 1

        # Kullanıcı verisi taşıyan kayıtlar hâlâ yerinde.
        for survivor in (has_note, applied, manual):
            assert (await client.get(f"/api/opportunities/{survivor}")).status_code == 200
        assert (await client.get(f"/api/opportunities/{untouched}")).status_code == 404

        events = (await client.get("/api/activity", params={"limit": 200})).json()
        assert any(event["verb"] == "opportunity.pruned" for event in events)
    finally:
        await _delete_entities(untouched, has_note, applied, manual)


async def test_interview_deadline_points_at_parent_opportunity(client: AsyncClient):
    item_id = await _seed()
    try:
        await client.post(f"/api/opportunities/{item_id}/apply", json={})
        await client.post(f"/api/applications/{item_id}/transition", json={"to": "interview"})
        scheduled = datetime.now(UTC) + timedelta(days=2)
        await client.post(
            f"/api/opportunities/{item_id}/interviews",
            json={"stage": "teknik", "scheduled_at": scheduled.isoformat()},
        )
        deadlines = (await client.get("/api/deadlines")).json()
        interview_rows = [
            row
            for row in deadlines
            if row["entity_id"] == str(item_id) and row["sub_kind"] == "interview"
        ]
        assert interview_rows, "görüşme deadline satırı düşmüş"
        assert "Görüşme" in interview_rows[0]["title"]
        assert interview_rows[0]["priority"] == 1
    finally:
        await _delete_entities(item_id)


async def test_prune_token_is_bound_to_the_exact_candidate_set(client: AsyncClient):
    """Onay ile silme arasında aday kümesi değişirse silme REDDEDİLİR (TOCTOU)."""
    from datetime import UTC, datetime, timedelta
    from typing import Any

    from sqlalchemy import text

    from app.db import engine

    async def seed(title: str, *, age_days: int) -> str:
        item_id = uuid.uuid4()
        found = datetime.now(UTC) - timedelta(days=age_days)
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
                    "insert into opportunity (id, kind, status, found_at, source) "
                    "values (:id, 'job', 'discovered', :found, 'sweep-test')"
                ),
                {"id": item_id, "found": found},
            )
        return str(item_id)

    leftovers: list[str] = []
    try:
        old_id = await seed(f"Eski aday {uuid.uuid4().hex[:6]}", age_days=400)
        leftovers.append(old_id)
        preview = await client.get("/api/opportunities/prune/preview", params={"days": 90})
        assert preview.status_code == 200
        body: dict[str, Any] = preview.json()
        token = body["confirm_token"]
        assert body["candidate_digest"], "token aday kümesinin özetini taşımalı"

        # Onaydan SONRA kümeye yeni bir aday giriyor: token artık geçersiz.
        new_id = await seed(f"Yeni aday {uuid.uuid4().hex[:6]}", age_days=400)
        leftovers.append(new_id)

        stale = await client.post(
            "/api/opportunities/prune", params={"days": 90, "confirm_token": token}
        )
        assert stale.status_code == 409, stale.text
        # Hiçbir aday silinmedi: kullanıcı görmediği kümeyi silmiş olmamalı.
        assert (await client.get(f"/api/opportunities/{old_id}")).status_code == 200
        assert (await client.get(f"/api/opportunities/{new_id}")).status_code == 200

        # Yeniden önizleme + yeni token ile silme çalışır.
        again = (await client.get("/api/opportunities/prune/preview", params={"days": 90})).json()
        assert again["candidate_digest"] != body["candidate_digest"]
        ok = await client.post(
            "/api/opportunities/prune",
            params={"days": 90, "confirm_token": again["confirm_token"]},
        )
        assert ok.status_code == 200, ok.text
        assert ok.json()["pruned"] >= 2
    finally:
        async with engine.begin() as connection:
            for item_id in leftovers:
                await connection.execute(
                    text("delete from entity where id = :id"), {"id": item_id}
                )
