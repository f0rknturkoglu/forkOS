# forkOS × Hermes — H7 Durum Makinesi

H7 plan durumu **açık** ve **zorunlu** bir geçiş kümesiyle değişir. Durum
yalnızca `ensure_transition()` içinde tanımlı geçişlerle ilerler; terminal
durumdan çıkış **yoktur** (`completed → approved` imkânsızdır)
(`backend/app/modules/execution/state.py:1-6`).

```text
draft ──► validating ──► awaiting_approval ──► approved ──► executing ──► completed
  │            │                  │                │             │
  │            │                  ├──► rejected    ├──► cancelled └──► partial
  │            │                  │                │              └──► failed
  └────────────┴──► input_required │                │
                     │            └──► expired ◄────┘
                     └──► draft
```

Diyagram bir **özet**tir; bağlayıcı olan §2'de birebir verilen tablodur.

---

## 1. Durumlar (12)

`PLAN_STATES` (`models.py:45-58`) — `state.py` bu kümenin dışına çıkılmasına
izin vermez; DB'de de check constraint vardır
(`alembic/versions/0061_execution.py:60-64`).

| Durum | Anlam | Karar bekler? |
|---|---|---|
| `draft` | doğrulama/karar için hazırlanmış taslak (cevap sonrası dönüş durağı) | — |
| `validating` | doğrulama aşaması (bkz. §7) | — |
| `input_required` | eksik bilgi var; "Approve" sunulmaz | ✅ |
| `awaiting_approval` | kullanıcı kararı bekleniyor | ✅ |
| `approved` | onay **sunucu tarafında** kayıtlı; revizyon kilitli | — |
| `executing` | yürütme sahipliği alınmış (CAS) | — |
| `completed` | tüm adımlar tamamlandı | terminal |
| `partial` | kısmi tamamlandı, sonra durdu | terminal |
| `failed` | hiçbir adım tamamlanmadı / mutabakat gerekli | terminal |
| `rejected` | kullanıcı reddetti | terminal |
| `cancelled` | kullanıcı iptal etti | terminal |
| `expired` | TTL doldu; kimse karar vermedi | terminal |

```text
TERMINAL_PLAN_STATES = {completed, partial, failed, rejected, cancelled, expired}   models.py:61-63
DECISION_REQUIRED_STATES = {awaiting_approval, input_required}                      models.py:66-68
FINAL_STATUSES = {completed, partial, failed, cancelled}                            models.py:96
```

`FINAL_STATUSES` yürütme bittiğinde yazılan `final_status` değerleridir;
`expired`/`rejected` yürütme sonucu değil, karar sonucudur.

---

## 2. İzinli geçişler (birebir)

`state.ALLOWED_TRANSITIONS` (`state.py:13-27`) — anahtar kaynak durumdur:

| Kaynak | İzinli hedefler | Tipik üretici |
|---|---|---|
| `draft` | `validating`, `input_required`, `cancelled`, `expired` | `prepare`, `respond`, `cancel`, TTL |
| `validating` | `awaiting_approval`, `input_required`, `expired` | doğrulama sonucu |
| `input_required` | `draft`, `cancelled`, `expired` | `respond`, `cancel`, TTL |
| `awaiting_approval` | `approved`, `rejected`, `cancelled`, `expired` | `approve`, `reject`, `cancel`, TTL |
| `approved` | `executing`, `cancelled`, `expired` | `execute` (claim), `cancel`, TTL |
| `executing` | `completed`, `partial`, `failed` | yürütme sonucu |
| `completed` | — | terminal |
| `partial` | — | terminal |
| `failed` | — | terminal |
| `rejected` | — | terminal |
| `cancelled` | — | terminal |
| `expired` | — | terminal |

Kritik özellikler:

```text
onaydan sonra revizyon DEĞİŞEMEZ   approved → yalnızca executing/cancelled/expired
canonical yürütmenin TEK kapısı    approved → executing  (state.can_execute:49-50)
terminal durumdan çıkış            ALLOWED_TRANSITIONS[terminal] == frozenset()
küme ile durum listesi birebir     set(ALLOWED_TRANSITIONS) == set(PLAN_STATES)
```

Kanıt: `test_h7_models.py::test_valid_transitions_are_allowed`,
`test_h7_models.py::test_terminal_states_have_no_exit`.

---

## 3. Geçiş zorlaması

```text
ensure_transition(current, target)      state.py:39-46
  bilinmeyen durum         → TransitionError("UNKNOWN_STATE")
  kaynak terminal          → TransitionError("PLAN_TERMINAL")
  hedef izinli değil       → TransitionError("INVALID_TRANSITION")
```

Hata **fail-closed**'dur: geçiş yapılmaz ve çağıran taraf durumu değiştiremez
(`state.py:30-37`). `TransitionError` MCP'de araç hatası, REST'te `422` olur
(`router.py:22-29`).

### 3.1 Geçersiz geçiş örnekleri

`test_h7_models.py:78-93` ile birebir sınanan set:

| Kaynak → Hedef | Neden geçersiz | Kod |
|---|---|---|
| `completed → approved` | terminal durumdan çıkış yok | `PLAN_TERMINAL` |
| `rejected → executing` | reddedilmiş plan yürütülemez | `PLAN_TERMINAL` |
| `expired → approved` | süresi geçmiş plana onay verilemez | `PLAN_TERMINAL` |
| `cancelled → awaiting_approval` | iptal geri alınamaz | `PLAN_TERMINAL` |
| `executing → approved` | yürütme başlamış; geri dönüş yok | `INVALID_TRANSITION` |
| `draft → executing` | canonical yürütme yalnızca `approved`'dan | `INVALID_TRANSITION` |
| `* → *` (bilinmeyen ad) | durum kümesi dışı | `UNKNOWN_STATE` |

Servis düzeyinde aynı kurallar daha **spesifik** koda çevrilebilir: örneğin
`approve()` terminal bir plana `PLAN_NOT_APPROVABLE`, reddedilmiş plana
`PLAN_REJECTED`, süresi geçmişe `PLAN_EXPIRED` der (`service.py:280-285`) —
ama hiçbiri geçişi zorlamaz; `ensure_transition` her zaman son sözü söyler
(`service.py:305`).

---

## 4. Terminal durumlar ve dürüstlük

```text
completed  tüm adımlar makbuzlu tamamlandı
partial    bir kısmı tamamlandı, sonra DURULDU (rollback YOK)
failed     hiçbir adım tamamlanmadı ya da mutabakat gerekli
rejected   kullanıcı reddetti            (kimse yürütmedi)
cancelled  kullanıcı iptal etti          (yürütme başlamadan durdu)
expired    TTL doldu; karar VERİLMEDİ    (aktif karar verilmedi)
```

Altı durum **tek terminal** değildir: `partial` bir başarısızlık değil, dürüst
bir kısmi sonuçtur; `expired` bir hata değil, karar verilmemesidir
(`service.py:103-124`). Bu ayrım korunmazsa denetim izi "ne oldu?" sorusunu
cevaplayamaz.

---

## 5. MCP Tasks eşlemesi

`forkos_execution` **senkron** bir istek/yanıt aracıdır: sunucu MCP Tasks
protokolünü uygulamaz (`create_task`, `TaskStore`, `tasks/get` yoktur). Her
çağrı bir sözlük döner ve plan durumu yanıttaki `state` alanındadır.

Aşağıdaki eşleme, durumları standart MCP Tasks sözlüğüyle **okuma
kılavuzu**dur; protokol düzeyinde bir taahhüt değildir.

| H7 durumu | MCP Tasks karşılığı | Not |
|---|---|---|
| `input_required` | `input_required` | eksik bilgi; sorular `input_questions`'ta |
| `awaiting_approval` | `input_required` | kullanıcı kararı da bir "girdi bekleniyor" durumudur |
| `executing` | `working` | yürütme sürüyor |
| `completed` | `completed` | tüm adımlar tamam |
| `failed` | `failed` | hiçbir adım tamamlanmadı |
| `cancelled` | `cancelled` | kullanıcı iptali |
| `draft` | — (iç durum) | cevap sonrası yeniden hazırlık durağı |
| `validating` | — (iç durum) | bekleme değil, doğrulama aşaması |
| `approved` | — (iç durum) | yetki var, **iş başlamadı** → `working` DEĞİL |
| `partial` | — (iç durum) | `completed` "tam", `failed` "hiç" demektir; ikisi de yalan |
| `rejected` | — (iç durum) | kullanıcı reddi; `cancelled`den farklı bir karar |
| `expired` | — (iç durum) | kimse karar vermedi; hata ya da iptal değil |

### 5.1 Birebir karşılığı olmayan iç durumlar neden korunuyor?

```text
approved   onay ile yürütme arasındaki tek güvenlik durağıdır: "yetki verildi
           ama mutasyon henüz olmadı". `working` denseydi, hiç başlamamış bir iş
           sürüyor gibi görünürdü.
partial    kısmi başarı gerçektir. `completed` yazmak tamamlanmamış adımları
           saklardı; `failed` yazmak yapılan işi inkâr ederdi.
rejected   insan kararıdır ve `cancelled`den ayrıdır: biri "istemiyorum",
           diğeri "vazgeçtim". Denetim izi ikisini ayırt etmek zorundadır.
expired    karar verilmemesidir. `failed` denseydi sistem suçlanır,
           `cancelled` denseydi kullanıcı suçlanırdı — ikisi de yanlış olurdu.
draft /    plan yaşam döngüsünün doğrulama/cevap duraklarıdır; dış yüzeye
validating "iş yok" diye değil, "hazırlık sürüyor" diye görünmelidir.
```

Ayrıca `validated` bir **durum değil**, `execution_decision.kind` değeridir:
doğrulamanın geçtiğini gösteren denetim kaydıdır
(`models.py:74-90`, `service.py:255`). Durum kümesine eklenmesi, iki farklı
ekseni (karar izi ≠ yaşam döngüsü) karıştırırdı.

---

## 6. Karar izi (`execution_decision`)

Append-only, sınırlı `detail` taşır (`models.py:217-236`). Kapalı tür kümesi
`DECISION_KINDS` (`models.py:74-90`):

```text
created · validated · validation_failed · input_requested · input_supplied
revision_created · approved · rejected · cancelled · expired
execution_started · step_completed · step_failed · execution_finished
execution_blocked
```

Bilinmeyen tür reddedilir: `UNKNOWN_DECISION_KIND` (`service.py:66-67`).
Kayıtlar `plan_id` + `plan_row_id` + `revision` taşıdığı için "hangi revizyonu
onaylamıştım?" sorusu tarihsel olarak cevaplanabilir kalır.

---

## 7. Tanımlı ama üretilmeyen değerler (dürüstlük notu)

Bu fazda aşağıdaki değerler sözleşmede tanımlıdır ancak mevcut servis
yollarında **üretilmez**; kod okunurken yanıltmasınlar diye açıkça yazılır:

| Değer | Durum |
|---|---|
| `validating` | `prepare()` doğrulamayı satır içi yapar ve doğrudan `awaiting_approval`/`input_required` yazar (`service.py:164-200`); `draft → validating` geçişini üreten bir yol yoktur |
| `validation_failed` (karar türü) | geçersiz plan kaydedilmediği için denetim satırı açılmaz; hata `PLAN_VALIDATION_FAILED` olarak çağırana döner (`service.py:166-172`) |
| `execution_blocked` (karar türü) | mutabakat durumu `step_failed` + `RECONCILIATION_REQUIRED` ile raporlanır (`execution.py:197-211`) |
| `skipped` (adım sonucu) | hiç denenmeyen adım `not_attempted` işaretlenir (`execution.py:213-222`) |
| `pending` / `invalid` (`validation_status`) | kaydedilen plan ya `valid` ya `input_required`'dır (`service.py:213-215`) |

Bu değerler "ölü sözleşme"dir: ya gerçek bir üretim yoluna bağlanmalı ya da
kaldırılmalıdır. Doküman şu anki davranışı anlatır, olmayan üretimi anlatmaz.

---

## 8. İlgili belgeler

- [H7 Karar ve Yürütme](h7-execution.md) — zincir, plan nesnesi, sınırlı
  yürütme, crash/resume.
- [H7 Karar ve Onay Politikası](h7-approval-policy.md) — karar türleri,
  replay koruması, TTL, değişmezler.
- [H7 Araç Sözleşmesi](h7-tool-contract.md) — işlem tablosu ve örnek çıktılar.
