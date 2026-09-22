"""Repo-owned Hermes plugin contract, no user content or model context."""

from __future__ import annotations

import importlib.util
import json
import logging
import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_database

ROOT = Path(__file__).resolve().parents[2]
#: Sunucu tarafındaki A3 damıtma bütçesinin varsayılanı (`app/config.py`).
#: Plugin zaman aşımı bunun ÜSTÜNDE olmalıdır.
DEFAULT_A3_SERVER_BUDGET_SECONDS = 2.0

PLUGIN = ROOT / "tools/hermes/forkos-lifecycle/__init__.py"
INSTALLER = ROOT / "scripts/install_hermes_lifecycle.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def start_recording_server(statuses: dict[str, int]):
    """Loopback HTTP server recording every POST path/body; statuses keyed by path."""
    requests: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            requests.append({"path": self.path, "body": json.loads(raw or b"{}")})
            self.send_response(statuses.get(self.path, 200))
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *_):
            pass

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

    server = Server(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, requests


def recording_hook(plugin):
    """Hook factory whose transport records payloads instead of touching the network."""
    sent: list[dict] = []

    def mock_send(url, body, path=plugin.EVENT_PATH):
        sent.append({"path": path, **body.copy()})
        return 200, {}

    return sent, mock_send


def test_register_maps_events_without_context_or_content(monkeypatch) -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_test")
    sent = []

    def mock_send(url, body, path=plugin.EVENT_PATH):
        sent.append({"path": path, **body.copy()})
        if path == plugin.TURN_PATH:
            return 200, {"rendered_context": None}
        return 200

    monkeypatch.setattr(plugin, "_send", mock_send)

    class Context:
        hooks = {}

        def register_hook(self, name, callback):
            self.hooks[name] = callback

    ctx = Context()
    plugin.register(ctx)
    assert set(ctx.hooks) == {"pre_llm_call", "post_llm_call", "on_session_finalize"}
    extra = {"conversation_history": ["VERY_PRIVATE_HISTORY"], "future_key": "ignored"}
    assert ctx.hooks["pre_llm_call"](session_id="sid", turn_id="t1", platform="desktop", is_first_turn=True, **extra) is None
    assert ctx.hooks["pre_llm_call"](session_id="sid", turn_id="t2", platform="desktop", is_first_turn=False, **extra) is None
    assert ctx.hooks["post_llm_call"](session_id="sid", turn_id="t2", platform="desktop", **extra) is None
    assert ctx.hooks["on_session_finalize"](session_id="sid", platform="desktop", **extra) is None

    assert sent[0]["path"] == plugin.TURN_PATH
    assert sent[0]["is_first_turn"] is True
    assert sent[0]["turn_id"] == "t1"

    assert sent[1]["path"] == plugin.TURN_PATH
    assert sent[1]["is_first_turn"] is False
    assert sent[1]["turn_id"] == "t2"

    assert sent[2]["path"] == plugin.EPISODE_TURN_PATH
    assert sent[2]["turn_id"] == "t2"

    assert sent[3]["path"] == plugin.EPISODE_FINALIZE_PATH

    assert sent[4]["path"] == plugin.EVENT_PATH
    assert sent[4]["event"] == "session_finalize"


def test_pre_llm_call_injects_rendered_context(monkeypatch) -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_inject_test")

    def mock_send(url, body, path=plugin.TURN_PATH):
        return 200, {"rendered_context": "<forkos-context>hello</forkos-context>"}

    monkeypatch.setattr(plugin, "_send", mock_send)
    before, _, _ = plugin.make_hooks()

    res = before(session_id="sid", turn_id="t1", is_first_turn=True, user_message="test")
    assert res == {"context": "<forkos-context>hello</forkos-context>"}


def test_pre_llm_call_bounds_user_message(monkeypatch) -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_bounds_test")
    sent = []

    def mock_send(url, body, path=plugin.TURN_PATH):
        sent.append(body.copy())
        return 200, {"rendered_context": None}

    monkeypatch.setattr(plugin, "_send", mock_send)
    before, _, _ = plugin.make_hooks()

    long_msg = "x" * 1000
    res = before(session_id="sid", turn_id="t1", is_first_turn=True, user_message=long_msg)
    assert res is None
    assert len(sent) == 1
    assert len(sent[0]["user_message"]) == 500



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
    before, _, _ = plugin.make_hooks("http://127.0.0.1:1")
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
        before, _, _ = plugin.make_hooks(f"http://127.0.0.1:{server.server_address[1]}")
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
        before, _, finalize = plugin.make_hooks(base_url)

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


def test_post_llm_call_reports_turn_metadata(monkeypatch) -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_episode_metadata_test")
    sent, mock_send = recording_hook(plugin)
    monkeypatch.setattr(plugin, "_send", mock_send)
    _, observe_turn, _ = plugin.make_hooks()

    assert observe_turn(session_id="sid", turn_id="t1", platform="desktop",
                        user_message="hello", assistant_response="world") is None

    assert len(sent) == 1
    body = sent[0]
    assert body["path"] == plugin.EPISODE_TURN_PATH
    assert body["schema_version"] == 1
    assert body["harness"] == "hermes"
    assert body["session_id"] == "sid"
    assert body["turn_id"] == "t1"
    assert body["platform"] == "desktop"
    assert body["user_message"] == "hello"
    assert body["assistant_response"] == "world"
    assert body["user_truncated"] is False
    assert body["assistant_truncated"] is False


def test_post_llm_call_never_transports_conversation_history(monkeypatch) -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_episode_history_test")
    sent, mock_send = recording_hook(plugin)
    monkeypatch.setattr(plugin, "_send", mock_send)
    _, observe_turn, _ = plugin.make_hooks()

    history = [{"role": "user", "content": "PRIVATE_TRANSCRIPT"} for _ in range(500)]
    observe_turn(session_id="sid", turn_id="t1", user_message="hi",
                 assistant_response="yo", conversation_history=history)

    assert len(sent) == 1
    assert "conversation_history" not in sent[0]
    assert "PRIVATE_TRANSCRIPT" not in json.dumps(sent[0])


def test_post_llm_call_bounds_turn_text(monkeypatch) -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_episode_bounds_test")
    sent, mock_send = recording_hook(plugin)
    monkeypatch.setattr(plugin, "_send", mock_send)
    _, observe_turn, _ = plugin.make_hooks()

    observe_turn(session_id="sid", turn_id="t1",
                 user_message="u" * 2500, assistant_response="a" * 7000)

    body = sent[0]
    assert plugin.MAX_EPISODE_USER_CHARS == 2000
    assert plugin.MAX_EPISODE_ASSISTANT_CHARS == 6000
    assert len(body["user_message"]) == 2000
    assert len(body["assistant_response"]) == 6000
    assert body["user_truncated"] is True
    assert body["assistant_truncated"] is True


def test_post_llm_call_enforces_total_turn_budget(monkeypatch) -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_episode_budget_test")
    sent, mock_send = recording_hook(plugin)
    monkeypatch.setattr(plugin, "_send", mock_send)
    monkeypatch.setattr(plugin, "MAX_EPISODE_TURN_CHARS", 4000)
    _, observe_turn, _ = plugin.make_hooks()

    observe_turn(session_id="sid", turn_id="t1",
                 user_message="u" * 2000, assistant_response="a" * 6000)

    body = sent[0]
    assert len(body["user_message"]) == 2000
    assert len(body["assistant_response"]) == 2000
    assert body["assistant_truncated"] is True
    assert body["user_truncated"] is False


def test_post_llm_call_skips_invalid_identity_without_request(monkeypatch) -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_episode_identity_test")
    sent, mock_send = recording_hook(plugin)
    monkeypatch.setattr(plugin, "_send", mock_send)
    _, observe_turn, _ = plugin.make_hooks()

    assert observe_turn(session_id="", turn_id="t1", user_message="x") is None
    assert observe_turn(session_id=None, turn_id="t1", user_message="x") is None
    assert observe_turn(session_id="sid") is None
    assert observe_turn(session_id="sid", turn_id="   ") is None
    assert sent == []


def test_post_llm_call_absorbs_http_errors() -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_episode_status_test")
    statuses: dict[str, int] = {}
    server, requests = start_recording_server(statuses)
    try:
        _, observe_turn, _ = plugin.make_hooks(f"http://127.0.0.1:{server.server_address[1]}")
        for status in (404, 500, 503):
            statuses[plugin.EPISODE_TURN_PATH] = status
            assert observe_turn(session_id="sid", turn_id="t1",
                                user_message="x", assistant_response="y") is None
        assert len(requests) == 3
    finally:
        server.shutdown()
        server.server_close()


def test_post_llm_call_absorbs_connection_refusal() -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_episode_down_test")
    _, observe_turn, _ = plugin.make_hooks("http://127.0.0.1:1")
    assert observe_turn(session_id="sid", turn_id="t1", user_message="x") is None


def test_post_llm_call_waits_out_the_episode_timeout() -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_episode_timeout_test")

    class Slow(BaseHTTPRequestHandler):
        def do_POST(self):
            time.sleep(1.0)
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *_):
            pass

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

    with Server(("127.0.0.1", 0), Slow) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        _, observe_turn, _ = plugin.make_hooks(f"http://127.0.0.1:{server.server_address[1]}")
        started = time.monotonic()
        assert observe_turn(session_id="sid", turn_id="t1", user_message="x") is None
        elapsed = time.monotonic() - started
        # Bütçe sunucunun damıtma bütçesinin ÜSTÜNDE bir güvenlik ağıdır:
        # sunucu işi `A3_EXTRACTION_BUDGET_SECONDS` ile sınırlar, bu değer
        # yalnız sunucu takılırsa turu kurtarır.
        assert plugin.EPISODE_TIMEOUT_SECONDS > DEFAULT_A3_SERVER_BUDGET_SECONDS
        assert 0.9 <= elapsed < plugin.EPISODE_TIMEOUT_SECONDS
        server.shutdown()


def test_episode_timeout_is_env_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sunucu bütçesi yükseltilirse plugin zaman aşımı da yükseltilebilmelidir.

    İkisi bağımsız ayarlanabildiği için bu bir sözleşmedir: plugin zaman aşımı
    sunucu bütçesinin altında kalırsa istek erken kesilir ve damıtma sonucu
    kaybolur (tur `pending` kalır).
    """
    monkeypatch.setenv("FORKOS_EPISODE_TIMEOUT_SECONDS", "42.5")
    plugin = load(PLUGIN, "forkos_lifecycle_episode_timeout_env_test")
    assert plugin.EPISODE_TIMEOUT_SECONDS == 42.5
    monkeypatch.delenv("FORKOS_EPISODE_TIMEOUT_SECONDS")


def test_finalize_runs_episode_and_lifecycle_independently() -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_finalize_independent_test")
    statuses = {plugin.EPISODE_FINALIZE_PATH: 500, plugin.EVENT_PATH: 200}
    server, requests = start_recording_server(statuses)
    try:
        _, _, finalize = plugin.make_hooks(f"http://127.0.0.1:{server.server_address[1]}")
        assert finalize(session_id="sid", platform="cli") is None
        assert [r["path"] for r in requests] == [plugin.EPISODE_FINALIZE_PATH, plugin.EVENT_PATH]
        assert requests[0]["body"]["session_id"] == "sid"
        assert requests[1]["body"]["event"] == "session_finalize"
    finally:
        server.shutdown()
        server.server_close()


def test_finalize_absorbs_lifecycle_event_failure() -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_finalize_lifecycle_fail_test")
    statuses = {plugin.EPISODE_FINALIZE_PATH: 200, plugin.EVENT_PATH: 500}
    server, requests = start_recording_server(statuses)
    try:
        _, _, finalize = plugin.make_hooks(f"http://127.0.0.1:{server.server_address[1]}")
        assert finalize(session_id="sid", platform="cli") is None
        assert [r["path"] for r in requests] == [plugin.EPISODE_FINALIZE_PATH, plugin.EVENT_PATH]
    finally:
        server.shutdown()
        server.server_close()


def test_finalize_does_not_retry_episode_endpoint() -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_finalize_no_retry_test")
    statuses = {plugin.EPISODE_FINALIZE_PATH: 503, plugin.EVENT_PATH: 200}
    server, requests = start_recording_server(statuses)
    try:
        _, _, finalize = plugin.make_hooks(f"http://127.0.0.1:{server.server_address[1]}")
        assert finalize(session_id="sid", platform="cli") is None
        assert [r["path"] for r in requests].count(plugin.EPISODE_FINALIZE_PATH) == 1
    finally:
        server.shutdown()
        server.server_close()


def test_post_llm_call_never_logs_raw_message(caplog) -> None:
    plugin = load(PLUGIN, "forkos_lifecycle_episode_log_test")
    secret = "A3_RAW_SECRET_XYZ_987654"
    statuses = {plugin.EPISODE_TURN_PATH: 500}
    server, requests = start_recording_server(statuses)
    try:
        _, observe_turn, _ = plugin.make_hooks(f"http://127.0.0.1:{server.server_address[1]}")
        with caplog.at_level(logging.WARNING, logger="forkos_lifecycle"):
            assert observe_turn(session_id="sid", turn_id="t1",
                                user_message=secret, assistant_response=secret) is None
        assert len(requests) == 1
        assert requests[0]["body"]["user_message"] == secret
        assert secret not in caplog.text
        assert any("failed" in record.getMessage() for record in caplog.records)
    finally:
        server.shutdown()
        server.server_close()


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
