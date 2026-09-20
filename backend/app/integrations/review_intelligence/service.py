"""H5 servis — doğrulama, mod dağıtımı ve paket birleştirme (§115).

Bu modül bilerek ince tutulur: muhakeme modüllerde, politika `policy.py`'de,
kaynak okumaları `sources.py`'de yaşar. Burada yalnızca:

```text
girdi doğrulama → mod dağıtımı → bütçe/kapsam koordinasyonu
→ bozulmuş mod davranışı → nihai paket montajı
```

H5 **salt-okunurdur**: hiçbir tabloya/satıra/dosyaya yazmaz.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.review_intelligence import continuity as continuity_svc
from app.integrations.review_intelligence import policy as policy_svc
from app.integrations.review_intelligence import review as review_svc
from app.integrations.review_intelligence import sources as source_svc
from app.integrations.review_intelligence.models import (
    Collector,
    Coverage,
    ReviewIntelligenceError,
    ReviewIntelligenceResponse,
)


def _provided_arguments(**kwargs: Any) -> set[str]:
    """Gerçekten VERİLEN argümanlar — `None` geçmek "verildi" sayılmaz."""
    return {name for name, value in kwargs.items() if value is not None}


async def review_intelligence(
    session: AsyncSession,
    *,
    mode: str,
    since: str | None = None,
    until: str | None = None,
    reference_date: str | None = None,
    focus_entity_id: str | None = None,
    include_knowledge: bool = True,
    now: datetime | None = None,
) -> ReviewIntelligenceResponse:
    """H5'in tek giriş noktası.

    Mod ve argüman uyumu ÇALIŞMA ZAMANINDA doğrulanır (§124): uyumsuz argüman
    sessizce yok sayılmaz.
    """
    resolved_mode = policy_svc.validate_mode(mode)
    policy_svc.validate_mode_arguments(
        resolved_mode,
        _provided_arguments(
            since=since,
            until=until,
            reference_date=reference_date,
            focus_entity_id=focus_entity_id,
            # Varsayılan `True` "verilmedi" sayılır; `False` kapsamı DARALTAN
            # açık bir istektir ve etkisiz modda reddedilir (§124).
            include_knowledge=False if include_knowledge is False else None,
        ),
    )

    since_dt = source_svc.parse_aware(since, "since")
    until_dt = source_svc.parse_aware(until, "until")
    if since_dt is not None and until_dt is not None and until_dt <= since_dt:
        raise ReviewIntelligenceError("INVALID_TIME_RANGE", "'since' must be before 'until'")
    reference = source_svc.parse_reference_date(reference_date)
    focus = source_svc.parse_focus_entity(focus_entity_id)

    collector = Collector()
    payload: Any
    coverage: Coverage

    if resolved_mode == "continuity":
        payload, coverage = await continuity_svc.build_continuity(
            session,
            collector,
            since=since_dt,
            until=until_dt,
            focus_entity_id=focus,
            include_knowledge=include_knowledge,
            now=now,
        )
    elif resolved_mode == "daily_close":
        payload, coverage = await review_svc.build_daily_close(
            session,
            collector,
            reference_date=reference,
            include_knowledge=include_knowledge,
            now=now,
        )
    elif resolved_mode == "weekly_review":
        payload, coverage = await review_svc.build_weekly_review(
            session,
            collector,
            reference_date=reference,
            include_knowledge=include_knowledge,
            now=now,
        )
    elif resolved_mode == "period_delta":
        payload, coverage = await review_svc.build_period_delta(
            session,
            collector,
            since=since_dt,  # type: ignore[arg-type]
            until=until_dt,
            focus_entity_id=focus,
            now=now,
        )
    else:
        payload, coverage = await review_svc.build_consolidation(
            session,
            collector,
            since=since_dt,
            until=until_dt,
            focus_entity_id=focus,
            include_knowledge=include_knowledge,
            now=now,
        )

    # Deterministik kaynak sıralaması (§140): domain, ref.
    collector.sources.sort(key=lambda item: (item.domain, item.ref))
    collector.manifest.vault_sources = sorted(set(collector.manifest.vault_sources))
    collector.manifest.h3_evidence_ids = sorted(set(collector.manifest.h3_evidence_ids))
    collector.manifest.truncated = collector.manifest.truncated or collector.truncated
    collector.manifest.h3_evidence_ids = collector.manifest.h3_evidence_ids[:100]

    return ReviewIntelligenceResponse(
        mode=resolved_mode,
        coverage=coverage,
        payload=payload,
        sources=collector.sources,
        evidence=collector.evidence,
        source_manifest=collector.manifest,
        trace=collector.trace,
        warnings=collector.warnings,
        truncated=collector.truncated or collector.manifest.truncated,
    )


__all__ = ["review_intelligence"]


def _unused_uuid_guard(value: uuid.UUID) -> uuid.UUID:  # pragma: no cover - tip ipucu
    return value
