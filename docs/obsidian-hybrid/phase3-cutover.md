# PHASE 3 — Bilgi sahipliği devri (cutover)

> **Tek cümle:** forkOS artık insan bilgisinin sahibi değil.
> forkOS **yürütmeyi**, f0rknbrain Obsidian Vault'u **bilgiyi** yönetir.

Bu belge devrin sözleşmesini, dondurulan legacy arşivi, çalışma zamanı
gereksinimlerini ve geri dönüş yolunu tanımlar.

---

## 1. Yeni sahiplik sınırı

```text
                forkOS                        f0rknbrain (Obsidian Vault)
                ──────                        ──────────────────────────
                Today, Tasks, Routines        Notlar, Daily notes
                Planner, Pomodoro             Proje bilgi notları
                Calendar                      Proje günlükleri (metin)
                Learning state, Flashcards    Öğrenme bilgi notları
                Opportunities, RSS/Bookmarks  Kaynak notları
                Projects (operasyonel)        Araştırma notları
                Activity, Automation          Uzun süreli hafıza
```

**Kural:** bir veri parçasının TEK birincil sahibi olur. Senkron yok, aynalı
Not sistemi yok, "forkOS notu + Vault notu" çifti yok.

| Bilgi | Sahip | forkOS'ta kalan |
|---|---|---|
| Hızlı not | Vault (`00 Inbox/`) | — |
| Günlük not | Obsidian Daily Notes | açma bağlantısı |
| Proje bilgi notu | Vault (`20 Projects/<Proje>/<Proje>.md`) | proje kimliği |
| Proje günlüğü | Vault (`…/Journal/YYYY-MM-DD.md`) | olay zaman çizelgesi |
| Öğrenme bilgi notu | Vault (`40 Learning/<Konu>.md`) | ilerleme, SRS, kartlar |
| Yer imi kaynak notu | Vault (`60 Sources/<Başlık>.md`) | URL, okuma durumu, vurgular |
| Fırsat araştırma notu | Vault (`00 Inbox/`) | fırsat alanları, CRM |
| Bilgi grafi | — (kaldırıldı) | domain grafiği (Entity/Link/Event) |

---

## 2. Vault köprüsü (tek merkez)

Vault dosya sistemi davranışı yalnızca `backend/app/integrations/obsidian/`
altında yaşar. Özellik modülleri doğrudan dosya yazmaz.

HTTP yüzeyi:

```http
GET    /api/obsidian/status                      # durum + Obsidian bağlantıları
POST   /api/obsidian/index/refresh               # indeksi tazele
GET    /api/obsidian/uri/search?q=<metin>        # Vault'ta ara URI'si
GET    /api/obsidian/items/{forkos_id}           # managed dosyayı çöz (404/409)
POST   /api/obsidian/capture                     # 00 Inbox'a yeni not (sunucu UUID)
POST   /api/obsidian/ensure                      # kayda bağlı kanonik not (idempotent)
POST   /api/projects/{id}/journal/{day}/obsidian # proje günlüğü köprüsü
POST   /api/bookmarks/{id}/source-note           # kaynak notu köprüsü
POST   /api/opportunities/{id}/research-note     # araştırma notu köprüsü
```

Kapalı yüzeyler: `/api/notes*`, `/api/note-folders*`, `/api/graph`,
`GET /api/opportunities/{id}/notes`, `POST /api/bookmarks/{id}/create-note`.

### Frontmatter sözleşmesi

Yeni notlar PHASE 2 göçünün anahtar sözlüğünü kullanır; taşınmış ve yeni
notlar tek şemayla okunur:

```yaml
forkos_id: "<uuid>"            # kimlik; dosya adı/klasör kimlik DEĞİLDİR
forkos_type: note              # note | project | learning | source | …
forkos_note_kind: personal     # personal | daily | project_journal | bookmark_note
forkos_created_at: "<iso>"
forkos_updated_at: "<iso>"
forkos_captured_from: forkOS   # yalnız hızlı yakalamada
forkos_entity_type: study_topic# kanonik notlarda (project/learning/source/…)
forkos_project_id / forkos_journal_day / forkos_source_bookmark_id
forkos_relations:              # notes_about; tip/başlık SUNUCUDA çözülür
  - relation: notes_about
    target_id: "<entity uuid>"
    target_type: opportunity
    target_title: "Backend Engineer"
```

### Yazma güvenliği

- Oluşturma `O_CREAT|O_EXCL` ile atomiktir; **sessiz üzerine yazma yoktur**.
- Çakışmada sıraya bağlı `(1)` DEĞİL, kimlikten türeyen deterministik sonek
  kullanılır: `Başlık--a1b2c3d4.md`.
- Aynı `forkos_id` iki dosyada varsa **fail-closed** (409); hiçbir yazma olmaz.
- Güncelleme `os.replace` ile atomiktir, bilinmeyen kullanıcı frontmatter
  alanlarını korur ve bayat yazmayı (mtime uyuşmazlığı) reddeder.
- API yanıtları yalnızca Vault köküne **göreli** yol taşır.
- Kullanıcı dosyayı taşısa bile not `forkos_id` ile bulunur.

---

## 3. Legacy Notlar: dondurulmuş arşiv

PHASE 2, legacy Notlar'ın Vault'ta eksiksiz temsil edildiğini kanıtladı
(13/13, 0 çakışma, 0 diverged). PHASE 3 arşivi **dondurur**:

- Fiziksel tablolar, `Entity`/`Link`/`Event` satırları ve
  `backend/data/attachments` yerinde kalır. Hiçbir migration tablo DROP etmez.
- Ürün akışları artık `INSERT/UPDATE/DELETE note`, `note_folder`,
  `note_attachment` YAPMAZ; `convert_legacy_attachments()` çağrılmaz.
- Günlük bakımdaki `attachments` adımı kaldırıldı; arşivi değiştirecek
  hiçbir zamanlanmış iş yoktur (kaynak parmak izinin sabit kalması buna bağlı).
- Legacy Notes CRUD rotaları kayıtlı DEĞİLDİR (§42/A). Eski bir istemci 404
  alır; hiçbir yazma oluşmaz. `extension` `/notes` kullanmadığı için bekleyen
  bir outbox kuyruğu riski yoktur.
- `note` / `note_folder` entity tipleri kayıt defterinde KALIR (tarihsel
  Aktivite etiketleri ve `/notes?focus=<id>` derin bağlantıları için) ama
  `searchable=False`, `linkable=False` oldukları için canlı kayıt gibi
  davranmazlar: global aramada çıkmaz, ilişki panellerinde görünmezler.
- Legacy `notes_about` / `mentions` bağları DB'de korunur ama operasyonel
  panellerde gösterilmez (`ARCHIVED_ENTITY_TYPES` süzgeci). Bağ satırları
  sırf gizlemek için DEĞİŞTİRİLMEZ.
- `note.*` olayları append-only geçmiş olarak kalır; yenisi üretilmez.
- Göç aracı ve testleri korunur (§7/§64):
  `--dry-run` / `--verify` dondurulmuş kaynağa karşı çalışmaya devam eder.

### Yedek ve geri yükleme (güvenlik dönemi)

- forkOS yedeği legacy Notlar tablolarını içermeye DEVAM eder; bunlar soğuk
  güvenlik arşividir.
- **PHASE 3'ten sonra yazılan yeni bilgi forkOS yedeğinde YOKTUR.** Sahibi
  f0rknbrain Vault'u ve onun kendi Git/senkron stratejisidir. Vault, forkOS
  yedeğine kopyalanmaz (çift sahiplik yaratmamak için).
- Legacy bir geri yükleme arşiv tablolarını geri getirebilir; bu, Notlar
  ürününü YENİDEN AKTİF ETMEZ. PHASE 3 kapsamında DB → Vault otomatik yeniden
  göçü YOKTUR; gerekirse göç CLI'si elle çalıştırılır.

### Vault Git sahipliği

Vault ayrı ve **private** bir depodur (`github.com/f0rknturkoglu/f0rknbrain`).
forkOS içinde `git add/commit/push` ÇALIŞTIRMAZ; yalnızca Markdown yazar.
Git geçmişi yönetimi uygulamaya bağlanmaz.

---

## 4. Çalışma zamanı gereksinimleri

```bash
make up-obsidian        # compose.yaml + compose.obsidian.yaml (günlük hibrit runtime)
```

| Ortam | Değişken |
|---|---|
| Container | `OBSIDIAN_VAULT_HOST_PATH` (host yolu), `OBSIDIAN_VAULT_NAME` |
| Native backend | `OBSIDIAN_VAULT_PATH`, `OBSIDIAN_VAULT_NAME` |

Makineye özel mutlak yol veya sır commit edilmez.

### Vault erişilemezse (fail-closed)

- forkOS **normal çalışır**: Today, görevler, pomodoro, fırsatlar, RSS, medya.
- Bilgi işlemleri açık hata verir (§56): `POST /obsidian/capture` →
  `503` (yapılandırılmamış/erişilemez) veya `403` (salt-okunur).
- **Legacy Notlar'a düşen bir yedek yazma yolu YOKTUR.** Kullanıcı metni
  arayüzde korunur; hata sessizce yutulmaz.
- Bilgi köprüsü sayfası ve modül köprüleri "Vault kullanılamıyor" durumunu
  gösterir; eylem düğmesi yerine açıklama sunar.

---

## 5. Kullanıcı yüzeyi

### Hızlı Yakalama (Not sekmesi)

Gövde + isteğe bağlı operasyonel ilişki. `pinned` KALDIRILDI (sabitlenecek
forkOS Not listesi kalmadı). Kaydetme `POST /obsidian/capture` ile
`00 Inbox/` altına yazılır ve "Obsidian'da aç" eylemi sunulur.

### Bilgi köprüsü sayfası (`/notes`)

Hafif köprü: kasa adı, `Obsidian'ı Aç` / `Inbox` / `Bugünün Notu` /
`Vault'ta Ara`, yönetilen dosya sayısı, çakışma ve geçersiz metadata uyarısı,
`İndeksi yenile`. Not listesi, editör, klasör, ek, canvas, backlink ve yerel
graf YOKTUR. Navigasyon etiketi `Bilgi`.

`/notes?focus=<uuid>` eski Aktivite/yer imi bağlantıları için çalışmaya devam
eder: not Vault'ta çözülürse başlık + göreli yol + `Obsidian'da Aç` gösterilir;
çözülemezse göç/arşiv mesajı verilir. Legacy DB'ye düşen bir okuma yoktur.

Komutlar: `Bilgi kasasını aç`, `Hızlı not yakala`, `Bugünün günlük notunu aç`,
`Vault'ta ara` (palet girdisi alır, URI'yi sunucu kurar).

### Proje sayfası

Operasyonel kabuk: kimlik, durum, `next_action`, yığın, kilometre taşları,
görevler, GitHub, aktivite. Bunlara ek olarak `ProjectActivityTimeline`
(salt okunur olay zaman çizelgesi; `GET /projects/{id}/journal` artık
`[{day, events}]` döner, gövde alanı yoktur) ve `ProjectJournalBridge`
(tarih seçimi + `Bugünün proje günlüğünü Obsidian'da aç`). Gövde düzenleme
Obsidian'da yapılır. Proje silindiğinde veya yeniden adlandırıldığında Vault
dosyaları **taşınmaz/silinmez** (`forkos_id` kimliktir).

### Öğrenme

İlerleme, SRS, güven, tekrar tarihleri, kaynaklar ve kartlar aynen kalır.
Konu başına TEK kanonik bilgi notu `40 Learning/<Konu>.md` (`TopicKnowledgeNote`).
PHASE 2 ile taşınmış eski notlar otomatik BİRLEŞTİRİLMEZ; `Vault'ta ara` ile
keşfedilir.

### Arama sınırı

- forkOS global arama **operasyonel** kalır (görev, proje, fırsat, yer imi,
  medya, belge, öğrenme konusu…). Legacy notlar artık sonuç dönmez.
- Bilgi araması Obsidian'ındır: `Vault'ta ara` → `obsidian://search`.
- Semantik arama / RAG bu fazda YOKTUR.

---

## 6. Geri dönüş (rollback)

- DB tabloları silinmediği için geri dönüş esas olarak **kodun geri
  alınmasıdır** (git revert). Legacy Notlar kaynağı yerinde durur.
- Vault düzenlemeleri DB'ye OTOMATİK kopyalanmaz; ters senkron yoktur.
- **Sınır:** PHASE 3'ten sonra Vault'ta oluşan YENİ notlar Vault'a aittir ve
  legacy DB'ye kendiliğinden görünmez. Geri dönüş, bu notları forkOS arayüzüne
  getirmez.
- Vault'taki PHASE 2 kopyasını geri almak isteyen operatör, yalnızca
  manifest'in kaydettiği dosyaları siler (`docs/obsidian-hybrid/migration-runbook.md` §7).

---

## 7. PHASE 4 kapısı

PHASE 3 sonunda `READY_FOR_LEGACY_SCHEMA_CLEANUP` değerlendirilir. Bu, PHASE
2'nin `READY_FOR_CUTOVER` kararından FARKLIDIR ve şunları gerektirir: hiçbir
ürün akışı legacy Notlar'a yazmıyor/okumuyor, proje ve öğrenme modülleri not
servisine bağlı değil, bilgi grafi arayüzü kaldırıldı, Vault çalışma zamanı
sağlıklı, göç doğrulaması temiz, test ve gerçek smoke testi kabul edilebilir.

**PHASE 4 bu fazda YAPILMAZ.** Fiziksel şema/arşiv temizliği gerçek kullanım
sonrasına bırakılır.
