# forkOS × Hermes — H7 Karar ve Onay Politikası

Bu doküman H7'nin tek sorusunun cevabıdır: **"bu plan yürütülebilir mi, ve
yürütüldüyse ne oldu?"** Cevap beş ayrımda saklıdır; bu ayrımlar karıştığı
anda otomasyon "kendi kendine karar veren" bir sisteme dönüşür.

```text
akıl yürütme  ≠  yetki            (reasoning ≠ authorization)
onay          ≠  doğrulama        (approval ≠ validation)
plan          ≠  yürütme          (plan ≠ execution)
yürütme       ≠  başarı           (execution ≠ success)
kısmi         ≠  tamam            (partial ≠ completed)
```

---

## 1. Beş ayrım

### 1.1 Akıl yürütme ≠ yetki

Hermes planı üretir; bu bir **öneridir**. Önerinin doğru, düşünülmüş veya
"açıkça istenmiş" görünmesi yetki üretmez: yetki yalnızca sunucu tarafında
yazılan bir onay kaydıdır (`service.py:1-14`). Araç açıklaması bunu istemciye
açıkça söyler: *"a model can never approve"*
(`app/integrations/agent/tools.py:99-102`).

```text
model "approved": true derse      → yetkisi YOK; kayıt yoksa yürütme reddedilir
model onay niyetini iletir        → kanal kaydedilir (actor="mcp_client")
yetkiyi üreten yer                → approve() → approved_at + approved_revision
```

### 1.2 Onay ≠ doğrulama

Doğrulama **deterministik** bir kapıdır (`h7-execution.md` §5): şema, sınır,
kanıt soyağacı ve hedef tazeliği. Onay ise **insan kararıdır** ve doğrulamanın
yerini almaz; ikisi birbirinin önkoşuludur.

```text
doğrulama geçmedi  → plan KAYDEDİLMEZ, onay sorulamaz  (service.py:166-172)
doğrulama geçti    → awaiting_approval; "Approve" gösterilebilir
doğrulama eksik    → input_required; "Approve" SUNULMAZ (validation.py:225-227)
```

### 1.3 Plan ≠ yürütme

Plan hazırlamak canonical mutasyon **değildir**: yalnızca H7'nin operasyonel
tablolarına yazılır (`service.py:196-218`). Gerçek mutasyon tek bir yerde olur:
`execute()` sırasında ve H1 üzerinden (`execution.py:283-285`).

Kanıt: `test_h7_approval.py::test_prepare_does_not_mutate_canonical_state`.

### 1.4 Yürütme ≠ başarı

Çağrı tamamlandı diye sonuç tamam değildir. Yürütme **kendi sonucunu dürüstçe
raporlar**: tamamlanan adımlar, ilk hata kodu ve `final_status`
(`execution.py:307-324`).

```text
completed  tüm adımlar tamamlandı
partial    bir kısmı tamam, sonra DURDU
failed     hiçbir adım tamamlanmadı / mutabakat gerekli
```

### 1.5 Kısmi ≠ tamam

`partial` **terminal bir sonuçtur** ve `completed` değildir; `failure_code`
hangi adımda neden durulduğunu söyler. Tamamlanmış adımlar geri alınmaz
(otomatik rollback yoktur), yeniden denenmez ve "temizlendi" izlenimi
verilmez (`h7-execution.md` §7).

---

## 2. Onay sunucu tarafıdır — ve tam revizyona bağlanır

```text
approve(plan_row_id, revision)      service.py:269-316
  yazılan alanlar                   approved_at, approved_revision, decided_by
  denetim kaydı                     kind="approved", detail={"revision": ...}
  bağlandığı şey                    plan.revision  (plan-v1:<sha256>)
```

- **Yalnızca `awaiting_approval` onaylanır** (`service.py:284-285`).
- **İstenen revizyon güncel değilse onay reddedilir** (`APPROVAL_STALE`,
  `service.py:286-291`).
- **Soy ağacının en yeni revizyonu değilse onay reddedilir**
  (`APPROVAL_STALE`, `service.py:289-291`).
- **Hedef tazeliği onay anında yeniden doğrulanır**: kullanıcı gördüğü
  durumu onaylar; durum değiştiyse `PLAN_NEEDS_REVALIDATION`
  (`service.py:293-298`).
- Yürütmede aynı üç kural yinelenir: `approved_at`/`approved_revision` yok →
  `APPROVAL_REQUIRED`; `approved_revision != revision` ya da daha yeni bir
  revizyon var → `APPROVAL_STALE` (`service.py:414-430`).

Onaydan sonra plan **değişmez**: `approved → executing` dışında canonical
yürütmeye çıkan yol yoktur (`state.py:18-19`, `state.py:49-50`).

---

## 3. Dört karar türü

| Karar | Girdi | Uygulayıcı | Durum geçişi | Denetim türü |
|---|---|---|---|---|
| **APPROVE** | `plan_row_id` (+ `revision`) | `service.approve()` | `awaiting_approval → approved` | `approved` |
| **EDIT** | aynı `plan_id` ile yeni `prepare` | `service.prepare()` | yeni satır: `awaiting_approval`/`input_required` | `revision_created` |
| **REJECT** | `plan_row_id` | `service.reject()` | `awaiting_approval → rejected` | `rejected` |
| **RESPOND** | `plan_row_id`, `answers` | `service.respond()` | `input_required → draft` | `input_supplied` |

Ek olarak **CANCEL** her karar bekleyen/yürütülmemiş durumdan çalışır:
`draft`, `input_required`, `awaiting_approval`, `approved` (`state.py:14-20`).

### 3.1 EDIT neden ayrı bir işlem değil

Yerinde düzenleme **yoktur**: plan içeriği immutable'dır. Düzenleme, aynı
`plan_id` ile **yeni bir revizyon** hazırlamaktır; yeni satır
`supersedes_revision` alanıyla eskisini işaretler (`service.py:194-199`).

```text
prepare(plan_id=<aynı soy>)      → yeni satır + yeni revizyon
eski satırın onayı               → SİLİNMEZ (tarihsel kayıt olarak kalır)
eski satırın yürütülmesi         → APPROVAL_STALE (artık güncel revizyon değil)
yeni satır                       → yeniden onay ister
```

Kanıt: `test_h7_approval.py::test_new_revision_invalidates_previous_approval`.

### 3.2 REJECT ve RESPOND'un sınırları

```text
reject()   yalnızca awaiting_approval'dan         service.py:318-331
respond()  yalnızca input_required'dan            service.py:334-367
cevap boş  → INVALID_INPUT_RESPONSE               service.py:347-348
cevap anahtarı ≤64, değeri ≤1000 karakter          models.py:117-118
```

`respond()` **mutasyon üretmez**: cevap yeni bir eylem olamaz; plan `draft`'a
döner ve yeniden hazırlanır (`service.py:340-345`). Kanıt:
`test_h7_approval.py::test_respond_returns_plan_to_draft_without_mutation`.

---

## 4. Replay koruması

Aynı isteğin tekrarı yeni bir sonuç üretmez:

| Tekrar | Sonuç | Yer |
|---|---|---|
| aynı içerikle ikinci `prepare` | **aynı satır** döner (yeni revizyon açılmaz) | `unique (plan_id, revision)`, `service.py:180-192` |
| onaylanmış plana ikinci `approve` | `PLAN_NOT_APPROVABLE` | `service.py:284-285` |
| yürütülmüş plana ikinci `execute` | `PLAN_TERMINAL` | `service.py:426-427` |
| süren plana eşzamanlı `execute` | `PLAN_ALREADY_EXECUTING` (CAS kaybedilir) | `execution.py:73-92`, `service.py:432-434` |
| aynı adımın yeniden yürütülmesi | `completed` makbuz adımı atlatır | `execution.py:185-190` |
| eski revizyonun yürütülmesi | `APPROVAL_STALE` | `service.py:428-430` |
| süresi geçmiş planın yürütülmesi | `PLAN_EXPIRED` (durum `expired` yazılır) | `service.py:420-423` |

Adım düzeyinde mükerrer mutasyon, `execution_receipt` içindeki
`unique (plan_row_id, step_id)` kısıtıyla **veritabanında** engellenir
(`0061_execution.py:98`).

---

## 5. TTL — sınırsız bekleyen plan yoktur

```text
DEFAULT_PLAN_TTL_HOURS = 72                        models.py:99
expires_at = hazırlık anı + ttl_hours or 72        service.py:216
onay anında süre dolmuşsa  → PLAN_EXPIRED          service.py:280-281
yürütmede süre dolmuşsa    → state="expired" + PLAN_EXPIRED   service.py:420-423
okuma anında               → expire_due_plans() durumu maddileştirir  service.py:103-124
```

`expire_due_plans()` yalnızca **karar/yürütme bekleyen** durumları süresi
geçirir: `awaiting_approval`, `input_required`, `approved`
(`service.py:105-109`). `get_plan()` ve `list_plans()` her çağrıda bu taramayı
çalıştırır (`service.py:486`, `service.py:511`), yani süresi geçmiş bir plan
"hâlâ onaylanabilir" gibi görünmez.

Yürütme başladıktan sonra TTL uygulanmaz: `executing` bir karar beklemez.

---

## 6. `input_required` — eksik bilgi onayla kapatılmaz

```text
doğrulama soru üretirse plan input_required'a girer   validation.py:225-227
sorular sınırlıdır (≤3) ve 200 karaktere kırpılır      validation.py:180-187
"Approve" bu durumda SUNULMAZ                          validation.py:226
onay denemesi → PLAN_NOT_APPROVABLE                    service.py:284-285
respond() → draft (yeni revizyon, yeni onay gerekir)   service.py:334-367
```

Bu davranışın amacı, eksik bilgiyi **varsayımla doldurmak yerine** kullanıcıya
sormaktır: yanlış varsayım, geç onaydan daha pahalıdır.

---

## 7. Değişmezler

```text
onay kaydı yok                     → APPROVAL_REQUIRED
onay başka/eski revizyona ait      → APPROVAL_STALE
plan süresi geçmiş                 → PLAN_EXPIRED
hedef durum değişmiş (onay anı)    → PLAN_NEEDS_REVALIDATION
hedef durum değişmiş (adım anı)    → STEP_STALE (yürütme durur)
plan onaylanabilir durumda değil   → PLAN_NOT_APPROVABLE
plan reddedilmiş                   → PLAN_REJECTED
plan terminal durumda              → PLAN_TERMINAL
plan zaten yürütülüyor             → PLAN_ALREADY_EXECUTING
plan yok                           → PLAN_NOT_FOUND
```

| Kod | Tür | Üretim yeri | Kanıt |
|---|---|---|---|
| `APPROVAL_REQUIRED` | MCP + REST (422) | `service.py:414-415` | `test_h7_approval.py::test_approval_requires_server_side_record` |
| `APPROVAL_STALE` | MCP + REST (422) | `service.py:286-291`, `416-419`, `428-430` | `test_h7_approval.py::test_approval_with_wrong_revision_is_stale` |
| `PLAN_EXPIRED` | MCP + REST (422) | `service.py:280-281`, `420-423` | `test_h7_approval.py::test_expired_plan_cannot_be_approved` |
| `PLAN_NEEDS_REVALIDATION` | MCP + REST (422) | `service.py:293-298` | `test_h7_approval.py::test_source_freshness_blocks_stale_approval` |
| `STEP_STALE` | makbuz `error_code` | `execution.py:249-267` | `test_h7_execution.py::test_stale_target_stops_execution_and_marks_partial` |
| `PLAN_NOT_APPROVABLE` | MCP + REST (422) | `service.py:284-285` | `test_h7_approval.py::test_input_required_blocks_approval` |
| `PLAN_REJECTED` | MCP + REST (422) | `service.py:282-283` | `test_h7_approval.py::test_rejected_plan_cannot_execute` |
| `PLAN_TERMINAL` | MCP + REST (422) | `service.py:426-427`, `state.py:43-44` | `test_h7_execution.py::test_completed_steps_are_not_repeated_on_resume` |
| `PLAN_ALREADY_EXECUTING` | MCP + REST (**409**) | `service.py:424-425`, `432-434` | `test_h7_execution.py::test_concurrent_execute_has_single_owner` |
| `PLAN_NOT_FOUND` | MCP + REST (**404**) | `service.py:85-88` | `test_h7_approval.py::test_unknown_plan_is_reported` |

HTTP kodlaması `router.py:22-29` içindedir: `PLAN_NOT_FOUND` → `404`,
`*EXECUTING*` → `409`, kalan hatalar → `422`.

---

## 8. Neler YOK (bilinçli)

```text
modelin onayı / "kullanıcı onayladı" bayrağı   otomatik onay (timeout, kural,
sessiz onay                                      öncelik, düşük risk gerekçesi)
onay için ayrı tablo/kuyruk                    oy/çoklu onay (2 kişilik imza)
plan içeriğini yerinde düzenleme               revizyonun sessizce üzerine yazma
süresiz bekleyen plan                          "onaylanmış sayılır" varsayımı
başarı varsayımı (çağrı tamam = iş tamam)      risk skoru / güven yüzdesi
```

- **Otomatik onay yok:** onay daima açık bir çağrıdır; hiçbir zaman aşımı,
  kural veya "düşük risk" gerekçesi onayın yerine geçmez.
- **Sessiz onay yok:** onay kaydı yoksa yürütme `APPROVAL_REQUIRED` ile
  reddedilir; "muhtemelen onaylanmıştır" diye bir yol yoktur.
- **Güven yüzdesi yok:** planın doğruluğu, aciliyeti veya başarı olasılığı
  için hiçbir skor üretilmez; karar kullanıcının kararı olarak kalır.
- **Rollback yok:** onay geri alınmaz; iptal (`cancel`) yalnızca yürütme
  **başlamadan** çalışır (`state.py:14-20`). Yürütme başladıysa sonuç dürüstçe
  `partial`/`failed` olur.

---

## 9. İlgili belgeler

- [H7 Karar ve Yürütme](h7-execution.md) — zincir, plan nesnesi, sınırlı
  yürütme, crash/resume modeli.
- [H7 Durum Makinesi](h7-state-machine.md) — izinli geçişler ve MCP Tasks
  eşlemesi.
- [H7 Araç Sözleşmesi](h7-tool-contract.md) — `forkos_execution` işlemleri,
  REST uçları, örnek çıktılar.
- [H1 Araç Sözleşmesi](h1-tool-contract.md) — H1 onay modeli (istemci kapısı) ve
  yazma sözlüğü.
