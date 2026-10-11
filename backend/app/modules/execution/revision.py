"""H7 plan revizyonu — kanonik serileştirme ve deterministik özet.

Onayın bağlandığı şey BUDUR: plan içeriğinin normalize edilmiş özeti. Aynı
içerik her zaman aynı revizyonu üretir; modele ait hiçbir serbest metin
"onay" anlamı taşımaz.

Özete GİRMEZ (semantik olmayan / akışkan alanlar):

```text
created_at / updated_at      (zaman)
plan satır id'si             (DB ataması)
plan_id soy kimliği          (girdi, içerik değil)
input_answers                (karar girdisi; revizyonu kendisi belirler)
state / approval / execution (yaşam döngüsü, içerik değil)
```
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

#: Hash formatı sürümü. Format değişirse sürüm ARTIRILIR; eski revizyonlar
#: tarihsel olarak okunabilir kalır.
#: v3: Todo plan projection bound to approval. Old stored revisions remain readable.
#: v2: karar girdisi (`decision_context`) revizyona dahil edildi (H7.1/B).
REVISION_VERSION = "plan-v3"

#: Karar girdisi değeri için üst sınır (sınırsız metin taşıma yok).
MAX_DECISION_VALUE = 200


def normalized_step(step: dict[str, Any], ordinal: int) -> dict[str, Any]:
    """Bir adımı kararlı, sıra-bağımsız biçime indirger."""
    arguments = step.get("arguments") or {}
    return {
        "step_id": str(step.get("step_id") or f"s{ordinal + 1}"),
        "ordinal": ordinal,
        "action": str(step.get("action") or ""),
        # Sözlük anahtarları sıralanır: anahtar sırası revizyonu DEĞİŞTİRMEZ.
        "arguments": {key: arguments[key] for key in sorted(arguments)},
        "description": str(step.get("description") or ""),
        "expected_updated_at": step.get("expected_updated_at"),
        "expected_plan_fingerprint": step.get("expected_plan_fingerprint"),
    }


def normalized_plan(
    *,
    title: str,
    summary: str | None,
    reason: str | None,
    steps: list[dict[str, Any]],
    source_refs: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    decision_context: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Revizyona giren kanonik plan gövdesi.

    `decision_context`, kullanıcının `input_required` sorusuna verdiği SINIRLI
    cevaptır (H7.1/B). Revizyona girer çünkü cevapsız hâliyle aynı içerik
    "yeni karar alınmış" sayılmamalıdır: aksi halde `respond → prepare` eski
    `draft` satırına çökerek akış kilitlenirdi. Serbest konuşma dökümü DEĞİL,
    anahtar→sınırlı metin eşlemesidir.
    """
    return {
        "version": REVISION_VERSION,
        "title": str(title or ""),
        "summary": str(summary or ""),
        "reason": str(reason or ""),
        "steps": [normalized_step(step, index) for index, step in enumerate(steps)],
        # Kanıt referansları sıralanır ve tekilleştirilir: sıra/kopya özeti bozmaz.
        "source_refs": sorted({str(ref) for ref in (source_refs or []) if ref}),
        "evidence_refs": sorted({str(ref) for ref in (evidence_refs or []) if ref}),
        # Karar girdisi: anahtarlar sıralı, değerler sınırlı ve normalize.
        "decision_context": {
            str(key)[:64]: " ".join(str(value).split())[:MAX_DECISION_VALUE]
            for key, value in sorted((decision_context or {}).items())
            if str(value).strip()
        },
    }


def revision_of(plan: dict[str, Any]) -> str:
    """`plan-v1:<sha256>` — kanonik JSON üzerinden deterministik özet."""
    payload = json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{REVISION_VERSION}:{digest}"


def revision_version(revision: str) -> str:
    return revision.split(":", 1)[0] if ":" in revision else ""
