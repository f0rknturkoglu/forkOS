# forkOS × Hermes — H1 MCP Araç Sözleşmesi

Bu belge, Brain Interface'in **19 genel MCP aracını** tanımlar: 8 okuma (H0) +
11 yazma (H1). Yazma araçlarının tamamı:

```text
external network: NO          (hiçbir dış ağ çağrısı yapmaz)
destructiveHint : false       (H1'de yıkıcı yetenek yoktur)
readOnlyHint    : false       (onay gerektirir; untrusted istemcide)
```

Ortak yanıt zarfı `AgentEnvelope[T]`:

```json
{ "as_of": "…", "source": "forkos | f0rknbrain", "data": { … }, "truncated": false }
```

Yazma araçlarında `data`, bir `ActionReceipt`'tir (bkz. `h1-safe-actions.md` §6).
Hata zarfı model-okunurdur; yığın izi ve iç dosya yolu SIZMAZ.

Ortak hata kodları:

```text
TARGET_NOT_FOUND   INVALID_INPUT     INVALID_TRANSITION   STALE_ACTION
MCP_ARGUMENT_BINDING_UNAVAILABLE
AMBIGUOUS_PLAN     INVALID_DATE      INVALID_TARGET       ACTION_NOT_ALLOWED
VAULT_UNAVAILABLE  VAULT_CONFLICT    VAULT_STALE          VAULT_WRITE_FAILED
KNOWLEDGE_NOT_FOUND  HEADING_NOT_FOUND  AMBIGUOUS_HEADING  APPLICATION_NOT_FOUND
EXPECTED_STATUS_REQUIRED
```

---

## 1. Okuma araçları (H0 — değişmedi)

Hepsi `readOnlyHint=true`, `destructiveHint=false`, `idempotentHint=true`.
Ayrıntılı H0 sözleşmesi: `h0-tool-contract.md`.

| Araç | Zorunlu | Opsiyonel |
|---|---|---|
| `forkos_briefing` | — | `day` |
| `forkos_search` | `query` | `entity_types`, `limit` |
| `forkos_entity_context` | `entity_id` | — |
| `forkos_project_context` | `project_id` | — |
| `forkos_recent_activity` | — | `since`, `entity_type`, `verb`, `limit` |
| `brain_status` | — | — |
| `brain_search` | `query` | `scope`, `limit` |
| `brain_read` | — | `forkos_id`, `relative_path`, `heading` |

> `brain_read` okuma amaçlı `relative_path` kabul eder: kullanıcının kendi
> Obsidian notları **okunabilir**. Yazma yüzeyinde böyle bir alan YOKTUR.

---

## 2. Yazma araçları (H1)

### 2.1 `forkos_todo_create`

- **Amaç:** tek görev oluşturur. `plan_day` verilirse aynı transaction'da plan
  kaydı da yazılır; `project_id` görevi projeye `belongs_to` ile bağlar.
- **Girdi:** `title*` (1–300), `description` (≤5000), `priority` (0–3, varsayılan 2),
  `due_at`, `reminder_at` (ISO), `plan_day` (YYYY-MM-DD), `project_id`,
  `milestone_id`, `parent_id`, `tags` (≤20), `recur` (`daily|weekdays|weekly|monthly`).
- **Önkoşul:** `project_id`/`parent_id`/`milestone_id` mevcut olmalı.
- **Yan etki:** `Entity`, `Todo`, (gerekiyorsa) `PlanSlot`, `Link`, `EntityTag`, `Event`.
  Yeni görev **her zaman `open`** doğar: `status=done|dropped` şemada yoktur.
- **İdempotans:** `false`.
- **Hatalar:** `INVALID_INPUT`, `TARGET_NOT_FOUND`.
- **Makbuz notu:** `after.planned_day`, `after.planned_start_min`,
  `after.project_title` — plan/ilişki yan etkisi görünür olur.

### 2.2 `forkos_todo_update`

- **Amaç:** mevcut görevin metadata'sını günceller.
- **Girdi:** `todo_id*`, `title` (≤300), `description` (≤5000), `priority` (0–3),
  `due_at`, `reminder_at`, `tags` (≤20), `recur` (boş metin rutini KALDIRIR),
  `expected_updated_at`.
- **Kapsam dışı:** durum (`done`/`dropped`), silme, ebeveyn/ilişki yeniden
  düzenleme — bunlar bu araçta YOKTUR.
- **Verilmeyen ≠ null:** bir alanı hiç göndermemek onu KORUR; açıkça `null`
  göndermek (desteklenen alanlarda, ör. `recur: ""`) temizler. `expected_updated_at`
  yalnızca önkoşuldur, mutasyon değildir.
- **Önkoşul:** `expected_updated_at` verilmişse `Entity.updated_at` ile
  eşleşmeli, aksi halde `STALE_ACTION`.
- **Yan etki:** `Todo`, `Entity` (touch), etiketler, `Event` — yalnızca verilen alanlar.
  Verilmeyen alanlar KORUNUR.
- **İdempotans:** `true` — istenen değerler zaten geçerliyse servis çağrılmaz
  ve `status=noop` döner.
- **Hatalar:** `TARGET_NOT_FOUND`, `STALE_ACTION`, `INVALID_INPUT`.

### 2.3 `forkos_todo_complete`

- **Amaç:** görevi **canonical tekrar kurallarıyla** tamamlar.
- **Girdi:** `todo_id*`.
- **Önkoşul:** görev mevcut olmalı.
- **Yan etki:** `status=done`, `completed_at`, entity touch, `todo.completed`
  olayı ve **rutin görevde bir sonraki oluşum**. Tekrar davranışı burada
  taklit EDİLMEZ; canonical servis çalışır.
- **İdempotans:** `true` — zaten `done` ise `status=noop` döner ve EK oluşum
  üretilmez. Noop makbuzu **gerçek kalıcı** `completed_at` değerini taşır.
- **Hatalar:** `TARGET_NOT_FOUND`.
- **Makbuz notu:** `after.next_occurrence_id` ve `warnings` yeni oluşumu bildirir.

> **Onay notu:** rutin bir görevi tamamlamak forkOS tekrar kurallarına göre
> bir sonraki oluşumu yaratabilir. Bu, onaylanan eylemin parçasıdır.

### 2.4 `forkos_todo_plan`

- **Amaç:** görevi planlar veya yeniden zamanlar (canonical PlanSlot servisleri).
- **Girdi:** `todo_id*`, `day*` (YYYY-MM-DD), `start_min` (0–1439), `duration_min` (5–1440).
- **Önkoşul / belirsizlik kuralı:** gelecekte uygun slot **yoksa** oluşturulur,
  **tek** slot varsa güncellenir, **birden fazla** varsa `AMBIGUOUS_PLAN`.
- **Yan etki:** yalnızca `PlanSlot` (+ canonical planlama olayı). Görev içeriği
  DEĞİŞMEZ.
- **İdempotans:** `true` — istenen sonuç mevcut slotla AYNIYSA canonical servis
  çağrılmaz, olay/timestamp üretilmez ve `status=noop` döner.
- **Hatalar:** `TARGET_NOT_FOUND`, `AMBIGUOUS_PLAN`, `INVALID_DATE`, `INVALID_INPUT`.

### 2.5 `forkos_project_update`

- **Amaç:** projenin **operasyonel** `next_action` alanını günceller.
- **Girdi:** `project_id*`, `next_action` (≤500), `expected_updated_at`.
- **Kapsam dışı (kasıtlı):** başlık yeniden adlandırma, `github_repo`, `url`,
  `stack`, `position`, silme.
- **Önkoşul:** `expected_updated_at` verilmişse eşleşmeli (`STALE_ACTION`).
- **Yan etki:** `Project`, `Entity` (touch), `Event`. **Vault'a DOKUNMAZ**:
  operasyonel güncelleme proje Markdown'ını yeniden yazmaz.
- **Verilmeyen ≠ null:** yalnızca `project_id` göndermek `next_action`'ı
  TEMİZLEMEZ (`status=noop`); `next_action: null` açıkça temizler.
- **İdempotans:** `true` — aynı değer ise servis çağrılmaz, `status=noop`.
- **Hatalar:** `TARGET_NOT_FOUND`, `STALE_ACTION`, `INVALID_INPUT`.

### 2.6 `forkos_opportunity_transition`

- **Amaç:** fırsatın **keşif/duyuru** yaşam döngüsünde geçiş yapar.
- **Girdi:** `opportunity_id*`, `expected_status*`, `to_status*`, `note` (≤1000).
- **Önkoşul:** güncel durum `expected_status` ile **birebir** eşleşmeli;
  aksi halde `STALE_ACTION`. Geçiş matrisi canonical `opportunity.lifecycle`
  tarafından doğrulanır.
- **Kapsam dışı:** başvuru CRM hattı — o `forkos_application_transition`'dadır.
- **Yan etki:** `Opportunity`, `Entity`, (canonical servis kullanıyorsa)
  `ApplicationHistory`, `Event`.
- **İdempotans:** `false`.
- **Hatalar:** `TARGET_NOT_FOUND`, `STALE_ACTION`, `INVALID_TRANSITION`, `INVALID_INPUT`.

Geçerli keşif akışı (iş/ staj): `discovered → shortlisted | dismissed | archived | closed`.
Duyuru akışı: `new → reviewed | watching | action_required | applied | completed | expired | archived`.

### 2.7 `forkos_application_transition`

- **Amaç:** başvurunun **CRM hattında** geçiş yapar.
- **Girdi:** `opportunity_id*`, `to_status*`, `expected_status`, `note` (≤1000),
  `rejection_reason` (≤200, yalnızca `rejected` için anlamlı).
- **Önkoşul:**
  - başvuru kaydı **yoksa** yalnızca `to_status="applied"` kaydı oluşturabilir
    (canonical `apply`) ve `expected_status` gerekmez; diğer hedefler
    `APPLICATION_NOT_FOUND`;
  - kayıt **varsa** `expected_status` ZORUNLUDUR; verilmezse
    `EXPECTED_STATUS_REQUIRED` ile reddedilir (tazelik önkoşulu isteğe bağlı olamaz);
  - `expected_status` güncel durumla eşleşmezse `STALE_ACTION`;
  - hedef zaten geçerli durum ise `status=noop`.
- **Yan etki:** `Application`, `ApplicationHistory`, (canonical servisin
  bağladığı) `Opportunity` alanları, `Entity`, `Event`.
- **İdempotans:** `false` (append-only geçmiş üretir).
- **Hatalar:** `TARGET_NOT_FOUND`, `APPLICATION_NOT_FOUND`, `STALE_ACTION`,
  `EXPECTED_STATUS_REQUIRED`, `INVALID_TRANSITION`, `INVALID_INPUT`.

> Terminal durumlar (`accepted`, `rejected`, `closed`) operasyonel durumdur,
> veri silme DEĞİLDİR. Yine de kullanıcı onayı zorunludur; Hermes bir
> başvurunun reddedildiğine kendi başına KARAR VERMEZ.

### 2.8 `forkos_bookmark_capture`

- **Amaç:** URL'yi **yerel olarak** yer imi kaydeder.
- **Girdi:** `url*` (http/https, ≤2048), `title` (≤300), `collection`
  (`inbox|read_later|learning|reference|projects|archive`, varsayılan `inbox`),
  `tags` (≤20), `note` (≤5000).
- **Yan etki:** yalnızca Bookmark domaini. **Sayfa getirilmez, metadata
  kazınmaz, zenginleştirme yapılmaz** ve bilgi notu OLUŞTURULMAZ.
- **Tekilleştirme:** aynı URL (takip parametreleri normalize edilerek) zaten
  kayıtlıysa YENİ KAYIT AÇILMAZ; `status=noop` + mevcut kaydın kimliği +
  "duplicate" uyarısı döner.
- **İdempotans:** `false` (yeni kayıt üretebilir).
- **Hatalar:** `INVALID_INPUT`.

### 2.9 `forkos_bookmark_update`

- **Amaç:** düşük riskli yer imi alanlarını günceller.
- **Girdi:** `bookmark_id*`, `collection`, `favorite`, `read_status`
  (`unread|reading|read`), `tags` (≤20), `expected_updated_at`.
- **Kapsam dışı:** silme, toplu işlem, ilerleme simülasyonu, vurgu silme,
  zenginleştirme, fulltext yeniden yazımı.
- **Önkoşul:** `expected_updated_at` verilmişse eşleşmeli (`STALE_ACTION`).
- **Yan etki:** `Bookmark`, `Entity`, etiketler, `Event`.
- **Verilmeyen ≠ null:** yalnızca `favorite` göndermek koleksiyon, okuma durumu
  ve etiketleri KORUR.
- **Etiketler** idempotans karşılaştırmasına DÂHİLDİR: aynı etiket kümesi
  yeniden gönderilirse `status=noop`, farklıysa `executed` ve makbuz `tags`
  alanını `changed_fields` içinde bildirir.
- **İdempotans:** `true` — aynı değer ise `status=noop`.
- **Hatalar:** `TARGET_NOT_FOUND`, `STALE_ACTION`, `INVALID_INPUT`.

### 2.10 `brain_capture`

- **Amaç:** f0rknbrain kasasına **yeni bilgi notu** yazar (`00 Inbox/`).
- **Girdi:** `body*` (1–40000), `title` (≤300), `relate_to` (forkOS UUID), `tags` (≤20).
- **Yan etki:** **tek bir Vault Markdown dosyası.** forkOS veritabanında
  `entity`/`note`/`note_folder`/`note_attachment`/`link` satırı OLUŞMAZ;
  legacy Notlar arşivine SIFIR yazma. `relate_to` yalnızca frontmatter
  ilişkisi olarak yazılır (hedef tipi/başlığı SUNUCUDA çözülür).
- **İdempotans:** `false` (her çağrı yeni dosya).
- **Hatalar:** `VAULT_UNAVAILABLE`, `VAULT_CONFLICT`, `VAULT_WRITE_FAILED`,
  `INVALID_TARGET`.
- **Makbuz notu:** gövde KOPYALANMAZ; `forkos_id`, `relative_path`, `title`,
  `note_kind`, `relation_count` döner.

### 2.11 `brain_save_to_entity`

- **Amaç:** bir kaydın **yönetilen** bilgi notuna metin EKLER.
- **Girdi:** `forkos_id*`, `text*` (1–20000), `heading` (≤200).
- **Hedef kuralı:** yalnızca kararlı yönetilen kimlik (`forkos_id`).
  `relative_path` şemada YOKTUR — kullanıcının kendi notları yazılamaz.
- **Not yoksa:** canonical `ensure` ile oluşturulur, sonra eklenir (tek
  semantik eylem).
- **Başlık verilirse:** tam eşleşen tek başlık aranır; 0 eşleşme
  `HEADING_NOT_FOUND`, >1 eşleşme `AMBIGUOUS_HEADING`.
- **Başarısızlık atomikliği:** hedef not yoksa ve `heading` verildiyse istek
  **yaratmadan önce** `HEADING_NOT_FOUND` ile reddedilir; yetim yönetilen dosya
  BIRAKILMAZ. Başlıksız istekte canonical `ensure` ile oluşturup eklemek tek
  semantik eylemdir.
- **Yan etki:** **tek bir yönetilen Markdown dosyası** (oluşturma ve/veya
  gövde ekleme). Gövde DEĞİŞTİRİLMEZ, kullanıcı frontmatter'ı ve Markdown'ı
  korunur. Vault `mtime` tazelik kontrolü uygulanır (`VAULT_STALE`).
- **İdempotans:** `false` (ekleme yapar; sonucu belirsizse önce `brain_read`).
- **Hatalar:** `VAULT_UNAVAILABLE`, `VAULT_CONFLICT`, `VAULT_STALE`,
  `KNOWLEDGE_NOT_FOUND`, `INVALID_TARGET`, `HEADING_NOT_FOUND`, `AMBIGUOUS_HEADING`.

---

## 3. Özet tablo

| Araç | readOnly | destructive | idempotent | Ağ |
|---|---|---|---|---|
| `forkos_briefing` … `brain_read` (8 okuma) | `true` | `false` | `true` | yok |
| `forkos_todo_create` | `false` | `false` | `false` | yok |
| `forkos_todo_update` | `false` | `false` | `true` | yok |
| `forkos_todo_complete` | `false` | `false` | `true` | yok |
| `forkos_todo_plan` | `false` | `false` | `true` | yok |
| `forkos_project_update` | `false` | `false` | `true` | yok |
| `forkos_opportunity_transition` | `false` | `false` | `false` | yok |
| `forkos_application_transition` | `false` | `false` | `false` | yok |
| `forkos_bookmark_capture` | `false` | `false` | `false` | yok |
| `forkos_bookmark_update` | `false` | `false` | `true` | yok |
| `brain_capture` | `false` | `false` | `false` | yok |
| `brain_save_to_entity` | `false` | `false` | `false` | yok |

**Toplam: 19 araç.** Bu sayı sözleşmedir: yeni bir mutasyon aracı eklemek
bilinçli bir karar gerektirir.
