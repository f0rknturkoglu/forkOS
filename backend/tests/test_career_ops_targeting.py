from pathlib import Path
import pytest
import yaml

from app.integrations.career_ops.errors import CareerOpsSecurityError
from app.integrations.career_ops.targeting import CareerOpsDiscoveryConfigBuilder


@pytest.mark.no_database
def test_build_portals_yaml_from_forkos_config(tmp_path: Path):
    sample_config = """
scoring:
  role_terms:
    - software
    - engineer
    - backend
  skills:
    - name: python
    - name: fast-api
      aliases: ["fastapi"]
  kill_words:
    - sales representative
    - recruiter
  tr_office_cities:
    - ankara
    - istanbul
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(sample_config, encoding="utf-8")

    yaml_str = CareerOpsDiscoveryConfigBuilder.build_portals_yaml(config_path=config_file)
    parsed = yaml.safe_load(yaml_str)

    assert "title_filter" in parsed
    pos = parsed["title_filter"]["positive"]
    neg = parsed["title_filter"]["negative"]

    assert "software" in pos
    assert "backend" in pos
    assert "python" in pos
    assert "fastapi" in pos

    assert "sales representative" in neg
    assert "recruiter" in neg

    assert "location_filter" in parsed
    loc_filter = parsed["location_filter"]
    assert "always_allow" in loc_filter
    assert "allow" in loc_filter
    assert "block_hard" in loc_filter
    assert loc_filter["strict"] is False

    assert "remote" in loc_filter["always_allow"]
    assert "ankara" in loc_filter["always_allow"]
    assert "istanbul" in loc_filter["always_allow"]
    assert "europe" in loc_filter["allow"]
    assert "germany" in loc_filter["allow"]
    assert "us citizenship" in loc_filter["block_hard"]


@pytest.mark.no_database
def test_location_filter_matches_pinned_upstream_semantics(tmp_path: Path):
    """Contract test: verify generated portals.yml against pinned upstream buildLocationFilter()."""
    import json
    import subprocess
    import shutil

    repo_root = Path(__file__).resolve().parent.parent.parent
    vendor_scan_mjs = repo_root / ".vendor" / "career-ops" / "scan.mjs"
    if not vendor_scan_mjs.exists() or not shutil.which("node"):
        pytest.skip("Pinned career-ops or node not available for contract test")

    sample_config = """
scoring:
  role_terms:
    - backend
  tr_office_cities:
    - ankara
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(sample_config, encoding="utf-8")
    yaml_str = CareerOpsDiscoveryConfigBuilder.build_portals_yaml(config_path=config_file)
    parsed = yaml.safe_load(yaml_str)
    loc_filter_json = json.dumps(parsed["location_filter"])

    node_script = f"""
import('{vendor_scan_mjs.as_posix()}').then(({{ buildLocationFilter }}) => {{
  const filter = buildLocationFilter({loc_filter_json});
  const results = {{
    remote_europe: filter('Europe', '', 'Backend Engineer - Remote'),
    berlin_germany: filter('Berlin, Germany', '', 'Backend Engineer'),
    madrid_spain: filter('Madrid, Spain', '', 'Backend Engineer'),
    ankara_turkey: filter('Ankara, Türkiye', '', 'Backend Engineer'),
    us_restricted: filter('New York, NY (US citizenship required)', '', 'Backend Engineer'),
    unknown_location: filter('', '', 'Backend Engineer'),
  }};
  console.log(JSON.stringify(results));
}});
"""
    out = subprocess.check_output(["node", "--input-type=module", "-e", node_script], text=True).strip()
    data = json.loads(out)

    assert data["remote_europe"] is True
    assert data["berlin_germany"] is True
    assert data["madrid_spain"] is True
    assert data["ankara_turkey"] is True
    assert data["us_restricted"] is False
    assert data["unknown_location"] is True



@pytest.mark.no_database
def test_fail_closed_on_empty_positive_keywords(tmp_path: Path):
    empty_config = """
scoring:
  role_terms: []
  skills: []
  kill_words:
    - sales
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(empty_config, encoding="utf-8")

    with pytest.raises(CareerOpsSecurityError, match="Positive title keywords must not be empty"):
        CareerOpsDiscoveryConfigBuilder.build_portals_yaml(config_path=config_file)


@pytest.mark.no_database
def test_project_to_runtime(tmp_path: Path):
    sample_config = """
scoring:
  role_terms:
    - developer
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(sample_config, encoding="utf-8")

    runtime_dir = tmp_path / "runtime"
    projected_file = CareerOpsDiscoveryConfigBuilder.project_to_runtime(
        runtime_dir=runtime_dir,
        config_path=config_file,
    )

    assert projected_file.exists()
    assert projected_file == runtime_dir / "portals.yml"
    parsed = yaml.safe_load(projected_file.read_text(encoding="utf-8"))
    assert parsed["title_filter"]["positive"] == ["developer"]
