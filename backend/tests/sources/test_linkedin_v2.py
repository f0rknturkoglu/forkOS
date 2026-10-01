"""SYNTHETIC offline LinkedIn contracts; never assertions of live guest availability."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from app.sources.base import ScrapeTelemetry
from app.sources.forkjob_core.scrapers.linkedin import LinkedInScraper
from app.sources.forkjob_core.scrapers.linkedin_native import LinkedInNativeTransport, search_url
from app.sources.forkjob_core.scrapers.linkedin_parsing import (
    LinkedInResponseError,
    detail_job,
    linkedin_identity,
    parse_cards,
)
from app.sources.forkjob_core.scrapers.linkedin_policy import (
    PATHS,
    ROOT,
    LinkedInPolicyDenied,
    LinkedInPolicyGate,
)
from app.sources.forkjob_core.scrapers.linkedin_types import LinkedInBudget, LinkedInTransportResult

pytestmark = pytest.mark.no_database
FIXTURES = Path(__file__).parent / "fixtures/linkedin-v2"


def read(name):
    return (FIXTURES / name).read_text()


def response(body, status=200, mime="text/html", **headers):
    return httpx.Response(status, text=body, headers={"content-type": mime, **headers})


def client(pages=(), *, policy="allow-robots.txt"):
    return SimpleNamespace(
        _read_bounded_response=AsyncMock(return_value=response(read(policy), mime="text/plain")),
        _bounded_request=AsyncMock(side_effect=pages),
    )


def page(ids):
    return (
        '<ul class="jobs-search__results-list">'
        + "".join(
            f'<div class="base-search-card"><a class="base-card__full-link" href="{ROOT}/jobs/view/{i}"></a><h3 class="base-search-card__title">Software Engineer</h3><h4 class="base-search-card__subtitle">Acme</h4></div>'
            for i in ids
        )
        + "</ul>"
    )


@pytest.mark.parametrize("name,kind", [("login.html", "login"), ("challenge.html", "challenge")])
def test_fingerprint_rejects_authentication_pages(name, kind):
    with pytest.raises(LinkedInResponseError) as error:
        parse_cards(read(name))
    assert error.value.kind == kind and not error.value.eligible


def test_cards_optional_fields_identity_tracking_and_detail():
    cards, count = parse_cards(read("cards.html"))
    assert count == len(cards) == 2
    assert cards[0].job_id == "111" and cards[0].url == ROOT + "/jobs/view/111"
    assert cards[1].location is None
    job = detail_job(read("detail.html"), cards[0])
    assert "Visa sponsorship available" in job.description
    assert "Seniority: Entry level" in job.description
    assert "Application URL: https://employer.example/jobs/111" in job.description
    assert job.salary == "60000 EUR/year"
    assert linkedin_identity("https://evil.example/jobs/view/111") == (None, None)


def test_empty_unknown_malformed_and_reposted_are_distinct():
    assert parse_cards(read("empty.html")) == ([], 0)
    with pytest.raises(LinkedInResponseError, match="schema"):
        parse_cards("<html>unexpected document</html>")
    with pytest.raises(LinkedInResponseError, match="malformed_cards"):
        parse_cards('<div class="base-search-card"><h3>No identity</h3></div>')
    cards, _ = parse_cards(read("cards.html").replace("1 day ago", "Reposted 3 days ago"))
    job = detail_job(read("detail.html"), cards[0])
    assert job.date_source.value == "discovered"
    assert "Listing state: Reposted" in cards[0].to_job().description


@pytest.mark.parametrize("transport", ["auto", "native", "jobspy"])
async def test_current_denial_precedes_both_transports_even_with_runner(transport, monkeypatch):
    monkeypatch.setattr(
        "app.sources.forkjob_core.scrapers.linkedin._merge_user_profiles", lambda profiles: profiles
    )
    c = client()
    c._read_bounded_response.return_value = response(
        (FIXTURES.parent / "batch2/linkedin-robots.txt").read_text(), mime="text/plain"
    )
    native, jobspy = SimpleNamespace(search=AsyncMock()), SimpleNamespace(search=AsyncMock())
    scraper = LinkedInScraper(
        searches=[{"term": "Python"}],
        allow_direct=True,
        transport=transport,
        policy_gate=LinkedInPolicyGate(),
        native_transport=native,
        jobspy_transport=jobspy,
    )
    with pytest.raises(LinkedInPolicyDenied, match="robots.txt disallows"):
        await scraper.scrape(c)
    native.search.assert_not_awaited()
    jobspy.search.assert_not_awaited()
    c._bounded_request.assert_not_awaited()
    assert scraper.telemetry.metadata["policy_allowed"] is False
    assert all(not scraper.policy._parser.can_fetch("forkjob", ROOT + path) for path in PATHS)


@pytest.mark.parametrize(
    "body,status,mime",
    [
        ("garbage", 200, "text/plain"),
        ("<html>login</html>", 200, "text/html"),
        ("User-agent: *\nAllow: /", 404, "text/plain"),
        ("User-agent: Googlebot\nAllow: /", 200, "text/plain"),
    ],
)
async def test_unverifiable_policy_fails_closed(body, status, mime):
    c = client()
    c._read_bounded_response.return_value = response(body, status, mime)
    state = await LinkedInPolicyGate().check(c)
    assert not state.allowed
    c._bounded_request.assert_not_awaited()


async def test_policy_is_cached_once_and_refreshable():
    c, gate = client(), LinkedInPolicyGate()
    assert (await gate.check(c)).allowed
    await gate.require(c, ROOT + "/jobs")
    c._read_bounded_response.assert_awaited_once()
    c._read_bounded_response.return_value = response(
        "User-agent: *\nDisallow: /", mime="text/plain"
    )
    assert not (await gate.check(c, force=True)).allowed


@pytest.mark.parametrize(
    "wanted,expected,stop", [(50, 20, "exhausted"), (15, 15, "profile_limit_reached")]
)
async def test_actual_card_count_drives_cursor_and_cap(wanted, expected, stop):
    c, gate = (
        client(
            [
                response(page(range(1, 11))),
                response(page(range(11, 21))),
                response(read("empty.html")),
            ]
        ),
        LinkedInPolicyGate(),
    )
    result = await LinkedInNativeTransport(gate, minimum=0, jitter=0).search(
        [{"term": "Engineer", "results_wanted": wanted}], c, LinkedInBudget()
    )
    assert len(result.jobs) == expected and result.telemetry.stop_reason == stop
    starts = [
        parse_qs(urlsplit(call.args[1]).query)["start"][0]
        for call in c._bounded_request.call_args_list
    ]
    assert starts == (["0", "10", "20"] if wanted == 50 else ["0", "10"])
    assert c._read_bounded_response.await_count == 1


async def test_repeated_page_and_later_failure_keep_useful_records():
    c, gate = (
        client([response(page(range(1, 11))), response(page(range(1, 11)))]),
        LinkedInPolicyGate(),
    )
    result = await LinkedInNativeTransport(gate, minimum=0, jitter=0).search(
        [{"term": "Engineer"}], c, LinkedInBudget()
    )
    assert len(result.jobs) == 10 and result.errors and result.telemetry.stop_reason != "exhausted"
    assert c._bounded_request.await_count == 2


async def test_geo_cache_and_deterministic_filters():
    c, gate = client(), LinkedInPolicyGate()
    c._bounded_request.side_effect = [
        response('[{"id":"101","displayName":"Germany"}]', mime="application/json")
    ]
    native = LinkedInNativeTransport(gate, minimum=0, jitter=0)
    native.metadata = {
        "native_requests": 0,
        "geo_requested": 0,
        "geo_resolved": 0,
        "geo_failed": 0,
        "geo_fallback": 0,
    }
    profile = {"term": "AI", "location": "Germany", "is_remote": True, "hours_old": 72}
    assert await native.geo(profile, c, LinkedInBudget()) == "101"
    assert await native.geo(profile, c, LinkedInBudget()) == "101"
    assert c._bounded_request.await_count == 1
    params = parse_qs(urlsplit(search_url(profile, 7, "101")).query)
    assert params == {
        "keywords": ["AI"],
        "start": ["7"],
        "geoId": ["101"],
        "f_WT": ["2"],
        "f_TPR": ["r259200"],
    }


async def test_geo_failure_falls_back_to_location_text():
    c, gate = (
        client([response("[]", mime="application/json"), response(read("empty.html"))]),
        LinkedInPolicyGate(),
    )
    result = await LinkedInNativeTransport(gate, minimum=0, jitter=0).search(
        [{"term": "Engineer", "location": "Germany"}], c, LinkedInBudget()
    )
    assert result.telemetry.metadata["geo_fallback"] == 1
    assert "location=Germany" in c._bounded_request.call_args.args[1]


async def test_detail_budget_keeps_discovery_and_richer_evidence():
    c, gate = (
        client([response(read("cards.html")), response(read("detail.html"))]),
        LinkedInPolicyGate(),
    )
    result = await LinkedInNativeTransport(gate, minimum=0, jitter=0).search(
        [{"term": "Engineer", "results_wanted": 2, "fetch_description": True}],
        c,
        LinkedInBudget(max_details=1),
    )
    assert len(result.jobs) == 2 and result.telemetry.metadata["detail_succeeded"] == 1
    assert result.telemetry.metadata["detail_candidates"] == 2
    assert "detail_budget_reached" in result.telemetry.partial_reason


@pytest.mark.parametrize("kind", ["login", "challenge", "unknown", "403", "content_type"])
async def test_response_failures_never_become_healthy_zero(kind):
    body = read(kind + ".html") if kind in {"login", "challenge"} else "unknown"
    c, gate = (
        client(
            [
                response(
                    body,
                    status=403 if kind == "403" else 200,
                    mime="application/json" if kind == "content_type" else "text/html",
                )
            ]
        ),
        LinkedInPolicyGate(),
    )
    result = await LinkedInNativeTransport(gate, minimum=0, jitter=0, max_retries=0).search(
        [{"term": "Engineer"}], c, LinkedInBudget()
    )
    assert not result.jobs and result.errors and not result.succeeded
    assert result.telemetry.stop_reason != "exhausted"


async def test_retry_after_bounded_retry_and_telemetry(monkeypatch):
    from app.sources.forkjob_core.scrapers.linkedin_native import LinkedInRateController

    monkeypatch.setattr(LinkedInRateController, "wait", AsyncMock())
    throttle = __import__("unittest.mock", fromlist=["Mock"]).Mock()
    monkeypatch.setattr(LinkedInRateController, "throttle", throttle)
    c, gate = (
        client([response("", 429, **{"Retry-After": "3"}), response(read("empty.html"))]),
        LinkedInPolicyGate(),
    )
    result = await LinkedInNativeTransport(gate, minimum=0, jitter=0, max_retries=1).search(
        [{"term": "Engineer"}], c, LinkedInBudget()
    )
    assert result.telemetry.metadata["429_count"] == 1 and c._bounded_request.await_count == 2
    throttle.assert_called_once_with(3)


async def test_repeated_429_stops_without_ip_or_transport_retry(monkeypatch):
    from app.sources.forkjob_core.scrapers.linkedin_native import LinkedInRateController

    monkeypatch.setattr(LinkedInRateController, "wait", AsyncMock())
    c, gate = client([response("", 429), response("", 429)]), LinkedInPolicyGate()
    result = await LinkedInNativeTransport(gate, minimum=0, jitter=0, max_retries=1).search(
        [{"term": "Engineer"}], c, LinkedInBudget()
    )
    assert c._bounded_request.await_count == 2 and result.telemetry.metadata["429_count"] == 2
    assert result.telemetry.metadata["fallback_forbidden"]


async def test_native_cancellation_interrupts_http_wait():
    c, gate = client(), LinkedInPolicyGate()
    started = asyncio.Event()

    async def blocked(*args, **kwargs):
        started.set()
        await asyncio.sleep(60)

    c._bounded_request.side_effect = blocked
    task = asyncio.create_task(
        LinkedInNativeTransport(gate, minimum=0, jitter=0).search(
            [{"term": "Engineer"}], c, LinkedInBudget()
        )
    )
    await asyncio.wait_for(started.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, 2)


@pytest.mark.parametrize(
    "mode,native_failure,native_items,softblock,expected_fallback",
    [
        ("native", True, 0, False, False),
        ("jobspy", False, 0, False, False),
        ("auto", False, 1, False, False),
        ("auto", True, 0, False, True),
        ("auto", True, 1, False, True),
        ("auto", True, 1, True, True),
    ],
)
async def test_transport_fallback_matrix(
    mode, native_failure, native_items, softblock, expected_fallback, monkeypatch
):
    monkeypatch.setattr(
        "app.sources.forkjob_core.scrapers.linkedin._merge_user_profiles", lambda profiles: profiles
    )
    card = parse_cards(read("cards.html"))[0][0]
    native_result = LinkedInTransportResult(
        [card.to_job()] if native_items else [],
        ["profile-1: shell" if softblock else "profile-1: transport"] if native_failure else [],
        ScrapeTelemetry(
            items_seen=native_items, result_limit=50, metadata={"soft_block_count": int(softblock)}
        ),
        "native_v2",
        1,
        int(not native_failure),
        [0] if native_failure else [],
        [0] if native_failure else [],
    )
    recovery = LinkedInTransportResult(
        [detail_job(read("detail.html"), card)],
        [],
        ScrapeTelemetry(items_seen=1, result_limit=50),
        "jobspy_v1",
        1,
        1,
    )
    native = SimpleNamespace(search=AsyncMock(return_value=native_result))
    jobspy = SimpleNamespace(search=AsyncMock(return_value=recovery))
    scraper = LinkedInScraper(
        searches=[{"term": "Engineer"}],
        allow_direct=True,
        transport=mode,
        policy_gate=LinkedInPolicyGate(),
        native_transport=native,
        jobspy_transport=jobspy,
    )
    result = await scraper.scrape(client())
    assert result.telemetry.metadata["fallback_used"] == expected_fallback
    assert jobspy.search.await_count == int(expected_fallback or mode == "jobspy")
    if mode == "jobspy":
        native.search.assert_not_awaited()
    if expected_fallback:
        assert (
            len(result.jobs) == 1
            and result.errors
            and result.telemetry.stop_reason == "transport_degraded"
        )
        assert "Build software" in result.jobs[0].description
        if softblock:
            assert result.telemetry.metadata["soft_block_count"] == 1


async def test_unknown_transport_does_not_fetch_even_policy(monkeypatch):
    monkeypatch.setattr(
        "app.sources.forkjob_core.scrapers.linkedin._merge_user_profiles", lambda profiles: profiles
    )
    c = client()
    from app.sources.forkjob_core.scrapers.base import ScraperPermanentError

    with pytest.raises(ScraperPermanentError, match="Unknown LinkedIn transport"):
        await LinkedInScraper(transport="oops").scrape(c)
    c._read_bounded_response.assert_not_awaited()


async def test_both_transports_fail_truthfully(monkeypatch):
    monkeypatch.setattr(
        "app.sources.forkjob_core.scrapers.linkedin._merge_user_profiles", lambda profiles: profiles
    )
    failed = LinkedInTransportResult(
        [], ["profile-1: transport"], ScrapeTelemetry(items_seen=0), "native_v2", 1, 0, [0], [0]
    )
    legacy_failed = LinkedInTransportResult(
        [], ["profile-1: JobSpy failure"], ScrapeTelemetry(items_seen=0), "jobspy_v1", 1, 0, [0]
    )
    scraper = LinkedInScraper(
        searches=[{"term": "Engineer"}],
        allow_direct=True,
        policy_gate=LinkedInPolicyGate(),
        native_transport=SimpleNamespace(search=AsyncMock(return_value=failed)),
        jobspy_transport=SimpleNamespace(search=AsyncMock(return_value=legacy_failed)),
    )
    result = await scraper.scrape(client())
    assert not result.jobs and not result.succeeded and len(result.errors) == 2
    assert result.telemetry.stop_reason == "transport_degraded"


async def test_request_budget_preserves_partial_cards():
    c, gate = client([response(page(range(1, 11)))]), LinkedInPolicyGate()
    result = await LinkedInNativeTransport(gate, minimum=0, jitter=0).search(
        [{"term": "Engineer"}], c, LinkedInBudget(max_requests=1)
    )
    assert len(result.jobs) == 10 and "run_budget_reached" in result.errors[0]
    assert c._bounded_request.await_count == 1


async def test_cancel_during_backoff_leaves_no_request_task():
    from app.sources.forkjob_core.scrapers.linkedin_native import LinkedInRateController

    started = asyncio.Event()
    rate = LinkedInRateController()
    rate.next_at = asyncio.get_running_loop().time() + 60

    async def wait():
        started.set()
        await rate.wait(LinkedInBudget())

    task = asyncio.create_task(wait())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, 1)


def test_canonical_url_fallback_and_minimal_detail():
    html = page([111]).replace("/jobs/view/111", "/jobs/view/software-engineer?tracking=1")
    cards, count = parse_cards(html)
    assert count == 1 and cards[0].job_id is None
    assert cards[0].to_job().external_id == ROOT + "/jobs/view/software-engineer"
    minimal = (
        '<div class="show-more-less-html__markup">Full description without optional facts.</div>'
    )
    assert "Full description" in detail_job(minimal, cards[0]).description


async def test_invalid_profile_does_not_discard_previous_native_results():
    c = client([response(page([111]))])
    native = LinkedInNativeTransport(LinkedInPolicyGate(), minimum=0, jitter=0)
    result = await native.search(
        [{"term": "Engineer", "results_wanted": 1}, {"term": "Engineer", "results_wanted": "bad"}],
        c,
        LinkedInBudget(),
    )
    assert len(result.jobs) == 1 and result.failed_profiles == [1]
    assert result.errors == ["profile-2: invalid_profile"]


async def test_recovery_setup_failure_keeps_native_partial_cards(monkeypatch):
    monkeypatch.setattr(
        'app.sources.forkjob_core.scrapers.linkedin._merge_user_profiles', lambda profiles: profiles
    )
    card = parse_cards(read('cards.html'))[0][0]
    partial = LinkedInTransportResult(
        [card.to_job()], ['profile-1: transport'], ScrapeTelemetry(items_seen=1),
        'native_v2', 1, 0, [0], [0],
    )
    scraper = LinkedInScraper(
        searches=[{'term': 'Engineer'}], allow_direct=True, policy_gate=LinkedInPolicyGate(),
        native_transport=SimpleNamespace(search=AsyncMock(return_value=partial)),
        jobspy_transport=SimpleNamespace(search=AsyncMock(side_effect=RuntimeError('secret detail'))),
    )
    result = await scraper.scrape(client())
    assert len(result.jobs) == 1
    assert result.errors[-1] == 'fallback: RuntimeError'
    assert result.telemetry.stop_reason == 'transport_degraded'
