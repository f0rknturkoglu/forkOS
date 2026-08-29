from __future__ import annotations

import pytest

from app.sources.forkjob_core.scrapers.consider import ConsiderScraper

pytestmark = pytest.mark.no_database


class FakeClient:
    def __init__(self):
        self.calls = []

    async def get_html(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        return '<script>window.serverInitialData = {"csrfToken":"csrf-123"};</script>'

    async def post_json(self, url, payload, **kwargs):
        self.calls.append(("post", url, kwargs))
        return {"jobs": []}


async def test_consider_bootstraps_csrf_with_same_client():
    client = FakeClient()
    scraper = ConsiderScraper(
        board_id="sequoia-capital", base_url="https://jobs.sequoiacap.com"
    )
    assert await scraper.scrape(client) == []
    assert client.calls[0][:2] == ("get", "https://jobs.sequoiacap.com/jobs")
    assert client.calls[1][0:2] == (
        "post",
        "https://jobs.sequoiacap.com/api-boards/search-jobs",
    )
    assert client.calls[1][2]["headers"] == {
        "x-csrf-token": "csrf-123",
        "origin": "https://jobs.sequoiacap.com",
        "referer": "https://jobs.sequoiacap.com/jobs",
    }
