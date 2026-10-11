"""H7 adim sözleşmesi — KAPALI H1 aksiyon sözlüğü.

Bir adım serbest bir araç çağrısı DEĞİLDİR:

```text
{ step_id, ordinal, action, arguments, description, expected_updated_at }
```

`action` yalnızca `write_registry.ACTION_NAMES` içinden seçilebilir ve
`arguments` ilgili H1 girdi modeliyle doğrulanır. Böylece:

```text
shell / SQL / arbitrary http / delete / arbitrary tool name  → REDDEDİLİR
```

Yeni yetenek eklemek, H1'e fonksiyon eklemek demektir — H7 kendi fiil
dağarcığını uydurmaz (§4).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.integrations.agent.write_registry import ACTION_NAMES, BY_NAME, MAX_TEXT_ARGUMENT
from app.modules.execution.models import (
    MAX_ARGUMENT_BYTES,
    MAX_PLAN_STEPS,
    MAX_STEP_DESCRIPTION,
)


class StepError(Exception):
    """Sınırlı, model-okunur adım hatası."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ValidatedStep:
    step_id: str
    ordinal: int
    action: str
    arguments: dict[str, Any]
    description: str
    expected_updated_at: str | None
    expected_plan_fingerprint: str | None = None


def validate_steps(raw_steps: Any) -> list[ValidatedStep]:
    """Ham adım listesini doğrular; ilk hatada fail-closed durur.

    Doğrulama katmanı: yapı → sınırlar → KAPALI aksiyon kümesi → H1 girdi
    modeli. H1 modeli tek doğruluk kaynağıdır: argümanlar H1'in kendi
    şemasından geçmeden plan onaya hazır sayılmaz (§9).
    """
    if not isinstance(raw_steps, list) or not raw_steps:
        raise StepError("PLAN_HAS_NO_STEPS", "plan en az bir adım içermelidir")
    if len(raw_steps) > MAX_PLAN_STEPS:
        raise StepError("PLAN_BUDGET_EXCEEDED", f"adım sınırı {MAX_PLAN_STEPS}")

    validated: list[ValidatedStep] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_steps):
        if not isinstance(raw, dict):
            raise StepError("INVALID_STEP", "adım bir nesne olmalıdır")
        action = str(raw.get("action") or "").strip()
        if action not in ACTION_NAMES:
            # Bilinmeyen/yıkıcı eylem: sessizce yok sayılmaz, plan reddedilir.
            raise StepError("UNKNOWN_ACTION", f"bilinmeyen eylem: {action or '(boş)'}")
        spec = BY_NAME[action]

        arguments = raw.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise StepError("INVALID_STEP", "arguments bir nesne olmalıdır")
        encoded = json.dumps(arguments, ensure_ascii=False, default=str)
        if len(encoded.encode("utf-8")) > MAX_ARGUMENT_BYTES:
            raise StepError("PLAN_BUDGET_EXCEEDED", "adım argümanı çok büyük")
        for value in arguments.values():
            if isinstance(value, str) and len(value) > MAX_TEXT_ARGUMENT:
                raise StepError("PLAN_BUDGET_EXCEEDED", "adım metni çok uzun")

        try:
            data = spec.model(**arguments)
        except ValidationError as exc:
            first = exc.errors()[0] if exc.errors() else {}
            field = ".".join(str(part) for part in first.get("loc", ()) or ("?",))
            raise StepError(
                "INVALID_STEP_ARGUMENT", f"{action}: {field} geçersiz"
            ) from exc

        description = str(raw.get("description") or "")
        if len(description) > MAX_STEP_DESCRIPTION:
            raise StepError("INVALID_STEP", "adım açıklaması çok uzun")

        step_id = str(raw.get("step_id") or f"s{index + 1}")
        if step_id in seen:
            raise StepError("DUPLICATE_STEP_ID", f"adım kimliği tekrar ediyor: {step_id}")
        seen.add(step_id)

        validated.append(
            ValidatedStep(
                step_id=step_id,
                ordinal=index,
                action=action,
                # H1 modelinin normalize ettigi govde saklanir: plan, H1'in
                # gordugu seyin AYNISIDIR.
                arguments=json.loads(data.model_dump_json()),
                description=description,
                expected_updated_at=raw.get("expected_updated_at"),
            )
        )
    return validated


def step_payload(step: ValidatedStep) -> dict[str, Any]:
    """Adımı kalıcı/kanonik gövdeye çevirir."""
    return {
        "step_id": step.step_id,
        "action": step.action,
        "arguments": step.arguments,
        "description": step.description,
        "expected_updated_at": step.expected_updated_at,
        "expected_plan_fingerprint": step.expected_plan_fingerprint,
    }
