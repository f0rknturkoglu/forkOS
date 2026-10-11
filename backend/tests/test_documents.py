from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from app.modules.document import service


@pytest.mark.no_database
def test_extract_local_candidate_text_from_plain_text_and_docx(tmp_path: Path):
    plain = tmp_path / "cv.txt"
    plain.write_text("Python ve Kubernetes deneyimi", encoding="utf-8")
    assert service.extract_local_document_text(plain) == "Python ve Kubernetes deneyimi"

    docx = tmp_path / "cv.docx"
    with zipfile.ZipFile(docx, "w") as archive:
        archive.writestr(
            "word/document.xml",
            "<w:document><w:body><w:p><w:r><w:t>Terraform</w:t></w:r></w:p>"
            "<w:p><w:r><w:t>Azure platform</w:t></w:r></w:p></w:body></w:document>",
        )
    extracted = service.extract_local_document_text(docx)
    assert extracted is not None
    assert "Terraform" in extracted
    assert "Azure platform" in extracted
