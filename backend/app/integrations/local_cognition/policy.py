"""H4 yönlendirme politikası — SAF ve DETERMİNİSTİK.

Bu modül kararın TEK yeridir: hangi model slotu uygun, hangisi seçilir, hangi
gerekçe kodları üretilir. Model ÇALIŞTIRMAZ, ağa çıkmaz, veritabanına dokunmaz.

Temel ayrım (§19/§61):

```text
SİNYAL   : lane, input_chars, yetenekler, slot yapılandırması, sağlık
POLİTİKA : uygunluk kuralları (bu modül)
KARAR    : seçilen slot + gerekçe kodları
```

Model tabanlı yönlendirici YOKTUR (§20): "prompt zor görünüyor" bir politika
değildir. Seçim kuralı tek cümledir:

```text
en küçük, sağlıklı, yapılandırılmış ve bütçesi yeten uygun slot
```
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.integrations.local_cognition.models import (
    ACTIVE_LANES,
    LANE_REASON_CODES,
    SLOT_PRIORITY,
    Capability,
    ExecutionBoundary,
    Lane,
    ReasonCode,
    SlotName,
)

#: Slot → gereken yetenekler. Lane'ler aktif üçlüdür; her model bu üçünü de
#: desteklemek zorundadır çünkü hepsi yapılandırılmış çıktı üretir.
LANE_CAPABILITIES: dict[str, tuple[Capability, ...]] = {
    "classify": ("classify", "structured_output"),
    "structured_extract": ("structured_extract", "structured_output"),
    "query_rewrite": ("query_rewrite", "structured_output"),
}

#: Yapılandırılmış çıktı gerektiren lane'ler (§64: STRUCTURED_OUTPUT_REQUIRED).
STRUCTURED_LANES: tuple[str, ...] = ("structured_extract", "query_rewrite", "classify")


@dataclass(frozen=True)
class ModelProfile:
    """Bir slotun yapılandırmadan türeyen profili (§56).

    Kalıcı model kaydı YOKTUR: profiller ayarlardan türetilir (§58).
    """

    slot: SlotName
    provider: str
    model_id: str
    execution_boundary: ExecutionBoundary
    max_input_chars: int
    capabilities: frozenset[str]

    @property
    def configured(self) -> bool:
        return bool(self.model_id.strip())


@dataclass(frozen=True)
class ModelHealth:
    """Sağlık, UYGUNLUKTAN ayrıdır (§57).

    Bir model `healthy=True` ama `eligible=False` olabilir: girdi bütçesi
    yetmiyorsa sağlıklı olması onu uygun yapmaz.
    """

    configured: bool
    provider_reachable: bool
    model_available: bool
    healthy: bool

    @staticmethod
    def unavailable(*, configured: bool = True, provider_reachable: bool = True) -> ModelHealth:
        return ModelHealth(
            configured=configured,
            provider_reachable=provider_reachable,
            model_available=False,
            healthy=False,
        )


@dataclass(frozen=True)
class RoutePlan:
    """`route_task` çıktısı: yürütme ÖNCESİ deterministik karar."""

    lane: Lane
    input_chars: int
    required_capabilities: tuple[str, ...]
    eligible_slots: tuple[SlotName, ...]
    selected_slot: SlotName | None
    reason_codes: tuple[ReasonCode, ...]


def required_capabilities(lane: str) -> tuple[str, ...]:
    return LANE_CAPABILITIES.get(lane, ())


def _slot_unavailable_code(slot: str) -> ReasonCode:
    return "LOCAL_SMALL_UNAVAILABLE" if slot == "local-small" else "LOCAL_MEDIUM_UNAVAILABLE"


def _slot_context_code(slot: str) -> ReasonCode:
    return "LOCAL_SMALL_CONTEXT_EXCEEDED" if slot == "local-small" else "LOCAL_MEDIUM_UNAVAILABLE"


def _slot_selected_code(slot: str) -> ReasonCode:
    return "LOCAL_SMALL_SELECTED" if slot == "local-small" else "ESCALATED_TO_LOCAL_MEDIUM"


def route_task(
    *,
    lane: Lane,
    input_chars: int,
    profiles: Mapping[str, ModelProfile],
    health: Mapping[str, ModelHealth],
) -> RoutePlan:
    """Slot seçimini yapar. SAF fonksiyondur: aynı girdi → aynı karar (§89).

    Sıra: `local-small` → `local-medium`. Küçük model uygun olduğunda tercih
    edilir; medium "prompt zor göründüğü" için DEĞİL, yalnızca küçük model
    yoksa/bütçesi yetmiyorsa/doğrulamada tükendiyse seçilir (§62).
    """
    required = required_capabilities(lane)
    reason_codes: list[ReasonCode] = [LANE_REASON_CODES[lane]]
    if lane in STRUCTURED_LANES:
        reason_codes.append("STRUCTURED_OUTPUT_REQUIRED")

    eligible: list[SlotName] = []
    selected: SlotName | None = None

    for slot in SLOT_PRIORITY:
        profile = profiles.get(slot)
        slot_health = health.get(slot)
        if profile is None or not profile.configured:
            reason_codes.append(_slot_unavailable_code(slot))
            continue
        if slot_health is None or not slot_health.healthy:
            reason_codes.append(_slot_unavailable_code(slot))
            continue
        if not set(required) <= profile.capabilities:
            reason_codes.append("LOCAL_CAPABILITY_UNAVAILABLE")
            continue
        if input_chars > profile.max_input_chars:
            reason_codes.append(_slot_context_code(slot))
            continue

        eligible.append(slot)  # type: ignore[arg-type]
        if selected is None:
            selected = slot  # type: ignore[assignment]
            reason_codes.append(_slot_selected_code(slot))

    if selected is None:
        reason_codes.append("NO_ELIGIBLE_MODEL")

    return RoutePlan(
        lane=lane,
        input_chars=input_chars,
        required_capabilities=required,
        eligible_slots=tuple(eligible),
        selected_slot=selected,
        reason_codes=tuple(reason_codes),
    )


def build_profiles(settings: object) -> dict[str, ModelProfile]:
    """Ayarlardan slot profillerini türetir (§52/§54/§55).

    Kodda HİÇBİR sabit model adı yoktur: kimlikler yapılandırmadan gelir.
    """
    small_model = str(getattr(settings, "h4_small_model", "") or "").strip()
    medium_model = str(getattr(settings, "h4_medium_model", "") or "").strip()
    small_budget = int(getattr(settings, "h4_small_input_chars", 12000))
    medium_budget = int(getattr(settings, "h4_medium_input_chars", 24000))
    capabilities = frozenset(
        {"classify", "structured_extract", "query_rewrite", "structured_output"}
    )

    return {
        "local-small": ModelProfile(
            slot="local-small",
            provider="ollama",
            model_id=small_model,
            execution_boundary="local_loopback",
            max_input_chars=small_budget,
            capabilities=capabilities,
        ),
        "local-medium": ModelProfile(
            slot="local-medium",
            provider="ollama",
            model_id=medium_model,
            execution_boundary="local_loopback",
            max_input_chars=medium_budget,
            capabilities=capabilities,
        ),
    }


def is_active_lane(lane: str) -> bool:
    return lane in ACTIVE_LANES
