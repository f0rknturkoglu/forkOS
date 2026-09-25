"""Canonical constants and version pinning for career-ops integration."""

from __future__ import annotations

import json
from pathlib import Path

LOCK_MANIFEST_PATH: Path = Path(__file__).resolve().parent / "upstream.lock.json"

if not LOCK_MANIFEST_PATH.exists():
    raise RuntimeError(f"Authoritative career-ops lock manifest missing: {LOCK_MANIFEST_PATH}")

try:
    _lock_data = json.loads(LOCK_MANIFEST_PATH.read_text(encoding="utf-8"))
except Exception as _exc:
    raise RuntimeError(f"Malformed career-ops lock manifest: {_exc}") from _exc

CAREER_OPS_UPSTREAM_REPO: str = _lock_data["repository"]
CAREER_OPS_PINNED_VERSION: str = _lock_data["version"]
CAREER_OPS_PINNED_COMMIT: str = _lock_data["commit"]
