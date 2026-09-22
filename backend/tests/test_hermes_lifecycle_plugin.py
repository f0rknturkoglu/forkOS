"""Repo-owned Hermes plugin contract, no user content or model context."""

from __future__ import annotations

import importlib.util
import json
import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_database

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "tools/hermes/forkos-lifecycle/__init__.py"
INSTALLER = ROOT / "scripts/install_hermes_lifecycle.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_register_maps_events_without_context_or_content(monkeypatch) -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_test")
    sent = []
    monkeypatch.setattr(plugin, "_send", lambda url, body: sent.append(body.copy()))

    class Context:
        hooks = {}

        def register_hook(self, name, callback):
            self.hooks[name] = callback

    ctx = Context()
    plugin.register(ctx)
    assert set(ctx.hooks) == {"pre_llm_call", "on_session_finalize"}
    private = {"user_message": "VERY_PRIVATE_MESSAGE", "conversation_history": ["VERY_PRIVATE_HISTORY"], "future_key": "ignored"}
    assert ctx.hooks["pre_llm_call"](session_id="sid", turn_id="t1", platform="desktop", is_first_turn=True, **private) is None
    assert ctx.hooks["pre_llm_call"](session_id="sid", turn_id="t2", platform="desktop", is_first_turn=False, **private) is None
    assert ctx.hooks["on_session_finalize"](session_id="sid", platform="desktop", **private) is None
    assert [item["event"] for item in sent] == ["session_start", "turn_seen", "session_finalize"]
    assert [item.get("turn_id") for item in sent] == ["t1", "t2", None]
    assert "VERY_PRIVATE" not in json.dumps(sent)
    assert all(set(item) <= {"schema_version", "event", "harness", "session_id", "turn_id", "platform"} for item in sent)


def test_remote_urls_are_rejected() -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_url_test")
    assert plugin.validate_base_url("http://localhost:8787") == ("127.0.0.1", 8787)
    for url in ("https://example.com", "http://192.168.1.1:8787", "http://127.0.0.1:8787/redirect", "http://user:pass@localhost:8787"):
        with pytest.raises(ValueError):
            plugin.make_hooks(url)
        with pytest.raises(ValueError):
            plugin._send(url, {})


def test_server_down_and_stall_fail_open() -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_timeout_test")
    before, _ = plugin.make_hooks("http://127.0.0.1:1")
    started = time.monotonic()
    assert before(session_id="sid", turn_id="t1", is_first_turn=True) is None
    assert time.monotonic() - started < 1.5

    class Slow(BaseHTTPRequestHandler):
        def do_POST(self):
            time.sleep(2)
        def log_message(self, *_):
            pass

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

    with Server(("127.0.0.1", 0), Slow) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        before, _ = plugin.make_hooks(f"http://127.0.0.1:{server.server_address[1]}")
        started = time.monotonic()
        assert before(session_id="sid", turn_id="t1", is_first_turn=True) is None
        assert time.monotonic() - started < 1.5
        server.shutdown()


def test_http_status_semantics() -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_status_semantics_test")

    current_status = 200

    class StatusHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(current_status)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *_):
            pass

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

    with Server(("127.0.0.1", 0), StatusHandler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        before, finalize = plugin.make_hooks(base_url)

        # 2xx: Success
        for status in (200, 201, 204):
            current_status = status
            assert plugin._send(base_url, {"schema_version": 1}) == status
            assert before(session_id="sid", turn_id="t1", is_first_turn=True) is None
            assert finalize(session_id="sid") is None

        # 3xx: Fail-open (not accepted as success, but never crashes Hermes conversation)
        for status in (301, 302, 307, 308):
            current_status = status
            with pytest.raises(OSError, match=f"HTTP {status}"):
                plugin._send(base_url, {"schema_version": 1})
            assert before(session_id="sid", turn_id="t1", is_first_turn=True) is None
            assert finalize(session_id="sid") is None

        # 4xx: Fail-open
        for status in (400, 404, 409, 422):
            current_status = status
            with pytest.raises(OSError, match=f"HTTP {status}"):
                plugin._send(base_url, {"schema_version": 1})
            assert before(session_id="sid", turn_id="t1", is_first_turn=True) is None
            assert finalize(session_id="sid") is None

        # 5xx: Fail-open
        for status in (500, 502, 503):
            current_status = status
            with pytest.raises(OSError, match=f"HTTP {status}"):
                plugin._send(base_url, {"schema_version": 1})
            assert before(session_id="sid", turn_id="t1", is_first_turn=True) is None
            assert finalize(session_id="sid") is None

        server.shutdown()


def test_installer_refuses_unmanaged_or_edited_plugin(tmp_path: Path) -> None:
    installer = load(INSTALLER, "forkos_lifecycle_installer_test")
    target = installer.install(tmp_path)
    assert target.name == "forkos-lifecycle"
    cache = target / "__pycache__"
    cache.mkdir()
    (cache / "__init__.cpython-313.pyc").write_bytes(b"generated")
    assert installer.install(tmp_path) == target
    assert not cache.exists()
    (target / "__init__.py").write_text("user edit", encoding="utf-8")
    with pytest.raises(RuntimeError):
        installer.install(tmp_path)
    unmanaged = tmp_path / "other" / "plugins" / "forkos-lifecycle"
    unmanaged.mkdir(parents=True)
    with pytest.raises(RuntimeError):
        installer.install(tmp_path / "other")
