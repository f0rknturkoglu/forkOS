"""H7 — Durable Decision & Bounded Execution.

Bir insight'ı güvenli biçimde aksiyona çeviren katman: plan sözleşmesi,
deterministik doğrulama, SUNUCU TARAFI onay, sınırlı yürütme ve durable
makbuz. Canonical mutasyon yalnızca H1 üzerinden yapılır; H7 kendi fiil
dağarcığını uydurmaz ve otomatik onay/otomatik mutasyon içermez.

Entity tipi üretmez: bu motorun operasyonel durumudur.
"""

from __future__ import annotations

from app.modules import ModuleSpec
from app.modules.execution.router import router

MODULE = ModuleSpec(
    id="execution",
    title="Execution",
    router=router,
    entity_types=[],
    event_verbs=[],
)
