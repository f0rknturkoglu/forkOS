from datetime import UTC, datetime

import pytest

from app.modules.opportunity.identity import ListingIdentity, same_real_world_posting

pytestmark = pytest.mark.no_database


def _listing(**changes) -> ListingIdentity:
    base = dict(
        source="forkjob_core:greenhouse:acme",
        external_id="req-1",
        url="https://boards.greenhouse.io/acme/jobs/1",
        apply_url=None,
        provider="greenhouse",
        requisition_id="req-1",
        company="Acme",
        title="Senior Platform Engineer",
        location="Berlin",
        description="Build a reliable platform with Python, Kubernetes, and distributed systems. " * 4,
        published_at=datetime(2026, 9, 1, tzinfo=UTC),
    )
    base.update(changes)
    return ListingIdentity(**base)


def test_tracking_url_variants_are_strong_identity():
    assert same_real_world_posting(
        _listing(),
        _listing(
            source="careerops:greenhouse",
            external_id="wrapper-1",
            url="https://boards.greenhouse.io/acme/jobs/1/?utm_source=feed",
        ),
    )


def test_same_ats_requisition_across_sources_is_strong_identity():
    assert same_real_world_posting(
        _listing(),
        _listing(source="careerops:greenhouse", url="https://example.com/wrapped/1"),
    )


def test_coarse_cluster_with_distinct_requisitions_stays_separate():
    assert not same_real_world_posting(
        _listing(title="Backend Engineer", description=None),
        _listing(
            source="careerops:greenhouse",
            external_id="req-2",
            requisition_id="req-2",
            url="https://boards.greenhouse.io/acme/jobs/2",
            title="Backend Engineer",
            description=None,
        ),
    )


def test_different_jd_stays_separate_without_stable_id():
    assert not same_real_world_posting(
        _listing(external_id="first", requisition_id=None),
        _listing(
            source="careerops:workday",
            provider="workday",
            external_id="second",
            requisition_id=None,
            url="https://example.com/another",
            description="A different role with database, security, and API operations. " * 4,
        ),
    )


def test_identical_substantial_jd_and_compatible_date_can_merge():
    assert same_real_world_posting(
        _listing(external_id="first", requisition_id=None),
        _listing(
            source="careerops:workday",
            provider="workday",
            external_id="second",
            requisition_id=None,
            url="https://example.com/wrapped/1",
        ),
    )
