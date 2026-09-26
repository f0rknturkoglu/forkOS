"""Tests for deterministic job description identity validation (C3.2 Finding A)."""

import pytest
from app.integrations.career_ops.job_identity import (
    assess_extracted_job_identity,
)


@pytest.mark.no_database
def test_specific_job_to_same_specific_job():
    res = assess_extracted_job_identity(
        requested_url="https://boards.greenhouse.io/gitlab/jobs/4279007005",
        final_url="https://boards.greenhouse.io/gitlab/jobs/4279007005",
        title="Senior Security Engineer",
        text="A substantive job description with requirements, responsibilities, and qualifications " * 5,
    )
    assert res.identity_status == "valid_job"
    assert res.is_valid_for_promotion is True
    assert res.reason == "valid_specific_posting"


@pytest.mark.no_database
def test_canonical_equivalent_redirect():
    # http -> https
    res1 = assess_extracted_job_identity(
        requested_url="http://jobs.example.com/posting/123",
        final_url="https://jobs.example.com/posting/123",
        title="Senior Engineer",
        text="A substantive job description with requirements, responsibilities, and qualifications " * 5,
    )
    assert res1.identity_status == "valid_job"
    assert res1.is_valid_for_promotion is True
    assert res1.reason == "canonical_redirect_preserved_identity"

    # Greenhouse host migration preserving job ID
    res2 = assess_extracted_job_identity(
        requested_url="https://boards.greenhouse.io/gitlab/jobs/4279007005",
        final_url="https://job-boards.greenhouse.io/gitlab/jobs/4279007005",
        title="Senior Security Engineer",
        text="A substantive job description with requirements, responsibilities, and qualifications " * 5,
    )
    assert res2.identity_status == "valid_job"
    assert res2.is_valid_for_promotion is True
    assert res2.reason == "canonical_redirect_preserved_identity"


@pytest.mark.no_database
def test_greenhouse_error_redirect():
    # Real observed C3.1 smoke failure shape
    res = assess_extracted_job_identity(
        requested_url="https://boards.greenhouse.io/gitlab/jobs/4279007005",
        final_url="https://job-boards.greenhouse.io/gitlab?error=true",
        title="Current openings at GitLab",
        text="Current openings at GitLab Search Department Select... 199 jobs " * 10,
    )
    assert res.identity_status == "invalid_non_job"
    assert res.is_valid_for_promotion is False
    assert res.reason == "provider_error_redirect"


@pytest.mark.no_database
def test_specific_job_redirected_to_board_root():
    # Specific job path lost, landed on company board root
    res = assess_extracted_job_identity(
        requested_url="https://jobs.lever.co/netflix/12345-67890",
        final_url="https://jobs.lever.co/netflix",
        title="Netflix Jobs",
        text="Explore open positions across engineering, product, and creative teams. " * 8,
    )
    assert res.identity_status == "invalid_non_job"
    assert res.is_valid_for_promotion is False
    assert res.reason == "redirected_to_board_root"


@pytest.mark.no_database
def test_generic_openings_page_title():
    res = assess_extracted_job_identity(
        requested_url="https://careers.example.com/job/dev-1",
        final_url="https://careers.example.com/openings",
        title="Current openings at Example Corp",
        text="Browse our list of open roles and find your next opportunity. " * 6,
    )
    assert res.identity_status == "invalid_non_job"
    assert res.is_valid_for_promotion is False
    assert res.reason in ("generic_openings_page", "redirected_to_board_root")


@pytest.mark.no_database
def test_error_title_or_404_page():
    res = assess_extracted_job_identity(
        requested_url="https://example.com/careers/position/99",
        final_url="https://example.com/careers/position/99",
        title="Job Not Found - 404",
        text="The requested job posting could not be found or has been removed.",
    )
    assert res.identity_status == "invalid_non_job"
    assert res.is_valid_for_promotion is False
    assert res.reason == "provider_error_redirect"


@pytest.mark.no_database
def test_uncertain_redirect_destination():
    # Redirected to completely unrelated domain/path
    res = assess_extracted_job_identity(
        requested_url="https://example.com/jobs/123",
        final_url="https://thirdpartyportal.org/special-landing",
        title="Platform Software Architect",
        text="Architecting high throughput distributed systems across multiple regions. " * 6,
    )
    assert res.identity_status == "uncertain_identity"
    assert res.is_valid_for_promotion is False
    assert res.reason == "identity_uncertain"


@pytest.mark.no_database
def test_text_too_short():
    res = assess_extracted_job_identity(
        requested_url="https://boards.greenhouse.io/corp/jobs/123",
        final_url="https://boards.greenhouse.io/corp/jobs/123",
        title="Software Engineer",
        text="Brief one-liner.",
    )
    assert res.is_valid_for_promotion is False
    assert res.reason == "text_too_short"
