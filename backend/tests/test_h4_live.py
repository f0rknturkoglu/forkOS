"""H4 canlı yerel model testleri — VARSAYILAN OLARAK ATLANIR.

Çalıştırmak için:

```bash
H4_LIVE=1 H4_ENABLED=true H4_SMALL_MODEL=<model> \\
  backend/.venv/bin/python -m pytest backend/tests/test_h4_live.py -q
```

Normal CI model İNDİRMEZ ve yerel model GEREKTİRMEZ: bu dosya yalnızca açık
bayrak + yapılandırılmış model varsa koşar, aksi hâlde temiz biçimde atlar.
"""

from __future__ import annotations

import os

import pytest

from app.config import settings
from app.integrations.local_cognition import models as lc
from app.integrations.local_cognition import service as lc_svc
from app.integrations.local_cognition.ollama import OllamaProvider

pytestmark = pytest.mark.h4_live

CALENDAR_TEXT = (
    "Kayıt yenileme: 1 - 5 Eylül 2026\n"
    "Derslerin başlangıcı: 21 Eylül 2026\n"
)


def _skip_reason() -> str | None:
    if os.environ.get("H4_LIVE") != "1":
        return "H4_LIVE is not set to 1"
    if not settings.h4_enabled:
        return "H4_ENABLED is not true"
    if not settings.h4_small_model and not settings.h4_medium_model:
        return "no local model is configured (H4_SMALL_MODEL/H4_MEDIUM_MODEL)"
    return None


@pytest.fixture(autouse=True)
async def _require_live_runtime() -> None:
    reason = _skip_reason()
    if reason:
        pytest.skip(reason)
    provider = OllamaProvider(
        settings.h4_ollama_base_url, timeout_seconds=settings.h4_timeout_seconds
    )
    model_id = settings.h4_small_model or settings.h4_medium_model
    health = await provider.health(model_id)
    if not health.provider_reachable:
        pytest.skip("local model provider is not reachable")
    if not health.model_available:
        pytest.skip(f"configured model is not installed: {model_id}")


async def test_live_classify() -> None:
    request = lc.build_lane_request(
        lane="classify",
        text="29 Kasım ALES sınavı var.",
        labels=["calendar_event", "deadline", "task", "knowledge"],
        classification_goal="Metni en uygun kategoriye ata.",
    )
    response = await lc_svc.run_local_cognition(request)
    assert response.status == "success", response.failure_code
    assert response.result.label in request.labels


async def test_live_academic_calendar_extraction() -> None:
    request = lc.build_lane_request(
        lane="structured_extract", text=CALENDAR_TEXT, contract="academic_calendar_v1"
    )
    response = await lc_svc.run_local_cognition(request)
    assert response.status == "success", response.failure_code
    assert response.result.items, "expected at least one validated event"
    for item in response.result.items:
        assert item["source_excerpt"]


async def test_live_query_rewrite() -> None:
    request = lc.build_lane_request(
        lane="query_rewrite",
        text="forkjobda rustu neden seçtik",
        protected_terms=["forkjob", "Rust"],
    )
    response = await lc_svc.run_local_cognition(request)
    assert response.status == "success", response.failure_code
    rewrite = response.result.rewritten_query
    assert "forkjob" in rewrite and "Rust" in rewrite
    assert len(rewrite) <= lc.MAX_REWRITE_CHARS
