"""Faz 6: skor evreni, bayatlama ve veri kalitesi regresyonlari."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import SessionLocal
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


def _job(tag: str, *, url: str, title: str = "Backend Developer", cluster: str | None = None):
    from app.modules.opportunity.worker import NativeJob
    from app.sources.base import RawItem

    forkjob = {"cluster_key": cluster} if cluster else {}
    return NativeJob(
        RawItem(
            external_id=f"scoring-{tag}",
            title=title,
            url=url,
            summary="python backend",
            extra={
                "organization": "Acme",
                "location": "Remote",
                "remote": "remote",
                "kind": "job",
                "forkjob": forkjob,
            },
        )
    )


async def _cleanup(source: str) -> None:
    from sqlalchemy import select, text

    from app.db import engine
    from app.modules.opportunity.models import Opportunity

    async with SessionLocal() as session:
        ids = list(
            (await session.execute(select(Opportunity.id).where(Opportunity.source == source)))
            .scalars()
            .all()
        )
    if not ids:
        return
    async with engine.begin() as connection:
        await connection.execute(
            text("delete from entity where id = any(:ids)"), {"ids": [str(item) for item in ids]}
        )


# ---------------------------------------------------------------------------
# Skor evreni: hesaplanmadi / 0 / elendi ayrimi
# ---------------------------------------------------------------------------


@pytest.mark.no_database
def test_score_bands_have_no_gap_and_no_overlap():
    """Preset araliklari `{-1} ∪ [0,100]` evrenini tam ve tek kez kaplar."""
    from app.modules.opportunity.scoring import SCORE_CAP, SCORE_FLOOR

    ranges = [(80, 100), (70, 79.99), (40, 69.99), (0, 39.99), (-1, -1)]
    # Domain: elenmis (-1) + 0..100 (iki ondalik).
    values = [SCORE_FLOOR, *[round(step / 100, 2) for step in range(0, SCORE_CAP * 100 + 1)]]
    for value in values:
        hits = [low <= value <= high for low, high in ranges]
        assert sum(hits) == 1, f"{value} tam olarak bir araliga girmeli (bulunan: {sum(hits)})"
    assert SCORE_FLOOR == -1


async def test_uncomputed_zero_and_eliminated_are_distinct(client: AsyncClient):
    """`null`, `0` ve `-1` AYRI sonuc kumeleri uretir."""
    from datetime import UTC, datetime

    from app.core.entity import create_entity
    from app.modules.opportunity.models import Opportunity

    source = f"scoring-{uuid.uuid4().hex[:8]}"
    marker = f"Skor ayrimi {uuid.uuid4().hex[:6]}"
    ids: dict[str, str] = {}
    async with SessionLocal() as session:
        for key, score in (("uncomputed", None), ("zero", 0.0), ("eliminated", -1.0)):
            entity = await create_entity(
                session, type="opportunity", title=f"{marker} {key}", search_text=""
            )
            session.add(
                Opportunity(
                    id=entity.id,
                    kind="job",
                    status="discovered",
                    found_at=datetime.now(UTC),
                    source=source,
                    score=score,
                )
            )
            ids[key] = str(entity.id)
        await session.commit()

    async def total(params: dict) -> tuple[int, set[str]]:
        page = (
            await client.get(
                "/api/opportunities/browse", params={"limit": 120, "search": marker, **params}
            )
        ).json()
        return page["total"], {row["id"] for row in page["items"]}

    try:
        uncomputed_total, uncomputed_ids = await total({"score_state": "uncomputed"})
        zero_total, zero_ids = await total({"min_score": 0, "max_score": 0})
        eliminated_total, eliminated_ids = await total({"min_score": -1, "max_score": -1})
        computed_total, _ = await total({"score_state": "computed"})

        assert uncomputed_total == 1 and ids["uncomputed"] in uncomputed_ids
        assert zero_total == 1 and ids["zero"] in zero_ids
        assert eliminated_total == 1 and ids["eliminated"] in eliminated_ids
        assert computed_total == 2, "0 ve -1 hesaplanmis sayilir; null sayilmaz"
    finally:
        await _cleanup(source)


# ---------------------------------------------------------------------------
# Arama ve dedupe
# ---------------------------------------------------------------------------


async def test_updated_listing_is_found_by_its_new_title(client: AsyncClient):
    """Kaynak basligi degisince Entity basligi/arama vektoru de tazelenir."""
    from app.db import SessionLocal
    from app.modules.opportunity import service

    source = f"retitle-{uuid.uuid4().hex[:8]}"
    url = f"https://example.invalid/retitle/{uuid.uuid4().hex[:8]}"
    try:
        async with SessionLocal() as session:
            await service.ingest_jobs(
                session, [_job("a", url=url, title="Junior Backend Developer")], source
            )
            await session.commit()
        async with SessionLocal() as session:
            await service.ingest_jobs(
                session, [_job("a", url=url, title="Senior Platform Engineer")], source
            )
            await session.commit()

        found = (await client.get("/api/search", params={"q": "Senior Platform Engineer"})).json()
        titles = [hit["title"] for hit in found]
        assert "Senior Platform Engineer" in titles
    finally:
        await _cleanup(source)


async def test_same_url_variants_and_cluster_collapse_in_one_batch(client: AsyncClient):
    """Ayni batch icinde URL varyanti/kume tekrarı ikinci kayit ACMAZ."""
    from sqlalchemy import func, select

    from app.db import SessionLocal
    from app.modules.opportunity import service
    from app.modules.opportunity.models import Opportunity

    source = f"dedupe-{uuid.uuid4().hex[:8]}"
    base = f"https://example.invalid/dedupe/{uuid.uuid4().hex[:8]}"
    try:
        async with SessionLocal() as session:
            await service.ingest_jobs(
                session,
                [
                    _job("1", url=base),
                    # Ayni ilan, normalize edilince ayni adres (trailing slash + utm).
                    _job("2", url=f"{base}/?utm_source=newsletter"),
                    # Farkli URL, ayni kume anahtari.
                    _job("3", url=f"{base}-mirror", cluster="cluster-1"),
                    _job("4", url=f"{base}-mirror-2", cluster="cluster-1"),
                ],
                source,
            )
            await session.commit()
            count = (
                await session.execute(
                    select(func.count()).select_from(Opportunity).where(Opportunity.source == source)
                )
            ).scalar_one()
        assert count == 2, "URL varyanti ve kume tekrari tek kayda inmeli"
    finally:
        await _cleanup(source)


# ---------------------------------------------------------------------------
# Değerlendirme bayatlaması
# ---------------------------------------------------------------------------


async def test_evaluation_is_stale_when_the_listing_changes(client: AsyncClient):
    from httpx import ASGITransport
    from httpx import AsyncClient as Http

    from app.db import SessionLocal
    from app.modules.opportunity import service

    source = f"stale-{uuid.uuid4().hex[:8]}"
    url = f"https://example.invalid/stale/{uuid.uuid4().hex[:8]}"
    try:
        async with SessionLocal() as session:
            await service.ingest_jobs(session, [_job("s", url=url)], source)
            await session.commit()

        async with Http(transport=ASGITransport(app=app), base_url="http://test") as http:
            listing = next(
                row
                for row in (
                    await http.get("/api/opportunities/browse", params={"limit": 120})
                ).json()["items"]
                if row["url"] == url
            )
            assert listing["evaluation_stale_reason"] is None  # degerlendirme yok

            evaluated = await http.post(f"/api/opportunities/{listing['id']}/evaluation", json={})
            assert evaluated.status_code == 200, evaluated.text

            fresh = (await http.get(f"/api/opportunities/{listing['id']}")).json()
            assert fresh["evaluation_stale_reason"] is None, "yeni degerlendirme guncel olmali"

            # Ilan metni degisti: kayitli degerlendirme artik bayat.
            assert (
                await http.patch(
                    f"/api/opportunities/{listing['id']}",
                    json={"notes": "guncellendi"},
                )
            ).status_code == 200
            patched = (await http.get(f"/api/opportunities/{listing['id']}")).json()
            assert patched["evaluation"] is not None
            assert patched["evaluation_stale_reason"] in {"listing", "profile", "version", "missing"}
    finally:
        await _cleanup(source)


async def test_profile_change_marks_evaluations_stale(client: AsyncClient):
    """Profil ayarı değişince kayıtlı değerlendirmeler bayatlar."""
    from app.modules.opportunity import service
    from app.modules.system.models import Setting

    source = f"profile-{uuid.uuid4().hex[:8]}"
    url = f"https://example.invalid/profile/{uuid.uuid4().hex[:8]}"
    try:
        async with SessionLocal() as session:
            await service.ingest_jobs(session, [_job("p", url=url)], source)
            await session.commit()
        listing = next(
            row
            for row in (
                await client.get("/api/opportunities/browse", params={"limit": 120})
            ).json()["items"]
            if row["url"] == url
        )
        assert (
            await client.post(f"/api/opportunities/{listing['id']}/evaluation", json={})
        ).status_code == 200
        before = (await client.get(f"/api/opportunities/{listing['id']}")).json()
        assert before["evaluation_stale_reason"] is None

        # Profil ayari dogrudan degistirilir (ucu yok): degerlendirme eski ayara gore.
        async with SessionLocal() as session:
            row = await session.get(Setting, "opportunity.career_profile")
            value = dict(row.value) if row is not None and isinstance(row.value, dict) else {}
            value["target_titles"] = ["Staff Platform Engineer"]
            if row is None:
                session.add(Setting(key="opportunity.career_profile", value=value))
            else:
                row.value = value
            await session.commit()

        after = (await client.get(f"/api/opportunities/{listing['id']}")).json()
        assert after["evaluation"] is not None, "degerlendirme silinmez, bayat isaretlenir"
        assert after["evaluation_stale_reason"] == "profile"
    finally:
        await _cleanup(source)


# ---------------------------------------------------------------------------
# Skorlama konfigürasyonu
# ---------------------------------------------------------------------------


async def test_invalid_scoring_config_is_rejected_without_breaking_the_running_one(
    client: AsyncClient,
):
    from app.sources import forkjob_port

    before = forkjob_port.SCORING
    current = (await client.get("/api/sources/jobhunter/config")).json()

    invalid = {
        "scoring": {**current["scoring"], "kill_score": 9999},
        "balance": current["balance"],
    }
    rejected = await client.put("/api/sources/jobhunter/config", json=invalid)
    assert rejected.status_code == 422
    # Calisan ayar bozulmadi: dogrulama YAZMADAN once yapilir.
    assert forkjob_port.SCORING is before
    assert (await client.get("/api/sources/jobhunter/config")).json() == current

    broken_skill = {
        "scoring": {**current["scoring"], "skills": [{"name": "", "points": 3}]},
        "balance": current["balance"],
    }
    assert (await client.put("/api/sources/jobhunter/config", json=broken_skill)).status_code == 422
    assert forkjob_port.SCORING is before

    negative_quota = {
        "scoring": current["scoring"],
        "balance": {**current["balance"], "quotas": {"TR": -1}},
    }
    assert (await client.put("/api/sources/jobhunter/config", json=negative_quota)).status_code == 422
    assert forkjob_port.SCORING is before
