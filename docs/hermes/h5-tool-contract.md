# forkOS × Hermes — H5 Araç Sözleşmesi (`forkos_review_intelligence`)

H5 genel yüzeye **tam olarak bir** araç ekler. Yüzey **27** olur
(H0 8 + H1 11 + H2 5 + H3 1 + H4 1 + H5 1). Mikro-araç çoğaltması YOKTUR:
tek araç, beş mod.

---

## 1. İmza

```text
forkos_review_intelligence(
    mode:             "continuity" | "daily_close" | "weekly_review"
                    | "period_delta" | "consolidation_review",   # ZORUNLU
    since:            str | None = None,        # saat dilimli ISO-8601, ≤ 40
    until:            str | None = None,        # saat dilimli ISO-8601, ≤ 40
    reference_date:   str | None = None,        # YYYY-MM-DD, ≥ 10
    focus_entity_id:  str | None = None,        # UUID, ≤ 64
    include_knowledge: bool = True              # bilgi/vault adayları dâhil mi
)
```

Anotasyonlar:

```text
readOnlyHint    = true
destructiveHint = false
idempotentHint  = true
```

Çıktı `AgentEnvelope` İLE SARILMAZ: dönen gövde doğrudan
`ReviewIntelligenceResponse`'tur. H5 **salt-okunurdur** ve aynı girdiyle aynı
çıktıyı üretir (deterministik kaynak sıralaması: `domain`, sonra `ref`).

### 1.1 İç düğmeler genel yüzeyde YOKTUR

Genel yüzeyde **asla** bulunmayanlar:

```text
model · model_id · provider · base_url · endpoint · temperature
h4_enabled · scan_limit · max_events · budget · include_daily_notes
timeout · api_key · prompt · system_prompt · store_summary · persist
```

Model, sağlayıcı, tarama tavanı ve günlük not okuma gibi iç düğmeler
**yapılandırma ve iç politika**dır; genel yüzey semantiktir. `include_knowledge`
tek genişlik anahtarıdır ve etkisi moda göre değişir:

```text
continuity / daily_close / weekly_review   false → bilgi/vault adayları
                                                  (terfi, bilgi sağlığı,
                                                  yeniden yüzey) ve günlük not
                                                  paketi üretilmez
consolidation_review                       false → bilgi sağlığı ve yeniden
                                                  yüzey üretilmez; operasyonel
                                                  terfi adayları KALIR
period_delta                               REDDEDİLİR (INVALID_ARGUMENT):
                                           bu mod bilgi alanı taşımaz, bayrak
                                           sessizce yok sayılmaz (§124)
```

---

## 2. Mod başına argüman kuralları

| Mod | Kabul edilen argümanlar | Zorunlu | Reddedilen |
|---|---|---|---|
| `continuity` | `since?`, `until?`, `focus_entity_id?`, `include_knowledge?` | — | `reference_date` |
| `daily_close` | `reference_date?`, `include_knowledge?` | — | `since`, `until`, `focus_entity_id` |
| `weekly_review` | `reference_date?`, `include_knowledge?` | — | `since`, `until`, `focus_entity_id` |
| `period_delta` | `since` + `until?`, `focus_entity_id?` | **`since`** | `reference_date`, `include_knowledge=false` |
| `consolidation_review` | `since?`, `until?`, `focus_entity_id?`, `include_knowledge?` | — | `reference_date` |

Uyumsuz argüman sessizce YOK SAYILMAZ: `INVALID_ARGUMENT` döner. Bilinmeyen mod
`INVALID_MODE` ile reddedilir (`project_resume` gibi ertelenmiş modlar dâhil).

```text
include_knowledge=false etkisi
  continuity / daily_close / weekly_review → bilgi/vault adayları ve günlük notlar atlanır
  consolidation_review                     → bilgi sağlığı + yeniden yüzey atlanır
  period_delta                             → REDDEDİLİR (INVALID_ARGUMENT)
```

---

## 3. Zaman semantiği

```text
since / until     saat dilimli ISO-8601 ZORUNLU (ör. 2026-09-20T09:00:00+03:00 veya ...Z)
                  naif damga (2026-09-20T09:00:00) REDDEDİLİR → INVALID_TIME_RANGE
                  sessiz yerel saat varsayımı YOKTUR
reference_date    YYYY-MM-DD; saat dilimi yerel takvimden okunur
until ≤ since     INVALID_TIME_RANGE
```

| Mod | Dönem |
|---|---|
| `continuity` | `since` verilmişse oradan; yoksa çapadan (en fazla 120 gün geriye) bugüne |
| `daily_close` | `reference_date` günü (varsayılan: yerel bugün); `days=1` |
| `weekly_review` | `reference_date`'in içinde bulunduğu **Pazartesi–Pazar** haftası; `days=7` |
| `period_delta` | `since` → `until` (varsayılan `until`: şimdi); en fazla **31 gün** |
| `consolidation_review` | `since` verilirse `since` → `until` (≤ 31 gün); verilmezse içinde bulunulan haftanın Pazartesi'sinden şimdiye |

Yerel takvim günleri saat dilimi kaydırmasına karşı korunur: haftalık dönem
her zaman tam 7 günlük günlük not beklentisi üretir.

```text
gün henüz bitmedi        → partial=true, comparable=false
hafta henüz bitmedi      → partial=true, comparable=false
until verilmedi          → partial=true, comparable=false
since verilmedi (konsolidasyon) → partial=true, comparable=false
continuity               → HER ZAMAN partial=true, comparable=false
dönem tamamlandı         → partial=false, comparable=true
```

`comparable=false` iken sayısal karşılaştırma iddia edilmez. Haftalık modda bu
durum ayrıca `PARTIAL_PERIOD` uyarısıyla bildirilir; tüm modlarda
`coverage.partial` ve `coverage.comparable` bayrakları doğruyu söyler.

---

## 4. Çıktı

```text
ReviewIntelligenceResponse {
    mode:            "continuity" | "daily_close" | "weekly_review"
                   | "period_delta" | "consolidation_review"
    coverage:        Coverage          { period_start, period_end, days,
                                         partial, comparable, reference_date }
    payload:         moda göre tipli paket (ContinuityBundle | DailyCloseBundle
                     | WeeklyReviewBundle | PeriodDeltaBundle | ConsolidationBundle)
    sources:         SourceRef[]        incelenebilir kaynak referansları
    evidence:        dict[]             doğrudan H3 EvidenceItem'ları (opsiyonel)
    source_manifest: SourceManifest     H5 gerçekte NEYE baktı
    trace:           TraceStepRecord[]  sınırlı olgusal iz (düşünme zinciri DEĞİL)
    warnings:        string[]           sınırlı kod listesi (≤ 20)
    truncated:       bool               herhangi bir tavan devreye girdi mi
}
```

`SourceRef`:

```text
ref · domain(operational|review|vault|evidence|aggregate) · kind · title
timestamp · entity_id · evidence_id · locator · excerpt · truncated
```

`TraceStepRecord`:

```text
step · considered · accepted · truncated
```

İz adımları (kapalı küme): `period_resolved`, `review_preview_loaded`,
`previous_review_loaded`, `events_loaded`, `daily_notes_loaded`,
`deadlines_loaded`, `projects_checked`, `h3_evidence_loaded`,
`h4_candidates_extracted`, `knowledge_health_checked`, `budget_applied`.

`SourceManifest` — kapsam dürüstlüğünün taşıyıcısı:

```text
events_considered · reviews_considered · entities_considered · projects_considered
deadlines_considered · daily_notes_expected · daily_notes_found · daily_notes_missing
vault_sources[] · h3_evidence_ids[] · hot_memory_checked · h4_used · truncated
```

---

## 5. Sınırlar

| Alan | Sınır |
|---|---|
| Event taraması | 500 kayıt (+1 nöbetçi ile taşma ölçülür) |
| Kaynak referansı (`sources`) | 100 |
| H3 kanıt öğesi | 100 (`evidence` ve `h3_evidence_ids`) |
| Insight | 30 (`text` ≤ 400) |
| Açık döngü | 20 |
| Son tarih | 15 |
| Dikkat adayı | 15 |
| Terfi adayı | 20 (`text` ≤ 500) |
| Bilgi sağlığı adayı | 10 |
| Yeniden yüzey adayı | 3 |
| Uyarı | 20 (her biri ≤ 300 karakter) |
| Günlük not | 7 dosya × 4000 karakter |
| H4 kaynak paketi | 20000 karakter × 12 parça; aday çıkarımı ≤ 2 çağrı |
| Yerine geçme karşılaştırması | 5 aday (`decision` / `project_knowledge`) |
| H3 öğesi / aday | 3 |
| Aktif iş parçası | 10 |
| Günün işi / son tamamlanan / öncelik | 20 / 20 / 10 |
| Kaynak ref uzunluğu | ≤ 200 karakter |
| Özel dönem | ≤ 31 gün |
| Süreklilik çapası geriye bakış | ≤ 120 gün |

Eşikler:

```text
durağan proje              14 gün
yeniden yüzey yaşı         30 gün
yaklaşan son tarih          7 gün (gerekçe kodları: 1 / 3 / 7)
okunmamış birikim eşiği    20
```

Tavanlar **kırpma** ile uygulanır ve `truncated=true` + ilgili uyarı koduyla
bildirilir; aralık dışı **girdi** ise kırpılmaz, hata döner.

---

## 6. Hata kodları

| Kod | Anlam |
|---|---|
| `INVALID_MODE` | Mod beşli kümede değil |
| `INVALID_ARGUMENT` | Mod/argüman uyumsuzluğu, `period_delta`'da `since` yok |
| `INVALID_TIME_RANGE` | Damga ISO-8601 değil, saat dilimi yok ya da `until ≤ since` |
| `INVALID_REFERENCE_DATE` | `reference_date` `YYYY-MM-DD` değil |
| `INVALID_FOCUS_ENTITY` | `focus_entity_id` UUID değil veya varlık yok |
| `PERIOD_TOO_LARGE` | Özel dönem 31 günü aştı |

Hata zarfı sızdırmazdır: beklenmeyen iç hata `REVIEW_INTELLIGENCE_FAILED: <Tip>`
olarak döner; yığın izi, SQL veya dosya yolu taşınmaz.

---

## 7. Uyarı kodları

Uyarılar hata DEĞİLDİR: H5 bozulmuş modda da yanıt üretir ve neyin eksik
olduğunu söyler.

| Kod | Ne zaman görünür |
|---|---|
| `PARTIAL_PERIOD` | Dönem tamamlanmadı; sayısal karşılaştırma yapılmadı |
| `MISSING_DAILY_NOTES` | Dönemde beklenen günlük notlardan biri/birkaçı yok |
| `VAULT_UNAVAILABLE` | Kasa yapılandırılmamış/erişilemez; bilgi okuması YAPILMAZ (boş liste "bilgi yok" gibi okunmasın diye açıkça bildirilir) |
| `EVENT_SCAN_TRUNCATED` | Event taraması tavana ulaştı |
| `NO_PREVIOUS_REVIEW` | Karşılaştırılacak önceki Review yok |
| `NO_MEANINGFUL_ACTIVITY` | Sayılan kullanıcı hareketi bulunamadı; çapa `fallback` |
| `PRIORITY_RECEIPTS_UNAVAILABLE` | Önceki Review makbuz taşımıyor; tamamlanma durumu İDDİA EDİLMEZ |
| `H4_UNAVAILABLE` | Yerel biliş kapalı/erişilemez; çıktı deterministik kalır |
| `SOURCE_PACKET_TRUNCATED` | H4'e gönderilen kaynak paketi sınırlı kısmıyla kullanıldı |
| `AMBIGUOUS_CANDIDATE_SOURCE` | Adayın alıntısı birden fazla parçada geçiyor; aday atlandı |
| `CONFLICTING_KNOWLEDGE` | İndekste çelişen kimlik veya geçersiz metadata var; bilgi sinyallerinin kapsamı daralır (aday düzeyinde `managed_source_conflict` ile birlikte) |
| `KNOWLEDGE_HEALTH_TRUNCATED` | Bilgi sağlığı adayı tavanına ulaşıldı |
| `H3_EVIDENCE_UNAVAILABLE` | Kanıt katmanı erişilemez; bilgi sağlığı adayı üretilmedi |
| `DEADLINE_SCAN_TRUNCATED` | Son tarih taraması tavana ulaştı |

---

## 8. Kaynak ref sözdizimi

```text
event:<id>                          kanonik olay
entity:<uuid>                       kanonik varlık (todo, proje, fırsat, son tarih…)
review:<uuid>                       kabul edilmiş Review kaydı
vault:<göreli yol>:L<başlangıç>-L<bitiş>   günlük not / yönetilen not satır aralığı
h3:<evidence_id>                    H3 kanıt öğesi
aggregate:<metrik>:<pencere>        türetilmiş ölçüm (ör. review_preview, rss_unread)
plan_slot:<uuid>                    plan kaydı
notification:<id>                   bildirim
hot_memory:<id>                     sıcak hafıza öğesi (bağlam; tarihsel kanıt DEĞİL)
```

Ref'ler **mutlak dosya yolu taşımaz** ve deterministiktir: aynı durum için aynı
ref üretilir. `vault:` ref'leri göreli yol + satır aralığı taşır, böylece alıntı
denetlenebilir.

---

## 9. Örnek çıktı iskeleti

### 9.1 Süreklilik — istek

```json
{
  "mode": "continuity",
  "focus_entity_id": null,
  "include_knowledge": true
}
```

Yanıt (kısaltılmış, sentetik veriyle uyarlanmış):

```json
{
  "mode": "continuity",
  "coverage": {
    "period_start": "2026-09-06T09:00:00+03:00",
    "period_end": "2026-09-20T14:05:00+03:00",
    "days": 14,
    "partial": true,
    "comparable": false,
    "reference_date": null
  },
  "payload": {
    "anchor": {
      "kind": "last_meaningful_activity",
      "timestamp": "2026-09-06T09:00:00+03:00",
      "source_ref": "event:1042",
      "entity_id": null,
      "verb": "pomodoro.completed"
    },
    "activity_gap_hours": 341.08,
    "recent_completed": [
      {
        "type": "win",
        "text": "Tamamlandı: Veri yapıları ödevi",
        "support_refs": ["entity:6f1c9f3e-0000-4000-8000-000000000001"],
        "source_count": 1,
        "temporal_start": "2026-09-06T08:40:00+03:00",
        "temporal_end": null,
        "status": "fact"
      }
    ],
    "state_changes": [],
    "time_sensitive_changes": [
      {
        "type": "time_sensitive",
        "text": "Burs başvurusu için son tarih 3 gün içinde.",
        "support_refs": ["entity:6f1c9f3e-0000-4000-8000-000000000002"],
        "source_count": 1,
        "temporal_start": null,
        "temporal_end": "2026-09-23T17:00:00+03:00",
        "status": "fact"
      }
    ],
    "newly_overdue": [],
    "upcoming_deadlines": [
      {
        "entity_id": "6f1c9f3e-0000-4000-8000-000000000002",
        "type": "opportunity",
        "title": "Burs başvurusu",
        "due_at": "2026-09-23T17:00:00+03:00",
        "module": "opportunity",
        "sub_kind": "application",
        "priority": null,
        "remaining_days": 3,
        "remaining_seconds": 277200
      }
    ],
    "unread_accumulation": {
      "new_unread_since_anchor": 0,
      "current_unread_total": 6,
      "top_sources": [],
      "support_refs": ["aggregate:rss_unread_since:2026-09-06T09:00:00+03:00"]
    },
    "passed_plans_still_open": [],
    "open_loops": [
      {
        "kind": "project_next_action",
        "title": "Rust öğrenme",
        "entity_id": "6f1c9f3e-0000-4000-8000-000000000003",
        "detail": "sonraki adım tanımlı değil",
        "due_at": null,
        "support_refs": ["entity:6f1c9f3e-0000-4000-8000-000000000003"]
      }
    ],
    "active_threads": [
      {
        "kind": "project",
        "title": "Rust öğrenme",
        "entity_id": "6f1c9f3e-0000-4000-8000-000000000003",
        "detail": "sonraki adım yok",
        "support_refs": ["entity:6f1c9f3e-0000-4000-8000-000000000003"]
      }
    ],
    "learning_resume": null,
    "stalled_projects": [
      {
        "type": "stalled",
        "text": "'Rust öğrenme' projesinde 14 gündür kayıtlı anlamlı hareket yok.",
        "support_refs": ["entity:6f1c9f3e-0000-4000-8000-000000000003"],
        "source_count": 1,
        "temporal_start": null,
        "temporal_end": null,
        "status": "fact"
      }
    ],
    "attention_candidates": [
      {
        "reason": "deadline_3d",
        "text": "Burs başvurusu için son tarih 3 gün içinde.",
        "support_refs": ["entity:6f1c9f3e-0000-4000-8000-000000000002"],
        "entity_id": null,
        "due_at": "2026-09-23T17:00:00+03:00",
        "remaining_days": 3
      },
      {
        "reason": "project_without_next_action",
        "text": "'Rust öğrenme' projesinin sonraki adımı tanımlı değil.",
        "support_refs": ["entity:6f1c9f3e-0000-4000-8000-000000000003"],
        "entity_id": "6f1c9f3e-0000-4000-8000-000000000003",
        "due_at": null,
        "remaining_days": null
      },
      {
        "reason": "project_inactive",
        "text": "'Rust öğrenme' projesinde 14 gündür kayıtlı anlamlı hareket yok.",
        "support_refs": ["entity:6f1c9f3e-0000-4000-8000-000000000003"],
        "entity_id": null,
        "due_at": null,
        "remaining_days": null
      }
    ],
    "knowledge_changes": [],
    "resurface_candidates": [],
    "focus_entity": null
  },
  "sources": [
    {
      "ref": "aggregate:rss_unread_since:2026-09-06T09:00:00+03:00",
      "domain": "aggregate",
      "kind": "rss_unread",
      "title": "okunmamış içerik",
      "timestamp": null,
      "entity_id": null,
      "evidence_id": null,
      "locator": null,
      "excerpt": null,
      "truncated": false
    },
    {
      "ref": "entity:6f1c9f3e-0000-4000-8000-000000000003",
      "domain": "operational",
      "kind": "project",
      "title": "Rust öğrenme",
      "timestamp": "2026-09-06T09:00:00+03:00",
      "entity_id": "6f1c9f3e-0000-4000-8000-000000000003",
      "evidence_id": null,
      "locator": null,
      "excerpt": null,
      "truncated": false
    }
  ],
  "evidence": [],
  "source_manifest": {
    "events_considered": 42,
    "reviews_considered": 0,
    "entities_considered": 0,
    "projects_considered": 3,
    "deadlines_considered": 1,
    "daily_notes_expected": 0,
    "daily_notes_found": 0,
    "daily_notes_missing": 0,
    "vault_sources": [],
    "h3_evidence_ids": [],
    "hot_memory_checked": 0,
    "h4_used": false,
    "truncated": false
  },
  "trace": [
    {"step": "period_resolved", "considered": 1, "accepted": 1, "truncated": false},
    {"step": "events_loaded", "considered": 42, "accepted": 42, "truncated": false},
    {"step": "deadlines_loaded", "considered": 1, "accepted": 1, "truncated": false},
    {"step": "projects_checked", "considered": 3, "accepted": 3, "truncated": false},
    {"step": "knowledge_health_checked", "considered": 3, "accepted": 0, "truncated": false}
  ],
  "warnings": [],
  "truncated": false
}
```

### 9.2 Mod bazlı paket iskeleti

```text
daily_close          { day, review_preview, completed_outcomes[], focus_summary,
                       open_todos[], newly_overdue[], upcoming[], open_loops[],
                       promotion_candidates[], carry_forward_candidates[], daily_note }

weekly_review        { current_snapshot, previous_review, comparison,
                       declared_priorities[], priority_outcomes[], body_of_work[],
                       focus_distribution, changes[], wins[], open_loops[],
                       stalled_projects[], upcoming[], time_sensitive_changes[],
                       promotion_candidates[], knowledge_health[],
                       resurface_candidates[], carry_forward_candidates[] }

period_delta         { completed[], created[], closed[], opened[], status_changes[],
                       focus, deadline_changes[], new_announcements[],
                       applications[], project_changes[], open_loops[], focus_entity }

consolidation_review { promotion_candidates[], possible_open_loops[],
                       knowledge_health[], resurface_candidates[],
                       daily_notes[], source_fragments }
```

---

## 10. Özet semantiği (kritik)

```text
support_refs boş olamaz       her olgu (status="fact") kanıt taşır; kaynaksız
                              gözlem olgu olarak SUNULMAZ
status="fact"                 kanonik okuma; support_refs zorunlu
status="candidate"            kural/model kaynaklı olasılık; doğruluk DEĞİL
suggested_destination         ÖNERİ; H5 buraya YAZMAZ
source_manifest               "ne kadar gördüm" beyanı; sessiz kırpma YOK
warnings                      eksik/bozuk kaynağın dürüst beyanı
```

Yanıt **düzyazı değildir**: yapı, kaynak ve iz döner; anlatıyı Hermes kurar.
H5 hiçbir koşulda özeti kalıcı olarak saklamaz, hiçbir kaydı güncellemez.

---

## 11. Yüzey doğrulaması

```text
H0 = 8    H1 = 11    H2 = 5    H3 = 1    H4 = 1    H5 = 1    TOPLAM = 27
```

Kanıt dosyaları: `test_agent_h5_contract.py` (yüzey 27, tek yeni araç,
anotasyonlar, şema, yasak iç düğmeler), `test_agent_h5_transport.py` (gerçek
`/mcp` taşıması ve değişmezlik), `test_h5_models.py` (mod doğrulaması, zaman
semantiği, sınırlar, kimlikler, puan alanı yokluğu), `test_h5_continuity.py`
(çapa, iki grup ayrımı, gerekçe sıralaması, determinizm), `test_h5_review.py`
(gün kapanışı, haftalık, dönem deltası), `test_h5_consolidation.py` ve
`test_h5_knowledge.py` (adaylar, kaynak kilidi, bilgi sağlığı),
`test_review_priority_receipts.py` (makbuz semantiği), `h5_fixtures.py`
(sentetik dünya).
