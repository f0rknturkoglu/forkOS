# forkOS × Hermes — H5 Gözden Geçirme Zekâsı (Review Intelligence)

H5, Hermes'in şu sorularına **kanonik duruma bağlı**, **sınırlı** ve
**deterministik** bir zemin verir:

```text
"nerede kalmıştım?"            → continuity
"gün nasıl kapandı?"           → daily_close
"bu hafta ne oldu?"            → weekly_review
"şu iki an arasında ne değişti?" → period_delta
"hangi geçici bilgi kalıcılığı hak ediyor?" → consolidation_review
```

H5 bir sohbet botu, otomatik özet yazıcısı, hafıza yazıcısı, doğruluk sahibi,
arka plan işçisi, zamanlayıcı veya üretkenlik ölçer **değildir**. Yalnızca
**okur, toplar, işaretler ve kaynak gösterir**; anlatıyı Hermes kurar.

---

## 1. Sorumluluk paylaşımı

```text
Hermes   → hangi soruyu soracağına ve anlatıyı nasıl kuracağına karar verir
H5       → kanonik durumu DETERMİNİSTİK olarak toplar; kapsamı dürüstçe bildirir
H4       → (isteğe bağlı) aday çıkarır / yerine geçme sınıflandırır — doğruluk DEĞİL
H3       → (isteğe bağlı) kökenli kanıt getirir — yorum YAPMAZ
H1       → yalnızca kullanıcı onayından sonra kanonik yazmayı yapar
```

> **H5 hiçbir doğruluğa sahip değildir ve hiçbir şey yazmaz.** Entity, Link,
> Event, Todo, Review, Vault veya Sıcak Hafıza mutasyonu yoktur; kalıcı aday
> tablosu yoktur; otomatik özet saklama yoktur. Kanonik yazma yolu H1'dir.

---

## 2. Akış

```text
kanonik durum + Review + Event + son tarihler + günlük notlar + H3 kanıtı
        ↓  deterministik kaynak montajı (sources.py)
isteğe bağlı H4 aday çıkarımı / sınıflandırması (consolidation.py)
        ↓  kaynak kilidi (her olgu support_refs taşır)
ReviewIntelligenceResponse
        ↓  Hermes muhakemesi
        ↓  (isteğe bağlı) H1 onaylı yazmalar
```

Modül düzeni:

```text
review_intelligence/
  models.py         sözleşmeler, sınırlar, kodlar, Collector
  policy.py         SAF politika: mod/argüman uyumu, sıralama, varış yeri
  sources.py        sınırlı kanonik okumalar (yalnız OKUR)
  continuity.py     "nerede kalmıştım?" montajı
  review.py         gün kapanışı, haftalık, dönem deltası, konsolidasyon montajı
  consolidation.py  terfi / açık döngü / bilgi sağlığı / yeniden yüzey adayları
  service.py        ince: doğrulama → mod dağıtımı → nihai paket montajı
```

`service.py` bilerek incedir: muhakeme modüllerde, politika `policy.py`'de,
okumalar `sources.py`'de yaşar. Servis yalnızca **girdi doğrulama → mod
dağıtımı → kapsam/bütçe koordinasyonu → bozulmuş mod davranışı → paket
montajı** yapar.

---

## 3. FACT / CANDIDATE / SUGGESTION ayrımı

Yanıt tek bir düz metin değildir; üç farklı güven düzeyi **yapısal olarak**
ayrılır.

| Düzey | Alanlar | Ne demek |
|---|---|---|
| **FACT** (`status="fact"`) | `CanonicalOpenLoop`, `recent_completed`, `state_changes`, `time_sensitive_changes`, `newly_overdue`, `changes`, `wins`, `completed`/`created`/`closed`/`opened` | Kanonik durumdan deterministik okuma; her biri `support_refs` taşır |
| **CANDIDATE** (`status="candidate"`) | `PromotionCandidate`, `KnowledgeHealthCandidate`, `PossibleOpenLoop`, `ResurfaceCandidate` | Kural ya da yerel model kaynaklı **olasılık**; doğruluk değildir, yazma değildir |
| **SUGGESTION** | `suggested_destination`, `carry_forward_candidates`, `ThreadRef` (iş parçası) | Yön/öncelik önerisi; **eylem değildir**, kararı Hermes ve kullanıcı verir |

Dikkat adayları (`AttentionCandidate`) bu üçlüde ayrı durur: deterministik
olgulardan türetilir, gerekçe kodu taşır ve **emir değildir** (§7).

```text
olgu        = "X kanonik olarak açık ve kaynağı şu"
aday        = "X kalıcı bilgi olmayı hak ediyor OLABİLİR"
öneri       = "X için önerilen varış yeri todo"
```

Kritik ayrım: **aday bir hafıza değildir**, **özet bir kanıt değildir**,
**yerel model çıktısı bir doğruluk değildir**. Ayrıntılı politika:
[H5 Kaynak ve Konsolidasyon Politikası](h5-source-and-consolidation-policy.md).

---

## 4. Beş mod

| Mod | Soru | Zorunlu argüman | Paket tipi |
|---|---|---|---|
| `continuity` | "nerede kalmıştım?" | — | `ContinuityBundle` |
| `daily_close` | "gün nasıl kapandı?" | — | `DailyCloseBundle` |
| `weekly_review` | "bu hafta ne oldu?" | — | `WeeklyReviewBundle` |
| `period_delta` | "iki an arasında ne değişti?" | **`since`** | `PeriodDeltaBundle` |
| `consolidation_review` | "ne kalıcılığı hak ediyor?" | — | `ConsolidationBundle` |

Mod, **tek araç** üzerinden seçilir: `forkos_review_intelligence`. Mikro-araç
çoğaltması (`forkos_weekly_summary`, `forkos_consolidate`, …) YOKTUR.
Mod/argüman uyumu çalışma zamanında doğrulanır; uyumsuz argüman sessizce
**yok sayılmaz** (`INVALID_ARGUMENT`). Sözleşme ayrıntısı:
[H5 Araç Sözleşmesi](h5-tool-contract.md).

### 4.1 Mod paketlerinin omurgası

```text
continuity            anchor · activity_gap_hours · recent_completed · state_changes
                      time_sensitive_changes · newly_overdue · upcoming_deadlines
                      unread_accumulation · passed_plans_still_open · open_loops
                      active_threads · learning_resume · stalled_projects
                      attention_candidates · knowledge_changes · resurface_candidates
                      focus_entity

daily_close           day · review_preview · completed_outcomes · focus_summary
                      open_todos · newly_overdue · upcoming · open_loops
                      promotion_candidates · carry_forward_candidates · daily_note

weekly_review         current_snapshot · previous_review · comparison
                      declared_priorities · priority_outcomes · body_of_work
                      focus_distribution · changes · wins · open_loops
                      stalled_projects · upcoming · time_sensitive_changes
                      promotion_candidates · knowledge_health · resurface_candidates
                      carry_forward_candidates

period_delta          completed · created · closed · opened · status_changes · focus
                      deadline_changes · new_announcements · applications
                      project_changes · open_loops · focus_entity

consolidation_review  promotion_candidates · possible_open_loops · knowledge_health
                      resurface_candidates · daily_notes · source_fragments
```

Paket tipi moda göre **tiplidir**: Hermes hangi modda hangi alanları
bekleyeceğini şemadan bilir.

---

## 5. Süreklilik felsefesi — "nerede kalmıştım?"

Süreklilik iki grup değişikliği **ayırır**:

```text
KULLANICI HAREKETİ   sayılan fiiller (contributions.COUNTED_VERBS)
                     ör. pomodoro.completed, todo.completed
ZAMAN / DIŞ DURUM    son tarihler yaklaştı, görev gecikti, plan geçti,
                     RSS birikti, yeni ilan geldi, bildirim birikti
```

Kullanıcı hiçbir şey yapmamış olsa bile ikinci grup değişir ve bu
`time_sensitive_changes` içinde **görünür** — ama birincisinin yerine geçmez.
Bu yüzden süreklilik "hiçbir şey yapmadın" demez; **iki olguyu yan yana koyar**.

### 5.1 Çapa (anchor)

```text
explicit                  Hermes açık bir `since` verdi
last_meaningful_activity  sayılan son insan hareketi bulundu (verb + timestamp)
previous_review           sayılan hareket yok, ama kabul edilmiş bir Review var:
                          çapa o Review'ın bittiği YEREL günün başlangıcı
fallback                  hiçbiri yok: dönem başı + NO_MEANINGFUL_ACTIVITY uyarısı
```

Her çapa türü GERÇEK bir damgaya karşılık gelir; `previous_review` "son gözden
geçirmeden beri sessiz" demenin dürüst yoludur. Hiçbiri yoksa çapa **asla**
uydurulmaz.

**Uydurma "son kez" YOKTUR.** Çapa bulunamazsa tarih icat edilmez; `fallback`
kullanılır ve uyarı verilir. Worker gürültüsü (feed çekimi, kaynak senkronu,
sağlık kayıtları) **kullanıcı emeği sayılmaz**.

Süreklilik çapası geriye en fazla 120 gün bakar: çapa daha eski olabilir ama
tarama sınırsız olamaz.

### 5.2 Yanında gelen olgular

```text
recent_completed          son tamamlanan işler (kanonik kimlikle)
state_changes             yeni kayıt/bildirim gibi durum değişiklikleri
newly_overdue             bu pencerede son tarihi geçen kanonik döngüler
upcoming_deadlines        yaklaşan son tarihler (kalan gün ile)
passed_plans_still_open   planlanan zamanı geçmiş, hâlâ açık görevler
unread_accumulation       okunmamış birikimi (yüzlerce başlık DÖKÜLMEZ)
active_threads            sınırlı iş parçası listesi (≤ 10)
learning_resume           öğrenme/odak bağlamına dönüş zemini
stalled_projects          yalnızca "hareket yok" olgusu (gerekçe değil)
focus_entity              Hermes bir varlık verdiyse o varlığın sınırlı kesiti
```

---

## 6. Neden hareketin durduğu ASLA çıkarılmaz

H5 **neden**'i üretmez. "Yoruldun", "motivasyonunu kaybettin", "dinlenmen
gerekiyor" gibi bir cümle yapısal olarak kurulmaz: kaynak kodda böyle bir
şablon yoktur ve `test_h5_continuity.py` yanıtın tamamında bu tür sözcüklerin
**hiç geçmediğini** doğrular.

```text
SÖYLENEN     "'Rust öğrenme' projesinde 21 gündür kayıtlı anlamlı hareket yok."
SÖYLENMEYEN  "... çünkü motivasyonunu kaybettin / yoğundun / yoruldun."
```

Nedensellik Hermes'in (ya da kullanıcının) işidir; H5 yalnızca olguyu ve
kaynağını verir.

---

## 7. Dikkat adayları ≠ öneri (opak puan yok)

`attention_candidates` deterministik olgulardan türetilir ve **gerekçe kodu**
taşır. Sıralama koddadır; model çıktısı ya da gizli skor değildir:

```text
overdue                      gecikmiş
deadline_1d / _3d / _7d      kalan güne göre gerekçe (1 / 3 / 7)
passed_plan_open             planlanan zaman geçti, görev hâlâ açık
unread_accumulation          okunmamış içerik eşiği aştı
project_without_next_action  projenin sonraki adımı tanımlı değil
project_inactive             projede kayıtlı anlamlı hareket yok
```

Yanıtın **hiçbir yerinde** `score`, `confidence`, `probability`, `priority_score`
veya üretkenlik puanı alanı yoktur; bu da testle kilitlenmiştir. Dikkat listesi
bir "yapılacaklar emri" değil, **bakılacaklar listesidir**.

---

## 8. Bilgi sağlığı adayları

Bilgi sağlığı **adaydır**: H5 hiçbir notu eskimiş ilan etmez, hiçbir kaydı
geçersiz kılmaz.

| Sorun | Anlamı |
|---|---|
| `possibly_stale` | Yapısal olarak eskimiş görünüyor (örn. yeniden yüzey yaşı) |
| `possibly_superseded` | Yeni bir aday ifade eskisinin yerine geçiyor **olabilir** |
| `possibly_conflicting` | Eski ve yeni ifade çelişiyor **olabilir** |
| `managed_source_conflict` | Aynı yönetilen not kimliğini birden fazla dosya sahipleniyor |

Yerine geçme karşılaştırması yalnızca **aday** üretir ve H4 `classify` etiketleri
(`consistent` · `possibly_superseded` · `possibly_conflicting` · `unrelated`)
kullanılır. Otomatik geçersiz kılma, otomatik düzeltme veya otomatik silme
YOKTUR.

---

## 9. Yeniden yüzey (resurface)

Yeniden yüzey, **rastgele not önermez**: yalnızca yapısal olarak ilgili
(varlık kapsamlı) ve yeterince eskimiş bilgiyi sınırlı sayıda öne çıkarır.

```text
eşik   : 30 gün
tavan  : 3 aday
gerekçe: reasons[] — olgusal, puan değil
```

---

## 10. Bozulmuş mod davranışı — hiçbiri sessiz değildir

| Bozulma | Davranış |
|---|---|
| **Vault yok** | Günlük notlar okunamaz; dönem için beklenen notlar "eksik" sayılır → `MISSING_DAILY_NOTES`. H5 çalışmaya devam eder (kasa yokluğu hata değildir). |
| **H4 yok** (`H4_ENABLED=false`, sağlayıcı düşük, model yok) | `H4_UNAVAILABLE`; çıktı **deterministik** kalır: olgular, kanonik açık döngüler, makbuz tabanlı sonuçlar ve `daily_notes` yine döner; yalnızca model kaynaklı adaylar düşer. |
| **Önceki Review yok** | `NO_PREVIOUS_REVIEW`; haftalık karşılaştırma ve makbuz sonuçları iddia edilmez. |
| **Eksik günlük not** | `MISSING_DAILY_NOTES` + manifestte `daily_notes_expected/found/missing`. Eksik not **hata değildir**. |
| **H3 erişilemez** | `H3_EVIDENCE_UNAVAILABLE`; bilgi sağlığı adayı üretilmez, geri kalan paket döner. |
| **Tarama tavanı** | `EVENT_SCAN_TRUNCATED` / `DEADLINE_SCAN_TRUNCATED` / `SOURCE_PACKET_TRUNCATED` / `KNOWLEDGE_HEALTH_TRUNCATED` ve `truncated=true`. |
| **Kapsam yarım** | `coverage.partial=true`, `coverage.comparable=false` — sayısal karşılaştırma **iddia edilmez**. Haftalık modda ek olarak `PARTIAL_PERIOD` uyarısı verilir. |

Tavanlar `+1 nöbetçi` ile ölçülür: "kaç kayıt gördüm" ile "kaç kayıt var"
karıştırılmaz.

---

## 11. Neler YOK (bilinçli)

```text
kalıcı aday tablosu        arka plan işçisi          zamanlayıcı
frontend                   gömme/vektör arama        bulut çıkarımı
duygu/ruh hâli profili     üretkenlik puanı          pasif yakalama (dinleme)
otomatik özet saklama      H6 proaktif ajan          ikinci Review alt sistemi
Entity/Event/Todo/Vault/Sıcak Hafıza mutasyonu
```

H5, **H4'ün loopback sağlayıcısı dışında hiçbir ağ çağrısı yapmaz**; kendi
modelini çalıştırmaz, model indirmez, dışarıya telemetri göndermez.

---

## 12. İlgili belgeler

- [H5 Araç Sözleşmesi](h5-tool-contract.md) — imza, mod/argüman kuralları, sınırlar, kodlar, örnek.
- [H5 Kaynak ve Konsolidasyon Politikası](h5-source-and-consolidation-policy.md) — episodic ≠ semantic, aday ≠ hafıza, kaynak kilidi ve kapsam dürüstlüğü.
- [H4 Yerel Biliş](h4-local-cognition.md) — H5'in isteğe bağlı kullandığı çıkarım/sınıflandırma katmanı.
- [H3 Kanıt Getirme](h3-retrieval-evidence.md) — bilgi sağlığı adaylarının dayandığı kanıt katmanı.
- [Yol Haritası](roadmap.md) — H5/H6 sıralaması.
