"""Hermes A1 adapter: bounded metadata POST, no context, no tools or Vault access."""

from __future__ import annotations

import http.client
import json
import logging
import os
import re
import time
from urllib.parse import urlsplit

LOGGER = logging.getLogger("forkos_lifecycle")
DEFAULT_BASE_URL = "http://127.0.0.1:8787"
TIMEOUT_SECONDS = 0.7
EVENT_PATH = "/api/agent/lifecycle/event"
TURN_PATH = "/api/agent/lifecycle/turn"
_PLATFORM = re.compile(r"^[a-z0-9_-]{1,64}$")


def validate_base_url(value: str) -> tuple[str, int]:
    """Reject redirects/proxies/remote hosts before any request is made."""
    parts = urlsplit(value)
    if (parts.scheme != "http" or parts.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parts.username or parts.password or parts.path not in {"", "/"}
            or parts.query or parts.fragment):
        raise ValueError("lifecycle endpoint must be a plain loopback HTTP origin")
    try:
        port = parts.port or 80
    except ValueError as exc:
        raise ValueError("invalid lifecycle port") from exc
    if not 1 <= port <= 65535:
        raise ValueError("invalid lifecycle port")
    return ("127.0.0.1" if parts.hostname == "localhost" else parts.hostname), port


def _safe_identity(value: object) -> str | None:
    if (not isinstance(value, str) or not 1 <= len(value) <= 256 or not value.strip()
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        return None
    return value


def _send(base_url: str, payload: dict[str, object], path: str = EVENT_PATH) -> tuple[int, dict[str, object] | None] | int:
    host, port = validate_base_url(base_url)  # validate again at request execution
    connection = http.client.HTTPConnection(host, port, timeout=TIMEOUT_SECONDS)
    try:
        connection.request(
            "POST", path, body=json.dumps(payload, separators=(",", ":")),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        data = response.read(65536)
        if not (200 <= response.status < 300):
            raise OSError(f"HTTP {response.status}")
        try:
            body = json.loads(data.decode("utf-8")) if data else None
        except Exception:
            body = None
        if path == EVENT_PATH:
            return response.status
        return response.status, body
    finally:
        connection.close()


def make_hooks(base_url: str = DEFAULT_BASE_URL):
    validate_base_url(base_url)

    def before(**kwargs: object) -> dict[str, str] | None:
        started = time.monotonic()
        session_id = _safe_identity(kwargs.get("session_id"))
        if session_id is None:
            LOGGER.warning("lifecycle turn skipped: invalid session identity")
            return None

        is_first = kwargs.get("is_first_turn") is True
        turn_id = _safe_identity(kwargs.get("turn_id"))
        if not is_first and turn_id is None:
            LOGGER.warning("lifecycle turn skipped: missing turn identity")
            return None

        payload: dict[str, object] = {
            "schema_version": 1,
            "harness": "hermes",
            "session_id": session_id,
            "platform": "unknown",
            "is_first_turn": is_first,
        }
        platform = kwargs.get("platform")
        if isinstance(platform, str) and _PLATFORM.fullmatch(platform.strip().lower()):
            payload["platform"] = platform.strip().lower()
        if turn_id is not None:
            payload["turn_id"] = turn_id

        raw_msg = kwargs.get("user_message") or kwargs.get("prompt")
        if isinstance(raw_msg, str) and raw_msg.strip():
            payload["user_message"] = raw_msg.strip()[:500]

        try:
            res = _send(base_url, payload, path=TURN_PATH)
            status = res[0] if isinstance(res, tuple) else res
            body = res[1] if isinstance(res, tuple) else None
            LOGGER.info("lifecycle turn delivered (HTTP %s, %.0f ms)",
                        status, (time.monotonic() - started) * 1000)
            if body and isinstance(body, dict):
                ctx = body.get("rendered_context")
                if ctx and isinstance(ctx, str):
                    return {"context": ctx}
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("lifecycle turn delivery failed (%s, %.0f ms)",
                           type(exc).__name__, (time.monotonic() - started) * 1000)
        return None

    def finalize(**kwargs: object) -> None:
        started = time.monotonic()
        session_id = _safe_identity(kwargs.get("session_id"))
        if session_id is None:
            LOGGER.warning("lifecycle session_finalize skipped: invalid session identity")
            return
        payload: dict[str, object] = {
            "schema_version": 1,
            "event": "session_finalize",
            "harness": "hermes",
            "session_id": session_id,
            "platform": "unknown",
        }
        platform = kwargs.get("platform")
        if isinstance(platform, str) and _PLATFORM.fullmatch(platform.strip().lower()):
            payload["platform"] = platform.strip().lower()
        try:
            status = _send(base_url, payload, path=EVENT_PATH)
            LOGGER.info("lifecycle session_finalize delivered (HTTP %s, %.0f ms)",
                        status, (time.monotonic() - started) * 1000)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("lifecycle session_finalize delivery failed (%s, %.0f ms)",
                           type(exc).__name__, (time.monotonic() - started) * 1000)

    return before, finalize



def register(ctx) -> None:
    base_url = os.environ.get("FORKOS_LIFECYCLE_BASE_URL", DEFAULT_BASE_URL)
    before, finalize = make_hooks(base_url)
    ctx.register_hook("pre_llm_call", before)
    ctx.register_hook("on_session_finalize", finalize)
