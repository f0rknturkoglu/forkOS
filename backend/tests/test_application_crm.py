"""Application CRM uctan uca testleri — Postgres gerektirir (lifeos_test)."""

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


async def _seed_opportunity() -> uuid.UUID:
    item_id = uuid.uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "insert into entity (id, type, title, search_text) values "
                "(:id, 'opportunity', :title, '')"
            ),
            {"id": item_id, "title": "CRM Test"},
        )
        await connection.execute(
            text(
                "insert into opportunity (id, kind, status, found_at, source) values "
                "(:id, 'job', 'discovered', now(), 'test')"
            ),
            {"id": item_id},
        )
    return item_id


async def _delete_entities(*entity_ids: uuid.UUID) -> None:
    async with engine.begin() as connection:
        for entity_id in entity_ids:
            await connection.execute(text("delete from entity where id = :id"), {"id": entity_id})


@pytest.fixture
async def client():
    if not await _database_ready():
        pytest.skip("Postgres yok veya migration calismamis")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def test_apply_snapshot_and_history(client: AsyncClient):
    item_id = await _seed_opportunity()
    try:
        response = await client.post(
            f"/api/opportunities/{item_id}/apply", json={"cover_letter": "merhaba"}
        )
        assert response.status_code == 200, response.text
        # Kesif durumu kisayokta alinir; basvuru hatti application.status'tadir.
        assert response.json()["status"] == "shortlisted"
        assert response.json()["application_status"] == "applied"
        history = (await client.get(f"/api/opportunities/{item_id}/history")).json()
        assert any(
            h["scope"] == "discovery"
            and h["from_status"] == "discovered"
            and h["to_status"] == "shortlisted"
            for h in history
        )
        assert any(
            h["scope"] == "application" and h["to_status"] == "applied" for h in history
        )
        application = (await client.get(f"/api/opportunities/{item_id}/application")).json()
        assert application["cover_letter"] == "merhaba"
        assert application["status"] == "applied"
    finally:
        await _delete_entities(item_id)


async def test_application_transitions_and_terminal_lock(client: AsyncClient):
    item_id = await _seed_opportunity()
    try:
        bad = await client.post(f"/api/applications/{item_id}/transition", json={"to": "offer"})
        assert bad.status_code == 404  # basvuru kaydi yok

        applied = await client.post(f"/api/opportunities/{item_id}/apply", json={})
        assert applied.status_code == 200, applied.text

        invalid = await client.post(
            f"/api/applications/{item_id}/transition", json={"to": "accepted"}
        )
        assert invalid.status_code == 409  # applied -> accepted gecersiz

        interview = await client.post(
            f"/api/applications/{item_id}/transition", json={"to": "interview"}
        )
        assert interview.status_code == 200
        offer = await client.post(f"/api/applications/{item_id}/transition", json={"to": "offer"})
        assert offer.status_code == 200
        accepted = await client.post(
            f"/api/applications/{item_id}/transition", json={"to": "accepted"}
        )
        assert accepted.status_code == 200
        locked = await client.post(
            f"/api/applications/{item_id}/transition", json={"to": "interview"}
        )
        assert locked.status_code == 409

        # Kural 3: her gecis opportunity.status_changed event'i yazar (append-only).
        events = (await client.get("/api/activity", params={"limit": 200})).json()
        status_events = sorted(
            (
                e
                for e in events
                if e["verb"] == "opportunity.status_changed"
                and e["entity_id"] == str(item_id)
                and e["payload"].get("scope") == "application"
            ),
            key=lambda e: e["id"],
        )
        assert [(e["payload"].get("from"), e["payload"].get("to")) for e in status_events] == [
            (None, "applied"),
            ("applied", "interview"),
            ("interview", "offer"),
            ("offer", "accepted"),
        ]
    finally:
        await _delete_entities(item_id)


async def test_rejection_reason_and_funnel(client: AsyncClient):
    item_id = await _seed_opportunity()
    try:
        await client.post(f"/api/opportunities/{item_id}/apply", json={})
        rejected = await client.post(
            f"/api/applications/{item_id}/transition",
            json={"to": "rejected", "rejection_reason": "maas uyumsuz"},
        )
        assert rejected.status_code == 200
        funnel = (await client.get("/api/applications/funnel")).json()
        assert any(r["reason"] == "maas uyumsuz" for r in funnel["rejection_reasons"])
        assert funnel["total"] >= 1
        detail = (await client.get(f"/api/opportunities/{item_id}")).json()
        assert detail["rejection_reason"] == "maas uyumsuz"
        assert detail["application_status"] == "rejected"
    finally:
        await _delete_entities(item_id)


async def test_followups_listing(client: AsyncClient):
    item_id = await _seed_opportunity()
    try:
        await client.post(f"/api/opportunities/{item_id}/apply", json={})
        future = datetime.now(UTC) + timedelta(days=5)
        update = await client.patch(
            f"/api/opportunities/{item_id}",
            json={"follow_up_at": future.isoformat()},
        )
        assert update.status_code == 200
        followups = (await client.get("/api/opportunities/followups")).json()
        assert any(f["id"] == str(item_id) for f in followups)
    finally:
        await _delete_entities(item_id)


async def test_interview_crud(client: AsyncClient):
    item_id = await _seed_opportunity()
    try:
        created = await client.post(
            f"/api/opportunities/{item_id}/interviews",
            json={"stage": "teknik", "mode": "video"},
        )
        assert created.status_code == 201, created.text
        interview_id = created.json()["id"]
        listed = (await client.get(f"/api/opportunities/{item_id}/interviews")).json()
        assert len(listed) == 1 and listed[0]["stage"] == "teknik"
        assert (await client.delete(f"/api/interviews/{interview_id}")).status_code == 204
    finally:
        await _delete_entities(item_id)


async def test_reply_analysis_is_local_and_suggests_a_confirmable_action(client: AsyncClient):
    item_id = await _seed_opportunity()
    try:
        response = await client.post(
            f"/api/opportunities/{item_id}/reply-analysis",
            json={
                "text": "We would like to invite you to an interview. Please share your availability."
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["kind"] == "interview_invite"
        assert body["suggested_status"] == "interview"
        # Analiz tek basina durumu degistirmez; HITL onayi frontend'den gelir.
        detail = (await client.get(f"/api/opportunities/{item_id}")).json()
        assert detail["status"] == "discovered"
    finally:
        await _delete_entities(item_id)


async def test_interview_silence_radar(client: AsyncClient):
    item_id = await _seed_opportunity()
    try:
        await client.post(f"/api/opportunities/{item_id}/apply", json={})
        await client.post(f"/api/applications/{item_id}/transition", json={"to": "interview"})
        scheduled_at = datetime.now(UTC) - timedelta(days=25)
        created = await client.post(
            f"/api/opportunities/{item_id}/interviews",
            json={"stage": "teknik", "mode": "video", "scheduled_at": scheduled_at.isoformat()},
        )
        assert created.status_code == 201, created.text

        silent = (await client.get("/api/opportunities/silence", params={"days": 21})).json()
        row = next(item for item in silent if item["id"] == str(item_id))
        assert row["days_silent"] >= 24
    finally:
        await _delete_entities(item_id)


async def test_detail_includes_repost_intelligence(client: AsyncClient):
    first_id = await _seed_opportunity()
    second_id = await _seed_opportunity()
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "update opportunity set organization = 'Acme', url = :url, found_at = :found_at "
                    "where id = :id"
                ),
                {
                    "id": first_id,
                    "url": "https://jobs.example/one",
                    "found_at": datetime.now(UTC) - timedelta(days=8),
                },
            )
            await connection.execute(
                text(
                    "update opportunity set organization = 'Acme', url = :url, found_at = :found_at "
                    "where id = :id"
                ),
                {
                    "id": second_id,
                    "url": "https://jobs.example/two",
                    "found_at": datetime.now(UTC),
                },
            )
        detail = (await client.get(f"/api/opportunities/{second_id}")).json()
        assert detail["intelligence"]["is_repost"] is True
        assert detail["intelligence"]["repost_count"] == 2
    finally:
        await _delete_entities(first_id, second_id)


async def test_two_pass_evaluation_persists_and_is_user_editable(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
):
    from app.modules.document import service as document_service

    monkeypatch.setattr(document_service, "DOCUMENTS_DIR", tmp_path / "documents")
    item_id = await _seed_opportunity()
    document_id = None
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "update opportunity set country = 'Germany', location = 'Berlin, Germany', "
                    "remote = 'remote', raw = cast(:raw as jsonb) where id = :id"
                ),
                {
                    "id": item_id,
                    "raw": (
                        '{"description":"C# and .NET are required. Strong experience with '
                        "Kubernetes is required. Candidates must be authorized to work without "
                        'sponsorship. Build agentic multi-agent systems."}'
                    ),
                },
            )

        uploaded = await client.post(
            "/api/documents/upload",
            files={
                "file": (
                    "career-ops-cv.txt",
                    b"Built Kubernetes platforms and Terraform modules for production systems.",
                    "text/plain",
                )
            },
            data={"category": "cv"},
        )
        assert uploaded.status_code == 200, uploaded.text
        document_id = uuid.UUID(uploaded.json()["id"])
        linked = await client.put(
            f"/api/opportunities/{item_id}/application",
            json={"cv_document_id": str(document_id)},
        )
        assert linked.status_code == 200, linked.text

        generated = await client.post(f"/api/opportunities/{item_id}/evaluation")
        assert generated.status_code == 200, generated.text
        body = generated.json()
        assert body["version"] == "career-ops-v1"
        assert body["candidate_source"] == "document"
        assert body["candidate_document_id"] == str(document_id)
        assert body["candidate_document_title"] == "career-ops-cv.txt"
        assert body["gate"]["hard_blocker"] is True
        assert body["recommendation"] == "skip"
        assert any(item["name"] == "C#" for item in body["requirements"])
        kubernetes = next(item for item in body["matches"] if item["requirement"] == "Kubernetes")
        assert kubernetes["match"] == "strong"
        assert "career-ops-cv.txt" in kubernetes["evidence"]
        assert all(
            item["importance"] not in {"critical", "high"}
            for item in body["requirements"]
            if item["evidence"] == "inferred"
        )

        saved = await client.put(
            f"/api/opportunities/{item_id}/evaluation",
            json={"notes": "Bu ilan için referans bulmadan ilerleme."},
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["notes"] == "Bu ilan için referans bulmadan ilerleme."

        detail = (await client.get(f"/api/opportunities/{item_id}")).json()
        assert detail["evaluation"]["notes"] == "Bu ilan için referans bulmadan ilerleme."
        events = (await client.get("/api/activity", params={"limit": 200})).json()
        verbs = {event["verb"] for event in events if event["entity_id"] == str(item_id)}
        assert {"opportunity.evaluated", "opportunity.evaluation_updated"} <= verbs
    finally:
        await _delete_entities(item_id, *([document_id] if document_id else []))


async def test_career_story_salary_claims_and_cover_letter_voice_review(client: AsyncClient):
    item_id = await _seed_opportunity()
    story_id = None
    try:
        created = await client.post(
            "/api/career/stories",
            json={
                "title": "Dağıtım süresini kısaltma",
                "situation": "Üretim dağıtımları elle ve hataya açıktı.",
                "task": "Dağıtımı güvenilir hale getirmek.",
                "action": "Kubernetes dağıtım hattını ve otomatik kontrolleri kurdum.",
                "result": "Dağıtım süresi 45 dakikadan 12 dakikaya indi.",
                "reflection": "Küçük geri alma adımları riski azalttı.",
                "provenance": "supported",
                "tags": ["kubernetes", "delivery"],
            },
        )
        assert created.status_code == 201, created.text
        story_id = uuid.UUID(created.json()["id"])
        assert created.json()["provenance"] == "supported"

        patched = await client.patch(
            f"/api/career/stories/{story_id}",
            json={"provenance": "existing"},
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["provenance"] == "existing"

        evaluated = await client.post(f"/api/opportunities/{item_id}/evaluation")
        assert evaluated.status_code == 200, evaluated.text
        matches = evaluated.json()["matches"]
        matches[0]["story_ids"] = [str(story_id)]
        mapped = await client.put(
            f"/api/opportunities/{item_id}/evaluation",
            json={"matches": matches},
        )
        assert mapped.status_code == 200, mapped.text
        assert mapped.json()["matches"][0]["story_ids"] == [str(story_id)]
        refreshed = await client.post(f"/api/opportunities/{item_id}/evaluation")
        assert refreshed.status_code == 200, refreshed.text
        assert refreshed.json()["matches"][0]["story_ids"] == [str(story_id)]

        first = await client.post(
            f"/api/opportunities/{item_id}/interviews",
            json={"stage": "HR", "salary_stated": "€60k - €70k"},
        )
        second = await client.post(
            f"/api/opportunities/{item_id}/interviews",
            json={"stage": "Hiring Manager", "salary_stated": "€80k - €90k"},
        )
        assert first.status_code == 201, first.text
        assert second.status_code == 201, second.text
        salary = await client.get(f"/api/opportunities/{item_id}/salary-consistency")
        assert salary.status_code == 200, salary.text
        assert salary.json()["inconsistent"] is True
        assert len(salary.json()["claims"]) == 2

        # Test application salary expectation is included in consistency checks
        put_app = await client.put(
            f"/api/opportunities/{item_id}/application",
            json={"salary_expectation": "€100k"},
        )
        assert put_app.status_code == 200, put_app.text
        salary_with_app = await client.get(f"/api/opportunities/{item_id}/salary-consistency")
        assert salary_with_app.status_code == 200
        assert len(salary_with_app.json()["claims"]) == 3
        assert any(c["stage"] == "Başvuru beklentisi" for c in salary_with_app.json()["claims"])

        review = await client.post(
            "/api/career/cover-letter-review",
            json={
                "text": (
                    "I am excited to apply. I built a Kubernetes deployment pipeline and "
                    "automated production controls. I reduced deployment time from 45 minutes "
                    "to 12 minutes."
                )
            },
        )
        assert review.status_code == 200, review.text
        assert str(story_id) in review.json()["matched_story_ids"]
        assert "i am excited to apply" in review.json()["generic_phrases"]

        stories = await client.get("/api/career/stories")
        assert any(item["id"] == str(story_id) for item in stories.json())
        archived = await client.delete(f"/api/career/stories/{story_id}")
        assert archived.status_code == 204, archived.text
        assert all(
            item["id"] != str(story_id) for item in (await client.get("/api/career/stories")).json()
        )
    finally:
        await _delete_entities(item_id, *([story_id] if story_id else []))


async def test_linkedin_connections_import_and_local_company_join(client: AsyncClient):
    item_id = await _seed_opportunity()
    connection_ids: list[uuid.UUID] = []
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("update opportunity set organization = 'Acme Energy Ltd' where id = :id"),
                {"id": item_id},
            )

        csv_body = (
            b"Notes:\nLinkedIn export\n\n"
            b"First Name,Last Name,URL,Email Address,Company,Position,Connected On\n"
            b"Ada,Lovelace,https://linkedin.com/in/ada,ada@example.com,Acme Energy GmbH,"
            b"Staff Engineer,04 Sep 2026\n"
            b"Grace,Hopper,https://linkedin.com/in/grace,grace@example.com,Other Corp,"
            b"Engineering Manager,03 Sep 2026\n"
        )
        imported = await client.post(
            "/api/career/connections/import",
            files={"file": ("Connections.csv", csv_body, "text/csv")},
        )
        assert imported.status_code == 200, imported.text
        assert imported.json() == {"total_rows": 2, "created": 2, "updated": 0, "skipped": 0}

        listed = (await client.get("/api/career/connections")).json()
        connection_ids = [uuid.UUID(item["id"]) for item in listed]
        assert {item["name"] for item in listed} >= {"Ada Lovelace", "Grace Hopper"}

        matched = await client.get(f"/api/opportunities/{item_id}/connections")
        assert matched.status_code == 200, matched.text
        assert matched.json()["normalized_organization"] == "acme energy"
        assert [item["name"] for item in matched.json()["connections"]] == ["Ada Lovelace"]
        assert matched.json()["connections"][0]["position"] == "Staff Engineer"

        detail = (await client.get(f"/api/opportunities/{item_id}")).json()
        assert detail["intelligence"]["connection_count"] == 1
        assert any(s["code"] == "connection" for s in detail["intelligence"]["signals"])

        repeated = await client.post(
            "/api/career/connections/import",
            files={"file": ("Connections.csv", csv_body, "text/csv")},
        )
        assert repeated.status_code == 200, repeated.text
        assert repeated.json()["created"] == 0
        assert repeated.json()["skipped"] == 2

        events = (await client.get("/api/activity", params={"limit": 200})).json()
        assert any(event["verb"] == "career_connections.imported" for event in events)
    finally:
        await _delete_entities(item_id, *connection_ids)
