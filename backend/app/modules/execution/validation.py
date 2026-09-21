"""H7 doğrulama — onaydan ÖNCE, deterministik, fail-closed.

Sıra (§9):

```text
yapı → sınırlar → KAPALI aksiyon kümesi + H1 şema doğrulaması
→ metin/argüman sınırları → kanıt referansı soyağacı
→ hedef varlığı + freshness damgası → bütçe
→ (varsa) input_required
```

Kullanıcıya "Approve" yalnızca `valid` sonuçta gösterilir. Model bağımsız
olarak "approved" iddia etse bile bu katman atlanamaz.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.integrations.agent.write_registry import BY_NAME
from app.modules.execution.models import (
    MAX_EVIDENCE_REFS,
    MAX_INPUT_QUESTIONS,
    MAX_PLAN_MUTATIONS,
    MAX_PLAN_REASON,
    MAX_PLAN_STEPS,
    MAX_PLAN_SUMMARY,
    MAX_PLAN_TITLE,
    MAX_SOURCE_REFS,
    MAX_VALIDATION_ERRORS,
)
from app.modules.execution.steps import StepError, ValidatedStep, validate_steps

#: Kanıt referansı SÖZDİZİMİ (uydurma provenance yasak, §10).
REF_PREFIXES: frozenset[str] = frozenset(
    {"entity", "event", "link", "vault", "h3", "proactivity", "review", "aggregate", "memory"}
)


@dataclass
class ValidationResult:
    status: str  # valid | invalid | input_required
    steps: list[ValidatedStep] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.status == "valid"


def _error(code: str, message: str, *, step_id: str | None = None) -> dict[str, Any]:
    return {"code": code, "message": message[:200], "step_id": step_id}


def _check_refs(refs: Any, *, label: str, limit: int, errors: list[dict[str, Any]]) -> list[str]:
    if refs is None:
        return []
    if not isinstance(refs, list):
        errors.append(_error("INVALID_REFS", f"{label} bir liste olmalıdır"))
        return []
    cleaned: list[str] = []
    for ref in refs:
        text = str(ref or "").strip()
        if not text:
            continue
        prefix = text.split(":", 1)[0]
        if prefix not in REF_PREFIXES:
            errors.append(_error("UNKNOWN_REF_SCHEME", f"{label}: bilinmeyen şema: {prefix}"))
            continue
        cleaned.append(text)
    if len(cleaned) > limit:
        errors.append(_error("BUDGET_EXCEEDED", f"{label}: en fazla {limit} referans"))
    return sorted(set(cleaned))[:limit]


async def _known_entities(session: AsyncSession, refs: list[str]) -> set[str]:
    """`entity:<uuid>` referanslarının GERÇEKTEN var olduğunu doğrular."""
    ids: list[uuid.UUID] = []
    for ref in refs:
        if not ref.startswith("entity:"):
            continue
        try:
            ids.append(uuid.UUID(ref.split(":", 1)[1]))
        except (ValueError, IndexError):
            continue
    if not ids:
        return set()
    rows = (await session.execute(select(Entity.id).where(Entity.id.in_(ids)))).scalars()
    return {str(item) for item in rows}


async def _target_state(
    session: AsyncSession, steps: list[ValidatedStep]
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Hedef kimliklerini ve GÜNCEL `updated_at` damgalarını toplar.

    Damga planın parçası olur: onay bu damgaya bağlanır, sonradan hedef
    değişirse adım stale olur (§15/§35).
    """
    stamps: dict[str, str] = {}
    errors: list[dict[str, Any]] = []
    ids: list[uuid.UUID] = []
    for step in steps:
        spec = BY_NAME[step.action]
        if spec.target_field is None:
            continue
        raw = step.arguments.get(spec.target_field)
        if raw is None:
            errors.append(
                _error("STEP_TARGET_REQUIRED", f"{step.action}: hedef kimliği zorunlu", step_id=step.step_id)
            )
            continue
        try:
            entity_id = uuid.UUID(str(raw))
        except (ValueError, AttributeError):
            errors.append(
                _error("STEP_TARGET_INVALID", f"{step.action}: hedef kimliği geçersiz", step_id=step.step_id)
            )
            continue
        ids.append(entity_id)

    if not ids:
        return stamps, errors
    rows = (
        await session.execute(select(Entity.id, Entity.updated_at).where(Entity.id.in_(ids)))
    ).all()
    found = {str(row.id): row.updated_at for row in rows}
    for step in steps:
        spec = BY_NAME[step.action]
        if spec.target_field is None:
            continue
        raw = step.arguments.get(spec.target_field)
        if raw is None:
            continue
        entity = found.get(str(raw))
        if entity is None:
            errors.append(
                _error("STEP_TARGET_MISSING", f"{step.action}: hedef bulunamadı", step_id=step.step_id)
            )
            continue
        stamps[step.step_id] = entity.isoformat()
    return stamps, errors


async def validate_plan(
    session: AsyncSession,
    *,
    title: str,
    summary: str | None,
    reason: str | None,
    steps: Any,
    source_refs: Any = None,
    evidence_refs: Any = None,
    input_questions: Any = None,
) -> ValidationResult:
    """Onaya hazırlık doğrulaması. Model çağrısı YOK, saf + deterministik."""
    errors: list[dict[str, Any]] = []

    text = str(title or "").strip()
    if not text:
        errors.append(_error("TITLE_REQUIRED", "plan başlığı zorunlu"))
    if len(text) > MAX_PLAN_TITLE:
        errors.append(_error("BUDGET_EXCEEDED", "başlık çok uzun"))
    if summary and len(str(summary)) > MAX_PLAN_SUMMARY:
        errors.append(_error("BUDGET_EXCEEDED", "özet çok uzun"))
    if reason and len(str(reason)) > MAX_PLAN_REASON:
        errors.append(_error("BUDGET_EXCEEDED", "gerekçe çok uzun"))

    clean_source = _check_refs(source_refs, label="source_refs", limit=MAX_SOURCE_REFS, errors=errors)
    clean_evidence = _check_refs(
        evidence_refs, label="evidence_refs", limit=MAX_EVIDENCE_REFS, errors=errors
    )

    questions: list[str] = []
    if input_questions:
        if not isinstance(input_questions, list):
            errors.append(_error("INVALID_INPUT_REQUEST", "input_questions bir liste olmalıdır"))
        else:
            questions = [str(item).strip()[:200] for item in input_questions if str(item).strip()]
            if len(questions) > MAX_INPUT_QUESTIONS:
                errors.append(_error("BUDGET_EXCEEDED", "soru sayısı sınırı aşıldı"))

    try:
        validated = validate_steps(steps)
    except StepError as exc:
        errors.append(_error(exc.code, exc.message))
        return ValidationResult("invalid", [], errors[:MAX_VALIDATION_ERRORS], questions)

    if len(validated) > MAX_PLAN_MUTATIONS:
        errors.append(_error("PLAN_BUDGET_EXCEEDED", f"mutasyon sınırı {MAX_PLAN_MUTATIONS}"))
    if len(validated) > MAX_PLAN_STEPS:
        errors.append(_error("PLAN_BUDGET_EXCEEDED", f"adım sınırı {MAX_PLAN_STEPS}"))

    # Kanıt soyağacı: entity referansları GERÇEK olmalı (uydurma provenance yasak).
    known = await _known_entities(session, [*clean_source, *clean_evidence])
    for ref in [*clean_source, *clean_evidence]:
        if ref.startswith("entity:") and ref.split(":", 1)[1] not in known:
            errors.append(_error("UNKNOWN_SOURCE_REF", f"kanıt referansı çözülemedi: {ref}"))

    # Hedef varlığı + freshness damgası.
    stamps, target_errors = await _target_state(session, validated)
    errors.extend(target_errors)
    if not errors:
        validated = [
            ValidatedStep(
                step_id=step.step_id,
                ordinal=step.ordinal,
                action=step.action,
                arguments=step.arguments,
                description=step.description,
                expected_updated_at=stamps.get(step.step_id, step.expected_updated_at),
            )
            for step in validated
        ]

    if errors:
        return ValidationResult("invalid", validated, errors[:MAX_VALIDATION_ERRORS], questions)
    if questions:
        # Eksik bilgi varsa "Approve" SUNULMAZ: önce kullanıcı cevabı gerekir.
        return ValidationResult("input_required", validated, [], questions)
    return ValidationResult("valid", validated, [], [])
