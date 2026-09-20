"""H4 servis orkestrasyonu: doğrulama, sınırlı tekrar, yukarı çıkış, sonuç.

Sağlayıcı BETİKLİDİR: Ollama gerekmez, ağ kullanılmaz, sonuç deterministiktir.
"""

from __future__ import annotations

import inspect
import json

import pytest
from sqlalchemy import func, select

from app.config import settings
from app.core.models import Entity, Event, Link
from app.db import SessionLocal
from app.integrations.local_cognition import models as lc
from app.integrations.local_cognition import service as lc_svc
from app.integrations.local_cognition.policy import ModelHealth, ModelProfile
from tests.agent_test_utils import capture_db_content_fingerprint, table_counts
from tests.h4_test_provider import HEALTHY, MODEL_MISSING, ScriptedProvider

CAPABILITIES = frozenset({"classify", "structured_extract", "query_rewrite", "structured_output"})

CALENDAR_TEXT = (
    "2026-2027 Güz Dönemi Akademik Takvim\n"
    "Kayıt yenileme: 1 - 5 Eylül 2026\n"
    "Derslerin başlangıcı: 21 Eylül 2026\n"
    "Ara sınav haftası: 14 - 22 Kasım 2026\n"
    "Yarıyıl tatili: 25 Ocak - 5 Şubat 2027\n"
)
SCHEDULE_TEXT = (
    "Pazartesi 09:00-11:00 Veri Yapıları\n"
    "Çarşamba 14:00-16:00 İngilizce\n"
)
DEADLINE_TEXT = "Başvuru son tarihi: 30 Eylül 2026\nTeslim: 12 Ekim 2026 23:00\n"
REWRITE_TEXT = "forkjobda rustu neden seçtik"


@pytest.fixture
def h4_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "h4_enabled", True)


def _profiles(small: str = "small-model", medium: str = "medium-model") -> dict[str, ModelProfile]:
    return {
        "local-small": ModelProfile(
            slot="local-small", provider="ollama", model_id=small,
            execution_boundary="local_loopback", max_input_chars=12000, capabilities=CAPABILITIES,
        ),
        "local-medium": ModelProfile(
            slot="local-medium", provider="ollama", model_id=medium,
            execution_boundary="local_loopback", max_input_chars=24000, capabilities=CAPABILITIES,
        ),
    }


def _health(small: ModelHealth = HEALTHY, medium: ModelHealth = HEALTHY) -> dict[str, ModelHealth]:
    return {"local-small": small, "local-medium": medium}


async def _run(request, provider, *, profiles=None, health=None):
    """Sağlık SNAPSHOT'ı enjekte edilir: yönlendirme deterministik ölçülür."""
    return await lc_svc.run_local_cognition(
        request,
        provider_factory=lambda: provider,
        profiles=profiles if profiles is not None else _profiles(),
        health_snapshot=health if health is not None else _health(),
    )


async def _run_with_probe(request, provider, *, profiles=None):
    """Snapshot ENJEKTE EDİLMEZ: gerçek sağlık probu çalışır (§41).

    Sağlayıcı düşmesi bu yolda ölçülür; aksi hâlde prob hiç çağrılmaz.
    """
    return await lc_svc.run_local_cognition(
        request,
        provider_factory=lambda: provider,
        profiles=profiles if profiles is not None else _profiles(),
    )


def _classify_request() -> lc.LaneRequest:
    return lc.build_lane_request(
        lane="classify",
        text="29 Kasım ALES sınavı var.",
        labels=["calendar_event", "deadline", "task", "knowledge"],
        classification_goal="Metni en uygun kategoriye ata.",
    )


def _extract_request() -> lc.LaneRequest:
    return lc.build_lane_request(
        lane="structured_extract", text=CALENDAR_TEXT, contract="academic_calendar_v1"
    )


def _rewrite_request() -> lc.LaneRequest:
    return lc.build_lane_request(
        lane="query_rewrite", text=REWRITE_TEXT, protected_terms=["forkjob", "Rust"]
    )


def _calendar_payload() -> str:
    return json.dumps(
        {
            "events": [
                {
                    "title": "Kayıt yenileme",
                    "category": "registration",
                    "date_text": "1 - 5 Eylül 2026",
                    "start_date": "2026-09-01",
                    "end_date": "2026-09-05",
                    "source_excerpt": "Kayıt yenileme: 1 - 5 Eylül 2026",
                },
                {
                    "title": "Ara sınav haftası",
                    "category": "exam",
                    "date_text": "14 - 22 Kasım 2026",
                    "start_date": None,
                    "end_date": None,
                    "source_excerpt": "Ara sınav haftası: 14 - 22 Kasım 2026",
                },
            ]
        }
    )


# ---------------------------------------------------------------------------
# Mutlu yol ve doğrulama
# ---------------------------------------------------------------------------


async def test_classify_succeeds_on_first_attempt(h4_on: None) -> None:
    provider = ScriptedProvider(responses=['{"label": "deadline"}'])
    response = await _run(_classify_request(), provider)

    assert response.status == "success"
    assert isinstance(response.result, lc.ClassificationResult)
    assert response.result.label == "deadline"
    assert provider.call_count == 1
    assert response.route_decision.attempts[0].slot == "local-small"
    assert response.route_decision.validation_status == "valid"
    assert response.route_decision.execution_boundary == "local_loopback"


async def test_classify_rejects_label_outside_supplied_set(h4_on: None) -> None:
    """Etiket doğrulaması: model yalnızca SAĞLANAN etiketlerden birini dönebilir."""
    provider = ScriptedProvider(
        responses=['{"label": "uydurma"}', '{"label": "task"}']
    )
    response = await _run(_classify_request(), provider)

    assert response.status == "success"
    assert response.result.label == "task"
    assert response.route_decision.attempts[0].failure_code == "INVALID_CLASS_LABEL"
    assert provider.call_count == 2


async def test_academic_calendar_extraction_is_validated(h4_on: None) -> None:
    provider = ScriptedProvider(responses=[_calendar_payload()])
    response = await _run(_extract_request(), provider)

    assert response.status == "success"
    assert isinstance(response.result, lc.ExtractionResult)
    assert response.result.contract == "academic_calendar_v1"
    assert [item["category"] for item in response.result.items] == ["registration", "exam"]
    # Tarih uydurulmaz: kaynak desteklemiyorsa null kalır (§34).
    assert response.result.items[1]["start_date"] is None


async def test_extraction_with_invented_excerpt_is_rejected(h4_on: None) -> None:
    payload = json.dumps(
        {
            "events": [
                {
                    "title": "Uydurma",
                    "category": "exam",
                    "date_text": "1 Ocak 2030",
                    "source_excerpt": "Bu metin kaynakta yok",
                }
            ]
        }
    )
    provider = ScriptedProvider(responses=[payload, payload, payload])
    response = await _run(_extract_request(), provider)

    assert response.status == "needs_escalation"
    assert all(
        attempt.failure_code == "SOURCE_EXCERPT_NOT_FOUND"
        for attempt in response.route_decision.attempts
    )


async def test_schedule_validation_rejects_invalid_and_reversed_times(h4_on: None) -> None:
    bad_hour = json.dumps(
        {
            "blocks": [
                {
                    "title": "Gece",
                    "day_of_week": "tuesday",
                    "start_time": "25:00",
                    "end_time": "26:30",
                    "source_excerpt": "Salı 25:00 - 26:30 Gece",
                }
            ]
        }
    )
    reversed_time = json.dumps(
        {
            "blocks": [
                {
                    "title": "Okuma",
                    "day_of_week": "monday",
                    "start_time": "16:00",
                    "end_time": "14:00",
                    "source_excerpt": "Pazartesi 16:00 - 14:00 Okuma",
                }
            ]
        }
    )
    request = lc.build_lane_request(
        lane="structured_extract",
        text="Salı 25:00 - 26:30 Gece\nPazartesi 16:00 - 14:00 Okuma",
        contract="weekly_schedule_v1",
    )

    first = await _run(request, ScriptedProvider(responses=[bad_hour, bad_hour, bad_hour]))
    assert first.status == "needs_escalation"
    assert first.route_decision.attempts[0].failure_code == "INVALID_TIME"

    second = await _run(request, ScriptedProvider(responses=[reversed_time, reversed_time, reversed_time]))
    assert second.status == "needs_escalation"
    assert second.route_decision.attempts[0].failure_code == "INVALID_TIME"


async def test_deadline_extraction_keeps_ambiguous_date_null(h4_on: None) -> None:
    payload = json.dumps(
        {
            "deadlines": [
                {
                    "title": "Başvuru",
                    "kind": "application",
                    "date_text": "30 Eylül 2026",
                    "due_date": "2026-09-30",
                    "due_time": None,
                    "source_excerpt": "Başvuru son tarihi: 30 Eylül 2026",
                },
                {
                    "title": "Teslim",
                    "kind": "submission",
                    "date_text": "12 Ekim 2026 23:00",
                    "due_date": None,
                    "due_time": None,
                    "source_excerpt": "Teslim: 12 Ekim 2026 23:00",
                },
            ]
        }
    )
    request = lc.build_lane_request(
        lane="structured_extract", text=DEADLINE_TEXT, contract="deadline_candidates_v1"
    )
    response = await _run(request, ScriptedProvider(responses=[payload]))

    assert response.status == "success"
    assert [item["kind"] for item in response.result.items] == ["application", "submission"]
    assert response.result.items[1]["due_date"] is None


async def test_query_rewrite_keeps_protected_terms(h4_on: None) -> None:
    provider = ScriptedProvider(
        responses=['{"rewritten_query": "forkjob Rust mimari kararı gerekçesi"}']
    )
    response = await _run(_rewrite_request(), provider)

    assert response.status == "success"
    assert response.result.rewritten_query.startswith("forkjob Rust")
    assert len(response.result.rewritten_query) <= lc.MAX_REWRITE_CHARS


async def test_query_rewrite_fails_when_protected_term_is_lost(h4_on: None) -> None:
    lost = '{"rewritten_query": "architecture decision rationale notes"}'
    provider = ScriptedProvider(responses=[lost, lost, lost])
    response = await _run(_rewrite_request(), provider)

    assert response.status == "needs_escalation"
    assert response.route_decision.attempts[0].failure_code == "PROTECTED_TERM_LOST"
    assert response.failure_code == "LOCAL_CAPABILITY_UNAVAILABLE"


async def test_query_rewrite_output_bound_is_enforced(h4_on: None) -> None:
    too_long = json.dumps({"rewritten_query": "x" * (lc.MAX_REWRITE_CHARS + 1)})
    provider = ScriptedProvider(responses=[too_long, too_long, too_long])
    response = await _run(_rewrite_request(), provider)

    assert response.status == "needs_escalation"
    assert response.route_decision.attempts[0].failure_code == "OUTPUT_TOO_LARGE"


async def test_empty_model_output_is_a_validation_failure(h4_on: None) -> None:
    provider = ScriptedProvider(script="empty_output")
    response = await _run(_classify_request(), provider)

    assert response.status == "needs_escalation"
    assert response.route_decision.attempts[0].failure_code == "INVALID_MODEL_JSON"


# ---------------------------------------------------------------------------
# Tekrar ve yukarı çıkış (§71-§74/§122/§162-§164)
# ---------------------------------------------------------------------------


async def test_small_retry_succeeds_without_touching_medium(h4_on: None) -> None:
    provider = ScriptedProvider(
        responses=['{"label": "uydurma"}', '{"label": "task"}']
    )
    response = await _run(_classify_request(), provider)

    assert response.status == "success"
    assert len(response.route_decision.attempts) == 2
    assert [attempt.slot for attempt in response.route_decision.attempts] == [
        "local-small",
        "local-small",
    ]
    assert provider.call_count == 2
    assert "LOCAL_SMALL_VALIDATION_FAILED" in response.route_decision.reason_codes
    assert "ESCALATED_TO_LOCAL_MEDIUM" not in response.route_decision.reason_codes


async def test_small_exhausted_then_medium_succeeds(h4_on: None) -> None:
    """§163: small, small, medium — ve ASLA small'a geri dönülmez."""
    provider = ScriptedProvider(
        responses=['{"label": "u1"}', '{"label": "u2"}', '{"label": "knowledge"}']
    )
    response = await _run(_classify_request(), provider)

    assert response.status == "success"
    assert [attempt.slot for attempt in response.route_decision.attempts] == [
        "local-small",
        "local-small",
        "local-medium",
    ]
    assert provider.call_count == 3
    assert response.route_decision.escalated is True
    assert "ESCALATED_TO_LOCAL_MEDIUM" in response.route_decision.reason_codes


async def test_complete_local_failure_needs_escalation(h4_on: None) -> None:
    """§164: iki slot da düşerse `needs_escalation`; uzak model ÇAĞRILMAZ."""
    provider = ScriptedProvider(
        responses=['{"label": "u1"}', '{"label": "u2"}', '{"label": "u3"}']
    )
    response = await _run(_classify_request(), provider)

    assert response.status == "needs_escalation"
    assert response.result is None
    assert response.failure_code == "LOCAL_CAPABILITY_UNAVAILABLE"
    assert provider.call_count <= lc.MAX_TOTAL_ATTEMPTS
    assert response.recovery_hint is not None


async def test_single_slot_exhaustion_reports_validation_failed(h4_on: None) -> None:
    provider = ScriptedProvider(responses=['{"label": "u1"}', '{"label": "u2"}'])
    response = await _run(
        _classify_request(),
        provider,
        profiles=_profiles(medium=""),
        health=_health(HEALTHY, ModelHealth.unavailable(configured=False)),
    )

    assert response.status == "needs_escalation"
    assert response.failure_code == "VALIDATION_FAILED"
    assert provider.call_count == 2


async def test_model_calls_never_exceed_the_total_budget(h4_on: None) -> None:
    provider = ScriptedProvider(script="malformed_json")
    response = await _run(_classify_request(), provider)

    assert provider.call_count == lc.MAX_TOTAL_ATTEMPTS
    assert len(response.route_decision.attempts) == lc.MAX_TOTAL_ATTEMPTS


# ---------------------------------------------------------------------------
# Sağlayıcı düzeyinde bozulmalar (§167)
# ---------------------------------------------------------------------------


async def test_provider_timeout_does_not_retry_forever(h4_on: None) -> None:
    provider = ScriptedProvider(script="timeout")
    response = await _run(_classify_request(), provider)

    assert response.status == "needs_escalation"
    assert response.failure_code == "MODEL_PROVIDER_UNAVAILABLE"
    assert provider.call_count == 1


async def test_health_snapshot_routes_around_a_missing_model(h4_on: None) -> None:
    """Sağlık probu modelin kurulu olmadığını görürse small UYGUN OLMAZ."""
    provider = ScriptedProvider(responses=['{"label": "task"}'])
    response = await _run(
        _classify_request(),
        provider,
        health=_health(MODEL_MISSING, HEALTHY),
    )

    assert response.status == "success"
    assert response.route_decision.selected_slot == "local-medium"
    assert provider.call_count == 1
    assert provider.calls[0].model_id == "medium-model"
    assert "LOCAL_SMALL_UNAVAILABLE" in response.route_decision.reason_codes


async def test_generation_time_model_unavailable_escalates_once(h4_on: None) -> None:
    """Üretim anında `MODEL_UNAVAILABLE` gelirse bir üst slota çıkılır."""
    provider = ScriptedProvider(script="model_missing")
    response = await _run(_classify_request(), provider)

    assert response.status == "needs_escalation"
    assert response.failure_code == "MODEL_UNAVAILABLE"
    assert [attempt.slot for attempt in response.route_decision.attempts] == [
        "local-small",
        "local-medium",
    ]
    assert provider.call_count == 2


# ---------------------------------------------------------------------------
# Yapılandırma ve sınır hataları
# ---------------------------------------------------------------------------


async def test_disabled_h4_returns_clean_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """§166: H4 kapalıyken araç yüzeyde kalır, yürütme temiz hata verir."""
    monkeypatch.setattr(settings, "h4_enabled", False)
    provider = ScriptedProvider(responses=['{"label": "task"}'])

    with pytest.raises(lc.H4Error, match="H4_DISABLED"):
        await _run(_classify_request(), provider)
    assert provider.call_count == 0


async def test_non_loopback_endpoint_is_rejected_before_any_call(
    h4_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§165: bulut adresi reddedilir ve HİÇBİR bağlantı denenmez."""
    monkeypatch.setattr(settings, "h4_ollama_base_url", "https://api.somecloud.com")
    provider = ScriptedProvider(responses=['{"label": "task"}'])

    with pytest.raises(lc.H4Error, match="INVALID_LOCAL_MODEL_ENDPOINT"):
        await _run(_classify_request(), provider)
    assert provider.call_count == 0


async def test_context_too_large_is_rejected(h4_on: None) -> None:
    """Metin şema sınırı içinde ama yapılandırılmış TÜM bütçeleri aşıyorsa."""
    request = lc.build_lane_request(lane="query_rewrite", text="x" * 2000, protected_terms=[])
    tiny = {
        "local-small": ModelProfile(
            slot="local-small", provider="ollama", model_id="small-model",
            execution_boundary="local_loopback", max_input_chars=500, capabilities=CAPABILITIES,
        ),
        "local-medium": ModelProfile(
            slot="local-medium", provider="ollama", model_id="medium-model",
            execution_boundary="local_loopback", max_input_chars=1000, capabilities=CAPABILITIES,
        ),
    }
    with pytest.raises(lc.H4Error, match="CONTEXT_TOO_LARGE"):
        await _run(request, ScriptedProvider(responses=["{}"]), profiles=tiny)


async def test_no_configured_model_is_rejected(h4_on: None) -> None:
    with pytest.raises(lc.H4Error, match="NO_ELIGIBLE_MODEL"):
        await _run(
            _classify_request(),
            ScriptedProvider(responses=["{}"]),
            profiles=_profiles(small="", medium=""),
            health=_health(ModelHealth.unavailable(configured=False), ModelHealth.unavailable(configured=False)),
        )


async def test_service_does_not_need_a_database_session() -> None:
    """§83: H4 yalnızca veritabanına ihtiyaç duyduğu için DB'ye DOKUNMAZ."""
    signature = inspect.signature(lc_svc.run_local_cognition)
    assert "session" not in signature.parameters
    assert set(signature.parameters) == {"request", "provider_factory", "profiles", "health_snapshot"}


# ---------------------------------------------------------------------------
# Değişmezlik (§82)
# ---------------------------------------------------------------------------


async def test_h4_writes_nothing_on_success_or_failure(h4_on: None) -> None:
    async with SessionLocal() as session:
        before = await capture_db_content_fingerprint(session)
        counts_before = await table_counts(session)
        events_before = (await session.execute(select(func.count(Event.id)))).scalar_one()

        await _run(_classify_request(), ScriptedProvider(responses=['{"label": "task"}']))
        await _run(_extract_request(), ScriptedProvider(responses=[_calendar_payload()]))
        await _run(_rewrite_request(), ScriptedProvider(script="malformed_json"))
        await _run(_classify_request(), ScriptedProvider(script="timeout"))

        assert await capture_db_content_fingerprint(session) == before
        assert await table_counts(session) == counts_before
        for model in (Entity, Link, Event):
            assert (await session.execute(select(func.count(model.id)))).scalar_one() >= 0
        assert (await session.execute(select(func.count(Event.id)))).scalar_one() == events_before


# ---------------------------------------------------------------------------
# H4.1 — sağlayıcı düşmesi ve yönlendirme semantiği
# ---------------------------------------------------------------------------


async def test_health_probe_provider_failure_returns_needs_escalation(h4_on: None) -> None:
    """§41/§99: sağlayıcı düşmesi BEKLENEN bir durumdur; tipik H4 sonucu döner."""
    from tests.h4_test_provider import DownProvider

    response = await _run_with_probe(_classify_request(), DownProvider())

    assert response.status == "needs_escalation"
    assert response.failure_code == "MODEL_PROVIDER_UNAVAILABLE"
    assert response.result is None
    assert response.recovery_hint


async def test_health_probe_failure_has_zero_generation_attempts(h4_on: None) -> None:
    """§36: sağlık probu bir çıkarım denemesi DEĞİLDİR."""
    from tests.h4_test_provider import DownProvider

    provider = DownProvider()
    response = await _run_with_probe(_classify_request(), provider)

    assert response.route_decision.attempts == []
    assert provider.generation_calls == 0
    assert response.route_decision.selected_slot is None
    assert response.route_decision.selected_model is None
    assert response.route_decision.validation_status == "not_attempted"
    assert response.route_decision.escalated is False


async def test_health_probe_failure_does_not_escape_provider_error(h4_on: None) -> None:
    """§34/§35: ham `ProviderError` servis sınırından ÇIKMAZ."""
    from app.integrations.local_cognition.provider import ProviderError
    from tests.h4_test_provider import DownProvider

    try:
        response = await _run_with_probe(_classify_request(), DownProvider())
    except ProviderError as exc:  # pragma: no cover - regresyon kapısı
        raise AssertionError(f"raw ProviderError escaped the service: {exc}") from exc

    assert response.failure_code == "MODEL_PROVIDER_UNAVAILABLE"


async def test_health_probe_failure_reason_codes_are_factual(h4_on: None) -> None:
    """§37: "small doğrulamada düştü" gibi bir iddia ÜRETİLMEZ."""
    from tests.h4_test_provider import DownProvider

    response = await _run_with_probe(_classify_request(), DownProvider())
    codes = set(response.route_decision.reason_codes)

    assert "LANE_CLASSIFY" in codes
    assert "LOCAL_SMALL_VALIDATION_FAILED" not in codes
    assert "LOCAL_SMALL_UNAVAILABLE" not in codes


async def test_health_probe_failure_is_single_condition(h4_on: None) -> None:
    """§38: sağlayıcı global olarak düşükse slot başına ayrı hata üretilmez."""
    from tests.h4_test_provider import DownProvider

    provider = DownProvider()
    await _run_with_probe(_classify_request(), provider)

    assert len(provider.health_calls) == 1


async def test_runtime_small_to_medium_uses_escalated_reason(h4_on: None) -> None:
    """§53/§103: gerçek çalışma zamanı geçişi yükseltmedir."""
    provider = ScriptedProvider(
        responses=['{"label": "u1"}', '{"label": "u2"}', '{"label": "knowledge"}']
    )
    response = await _run(_classify_request(), provider)
    codes = response.route_decision.reason_codes

    assert "LOCAL_SMALL_SELECTED" in codes
    assert "LOCAL_SMALL_VALIDATION_FAILED" in codes
    assert "ESCALATED_TO_LOCAL_MEDIUM" in codes
    assert response.route_decision.escalated is True
    # H4 final cila §2: `selected_slot` İLK yönlendirme seçimidir; medium'a
    # çıkıldığı gerçeği `attempts[]` ile raporlanır.
    assert response.route_decision.selected_slot == "local-small"
    assert response.route_decision.selected_model == "small-model"
    assert [attempt.slot for attempt in response.route_decision.attempts] == [
        "local-small",
        "local-small",
        "local-medium",
    ]
    assert [attempt.validation_status for attempt in response.route_decision.attempts] == [
        "invalid",
        "invalid",
        "valid",
    ]


async def test_direct_medium_execution_is_not_escalation(h4_on: None) -> None:
    """§51/§100: medium doğrudan seçildiyse `escalated=false` ve yükseltme kodu YOK."""
    provider = ScriptedProvider(responses=['{"label": "task"}'])
    response = await _run(
        _classify_request(),
        provider,
        profiles=_profiles(small=""),
        health=_health(ModelHealth.unavailable(configured=False), HEALTHY),
    )
    codes = response.route_decision.reason_codes

    assert response.status == "success"
    assert response.route_decision.selected_slot == "local-medium"
    assert "LOCAL_SMALL_UNAVAILABLE" in codes
    assert "LOCAL_MEDIUM_SELECTED" in codes
    assert "ESCALATED_TO_LOCAL_MEDIUM" not in codes
    assert response.route_decision.escalated is False


async def test_generation_time_model_unavailable_counts_as_escalation(h4_on: None) -> None:
    """§54: small probda sağlıklıydı ama üretimde yoksa bu GERÇEK yükseltmedir."""
    provider = ScriptedProvider(script="model_missing")
    response = await _run(_classify_request(), provider)

    assert response.route_decision.escalated is True
    assert "ESCALATED_TO_LOCAL_MEDIUM" in response.route_decision.reason_codes
    assert [attempt.slot for attempt in response.route_decision.attempts] == [
        "local-small",
        "local-medium",
    ]


async def test_medium_context_exceeded_is_not_reported_as_unavailable(h4_on: None) -> None:
    """§46: orta bütçe aşımı "kullanılamaz" değildir."""
    tiny = {
        "local-small": ModelProfile(
            slot="local-small", provider="ollama", model_id="small-model",
            execution_boundary="local_loopback", max_input_chars=500, capabilities=CAPABILITIES,
        ),
        "local-medium": ModelProfile(
            slot="local-medium", provider="ollama", model_id="medium-model",
            execution_boundary="local_loopback", max_input_chars=1000, capabilities=CAPABILITIES,
        ),
    }
    request = lc.build_lane_request(lane="query_rewrite", text="x" * 2000, protected_terms=[])

    with pytest.raises(lc.H4Error, match="CONTEXT_TOO_LARGE") as excinfo:
        await _run(request, ScriptedProvider(responses=["{}"]), profiles=tiny)

    assert excinfo.value.code == "CONTEXT_TOO_LARGE"


# ---------------------------------------------------------------------------
# H4 final cila — `selected_slot` tek anlamlıdır (§2/§3)
# ---------------------------------------------------------------------------


async def test_selected_slot_is_initial_route_on_success_after_escalation(h4_on: None) -> None:
    """Small seçildi, düştü, medium başardı → `selected_slot` yine local-small."""
    provider = ScriptedProvider(
        responses=['{"label": "u1"}', '{"label": "u2"}', '{"label": "knowledge"}']
    )
    response = await _run(_classify_request(), provider)
    decision = response.route_decision

    assert response.status == "success"
    assert decision.selected_slot == "local-small"
    assert decision.selected_model == "small-model"
    assert decision.escalated is True
    assert [attempt.slot for attempt in decision.attempts] == [
        "local-small",
        "local-small",
        "local-medium",
    ]


async def test_selected_slot_is_initial_route_on_exhausted_chain(h4_on: None) -> None:
    provider = ScriptedProvider(
        responses=['{"label": "u1"}', '{"label": "u2"}', '{"label": "u3"}']
    )
    response = await _run(_classify_request(), provider)
    decision = response.route_decision

    assert response.status == "needs_escalation"
    assert decision.selected_slot == "local-small"
    assert decision.selected_model == "small-model"


async def test_selected_slot_is_medium_when_medium_was_selected_initially(h4_on: None) -> None:
    provider = ScriptedProvider(responses=['{"label": "task"}'])
    response = await _run(
        _classify_request(),
        provider,
        profiles=_profiles(small=""),
        health=_health(ModelHealth.unavailable(configured=False), HEALTHY),
    )

    assert response.route_decision.selected_slot == "local-medium"
    assert response.route_decision.selected_model == "medium-model"
    assert response.route_decision.escalated is False


async def test_selected_slot_is_null_when_health_probe_fails(h4_on: None) -> None:
    from tests.h4_test_provider import DownProvider

    response = await _run_with_probe(_classify_request(), DownProvider())

    assert response.route_decision.selected_slot is None
    assert response.route_decision.selected_model is None


async def test_selected_slot_semantics_are_consistent_across_outcomes(h4_on: None) -> None:
    """Aynı istek için başarı/başarısızlık `selected_slot`'u DEĞİŞTİRMEZ."""
    success = await _run(
        _classify_request(), ScriptedProvider(responses=['{"label": "u1"}', '{"label": "task"}'])
    )
    failure = await _run(
        _classify_request(), ScriptedProvider(responses=['{"label": "u1"}', '{"label": "u2"}', '{"label": "u3"}'])
    )

    assert success.status == "success"
    assert failure.status == "needs_escalation"
    assert success.route_decision.selected_slot == failure.route_decision.selected_slot
    assert success.route_decision.selected_model == failure.route_decision.selected_model


async def test_auto_protected_identifier_is_enforced_end_to_end(h4_on: None) -> None:
    """§160: model UUID'yi düşürürse zincir tükenir (açık terim verilmemiş olsa bile)."""
    uuid_value = "4f1c9a2e-7b3d-4c58-9a11-2d6e8f0b7c34"
    request = lc.build_lane_request(
        lane="query_rewrite",
        text=f"Show evidence for entity {uuid_value}",
        protected_terms=[],
    )
    dropped = '{"rewritten_query": "evidence request summary"}'
    provider = ScriptedProvider(responses=[dropped, dropped, dropped])

    response = await _run(request, provider)

    assert response.status == "needs_escalation"
    assert all(
        attempt.failure_code == "PROTECTED_TERM_LOST" for attempt in response.route_decision.attempts
    )

    kept = json.dumps({"rewritten_query": f"evidence entity {uuid_value}"})
    ok_response = await _run(request, ScriptedProvider(responses=[kept]))
    assert ok_response.status == "success"
    assert uuid_value in ok_response.result.rewritten_query
