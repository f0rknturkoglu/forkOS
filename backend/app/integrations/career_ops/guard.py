"""Runtime readiness and pinned identity verification guard for career-ops."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from app.integrations.career_ops.config import (
    CAREER_OPS_PINNED_COMMIT,
    CAREER_OPS_PINNED_VERSION,
    CAREER_OPS_UPSTREAM_REPO,
)
from app.integrations.career_ops.errors import (
    CareerOpsConfigurationError,
    CareerOpsUnavailableError,
    CareerOpsVersionMismatchError,
)
from app.integrations.career_ops.models import (
    CareerOpsIdentity,
    CareerOpsRuntimeStatus,
)


class CareerOpsRuntimeGuard:
    """Shared identity and runtime readiness verifier for career-ops capabilities."""

    def __init__(
        self,
        enabled: bool,
        checkout_dir: Path,
        node_bin: str = "node",
        discovery_enabled: bool = True,
    ) -> None:
        self.enabled = enabled
        self.checkout_dir = checkout_dir.resolve()
        self.node_bin = node_bin
        self.discovery_enabled = discovery_enabled

    @staticmethod
    def expected_identity() -> CareerOpsIdentity:
        return CareerOpsIdentity(
            repository=CAREER_OPS_UPSTREAM_REPO,
            version=CAREER_OPS_PINNED_VERSION,
            commit=CAREER_OPS_PINNED_COMMIT,
        )

    def check_node_runtime(self) -> CareerOpsRuntimeStatus:
        node_path = shutil.which(self.node_bin)
        if not node_path:
            return CareerOpsRuntimeStatus(
                node_version=None,
                node_compatible=False,
                installed=False,
                details=f"Node.js binary '{self.node_bin}' not found on PATH.",
            )

        try:
            out = subprocess.check_output([node_path, "--version"], text=True, timeout=5).strip()
            m = re.match(r"^v(\d+)\.(\d+)\.", out)
            if not m:
                return CareerOpsRuntimeStatus(
                    node_version=out,
                    node_compatible=False,
                    installed=True,
                    details=f"Unrecognized Node.js version format: {out}",
                )
            major = int(m.group(1))
            compatible = major >= 18
            return CareerOpsRuntimeStatus(
                node_version=out.lstrip("v"),
                node_compatible=compatible,
                installed=True,
                details="Node runtime OK" if compatible else "Node >= 18 required",
            )
        except Exception as exc:
            return CareerOpsRuntimeStatus(
                node_version=None,
                node_compatible=False,
                installed=True,
                details=f"Failed to check Node version: {exc}",
            )

    def get_actual_identity(self) -> tuple[CareerOpsIdentity | None, str | None]:
        """Returns (identity, error_message)."""
        if not self.checkout_dir.exists() or not (self.checkout_dir / "package.json").exists():
            return None, f"career-ops checkout missing at {self.checkout_dir}"

        try:
            pkg_data = json.loads((self.checkout_dir / "package.json").read_text("utf-8"))
            actual_version = pkg_data.get("version", "")
        except Exception as exc:
            return None, f"Failed to read package.json: {exc}"

        actual_commit = ""
        git_dir = self.checkout_dir / ".git"
        if git_dir.exists():
            try:
                actual_commit = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(self.checkout_dir),
                    text=True,
                    timeout=5,
                ).strip()
            except Exception:
                actual_commit = "unknown"
        else:
            actual_commit = "unknown"

        return (
            CareerOpsIdentity(
                repository=CAREER_OPS_UPSTREAM_REPO,
                version=actual_version,
                commit=actual_commit,
            ),
            None,
        )

    def ensure_ready(self, required_script: str | None = None) -> None:
        """Fail-closed assertion of identity and runtime readiness.

        Raises:
            CareerOpsUnavailableError: if disabled, node missing, checkout missing, or required script missing.
            CareerOpsConfigurationError: if discovery disabled or commit is unknown.
            CareerOpsVersionMismatchError: if version or commit does not match lock.
        """
        if not self.enabled:
            raise CareerOpsUnavailableError("career-ops capability engine is disabled in configuration.")

        runtime = self.check_node_runtime()
        if not runtime.installed or not runtime.node_compatible:
            raise CareerOpsUnavailableError(runtime.details or "Node runtime incompatible or missing")

        identity, err = self.get_actual_identity()
        if not identity:
            raise CareerOpsUnavailableError(err or "career-ops checkout or package.json missing")

        expected = self.expected_identity()
        if identity.version != expected.version:
            raise CareerOpsVersionMismatchError(
                f"Version mismatch! Expected {expected.version}, got {identity.version}"
            )

        if identity.commit == "unknown":
            raise CareerOpsConfigurationError(
                "Pinned commit SHA could not be positively verified (missing git repository or commit metadata)."
            )

        if identity.commit != expected.commit:
            raise CareerOpsVersionMismatchError(
                f"Commit mismatch! Expected {expected.commit[:7]}, got {identity.commit[:7]}"
            )

        if required_script:
            script_path = self.checkout_dir / required_script
            if not script_path.exists():
                raise CareerOpsUnavailableError(f"Required script '{required_script}' does not exist at {script_path}")
