"""Comprehensive diagnostic surface for career-ops."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from app.integrations.career_ops.capabilities import get_declared_capabilities
from app.integrations.career_ops.config import (
    CAREER_OPS_PINNED_COMMIT,
    CAREER_OPS_PINNED_VERSION,
    CAREER_OPS_UPSTREAM_REPO,
)
from app.integrations.career_ops.models import (
    CareerOpsDoctorResult,
    CareerOpsIdentity,
    CareerOpsRuntimeStatus,
    CareerOpsStatusEnum,
    CareerOpsUpstreamOnboarding,
)
from app.integrations.career_ops.runner import CareerOpsRunner


class CareerOpsDoctor:
    def __init__(
        self,
        enabled: bool,
        checkout_dir: Path,
        runtime_dir: Path,
        runner: CareerOpsRunner,
        node_bin: str = "node",
    ) -> None:
        self.enabled = enabled
        self.checkout_dir = checkout_dir
        self.runtime_dir = runtime_dir
        self.runner = runner
        self.node_bin = node_bin

    def _expected_identity(self) -> CareerOpsIdentity:
        return CareerOpsIdentity(
            repository=CAREER_OPS_UPSTREAM_REPO,
            version=CAREER_OPS_PINNED_VERSION,
            commit=CAREER_OPS_PINNED_COMMIT,
        )

    def _check_node_runtime(self) -> CareerOpsRuntimeStatus:
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
            # Expect v26.x or v22.x or >=18
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

    async def run_diagnostics(self) -> CareerOpsDoctorResult:
        expected = self._expected_identity()
        runtime = self._check_node_runtime()
        declared = get_declared_capabilities()

        if not self.enabled:
            return CareerOpsDoctorResult(
                status=CareerOpsStatusEnum.DISABLED,
                expected_identity=expected,
                actual_identity=None,
                runtime=runtime,
                upstream_onboarding=None,
                capabilities_declared=len(declared),
                capabilities_available=0,
                warnings=["career-ops capability engine is disabled in configuration."],
            )

        if not runtime.installed or not runtime.node_compatible:
            return CareerOpsDoctorResult(
                status=CareerOpsStatusEnum.UNAVAILABLE,
                expected_identity=expected,
                actual_identity=None,
                runtime=runtime,
                upstream_onboarding=None,
                capabilities_declared=len(declared),
                capabilities_available=0,
                errors=[runtime.details or "Node runtime incompatible or missing"],
            )

        if not self.checkout_dir.exists() or not (self.checkout_dir / "package.json").exists():
            return CareerOpsDoctorResult(
                status=CareerOpsStatusEnum.UNAVAILABLE,
                expected_identity=expected,
                actual_identity=None,
                runtime=runtime,
                upstream_onboarding=None,
                capabilities_declared=len(declared),
                capabilities_available=0,
                errors=[f"career-ops checkout missing at {self.checkout_dir}"],
            )

        # Inspect package.json version
        actual_version = ""
        try:
            pkg_data = json.loads((self.checkout_dir / "package.json").read_text("utf-8"))
            actual_version = pkg_data.get("version", "")
        except Exception as exc:
            return CareerOpsDoctorResult(
                status=CareerOpsStatusEnum.MISCONFIGURED,
                expected_identity=expected,
                actual_identity=None,
                runtime=runtime,
                upstream_onboarding=None,
                capabilities_declared=len(declared),
                capabilities_available=0,
                errors=[f"Failed to read package.json: {exc}"],
            )

        # Inspect actual commit
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

        actual_identity = CareerOpsIdentity(
            repository=CAREER_OPS_UPSTREAM_REPO,
            version=actual_version,
            commit=actual_commit,
        )

        if actual_version != expected.version:
            return CareerOpsDoctorResult(
                status=CareerOpsStatusEnum.VERSION_MISMATCH,
                expected_identity=expected,
                actual_identity=actual_identity,
                runtime=runtime,
                upstream_onboarding=None,
                capabilities_declared=len(declared),
                capabilities_available=0,
                errors=[
                    f"Version mismatch! Expected {expected.version}, got {actual_version}"
                ],
            )

        # Strict commit verification: unknown commit CANNOT be READY
        if actual_commit == "unknown":
            return CareerOpsDoctorResult(
                status=CareerOpsStatusEnum.MISCONFIGURED,
                expected_identity=expected,
                actual_identity=actual_identity,
                runtime=runtime,
                upstream_onboarding=None,
                capabilities_declared=len(declared),
                capabilities_available=0,
                errors=[
                    "Pinned commit SHA could not be positively verified (missing git repository or commit metadata)."
                ],
            )

        if actual_commit != expected.commit:
            return CareerOpsDoctorResult(
                status=CareerOpsStatusEnum.VERSION_MISMATCH,
                expected_identity=expected,
                actual_identity=actual_identity,
                runtime=runtime,
                upstream_onboarding=None,
                capabilities_declared=len(declared),
                capabilities_available=0,
                errors=[
                    f"Commit mismatch! Expected {expected.commit[:7]}, got {actual_commit[:7]}"
                ],
            )

        # Verify core files
        core_files = ["doctor.mjs", "path-resolver.mjs"]
        missing_files = [f for f in core_files if not (self.checkout_dir / f).exists()]
        if missing_files:
            return CareerOpsDoctorResult(
                status=CareerOpsStatusEnum.MISCONFIGURED,
                expected_identity=expected,
                actual_identity=actual_identity,
                runtime=runtime,
                upstream_onboarding=None,
                capabilities_declared=len(declared),
                capabilities_available=0,
                errors=[f"Required core files missing: {', '.join(missing_files)}"],
            )

        # Execute upstream doctor in isolated workspace WITHOUT --target
        # Upstream doctor resolves codeRoot as __dirname and projectRoot via CAREER_OPS_ROOT / CAREER_OPS_DATA_DIR
        upstream_onboarding: CareerOpsUpstreamOnboarding | None = None
        warnings: list[str] = []
        try:
            exec_res = await self.runner.run_script(
                "doctor.mjs",
                ["--json"],
                timeout_seconds=15.0,
            )
            if exec_res.exit_code != 0:
                warnings.append(f"doctor.mjs exited with code {exec_res.exit_code}")
            else:
                try:
                    payload = json.loads(exec_res.stdout)
                    upstream_onboarding = CareerOpsUpstreamOnboarding(
                        onboarding_needed=bool(payload.get("onboardingNeeded")),
                        missing=list(payload.get("missing") or []),
                        unpersonalized=list(payload.get("unpersonalized") or []),
                        warnings=[str(w) for w in (payload.get("warnings") or [])],
                        plugins=list(payload.get("plugins") or []),
                        playwright_mcp=dict(payload.get("playwright_mcp") or {}),
                        active_cli=payload.get("active_cli"),
                    )
                except Exception:
                    warnings.append("doctor.mjs stdout was not JSON parseable")
        except Exception as exc:
            return CareerOpsDoctorResult(
                status=CareerOpsStatusEnum.DEGRADED,
                expected_identity=expected,
                actual_identity=actual_identity,
                runtime=runtime,
                upstream_onboarding=None,
                capabilities_declared=len(declared),
                capabilities_available=1,
                warnings=[f"Engine doctor probe failed: {exc}"],
            )

        return CareerOpsDoctorResult(
            status=CareerOpsStatusEnum.READY,
            expected_identity=expected,
            actual_identity=actual_identity,
            runtime=runtime,
            upstream_onboarding=upstream_onboarding,
            capabilities_declared=len(declared),
            capabilities_available=1,
            warnings=warnings,
        )
