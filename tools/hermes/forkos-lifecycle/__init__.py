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


def _send(base_url: str, payload: dict[str, object]) -> int:
    host, port = validate_base_url(base_url)  # validate again at request execution
    connection = http.client.HTTPConnection(host, port, timeout=TIMEOUT_SECONDS)
    try:
        connection.request(
            "POST", EVENT_PATH, body=json.dumps(payload, separators=(",", ":")),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        response.read(256)
        if response.status >= 400:
            raise OSError(f"HTTP {response.status}")
        return response.status
    finally:
        connection.close()


def make_hooks(base_url: str = DEFAULT_BASE_URL):
    validate_base_url(base_url)

    def deliver(event: str, kwargs: dict[str, object]) -> None:
        started = time.monotonic()
        session_id = _safe_identity(kwargs.get("session_id"))
        if session_id is None:
            LOGGER.warning("lifecycle %s skipped: invalid session identity", event)
            return
        payload: dict[str, object] = {
            "schema_version": 1,
            "event": event,
            "harness": "hermes",
            "session_id": session_id,
            "platform": "unknown",
        }
        platform = kwargs.get("platform")
        if isinstance(platform, str) and _PLATFORM.fullmatch(platform.strip().lower()):
            payload["platform"] = platform.strip().lower()
        turn_id = _safe_identity(kwargs.get("turn_id"))
        if event == "turn_seen" and turn_id is None:
            LOGGER.warning("lifecycle %s skipped: missing turn identity", event)
            return
        if event != "session_finalize" and turn_id is not None:
            payload["turn_id"] = turn_id
        try:
            status = _send(base_url, payload)
            LOGGER.info("lifecycle %s delivered (HTTP %s, %.0f ms)",
                        event, status, (time.monotonic() - started) * 1000)
        except Exception as exc:  # noqa: BLE001
            # Hooks must never break a Hermes turn.
            LOGGER.warning("lifecycle %s delivery failed (%s, %.0f ms)",
                           event, type(exc).__name__, (time.monotonic() - started) * 1000)

    def before(**kwargs: object) -> None:
        deliver("session_start" if kwargs.get("is_first_turn") is True else "turn_seen", kwargs)

    def finalize(**kwargs: object) -> None:
        deliver("session_finalize", kwargs)

    return before, finalize


def register(ctx) -> None:
    base_url = os.environ.get("FORKOS_LIFECYCLE_BASE_URL", DEFAULT_BASE_URL)
    before, finalize = make_hooks(base_url)
    ctx.register_hook("pre_llm_call", before)
    ctx.register_hook("on_session_finalize", finalize)
