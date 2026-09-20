# forkOS × Hermes — H6 Proaktivite ve Dikkat Kontrolü

H6, forkOS'un **kullanıcı sormadan ne zaman devreye gireceğine** karar veren
katmandır. Tek sorusu şudur:

```text
"şimdi kullanıcıya dokunmalı mıyız?"   → H6 = WHEN
```

Sorumluluk zinciri dört faza yayılır ve hiçbiri diğerinin işini yapmaz:

```text
H5      → WHAT : kanonik durumu toplar (süreklilik, gün kapanışı, haftalık, delta)
Hermes  → MUHAKEME : anlatıyı kurar, kullanıcıya ne söyleneceğine karar verir
H6      → WHEN : dikkat çekmenin ZAMANI, kategorisi ve teslim biçimi
H1      → MUTASYON : yalnızca kullanıcı onayından sonra canonical yazma
```

H6 bir iş akışı motoru, zamanlanmış serbest istem yürütücüsü, kural DSL'i veya
otomatik mutasyon katmanı **değildir**. Aday üretir, karar verir, (gerekirse)
bildirir; hiçbir Todo/Project/Opportunity/Vault/Review/Event kaydını değiştirmez
(`backend/app/modules/proactivity/__init__.py:8-14`).

## H6.1 — Doğruluk sertleştirmesi (dört açık kapatıldı)

```text
1) entity kimliği != temporal koşul kimliği
   Aynı fırsatın üzerinde ilan son tarihi, takip tarihi ve N görüşme
   BAĞIMSIZ koşullardır. Koşul kimliği:
       <module>.<sub_kind|due>.<condition_id|entity_id>
   (görüşmede alt kaydın kararlı PK'si kullanılır; başlık ya da liste sırası
   ASLA kimlik yerine geçmez). Kimlik ve revizyon ":" içermez, böylece
   `deadline:v2:<kimlik>:<revizyon>:<rung>d` ayrıştırması belirsiz kalmaz.

2) aralık dışı son tarih ADAY DEĞİLDİR
   T-31 normal son tarih ve T-15 takip tarihi basamak dışıdır; `None` aday
   listesine giremez (aksi halde kuralın tamamı düşerdi). Kural sözleşmesi
   yalnızca gerçek `Candidate` üretir; ihlal edilirse `INVALID_CANDIDATE`
   hata koduyla raporlanır.

3) digest'te "delivered" = kullanıcıya GERÇEKTEN gösterildi
   Bir `ProactivityRun` ancak bildirime girdiyse teslim edildi sayılır.
   Parti kimliği ÜYE KÜMESİNDEN türetilir (deterministik, restart-safe);
   gösterilmeyen üyeler kuyrukta kalır ve sonraki digest'te teslim edilir.

4) açılışta H6 turu kaynak tazelemeyi BEKLER
   `proactivity_tick` işi, açılış zinciri (kaynak tazeleme + H6 telafisi)
   tamamlandıktan SONRA kaydedilir; dakikalık tur bayat durumdan aday üretmez.
```

### Son tarih kimliği neden ayrı bir kavram?

`DeadlineRow.entity_id` bir son tarihin BAĞLI olduğu entity'dir; koşulun
kimliği değildir. Fırsat modülünde aynı entity üzerinde üç ayrı koşul
üretilebilir:

```text
opportunity.job.<opportunity_id>        ilan son tarihi
opportunity.follow_up.<opportunity_id>  takip tarihi
opportunity.interview.<interview_id>    her görüşme AYRI koşul
```

Kimlik olmadan: bir görüşmenin taşınması ilan son tarihini "bayat" sanar,
snooze kardeş koşula sızar, kompozisyon yanlış satırı okur.


---

## 1. Sorumluluk paylaşımı

```text
kural katmanı (rules.py)   → "değerlendirilecek bir koşul var mı?" → Candidate
politika (policy.py)       → "şimdi dokunalım mı?" → InterventionDecision
servis (service.py)        → koşu kimliği, yeniden doğrulama, teslim sırası
teslim (delivery.py)       → kısa, deterministik bildirim metni (LLM YOK)
```

> **H6 hiçbir zaman doğrudan tetikleyici payload'una güvenmez.** Bir aday
> üretildiğinde ve teslim edilmeden hemen önce koşul **güncel durumdan yeniden
> doğrulanır** (`rules.revalidate`, `rules.py:449`). Ertelenen bir teslim,
> koşul ortadan kalktıysa iptal edilir.

---

## 2. Boru hattı

Tek giriş noktası `service.tick()`'tir (`service.py:438`). Zamanlayıcı yalnızca
onu çağırır; ritüeller, son tarihler ve proje izleme ayrı işler değildir.

```text
kural değerlendirmesi (rules.evaluate_all, rules.py:420)
        ↓  Candidate (kullanıcıya dokunma kararı HENÜZ verilmedi)
mantıksal koşu kimliği   (service._claim_run, service.py:329)  ── idempotent, DB'de tek
        ↓
GÜNCEL durum yeniden doğrulaması (rules.revalidate)
        ↓
saf politika kararı      (policy.decide, policy.py:157)
        ↓
silent | defer | digest | surface | prepare        (policy.OUTCOMES, policy.py:22)
        ↓  surface / prepare ise
H5 bağlamı TESLİM ANINDA kurulur (service._compose, service.py:753)
        ↓
yeniden doğrulama (service._deliver_now, service.py:565)
        ↓
Notification (delivery.deliver_run, delivery.py:81)
        ↓
kullanıcı override'ı (snooze / dismiss)
```

Koşu durumları bu boru hattının olgusal izidir; her tur için "değerlendirildi"
satırı **yazılmaz** — yalnızca anlamlı geçişler kalıcıdır (`service.py:15-18`).

### 2.1 Neden koşu kimliği kalıcı

Aynı mantıksal tetik yüz kez değerlendirilse de **tek satır** kalır
(`logical_trigger_key` UNIQUE; `backend/alembic/versions/0060_proactivity.py`).
Bu yüzden idempotans yalnızca zamanlayıcının `max_instances=1` davranışına
bırakılmaz. Kimlik, koşulu yeniden çözmeye yetecek kadar yapısal bilgi taşır
(kural türü, konu tipi, konu kimliği, gerekçe kodları); kullanıcıya giden metin
teslim anında yeniden üretilir (`models.py:129`, `models.py:13-15`).

---

## 3. Modül düzeni

```text
proactivity/
  models.py     iki tablo + kapalı kural kümesi + koşu durum makinesi
  schemas.py    REST ve MCP'nin paylaştığı Pydantic sözleşmeleri
  policy.py     SAF karar: veritabanı ve model çağrısı YOK
  rules.py      kapalı kural değerlendiricileri + yeniden doğrulama
  service.py    tur döngüsü, koşu yaşam döngüsü, konfigürasyon, kontrol yüzeyi
  delivery.py   bildirim kompozisyonu (LLM çağrısı YOK)
  router.py     REST uçları
```

Modül kaydı: `ModuleSpec(id="proactivity", entity_types=[], event_verbs=[])`
(`__init__.py:18-24`). **Hiçbir entity tipi ve hiçbir olay fiili üretmez**: bu
motorun operasyonel durumudur, aranabilir/linklenebilir nesne değildir.

---

## 4. İki tablo ve neden entity FK'si yok

| Tablo | Ne tutar | Kapsam |
|---|---|---|
| `proactivity_rule` | kullanıcıya ait kural aç/kapa + eşik ayarı | `logical_key = <kind>:v<version>:<scope>` (UNIQUE) |
| `proactivity_run` | TEK proaktif koşulun (episodun) yaşam döngüsü | `logical_trigger_key` (UNIQUE) |

`source_run`/`source_sync_batch` ile **aynı sınıftır**: bağımsız
aranabilir/linklenebilir nesne değil, motorun operasyonel kaydıdır
(`models.py:4-8`). Bu yüzden:

```text
proactivity_run.subject_id   → FK YOK : entity silinse bile "neden o gün
                                        dürtüldü" tarihi okunabilir kalır
proactivity_rule.scope_entity_id → FK VAR (entity.id, on delete cascade):
                                        entity kapsamlı kural entity ile gider
proactivity_run.notification_id → FK VAR (notification.id, on delete SET NULL):
                                        bildirim budansa koşu okunabilir kalır
```

Kullanıcıya dönük kayıt `notification` tablosudur ve o çekirdektedir.
Koşu ondan bağımsız olarak susturulabilir, ertelenebilir veya iptal edilebilir
(`models.py:147-151`).

**Saklanmayanlar (bilinçli):** H5 paketleri, Vault alıntıları, sıcak hafıza
gövdeleri, model istem/yanıtları (`models.py:13-15`). Koşu satırı yalnızca
koşulu yeniden çözmeye yetecek yapısal kimlik taşır.

---

## 5. Kapalı kural ailesi (6)

Genel bir kural DSL'i **yoktur**: yeni davranış eklemek kod yazmak demektir
(`models.py:41-45`). Kural türü kümesi `models.RULE_KINDS` (`models.py:46`).

| Kural | Varsayılan | Ayar alanları | Kategori | H5 modu | Tetik anahtarı |
|---|---|---|---|---|---|
| `morning_continuity` | **kapalı** | `time` 08:05, `grace_hours` 4 | `ritual` | `continuity` | `morning_continuity:v1:<gün>` |
| `daily_close` | **kapalı** | `time` 21:00, `grace_hours` 3 | `ritual` | `daily_close` | `daily_close:v1:<gün>` |
| `weekly_review` | **kapalı** | `weekday` 6, `time` 18:00, `grace_hours` 24 | `ritual` | `weekly_review` | `weekly_review:v1:<yıl>-W<hafta>` |
| `deadline_staircase` | **açık** | — | `deadline_*` | — | `deadline:v2:<koşul-kimliği>:<revizyon>:<rung>d` |
| `continuity_gap` | **kapalı** | `threshold_hours` 48 | `continuity_comeback` | `continuity` | `continuity_gap:v1:<gün>` |
| `project_stalled` | **kapalı** | `days` 14, `cooldown_days` 7 | `project_stalled` | `continuity` | `project_stalled:v1:<project_id>` |

Birikim (okunmamış içerik) için **ayrı bir kural ya da kategori yoktur**:
H5 `unread_accumulation`'ı bir `AttentionCandidate` olarak üretir
(`continuity.py:542-548`); H6 bunu süreklilik/ritüel adaylarının içinde taşır
(`rules.py:530-538`).

Varsayılanlar `service.RULE_DEFAULTS` (`service.py:65`), izin verilen ayar
alanları `service.RULE_CONFIG_FIELDS` (`service.py:75`). Kurallar açılışta
**idempotent** yazılır (`service.seed_rules`, `service.py:211`); her açılışta
çoğalmaz.

### 5.1 Son tarih basamakları

Tek mantıksal üretici `deadline_staircase`'tir (`rules.py:123`):

```text
son tarih merdiveni  (0, 1, 3, 7, 14, 30)   → basamak 0 "bugün bitiyor" ayrı koşudur
takip merdiveni      (0, 1, 3, 7, 14)       → 30 gün takip için fazla geniştir
```

Kalan süreye **en yakın** eşik kazanır (`rules._rung`, `rules.py:95`). Revizyon
= son tarihin kendisidir: tarih değişirse eski koşu bayatlar ve yeni tarih
bağımsız basamaklar üretir (`rules.py:164-166`).

### 5.2 Ritüel penceresi (misfire politikası)

`run_once_if_still_relevant`: kaçırılan tur, **pencere içinde bir kez** telafi
edilir; gün dışına taşan tur tekrar oynatılmaz (`rules._ritual_due`,
`rules.py:359`). Haftalık ritüel ayrıca yapılandırılmış günü bekler
(`rules._weekly_due`, `rules.py:375`).

### 5.3 Proje hareketsizliği ≠ ihmal

`project_stalled` "ihmal ediyorsun" demez; "kayıtlı aktivite yok" der
(`rules.py:293-298`). Proje hareketi tanımı **tek yerde** durur: H5'in kanonik
`project_last_activity` okuyucusu — kanonik `Event` geçmişi (sayılan fiiller),
projeye **bağlı görevlerin** hareketi dâhil. İkinci bir tanım yazmak aynı proje
için iki farklı "durağan" cevabı üretirdi (`rules.py:318-323`). Worker senkronu,
kaynak sağlığı, bildirim ve proaktif koşular sayılan fiiller arasında olmadığı
için hareketsizliği sıfırlayamaz (`rules.last_meaningful_activity_at`,
`rules.py:104-118`). Hiç kayıtlı hareketi olmayan proje için yaş **uydurulmaz**:
"16 gündür" denmez, aday atlanır (`rules.py:329-332`).

---

## 6. Sessizlik felsefesi

```text
sessizlik  birincil sınıftır: "yapacak bir şey yok" BAŞARIDIR.
```

- Ana anahtar kapalıysa **hiçbir** H6 bildirimi çıkmaz (`proactivity.enabled`
  varsayılan **false**; `service.CONFIG_DEFAULTS`, `service.py:56-62`).
- Kural, bir tetik gördü diye bildirim çıkmaz: tetik yalnızca "şimdi
  değerlendir" demektir.
- Anlamlı içerik yoksa teslim yerine **sessizlik** seçilir: koşu `suppressed` +
  `NO_MEANINGFUL_CONTENT` olur, boş bildirim gönderilmez (`service.py:585-586`).
- Ritüeller anlamlı bir şey bulamazsa **hiç aday üretmez**: temiz gün sessiz
  geçer (`rules.py:211-291`).
- `continuity_gap` yalnızca hareketsizlik **ve** anlamlı değişim birlikteyse
  aday üretir (`rules.py:180-197`).

Kullanıcı override'ı otomasyonun önündedir: `snooze` verilen ana kadar susar ve
bu, kuralların/kuyrukta bekleyen koşuların üstünde durur
(`policy.decide` adım 3, `policy.py:169-171`). Snooze **ayrı bir koşu durumudur**
(`snoozed`; "çözüldü"/"kapatıldı" değil, `service.py:1067-1068`); süre dolduğunda
tur koşuyu yeniden `candidate` yapıp **güncel** durumla değerlendirir
(`service.py:503-505`).

---

## 7. Worker: tek iş

```text
proactivity_tick       her 1 dakika, max_instances=1, coalesce=True
                       (backend/app/worker/main.py:125-132)
proactivity_catch_up   açılışta BİR KEZ, kaynaklar tazelendikten SONRA
                       (backend/app/worker/main.py:156-157)
```

Her ikisi de **aynı servisi** çağırır (`backend/app/worker/jobs.py:43` ve
`jobs.py:62`). Ritüel/son tarih/proje kararları bu turun içinde verilir; H6'nın
kendi durumu (idempotent koşu kimliği) fırtına korumasıdır.

**Emekli işler:** eski `morning_digest` ve `deadline_ladder` işleri
**kaldırıldı**; depoda kod izi yoktur. Zamanlama semantiği artık yalnızca H6'nın
durumundadır.

---

## 8. Kontrol yüzeyi

| Yüzey | Girdi noktası |
|---|---|
| MCP (tek araç) | `forkos_proactivity` (`backend/app/integrations/agent/tools.py:1178`) |
| REST | `GET/PUT /api/proactivity/*` (`backend/app/modules/proactivity/router.py`) |

İkisi de **aynı servis fonksiyonlarını** çağırır; H6 kendi ikinci durum
kopyasını tutmaz. Ayrıntı: [H6 Araç Sözleşmesi](h6-tool-contract.md).

---

## 9. Bozulmuş mod davranışı — hiçbiri sessiz değildir

| Bozulma | Davranış |
|---|---|
| **Ana anahtar kapalı** | Hiçbir bildirim çıkmaz. Bekleyen koşular tarihsel kalır; tekrar açıldığında **güncel** durumla yeniden değerlendirilir (`service.py:450-454`). |
| **Kural kapalı** | Kuralın bekleyen teslimleri iptal edilir (`service.cancel_pending`, `service.py:378`); yeni aday üretilmez. |
| **Kural değerlendirmesi çöker** | Diğer kurallar **etkilenmez**; hata sınırlı kodla koşu geçmişine yazılır (`RULE_EVALUATION_FAILED`), kullanıcıya bildirilmez (`rules.evaluate_all`, `rules.py:420`; `service._record_rule_failure`, `service.py:899`). |
| **Yeniden doğrulama çöker** | Teslim **edilmez**; fail-closed (`rules.py:477`). |
| **Bildirim zaten var** | Koşu teslim sayılmaz: `suppressed` + `DUPLICATE_TRIGGER` (`service.py:602-603`). |
| **H5 erişilemez / anlamlı içerik yok** | Boş bildirim yerine sessizlik: `NO_MEANINGFUL_CONTENT`. |

---

## 10. Neler YOK (bilinçli)

```text
kural DSL'i / serbest ifade      zamanlanmış serbest istem
otomatik mutasyon                LLM karar kapısı ("dokunayım mı?")
dış push (e-posta/SMS/webhook)   gözetim / pasif dinleme
ayrı H6 temizlik işi             kalıcı aday tablosu
cron string / SQL / araç adı     Entity/Event üretimi
```

- **DSL yok:** kural kümesi kapalı; kullanıcı tanımlı ifade reddedilir.
- **Otomatik mutasyon yok:** H6 hiçbir canonical kaydı değiştirmez; yazma yolu
  H1'dir ve onay kapısından geçer.
- **LLM kapısı yok:** H6 v1'de "dokunayım mı?" sorusunu model **cevaplamaz**
  (`policy.py:9-12`); bildirim metni bile kodla kurulur
  (`delivery.py:1-8`) — worker Hermes olmadan da çalışır.
- **Dış push yok:** teslim yalnızca `notification` tablosuna yazılır
  (`delivery.deliver_run`, `delivery.py:81`); e-posta/SMS/webhook/telemetri yok.
- **Gözetim yok:** H6 kullanıcıyı izlemez; yalnızca zaten kanonik olan olay
  geçmişini ve H5 çıktısını okur (`rules.py:104-118`).
- **Ayrı temizlik işi yok:** budama mevcut günlük bakım adımına devredilir
  (`service.prune_runs`, `service.py:1137`; `core/retention.py`).

---

## 11. İlgili belgeler

- [H6 Karar Politikası](h6-policy.md) — karar sırası, kategoriler, kuiet saat,
  cooldown, neden-şimdi ve sınırlar.
- [H6 Araç Sözleşmesi](h6-tool-contract.md) — `forkos_proactivity` imzası,
  işlemler, REST uçları ve örnek çıktı.
- [H5 Gözden Geçirme Zekâsı](h5-review-intelligence.md) — H6'nın bağlam
  kaynağı (WHAT).
- [Yol Haritası](roadmap.md) — H6'nın serideki yeri.
