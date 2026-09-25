import pytest
from app.config import Settings


@pytest.mark.no_database
def test_career_ops_config_defaults():
    cfg = Settings(
        career_ops_enabled=False,
        career_ops_root="",
        career_ops_node_bin="node",
        career_ops_timeout_seconds=30.0,
    )
    assert cfg.career_ops_enabled is False
    assert cfg.career_ops_node_bin == "node"
    assert cfg.career_ops_timeout_seconds == 30.0
    assert cfg.resolved_career_ops_root.name == "career-ops"
    assert "runtime/career-ops" in str(cfg.resolved_career_ops_runtime_dir)
