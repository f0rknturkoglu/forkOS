# forkOS × Hermes — H6 Araç Sözleşmesi (`forkos_proactivity`)

H6 genel yüzeye **tam olarak bir** araç ekler. Yüzey **28** olur
(H0 8 + H1 11 + H2 5 + H3 1 + H4 1 + H5 1 + H6 1). Mikro-araç çoğaltması
YOKTUR: tek araç, yedi işlem.

Araç bir otomasyon yürütücüsü **değildir**: kapalı bir işlem kümesi
(incele / ayarla / snooze / geçmiş) sunar
(`backend/app/integrations/agent/tools.py:1156-1160`).

---

## 1. İmza

```text
forkos_proactivity(
    operation: "status" | "configure" | "rule_set" | "snooze"
             | "unsnooze" | "history" | "evaluate_now",   # ZORUNLU
    kind:      str | None = None,     # kural türü, ≤ 48 karakter
    enabled:   bool | None = None,    # configure / rule_set için aç-kapa
    config:    dict | None = None,    # configure / rule_set kapalı şema ayarı
    run_id:    int | None = None,     # koşu düzeyi override hedefi
    until:     str | None = None,     # saat dilimli ISO-8601 snooze damgası, ≤ 40
    limit:     int | None = None      # history dönüş sınırı (varsayılan 20)
)
```

Anotasyonlar (`tools.py:83-87`):

```text
readOnlyHint    = false      yapılandırma ve override durumunu YAZAR
destructiveHint = false      hiçbir kaydı silmez, canonical domain'e dokunmaz
idempotentHint  = true       aynı girdiyle tekrar çağrı ek durum üretmez
```

Araç **hiçbir koşulda** Todo, Project, Opportunity, Review, Vault veya Hot
Memory kaydını değiştirmez; arka plan worker'ı da canonical mutasyon yapmaz
(`tools.py:1187-1192`).

### 1.1 Reddedilen alan ve işlemler

Genel yüzeyde **asla** bulunmayanlar:

```text
cron · schedule · expression · sql · query · tool · prompt · system_prompt
model · model_id · provider · base_url · endpoint · temperature · api_key
timeout · webhook · url · channel · email · push
```

Bilinmeyen anahtar **sessizce düşmez**: şemalar `extra="forbid"` taşır
(`schemas.py:14`, `schemas.py:26`), yani REST tarafında 422 döner. MCP
`configure` yolunda bilinmeyen alt anahtar `UNKNOWN_CONFIG_FIELD` ile
reddedilir (`tools.py:1162`, `tools.py:1212-1216`); kural ayarında kapalı şema
`service.py:287-290`'dır.

- Bilinmeyen `operation` → `UNKNOWN_OPERATION` (`tools.py:1276-1278`).
- Bilinmeyen `kind` → `UNKNOWN_RULE_KIND` (`service.py:249-250`).
- Kural `kind` kümesi **kapalıdır**: `morning_continuity`, `daily_close`,
  `weekly_review`, `deadline_staircase`, `continuity_gap`, `project_stalled`
  (`models.py:46-53`). Serbest ifade kabul edilmez.
- `config` serbest JSON **değildir**: `rule_set`'te kural türüne göre izin
  verilen alanlar kapalıdır ve bilinmeyen alan `UNKNOWN_CONFIG_FIELD` ile
  reddedilir (`service.validate_rule_config`, `service.py:283`);
  `configure`'ın davranışı için §5'e bakın.

---

## 2. İşlem tablosu

| İşlem | Zorunlu girdi | Ek girdi | Çıktı | Hatalar |
|---|---|---|---|---|
| `status` | — | — | durum şeması (§3.1) | `PROACTIVITY_FAILED` |
| `configure` | en az bir alan | `enabled`, `config{quiet_hours_start, quiet_hours_end, focus_deferral_enabled, digest_time}` | **durum şeması** (§3.1) | `INVALID_CONFIG`, `UNKNOWN_CONFIG_FIELD` |
| `rule_set` | `kind` | `enabled`, `config` | kural şeması (§3.2) | `INVALID_ARGUMENT`, `UNKNOWN_RULE_KIND`, `UNKNOWN_CONFIG_FIELD`, `INVALID_CONFIG`, `INVALID_ENTITY_SCOPE` |
| `snooze` | `until` + (`run_id` **veya** `kind`) | — | `{"snoozed": true, "until": "<ISO>"}` | `INVALID_ARGUMENT`, `INVALID_SNOOZE`, `RUN_NOT_FOUND`, `UNKNOWN_RULE_KIND` |
| `unsnooze` | `run_id` **veya** `kind` | — | `{"snoozed": false}` | `RUN_NOT_FOUND`, `UNKNOWN_RULE_KIND` |
| `history` | — | `limit` (varsayılan 20) | `{"runs": [ ... ]}` (§3.3) | `PROACTIVITY_FAILED` |
| `evaluate_now` | — | — | tur sayacı (§3.4) | `PROACTIVITY_FAILED` |

`configure` ve `rule_set` **aynı servis fonksiyonlarını** REST uçlarıyla
paylaşır; araç kendi ikinci durum kopyasını tutmaz
(`tools.py:1210-1229`, `tools.py:1230-1239`).

`evaluate_now` `catch_up` çağırmaz: normal turdur, `proactivity_tick` ile
aynıdır (`tools.py:1264-1275`).

### 2.1 Snooze semantiği

```text
until  saat dilimli ISO-8601 ZORUNLU          service.py:1054-1055
until  şimdiden SONRA olmalı                  service.py:1056-1057
until + run_id  → koşu `snoozed` durumuna geçer   service.py:1061-1070
until + kind    → kural düzeyinde susar           service.py:1072-1078
serbest metin ("yarın sabah") çözümlenmez     INVALID_ARGUMENT
```

Snooze **açık kullanıcı override'ıdır** ve otomasyonun önündedir. `run_id` ile
verilen snooze koşuyu **`snoozed` durumuna geçirir** (`service.py:1067-1068`) —
bu "çözüldü" ya da "kapatıldı" değildir. Süre dolduğunda tur koşuyu yeniden
`candidate` yapar ve **güncel durumla** değerlendirir (`service.py:503-505`).

`unsnooze` override'ı kaldırır; bu **hemen** bildirim üretmez — sonraki tur karar
verir (`service.unsnooze`, `service.py:1081-1088`).

---

## 3. Çıktı şemaları

Pydantic karşılıkları `backend/app/modules/proactivity/schemas.py` içindedir ve
REST ile MCP **aynı şemayı** kullanır.

### 3.1 Durum (`ProactivityStatusOut`)

```text
enabled                    bool
quiet_hours_start          "HH:MM"
quiet_hours_end            "HH:MM"
focus_deferral_enabled     bool
digest_time                "HH:MM"
immediate_budget           int     (bugünkü anlık yüzey tavanı, 3)
immediate_surfaces_today   int     (bugün teslim edilen anlık yüzey)
pending_deferred           int     (ertelenmiş koşu)
pending_digest             int     (digest kuyruğundaki koşu)
worker_heartbeat           dict | null
last_run_at                str | null  (ISO-8601)
rules                      ProactivityRuleOut[]
recent_failures            ProactivityFailureOut[]
```

### 3.2 Kural (`ProactivityRuleOut`)

```text
kind            "morning_continuity" | ... | "project_stalled"
version         1
logical_key     "<kind>:v<version>:<scope>"
enabled         bool
config          { ... }        (kural türüne göre kapalı şema)
snoozed_until   str | null     (ISO-8601)
```

`recent_failures[]` (`ProactivityFailureOut`): `rule_kind`, `failure_code`, `at`
(ISO-8601). Son `MAX_RECENT_FAILURES = 5` kayıt gösterilir (`service.py:89`).

### 3.3 Koşu (`ProactivityRunOut`)

```text
id · rule_kind · subject_type · subject_id
state              candidate | deferred | digest_queued | snoozed
                 | delivered | suppressed | resolved | cancelled
                 | dismissed | failed
                 (snoozed: kullanıcı override'ı sürüyor; ayrı bir
                  durumdur, "resolved"/"dismissed" DEĞİLDİR)
reason_codes       string[]   (sınırlı sözlük — h6-policy.md §6)
why_now            str | null
triggered_at       ISO-8601
delivered_at       str | null
delivery_count     int
snoozed_until      str | null
notification_id    int | null
failure_code       str | null
```

### 3.4 Tur sayacı (`evaluate_now`)

```text
evaluated    int    (değerlendirilen kural sayısı)
candidates   int    (üretilen aday sayısı)
surfaced     int    (anlık teslim)
digested     int    (digest kuyruğuna giren)
deferred     int    (ertelenen)
suppressed   int    (sessizlik kazanan)
cancelled    int    (iptal edilen)
failed       string[]  (değerlendirmesi çöken kural türleri)
```

---

## 4. Hata kodları

| Kod | Anlam | Yüzey |
|---|---|---|
| `INVALID_ARGUMENT` | İşlem için gerekli alan eksik (`kind` / `until`) veya `until` ISO-8601 değil | MCP |
| `INVALID_CONFIG` | `HH:MM` biçimi ya da aralık dışı değer | MCP + REST (422) |
| `UNKNOWN_CONFIG_FIELD` | Kural türü için tanımsız ayar alanı | MCP + REST (422) |
| `UNKNOWN_RULE_KIND` | Kural türü kapalı kümede değil | MCP + REST (422) |
| `UNKNOWN_OPERATION` | İşlem yedili kümede değil | MCP |
| `INVALID_ENTITY_SCOPE` | Entity kapsamlı kuralın hedefi bulunamadı | MCP + REST (422) |
| `INVALID_SNOOZE` | Snooze damgası saat dilimsiz veya geçmişte | MCP + REST (422) |
| `RUN_NOT_FOUND` | Koşu kimliği yok | MCP + REST (404) |
| `PROACTIVITY_FAILED` | Beklenmeyen iç hata (`PROACTIVITY_FAILED: <Tip>`) | MCP |

Hata zarfı sızdırmazdır: yığın izi, SQL veya dosya yolu taşınmaz
(`tools.py:1279-1284`). REST tarafında `RUN_NOT_FOUND` → **404**, kalan
`ProactivityError` kodları → **422**; gövde `{"detail": "<KOD>: <mesaj>"}`
(`router.py:26-28`).

---

## 5. REST uçları

Tümü `/api` öneki altındadır (`backend/app/main.py:144`).

| Metot | Yol | Gövde | Dönüş | Hata |
|---|---|---|---|---|
| `GET` | `/api/proactivity/status` | — | durum şeması | — |
| `PUT` | `/api/proactivity/config` | `ProactivityConfigIn` | durum şeması | 422 |
| `GET` | `/api/proactivity/rules` | — | kural listesi | — |
| `PUT` | `/api/proactivity/rules/{kind}` | `ProactivityRuleIn` | kural şeması | 422 |
| `GET` | `/api/proactivity/history` | `?limit=1..50` (varsayılan 50) | koşu listesi | — |
| `POST` | `/api/proactivity/runs/{run_id}/snooze` | `SnoozeIn{until}` | koşu listesi | 404 / 422 |
| `DELETE` | `/api/proactivity/runs/{run_id}/snooze` | — | koşu listesi | 404 |
| `POST` | `/api/proactivity/rules/{kind}/snooze` | `SnoozeIn{until}` | kural listesi | 422 |

`ProactivityConfigIn` yalnızca bilinen alanları **okur**: `enabled`,
`quiet_hours_start`, `quiet_hours_end`, `focus_deferral_enabled`, `digest_time`
(`schemas.py:12-19`).

```text
configure  bilinmeyen alan  → REDDEDİLİR (422 / UNKNOWN_CONFIG_FIELD)
rule_set   bilinmeyen alan  → REDDEDİLİR (UNKNOWN_CONFIG_FIELD, §2)
snooze     saat dilimsiz / geçmiş damga → REDDEDİLİR (INVALID_SNOOZE)
```

`SnoozeIn.until` **saat dilimli** mutlak zamandır.

`GET /api/proactivity/rules` çağrısı kuralların açılışta yazılmasını
(varsayılanların tohumlanmasını) tetikler; idempotenttir (`router.py:56-58`).

---

## 6. Örnek çıktılar

### 6.1 `status`

```json
{
  "enabled": false,
  "quiet_hours_start": "23:30",
  "quiet_hours_end": "08:30",
  "focus_deferral_enabled": true,
  "digest_time": "18:30",
  "immediate_budget": 3,
  "immediate_surfaces_today": 0,
  "pending_deferred": 0,
  "pending_digest": 0,
  "worker_heartbeat": null,
  "last_run_at": null,
  "rules": [
    {
      "kind": "deadline_staircase",
      "version": 1,
      "logical_key": "deadline_staircase:v1:global",
      "enabled": true,
      "config": {},
      "snoozed_until": null
    },
    {
      "kind": "project_stalled",
      "version": 1,
      "logical_key": "project_stalled:v1:global",
      "enabled": false,
      "config": {"days": 14, "cooldown_days": 7},
      "snoozed_until": null
    }
  ],
  "recent_failures": []
}
```

### 6.2 `rule_set`

```json
{
  "kind": "continuity_gap",
  "enabled": true,
  "config": {"threshold_hours": 72},
  "snoozed_until": null
}
```

### 6.3 `history`

```json
{
  "runs": [
    {
      "id": 41,
      "rule_kind": "deadline_staircase",
      "subject_type": "deadline",
      "subject_id": "6f1c9f3e-0000-4000-8000-000000000003",
      "state": "delivered",
      "reason_codes": ["DEADLINE_3D"],
      "why_now": "Kurgusal kayıt için son tarih 3 gün içinde",
      "triggered_at": "2026-09-21T08:00:00+00:00",
      "delivered_at": "2026-09-21T08:00:02+00:00",
      "delivery_count": 1,
      "snoozed_until": null,
      "notification_id": 918,
      "failure_code": null
    },
    {
      "id": 40,
      "rule_kind": "daily_close",
      "subject_type": null,
      "subject_id": null,
      "state": "suppressed",
      "reason_codes": ["NO_MEANINGFUL_CONTENT"],
      "why_now": "gün kapanışı 2 açık uç buldu",
      "triggered_at": "2026-09-21T18:00:00+00:00",
      "delivered_at": null,
      "delivery_count": 0,
      "snoozed_until": null,
      "notification_id": null,
      "failure_code": null
    }
  ]
}
```

### 6.4 `evaluate_now`

```json
{
  "evaluated": 6,
  "candidates": 2,
  "surfaced": 1,
  "digested": 1,
  "deferred": 0,
  "suppressed": 0,
  "cancelled": 0,
  "failed": []
}
```

### 6.5 `snooze`

```json
{
  "snoozed": true,
  "until": "2026-09-27T21:00:00+00:00"
}
```

---

## 7. Özet semantiği (kritik)

```text
tetik ≠ bildirim          tetik yalnızca "şimdi değerlendir" demektir
sessizlik başarıdır      silent/defer/suppressed geçerli SONUÇLARDIR
idempotans DB'de         logical_trigger_key UNIQUE; tekrarlanan tur satır açmaz
yeniden doğrulama şart   teslimden hemen önce koşul güncel durumdan doğrulanır
kullanıcı override'ı üst  snooze otomasyonun önündedir
canonical mutasyon yok   yazma yolu H1'dir ve onay kapısından geçer
```

---

## 8. Yüzey doğrulaması

```text
H0 = 8    H1 = 11    H2 = 5    H3 = 1    H4 = 1    H5 = 1    H6 = 1    TOPLAM = 28
```

Yüzey sayısı ve aracın varlığı `backend/tests/test_agent_h6_contract.py` ile
doğrulanır (tek yeni araç, anotasyonlar, işlem kümesi, reddedilen alanlar);
taşıma `test_agent_h6_transport.py`, karar tablosu `test_h6_policy.py`, model ve
durum sözlüğü `test_h6_models.py`, kural üretimi `test_h6_rules.py`, teslim
metni `test_h6_delivery.py`, uçtan uca tur `test_h6_service.py`, REST uçları
`test_h6_api.py` ve worker zamanlaması `test_h6_worker.py` ile sınanır.

---

## 9. İlgili belgeler

- [H6 Proaktivite ve Dikkat Kontrolü](h6-proactivity.md) — ürün kimliği, boru
  hattı ve kural aileleri.
- [H6 Karar Politikası](h6-policy.md) — karar sırası, kategoriler, sınırlar.
- [H5 Araç Sözleşmesi](h5-tool-contract.md) — H6'nın bağlam kaynağı.
