"""H6 — proaktivite ve dikkat kontrolu.

forkOS'un KENDILIGINDEN ne zaman devreye girecegine karar veren katman.
Tek soru: "simdi kullaniciya dokunmali miyiz?" (H6 = WHEN).
Baglam H5'ten gelir (WHAT), muhakeme Hermes'indir, canonical degisiklik
yalnizca H1 ile ve kullanici onayiyla olur.

Kurallar KAPALI bir kume; genel bir otomasyon DSL'i, zamanlanmis serbest
istem veya otomatik mutasyon YOKTUR. Entity tipi uretmez: bu motorun
operasyonel durumudur, aranabilir/linklenebilir nesne degil.
"""

from __future__ import annotations

from app.modules import ModuleSpec
from app.modules.proactivity.router import router

MODULE = ModuleSpec(
    id="proactivity",
    title="Proactivity",
    router=router,
    entity_types=[],
    event_verbs=[],
)
