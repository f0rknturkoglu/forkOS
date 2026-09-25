import pytest
from app.integrations.career_ops.config import (
    CAREER_OPS_PINNED_COMMIT,
    CAREER_OPS_PINNED_VERSION,
    CAREER_OPS_UPSTREAM_REPO,
)


@pytest.mark.no_database
def test_career_ops_pinned_constants():
    assert CAREER_OPS_UPSTREAM_REPO == "career-ops-hq/career-ops"
    assert CAREER_OPS_PINNED_VERSION == "1.34.0"
    assert CAREER_OPS_PINNED_COMMIT == "6326eb5d3804e8cb20d28acd5701a4e603a301f9"
