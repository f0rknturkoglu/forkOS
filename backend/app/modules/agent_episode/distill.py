"""A3 tur damıtma: geçici metinden sınırlı epizodik ifadeler çıkarır.

Bu modül H4 yerel biliş altyapısını YENİDEN KULLANIR: yeni bir özetleyici, yeni
bir LLM soyutlaması veya ikinci bir yerel biliş yolu YOKTUR. Tek eklenen şey
dar, sürümlü bir çıkarım sözleşmesidir (`episodic_turn_v1`).

İki invariant burada korunur:

1. **Ham transkript kalıcılaşmaz (§5).** `user_message`/`assistant_response`
   yalnız bu istek boyunca yaşar; fonksiyon dönerken yalnız türetilmiş,
   karakterle sınırlı ifadeler ve doğrulama için gereken digest kalır.
2. **Birebir sızıntı reddedilir.** Model bir ifadeyi kaynak metinden uzun bir
   parça hâlinde kopyalarsa ifade kabul EDİLMEZ; "türetilmiş ifade" ile "ham
   alıntı" arasındaki fark böylece denetlenebilir kalır.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

from app.config import settings
from app.core.secret_safety import contains_high_confidence_secret
from app.integrations.local_cognition.models import H4Error, StructuredExtractRequest
from app.integrations.local_cognition.service import run_local_cognition
from app.modules.agent_episode.schemas import (
    MAX_ITEM_TEXT_CHARS,
    MAX_ITEMS_PER_TURN,
    MAX_SUPPORT_REFS_PER_ITEM,
    MAX_VERBATIM_ITEM_SPAN_CHARS,
    normalize_for_matching,
)

#: Bir kaynak başlığının eşleşme için sayılması gereken en kısa normalize uzunluk.
#: Kısa başlıklar ("a", "cv") yanlış eşleşme üretir; eşleşmemek daha dürüsttür.
MIN_TITLE_MATCH_CHARS = 4

#: Deftere yazılabilecek en fazla teslim edilen kaynak referansı.
MAX_DELIVERED_REFS = 8

#: Başlık defterde bu uzunlukta saklanır (kanonik metadata, ham metin değil).
MAX_REF_TITLE_CHARS = 128

_USER_LABEL = "USER MESSAGE"
_ASSISTANT_LABEL = "ASSISTANT RESPONSE"


def compute_turn_digest(
    *, session_key: str, turn_key: str, user_text: str, assistant_text: str
) -> str:
    """Tur kökenini doğrulayan alan-ayrılmış digest (§8).

    Digest bir denetim/ilişkilendirme METAVERİSİDİR: içeriğin kendisi değildir
    ve geri çevrilemez. Ham metin saklanmadığı için "bu ifade hangi turdan
    geldi" sorusu yalnız bu değerle tutarlılık kontrolü olarak cevaplanır.
    """
    payload = "\0".join(
        (
            "forkos-episode-turn-v1",
            session_key,
            turn_key,
            normalize_for_matching(user_text),
            normalize_for_matching(assistant_text),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_transient_text(user_text: str | None, assistant_text: str | None) -> str:
    """H4'e gönderilecek GEÇİCİ kaynak metni kurar.

    Etiketler, modelin hangi parçanın kullanıcıya hangisinin asistana ait
    olduğunu ayırt edebilmesi içindir; `source_excerpt` doğrulaması bu metnin
    tamamına karşı yapılır.
    """
    parts: list[str] = []
    if user_text and user_text.strip():
        parts.append(f"{_USER_LABEL}:\n{user_text.strip()}")
    if assistant_text and assistant_text.strip():
        parts.append(f"{_ASSISTANT_LABEL}:\n{assistant_text.strip()}")
    return "\n\n".join(parts)


def has_verbatim_leak(text: str, source_text: str) -> bool:
    """`text` kaynak metinden `MAX_VERBATIM_ITEM_SPAN_CHARS`'ı aşan parça taşıyor mu?

    Sabit uzunlukta bir pencere kaydırılır ve her pencere kaynakta aranır. Bu,
    "uzun birebir alıntı" tanımının doğrudan karşılığıdır ve bulanık değildir.
    Kısa teknik terim, kimlik veya proje adı alıntılamak serbesttir.
    """
    normalized_text = normalize_for_matching(text)
    normalized_source = normalize_for_matching(source_text)
    window = MAX_VERBATIM_ITEM_SPAN_CHARS
    if len(normalized_text) < window or not normalized_source:
        return False
    for start in range(len(normalized_text) - window + 1):
        if normalized_text[start : start + window] in normalized_source:
            return True
    return False


def delivered_ref_from_source(source: Any) -> dict[str, Any] | None:
    """A2'nin teslim ettiği kaynağı A3 defter satırına çevirir.

    Defter YALNIZ kanonik metadata taşır: kimlik, tür, sürüm, kapsam ve
    eşleştirme için başlık. Ham konuşma metni buraya asla girmez.
    """
    source_id = getattr(source, "source_id", None)
    source_type = getattr(source, "source_type", None)
    if not isinstance(source_id, str) or not source_id or not isinstance(source_type, str):
        return None
    title = getattr(source, "title", None)
    ref: dict[str, Any] = {
        "source_id": source_id[:128],
        "source_type": source_type[:32],
        "source_version": (
            getattr(source, "source_version", None) if isinstance(getattr(source, "source_version", None), str) else None
        ),
        "scope_project": (
            getattr(source, "scope_project", None) if isinstance(getattr(source, "scope_project", None), str) else None
        ),
        "title": title[:MAX_REF_TITLE_CHARS] if isinstance(title, str) and title.strip() else None,
    }
    return ref


def match_support_refs(
    *,
    item_text: str,
    source_excerpt: str,
    delivered_refs: list[dict[str, Any]],
    scope_project: str | None,
) -> list[dict[str, Any]]:
    """İfadeyi teslim edilen kaynak kümesiyle DETERMİNİSTİK olarak eşler.

    Eşleşme yalnız birebir metin kanıtıyla kurulur: kaynağın başlığı ya da
    kimliği ifadede/alıntıda aynen geçiyorsa bağlanır. Kapsam çelişkisi varsa
    kaynak BAĞLANMAZ. Hiçbir eşleşme yoksa boş liste döner ve ifade
    `turn_derived` kalır — bu bir hata değildir; yanlış atıf daha kötüdür (§9).
    """
    haystack = normalize_for_matching(f"{source_excerpt}\n{item_text}")
    if not haystack:
        return []
    matched: list[dict[str, Any]] = []
    for ref in delivered_refs:
        if len(matched) >= MAX_SUPPORT_REFS_PER_ITEM:
            break
        ref_scope = ref.get("scope_project")
        if scope_project and isinstance(ref_scope, str) and ref_scope and ref_scope != scope_project:
            continue
        title = ref.get("title")
        normalized_title = normalize_for_matching(title) if isinstance(title, str) else ""
        source_id = ref.get("source_id")
        normalized_id = normalize_for_matching(source_id) if isinstance(source_id, str) else ""
        hit = bool(normalized_title) and len(normalized_title) >= MIN_TITLE_MATCH_CHARS and (
            normalized_title in haystack
        )
        if not hit and normalized_id:
            hit = normalized_id in haystack
        if not hit:
            continue
        matched.append(
            {
                "source_id": str(source_id)[:128],
                "source_type": str(ref.get("source_type") or "")[:32],
                "source_version": ref.get("source_version"),
                "scope_project": ref.get("scope_project"),
            }
        )
    return matched


def compute_source_role_and_digest(
    excerpt: str,
    user_text: str | None,
    assistant_text: str | None,
) -> tuple[str | None, str | None]:
    """A4 §22: Geçici alıntıdan kaynak rolü ve kanıt özeti türetir (alıntı saklanmaz)."""
    norm_excerpt = normalize_for_matching(excerpt)
    if not norm_excerpt:
        return None, None
    digest = hashlib.sha256(
        ("forkos-explicit-evidence-v1" + norm_excerpt).encode("utf-8")
    ).hexdigest()

    norm_user = normalize_for_matching(user_text) if user_text else ""
    norm_asst = normalize_for_matching(assistant_text) if assistant_text else ""

    in_user = bool(norm_user and norm_excerpt in norm_user)
    in_asst = bool(norm_asst and norm_excerpt in norm_asst)

    if in_user and not in_asst:
        role = "user"
    elif in_asst and not in_user:
        role = "assistant"
    elif in_user and in_asst:
        role = "mixed"
    else:
        role = None

    return role, digest


@dataclass(frozen=True)
class DistilledItem:
    """Kabul edilmiş tek epizodik ifade (ham alıntı TAŞIMAZ)."""

    kind: str
    text: str
    evidence_class: str
    support_refs: list[dict[str, Any]] = field(default_factory=list)
    source_role: str | None = None
    evidence_digest: str | None = None


@dataclass(frozen=True)
class DistillationOutcome:
    items: list[DistilledItem] = field(default_factory=list)
    degraded_reasons: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    available: bool = False


def _classify_reason(response: Any) -> str:
    """H4 yanıtını sınırlı bir A3 gerekçe koduna indirir (§11/§28).

    `failure_code` tek başına yeterli değildir: iki yuva da yapılandırıldığında
    H4 zinciri tükendiğinde `LOCAL_CAPABILITY_UNAVAILABLE` döner ve "iki model
    de doğrulamayı geçemedi" ile "yerel yetenek yok" aynı koda düşerdi. Bu
    ayrımı `attempts[].validation_status` verir: tüm denemeler `invalid` ise
    sebep DOĞRULAMADIR; herhangi biri `provider_error` ise sebep sağlayıcıdır.
    """
    decision = getattr(response, "route_decision", None)
    attempts = list(getattr(decision, "attempts", None) or [])
    if attempts and all(
        getattr(attempt, "validation_status", None) == "invalid" for attempt in attempts
    ):
        return "EPISODE_VALIDATION_FAILED"

    failure = getattr(response, "failure_code", None)
    if failure in {"VALIDATION_FAILED", "OUTPUT_SCHEMA_MISMATCH", "SOURCE_EXCERPT_NOT_FOUND"}:
        return "EPISODE_VALIDATION_FAILED"
    if failure in {"MODEL_UNAVAILABLE", "MODEL_PROVIDER_UNAVAILABLE"}:
        return "LOCAL_COGNITION_UNAVAILABLE"
    return "EPISODE_EXTRACTION_UNAVAILABLE"


def _accept_items(
    raw_items: list[dict[str, Any]],
    *,
    transient_text: str,
    user_text: str | None = None,
    assistant_text: str | None = None,
    delivered_refs: list[dict[str, Any]],
    scope_project: str | None,
) -> tuple[list[DistilledItem], list[str]]:
    """Doğrulanmış H4 öğelerini A3 ifadelerine çevirir; sızıntıyı reddeder."""
    accepted: list[DistilledItem] = []
    degraded: list[str] = []
    for raw in raw_items[:MAX_ITEMS_PER_TURN]:
        kind = str(raw.get("kind") or "")
        text = str(raw.get("text") or "").strip()
        excerpt = str(raw.get("source_excerpt") or "")
        if not kind or not text:
            continue
        if len(text) > MAX_ITEM_TEXT_CHARS:
            text = text[:MAX_ITEM_TEXT_CHARS].rstrip()
        # Ham transkript sızıntısı: uzun birebir alıntı taşıyan ifade saklanmaz.
        if has_verbatim_leak(text, transient_text):
            if "VERBATIM_LEAKAGE" not in degraded:
                degraded.append("VERBATIM_LEAKAGE")
            continue
        # Kısa kimlik bilgisi / sır sızıntısı: apaçık kimlik deseni taşıyan ifade saklanmaz.
        if contains_high_confidence_secret(text):
            if "SECRET_LEAKAGE" not in degraded:
                degraded.append("SECRET_LEAKAGE")
            continue
        refs = match_support_refs(
            item_text=text,
            source_excerpt=excerpt,
            delivered_refs=delivered_refs,
            scope_project=scope_project,
        )
        role, digest = compute_source_role_and_digest(excerpt, user_text, assistant_text)
        accepted.append(
            DistilledItem(
                kind=kind,
                text=text,
                evidence_class="canonical_supported" if refs else "turn_derived",
                support_refs=refs,
                source_role=role,
                evidence_digest=digest,
            )
        )
    return accepted, degraded


async def distill_turn(
    *,
    user_text: str | None,
    assistant_text: str | None,
    delivered_refs: list[dict[str, Any]],
    scope_project: str | None,
) -> DistillationOutcome:
    """Tek turu H4 ile damıtır. Asla exception fırlatmaz; her hata degrade olur.

    H4 devre dışı / model yok / zaman aşımı / doğrulama hatası durumlarında
    konuşmaya özgü hiçbir anlamsal ifade UYDURULMAZ (§11). Boş sonuç dürüsttür.
    """
    transient_text = build_transient_text(user_text, assistant_text)
    if not transient_text.strip():
        return DistillationOutcome(degraded_reasons=["EPISODE_EXTRACTION_UNAVAILABLE"])

    started = time.perf_counter()
    request = StructuredExtractRequest(
        lane="structured_extract", contract="episodic_turn_v1", text=transient_text
    )
    # Bütçe AYARDAN gelir: makineye ve yerel modele göre ölçülerek ayarlanır.
    budget = float(getattr(settings, "a3_extraction_budget_seconds", 2.0))
    try:
        response = await asyncio.wait_for(run_local_cognition(request), timeout=budget)
    except TimeoutError:
        return DistillationOutcome(
            degraded_reasons=["EPISODE_EXTRACTION_TIMEOUT"],
            latency_ms=(time.perf_counter() - started) * 1000,
        )
    except H4Error:
        # H4 devre dışı, uç geçersiz veya bağlam bütçesi aşıldı: yerel biliş yok.
        return DistillationOutcome(
            degraded_reasons=["LOCAL_COGNITION_UNAVAILABLE"],
            latency_ms=(time.perf_counter() - started) * 1000,
        )
    except Exception:  # noqa: BLE001 - A3 hiçbir koşulda turu düşürmez
        return DistillationOutcome(
            degraded_reasons=["EPISODE_EXTRACTION_UNAVAILABLE"],
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    latency_ms = (time.perf_counter() - started) * 1000
    if getattr(response, "status", None) != "success":
        return DistillationOutcome(
            degraded_reasons=[_classify_reason(response)], latency_ms=latency_ms
        )

    result = getattr(response, "result", None)
    raw_items = list(getattr(result, "items", None) or [])
    if not raw_items:
        # Doğrulanmış ama boş çıktı: uydurma yapılmaz, tur yine de gözlenmiştir.
        return DistillationOutcome(degraded_reasons=["EPISODE_EMPTY"], latency_ms=latency_ms)

    items, degraded = _accept_items(
        raw_items,
        transient_text=transient_text,
        user_text=user_text,
        assistant_text=assistant_text,
        delivered_refs=delivered_refs,
        scope_project=scope_project,
    )
    if not items and not degraded:
        degraded.append("EPISODE_EMPTY")
    return DistillationOutcome(
        items=items, degraded_reasons=degraded, latency_ms=latency_ms, available=True
    )


__all__ = [
    "DistilledItem",
    "DistillationOutcome",
    "build_transient_text",
    "compute_source_role_and_digest",
    "compute_turn_digest",
    "delivered_ref_from_source",
    "distill_turn",
    "has_verbatim_leak",
    "match_support_refs",
    "normalize_for_matching",
]
