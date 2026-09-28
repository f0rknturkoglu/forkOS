"""Local, escaped source artifacts and conservative material-claim gate."""

import html
import re

from app.modules.opportunity.candidate_context import CandidateCareerContext
from app.modules.opportunity.reasoner.base import TailoredCvDraft


def _leaves(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key not in {"evidence_refs", "candidate_fact_ref"}:
                yield from _leaves(item)
    elif isinstance(value, list):
        for item in value:
            yield from _leaves(item)
    elif isinstance(value, str) and value.strip():
        yield value


def verify_material_claims(draft: TailoredCvDraft, context: CandidateCareerContext) -> bool:
    def normalize(text):
        return re.sub(r"\s+", " ", text).casefold().strip()

    for field, sections in (
        ("summary", {"summary"}),
        ("experience", {"employment"}),
        ("projects", {"projects"}),
        ("languages", {"languages"}),
        ("education", {"education"}),
    ):
        corpus = normalize(
            " ".join(
                text
                for fact in context.facts
                if fact.verified
                and fact.source_type == "document"
                and isinstance(fact.value, dict)
                and fact.value.get("section") in sections
                for text in _leaves(fact.value)
            )
        )
        if not all(normalize(claim) in corpus for claim in _leaves(getattr(draft, field))):
            return False
    return all(context.has_verified_skill(skill) for skill in draft.skills)


def build_cv_html(draft: TailoredCvDraft, context: CandidateCareerContext | None = None) -> str:
    sections = [
        ("Summary", draft.summary),
        ("Projects", draft.projects),
        ("Experience", draft.experience),
        ("Education", draft.education),
        ("Skills", ", ".join(draft.skills)),
        ("Languages", draft.languages),
    ]
    identity = "".join(
        f"<p>{html.escape(f.value['text'])}</p>"
        for f in (context.facts if context else [])
        if isinstance(f.value, dict) and f.value.get("section") == "identity"
    )
    body = identity + "".join(
        f"<section><h2>{title}</h2>"
        + "".join(f"<p>{html.escape(text)}</p>" for text in _leaves(value))
        + "</section>"
        for title, value in sections
    )
    style = "<style>body{font-family:sans-serif;font-size:10pt;line-height:1.35}h2{font-size:13pt;break-after:avoid;margin:12pt 0 5pt}p{margin:0 0 5pt;orphans:3;widows:3}</style>"
    return (
        '<!doctype html><html><meta charset="utf-8"><title>Tailored CV</title>'
        + style
        + "<body>"
        + body
        + "</body></html>"
    )


async def render_cv_pdf(source: str) -> tuple[bytes | None, dict]:
    """Optional pinned renderer; no installation, downloads, remote resources or fallback."""
    import io
    import tempfile
    from pathlib import Path

    from pypdf import PdfReader

    from app.config import settings
    from app.integrations.career_ops.guard import CareerOpsRuntimeGuard
    from app.integrations.career_ops.runner import SubprocessCareerOpsRunner

    if not settings.career_ops_enabled:
        return None, {
            "status": "unavailable",
            "reason": "career_ops_disabled",
            "visual": "unavailable",
        }
    root = settings.resolved_career_ops_root
    guard = CareerOpsRuntimeGuard(True, root, settings.career_ops_node_bin)
    identity, error = guard.get_actual_identity()
    if error or identity != guard.expected_identity():
        return None, {
            "status": "unavailable",
            "reason": "pinned_identity_unavailable",
            "visual": "unavailable",
        }
    try:
        with tempfile.TemporaryDirectory(prefix="forkos-cv-render-") as directory:
            workspace = Path(directory).resolve()
            html_path = workspace / "cv.html"
            pdf_path = workspace / "cv.pdf"
            html_path.write_text(source, encoding="utf-8")
            runner = SubprocessCareerOpsRunner(root, workspace, settings.career_ops_node_bin)
            result = await runner.run_script(
                "bridges/render.mjs", [str(html_path), str(pdf_path)], timeout_seconds=45
            )
            if result.exit_code != 0:
                return None, {
                    "status": "failed",
                    "reason": "local_renderer_exit",
                    "visual": "unavailable",
                }
            content = pdf_path.read_bytes()
            reader = PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            valid = (
                content.startswith(b"%PDF")
                and 1 <= len(reader.pages) <= 3
                and all(title in text for title in ("Summary", "Experience", "Education", "Skills"))
            )
            if not valid:
                return None, {
                    "status": "failed",
                    "reason": "pdf_content_validation",
                    "visual": "unavailable",
                }
            positions = [
                text.find(title) for title in ("Summary", "Experience", "Education", "Skills")
            ]
            if positions != sorted(positions) or min(positions) < 0:
                return None, {
                    "status": "failed",
                    "reason": "pdf_read_order",
                    "visual": "unavailable",
                    "read_order": "failed",
                }
            return content, {
                "status": "passed",
                "pages": len(reader.pages),
                "extractable_chars": len(text),
                "visual": "unavailable",
                "read_order": "passed"
                if positions == sorted(positions) and min(positions) >= 0
                else "needs_review",
                "read_order_check": "major_section_sequence",
            }
    except Exception:
        return None, {
            "status": "failed",
            "reason": "local_renderer_failure",
            "visual": "unavailable",
        }
