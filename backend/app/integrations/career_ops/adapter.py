import ipaddress
import json
import shutil
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.config import settings
from app.integrations.career_ops.capabilities import (
    get_capability_status,
    get_declared_capabilities,
)
from app.integrations.career_ops.doctor import CareerOpsDoctor
from app.integrations.career_ops.errors import (
    CareerOpsConfigurationError,
    CareerOpsExecutionError,
    CareerOpsInvalidOutputError,
    CareerOpsSecurityError,
    CareerOpsTimeoutError,
    CareerOpsUnavailableError,
)
from app.integrations.career_ops.guard import CareerOpsRuntimeGuard
from app.integrations.career_ops.job_identity import assess_extracted_job_identity
from app.integrations.career_ops.models import (
    CareerOpsCapability,
    CareerOpsCapabilityContext,
    CareerOpsDiscoveredJob,
    CareerOpsDiscoveryResult,
    CareerOpsDoctorResult,
    CareerOpsJobExtractionResult,
    CareerOpsLivenessReceipt,
    CareerOpsOfferReceipt,
    CareerOpsProviderInventory,
    CareerOpsProviderScanReceipt,
    CareerOpsRepostCluster,
    CareerOpsScanReceipt,
)
from app.integrations.career_ops.provider_targets import (
    build_provider_targets,
    project_provider_targets,
)
from app.integrations.career_ops.runner import CareerOpsRunner, SubprocessCareerOpsRunner
from app.integrations.career_ops.targeting import CareerOpsDiscoveryConfigBuilder

REVERSE_ATS_PROVIDERS: frozenset[str] = frozenset(
    {
        "greenhouse",
        "lever",
        "ashby",
        "workday",
        "icims",
        "bamboohr",
    }
)


def _is_safe_http_url(url: str) -> bool:
    """Validate that URL has safe http/https scheme, non-empty host, and is not private/loopback/cloud-metadata."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return False
        netloc = parsed.netloc.strip()
        if not netloc:
            return False
        hostname = (parsed.hostname or "").strip().lower()
        if not hostname:
            return False
        if hostname in ("localhost", "0.0.0.0", "metadata.google.internal"):
            return False
        if hostname.endswith((".local", ".internal", ".localhost")):
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
                or str(ip) == "0.0.0.0"
            ):
                return False
        except ValueError:
            pass
        return True
    except Exception:
        return False


class CareerOpsAdapter:
    def __init__(
        self,
        enabled: bool | None = None,
        checkout_dir: Path | None = None,
        runtime_dir: Path | None = None,
        node_bin: str | None = None,
        runner: CareerOpsRunner | None = None,
    ) -> None:
        self.enabled = enabled if enabled is not None else settings.career_ops_enabled
        self.checkout_dir = (
            checkout_dir.resolve()
            if checkout_dir is not None
            else settings.resolved_career_ops_root
        )
        self.runtime_dir = (
            runtime_dir.resolve()
            if runtime_dir is not None
            else settings.resolved_career_ops_runtime_dir
        )
        self.node_bin = node_bin if node_bin is not None else settings.career_ops_node_bin

        if runner is not None:
            self.runner = runner
        else:
            self.runner = SubprocessCareerOpsRunner(
                checkout_dir=self.checkout_dir,
                runtime_dir=self.runtime_dir,
                node_bin=self.node_bin,
                default_timeout_seconds=settings.career_ops_timeout_seconds,
                max_buffer_bytes=settings.career_ops_max_buffer_bytes,
            )

        self.guard = CareerOpsRuntimeGuard(
            enabled=self.enabled,
            checkout_dir=self.checkout_dir,
            node_bin=self.node_bin,
            discovery_enabled=settings.career_ops_discovery_enabled,
        )

        self._doctor = CareerOpsDoctor(
            enabled=self.enabled,
            checkout_dir=self.checkout_dir,
            runtime_dir=self.runtime_dir,
            runner=self.runner,
            node_bin=self.node_bin,
        )

    async def ensure_runtime_ready(self, required_script: str | None = None) -> None:
        self.guard.ensure_ready(required_script=required_script)

    async def doctor(self) -> CareerOpsDoctorResult:
        return await self._doctor.run_diagnostics()

    async def capabilities(self) -> list[CareerOpsCapability]:
        doc = await self.doctor()
        ctx = CareerOpsCapabilityContext(
            enabled=self.enabled,
            core_ready=doc.core_ready,
            discovery_enabled=settings.career_ops_discovery_enabled,
            browser_ready=doc.browser_ready,
            reasoner_status=doc.reasoner_status,
        )
        return [
            CareerOpsCapability(
                id=c.id,
                domain=c.domain,
                name=c.name,
                description=c.description,
                status=get_capability_status(c.id, context=ctx),
            )
            for c in get_declared_capabilities()
        ]

    async def provider_inventory(self) -> CareerOpsProviderInventory:
        self.guard.ensure_ready(required_script="scan.mjs")
        result = await self.runner.run_script("bridges/provider-scan.mjs", ["inventory"])
        if result.exit_code != 0:
            raise CareerOpsExecutionError(result.stderr.strip() or "Provider inventory failed")
        try:
            inventory = CareerOpsProviderInventory.model_validate_json(result.stdout)
        except Exception as exc:
            raise CareerOpsInvalidOutputError(f"Invalid provider inventory: {exc}") from exc
        ids = [provider.id for provider in inventory.providers]
        if len(ids) != len(set(ids)) or inventory.files != len(ids):
            raise CareerOpsInvalidOutputError("Provider registry has missing or duplicate modules")
        return inventory

    async def provider_scan(
        self,
        *,
        targets: dict[str, Any] | None = None,
        since_days: int | None = None,
    ) -> CareerOpsProviderScanReceipt:
        self.guard.ensure_ready(required_script="scan.mjs")
        if not settings.career_ops_discovery_enabled:
            raise CareerOpsConfigurationError("career-ops discovery capability is disabled")
        days = since_days or settings.career_ops_discovery_since_days
        if not 1 <= days <= 90:
            raise ValueError("since_days must be between 1 and 90")
        scan_targets = targets if targets is not None else build_provider_targets()
        for target in [
            *scan_targets.get("tracked_companies", []),
            *scan_targets.get("job_boards", []),
        ]:
            for key in ("careers_url", "api", "url"):
                value = target.get(key)
                if value is not None and (
                    not isinstance(value, str) or not _is_safe_http_url(value)
                ):
                    raise CareerOpsSecurityError(f"Unsafe provider target {key}")
        projection = project_provider_targets(
            self.runtime_dir,
            scan_targets,
            days,
        )
        try:
            result = await self.runner.run_script(
                "bridges/provider-scan.mjs",
                ["scan", str(projection)],
                timeout_seconds=settings.career_ops_discovery_timeout_seconds,
                max_buffer_bytes=settings.career_ops_discovery_max_buffer_bytes,
            )
        finally:
            projection.unlink(missing_ok=True)
        if result.exit_code != 0:
            raise CareerOpsExecutionError(result.stderr.strip() or "Provider scan failed")
        try:
            receipt = CareerOpsProviderScanReceipt.model_validate_json(result.stdout)
        except Exception as exc:
            raise CareerOpsInvalidOutputError(f"Invalid provider scan receipt: {exc}") from exc
        for offer in receipt.offers:
            if not _is_safe_http_url(offer.url):
                raise CareerOpsSecurityError(f"Unsafe provider offer URL: {offer.url}")
        return receipt

    async def reverse_scan(
        self,
        provider: str,
        *,
        since_days: int = 30,
        limit: int | None = 500,
        include_undated: bool = False,
        config_path: Path | None = None,
    ) -> CareerOpsDiscoveryResult:
        if not self.enabled:
            raise CareerOpsUnavailableError("career-ops integration is disabled")

        if not settings.career_ops_discovery_enabled:
            raise CareerOpsConfigurationError("career-ops discovery capability is disabled")

        # Identity and runtime readiness gate: fail-closed before any subprocess execution
        self.guard.ensure_ready(required_script="scan-ats-full.mjs")

        norm_provider = provider.strip().lower()
        if norm_provider not in REVERSE_ATS_PROVIDERS:
            raise CareerOpsSecurityError(
                f"Unknown or unallowlisted discovery provider '{provider}'. "
                f"Valid providers: {sorted(REVERSE_ATS_PROVIDERS)}"
            )

        if since_days < 1 or since_days > 90:
            raise ValueError("since_days must be between 1 and 90")

        if limit is not None and (limit < 1 or limit > 10000):
            raise ValueError("limit must be positive and at most 10000")

        # 1. Project targeting preferences to runtime portals.yml
        portals_path = CareerOpsDiscoveryConfigBuilder.project_to_runtime(
            self.runtime_dir,
            config_path=config_path,
        )

        # 2. Build safe command line arguments
        args = ["--json", "--dry-run", "--ats", norm_provider, "--since", str(since_days)]
        if limit is not None:
            args.extend(["--limit", str(limit)])
        if include_undated:
            args.append("--include-undated")

        # 3. Execute through runner with discovery timeout and buffer
        timeout = settings.career_ops_discovery_timeout_seconds
        if norm_provider == "workday":
            timeout = max(timeout, 600.0)
        max_buffer = settings.career_ops_discovery_max_buffer_bytes
        try:
            exec_res = await self.runner.run_script(
                "scan-ats-full.mjs",
                args,
                timeout_seconds=timeout,
                extra_env={"CAREER_OPS_PORTALS": str(portals_path)},
                max_buffer_bytes=max_buffer,
            )
        finally:
            portals_path.unlink(missing_ok=True)

        if exec_res.exit_code not in (0, 2):
            raise CareerOpsExecutionError(
                f"scan-ats-full.mjs exited with code {exec_res.exit_code}: {exec_res.stderr.strip() or exec_res.stdout.strip()}"
            )

        # 4. Parse stdout strictly as single JSON document (Finding H)
        raw_stdout = exec_res.stdout.strip()
        if not raw_stdout:
            raise CareerOpsInvalidOutputError(
                "scan-ats-full.mjs produced empty stdout in --json mode"
            )

        try:
            payload = json.loads(raw_stdout)
        except Exception as exc:
            raise CareerOpsInvalidOutputError(
                f"Strict JSON contract failed on scan-ats-full.mjs stdout: {exc}"
            ) from exc

        if not isinstance(payload, dict):
            raise CareerOpsInvalidOutputError(
                f"Expected JSON object from scan-ats-full.mjs, got {type(payload).__name__}"
            )

        try:
            receipt = CareerOpsScanReceipt.model_validate(payload)
        except Exception as exc:
            raise CareerOpsInvalidOutputError(
                f"Receipt validation failed against typed contract: {exc}"
            ) from exc

        # 5. Evaluate partial / degraded conditions (Finding F)
        cap_hit = bool(receipt.capHit)
        stopped_by_outage = bool(receipt.stoppedByOutage)
        dataset_status = receipt.datasetStatus or "ok"
        dataset_degraded = False
        if isinstance(dataset_status, dict):
            dataset_degraded = any(v != "ok" for v in dataset_status.values())
        elif isinstance(dataset_status, str) and dataset_status != "ok":
            dataset_degraded = True

        capped_boards = int(receipt.cappedBoards or 0)
        unreachable = int(receipt.unreachableBoards or 0)

        is_partial = False
        partial_reasons: list[str] = []
        if cap_hit:
            is_partial = True
            partial_reasons.append("scan reached configured cap")
        if capped_boards > 0:
            is_partial = True
            partial_reasons.append(f"{capped_boards} boards capped")
        if stopped_by_outage:
            is_partial = True
            partial_reasons.append("stopped by outage")
        if dataset_degraded:
            is_partial = True
            partial_reasons.append(f"dataset status degraded: {dataset_status}")
        if unreachable > 0 and unreachable > (receipt.companiesScanned or 0) * 0.5:
            is_partial = True
            partial_reasons.append(f"high unreachable boards count: {unreachable}")

        offers: list[CareerOpsDiscoveredJob] = []
        for raw_offer in receipt.offers:
            if not isinstance(raw_offer, dict):
                continue
            try:
                offer_receipt = CareerOpsOfferReceipt.model_validate(raw_offer)
            except Exception:
                # Malformed individual offer is quarantined/skipped while top-level receipt is valid
                continue

            c = offer_receipt.company.strip()
            t = offer_receipt.title.strip()
            u = offer_receipt.url.strip()
            if not c or not t or not u:
                continue

            # Finding G: URL boundary validation (http/https only)
            if not _is_safe_http_url(u):
                continue

            offers.append(
                CareerOpsDiscoveredJob(
                    company=c,
                    title=t,
                    url=u,
                    location=offer_receipt.location or None,
                    posted_at=offer_receipt.postedAt or None,
                    date_status=offer_receipt.dateStatus or "unknown",
                    blacklisted=bool(offer_receipt.blacklisted),
                    note=offer_receipt.note,
                    source=offer_receipt.source or norm_provider,
                    upstream_metadata={
                        k: v
                        for k, v in raw_offer.items()
                        if k
                        not in (
                            "company",
                            "title",
                            "url",
                            "location",
                            "postedAt",
                            "dateStatus",
                            "blacklisted",
                            "note",
                            "source",
                        )
                    },
                )
            )

        return CareerOpsDiscoveryResult(
            provider=norm_provider,
            date=str(receipt.date or ""),
            since_days=int(receipt.sinceDays or since_days),
            companies_available=int(receipt.companiesAvailable or 0),
            companies_scanned=int(receipt.companiesScanned or 0),
            cap_hit=cap_hit,
            stopped_by_outage=stopped_by_outage,
            dataset_status=dataset_status,
            unreachable_boards=unreachable,
            retired_boards_skipped=int(receipt.retiredBoardsSkipped or 0),
            postings_kept=len(offers),
            is_partial=is_partial,
            partial_detail="; ".join(partial_reasons) if is_partial else "",
            offers=offers,
        )

    async def check_liveness(
        self,
        url: str,
        timeout_ms: int = 15_000,
        no_fallback: bool = False,
    ) -> CareerOpsLivenessReceipt:
        """Verify URL liveness via zero-token ATS API first, then Playwright fallback."""
        if not self.enabled:
            raise CareerOpsUnavailableError("career-ops capability engine is disabled")

        # Identity and runtime readiness gate: fail-closed before any subprocess execution
        self.guard.ensure_ready(required_script="liveness-api.mjs")
        if not (self.checkout_dir / "liveness-browser.mjs").exists():
            raise CareerOpsUnavailableError(
                f"Required upstream script 'liveness-browser.mjs' missing from checkout at {self.checkout_dir}"
            )
        bridge_path = Path(__file__).parent / "bridges" / "liveness.mjs"
        if not bridge_path.exists():
            raise CareerOpsUnavailableError(
                f"Required bridge script 'bridges/liveness.mjs' missing at {bridge_path}"
            )

        if not _is_safe_http_url(url):
            return CareerOpsLivenessReceipt(
                url=url,
                status="uncertain",
                code="invalid_url",
                reason="URL scheme must be http or https, and cannot target private/local/metadata networks",
                method="bridge",
                checked_at=datetime.now(UTC).isoformat(),
            )

        args = [url, f"--timeout={timeout_ms}"]
        if no_fallback:
            args.append("--no-fallback")

        timeout_sec = (timeout_ms / 1000.0) + 5.0
        try:
            exec_res = await self.runner.run_script(
                "bridges/liveness.mjs",
                args,
                timeout_seconds=timeout_sec,
            )
        except CareerOpsTimeoutError:
            return CareerOpsLivenessReceipt(
                url=url,
                status="uncertain",
                code="timeout",
                reason="Liveness check timed out",
                method="bridge",
                checked_at=datetime.now(UTC).isoformat(),
            )
        except Exception as exc:
            return CareerOpsLivenessReceipt(
                url=url,
                status="uncertain",
                code="execution_error",
                reason=str(exc),
                method="bridge",
                checked_at=datetime.now(UTC).isoformat(),
            )

        try:
            payload = json.loads(exec_res.stdout)
            return CareerOpsLivenessReceipt.model_validate(payload)
        except Exception as exc:
            raise CareerOpsInvalidOutputError(
                f"Failed to parse JSON receipt from liveness bridge: {exc}"
            ) from exc

    async def extract_job(
        self,
        url: str,
        max_chars: int = 12_000,
        timeout_ms: int = 15_000,
    ) -> CareerOpsJobExtractionResult:
        """Extract job description text headlessly via browser-extract.mjs."""
        if not self.enabled:
            raise CareerOpsUnavailableError("career-ops capability engine is disabled")

        # Identity and runtime readiness gate: fail-closed before any subprocess execution
        self.guard.ensure_ready(required_script="browser-extract.mjs")

        if not _is_safe_http_url(url):
            return CareerOpsJobExtractionResult(
                url=url,
                error="Invalid URL (must be public http or https)",
                code="invalid_url",
            )

        args = [url, "--mode", "jd", "--max-chars", str(max_chars), "--timeout", str(timeout_ms)]
        timeout_sec = (timeout_ms / 1000.0) + 5.0

        try:
            exec_res = await self.runner.run_script(
                "browser-extract.mjs",
                args,
                timeout_seconds=timeout_sec,
            )
        except CareerOpsTimeoutError:
            return CareerOpsJobExtractionResult(
                url=url,
                requested_url=url,
                final_url=url,
                error="JD extraction timed out",
                code="timeout",
                extraction_status="error",
                job_identity_status="invalid_non_job",
                identity_reason="timeout",
            )
        except Exception as exc:
            return CareerOpsJobExtractionResult(
                url=url,
                requested_url=url,
                final_url=url,
                error=str(exc),
                code="execution_error",
                extraction_status="error",
                job_identity_status="invalid_non_job",
                identity_reason="execution_error",
            )

        if exec_res.exit_code != 0:
            err_msg = exec_res.stderr.strip() or exec_res.stdout.strip()
            err_code = "extraction_error"
            try:
                parsed_err = json.loads(err_msg)
                if isinstance(parsed_err, dict):
                    err_msg = parsed_err.get("error", err_msg)
                    err_code = parsed_err.get("code", err_code)
            except Exception:
                pass
            return CareerOpsJobExtractionResult(
                url=url,
                requested_url=url,
                final_url=url,
                error=err_msg,
                code=err_code,
                extraction_status="error",
                job_identity_status="invalid_non_job",
                identity_reason="extraction_error",
            )

        try:
            payload = json.loads(exec_res.stdout)
            final_url = payload.get("url") or url
            title = payload.get("title") or ""
            text = payload.get("text") or ""

            parsed_url = urlparse(final_url or url)
            host = (parsed_url.netloc or "").lower()
            if any(
                ats in host
                for ats in ("myworkdayjobs.com", "ashbyhq.com", "greenhouse.io", "lever.co")
            ):
                method = "ats_api"
            else:
                method = "browser"

            assessment = assess_extracted_job_identity(
                requested_url=url,
                final_url=final_url,
                title=title,
                text=text,
            )

            return CareerOpsJobExtractionResult(
                url=final_url,
                requested_url=url,
                final_url=final_url,
                title=title,
                text=text,
                extraction_status="success",
                method=method,
                job_identity_status=assessment.identity_status,
                identity_reason=assessment.reason,
                warnings=assessment.warnings,
            )
        except Exception as exc:
            raise CareerOpsInvalidOutputError(
                f"Failed to parse JSON from browser-extract.mjs: {exc}"
            ) from exc

    async def detect_reposts(
        self,
        rows: list[dict[str, Any]],
        window_days: int = 90,
        min_span_days: int = 1,
    ) -> list[CareerOpsRepostCluster]:
        """Detect repost clusters from ephemeral scan history projection."""
        if not self.enabled:
            raise CareerOpsUnavailableError("career-ops capability engine is disabled")

        # Identity and runtime readiness gate: fail-closed before creating projection or subprocess
        self.guard.ensure_ready(required_script="detect-reposts.mjs")

        scratch_id = uuid.uuid4().hex[:12]
        scratch_dir = self.runtime_dir / "repost_scratch" / scratch_id
        tsv_dir = scratch_dir / "data"
        tsv_dir.mkdir(parents=True, exist_ok=True)
        tsv_path = tsv_dir / "scan-history.tsv"

        lines = ["url\tfirst_seen\tportal\ttitle\tcompany\tstatus\tlocation"]
        for r in rows:
            u = str(r.get("url") or "").replace("\t", " ").strip()
            d = str(r.get("first_seen") or r.get("date") or "").replace("\t", " ").strip()
            p = str(r.get("portal") or "forkos").replace("\t", " ").strip()
            t = str(r.get("title") or "").replace("\t", " ").strip()
            c = str(r.get("company") or r.get("organization") or "").replace("\t", " ").strip()
            s = str(r.get("status") or "added").replace("\t", " ").strip()
            loc = str(r.get("location") or "").replace("\t", " ").strip()
            if u and d and t and c:
                lines.append(f"{u}\t{d}\t{p}\t{t}\t{c}\t{s}\t{loc}")

        tsv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        try:
            exec_res = await self.runner.run_script(
                "detect-reposts.mjs",
                ["--window", str(window_days), "--min-span", str(min_span_days)],
                extra_env={"CAREER_OPS_ROOT": str(scratch_dir)},
                timeout_seconds=30.0,
            )
            if exec_res.exit_code != 0:
                raise CareerOpsExecutionError(
                    f"detect-reposts.mjs failed with exit code {exec_res.exit_code}: {exec_res.stderr}"
                )

            payload = json.loads(exec_res.stdout)
            clusters_raw = payload.get("clusters") or []
            return [CareerOpsRepostCluster.model_validate(c) for c in clusters_raw]
        finally:
            if scratch_dir.exists():
                shutil.rmtree(scratch_dir, ignore_errors=True)
            parent_scratch = self.runtime_dir / "repost_scratch"
            if parent_scratch.exists() and not any(parent_scratch.iterdir()):
                with suppress(OSError):
                    parent_scratch.rmdir()
