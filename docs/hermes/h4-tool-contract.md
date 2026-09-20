# forkOS × Hermes — H4 Araç Sözleşmesi (`forkos_local_cognition`)

H4 genel yüzeye **tam olarak bir** araç ekler. Yüzey 26 olur
(H0 8 + H1 11 + H2 5 + H3 1 + H4 1). Mikro-araç çoğaltması YOKTUR: tek araç,
üç lane.

---

## 1. İmza

```text
forkos_local_cognition(
    lane:                "classify" | "structured_extract" | "query_rewrite",   # ZORUNLU
    text:                str,                        # ZORUNLU, 2-24000
    contract:            "academic_calendar_v1" | "weekly_schedule_v1"
                       | "deadline_candidates_v1" | None = None,
    labels:              list[str] | None = None,     # 2-20, tekil, her biri 1-80
    classification_goal: str | None = None,           # ≤ 300
    protected_terms:     list[str] | None = None      # ≤ 20, her biri 1-100
)
```

Anotasyonlar:

```text
readOnlyHint    = true
destructiveHint = false
idempotentHint  = true
```

Çıktı `AgentEnvelope` İLE SARILMAZ: bu bir okuma modeli değil, bir yürütme
sonucudur. Dönen gövde doğrudan `LocalCognitionResponse`'tur.

### 1.1 Model/ucu parametresi YOKTUR

Genel yüzeyde **asla** bulunmayanlar:

```text
model · model_id · base_url · endpoint · temperature · provider
system_prompt · prompt · tools · api_key · options
```

Bunlar yapılandırma ve iç politikadır. Genel yüzey semantiktir.

### 1.2 Lane/argüman uyumu

| Lane | Zorunlu | Reddedilen |
|---|---|---|
| `classify` | `labels`, `classification_goal` | `contract`, `protected_terms` |
| `structured_extract` | `contract` | `labels`, `classification_goal`, `protected_terms` |
| `query_rewrite` | — (`protected_terms` opsiyonel) | `contract`, `labels`, `classification_goal` |

Uyumsuz argüman sessizce YOK SAYILMAZ: `INVALID_ARGUMENT`.

---

## 2. Çıktı

```text
LocalCognitionResponse {
    status:         "success" | "needs_escalation"
    lane
    result?:        ClassificationResult | ExtractionResult | QueryRewriteResult
    failure_code?:  sınırlı kod
    recovery_hint?: eyleme dönük tek cümle
    route_decision: RouteDecision
}
```

`RouteDecision`:

```text
lane · selected_slot · selected_model · execution_boundary(=local_loopback)
input_chars · required_capabilities · reason_codes · attempts[]
validation_status(valid|invalid|not_attempted) · escalated · escalation_reason · latency_ms
```

Sağlayıcı düşmesi (H4.1): sağlık probu başarısızsa `status=needs_escalation`,
`failure_code=MODEL_PROVIDER_UNAVAILABLE`, `attempts=[]`, `selected_slot=null`,
`validation_status=not_attempted`. Bu bir uygulama hatası DEĞİLDİR: MCP yanıtı
`is_error=false` ile döner ve `LOCAL_COGNITION_FAILED` üretilmez.

`AttemptRecord` (yalnız GÜVENLİ meta veri):

```text
slot · model_id · attempt_number · latency_ms · validation_status · failure_code
```

Ham prompt, ham model çıktısı, kaynak metin, kanıt paketi veya sıcak hafıza bu
kayıtlarda **yer almaz**.

### 2.1 Sonuç tipleri

```text
ClassificationResult  { lane, label }              # güven/olasılık ALANI YOK
ExtractionResult      { lane, contract, items[] }
QueryRewriteResult    { lane, rewritten_query }    # 2-200
```

---

## 3. Örnek — akademik takvim çıkarımı

İstek:

```json
{
  "lane": "structured_extract",
  "contract": "academic_calendar_v1",
  "text": "Kayıt yenileme: 1 - 5 Eylül 2026\nDerslerin başlangıcı: 21 Eylül 2026\n"
}
```

Yanıt (kısaltılmış, gerçek bir canlı çağrıdan):

```json
{
  "status": "success",
  "lane": "structured_extract",
  "result": {
    "lane": "structured_extract",
    "contract": "academic_calendar_v1",
    "items": [
      {
        "title": "Kayıt yenileme",
        "category": "registration",
        "date_text": "1 - 5 Eylül 2026",
        "start_date": "2026-09-01",
        "end_date": "2026-09-05",
        "source_excerpt": "Kayıt yenileme: 1 - 5 Eylül 2026"
      }
    ]
  },
  "failure_code": null,
  "route_decision": {
    "lane": "structured_extract",
    "selected_slot": "local-small",
    "selected_model": "qwen2.5:14b-instruct-q4_K_M",
    "execution_boundary": "local_loopback",
    "input_chars": 68,
    "required_capabilities": ["structured_extract", "structured_output"],
    "reason_codes": [
      "LANE_STRUCTURED_EXTRACT",
      "STRUCTURED_OUTPUT_REQUIRED",
      "LOCAL_SMALL_SELECTED"
    ],
    "attempts": [
      {
        "slot": "local-small",
        "model_id": "qwen2.5:14b-instruct-q4_K_M",
        "attempt_number": 1,
        "latency_ms": 12540.8,
        "validation_status": "valid",
        "failure_code": null
      }
    ],
    "validation_status": "valid",
    "escalated": false,
    "latency_ms": 12540.8
  }
}
```

`source_excerpt` sağlanan metnin birebir parçasıdır: çıkarım denetlenebilir.

---

## 4. Girdi sınırları

| Alan | Sınır |
|---|---|
| `text` | 2–24000 karakter |
| `labels` | 2–20 adet, tekil, her biri 1–80 |
| `classification_goal` | ≤ 300 |
| `protected_terms` | ≤ 20 adet, her biri 1–100 |
| yeniden yazılan sorgu | 2–200 |
| çıkarım koleksiyonu | ≤ 80 öğe |
| `title` / `date_text` / `source_excerpt` | ≤ 200 / ≤ 120 / ≤ 500 |

Kaynak temellendirmesi (H4.1): `date_text` alıntıdan, normalize tarih/saat ise
deterministik ayrıştırıcıdan doğrulanır. Desteklenmeyen biçimde normalize alan
`null` kalmalıdır; eksik normalizasyon geçerlidir, uydurma değer değildir.

Şema ilk savunmadır; **çalışma zamanı otoritedir**. Aralık dışı girdi
KIRPILMAZ: `INVALID_ARGUMENT`.

---

## 5. Hata ve sonuç kodları

| Kod | Katman | Anlam |
|---|---|---|
| `H4_DISABLED` | hata | `H4_ENABLED=false` (varsayılan) |
| `INVALID_LANE` | hata | Lane aktif üçlüde değil (ertelenen/reddedilen dâhil) |
| `INVALID_ARGUMENT` | hata | Lane/argüman uyumsuzluğu, bilinmeyen sözleşme, sınır ihlali |
| `INVALID_LOCAL_MODEL_ENDPOINT` | hata | Sağlayıcı adresi loopback değil (bağlantı denenmez) |
| `CONTEXT_TOO_LARGE` | hata | Girdi TÜM yapılandırılmış bütçeleri aştı |
| `NO_ELIGIBLE_MODEL` | hata | Hiçbir slot yapılandırılmamış/uygun değil |
| `MODEL_PROVIDER_UNAVAILABLE` | `needs_escalation` | Yerel sağlayıcı erişilemez veya zaman aşımı |
| `MODEL_UNAVAILABLE` | `needs_escalation` | Yapılandırılmış model kurulu değil |
| `LOCAL_CAPABILITY_UNAVAILABLE` | `needs_escalation` | İki slot da denendi, sözleşme karşılanamadı |
| `VALIDATION_FAILED` | `needs_escalation` | Tek slot denendi, doğrulama tutmadı |

Doğrulama alt kodları (deneme kayıtlarında görünür): `INVALID_MODEL_JSON`,
`OUTPUT_SCHEMA_MISMATCH`, `INVALID_CLASS_LABEL`, `SOURCE_EXCERPT_NOT_FOUND`,
`SOURCE_FIELD_NOT_SUPPORTED`, `INVALID_DATE`, `INVALID_TIME`,
`PROTECTED_TERM_LOST`, `OUTPUT_TOO_LARGE`.

Kod semantiği (H4.1):

```text
SOURCE_EXCERPT_NOT_FOUND    alıntının KENDİSİ metinden değil
SOURCE_FIELD_NOT_SUPPORTED  ham alan (ör. date_text) alıntıdan değil
INVALID_DATE                normalize tarih kaynak çözümüyle çelişiyor
INVALID_TIME                normalize saat/gün ya da saat sırası kaynakla çelişiyor
```

Yönlendirme gerekçe kodları: `LANE_*`, `STRUCTURED_OUTPUT_REQUIRED`,
`LOCAL_SMALL_SELECTED`, `LOCAL_SMALL_UNAVAILABLE`, `LOCAL_SMALL_CONTEXT_EXCEEDED`,
`LOCAL_SMALL_VALIDATION_FAILED`, `LOCAL_MEDIUM_SELECTED`,
`ESCALATED_TO_LOCAL_MEDIUM`, `LOCAL_MEDIUM_UNAVAILABLE`,
`LOCAL_MEDIUM_CONTEXT_EXCEEDED`, `LOCAL_MEDIUM_VALIDATION_FAILED`,
`NO_ELIGIBLE_MODEL`, `LOCAL_CAPABILITY_UNAVAILABLE`.

```text
LOCAL_MEDIUM_SELECTED       İLK yönlendirme medium'u seçti (small hiç denenmedi)
ESCALATED_TO_LOCAL_MEDIUM   small DENENDİ ve medium'a çıkıldı (gerçek geçiş)
LOCAL_MEDIUM_CONTEXT_EXCEEDED  medium sağlıklı ama girdi bütçesi yetmiyor
LOCAL_MEDIUM_UNAVAILABLE       medium yapılandırılmamış/sağlıksız
```

`RouteDecision.escalated` yalnızca gerçek yukarı geçişte `true` olur.

`selected_slot` semantiği: yönlendirmenin **ilk deneme için seçtiği** slottur.
Yalnızca hiçbir slot uygun değilse, argüman hatası varsa ya da sağlayıcı sağlık
probu başarısızsa `null` olur; başarısız denemelerde `attempts` listesi ne
olduğunu söyler.

---

## 6. Deneme politikası

```text
local-small : ≤ 2 deneme (2. deneme sınırlı onarım promptu)
local-medium: ≤ 1 deneme
toplam      : ≤ 3 model çağrısı
yön         : yalnız YUKARI (small → medium); geri dönüş yok
```

Onarım promptu yalnızca doğrulama kodunu ve şema hatırlatmasını taşır.

---

## 7. Yüzey doğrulaması

```text
H0 = 8    H1 = 11    H2 = 5    H3 = 1    H4 = 1    TOPLAM = 26
```

Kanıt dosyaları: `test_agent_h4_contract.py` (yüzey + şema + yasak parametreler),
`test_agent_h4_transport.py` (gerçek `/mcp` + değişmezlik + gizli bağlam yok),
`test_h4_models.py` / `test_h4_policy.py` / `test_h4_service.py` /
`test_h4_ollama.py` (sözleşme, politika, akış, sağlayıcı), `test_h4_live.py`
(yalnız `H4_LIVE=1` ile koşan gerçek model testleri).
