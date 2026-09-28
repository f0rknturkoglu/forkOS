"""Reverse ATS acquisition must not apply candidate-fit rejection."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from app.integrations.career_ops.targeting import CareerOpsDiscoveryConfigBuilder

pytestmark = pytest.mark.no_database


def test_candidate_preferences_do_not_filter_acquisition(tmp_path: Path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """scoring:
  role_terms: [Backend Engineer]
  skills: [{name: Python}]
  kill_words: [sales, recruiter]
  blocked_locations: [United States]
""",
        encoding="utf-8",
    )
    configured = yaml.safe_load(
        CareerOpsDiscoveryConfigBuilder.build_portals_yaml(config_path=config_file)
    )
    absent = yaml.safe_load(
        CareerOpsDiscoveryConfigBuilder.build_portals_yaml(config_path=tmp_path / "missing.yaml")
    )
    assert configured == absent
    assert configured["title_filter"] == {"positive": [], "negative": []}
    assert configured["location_filter"] == {"strict": False}


def test_project_to_runtime_does_not_read_candidate_config(tmp_path: Path):
    runtime_dir = tmp_path / "runtime"
    result = CareerOpsDiscoveryConfigBuilder.project_to_runtime(
        runtime_dir, config_path=tmp_path / "missing.yaml"
    )
    assert result == runtime_dir / "portals.yml"
    assert yaml.safe_load(result.read_text(encoding="utf-8"))["title_filter"]["positive"] == []


def test_unrestricted_filters_match_pinned_scanner_contract():
    repo_root = Path(__file__).resolve().parent.parent.parent
    vendor_scan = repo_root / ".vendor" / "career-ops" / "scan.mjs"
    if not vendor_scan.exists() or not shutil.which("node"):
        pytest.skip("Pinned career-ops or node unavailable")
    config = yaml.safe_load(CareerOpsDiscoveryConfigBuilder.build_portals_yaml())
    script = f"""
import('{vendor_scan.as_posix()}').then(({{ buildTitleFilter, buildLocationFilter }}) => {{
  const title = buildTitleFilter({json.dumps(config['title_filter'])});
  const location = buildLocationFilter({json.dumps(config['location_filter'])});
  console.log(JSON.stringify({{
    platform: title('Platform Engineer'),
    recruiter: title('Technical Recruiter'),
    us: location('New York, United States', '', 'Platform Engineer'),
    unknown: location('', '', 'Platform Engineer')
  }}));
}});
"""
    output = subprocess.check_output(
        ["node", "--input-type=module", "-e", script], text=True
    ).strip()
    assert json.loads(output) == {
        "platform": True,
        "recruiter": True,
        "us": True,
        "unknown": True,
    }
