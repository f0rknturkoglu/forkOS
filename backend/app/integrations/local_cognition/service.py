"""H4 servis orkestrasyonu: yönlendir → yürüt → doğrula → tekrar dene → sonuç.

Akış (§18)::

    SİNYALLER
      ↓
    SERT UYGUNLUK POLİTİKASI      (policy.route_task — saf)
      ↓
    MODEL SEÇİMİ
      ↓
    YEREL YÜRÜTME                 (sağlayıcı, loopback)
      ↓
    DETERMİNİSTİK DOĞRULAMA       (contracts — otorite)
      ↓
    SINIRLI TEKRAR / YEREL ÇIKIŞ
      ↓
    SONUÇ ya da needs_escalation

Sınırlar: small en fazla 2, medium en fazla 1 deneme; toplam model çağrısı ≤ 3.
Çıkış yalnızca YUKARI olabilir (small → medium); geri dönüş yoktur (§73).

H4 hiçbir yazma yapmaz, veritabanına ve kasa'ya dokunmaz, uzak model çağırmaz.
Zincir tükenirse `needs_escalation` döner — arka planda buluta düşülmez (§69).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

from app.config import settings
from app.integrations.local_cognition import contracts as contract_svc
from app.integrations.local_cognition import policy as policy_svc
from app.integrations.local_cognition import prompts as prompt_svc
from app.integrations.local_cognition.models import (
    LANE_REASON_CODES,
    MAX_MEDIUM_ATTEMPTS,
    MAX_SMALL_ATTEMPTS,
    AttemptRecord,
    ClassificationResult,
    ClassifyRequest,
    ExtractionResult,
    H4Error,
    LaneRequest,
    LaneResult,
    LocalCognitionResponse,
    QueryRewriteRequest,
    QueryRewriteResult,
    RouteDecision,
    SlotName,
    validate_lane_request,
)
from app.integrations.local_cognition.ollama import OllamaProvider, validate_loopback_base_url
from app.integrations.local_cognition.policy import ModelHealth, ModelProfile
from app.integrations.local_cognition.provider import (
    GenerationRequest,
    LocalModelProvider,
    ProviderError,
)

#: Slot → deneme tavanı (§71).
SLOT_ATTEMPTS: dict[str, int] = {
    "local-small": MAX_SMALL_ATTEMPTS,
    "local-medium": MAX_MEDIUM_ATTEMPTS,
}

ProviderFactory = Callable[[], LocalModelProvider]


def _json_schema_for(request: LaneRequest) -> dict[str, Any]:
    if isinstance(request, ClassifyRequest):
        return contract_svc.CLASSIFICATION_SCHEMA
    if isinstance(request, QueryRewriteRequest):
        return contract_svc.QUERY_REWRITE_SCHEMA
    return contract_svc.EXTRACTION_SCHEMAS[request.contract][1]


def _validate(request: LaneRequest, payload: Any) -> contract_svc.ValidationOutcome:
    """Lane'e göre deterministik doğrulama. Tek otorite burasıdır."""
    if isinstance(request, ClassifyRequest):
        return contract_svc.validate_classification(payload, request.text, request.labels)
    if isinstance(request, QueryRewriteRequest):
        return contract_svc.validate_query_rewrite(payload, request.text, request.protected_terms)
    validator = contract_svc.EXTRACTION_VALIDATORS[request.contract]
    return validator(payload, request.text)


def _parse_model_json(content: str) -> tuple[Any, str | None]:
    """Ham model içeriğini JSON'a çevirir. Bozuk çıktı bir DOĞRULAMA hatasıdır."""
    text = (content or "").strip()
    if not text:
        return None, "INVALID_MODEL_JSON"
    if text.startswith("```"):
        # Modelin kod bloğu sarmasına tolerans: yalnızca çitleri soy.
        text = text.strip("`")
        if "\n" in text:
            first, _, rest = text.partition("\n")
            if first.strip().lower() in {"json", ""}:
                text = rest
    try:
        return json.loads(text), None
    except (ValueError, TypeError):
        return None, "INVALID_MODEL_JSON"


def _build_result(request: LaneRequest, payload: dict[str, Any]) -> LaneResult:
    if isinstance(request, ClassifyRequest):
        return ClassificationResult(label=str(payload["label"]))
    if isinstance(request, QueryRewriteRequest):
        return QueryRewriteResult(rewritten_query=str(payload["rewritten_query"]))
    collection_key, _schema = contract_svc.EXTRACTION_SCHEMAS[request.contract]
    return ExtractionResult(contract=request.contract, items=list(payload.get(collection_key, [])))


async def _probe_health(
    provider: LocalModelProvider, profiles: dict[str, ModelProfile]
) -> dict[str, ModelHealth]:
    """Slotların sağlık anlık görüntüsü (§57). Kalıcı kayıt tutulmaz."""
    snapshot: dict[str, ModelHealth] = {}
    for slot, profile in profiles.items():
        if not profile.configured:
            snapshot[slot] = ModelHealth(
                configured=False, provider_reachable=False, model_available=False, healthy=False
            )
            continue
        snapshot[slot] = await provider.health(profile.model_id)
    return snapshot


def _failure_code_for_exhausted_chain(
    *, tried_slots: list[str], last_validation_code: str | None, last_provider_code: str | None
) -> str:
    """Zincir tükendiğinde dönen SINIRLI kod.

    - Birden fazla slot denendi (small → medium) → `LOCAL_CAPABILITY_UNAVAILABLE`
    - Tek slot denendi ve hata DOĞRULAMA kaynaklı → `VALIDATION_FAILED`
    - Tek slot denendi ve hata SAĞLAYICI kaynaklı → sağlayıcı kodu
    """
    if last_provider_code is not None:
        return last_provider_code
    if len(tried_slots) > 1:
        return "LOCAL_CAPABILITY_UNAVAILABLE"
    if last_validation_code is not None:
        return "VALIDATION_FAILED"
    return "LOCAL_CAPABILITY_UNAVAILABLE"


async def run_local_cognition(
    request: LaneRequest,
    *,
    provider_factory: ProviderFactory | None = None,
    profiles: dict[str, ModelProfile] | None = None,
    health_snapshot: dict[str, ModelHealth] | None = None,
) -> LocalCognitionResponse:
    """Tek bir yerel biliş isteğini yürütür.

    `health_snapshot` ve `profiles` yalnızca testler/eval için enjekte edilir;
    üretimde ayarlardan ve gerçek sağlayıcıdan gelir.
    """
    validate_lane_request(request)

    if not bool(getattr(settings, "h4_enabled", False)):
        raise H4Error("H4_DISABLED", "local cognition is disabled (H4_ENABLED is false)")

    # Loopback kuralı SAĞLAYICIDAN BAĞIMSIZ dayatılır: sağlayıcı enjekte
    # edilmiş olsa bile yapılandırılmış adres loopback olmalıdır (§47). Böylece
    # H4, yapılandırma yoluyla bir bulut geçidine dönüşemez.
    try:
        validate_loopback_base_url(str(getattr(settings, "h4_ollama_base_url", "")))
    except ProviderError as exc:
        raise H4Error("INVALID_LOCAL_MODEL_ENDPOINT", exc.message) from exc

    resolved_profiles = profiles if profiles is not None else policy_svc.build_profiles(settings)
    if provider_factory is not None:
        provider: LocalModelProvider = provider_factory()
    else:
        # Yapıcı loopback doğrulaması yapar: geçersiz adresle HİÇBİR istek denenmez.
        provider = OllamaProvider(
            str(getattr(settings, "h4_ollama_base_url", "")),
            timeout_seconds=float(getattr(settings, "h4_timeout_seconds", 45.0)),
        )

    input_chars = len(request.text)
    started = time.perf_counter()

    try:
        health = (
            health_snapshot
            if health_snapshot is not None
            else await _probe_health(provider, resolved_profiles)
        )
    except ProviderError as exc:
        # Sağlayıcının düşmesi BEKLENEN bir operasyonel durumdur (§35): ham
        # istisna MCP'nin genel güvenlik ağına kaçmaz, tipik H4 sonucuna
        # dönüşür. Sağlık probu bir ÇIKARIM DENEMESİ DEĞİLDİR: `attempts=[]`
        # kalır ve hiçbir üretim çağrısı yapılmaz (§36).
        provider_code = (
            exc.code if exc.code in {"MODEL_PROVIDER_UNAVAILABLE", "MODEL_UNAVAILABLE"} else "MODEL_PROVIDER_UNAVAILABLE"
        )
        decision = RouteDecision(
            lane=request.lane,
            selected_slot=None,
            selected_model=None,
            input_chars=input_chars,
            required_capabilities=list(policy_svc.required_capabilities(request.lane)),
            reason_codes=[LANE_REASON_CODES[request.lane], "STRUCTURED_OUTPUT_REQUIRED"],
            attempts=[],
            validation_status="not_attempted",
            escalated=False,
            escalation_reason=None,
            latency_ms=(time.perf_counter() - started) * 1000,
        )
        return LocalCognitionResponse(
            status="needs_escalation",
            lane=request.lane,
            result=None,
            failure_code=provider_code,
            recovery_hint=(
                "The local model provider is not reachable; start it (for example "
                "`ollama serve`) or handle this task with the caller's own model."
            ),
            route_decision=decision,
        )

    plan = policy_svc.route_task(
        lane=request.lane,
        input_chars=input_chars,
        profiles=resolved_profiles,
        health=health,
    )

    if plan.selected_slot is None:
        configured_budgets = [
            profile.max_input_chars
            for profile in resolved_profiles.values()
            if profile.configured
        ]
        if configured_budgets and input_chars > max(configured_budgets):
            raise H4Error(
                "CONTEXT_TOO_LARGE",
                "the supplied text exceeds every configured local input budget",
            )
        if not configured_budgets:
            raise H4Error(
                "NO_ELIGIBLE_MODEL", "no local model slot is configured (H4_SMALL_MODEL/H4_MEDIUM_MODEL)"
            )
        decision = RouteDecision(
            lane=request.lane,
            selected_slot=None,
            selected_model=None,
            input_chars=input_chars,
            required_capabilities=list(plan.required_capabilities),
            reason_codes=list(plan.reason_codes),
            attempts=[],
            validation_status="not_attempted",
            escalated=False,
            escalation_reason=None,
            latency_ms=(time.perf_counter() - started) * 1000,
        )
        return LocalCognitionResponse(
            status="needs_escalation",
            lane=request.lane,
            result=None,
            failure_code="MODEL_UNAVAILABLE",
            recovery_hint="Configure or start the local model, or handle the task with the caller's own model.",
            route_decision=decision,
        )

    # `selected_slot` HER YOLDA ilk yönlendirme seçimidir (H4 final cila §2):
    # çalışma zamanında medium'a çıkılsa bile alan DEĞİŞMEZ. Gerçek yürütme
    # yolu `attempts[]` ile dürüstçe raporlanır.
    initial_slot = plan.selected_slot
    initial_profile = resolved_profiles[initial_slot]
    json_schema = _json_schema_for(request)
    attempts: list[AttemptRecord] = []
    reason_codes = list(plan.reason_codes)
    tried_slots: list[str] = []
    last_validation_code: str | None = None
    last_provider_code: str | None = None
    escalated = False

    for slot in plan.eligible_slots:
        profile = resolved_profiles[slot]
        tried_slots.append(slot)
        if slot != plan.selected_slot:
            escalated = True
            # Yukarı çıkış GÖRÜNÜR olmalı: hangi kodla medium'a geçildiği
            # karar kaydında kalır (§64).
            if "ESCALATED_TO_LOCAL_MEDIUM" not in reason_codes:
                reason_codes.append("ESCALATED_TO_LOCAL_MEDIUM")
        max_attempts = SLOT_ATTEMPTS.get(slot, 1)

        for attempt_number in range(1, max_attempts + 1):
            user_prompt = (
                prompt_svc.build_user_prompt(request)
                if attempt_number == 1 or last_validation_code is None
                else prompt_svc.build_repair_prompt(request, last_validation_code)
            )
            generation = GenerationRequest(
                model_id=profile.model_id,
                system_prompt=prompt_svc.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                json_schema=json_schema,
                temperature=0.0,
                timeout_seconds=float(getattr(settings, "h4_timeout_seconds", 45.0)),
            )
            try:
                generated = await provider.generate_structured(generation)
            except ProviderError as exc:
                attempts.append(
                    AttemptRecord(
                        slot=slot,  # type: ignore[arg-type]
                        model_id=profile.model_id,
                        attempt_number=attempt_number,
                        latency_ms=0.0,
                        validation_status="provider_error",
                        failure_code=exc.code,
                    )
                )
                last_provider_code = exc.code
                if exc.code == "MODEL_UNAVAILABLE":
                    # Model kurulu değil: bir sonraki slota çıkılabilir.
                    break
                # Sağlayıcı düzeyinde hata: zincir burada durur.
                decision = RouteDecision(
                    lane=request.lane,
                    selected_slot=initial_slot,
                    selected_model=initial_profile.model_id,
                    input_chars=input_chars,
                    required_capabilities=list(plan.required_capabilities),
                    reason_codes=reason_codes,
                    attempts=attempts,
                    validation_status="invalid",
                    escalated=escalated,
                    escalation_reason="provider error" if escalated else None,
                    latency_ms=(time.perf_counter() - started) * 1000,
                )
                return LocalCognitionResponse(
                    status="needs_escalation",
                    lane=request.lane,
                    result=None,
                    failure_code=exc.code,
                    recovery_hint="Local model provider is unavailable; the caller should handle this task.",
                    route_decision=decision,
                )

            payload, parse_code = _parse_model_json(generated.content)
            if parse_code is not None:
                attempts.append(
                    AttemptRecord(
                        slot=slot,  # type: ignore[arg-type]
                        model_id=profile.model_id,
                        attempt_number=attempt_number,
                        latency_ms=generated.latency_ms,
                        validation_status="invalid",
                        failure_code=parse_code,
                    )
                )
                last_validation_code = parse_code
                continue

            outcome = _validate(request, payload)
            attempts.append(
                AttemptRecord(
                    slot=slot,  # type: ignore[arg-type]
                    model_id=profile.model_id,
                    attempt_number=attempt_number,
                    latency_ms=generated.latency_ms,
                    validation_status="valid" if outcome.ok else "invalid",
                    failure_code=None if outcome.ok else outcome.code,
                )
            )
            if outcome.ok:
                decision = RouteDecision(
                    lane=request.lane,
                    selected_slot=initial_slot,
                    selected_model=initial_profile.model_id,
                    input_chars=input_chars,
                    required_capabilities=list(plan.required_capabilities),
                    reason_codes=reason_codes,
                    attempts=attempts,
                    validation_status="valid",
                    escalated=escalated,
                    escalation_reason="small slot did not satisfy the contract" if escalated else None,
                    latency_ms=(time.perf_counter() - started) * 1000,
                )
                return LocalCognitionResponse(
                    status="success",
                    lane=request.lane,
                    result=_build_result(request, outcome.payload or {}),
                    failure_code=None,
                    recovery_hint=None,
                    route_decision=decision,
                )
            last_validation_code = outcome.code
            # Doğrulama hatası ANINDA karar kaydına girer: retry sonrası
            # başarı gelse bile "small bir kez düştü" olgusu görünür kalır.
            retry_code = (
                "LOCAL_SMALL_VALIDATION_FAILED"
                if slot == "local-small"
                else "LOCAL_MEDIUM_VALIDATION_FAILED"
            )
            if retry_code not in reason_codes:
                reason_codes.append(retry_code)

    failure_code = _failure_code_for_exhausted_chain(
        tried_slots=tried_slots,
        last_validation_code=last_validation_code,
        last_provider_code=last_provider_code,
    )
    decision = RouteDecision(
        lane=request.lane,
        selected_slot=initial_slot,
        selected_model=initial_profile.model_id,
        input_chars=input_chars,
        required_capabilities=list(plan.required_capabilities),
        reason_codes=reason_codes,
        attempts=attempts,
        validation_status="invalid",
        escalated=escalated,
        escalation_reason="local chain exhausted" if escalated else None,
        latency_ms=(time.perf_counter() - started) * 1000,
    )
    hint = "No local model satisfied the contract; the caller may handle this task with its own model."
    if last_validation_code is not None:
        hint = (
            f"Local models kept failing validation ({last_validation_code}); "
            "the caller may handle this task with its own model."
        )
    return LocalCognitionResponse(
        status="needs_escalation",
        lane=request.lane,
        result=None,
        failure_code=failure_code,
        recovery_hint=hint,
        route_decision=decision,
    )


__all__ = ["SLOT_ATTEMPTS", "run_local_cognition"]


def _unused_slot_name_guard(slot: SlotName) -> SlotName:  # pragma: no cover - tip ipucu
    return slot
