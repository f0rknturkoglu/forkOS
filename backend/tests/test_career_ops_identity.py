import json
from pathlib import Path
import pytest
from app.integrations.career_ops.config import (
    CAREER_OPS_PINNED_COMMIT,
    CAREER_OPS_PINNED_VERSION,
    CAREER_OPS_UPSTREAM_REPO,
    LOCK_MANIFEST_PATH,
)


@pytest.mark.no_database
def test_career_ops_pinned_constants_match_lock_manifest():
    assert LOCK_MANIFEST_PATH.exists()
    lock_data = json.loads(LOCK_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert lock_data["repository"] == "career-ops-hq/career-ops"
    assert lock_data["version"] == "1.34.0"
    assert lock_data["commit"] == "6326eb5d3804e8cb20d28acd5701a4e603a301f9"

    # Python constants must derive directly from the lockfile
    assert CAREER_OPS_UPSTREAM_REPO == lock_data["repository"]
    assert CAREER_OPS_PINNED_VERSION == lock_data["version"]
    assert CAREER_OPS_PINNED_COMMIT == lock_data["commit"]


@pytest.mark.no_database
def test_setup_script_consumes_lock_manifest():
    repo_root = Path(__file__).resolve().parent.parent.parent
    setup_script = repo_root / "scripts" / "setup_career_ops.sh"
    content = setup_script.read_text(encoding="utf-8")

    # setup script must reference upstream.lock.json
    assert "upstream.lock.json" in content
    # setup script must NOT hardcode the commit or version literals
    assert 'PINNED_COMMIT="6326eb5d3804e8cb20d28acd5701a4e603a301f9"' not in content
    assert 'PINNED_VERSION="1.34.0"' not in content
