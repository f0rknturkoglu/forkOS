"""Agent epizodik oturum devri; aranabilir bir domain nesnesi değildir.

A3 yeni bir kanonik doğruluk sahibi DEĞİLDİR: ürettiği kayıtlar "önceki
oturumda böyle konuşuldu/sonuçlandı" anlamına gelen TARİHSEL iddialardır.
Todo, proje durumu, H2 hafızası, Vault bilgisi veya H7 yetkilendirmesi
değildir.
"""

from app.modules import ModuleSpec
from app.modules.agent_episode.router import router

MODULE = ModuleSpec(id="agent_episode", title="Agent episode", router=router)
