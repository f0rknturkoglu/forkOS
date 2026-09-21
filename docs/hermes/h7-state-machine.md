# forkOS × Hermes — H7 Durum Makinesi

H7 plan durumu **açık** ve **zorunlu** bir geçiş kümesiyle değişir. Durum
yalnızca `ensure_transition()` içinde tanımlı geçişlerle ilerler; terminal
durumdan çıkış **yoktur** (`completed → approved` imkânsızdır)
(`backend/app/modules/execution/state.py:1-6`).

```text
awaiting_approval ──► approved ──► executing ──► completed
       │                  │             │        └──► partial
       ├──► rejected      ├──► cancelled└───────────► failed
       └──► expired ◄─────┘
input_required ──► draft   (cevap sonrası yeniden hazırlık durağı)
```

Doğrulama AYRI bir durum DEĞİLDİR: plan satırı yazılmadan ÖNCE çalışır ve
sonucu denetim izine düşer (`validated` / `validation_failed`).

Diyagram bir **özet**tir; bağlayıcı olan §2'de birebir verilen tablodur.

---

## 1. Durumlar (11)

`PLAN_STATES` (`models.py:45-58`) — `state.py` bu kümenin dışına çıkılmasına
izin vermez; DB'de de check constraint vardır
(`alembic/versions/0061_execution.py:60-64`).

| Durum | Anlam | Karar bekler? |
|---|---|---|
| `draft` | cevap sonrası yeniden hazırlanmayı bekleyen revizyon | — |
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

| Kaynak | İzinli hedefler | Üreten yol |
|---|---|---|
| `draft` | `input_required`, `cancelled`, `expired` | `respond` (cevap sonrası dönüş), `cancel`, TTL |
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

"TTL" satırları `expire_due_plans()`'in kapsadığı durumlardır
(`awaiting_approval`, `input_required`, `approved`); `draft` bu taramanın
dışındadır — karar bekleyen bir plan değildir (`service.py:expire_due_plans`).

Kritik özellikler:

```text
onaydan sonra revizyon DEĞİŞEMEZ   approved → yalnızca executing/cancelled/expired
canonical yürütmenin TEK kapısı    approved → executing  (yalnızca CAS claim ile)
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
(`service.py:303`).

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

## 7. Ölü sözleşme yok — denetim sonucu

H7.0 taslağında tanımlı olup hiçbir yolda üretilmeyen değerler denetimde
bulundu ve **kapatıldı**: ya gerçek bir üretim yoluna bağlandı ya kaldırıldı.

```text
BAĞLANDI
  validation_failed   prepare() geçersiz öneriyi kaydetmez ama denetim izine
                      sınırlı bir kayıt bırakır (plan satırı OLMADAN):
                      "bu öneri neden reddedildi" cevaplanabilir kalır.
  execution_blocked   mutabakat gerektiren yarıda kalmış adım, `execution_blocked`
                      kararı olarak yazılır (step_failed ile birlikte).

KALDIRILDI (üretim yolu yoktu)
  validating (durum)          → doğrulama satır yazılmadan ÖNCE çalışır; ayrı bir
                                durum, gözlemlenemeyen ölü bir düğüm olurdu.
  skipped (adım sonucu)       → hiç denenmeyen adım `not_attempted`tır.
  pending / invalid (validation_status)
                              → geçersiz plan kaydedilmediği için kalıcı satırda
                                yalnızca `valid` ve `input_required` görülür.
  state.can_execute()         → yürütme kapısı CAS claim'dir; yardımcı ölüydü.
  execution._decision()       → denetim yazımı tek yerde: service._audit().
```

Kilit: `tests/test_h7_models.py::test_every_declared_state_and_code_has_a_production_path`
ve `test_no_dead_helpers_remain`.

---

## 8. İlgili belgeler

- [H7 Karar ve Yürütme](h7-execution.md) — zincir, plan nesnesi, sınırlı
  yürütme, crash/resume.
- [H7 Karar ve Onay Politikası](h7-approval-policy.md) — karar türleri,
  replay koruması, TTL, değişmezler.
- [H7 Araç Sözleşmesi](h7-tool-contract.md) — işlem tablosu ve örnek çıktılar.
