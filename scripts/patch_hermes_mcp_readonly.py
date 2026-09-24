#!/usr/bin/env python3
"""forkOS — Repo-owned compatibility patch for upstream Hermes MCP readOnlyHint bug.

Upstream Hermes (v0.21.4 and adjacent versions) inspects ``getattr(annotations, "readOnlyHint", None)``
on Pydantic v2 ``mcp.types.ToolAnnotations`` objects. Because the Python SDK attributes are snake_case
(``read_only_hint``) and Pydantic v2 does not alias attribute access, Hermes evaluates all tools as
write-capable (readOnlyHint=False). In `trust: untrusted` mode, this forces interactive confirmations
for all read-only calls.

This script safely, deterministically, and idempotently patches the installed Hermes runtime to check
both `read_only_hint` and `readOnlyHint`.

Usage:
    python3 scripts/patch_hermes_mcp_readonly.py [--check] [--dry-run] [--no-cache-clear]
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import shutil
import sys
from pathlib import Path


VULNERABLE_SNIPPET = (
    '    hint = annotations.get("readOnlyHint") if isinstance(annotations, dict) else getattr(annotations, "readOnlyHint", None)'
)

PATCHED_SNIPPET = (
    '    if isinstance(annotations, dict):\n'
    '        hint = annotations.get("readOnlyHint")\n'
    '    else:\n'
    '        hint = getattr(annotations, "read_only_hint", getattr(annotations, "readOnlyHint", None))'
)


def find_hermes_dir() -> Path | None:
    """Locate the installed hermes-agent root directory."""
    candidates = []
    if "HERMES_AGENT_PATH" in os.environ:
        candidates.append(Path(os.environ["HERMES_AGENT_PATH"]))
    if "HERMES_HOME" in os.environ:
        candidates.append(Path(os.environ["HERMES_HOME"]) / "hermes-agent")
    candidates.append(Path.home() / ".hermes" / "hermes-agent")

    for path in candidates:
        target = path.expanduser().resolve()
        if (target / "tools" / "mcp_tool_registration.py").is_file():
            return target
    return None


def get_hermes_version(hermes_dir: Path) -> str:
    pyproject = hermes_dir / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8")
        match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', text)
        if match:
            return match.group(1)
    return "unknown"


def clear_mcp_schema_cache(hermes_dir: Path) -> int:
    """Clear cached forkos-brain schema entries so Hermes re-discovers live annotations."""
    cleared = 0
    cache_dirs = [
        Path.home() / ".hermes" / "cache",
        hermes_dir / "cache",
    ]
    for cdir in cache_dirs:
        if not cdir.is_dir():
            continue
        for f in cdir.glob("*mcp*"):
            if f.is_file() and f.suffix in {".json", ".cache"}:
                try:
                    f.unlink()
                    cleared += 1
                except OSError:
                    pass
    return cleared


def patch_hermes(hermes_dir: Path, dry_run: bool = False, check_only: bool = False, clear_cache: bool = True) -> int:
    target_file = hermes_dir / "tools" / "mcp_tool_registration.py"
    version = get_hermes_version(hermes_dir)
    print(f"Target Hermes install: {hermes_dir} (version: {version})")
    print(f"Target file: {target_file}")

    content = target_file.read_text(encoding="utf-8")

    if "_annotation_read_only_hint" not in content:
        print("REFUSE PATCH: Function `_annotation_read_only_hint` not found in target file.", file=sys.stderr)
        return 1

    # Check if already patched or upstream has fixed it
    if 'getattr(annotations, "read_only_hint"' in content or "read_only_hint" in content.split("def _annotation_read_only_hint")[1].split("def ")[0]:
        print("PATCH NOT REQUIRED: Target `_annotation_read_only_hint` already supports `read_only_hint`.")
        return 0

    if VULNERABLE_SNIPPET not in content:
        print("REFUSE PATCH: Target function does not match known vulnerable pattern.", file=sys.stderr)
        print("Manual inspection of `_annotation_read_only_hint` is required.", file=sys.stderr)
        return 1

    if check_only:
        print("VULNERABLE: Hermes MCP registration does not check snake_case `read_only_hint`.")
        return 2

    print("Vulnerability detected: Hermes only checks camelCase `readOnlyHint` on SDK objects.")

    if dry_run:
        print("DRY-RUN: Would replace vulnerable snippet with snake_case-aware fallback.")
        return 0

    # Backup original
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_file = target_file.with_name(f"{target_file.name}.bak.{timestamp}")
    shutil.copy2(target_file, backup_file)
    print(f"Created backup: {backup_file}")

    # Deterministic replacement
    new_content = content.replace(VULNERABLE_SNIPPET, PATCHED_SNIPPET, 1)
    target_file.write_text(new_content, encoding="utf-8")
    print("Successfully patched `_annotation_read_only_hint`.")

    if clear_cache:
        cleared_count = clear_mcp_schema_cache(hermes_dir)
        print(f"Cleared {cleared_count} stale MCP schema cache file(s).")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check if vulnerable without making changes")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying files")
    parser.add_argument("--no-cache-clear", action="store_true", help="Do not clear MCP schema cache after patch")
    parser.add_argument("--hermes-dir", type=Path, help="Override Hermes installation directory")

    args = parser.parse_args()

    hermes_dir = args.hermes_dir or find_hermes_dir()
    if not hermes_dir or not hermes_dir.is_dir():
        print("ERROR: Could not locate Hermes installation directory.", file=sys.stderr)
        print("Specify with --hermes-dir or set HERMES_HOME / HERMES_AGENT_PATH.", file=sys.stderr)
        return 1

    return patch_hermes(
        hermes_dir,
        dry_run=args.dry_run,
        check_only=args.check,
        clear_cache=not args.no_cache_clear,
    )


if __name__ == "__main__":
    sys.exit(main())
