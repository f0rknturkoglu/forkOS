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
    loc_pos = parsed["location_filter"]["positive"]
    assert "remote" in loc_pos
    assert "ankara" in loc_pos
    assert "istanbul" in loc_pos


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
