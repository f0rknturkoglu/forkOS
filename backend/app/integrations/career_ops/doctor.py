"""Comprehensive diagnostic surface for career-ops."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from app.config import settings
from app.integrations.career_ops.capabilities import (
    count_available_capabilities,
    get_declared_capabilities,
)
from app.integrations.career_ops.config import (
    CAREER_OPS_PINNED_COMMIT,
    CAREER_OPS_PINNED_VERSION,
    CAREER_OPS_UPSTREAM_REPO,
)
from app.integrations.career_ops.guard import CareerOpsRuntimeGuard
from app.integrations.career_ops.models import (
    CareerOpsCapabilityContext,
    CareerOpsDoctorResult,
    CareerOpsIdentity,
    CareerOpsRuntimeStatus,
    CareerOpsStatusEnum,
    CareerOpsUpstreamOnboarding,
)
from app.integrations.career_ops.runner import CareerOpsRunner


def probe_browser_readiness(checkout_dir: Path, node_bin: str = "node") -> bool:
    """Check if Playwright and Chromium browser binary are installed and ready."""
    if not (checkout_dir / "node_modules" / "playwright").exists():
        return False
    try:
        res = subprocess.run(
            [
                node_bin,
                "-e",
                "import('playwright').then(p => { const pth = p.chromium.executablePath(); process.stdout.write(pth); }).catch(() => process.exit(1))",
            ],
            cwd=str(checkout_dir),
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        if res.returncode == 0 and res.stdout.strip():
            chrome_path = Path(res.stdout.strip())
            return chrome_path.exists()
        return False
    except Exception:
        return False


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
        self.guard = CareerOpsRuntimeGuard(
            enabled=enabled,
            checkout_dir=checkout_dir,
            node_bin=node_bin,
            discovery_enabled=settings.career_ops_discovery_enabled,
        )

    def _expected_identity(self) -> CareerOpsIdentity:
        return self.guard.expected_identity()

    def _check_node_runtime(self) -> CareerOpsRuntimeStatus:
        return self.guard.check_node_runtime()

    async def run_diagnostics(self) -> CareerOpsDoctorResult:
        expected = self.guard.expected_identity()
        runtime = self.guard.check_node_runtime()
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

        actual_identity, ident_err = self.guard.get_actual_identity()
        if actual_identity is None:
            return CareerOpsDoctorResult(
                status=CareerOpsStatusEnum.MISCONFIGURED,
                expected_identity=expected,
                actual_identity=None,
                runtime=runtime,
                upstream_onboarding=None,
                capabilities_declared=len(declared),
                capabilities_available=0,
                errors=[ident_err or "Failed to read package.json"],
            )

        if actual_identity.version != expected.version:
            return CareerOpsDoctorResult(
                status=CareerOpsStatusEnum.VERSION_MISMATCH,
                expected_identity=expected,
                actual_identity=actual_identity,
                runtime=runtime,
                upstream_onboarding=None,
                capabilities_declared=len(declared),
                capabilities_available=0,
                errors=[
                    f"Version mismatch! Expected {expected.version}, got {actual_identity.version}"
                ],
            )

        # Strict commit verification: unknown commit CANNOT be READY
        if actual_identity.commit == "unknown":
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

        if actual_identity.commit != expected.commit:
            return CareerOpsDoctorResult(
                status=CareerOpsStatusEnum.VERSION_MISMATCH,
                expected_identity=expected,
                actual_identity=actual_identity,
                runtime=runtime,
                upstream_onboarding=None,
                capabilities_declared=len(declared),
                capabilities_available=0,
                errors=[
                    f"Commit mismatch! Expected {expected.commit[:7]}, got {actual_identity.commit[:7]}"
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

        # Probe browser readiness for C3 execution
        browser_ready = probe_browser_readiness(self.checkout_dir, self.node_bin)

        # Dynamic computation of available capabilities based on runtime readiness and feature flags
        cap_ctx = CareerOpsCapabilityContext(
            enabled=True,
            core_ready=True,
            discovery_enabled=settings.career_ops_discovery_enabled,
            browser_ready=browser_ready,
        )
        available_capabilities_count = count_available_capabilities(context=cap_ctx)


        # Execute upstream doctor in isolated workspace WITHOUT --target
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
                capabilities_available=available_capabilities_count,
                browser_ready=browser_ready,
                warnings=[f"Engine doctor probe failed: {exc}"],
            )

        return CareerOpsDoctorResult(
            status=CareerOpsStatusEnum.READY,
            expected_identity=expected,
            actual_identity=actual_identity,
            runtime=runtime,
            upstream_onboarding=upstream_onboarding,
            capabilities_declared=len(declared),
            capabilities_available=available_capabilities_count,
            browser_ready=browser_ready,
            warnings=warnings,
        )
