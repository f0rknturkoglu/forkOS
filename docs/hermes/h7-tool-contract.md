# forkOS × Hermes — H7 Araç Sözleşmesi (`forkos_execution`)

H7 genel yüzeye **tam olarak bir** araç ekler. Yüzey **29** olur
(H0 8 + H1 11 + H2 5 + H3 1 + H4 1 + H5 1 + H6 1 + H7 1). Mikro-araç
çoğaltması YOKTUR: tek araç, dokuz işlem.

Araç bir otomasyon yürütücüsü **değildir**: kapalı bir işlem kümesi sunar ve
yürütme yalnızca **onaylanmış tam bir revizyon** üzerinde çalışır
(`backend/app/integrations/agent/tools.py:1307-1310`).

---

## 1. İmza

```text
forkos_execution(
    operation:       "prepare" | "get" | "list" | "approve" | "reject"
                   | "respond" | "cancel" | "execute" | "recover"
                   | "status",                                    # ZORUNLU
    title:           str | None = None,   # prepare; ≤ 160
    steps:           list[dict] | None = None,   # prepare; kapalı H1 adım kümesi
    summary:         str | None = None,   # prepare; ≤ 400
    reason:          str | None = None,   # prepare; ≤ 600
    source_refs:     list[str] | None = None,   # prepare; ≤ 20
    evidence_refs:   list[str] | None = None,   # prepare; ≤ 20
    input_questions: list[str] | None = None,   # prepare; ≤ 3
    plan_row_id:     int | None = None,   # get/approve/reject/respond/cancel/execute/recover; ≥ 1
    plan_id:         str | None = None,   # prepare; aynı soy ağacına yeni revizyon
    revision:        str | None = None,   # approve/execute; ≤ 80, `plan-v1:<sha256>`
    answers:         dict | None = None,   # respond
    states:          list[str] | None = None,   # list
    limit:           int | None = None    # list/status (varsayılan 20, ≤ 50)
)
```

Anotasyonlar (`tools.py:92-97`):

```text
readOnlyHint    = false      plan/karar durumunu YAZAR (H7'nin kendi tabloları)
destructiveHint = false      hiçbir kaydı silmez; canonical domain'e dokunmaz
idempotentHint  = true       aynı girdiyle tekrar çağrı ek durum üretmez
```

`execute` dışındaki tüm işlemler **yalnızca H7'nin operasyonel tablolarına**
yazar; canonical mutasyon tek bir yerde ve H1 üzerinden olur
(`execution.py:283-285`).

### 1.1 Reddedilen alan ve işlemler

Genel yüzeyde **asla** bulunmayanlar:

```text
tool · tool_name · function · shell · command · sql · query · script
http · url · webhook · channel · email · push · webhook_url
auto_approve · approved · skip_approval · force · dry_run=false · rollback
model · prompt · system_prompt · temperature · api_key
```

- Bilinmeyen `operation` → `UNKNOWN_OPERATION` (`tools.py:1453-1455`).
- Adım `action` kümesi **kapalıdır**: yalnızca
  `write_registry.WRITE_ACTIONS` içindeki 11 H1 eylemi
  (`write_registry.py:88-136`); bilinmeyen eylem `UNKNOWN_ACTION` ile planı
  reddeder (`steps.py:76-81`).
- `steps` serbest JSON **değildir**: her argüman H1'in Pydantic modelinden
  geçer (`steps.py:88-95`).
- Onay bir **alan değildir**: `approved: true` diye bir girdi yoktur; onay
  ayrı bir işlemdir ve sunucu tarafında kayıt üretir (`tools.py:99-102`).

---

## 2. İşlem tablosu

| İşlem | Zorunlu girdi | Ek girdi | Çıktı | Hatalar |
|---|---|---|---|---|
| `prepare` | `title`, `steps` | `summary`, `reason`, `source_refs`, `evidence_refs`, `input_questions`, `plan_id` | plan görünümü (§3) | `INVALID_ARGUMENT`, `PLAN_VALIDATION_FAILED` |
| `get` | `plan_row_id` | — | plan görünümü | `INVALID_ARGUMENT`, `PLAN_NOT_FOUND` |
| `list` | — | `states`, `limit` | `{"plans": [ ... ]}` | `EXECUTION_FAILED` |
| `approve` | `plan_row_id` | `revision` | plan görünümü | `PLAN_EXPIRED`, `PLAN_REJECTED`, `PLAN_NOT_APPROVABLE`, `APPROVAL_STALE`, `PLAN_NEEDS_REVALIDATION` |
| `reject` | `plan_row_id` | — | plan görünümü | `PLAN_NOT_FOUND`, `INVALID_TRANSITION`, `PLAN_TERMINAL` |
| `respond` | `plan_row_id`, `answers` | — | plan görünümü | `PLAN_NOT_AWAITING_INPUT`, `INVALID_INPUT_RESPONSE` |
| `cancel` | `plan_row_id` | — | plan görünümü | `INVALID_TRANSITION`, `PLAN_TERMINAL` |
| `execute` | `plan_row_id` | `revision` | plan görünümü + `final_status` | `APPROVAL_REQUIRED`, `APPROVAL_STALE`, `PLAN_EXPIRED`, `PLAN_ALREADY_EXECUTING`, `PLAN_TERMINAL` |
| `recover` | `plan_row_id` | — | plan görünümü + `final_status` | `PLAN_NOT_FOUND`, `PLAN_NOT_RECOVERABLE`, `PLAN_ACTIVE_EXECUTOR`, `PLAN_ALREADY_RECOVERING` |
| `status` | — | `limit` | `{"pending_decisions": [...], "recent": [...]}` | `EXECUTION_FAILED` |

`recover` çökmüş bir yürütmeyi devralır ve **fail-closed** çalışır: yalnızca
`claimed_by` boş adımlar yürütülür. Dayanıklı talebi (`status=not_attempted` +
`claimed_by`) görünen adım otomatik TEKRARLANMAZ; sonuç `unresolved` +
`RECONCILIATION_REQUIRED` olur. Ayrıntı: `h7-execution.md` (adım niyeti
dayanıklılık sınırı).

İşlem yönlendirmesi tek bir servis katmanına gider (`service.py`); araç kendi
ikinci durum kopyasını tutmaz. MCP ile REST **aynı** `_plan_view()` çıktısını
üretir (`service.py:532-574`).

### 2.1 Kaydedilen aktör

```text
MCP  approve/reject/respond/cancel/execute/recover  → actor = "mcp_client"   tools.py:1402-1457
REST approve/reject/respond/cancel/execute/recover  → actor = "forkos_ui"    service.py:274/319/339/371/407/518
sistem kaynaklı süre dolumu                 → actor = "system"        service.py:122
```

`decided_by` **yeti üretmez**; yalnızca kararın hangi kanaldan geldiğini
kaydeder. Yetki her zaman `approve()` içinde üretilir.

---

## 3. Plan görünümü şeması

`_plan_view()` (`service.py:532-574`) — `get`, `approve`, `reject`, `respond`,
`cancel`, `execute`, `prepare` aynı şemayı döner:

```text
plan_row_id           int      satır kimliği (soy ağacı DEĞİL)
plan_id               uuid     soy ağacı kimliği
revision              str      `plan-v1:<sha256>` (onayın bağlandığı özet)
is_current_revision   bool     soy ağacının en yeni revizyonu mu
state                 str      12 durumdan biri (h7-state-machine.md)
title · summary · reason           sınırlı metinler
steps                 object[] {step_id, action, arguments, description, expected_updated_at}
step_count · mutation_count · budget   sınır muhasebesi
source_refs · evidence_refs            sıralı + tekil kanıt referansları
validation_status · validation_errors  doğrulama sonucu
input_questions · input_answers        eksik bilgi turu
approved_revision · approved_at        sunucu tarafı onay kaydı
expires_at            str|null  TTL damgası (ISO-8601)
decision_required     bool      state ∈ {awaiting_approval, input_required}
final_status · failure_code            yürütme sonucu (dürüst)
receipts              object[]  adım makbuzları (ordinal sıralı)
created_at · updated_at                ISO-8601
```

`receipts[]`: `step_id`, `ordinal`, `action`, `target`, `status`
(`completed|failed|skipped|not_attempted`), `error_code`, `result_ref`,
`completed_at`. Tam H1 yanıt gövdesi **taşınmaz**; `result_ref` yalnızca
sınırlı bir referanstır (`models.py:184-214`).

---

## 4. Hata kodları

| Kod | Anlam | Yüzey |
|---|---|---|
| `INVALID_ARGUMENT` | İşlem için gerekli alan eksik (`title`+`steps`, `plan_row_id`, `answers`) | MCP |
| `PLAN_VALIDATION_FAILED` | Doğrulama reddetti; plan **kaydedilmedi** | MCP |
| `PLAN_NOT_FOUND` | Satır kimliği yok | MCP + REST (404) |
| `APPROVAL_REQUIRED` | Onay kaydı yok; yürütme reddedildi | MCP + REST (422) |
| `APPROVAL_STALE` | Onay/istek güncel revizyona ait değil | MCP + REST (422) |
| `PLAN_EXPIRED` | TTL doldu | MCP + REST (422) |
| `PLAN_NEEDS_REVALIDATION` | Hedef durum değişti; plan yenilenmeli | MCP + REST (422) |
| `PLAN_NOT_APPROVABLE` | Durum onaylanabilir değil (or. `input_required`) | MCP + REST (422) |
| `PLAN_REJECTED` | Plan reddedilmiş | MCP + REST (422) |
| `PLAN_TERMINAL` | Terminal durumda; geçiş yok | MCP + REST (422) |
| `PLAN_ALREADY_EXECUTING` | Yürütme sahipliği başka çağrıda / sürüyor | MCP + REST (**409**) |
| `PLAN_NOT_AWAITING_INPUT` | `respond` yanlış durumda | MCP + REST (422) |
| `INVALID_INPUT_RESPONSE` | Cevap boş | MCP + REST (422) |
| `INVALID_TRANSITION` / `UNKNOWN_STATE` | Durum makinesi geçişi reddetti | MCP + REST (422) |
| `UNKNOWN_OPERATION` | İşlem dokuzlu kümede değil | MCP |
| `UNKNOWN_DECISION_KIND` | İç denetim türü tanımsız (iç hata) | MCP + REST |
| `EXECUTION_FAILED` | Beklenmeyen iç hata (`EXECUTION_FAILED: <Tip>`) | MCP |

Hata zarfı sızdırmazdır: yığın izi, SQL veya dosya yolu taşınmaz
(`tools.py:1456-1461`). Adım düzeyindeki H1 hataları çağırana değil, **makbuza**
yazılır ve sınırlı koda indirgenir: `INVALID_INPUT`, `NOT_FOUND`, `STALE`,
`EXPIRED`, `CONFLICT`, `ACTION_ERROR`, `FORBIDDEN`, aksi halde `ACTION_FAILED`
(`execution.py:327-342`).

---

## 5. REST uçları

Tümü `/api` öneki altındadır (`backend/app/main.py:144`);
`backend/app/modules/execution/router.py:40-107`.

| Metot | Yol | Gövde | Dönüş | Hata |
|---|---|---|---|---|
| `GET` | `/api/execution/plans` | `?states=a,b&limit=1..50` | plan görünümü listesi | 422 |
| `GET` | `/api/execution/plans/{plan_row_id}` | — | plan görünümü | 404 |
| `POST` | `/api/execution/plans/{plan_row_id}/approve` | `DecisionIn{revision?}` | plan görünümü | 422 |
| `POST` | `/api/execution/plans/{plan_row_id}/reject` | `DecisionIn{revision?}` | plan görünümü | 422 |
| `POST` | `/api/execution/plans/{plan_row_id}/respond` | `RespondIn{answers}` | plan görünümü | 422 |
| `POST` | `/api/execution/plans/{plan_row_id}/cancel` | `DecisionIn{revision?}` | plan görünümü | 422 |
| `POST` | `/api/execution/plans/{plan_row_id}/execute` | `DecisionIn{revision?}` | plan görünümü (+`final_status`) | 409 / 422 |

```text
plan hazırlama için REST ucu YOKTUR: plan üretimi Hermes/MCP yolundadır.
karar uçları canonical mutasyon YAPMAZ; yalnızca plan durumunu değiştirir  router.py:1-6
`states` filtresi bilinmeyen durum adını sessizce düşürür (boş liste döner).
```

---

## 6. Örnek çıktılar

### 6.1 `prepare` — kullanıcı kararı bekleyen plan

```json
{
  "plan_row_id": 12,
  "plan_id": "3f9d5b1a-6c2e-4f0b-9a1d-2b7c4e8f5a90",
  "revision": "plan-v1:5f2c1ab0d94e37c6817f0e2a4d5b6c8e9f10a1b2c3d4e5f60718293a4b5c6d7e",
  "is_current_revision": true,
  "state": "awaiting_approval",
  "title": "Kurgusal proje sonraki adımını güncelle",
  "summary": "İki adımlı kurgusal plan.",
  "reason": "Kurgusal vaka: sonraki adım alanı boş kalmış.",
  "steps": [
    {
      "step_id": "s1",
      "action": "project_update",
      "arguments": {"project_id": "11111111-2222-4333-8444-555555555555", "next_action": "Kurgusal taslağı tamamla"},
      "description": "Sonraki adımı yaz",
      "expected_updated_at": "2026-09-21T08:00:00+00:00"
    },
    {
      "step_id": "s2",
      "action": "todo_create",
      "arguments": {"title": "Kurgusal görev", "plan_day": "2026-09-22"},
      "description": "Takip görevi aç",
      "expected_updated_at": null
    }
  ],
  "step_count": 2,
  "mutation_count": 2,
  "budget": {"max_steps": 10, "max_mutations": 10, "steps": 2},
  "source_refs": ["entity:11111111-2222-4333-8444-555555555555"],
  "evidence_refs": ["h3:evidence-bundle-7"],
  "validation_status": "valid",
  "validation_errors": [],
  "input_questions": [],
  "input_answers": {},
  "approved_revision": null,
  "approved_at": null,
  "expires_at": "2026-09-24T09:00:00+00:00",
  "decision_required": true,
  "final_status": null,
  "failure_code": null,
  "receipts": [],
  "created_at": "2026-09-21T09:00:00+00:00",
  "updated_at": "2026-09-21T09:00:00+00:00"
}
```

### 6.2 `execute` — kısmi sonuç (ikinci adım stale)

```json
{
  "plan_row_id": 12,
  "state": "partial",
  "is_current_revision": true,
  "approved_revision": "plan-v1:5f2c1ab0d94e37c6817f0e2a4d5b6c8e9f10a1b2c3d4e5f60718293a4b5c6d7e",
  "approved_at": "2026-09-21T09:05:00+00:00",
  "decision_required": false,
  "final_status": "partial",
  "failure_code": "STEP_STALE",
  "receipts": [
    {
      "step_id": "s1",
      "ordinal": 0,
      "action": "project_update",
      "target": "11111111-2222-4333-8444-555555555555",
      "status": "completed",
      "error_code": null,
      "result_ref": "11111111-2222-4333-8444-555555555555",
      "completed_at": "2026-09-21T09:05:01+00:00"
    },
    {
      "step_id": "s2",
      "ordinal": 1,
      "action": "todo_update",
      "target": "99999999-8888-4777-8666-555555555555",
      "status": "failed",
      "error_code": "STEP_STALE",
      "result_ref": null,
      "completed_at": "2026-09-21T09:05:01+00:00"
    }
  ]
}
```

### 6.3 `respond` — eksik bilgi turu

```json
{
  "plan_row_id": 14,
  "state": "draft",
  "validation_status": "input_required",
  "input_questions": ["Hangi kurgusal CV kullanılmalı?"],
  "input_answers": {"cv": "Backend CV"},
  "decision_required": false,
  "expires_at": "2026-09-24T09:00:00+00:00"
}
```

### 6.4 `status` — bekleyen kararlar

```json
{
  "pending_decisions": [
    {
      "plan_row_id": 14,
      "plan_id": "8c1e2d3f-4a5b-4c6d-8e7f-901122334455",
      "state": "input_required",
      "decision_required": true,
      "title": "Kurgusal başvuru hazırlığı",
      "expires_at": "2026-09-24T09:00:00+00:00"
    }
  ],
  "recent": [
    {
      "plan_row_id": 13,
      "plan_id": "3f9d5b1a-6c2e-4f0b-9a1d-2b7c4e8f5a90",
      "state": "completed",
      "decision_required": false,
      "final_status": "completed",
      "failure_code": null
    }
  ]
}
```

### 6.5 Hata yanıtı (MCP)

```json
{
  "is_error": true,
  "content": "APPROVAL_REQUIRED: plan onaylanmamis"
}
```

---

## 7. Özet semantiği (kritik)

```text
öneri ≠ yetki            plan hazırlamak izin DEĞİLDİR
onay sunucu tarafıdır     model onaylayamaz; kayıt yoksa APPROVAL_REQUIRED
onay revizyona bağlıdır   yeni revizyon eski onayı GEÇERSİZ kılar
doğrulama modele kapalı   invalid plan hiç kaydedilmez
yürütme tek sahipli        CAS ile devralınır; ikinci çağrı kaybeder
ilk hatada durulur        best-effort devam ve otomatik rollback YOK
makbuz idempotanstır      completed adım restart sonrası tekrarlanmaz
sonuç dürüsttür           partial ≠ completed; failure_code gizlenmez
```

---

## 8. Yüzey doğrulaması

```text
H0 = 8    H1 = 11    H2 = 5    H3 = 1    H4 = 1    H5 = 1    H6 = 1    H7 = 1    TOPLAM = 29
```

Yüzey sayısı ve aracın varlığı `backend/tests/test_agent_h1_contract.py`,
`test_agent_h3_contract.py`, `test_agent_h4_contract.py`,
`test_agent_h5_contract.py`, `test_agent_h6_contract.py` ve
`test_agent_tools.py` içindeki yüzey sayaçlarıyla; taşıma
`test_agent_mcp.py` ile sınanır. H7'nin davranışı `test_h7_models.py`
(revizyon, durum makinesi, adım doğrulama), `test_h7_approval.py` (onay, TTL,
tazeleme, red) ve `test_h7_execution.py` (yürütme, durma, kısmi sonuç,
mükerrer/eşzamanlı yürütme, mutabakat) ile doğrulanır.

---

## 9. İlgili belgeler

- [H7 Karar ve Yürütme](h7-execution.md) — zincir, plan nesnesi, sınırlı
  yürütme, crash/resume.
- [H7 Durum Makinesi](h7-state-machine.md) — durumlar, izinli geçişler, MCP
  Tasks eşlemesi.
- [H7 Karar ve Onay Politikası](h7-approval-policy.md) — beş ayrım, dört karar
  türü, değişmez tablosu.
- [H1 Araç Sözleşmesi](h1-tool-contract.md) — adımların gerçek H1 karşılıkları.

## Contextual planning freshness (plan-v3)

Yeni hazırlanan `todo_plan` adımları `expected_plan_fingerprint` taşır. Sunucu bu değeri mevcut gelecek PlanSlot kayıtlarının kimliği, günü, başlangıcı ve süresinden üretir; model değeri belirleyemez. Onayda ve adım öncesinde yeniden doğrulanır. Eski plan-v1/v2 kayıtları kendi saklanmış revizyonlarıyla okunabilir; yeniden hesaplanmaz. Yeni içerik plan-v3 ile onaylanır. Canonical Todo/Entity yazma kapsamı genişlemez.
