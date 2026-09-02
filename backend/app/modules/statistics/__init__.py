"""Istatistikler modulu.

Yeni tablo YOK: event (append-only, kural 3) + opportunity tablosu uzerine
salt-okunur toplamlardir. Kullanici istatistikleri heatmap'in altinda durur
(today widget), guncel hayat akisini bozmaz.
"""

from app.modules import ModuleSpec
from app.modules.statistics.router import router

MODULE = ModuleSpec(id="statistics", title="İstatistikler", router=router)
