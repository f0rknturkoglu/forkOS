"""Skor evreni: uc skorun sinirlari TEK yerde.

forkOS bir ilanda UC ayri skor tasir ve bunlar karistirilmaz:

* **kalite skoru** (``opportunity.score``): kaynak/kural tabanli ilan kalitesi.
  ``-1..100``. ``-1`` = elendi (kill kelimesi yakalandi). ``None`` = hic
  hesaplanmadi. ``0`` ile ``None`` AYNI SEY DEGILDIR.
* **profil uyumu** (``opportunity.skill_match_ratio``): ``0..1`` arasi oran.
  ``None`` = hesaplanmadi (eski surumler bunu ``0`` yaziyordu ve "hesaplanmadi"
  filtresi is ilanlarinda asla eslesmiyordu).
* **tavsiye skoru** (``opportunity.candidate_evaluation.score``): CV ile iki asamali
  degerlendirmenin ``0..100`` sonucu.

Aralik esikleri buradan gelir; arayuzdeki preset listesi bununla ayni olmali
(bkz. ``frontend/src/modules/opportunity/scoreDomain.ts``).
"""

from __future__ import annotations

#: Kalite skorunun alt/ust siniri (router Query dogrulamasi da bunu kullanir).
SCORE_FLOOR = -1
SCORE_CAP = 100
#: Elenmis kaydin skoru.
SCORE_ELIMINATED = -1
#: "guclu" bandin esigi; arayuzdeki 70-79 / 80-100 bolunmesinin alt siniri.
SCORE_STRONG = 70
#: "orta" bandin esigi; 40-69 bandinin alt siniri.
SCORE_FAIR = 40

#: Degerlendirme bayatlama nedenleri (bkz. intelligence.evaluation_staleness).
STALE_VERSION = "version"
STALE_LISTING = "listing"
STALE_PROFILE = "profile"
STALE_MISSING = "missing"
