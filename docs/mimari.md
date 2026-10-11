# forkOS yaşayan mimarisi

Bu belge forkOS'un güncel teknik sözleşmesini anlatır. Tamamlanmış fazların değişiklik günlüğü değildir; yeni bir modül veya entegrasyon geliştirirken başvurulacak yaşayan kaynaktır. Bağlayıcı agent kuralları `AGENTS.md` dosyasındadır.

## 1. Çalışma modeli

forkOS tek makinede ve tek kullanıcı için çalışır:

```text
Chrome extension ─┐
React/Vite PWA ───┼──> FastAPI ───> PostgreSQL 16
                  │        │
                  │        ├──> kalıcı kaynak kuyruğu ──> SourceAdapter'lar
                  │        └──> f0rknbrain Obsidian Vault (bind mount; bilgi)
                  │
                  └──> isteğe bağlı APScheduler worker aynı kuyruğu tüketir
```

| Servis | Görev | Varsayılan adres |
| --- | --- | --- |
| `web` | React/Vite arayüz ve PWA | `127.0.0.1:5173` |
| `api` | FastAPI, iş kuralları ve manuel yenileme | `127.0.0.1:8787` |
| `db` | PostgreSQL 16 | `127.0.0.1:5433` |
| `worker` | Zamanlanmış kaynak ve bakım işleri | profil kapalı |

Manuel genel yenileme worker'a bağımlı değildir. API bir batch oluşturur ve aynı kalıcı kaynak kuyruğunu arka planda tüketir. Worker açılırsa yarım kalan/due işleri aynı sözleşmeyle devralır.

## 2. Entity, link ve event omurgası

### Entity

`backend/app/core/models.py::Entity`, bütün aranabilir ve linklenebilir kayıtların kimliğidir:

- `id`: sistem genelinde UUID
- `type`: registry'deki entity tipi
- `title`: ortak görünen başlık
- `search_text`: FTS/trigram arama içeriği
- `archived_at`: ortak yaşam döngüsü

Bir modülün ana kaydı `EntityBacked` olur ve PK'si aynı zamanda `entity.id` alanına FK'dır. Yazmalar `backend/app/core/entity.py` içindeki `create_entity`, `touch_entity`, `archive_entity` ve `delete_entity` helper'larından geçer.

### Link

`link`, iki entity arasında yönlü ilişki kurar: `from_id → to_id`. İlişki sözlüğünün tek kaynağı `backend/app/core/links.py::RELATIONS` değeridir. Frontend ilişkileri `RelatedPanel` ve `BacklinksPanel` üzerinden gösterir.

Yeni bir ilişki eklerken:

1. İleri/geri Türkçe etiket çiftini `RELATIONS` içine ekle.
2. Bağı aynı transaction içinde yaz.
3. Anlamlı event üret.
4. Frontend'de `invalidateAfter("link.write")` kullan.

### Event

`event` append-only aksiyon günlüğüdür. Domain tabloları güncel durumu, event ise nasıl o duruma gelindiğini taşır. Event satırları güncellenmez veya silinmez.

```python
await log_event(
    session,
    verb="todo.completed",
    entity_id=todo.id,
    entity_type="todo",
    payload={"title": "Runbook'u güncelle", "was_overdue": False},
)
```

Activity, ritim/ısı haritası, review özetleri ve bazı proje zaman akışları bu günlükten türetilir.

## 3. Registry'ler

### Backend

`backend/app/modules/__init__.py` iki merkezi sözleşmeyi taşır:

- `MODULES`: router, event verb'leri ve deadline provider'lar
- `EntityTypeSpec`: entity tipi → etiket, çoğul etiket, ikon ve frontend rotası

`main.py`, arama, deadline toplama ve registry uçları bu listeden beslenir. Yeni modül için özel `main.py` bağlantısı yazılmaz.

`note` ve `note_folder` tipleri registry'de tarihsel olarak kalır (eski Aktivite etiketleri ve `/notes?focus=<uuid>` derin bağlantıları için) ama `searchable=False`, `linkable=False` oldukları için canlı kayıt gibi davranmazlar: global aramada çıkmaz, ilişki panellerinde görünmezler.

### Frontend

`frontend/src/modules/index.ts`, her frontend modülünü bir kez import eder. Modülün `index.ts` dosyası `registerModule(...)` ile şunları kaydeder:

- route'lar
- sidebar hiyerarşisi (ürün alanları: bkz. `docs/product-navigation.md`)
- komut paleti eylemleri
- Today widget'ları

Entity linkleri ve global arama hedefleri backend registry'sinden gelen veriyi `frontend/src/core/entityRegistry.ts` içindeki `entityRoute()` ve `typeLabel()` üzerinden çözer.

## 4. Modül anatomisi

### Backend

```text
backend/app/modules/<name>/
├── __init__.py     MODULE = ModuleSpec(...)
├── models.py       EntityBacked domain modelleri
├── schemas.py      Pydantic sözleşmeleri
├── service.py      Transaction ve iş kuralları
└── router.py       İnce HTTP katmanı
```

Router transaction/iş mantığını tekrar etmez. Entity helper'ları, link ve event yazımları service katmanında aynı transaction sınırında yürür.

### Frontend

```text
frontend/src/modules/<name>/
├── index.ts        registerModule(...)
├── <Name>Page.tsx  çalışma alanı kompozisyonu
├── bileşenler
└── *.test.ts(x)
```

Sayfa, uygulama kabuğunu veya ikinci bir navigasyonu yeniden üretmez. Ortak yüzeyler `frontend/src/core/shell`, form ve durum bileşenleri `frontend/src/core/ui.tsx` üzerinden gelir.

## 5. Modüller arası sözleşmeler

### Mutation invalidation

`frontend/src/core/invalidation.ts::AFTER`, bir domain yazımının hangi query key'lerini tazeleyeceğinin tek kaynağıdır:

```ts
invalidateAfter("todo.write", "plan.write");
```

Yeni mutation için önce anlamlı event adını/invalidasyon girdisini ekle; bileşenlere dağılmış ham query-key listeleri yazma.

### Görev oluşturma

Backend'de görev oluşturmanın tek sınırı todo service'tir. Opportunity, learning ve project gibi bağlamlar bu service'e delege eder, sonra kendi linkini aynı transaction içinde kurar.

Frontend'de `frontend/src/core/tasks.ts`, bütün manuel görev girişlerinin ortak intent katmanıdır. `plan_day` “o gün yap” anlamına gelir; `due_at` teslim tarihidir ve birbirine dönüştürülmez.

### Evrensel yakalama

`frontend/src/core/capture.ts`, görev/not/bağlantı yakalama intent'lerini tek noktada toplar; not dalı Vault'a yazar (`captureVaultNote` → `POST /api/obsidian/capture`) ve invalidation anahtarı `obsidian.write`'tır. Extension yazımları `client_uuid` ile idempotenttir. Inbox ve Bookmark aynı domain tablosunu kullanır; `collection` kayıt durumunu belirler.

### Son tarihler

Son tarih üreten modüller `ModuleSpec.deadline_provider` sağlar. `backend/app/core/deadlines.py` sağlayıcıları toplar. SQL union view veya modüller arası elle join zinciri kullanılmaz.

### Today

Today bir veri sahibi değil, orkestrasyon yüzeyidir. Modüller `todayWidgets` ile benzersiz ve kalıcı widget ID'leri kaydeder. Kullanıcının sıra/görünürlük tercihleri bu ID'lere bağlıdır.

Agenda; görev, plan, takvim, fırsat, öğrenme ve medya kayıtlarını tek günlük read-model içinde birleştirir. Bir widget hatası diğer widget'ları engellememelidir.

### Pomodoro

Pomodoro sunucu otoritelidir; sayfadan bağımsız global yüzey yalnızca aktif session'ı yansıtır. Context bir entity'ye bağlanabilir. Tamamlanan session domain'e özgü tüketim/çalışma event'lerine köprü olabilir.

### Bilgi sahipliği sınırı (PHASE 3)

forkOS **yürütmenin**, ayrı ve private `f0rknbrain` Obsidian Vault'u **bilginin** sahibidir. İnsan bilgisi (serbest notlar, günlükler, proje bilgi notları ve günlükleri, öğrenme bilgi notları, kaynak notları) Vault'ta Markdown olarak yaşar; forkOS yalnızca yürütme/operasyonel durumu (görev, plan, ilerleme, SRS, CRM, olay geçmişi) tutar. Bir veri parçasının **tek** birincil sahibi olur: aynalı Not sistemi ve çift yazma yoktur.

Vault dosya sistemi davranışı yalnızca `backend/app/integrations/obsidian/` altında yaşar; özellik modülleri doğrudan dosya yazmaz. HTTP köprüsü:

```http
GET    /api/obsidian/status                      # durum + Obsidian bağlantıları
POST   /api/obsidian/index/refresh               # indeksi tazele
GET    /api/obsidian/uri/search?q=<metin>         # Vault'ta ara URI'si
GET    /api/obsidian/items/{forkos_id}            # managed dosyayı çöz (404/409)
POST   /api/obsidian/capture                      # 00 Inbox'a yeni not
POST   /api/obsidian/ensure                       # kayda bağlı kanonik not
POST   /api/projects/{id}/journal/{day}/obsidian   # proje günlüğü köprüsü
POST   /api/bookmarks/{id}/source-note             # kaynak notu köprüsü
POST   /api/opportunities/{id}/research-note       # araştırma notu köprüsü
```

Kapalı yüzeyler: `/api/notes*`, `/api/note-folders*`, `/api/graph` ve bağımsız `/notes` UI. Obsidian köprüsü ve ajan bağlamı Ayarlar → Agent & Bilgi ve retained modüllerde devam eder. [V1 kapsamı](architecture/v1-scope-consolidation.md).

Legacy Notlar tabloları, blokları ve `note.*` olayları **dondurulmuş arşiv** olarak yerinde kalır (hiçbir migration tablo DROP etmez): hiçbir ürün akışı yazmaz, global aramada ve ilişki panellerinde görünmez, günlük bakımla budanmaz. Vault erişilemezse bilgi işlemleri **fail-closed**'dur (`503`/`403`) ve legacy Notlar'a düşen bir yedek yazma yolu yoktur. Domain grafiği (Entity/Link/Event, `RelatedPanel`, `BacklinksPanel`) yürütme omurgasıdır ve aynen korunur. Ayrıntı: `docs/obsidian-hybrid/phase3-cutover.md`.

## 6. Kaynak ve scraper mimarisi

Her yeni ağ kaynağı `backend/app/sources/base.py` içindeki `SourceAdapter` sözleşmesini uygular. Öncelik sırası:

1. Resmî API veya JSON-LD/schema.org
2. Kararlı HTML seçiciler
3. Kontrollü fallback ayrıştırma

### Kaynak koşusu sonuçları

Her çalıştırma `source_run` üretir ve sonucu dört durumdan BİRİDİR:

| Durum | `source_run.status` | Anlamı |
|---|---|---|
| **complete** | `ok` | Kaynağın hedeflenen kapsamı tamamen tarandı. Yalnız bu sonuç kapanma taramasını (sweep) tetikler. |
| **partial** | `partial` | Bazı geçerli kayıtlar alındı ama sayfalama, yardımcı feed/PDF, timeout veya parser sorunu kapsamı daralttı. Kayıtlar işlenir, sweep YAPILMAZ. |
| **empty** | `empty` | Koşu teknik olarak tamamlandı, hiç kayıt yok. |
| **error** | `error` | Koşu güvenilir sonuç üretemedi (ağ, TLS, timeout, parser, config, ingest). |

Kurallar:

- Ağ/TLS/timeout/parser/config/ingest hataları **boş listeye çevrilmez**; koşum `error` olur.
- `partial` bir alarm değildir: kaynak çalışıyor, kapsamı eksik. Detayı `source_run.error` taşır.
- Kapsam koruması: yeni koşu, önceki **tam** koşunun gördüğü kayıt sayısının yarısından azını görürse koşum `partial` işaretlenir ve sweep yapılmaz (`items_seen` kolonu).
- `item_found` = yeni oluşturulan kayıt, `items_seen` = kaynağın gördüğü kayıt.
- Üst üste 3 `empty` → "kaynak duraksadı", üst üste 3 `error` → "kaynak erişilemiyor" bildirimi. Aynı seride tekrar bildirim üretilmez.
- Ardışık 5 hata devre kesiciyi açar; kaynak cooldown boyunca ağa hiç çıkmadan atlanır.

### Kaynak sınıfları ve manuel yenileme

| Sınıf | Kimler | Davranış |
|---|---|---|
| `critical` | Resmî kaynaklar (ÖSYM, YLSY, YÖK) ve hızlı ATS panoları | Kuyruğun BAŞINDA; uygulama/worker açılışında bounded catch-up |
| `normal` | Diğer iş panoları | Genel yenilemede kritiklerden sonra |
| `slow_optin` | EURES, LinkedIn, Memurlar | Periyodik turda **ASLA** koşmaz; yalnızca kullanıcı açıkça seçince |

Manuel yenileme kapsamları (`POST /api/system/refresh` gövdesi `{"scope": ...}`):

- `critical` — yalnız resmî/hızlı kaynaklar (medya hariç)
- `standard` (varsayılan) — opt-in kaynaklar hariç tümü + medya
- `full` — katalogun tamamı, opt-in dahil

Aynı yenileme çift başlatılmaz; süreci ölmüş bir `running` kaydı bayat sayılır ve kilit açılır.

`backend/app/core/source_sync.py` kalıcı batch/kuyruk sahipliğini yönetir. Uzun senkron:

- API request ömrüne güvenmez,
- yeniden başlatmadan sonra devam edebilir,
- aynı kaynağın eşzamanlı sahiplenilmesini engeller,
- ilerlemeyi tamamlanan/toplam kaynak olarak raporlar,
- LinkedIn gibi opt-in kaynakları açık seçim olmadan çalıştırmaz.

**LinkedIn gizlilik/opt-in davranışı.** LinkedIn `slow_optin` sınıfındadır ve genel yenilemeye girmez. Proxy'siz (direct) erişim VARSAYILAN KAPALIDIR ve yalnızca `FORKJOB_LINKEDIN_ALLOW_DIRECT` açık bir değerle (`1/true/yes/on`) ayarlanırsa etkinleşir; `0/false/no` ve tanınmayan değerler kapalı sayılır (`env_flag`). Proxy listesi `FORKJOB_LINKEDIN_PROXIES_FILE` dosyasından okunur ve proxy kimlik bilgileri hiçbir zaman loglanmaz, arayüzde gösterilmez. Eski `LINKEDIN_*` ortam adları geriye uyumluluk için kabul edilir.

**Kullanıcı verisi.** LinkedIn arama profilleri ve kullanıcı RSS listesi `data/*.yaml` ŞABLONLARINA değil, git tarafından yok sayılan `<ad>.yaml.user` dosyalarına yazılır; şablonlar yalnızca örnektir ve kişisel veri taşımaz.

Başarılı HTTP yanıtlarını sınırsız biçimde diske yığma. Cache'in okuma yolu, boyut/yaş sınırı ve pruning davranışı tanımlı olmalıdır.

## 7. Arama

PostgreSQL'te Türkçe stemmer varsayılmaz. Arama:

- `simple` text search config,
- `immutable_unaccent()`,
- `pg_trgm`,
- entity `title + search_text`

bileşimiyle çalışır. Yeni aranabilir domain kaydı entity başlığı ve arama metnini create/update sırasında güncel tutar.

forkOS global araması **operasyoneldir** (görev, proje, fırsat, yer imi, medya, belge, öğrenme konusu…). Legacy notlar `searchable=False` olduğu için sonuç dönmez; bilgi araması Obsidian'ındır (`Vault'ta ara` → `obsidian://search`). Semantik arama/RAG bu fazda yoktur.

## 8. Tasarım sistemi

Tasarım tokenları `frontend/src/index.css` ve `frontend/tailwind.config.js` dosyalarındadır. Ortak primitive'ler `frontend/src/core/ui.tsx` içindedir.

- Semantik renkler: `accent`, `ok`, `warn`, `danger`
- Kimlik renkleri: `kind-*`, `src-*`, `feed-*`
- Grafik renkleri: `chart-1..8`
- Z-index: adlandırılmış katman tokenları
- Formlar: `Input`, `Select`, `Checkbox`, `Range`, `NumberInput`, `FileInput`, `Chip`

Loading için skeleton, veri yokluğu için açıklayıcı empty state, hata için erişilebilir geri bildirim kullan. Modal/popover focus yönetimi, Escape ve focus restore sözleşmesini korur.

## 9. Veri, gizlilik ve yedek

- PostgreSQL kalıcı verisi `forkos_pgdata` named volume'ündedir.
- Belge, attachment, medya cache'i, OAuth token'ları ve kişisel config Git'e girmez.
- Secret setting anahtarlarının tek kaynağı `backend/app/modules/system/secrets.py::SECRET_SETTING_KEYS` listesidir.
- Export ve taşınabilir yedek secret satırlarını içermez.
- Normal restore merge/idempotent'tir; mevcut veriyi silmez.
- Gerçek disaster restore uygulama dışı CLI sınırıdır, önce doğrulanmış safety dump alır ve transaction tamamlanmadan commit etmez.
- Bilgi (PHASE 3'ten sonra yazılan notlar, günlükler, kaynak notları) f0rknbrain Vault'unda yaşar ve **forkOS yedeğine girmez**; yedeklemesi Vault'un kendi Git/senkron stratejisine aittir. forkOS yedeği legacy Notlar tablolarını ve kullanılan ekleri soğuk güvenlik arşivi olarak taşımaya devam eder; bu, Notlar ürününü yeniden etkinleştirmez ve DB → Vault otomatik yeniden göçü yoktur.
- Vault ayrı ve private bir depodur: forkOS içinde `git add/commit/push` çalıştırmaz, yalnızca Markdown yazar.
- Çalışma zamanı: Vault host yolu `OBSIDIAN_VAULT_HOST_PATH` (container) veya `OBSIDIAN_VAULT_PATH` (native) ile verilir; günlük hibrit runtime `make up-obsidian`. Vault erişilemezse uygulama normal çalışır ama bilgi işlemleri `503`/`403` ile fail-closed olur.

Local-only, “hiç ağ isteği yok” anlamına gelmez. RSS, ilan, katalog ve açıkça bağlanan Google/GitHub entegrasyonları dış kaynaklardan veri çeker; kişisel veritabanını buluta yüklemez. Yeni paket veya ağ davranışında `.agents/skills/local-privacy-audit/SKILL.md` uygulanır.

## 10. Migration ve API sözleşmesi

Migration'lar elle yazılır; her SQL komutu ayrı `op.execute()` çağrısıdır. Yeni revision önce `alembic heads` çıktısındaki gerçek head'e bağlanır. Ayrıntı: `backend/alembic/README.md`.

FastAPI/Pydantic sözleşmesi değişirse:

```bash
cd backend
python scripts/export_openapi.py
cd ../frontend
npm run api:generate
npm run api:check
```

Generated TypeScript dosyası elle düzenlenmez.

## 11. Doğrulama

```bash
# İzole backend + migration testleri
make test CO="docker compose"

# Backend lint + frontend test/build + extension
make verify CO="docker compose"
```

Özellikle şu guardrail'ler mimari drift'i durdurur:

- entity-backed tablo ve tek migration head
- append-only event davranışı
- entity registry route/label sahipliği
- merkezi mutation invalidation
- design token ve UI primitive kullanımı
- frontend tarafından tüketilmeyen endpoint sınırı
- test DB'nin kişisel DB'den izolasyonu

## 12. Hafif çalışma ve kaynak felsefesi

forkOS tek kullanıcılı, yerel öncelikli (local-first) bir sistemdir. Sistem kaynakları (CPU, bellek, SSD yazma döngüsü ve disk alanı) kullanıcı çalışmadığı anlarda sakin kalacak şekilde tasarlanmıştır.

### 12.1 Runtime modları

- **Günlük (stable) runtime (`compose.yaml`):** Normal kullanım ortamı. Üretim derlemesi nginx ile sunulur, FastAPI reload'suz çalışır. Vite dosya izleme polling'i, HMR ve container içine bind-mount kaynak kod yoktur; SSD'ye sürekli gereksiz yazma yapılmaz.
- **Geliştirme runtime'ı (`compose.dev.yaml` overlay):** Yalnızca kod geliştirirken kullanılır. Vite dev server, HMR, uvicorn `--reload` ve bind-mount kaynak kod içerir.

### 12.2 Otomasyon profilleri ve modül ayrımı

- **Görünürlük vs. Otomasyon:** Ayarlar → Modüller ekranında bir modülü gizlemek arayüz rotasını ve Home bileşenlerini kapatır; arka plan ağ trafiğini kesmez. Arka plan trafiği ayrı olarak `automation.<domain>.enabled` (veya `rss.interval_minutes = 0`) ile yönetilir.
- **Çalışma profilleri:**
  - `Manual`: Dış ağ otomasyonu kapalıdır; yalnızca yerel hafif bakım ve açık manuel yenilemeler çalışır.
  - `Balanced` (varsayılan): RSS 60 dk, fırsat 30 dk, takvim 60 dk, GitHub 3 sa, medya 24 sa.
  - `Active`: Daha sık turlar (RSS 30 dk, fırsat 15 dk, takvim 30 dk).
- **Öncelik kuralı:** Modül otomasyonu kapalıysa profil ne olursa olsun çalışmaz; profiller yalnızca açık modüllerin sıklığını belirler.
- **Opt-in kaynaklar:** LinkedIn ve EURES gibi `slow_optin` kaynaklar otomatik profillerle asla kendiliğinden açılmaz; yalnızca açık manuel seçimle koşar.
- **Açılış telafisi:** Worker yeniden başlatıldığında ağ patlaması oluşmaz; tazelik kontrolü (RSS feed yaşı, son takvim/GitHub turu, son 2 saatlik kritik fırsat kontrolü) ile yakın zamanda güncellenmiş kaynaklar atlanır.

### 12.3 Depolama sınırları ve saklama (retention)

Disk büyümesi belirli sınırlarla (bounded) tutulur:

| Alan | Konum | Bounded / Temizleme |
| --- | --- | --- |
| **PostgreSQL** | `forkos_pgdata` | Operasyonel satırlar günlük hafif bakımla budanır |
| **Not ekleri (legacy arşiv)** | `backend/data/attachments/` | İçerik adresli (sha256) binary; PHASE 3'ten sonra yeni ek yazılmaz, bakım dokunmaz (dondurulmuş kaynak parmak izi) |
| **Belgeler** | `backend/data/documents/` | Kullanıcı tarafından yönetilen yerel belgeler |
| **Medya görselleri** | `backend/data/media/` | Emekli arşiv; otomatik budanmaz |
| **Scraper önbelleği** | `backend/data/cache/` | Yeniden üretilebilir; HTTP önbellek sınırları ile tutulur |
| **Yedekler** | `backend/backups/` | Sıkıştırılmış JSON ve pg_dump; kullanıcı yönetir |

Operasyonel veri budama politikası:
- `source_run`: `ok`/`empty` 30 gün, hatalı koşular 90 gün, kaynak başına **son 20 koşu daima korunur**.
- `source_sync_batch`: Terminal batch'ler 60 gün; aktif kuyruk kayıtları asla silinmez.
- `notification`: Okunmuş bildirimler 90 gün (önem derecesi ≥ 3 olanlar 180 gün); okunmamışlar asla silinmez.
- **Kişisel veri dokunulmazlığı:** legacy Notlar arşivi, görev, proje, medya, finans, fırsat ve `event` günlüğü asla otomatik budanmaz. PHASE 3'ten sonra yazılan bilgi zaten forkOS veritabanında değil, f0rknbrain Vault'undadır.

### 12.4 Hafif bakım (maintenance)

Worker açıkken her gece 04:00'te; worker kapalıyken API açılışında arka planda günde en fazla bir kez koşar (`maintenance.last_run` gün kapısı). Ağ çağrısı yapmaz; operasyonel satırları budar, süresi geçmiş RSS öğelerini temizler ve medya önbelleğini bütçeye çeker. Legacy ek dönüşümü (`convert_legacy_attachments`) ve ek budama adımı PHASE 3'te kaldırıldı: `data/attachments` dondurulmuş arşivdir ve bakım ona dokunmaz.

### 12.5 Kullanıcı odaklı yedekleme ve dirty check

- **Kapsam:** Entity omurgası, bağlantılar, olay günlüğü, modül kayıtları ve dondurulmuş legacy Notlar arşivi (tablolar + kullanılan ekler). PHASE 3'ten sonra yazılan bilgi f0rknbrain Vault'unda yaşar ve bu yedeğe girmez.
- **Kapsam dışı:** Rebuildable operasyonel durumlar (`source_run`, `source_sync_batch`) ve hassas `oauth_token` kayıtları.
- **Gece yedeği dirty check:** Makine durumları (kalp atışı, bakım temizliği, kaynak sağlığı) değişiklik sayılmaz. Anlamlı kullanıcı mutasyonu yoksa gece yedeği gereksiz yere disk tüketmez. Manuel "Şimdi yedekle" her zaman tam yedek üretir.

### 12.6 Tarayıcı ve UI kaynak optimizasyonu

- TanStack Query: `refetchOnWindowFocus: false` ve `refetchIntervalInBackground: false` ile arka plan sekmelerinde ve pencere odak değişimlerinde istek fırtınası engellenir.
- Paylaşılan runtime sorguları: Sistem istatistikleri, kaynak sağlığı ve yedek durumu tek anahtar üzerinden sorgulanır; bileşenler arası mükerrer polling yapılmaz.
- Home paneli (`today` modülü, görünen ad Home): Gizli widget'lar tamamen unmount edilir ve ağ isteği çıkarmaz; analog saat saniyelik render yerine dakika sınırına kilitlidir.

## Hedefler ve Strateji V1

Kanonik sahip mevcut `goal` modülüdür; plan/pillar/Goal/KR graph'ı, Decimal
ölçümler, deterministik rota ve H5 anlamlı event tabanlı uyum içerir.
Review.stats immutable sürümlü snapshot taşır. Hermes tek salt okunan strategy
aracıyla gerçekleri okur; H6 isteğe bağlı stratejik dikkat aynı teslim motorunu
kullanır. Ayrıntılar: [Hedefler ve Strateji](goals-strategy.md).
