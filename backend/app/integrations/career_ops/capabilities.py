"""Semantic capability registry for career-ops integration."""

from app.integrations.career_ops.models import (
    CapabilityStatus,
    CareerOpsCapability,
    CareerOpsCapabilityContext,
)

ALL_CAPABILITIES: tuple[CareerOpsCapability, ...] = (
    CareerOpsCapability(
        id="foundation.doctor",
        domain="foundation",
        name="Doctor & Diagnostic Probe",
        description="Verify engine identity, runtime readiness, and configuration.",
    ),
    CareerOpsCapability(
        id="discovery.scan",
        domain="discovery",
        name="Job Discovery Scan",
        description="Scan ATS APIs and RSS/JSON job portals without authentication.",
    ),
    CareerOpsCapability(
        id="discovery.reverse_ats",
        domain="discovery",
        name="Mass Reverse ATS Sweep",
        description="Discover unindexed openings across target ATS platforms.",
    ),
    CareerOpsCapability(
        id="discovery.liveness",
        domain="discovery",
        name="Posting Liveness Verification",
        description="Zero-token verification that job postings remain open.",
    ),
    CareerOpsCapability(
        id="job.extract",
        domain="job",
        name="Job Description Extraction",
        description="Extract structured posting content via browser / readability.",
    ),
    CareerOpsCapability(
        id="job.repost_analysis",
        domain="job",
        name="Repost Detection",
        description="Detect reposted and duplicate vacancies across boards.",
    ),
    CareerOpsCapability(
        id="job.legitimacy",
        domain="job",
        name="Posting Legitimacy & Risk Signals",
        description="Detect phantom jobs, agency scrapers, and high-risk signals.",
    ),
    CareerOpsCapability(
        id="evaluation.deep",
        domain="evaluation",
        name="Structured A-H Evaluation",
        description="Generate comprehensive multidimensional fit reports.",
    ),
    CareerOpsCapability(
        id="evaluation.requirements",
        domain="evaluation",
        name="Hard Requirement Extraction",
        description="Extract required skills, experience floor, and tech stack.",
    ),
    CareerOpsCapability(
        id="evaluation.compensation",
        domain="evaluation",
        name="Compensation Analysis",
        description="Extract and benchmark salary and equity offerings.",
    ),
    CareerOpsCapability(
        id="evaluation.work_authorization",
        domain="evaluation",
        name="Work Authorization & Visa Fit",
        description="Verify visa sponsorship and geographic eligibility.",
    ),
    CareerOpsCapability(
        id="cv.tailor",
        domain="cv",
        name="Targeted CV Tailoring",
        description="Tailor resume bullets to job requirements while preserving facts.",
    ),
    CareerOpsCapability(
        id="cv.verify_facts",
        domain="cv",
        name="CV Fact Checking",
        description="Ensure generated CV statements strictly match user career truth.",
    ),
    CareerOpsCapability(
        id="cv.render_pdf",
        domain="cv",
        name="PDF Rendering",
        description="Render pixel-perfect ATS-safe PDF documents.",
    ),
    CareerOpsCapability(
        id="cv.render_latex",
        domain="cv",
        name="LaTeX Compilation",
        description="Compile structured LaTeX CV templates into PDF.",
    ),
    CareerOpsCapability(
        id="cv.visual_validate",
        domain="cv",
        name="Visual Validation",
        description="Verify CV visual layout and pagination via Playwright.",
    ),
    CareerOpsCapability(
        id="application.cover_letter",
        domain="application",
        name="Cover Letter Generation",
        description="Generate contextual cover letters matched to company tone.",
    ),
    CareerOpsCapability(
        id="application.answers",
        domain="application",
        name="Application Question Answering",
        description="Synthesize answers for bespoke ATS application forms.",
    ),
    CareerOpsCapability(
        id="application.prefill",
        domain="application",
        name="Form Prefill Payload",
        description="Generate structured autofill payloads for job applications.",
    ),
    CareerOpsCapability(
        id="interview.prepare",
        domain="interview",
        name="Interview Preparation Brief",
        description="Synthesize company research and expected interview questions.",
    ),
    CareerOpsCapability(
        id="interview.practice",
        domain="interview",
        name="Mock Interview Simulation",
        description="Interactive technical and behavioral interview simulation.",
    ),
    CareerOpsCapability(
        id="interview.debrief",
        domain="interview",
        name="Post-Interview Debrief",
        description="Extract lessons, questions asked, and STAR updates after interview.",
    ),
    CareerOpsCapability(
        id="analytics.funnel",
        domain="analytics",
        name="Funnel Velocity Analysis",
        description="Measure conversion and velocity across application stages.",
    ),
    CareerOpsCapability(
        id="analytics.rejection_patterns",
        domain="analytics",
        name="Rejection Pattern Analysis",
        description="Identify systemic failure points in CV or interview loops.",
    ),
    CareerOpsCapability(
        id="analytics.skill_gap",
        domain="analytics",
        name="Skill Gap Analysis",
        description="Highlight missing requirements across target opportunity clusters.",
    ),
    CareerOpsCapability(
        id="analytics.calibration",
        domain="analytics",
        name="Market Calibration",
        description="Calibrate target compensation and seniority against market reality.",
    ),
)


def get_declared_capabilities() -> tuple[CareerOpsCapability, ...]:
    return ALL_CAPABILITIES


def get_capability_status(
    capability_id: str,
    context: CareerOpsCapabilityContext | None = None,
    *,
    enabled: bool | None = None,
    runtime_ready: bool | None = None,
    discovery_enabled: bool | None = None,
    browser_ready: bool | None = None,
) -> CapabilityStatus:
    if context is None:
        context = CareerOpsCapabilityContext(
            enabled=enabled if enabled is not None else True,
            core_ready=runtime_ready if runtime_ready is not None else False,
            discovery_enabled=discovery_enabled if discovery_enabled is not None else True,
            browser_ready=browser_ready if browser_ready is not None else False,
        )

    if not context.enabled:
        return CapabilityStatus.DISABLED
    if not context.core_ready:
        return CapabilityStatus.UNAVAILABLE
    if capability_id == "foundation.doctor":
        return CapabilityStatus.SUPPORTED
    if capability_id == "discovery.reverse_ats":
        if not context.discovery_enabled:
            return CapabilityStatus.DISABLED
        return CapabilityStatus.SUPPORTED
    if capability_id == "job.repost_analysis":
        # Repost analysis is deterministic Node + TSV cluster analysis; does not require browser
        return CapabilityStatus.SUPPORTED
    if capability_id == "job.legitimacy":
        # Option A: Deterministic listing-health, transparency, and risk signals
        return CapabilityStatus.SUPPORTED
    if capability_id in ("discovery.liveness", "job.extract"):
        if context.browser_ready:
            return CapabilityStatus.SUPPORTED
        # Truthful degraded status: ATS API tier works without browser, generic browser fallback unavailable
        return CapabilityStatus.DEGRADED

    # C4 / C5: Career Intelligence & Application Production capabilities
    C4_C5_REASONER_CAPABILITIES = (
        "evaluation.deep",
        "evaluation.requirements",
        "evaluation.compensation",
        "evaluation.work_authorization",
        "cv.tailor",
        "cv.verify_facts",
        "application.cover",
        "application.answers",
        "application.package",
    )
    if capability_id in C4_C5_REASONER_CAPABILITIES:
        if getattr(context, "reasoner_available", False):
            return CapabilityStatus.SUPPORTED
        return CapabilityStatus.DEGRADED

    if capability_id == "cv.render_pdf":
        if context.browser_ready and getattr(context, "reasoner_available", False):
            return CapabilityStatus.SUPPORTED
        return CapabilityStatus.DEGRADED

    return CapabilityStatus.UNAVAILABLE


def count_available_capabilities(
    context: CareerOpsCapabilityContext | None = None,
    *,
    enabled: bool | None = None,
    runtime_ready: bool | None = None,
    discovery_enabled: bool | None = None,
    browser_ready: bool | None = None,
) -> int:
    if context is None:
        context = CareerOpsCapabilityContext(
            enabled=enabled if enabled is not None else True,
            core_ready=runtime_ready if runtime_ready is not None else False,
            discovery_enabled=discovery_enabled if discovery_enabled is not None else True,
            browser_ready=browser_ready if browser_ready is not None else False,
        )
    return sum(
        1
        for cap in ALL_CAPABILITIES
        if get_capability_status(cap.id, context=context) == CapabilityStatus.SUPPORTED
    )




def get_provider_capability_inventory() -> dict[str, dict[str, str]]:
    """Diagnostic inventory of the pinned career-ops provider universe (§40)."""
    return {
        "greenhouse": {
            "status": "supported",
            "protocol": "reverse_ats_json",
            "source_id": "careerops:greenhouse",
        },
        "lever": {
            "status": "supported",
            "protocol": "reverse_ats_json",
            "source_id": "careerops:lever",
        },
        "ashby": {
            "status": "supported",
            "protocol": "reverse_ats_json",
            "source_id": "careerops:ashby",
        },
        "workday": {
            "status": "supported",
            "protocol": "reverse_ats_json_multitenant",
            "source_id": "careerops:workday",
        },
        "icims": {
            "status": "supported",
            "protocol": "reverse_ats_json",
            "source_id": "careerops:icims",
        },
        "bamboohr": {
            "status": "supported",
            "protocol": "reverse_ats_json",
            "source_id": "careerops:bamboohr",
        },
        "curated_scan_lane": {
            "status": "deferred_contract_limitation",
            "protocol": "scan.mjs --json",
            "reason": "Machine receipt produces added_urls array only; lacks offer metadata for canonical ingestion",
        },
    }
