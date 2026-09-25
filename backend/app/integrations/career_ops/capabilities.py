"""Semantic capability registry for career-ops integration."""

from app.integrations.career_ops.models import CapabilityStatus, CareerOpsCapability

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
    enabled: bool,
    runtime_ready: bool,
) -> CapabilityStatus:
    if not enabled:
        return CapabilityStatus.DISABLED
    if not runtime_ready:
        return CapabilityStatus.UNAVAILABLE
    # In C1, only foundation doctor capability is currently active.
    # C2 introduces discovery, C3 evaluation, C4 application/interview, C5 generation.
    if capability_id == "foundation.doctor":
        return CapabilityStatus.SUPPORTED
    return CapabilityStatus.UNAVAILABLE
