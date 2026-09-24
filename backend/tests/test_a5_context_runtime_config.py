"""A5 native defaults and explicit canonical Compose bridge wiring."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.config import Settings

pytestmark = pytest.mark.no_database


def test_native_defaults_and_typed_environment(monkeypatch):
    for name in (
        "A5_CONTEXT_MODE",
        "A5_JEVMLX_BASE_URL",
        "A5_CONTEXT_TIMEOUT_SECONDS",
        "A5_HOST_BRIDGE_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)
    native = Settings(_env_file=None)
    assert native.a5_context_mode == "off"
    assert native.a5_jevmlx_base_url == "http://127.0.0.1:8000"
    assert native.a5_context_timeout_seconds == 1.5
    assert native.a5_host_bridge_enabled is False

    monkeypatch.setenv("A5_CONTEXT_MODE", "shadow")
    monkeypatch.setenv("A5_CONTEXT_TIMEOUT_SECONDS", "2.25")
    monkeypatch.setenv("A5_HOST_BRIDGE_ENABLED", "1")
    configured = Settings(_env_file=None)
    assert configured.a5_context_mode == "shadow"
    assert configured.a5_context_timeout_seconds == 2.25
    assert configured.a5_host_bridge_enabled is True

    monkeypatch.setenv("A5_CONTEXT_MODE", "unknown")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_compose_api_wires_a5_without_enabling_judge():
    compose = yaml.safe_load((Path(__file__).resolve().parents[2] / "compose.yaml").read_text())
    env = compose["services"]["api"]["environment"]
    assert env["A5_CONTEXT_MODE"] == "${A5_CONTEXT_MODE:-off}"
    assert env["A5_JEVMLX_BASE_URL"] == "${A5_JEVMLX_BASE_URL:-http://host.docker.internal:8000}"
    assert env["A5_CONTEXT_TIMEOUT_SECONDS"] == "${A5_CONTEXT_TIMEOUT_SECONDS:-1.5}"
    assert env["A5_HOST_BRIDGE_ENABLED"] == "1"
