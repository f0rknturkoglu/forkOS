"""Conservative source extraction: source claims, not independently verified history.

Verified means faithfully transcribed from the user's canonical document. No dates,
metrics or employment history are inferred. Paragraph/page locators survive tailoring.
"""

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.modules.opportunity.candidate_context import CandidateFact

SECTIONS = {
    "PROFESYONEL ÖZET": "summary",
    "PROFESSIONAL SUMMARY": "summary",
    "PROJELER": "projects",
    "PROJECTS": "projects",
    "DENEYİM": "employment",
    "EXPERIENCE": "employment",
    "EĞİTİM": "education",
    "EDUCATION": "education",
    "TEKNİK BECERİLER": "skills",
    "TECHNICAL SKILLS": "skills",
    "DİLLER": "languages",
    "LANGUAGES": "languages",
    "CERTIFICATIONS": "certifications",
    "SERTİFİKALAR": "certifications",
    "ACHIEVEMENTS": "achievements",
    "BAŞARILAR": "achievements",
}


def _extract_cv_evidence(path: Path, source_id: str) -> list[CandidateFact]:
    rows: list[tuple[str, str]] = []
    if path.suffix.lower() == ".docx":
        with zipfile.ZipFile(path) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        for index, para in enumerate(root.findall(".//w:p", ns), 1):
            text = "".join(t.text or "" for t in para.findall(".//w:t", ns)).strip()
            if text:
                rows.append((text, f"paragraph:{index}"))
    elif path.suffix.lower() == ".pdf":
        for page_index, page in enumerate(PdfReader(path).pages, 1):
            rows.extend(
                (line.strip(), f"page:{page_index}/line:{i}")
                for i, line in enumerate((page.extract_text() or "").splitlines(), 1)
                if line.strip()
            )
    else:
        return []
    section = "identity"
    facts = []
    for text, locator in rows:
        heading = SECTIONS.get(text.upper())
        if heading:
            section = heading
            continue
        value = {"section": section, "text": text}
        # Delimited source headers expose fields without inferring employers,
        # dates or duration. Bullet text is always retained verbatim.
        parts = [part.strip() for part in text.split("|")]
        if len(parts) >= 3 and section in ("employment", "education", "projects"):
            value.update({"title": parts[0], "organization": parts[1], "dates": parts[-1]})
        facts.append(
            CandidateFact(
                key=f"cv:{source_id}:{locator}",
                value=value,
                source_type="document",
                source_id=source_id,
                source_locator=f"{section}/{locator}",
                verified=True,
                confidence=1.0,
            )
        )
        if section == "skills" and ":" in text:
            for skill in re.split(r",\s*", text.split(":", 1)[1]):
                skill = skill.strip()
                if skill:
                    facts.append(
                        CandidateFact(
                            key=f"skill:{skill.lower()}",
                            value=skill,
                            source_type="document",
                            source_id=source_id,
                            source_locator=locator,
                            verified=True,
                        )
                    )
    return facts


def extract_cv_evidence(path: Path, source_id: str) -> list[CandidateFact]:
    try:
        return _extract_cv_evidence(path, source_id)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError, PyPdfError):
        return []
