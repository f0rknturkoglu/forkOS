import httpx
import pytest
from sqlalchemy import select

from app.core.models import Event, SourceRun
from app.db import SessionLocal
from app.modules.system.news import fetch_news_source
from app.sources.news import HuggingFacePapersSource, clear_news_cache

PAPER = [
    {
        "publishedAt": "2026-01-01T00:00:00Z",
        "paper": {
            "id": "2610.11216",
            "title": "Actual paper",
            "summary": "Original abstract",
            "authors": [{"name": "Author One"}],
            "publishedAt": "2026-10-08T00:00:00Z",
            "submittedOnDailyAt": "2026-10-09",
            "upvotes": 12,
        },
        "numComments": 3,
    }
]


@pytest.mark.no_database
async def test_latest_and_historical_contract_uses_actual_paper_dates():
    requests = []

    def upstream(request):
        requests.append(request)
        return httpx.Response(200, json=PAPER)

    for date in [None, "2026-10-09"]:
        source = HuggingFacePapersSource(date=date, transport=httpx.MockTransport(upstream))
        items = await source.fetch()
        assert items[0].extra["featured_at"] == "2026-10-09"
        assert items[0].extra["published_at"] == "2026-10-08T00:00:00Z"
        assert items[0].extra["summary"] == "Original abstract"
        assert items[0].extra["authors"] == ["Author One"]
        assert items[0].url == "https://huggingface.co/papers/2610.11216"
        assert items[0].extra["arxiv_url"] == "https://arxiv.org/abs/2610.11216"
    assert "date" not in requests[0].url.params and requests[1].url.params["date"] == "2026-10-09"


async def test_health_success_empty_streak_and_error_are_recorded():
    clear_news_cache()
    async with SessionLocal() as db:
        good = HuggingFacePapersSource(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, json=PAPER))
        )
        assert len(await fetch_news_source(db, good, 20)) == 1
        empty = HuggingFacePapersSource(
            date="2026-01-01", transport=httpx.MockTransport(lambda r: httpx.Response(200, json=[]))
        )
        for _ in range(3):
            clear_news_cache()
            assert await fetch_news_source(db, empty, 20) == []
        failed = HuggingFacePapersSource(
            date="2026-01-02",
            transport=httpx.MockTransport(
                lambda r: httpx.Response(429, headers={"Retry-After": "60"})
            ),
        )
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_news_source(db, failed, 20)
        runs = list(await db.scalars(select(SourceRun).order_by(SourceRun.id)))
        assert [r.status for r in runs] == ["ok", "empty", "empty", "empty", "error"]
        assert await db.scalar(select(Event.id).where(Event.verb == "source.stalled")) is not None
        # A UI retry must respect upstream Retry-After and cannot create a fake run.
        with pytest.raises(RuntimeError, match="hız sınırı"):
            await fetch_news_source(db, failed, 20)
        assert len(list(await db.scalars(select(SourceRun)))) == 5


@pytest.mark.no_database
async def test_malformed_payload_and_invalid_date_are_not_empty_success():
    with pytest.raises(ValueError):
        HuggingFacePapersSource(date="yesterday")
    bad = HuggingFacePapersSource(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json=[{"paper": {"title": "No ID"}}])
        )
    )
    with pytest.raises(RuntimeError):
        await bad.fetch()


async def test_parallel_and_repeated_reads_make_one_upstream_request():
    import asyncio

    clear_news_cache()
    calls = 0

    async def upstream(request):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return httpx.Response(200, json=PAPER)

    async def read():
        async with SessionLocal() as db:
            source = HuggingFacePapersSource(transport=httpx.MockTransport(upstream))
            return await fetch_news_source(db, source, 20)

    results = await asyncio.gather(*[read() for _ in range(5)])
    assert all(len(result) == 1 for result in results)
    assert len(await read()) == 1
    assert calls == 1
    async with SessionLocal() as db:
        assert len(list(await db.scalars(select(SourceRun)))) == 1
