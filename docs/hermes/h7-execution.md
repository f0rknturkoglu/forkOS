# forkOS × Hermes — H7 Durable Decision & Bounded Execution

H7, bir **öneriyi** kullanıcı kararından geçip **gerçek mutasyona** dönüştüren
tek yoldur. Tek sorusu şudur:

> *Kanıta dayanan bir planı insan onayıyla, yarıda kesilse bile doğru şekilde
> nasıl yürütürüm?*

Cevap iki kelimede özetlenir: **kalıcı karar**, **sınırlı yürütme**. H7 yeni
yetenek uydurmaz; H1'in kapalı yazma sözlüğünü kullanır ve **hiçbir adımı**
onaylanmış tam bir revizyonun parçası olmadan çalıştırmaz
(`backend/app/modules/execution/__init__.py:1-7`).

```text
Hermes   öneriyi üretir          (hangi adımlar, hangi kanıtla)
H7       sözleşmeyi doğrular     (deterministik, fail-closed)
KULLANICI kararı verir           (sunucu tarafı kayıt)
H7       revizyonu yürütür       (sınırlı, kesintiye dayanıklı)
H1       canonical mutasyonu yapar (tek yazma yolu)
```

---

## 1. Zincir: kanıttan makbuza

```text
1  EVIDENCE      forkos_evidence (H3) / forkos_review_intelligence (H5)
                 / forkos_proactivity (H6) → sınırlı kanıt referansları
                 "entity:<uuid>", "event:<id>", "review:<id>", "h3:..."
2  PROPOSAL      Hermes adımları üretir; kanıt referanslarını taşır
                 (model burada SERBESTTİR; sonuç bağlayıcı değildir)
3  PLAN          service.prepare() → kanonik revizyon `plan-v1:<sha256>`
                 (aynı içerik = aynı revizyon; yeni satır açılmaz)
4  VALIDATION    validation.validate_plan() → yapı, sınırlar, KAPALI aksiyon
                 kümesi, H1 şema doğrulaması, kanıt soyağacı, hedef tazeliği
5  DECISION      service.approve() / reject() / respond() / cancel()
                 YALNIZCA kullanıcı; onay sunucu tarafında ve revizyona bağlı
6  EXECUTION     service.execute() → claim (CAS) → adım adım H1 çağrıları
7  RECEIPT       adım başına TEK durable makbuz + append-only karar izi
```

Zincir tek yönlüdür: **adım 3–7 arasında hiçbir halka atlanamaz.** Modelin
"approved" demesi bir halka değildir (bkz. `h7-approval-policy.md`).

---

## 2. Sorumluluk paylaşımı

```text
Hermes   → öneri            hangi adımlar, hangi argümanlarla, hangi kanıtla
H7       → plan sözleşmesi  revizyon, doğrulama, kalıcı karar, yürütme, makbuz
H1       → mutasyon         todo/project/opportunity/bookmark/brain yazmaları
```

- **H7 kendi fiil dağarcığını uydurmaz:** adım `action` alanı yalnızca H1'in
  makine-okunur kayıt defterinden seçilebilir
  (`app/integrations/agent/write_registry.py:88-136`; 11 aksiyon).
- **Argümanlar H1'in kendi Pydantic modelleridir**: ikinci bir doğrulama
  yazılmaz, plan H1'in gördüğü şeyin aynısıdır
  (`app/modules/execution/steps.py:100-114`).
- **H7 kendi mutasyonunu yapmaz:** plan/karar durumu H7'nin operasyonel
  tablolarında yaşar; canonical domain'e dokunma yalnızca `execute` sırasında
  ve H1 üzerinden olur (`app/modules/execution/execution.py:151-157`).

Kanıt: `backend/tests/test_h7_approval.py::test_prepare_does_not_mutate_canonical_state`
(plan hazırlamak Entity kümesini değiştirmez).

---

## 3. Plan nesnesi

Bir satır = **bir immutable revizyon**. Aynı `plan_id` altındaki satırlar bir
soy ağacıdır (`ExecutionPlan`, `models.py:121-182`).

| Alan | Anlam |
|---|---|
| `plan_id` | soy ağacı kimliği (revizyonlar bu değeri paylaşır) |
| `revision` | `plan-v1:<sha256>` — onayın bağlandığı içerik özeti |
| `supersedes_revision` | bu revizyonun geçersiz kıldığı önceki revizyon |
| `state` | yaşam döngüsü (bkz. `h7-state-machine.md`) |
| `title` · `summary` · `reason` | sınırlı, olgusal metin (≤160/400/600) |
| `steps` | kanonik adım listesi (aşağıya bakın) |
| `step_count` · `mutation_count` · `budget` | sınırların görünür muhasebesi |
| `source_refs` · `evidence_refs` | kanıt soyu (sıralı + tekil, ≤20 + ≤20) |
| `validation_status` · `validation_errors` | doğrulama sonucu (≤10 hata) |
| `input_questions` · `input_answers` | eksik bilgi turu (≤3 soru) |
| `approved_at` · `approved_revision` · `decided_by` | **sunucu tarafı** onay kaydı |
| `rejected_at` · `cancelled_at` · `expires_at` | karar/TTL damgaları |
| `execution_started_at` · `executor_token` | yürütme sahipliği (CAS izi) |
| `final_status` · `failure_code` · `execution_finished_at` | dürüst sonuç |

### 3.1 Revizyon nedir, ne değildir

`revision_of()` kanonik JSON'un sha256'sıdır
(`revision.py:65-69`); girdi `normalized_plan()` çıktısıdır
(`revision.py:43-62`):

```text
adımlar          ordinal sırasına göre; argüman anahtarları SIRALI yazılır
kanıt referansları  sıralanır ve TEKİLLEŞTİRİLİR (sıra/kopya özeti bozmaz)
metinler         title/summary/reason normalize edilir
```

Özete **girmez** (`revision.py:14-22`): `created_at`/`updated_at`, satır `id`,
`plan_id`, `input_answers`, `state`, onay ve yürütme alanları. Yani aynı içerik
her zaman aynı revizyonu üretir; akışkan alanlar "onay" anlamı taşımaz.

```text
aynı başlık + aynı adımlar        → AYNI revizyon (idempotent prepare)
bir adımın argümanı değişir       → YENİ revizyon (eski onay geçersiz)
kanıt sırası değişir               → AYNI revizyon (semantik fark yok)
```

Kanıt: `test_h7_models.py::test_revision_ignores_key_order_and_evidence_order`,
`test_h7_approval.py::test_prepare_is_idempotent_for_identical_content`.

---

## 4. Adım sözleşmesi

```text
{
  step_id:              str    (varsayılan "s<n>"; plan içinde TEKİL)
  ordinal:              int    (yürütme sırası; listedeki konumdan gelir)
  action:               str    (KAPALI H1 kümesinden)
  arguments:            object (H1 giriş modeliyle doğrulanır)
  description:          str    (≤240)
  expected_updated_at:  str?   (onay anındaki hedef damgası)
}
```

Doğrulama sırası `steps.validate_steps()` içinde sabittir
(`steps.py:55-119`):

```text
yapı (nesne mi)            → INVALID_STEP
adım sayısı (≤10)          → PLAN_BUDGET_EXCEEDED
KAPALI aksiyon kümesi      → UNKNOWN_ACTION
argüman boyutu (≤8192 B)   → PLAN_BUDGET_EXCEEDED
metin uzunluğu (≤20000)    → PLAN_BUDGET_EXCEEDED
H1 Pydantic modeli         → INVALID_STEP_ARGUMENT
açıklama uzunluğu (≤240)   → INVALID_STEP
step_id tekilliği          → DUPLICATE_STEP_ID
boş plan                   → PLAN_HAS_NO_STEPS
```

`SKIPPED` yoktur: hiç denenmeyen adım `not_attempted` işaretlenir.

---

## 5. Doğrulama: onaydan önce, modele kapalı

`validation.validate_plan()` **saf ve deterministiktir**: model çağrısı yok,
yalnızca veritabanı okuması (hedef damgası) ve saf karşılaştırma
(`validation.py:152-228`).

```text
1  başlık zorunlu / metin sınırları        → TITLE_REQUIRED, BUDGET_EXCEEDED
2  kanıt referans şeması ve sınırı         → INVALID_REFS, UNKNOWN_REF_SCHEME, BUDGET_EXCEEDED
3  soru listesi (≤3)                       → INVALID_INPUT_REQUEST, BUDGET_EXCEEDED
4  adımlar (§4)                            → INVALID_STEP_ARGUMENT, UNKNOWN_ACTION, ...
5  adım/mutasyon tavanı                    → PLAN_BUDGET_EXCEEDED
6  kanıt soyağacı GERÇEK olmalı            → UNKNOWN_SOURCE_REF
7  hedef varlığı + freshness damgası       → STEP_TARGET_REQUIRED / _INVALID / _MISSING
8  hata varsa: invalid | soru varsa: input_required | yoksa: valid
```

- Referans şemaları **kapalıdır**: `entity`, `event`, `link`, `vault`, `h3`,
  `proactivity`, `review`, `aggregate`, `memory` (`validation.py:41-43`).
  `entity:<uuid>` referansları **gerçekten var olmalıdır**
  (`validation.py:83-96`) — uydurma provenance reddedilir
  (`test_h7_approval.py::test_prepare_rejects_fabricated_evidence`).
- Hedef damgası (`Entity.updated_at`) plana yazılır (`validation.py:99-148`) ve
  onay bu damgaya bağlanır: hedef sonradan değişirse adım stale olur.
- `input_required` sonucunda **"Approve" sunulmaz** (`validation.py:225-227`);
  plan `invalid` ise **hiç kaydedilmez** (`service.py:166-171`) — kullanıcıya
  gösterilmeyen plan yoktur.

Sınırlar (`models.py:105-118`): 10 adım, 10 mutasyon, 8192 bayt argüman,
20 kaynak/kanıt referansı, 10 doğrulama hatası, 50 liste limiti, 3 soru,
1000 karakter cevap.

---

## 6. Kalıcılık: üç tablo, tek amaç

Migration `0061_execution` (`backend/alembic/versions/0061_execution.py:28-108`):

| Tablo | Ne tutar | Neden |
|---|---|---|
| `execution_plan` | bir satır = bir immutable revizyon | onayın bağlanacağı sabit içerik |
| `execution_receipt` | adım başına **tek** makbuz | idempotans çapası |
| `execution_decision` | append-only karar/yürütme izi | "neden bu durumda?" sorusu |

```text
unique (plan_id, revision)          aynı içerik iki satır açamaz   :70
unique (plan_row_id, step_id)       aynı adım iki makbuz taşıyamaz :98
```

Bu tablolar `source_run`/`proactivity_run` ile **aynı sınıftır**: ajan/iş akışı
operasyonel kaydıdır, bağımsız aranabilir nesne değildir; bu yüzden entity
FK'si taşımaz (`models.py:1-12`, `0061_execution.py:12-18`).

Saklanmayanlar (bilinçli): tam model konuşma dökümü, ham istem/yanıt, sınırsız
kanıt gövdesi. Makbuz `detail` alanı ≤400 karakterdir
(`models.py:115`) ve yalnızca sınırlı H1 referansı/mesajı taşır.

---

## 7. Sınırlı yürütme

`execution.py:151-324` + `service.py:402-480`. Yedi kural:

**7.1 Claim DB-desteklidir (CAS).** `approved → executing` yalnızca koşullu
`UPDATE ... WHERE state = 'approved' ... RETURNING id` ile alınır
(`execution.py:73-92`). İkinci eşzamanlı çağrı `None` alır ve
`PLAN_ALREADY_EXECUTING` döner (`service.py:432-434`). Süreç-içi kilit yeterli
sayılmaz. Kanıt: `test_h7_execution.py::test_concurrent_execute_has_single_owner`
(iki eşzamanlı çağrı → tek mutasyon).

**7.2 Sıra deterministiktir.** Adımlar listedeki ordinal sırayla yürütülür
(`execution.py:173`); paralellik, bağımlılık çözümü ve yeniden sıralama
YOKTUR.

**7.3 Her adım öncesi freshness yeniden doğrulanır.** Onay anındaki damga ile
hedefin şimdiki `updated_at` değeri karşılaştırılır
(`execution.py:123-148`, çağrı `execution.py:249`). Farklıysa adım `failed` +
`STEP_STALE` yazılır ve yürütme **durur**
(`test_h7_execution.py::test_stale_target_stops_execution_and_marks_partial`).

**7.4 İlk hatada DURULUR.** `failed` veya `blocked` bayrağı kalktıktan sonra
kalan adımlar denenmez; her biri `not_attempted` makbuzu alır
(`execution.py:213-222`). Best-effort devam, yeniden deneme döngüsü ve
kısmi ilerleme ısrarı YOKTUR.

**7.5 Otomatik rollback/compensation YOKTUR.** Tamamlanmış adımlar geri
alınmaz; sonuç dürüstçe `partial` olur (`execution.py:307-315`).

**7.6 Makbuz varsa adım tekrar edilmez.** `completed` makbuzlu adım atlanır
(`execution.py:185-190`); `failed` makbuzlu adım yeniden denenmez
(`execution.py:191-196`). `idempotency_key` = `<revision>:<step_id>`
(`execution.py:269-281`).

**7.7 Makbuzsuz yarım adım mutabakat gerektirir.** `not_attempted` makbuz,
"sonuç bilinmiyor" demektir: adım `blocked` sayılır, **körlemesine tekrar
denenmez** ve `failure_code = RECONCILIATION_REQUIRED` raporlanır
(`execution.py:197-211`, `test_h7_execution.py::test_mutation_without_receipt_requires_reconciliation`).

### 7.1 Sonuç dürüstlüğü

```text
tüm adımlar tamam            → completed
kısmi tamam + sonra durdu    → partial   (tamamlananlar listelenir)
hiç tamam yok + hata/mutabakat → failed
failure_code                 → ilk hatanın kodu (or. STEP_STALE, NOT_FOUND,
                               RECONCILIATION_REQUIRED)
```

H1 hataları **sınırlı koda** indirgenir ve yığın izi dışarı sızmaz:
`INVALID_INPUT`, `NOT_FOUND`, `STALE`, `EXPIRED`, `CONFLICT`, `ACTION_ERROR`,
`FORBIDDEN`; tanınmayan hata `ACTION_FAILED` olur (`execution.py:327-343`).

### 7.2 Yürütme modele bağlı değildir

Plan hazır ve onaylıysa yürütme **deterministiktir**: hiçbir yerel veya uzak
model çağrılmaz (`execution.py:36-41`). Kanıt:
`test_h7_execution.py::test_execution_requires_no_model` (yerel biliş servisi
patlatılmış haldeyken plan yine tamamlanır).

---

## 8. Crash / resume modeli

```text
1  makbuzlar DURABLE'dır: süreç ölse de "hangi adım yapıldı" kaybolmaz
2  completed adım yeniden yürütülmez  → mükerrer mutasyon yok
3  not_attempted makbuz = belirsiz sonuç → RECONCILIATION_REQUIRED, tekrar YOK
4  failed adımın kodu korunur         → yeniden deneme aynı sonucu dürüstçe bildirir
```

Devam yolu `execution.execute_plan()`'in yeniden çağrılmasıdır: fonksiyon
mevcut makbuzları okuyup yalnızca eksik adımları yürütür
(`execution.py:160-171`). **Otomatik kurtarma worker'ı YOKTUR:** plan
`executing` durumunda kalmışsa servis düzeyindeki `execute()` yeniden
çağrıldığında `PLAN_ALREADY_EXECUTING` döner (`service.py:424-425`) — bu
bilinçli bir fail-closed tercihtir, çünkü sahiplik jetonu (`executor_token`)
süreç başına üretilir ve "ölü yürütücü" ile "canlı yürütücü" ayrımı H7 v1'in
kapsamı dışındadır.

Kanıt: `test_h7_execution.py::test_completed_steps_are_not_repeated_on_resume`
(yeniden yürütmede ikinci Todo oluşmaz).

---

## 9. Neler YOK (bilinçli)

```text
genel amaçlı DSL / recipe dili   shell · SQL · keyfî HTTP
serbest araç adı                 silme / yıkıcı eylem
otomatik onay                    modelin "approved" iddiasının yetkisi
otomatik rollback / telafi       paralel adım yürütme
çoklu ajan / çoklu yürütücü      LLM risk skoru veya önem tahmini
otomatik crash kurtarma worker'ı gözetim / kendiliğinden tetikleme
```

- **DSL yok:** adım kümesi kapalıdır; yeni yetenek eklemek H1'e fonksiyon
  eklemektir (`steps.py:1-16`).
- **Shell/SQL/HTTP/silme yok:** kapanış `ACTION_NAMES` ile zorlanır; bilinmeyen
  eylem **sessizce yok sayılmaz**, plan reddedilir (`steps.py:76-81`).
- **Otomatik onay yok:** onay sunucu tarafında üretilir; model
  `approved=true` gönderemez (`h7-approval-policy.md`).
- **Rollback yok:** yarım kalan iş `partial` olarak dürüstçe raporlanır;
  "temizlendi" izlenimi verilmez.
- **Risk skoru yok:** plan önceliği, aciliyeti veya "başarı olasılığı" için
  hiçbir skor üretilmez; karar kullanıcının onayıdır.
- **Zamanlayıcı yok:** H7 kendiliğinden çalışmaz; yürütme yalnızca açık bir
  çağrıyla başlar. Proaktif zamanlama H6'nın işidir ve H6 mutasyon yapmaz.

---

## 10. İlgili belgeler

- [H7 Durum Makinesi](h7-state-machine.md) — durumlar, izinli geçişler, MCP
  Tasks eşlemesi.
- [H7 Karar ve Onay Politikası](h7-approval-policy.md) — onay sunucu tarafıdır,
  dört karar türü, replay koruması, TTL, değişmezler.
- [H7 Araç Sözleşmesi](h7-tool-contract.md) — `forkos_execution` imzası, işlem
  tablosu, REST uçları, örnek çıktılar.
- [H1 Araç Sözleşmesi](h1-tool-contract.md) — adımların gerçek mutasyon
  sözlüğü.
- [H6 Proaktivite](h6-proactivity.md) — "ne zaman dokunmalıyız?" sorusunun
  cevabı (H7 ondan sonra başlar).
- [Yol Haritası](roadmap.md) — H7'nin serideki yeri.
