# forkOS × Hermes — H6 Karar Politikası

Bu doküman H6'nın tek sorusunun cevabıdır: **"şimdi kullanıcıya dokunmalı
mıyız?"** Karar `policy.decide()` içinde (`backend/app/modules/proactivity/policy.py:157`),
**saf** ve **deterministiktir**: veritabanı, model ve saat çağrısı yoktur
(`policy.py:1-4`). Aynı girdi **her zaman** aynı kararı verir.

Opak puan **yoktur**: ne "aciliyet olasılığı" ne "AI skoru". Karar kategorik
eşiklerle ve sınırlı gerekçe kodlarıyla açıklanır (`policy.py:6-8`).

---

## 1. Karar sırası — ilk uyan gerekçe kazanır

`policy.decide()` adımları **kararlıdır**; her adım bir öncekinin üstünde durur.

```text
1) ana anahtar kapalı                     → silent  [PROACTIVITY_DISABLED]   policy.py:161-163
2) kural kapalı                           → silent  [RULE_DISABLED]          policy.py:165-167
3) kullanıcı snooze'u (snoozed_until>now) → silent  [USER_SNOOZED]           policy.py:169-171
4) tek seferlik koşu, delivery_count>0    → silent  [DUPLICATE_TRIGGER]      policy.py:173-175
5) cooldown penceresi dolmadı             → silent  [RECENTLY_SURFACED]      policy.py:177-183
   ── buradan sonra kategori sonucu hesaplanır ve gerekçeye EKLENİR ──
6) kuiet saatleri                         → defer   [QUIET_HOURS, <kat>]     policy.py:188-197
7) odak aktif + kritik olmayan kategori   → defer   [FOCUS_ACTIVE, <kat>]    policy.py:199-205
8) günlük anlık bütçe doldu (yalnız surface) → digest [IMMEDIATE_BUDGET_EXHAUSTED, <kat>]  policy.py:207-211
   değilse                                → CATEGORY_OUTCOMES[category]
```

Kritik sıralama sonuçları:

```text
snooze  >  tekrar  >  cooldown  >  kuiet  >  odak  >  bütçe  >  kategori
bütçe kontrolü YALNIZCA surface sonucunu etkiler: defer/silent/prepare'ı DURDURMAZ
kuiet saatleri ACİL istisnası TANIMAZ (§32)
```

### 1.1 Sessizlik kararları kategori kodunu taşımaz

1–5 arası adımlar dönerken henüz kategori kodu eklenmemiştir. Bu yüzden örneğin
kapatılmış kuralın gerekçesi yalnızca `["RULE_DISABLED"]` olur, `DEADLINE_3D`
**eklenmez** (`policy.py:161-183`). Kategori kodu 6. adımdan itibaren metinde
görünür.

### 1.2 Bir karar aynı zamanda bir talep taşır

`InterventionDecision.requires_revalidation` **varsayılan olarak `true`**'dur
(`policy.py:99`): politika "dokun" dese bile servis teslimden önce koşulu
yeniden doğrular.

---

## 2. Kategoriler ve önem eşlemesi

Kategori **kategoriktir**: ya vardır ya yoktur; ondalık skor yoktur
(`policy.py:54`). Sonuç `policy.CATEGORY_OUTCOMES` (`policy.py:55`), önem
`policy.CATEGORY_IMPORTANCE` (`policy.py:76`).

| Kategori | Sonuç | Önem (1..3) | Kategori kodu | Tipik üretici |
|---|---|---|---|---|
| `deadline_today` | `surface` | 3 | `DEADLINE_TODAY` | `deadline_staircase` (T-0) |
| `deadline_tomorrow` | `surface` | 3 | `DEADLINE_1D` | `deadline_staircase` (T-1) |
| `deadline_soon` | `surface` | 2 | `DEADLINE_3D` | `deadline_staircase` (T-3) |
| `deadline_near` | `digest` | 1 | `DEADLINE_7D` | `deadline_staircase` (T-7) |
| `deadline_far` | `digest` | 1 | `DEADLINE_14D` | `deadline_staircase` (T-14/T-30) |
| `continuity_comeback` | `prepare` | 2 | `CONTINUITY_GAP` | `continuity_gap` |
| `ritual` | `surface` | 2 | `RITUAL_DUE` | `morning_continuity`, `daily_close`, `weekly_review` |
| `project_stalled` | `digest` | 1 | `PROJECT_STALLED` | `project_stalled` |

Kategori kümesi **kapalıdır** (8 kayıt). Birikim içeriği ayrı bir kategori
değildir: H5 `unread_accumulation`'ı bir `AttentionCandidate` olarak üretir
(`continuity.py:542-548`) ve H6 bunu süreklilik/ritüel adaylarının içinde taşır
(`rules.py:530-538`); H6'da "accumulation" diye bir kural/kategori YOKTUR.

Bilinmeyen kategori `digest`'e düşer ve `DIGEST_ELIGIBLE` gerekçesiyle
işaretlenir; önem `1` olur (`policy.py:185`, `policy.py:230-231`).

`prepare` sonucu "önce H5 bağlamını kur, sonra teslim et" demektir: süreklilik
dönüşünde güncel H5 paketi kurulmadan bildirim üretilmez
(`service._compose`, `service.py:753`).

### 2.1 Odak kritik kategoriler

```text
FOCUS_CRITICAL_CATEGORIES = {deadline_today, deadline_tomorrow}
```

Yalnızca bu iki kategori odak ertelemesinden **muaftır** (`policy.py:71`).
Bunlar bile sessizlik/snooze/kuiet kurallarını atlayamaz; yalnızca odak
ertelemesine girmezler.

---

## 3. Kuiet saatleri — gece yarısını aşan pencere

```text
in_quiet_hours(local_now, start, end)   policy.py:131
  start == end                → false (pencere yok)
  start <  end                → start <= local_now < end
  start >  end (gece yarısı)  → local_now >= start  OR  local_now < end
```

Varsayılan pencere **23:30 → 08:30**'dur ve gece yarısını aşar
(`service.CONFIG_DEFAULTS`, `service.py:56-62`). Bu yüzden 23:45 de, 03:00 de
kuiet sayılır; 09:00 sayılmaz.

`quiet_hours_end()` (`policy.py:140`) kuietin biteceği **saat dilimli** anı
döner; kuiet içindeysem ve hedef saat bugün geçtiyse ertesi güne kaydırılır.
Defer kararının `earliest_delivery_at` alanı bu damgayı taşır
(`policy.py:188-197`).

**Acil istisnası yoktur:** T-1 son tarih 03:00'te dürtmez; pencere açılınca
teslim edilir.

---

## 4. Cooldown ≠ debounce

İkisi farklı soruları yanıtlar ve karıştırılmamalıdır:

| Kavram | Soru | Yeri | Etki |
|---|---|---|---|
| **Tekrar (idempotans)** | "Bu koşu zaten teslim edildi mi?" | `_claim_run` + `logical_trigger_key` UNIQUE (`service.py:329`) | Aynı mantıksal koşul ikinci **satır** açamaz; DB'de zorlanır. |
| **Cooldown** | "Tekrarlanabilir koşul yeniden yüzeye çıkabilir mi?" | `policy.decide` adım 5 (`policy.py:177`) | `last_delivered_at + cooldown_hours > now` iken `silent` / `RECENTLY_SURFACED`. |
| **Debounce (ritüel penceresi)** | "Kaçırılan tur hâlâ telafi edilebilir mi?" | `_ritual_due` (`rules.py:359`) | Pencere içinde bir kez telafi; gün dışına taşan tur tekrar oynatılmaz. |

Cooldown yalnızca **tekrarlanabilir** koşulda anlamlıdır: `cooldown_hours`
verilmediyse adım 5 atlanır. Tek seferlik koşulda (`one_shot`) tekrar koruması
adım 4'tedir. H6 v1'de yalnızca `project_stalled` tekrarlanabilirdir
(`one_shot=False`; cooldown `cooldown_days × 24` saat, `rules.py:347`).

---

## 5. Neden-şimdi (`why_now`)

Her aday, teslim anında kullanıcıya gösterilecek **olgusal** bir gerekçe taşır
(`Candidate.why_now`). `decide()` bu metni üretmez; yalnızca karara taşır
(`policy.py:188-197`).

```text
son tarih      "<başlık> için son tarih <N> gün içinde"
süreklilik     "<N> saattir sayılan kullanıcı hareketi yok; <K> dikkat sinyali var"
sabah ritüeli  "sabah ritüeli <K> dikkat sinyali buldu"
gün kapanışı   "gün kapanışı <K> açık uç buldu"
haftalık       "haftalık gözden geçirme <K> çözülmemiş madde buldu"
proje          "projede <N> gündür kayıtlı anlamlı aktivite yok"
```

Kurallar:

```text
olgusal          psikolojik çıkarım YASAK ("ihmal ediyorsun" denmez)
sınırlı          opak puan yok; sayı ve olgu var
yeniden üretilir teslim metni teslim ANINDA güncel veriyle kurulur
```

---

## 6. Gerekçe kodları sözlüğü

Sözlük kapalıdır: `policy.REASON_CODES` (`policy.py:25`). Yeni kod eklemek
bilinçli bir karardır ve her kodun **gerçek bir üretim yolu** olmalıdır.

| Kod | Ne zaman üretilir | Üretim yeri |
|---|---|---|
| `PROACTIVITY_DISABLED` | ana anahtar kapalı | `policy.py:162` |
| `RULE_DISABLED` | kural kapalı / kural kapatılınca bekleyenler iptal | `policy.py:166`, `service.py:378` |
| `QUIET_HOURS` | kuiet penceresi açık | `policy.py:189` |
| `FOCUS_ACTIVE` | odak oturumu açık, kritik olmayan kategori | `policy.py:205` |
| `USER_SNOOZED` | kullanıcı snooze'u sürüyor | `policy.py:170` |
| `RECENTLY_SURFACED` | cooldown dolmadı | `policy.py:183` |
| `DUPLICATE_TRIGGER` | tek seferlik koşu zaten teslim edildi **veya** bildirim dedup'ı tuttu | `policy.py:174`, `service.py:603` |
| `CONDITION_RESOLVED` | teslim öncesi yeniden doğrulama başarısız: koşul ortadan kalktı | `service.py:430` |
| `STALE_TRIGGER` | son tarih revizyonu değişti; aynı konunun eski koşusu iptal | `service.py:418` |
| `DEADLINE_TODAY` / `DEADLINE_1D` / `DEADLINE_3D` / `DEADLINE_7D` / `DEADLINE_14D` / `DEADLINE_30D` | son tarih basamağı | `policy._category_code`, `rules._RUNG_REASON` |
| `CONTINUITY_GAP` | hareketsizlik eşiği aşıldı | `rules.py:205` |
| `MEANINGFUL_STATE_CHANGED` | eşiğin yanında anlamlı bir dikkat sinyali var | `rules.py:205` |
| `PROJECT_STALLED` | projede kayıtlı hareket yok | `rules.py:342` |
| `RITUAL_DUE` | ritüel penceresi geldi | `rules.py:227`, `257`, `287` |
| `DIGEST_ELIGIBLE` | düşük/orta dikkat kategorisi veya bilinmeyen kategori | `policy._category_code` |
| `IMMEDIATE_BUDGET_EXHAUSTED` | günlük anlık yüzey bütçesi doldu | `policy.py:210` |
| `NO_MEANINGFUL_CONTENT` | teslim anında anlamlı olgu yok → sessizlik | `service.py:586` |

`why_now` **kod değildir**: serbest metin değil, sınırlı bir şablondan üretilen
tek cümledir (§5).

---

## 7. Koşu durum kümesi

```text
AKTİF      candidate · deferred · digest_queued · snoozed
TESLİM     delivered
TERMİNAL   resolved · cancelled · dismissed · failed
ek         suppressed
```

Kümeler `models.py:66-77`'dedir. Anlamları:

```text
candidate      aday, karar bekliyor
deferred       kuiet/odak nedeniyle ertelendi (deferred_until)
digest_queued  digest kuyruğunda; digest saatinde tek bildirime iner
snoozed        kullanıcı override'ı sürüyor ("çözüldü"/"kapatıldı" DEĞİL)
delivered      teslim edildi (delivery_count arttı)
suppressed     sessizlik kazandı (kural/bütçe/cooldown/içerik yok/dup)
resolved       koşul ortadan kalktı
cancelled      kural kapandı veya tetik bayatladı
dismissed      kullanıcı bildirimi kapattı (çözmek DEĞİLDİR)
failed         kural değerlendirmesi çöktü (sınırlı failure_code)
```

`snoozed` gerçek bir durumdur: `snooze(run_id=...)` koşuyu bu duruma geçirir
(`service.py:1067-1068`) ve süre dolduğunda tur onu yeniden `candidate` yapıp
**güncel** durumla değerlendirir (`service.py:503-505`). Kullanıcı override'ının
kural düzeyindeki karşılığı `proactivity_rule.snoozed_until`'dir; karar her iki
damgayı da okur (`policy.decide` adım 3, `policy.py:170`).

`dismissed` bilinçli olarak `resolved` **değildir**: bildirimi kapatmak koşulu
çözmez; bu yüzden `resolved_at` yazılmaz (`service.dismiss_for_notification`,
`service.py:1113`).

---

## 8. Sınırlar

| Sınır | Değer | Yer |
|---|---|---|
| Günlük anlık yüzey bütçesi | 3 (`MAX_IMMEDIATE_SURFACES_PER_DAY`) | `policy.py:88` |
| Tur başına değerlendirilecek aday | 100 (`MAX_TICK_CANDIDATES`) | `rules.py:30` |
| Son tarih taraması | 200 (`MAX_DEADLINE_ROWS`) | `rules.py:32` |
| Hareketsiz proje taraması | 50 (`MAX_STALLED_PROJECTS`) | `rules.py:33` |
| Bildirim gövdesindeki olgu | 3 (`MAX_SURFACE_FACTS`) | `delivery.py:21` |
| Digest maddesi | 10 (`MAX_DIGEST_ITEMS`) | `delivery.py:23` |
| Tek olgu satırı | 160 karakter (`MAX_FACT_CHARS`) | `delivery.py:25` |
| Geçmiş dönüşü | 50 (`MAX_HISTORY_RETURN`) | `service.py:87` |
| Koşu saklama | 90 gün (`RUN_RETENTION_DAYS`, yalnız terminal) | `service.py:85` |
| Durumda gösterilen son hata | 5 (`MAX_RECENT_FAILURES`) | `service.py:89` |

### 8.1 Yapılandırma aralıkları

`validate_rule_config` kapalı şemadır; bilinmeyen alan **reddedilir**
(`service.py:283`):

```text
weekday         0..6         (0 = Pazartesi)
threshold_hours 1..720
days            1..365
cooldown_days   1..90
grace_hours     1..72
time, digest_time  "HH:MM"  (00..23 : 00..59)
```

Saat ayrıştırma tek yerde doğrulanır (`service.parse_hhmm`, `service.py:137`).
Yazma yolu bozuk değeri **sessizce kırpmaz**, hata döner; okuma yolu (elle
DB'ye yazılmış bozuk değer) worker'ı öldürmez — varsayılana döner ve loglanır
(`service.load_config`, `service.py:149-173`).

### 8.2 Bütçe muhasebesi kategoriye değil teslime bakar

Günlük anlık bütçe, **bugün teslim edilmiş** anlık yüzeyleri sayar; digest
bildirimleri sayılmaz (`service._immediate_surfaces_today`, `service.py:877`).
Sayım yerel gün başlangıcından itibaren yapılır.

---

## 9. İlgili belgeler

- [H6 Proaktivite ve Dikkat Kontrolü](h6-proactivity.md) — ürün kimliği, boru
  hattı, kural aileleri ve sessizlik felsefesi.
- [H6 Araç Sözleşmesi](h6-tool-contract.md) — kontrol yüzeyi ve örnek çıktı.
- [H6 Değerlendirme Vakaları](evals/h6-proactivity.yaml) — politikanın
  tekrar oynatılabilir sentetik vakaları.
