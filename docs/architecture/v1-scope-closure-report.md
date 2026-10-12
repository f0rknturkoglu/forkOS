# V1 Scope Closure — doğrulama ve kalan işler

> Tarihsel doğrulama raporu. Bu belgedeki test sayıları ait olduğu commit içindir; güncel gate için [V1 final kapanış](v1-final-closure.md).

Başlangıç: `main`, `2c55ff5`, temiz çalışma ağacı. Kapsam kararı:
[V1 ürün sözleşmesi](v1-product-scope.md). Önceki
[konsolidasyon raporu](v1-scope-consolidation.md) tarihsel baseline'dır.

## A. Kapsam uyum matrisi

| Yetenek | Beklenen ve mevcut davranış | Kanıt | Durum |
|---|---|---|---|
| Home / Today, Inbox / Capture, Todo / Plan | Aktif kayıt, navigasyon ve yürütme | Backend API/Today/Todo, frontend registry testleri | Korundu |
| Projects | Aktif proje, bağlar ve tarihsel timeline | Project regresyonları; Pomodoro önceki/yeni bağlam audit'i | Korundu |
| Goals / Strategy | Aktif hedef ve strateji sağlayıcıları | Goal/strategy testleri ve MCP runtime sözleşmesi | Korundu |
| Career / Academia, forkjob_core / career-ops | Aktif ilan/akademi edinimi ve kariyer dosyaları | Opportunity, career-ops, local attachment testleri | Korundu |
| Learning | Alan/konu/kaynak ve güncel odak emeği | Learning testleri ve resource-context CRUD regresyonu | Düzeltildi |
| Flashcards / SRS | Bağımsız kayıt, API ve navigasyon | V1 registry/API ve Flashcard testleri | Korundu |
| Calendar | Google Calendar aynası ve doğrudan Todo oluşturma | Calendar-to-Todo entegrasyon ve OAuth fixture testleri | Korundu; gerçek hesap testi yok |
| Pomodoro | Timer, manuel geçmiş, edit/delete ve tutarlı canlı metrikler | V1 manual CRUD, timer, timezone, review/istatistik/harita testleri | Düzeltildi |
| RSS / Feed | Bağımsız aktif ürün ve kaynak işleri | RSS/API, frontend ve scheduler kayıt testleri | Korundu |
| Bookmarks | Bağımsız aktif ürün | Bookmark/API, extension ve frontend testleri | Korundu |
| Activity / Reviews | İşlem geçmişi korunur; canlı effort oturum tablosundan gelir | Contributions/Review/Statistics/Review intelligence testleri | Düzeltildi |
| Diagnostics, local backup / restore | Kullanıcıya açık tanılama ve yerel yedek | System/backup/restore ve frontend registry testleri | Korundu |
| Media / Finance | Aktif UI/API/job yok; tarihsel metadata ve veriler durur | Boş router, kapalı searchable/linkable, scheduler ve migration testleri | Emekli |
| Standalone Documents | Bağımsız UI ve Drive sync yok; kariyer upload/list/download devam eder | Runtime API kapsamı ve attachment regresyonları | Emekli ürün; dosya altyapısı korundu |
| Standalone Knowledge UI | İkinci bilgi uygulaması yok; eski focus bağlantısı Vault'a çözülür | LegacyVaultLink testleri ve gerçek tarayıcı fallback akışı | Emekli ürün; uyumluluk düzeltildi |
| Google Drive | Aktif endpoint, OAuth talebi, ayar ve polling yok | Runtime routes, settings, OAuth ve worker testleri | Emekli |
| Obsidian, agent/MCP/memory/retrieval, Entity/Link/Event, scheduler, GitHub | Meşru ortak altyapı devam eder | Runtime MCP ailesi 37 araç; registry, agent ve integration testleri | Korundu |

## B. Düzeltilen kusurlar

| Kusur / kök neden | Değişiklik ve ilgili dosyalar | Kanıt / regresyon sınırı |
|---|---|---|
| P1: Pomodoro edit/delete/backdate sonrası Event üzerinden hesaplanan effort güncel kayıttan ayrılıyordu | `review/service.py`, `statistics/service.py`, `core/contributions.py`, `review_intelligence/review.py`: ended focus oturumları, yerel `started_at` günü; Event yalnız audit | Backdate, gece yarısı, süre/gün/kind değişimi, silme, interrupted timer; kaydedilmiş Review snapshot değişmez |
| P1: Eski note focus URL'si ayarlara yönlenirken kimlik kayboluyordu | `LegacyVaultLink.tsx`, `App.tsx`, note registry ve agent context: backend Vault lookup ve mevcut URI helper; açık hata/retry | Geçerli/bozuk/eksik/unavailable/conflict; otomatik açma bir kez; no-focus ayarlara dönüş; bağımsız editor yok |
| P1: Extension kaldırılmış `/notes` ucuna yazıyordu | `extension/outbox.js`, Obsidian models/router/service: canonical `/obsidian/capture`, stable `client_uuid`, payload fingerprint ve transaction advisory lock | Retry tek dosya; farklı içerik/kimlik çakışması 409; 5xx/network kuyrukta, 4xx görünür başarısız; içerik/tag/metadata/ilişki korunur |
| P2: Emekli Media kuyrukları queued/running kalabiliyordu | `0079_retire_media_batches.py`, `core/source_sync.py`, `core/retention.py`: dürüst terminal sonuç ve retirement audit; yeni emekli iş reddedilir | Aynı migration SQL'i iki kez; opportunity kuyruğu etkilenmez, geçmiş batch/run korunur |
| P2: Ayarlar/tanılama/README güncel ürün sahipliğini yanlış anlatıyordu | README, mimari, navigasyon, setup checklist, system status ve BrainAgentSection | Gereksiz Bilgi alanı butonu kaldırıldı; Calendar adı ve Obsidian ayarları; kanonik kapsam belgesi |
| Ek: Kaynak entity'sine bağlı Pomodoro Learning alan/konu toplamından düşüyordu | Learning/review service: resource bağlamı ait olduğu topic'e çözülür, tek kez sayılır | Kaynak→başka konu bağlam değişimi ve silme tüm canlı Learning/Review toplamlarını günceller |
| Ek: Mutation sonrası bazı analitik cache'ler eski kalıyordu | `core/invalidation.ts`: Pomodoro→statistics/study-tree/study-areas; ölü media/finance mutation anahtarları çıkarıldı | Invalidation/V1 scope testleri; kariyer `document.write` korunur |
| Kalite: Lint ve biçim borcu | Güvenli Ruff import/unused düzeltmeleri; mevcut exception semantics korunarak suppress/raise-from; Prettier | Kurallar kapatılmadı, full regresyon ve format kontrolü |

## C. İkinci tarama ve legacy referans defteri

Başlangıç taramasından sonra imports, registries, routes, scheduler, MCP, search,
notifications, settings, diagnostics, extension, backup ve güncel dokümanlar tekrar incelendi.
Metin eşleşmesi tek başına aktif runtime bağımlılığı sayılmadı.

| Sınıf | Referans / gerekçe |
|---|---|
| A — aktif kusur, düzeltildi | Event tabanlı canlı Pomodoro effort; focus kaybeden redirect; extension `/notes`; emekli Media enqueue; eksik Learning resource effort |
| B — ölü kod, kaldırıldı | Media/Finance mutation anahtarları, media source cache anahtarları, kullanılmayan `MediaLink`, BrainAgentSection geri dönen butonu |
| C — eski doküman, düzeltildi | Drive backup yorumları, eski product navigation, Media worker/refresh anlatımı, eski MCP araç sayısı, emekli usages endpoint açıklaması |
| D — tarihsel uyumluluk | Media/Finance/Note model importları ve boş ModuleSpec router'ları: metadata, restore ve okunabilir Event tipleri için; searchable/linkable false |
| D — tarihsel uyumluluk | `media.*`, `expense.*`, `income.*`, `note.*`, `backup.drive_*` olay sözlüğü; eski bildirimler `/activity`; arşiv tüketimi `medya (arşiv)` |
| D — tarihsel uyumluluk | `/notes?focus=...` ve `/knowledge?focus=...`; diğer emekli rotalar açık navigasyon sözleşmesine göre yönlenir |
| D/E — kariyer altyapısı | Document DB/API içinde `drive_file_id`, `drive_modified_at` ve eski usage şemaları: tarihsel veri şekli korunur; aktif Drive sync değildir |
| E — ortak altyapı | Obsidian Vault/retrieval/semantic memory, yerel documents/attachments, GitHub, Google Calendar, agent action audit |
| F — zararsız adlandırma | `matchMedia`, `HardDrive` ikonları, proactivity `immediate_*`; emekli Media/Drive ürün çağrısı değildir |

## D. Veri, migration ve sahiplik

- Media, Finance, legacy Notes ve Document tabloları/dosyaları silinmedi. Kişisel
  Vault, DB, yedek, attachment ve credential değiştirilmedi.
- `0078_pomodoro_source` populated isolated DB üzerinde downgrade/upgrade ile
  doğrulandı: event kanıtı olan manual kayıt sınıflanır; timer ve süreler korunur.
- Yeni head `0079_retire_media_batches`: running Media run'larını abandoned,
  queued/running Media batch'lerini completed_with_errors yapar; gerekçeli yeni
  Event ekler. Eski Event'i UPDATE/DELETE etmez; sahte başarı sayısı üretmez.
  Downgrade geçmiş işlemi geri çevirmez veya işleri yeniden başlatmaz.
- SQL başına ayrı `op.execute`; migration iki kez uygulanınca ikinci retirement
  Event oluşmaz. Terminal geçmiş ve retention'da Media batch/run korunur.
- Migration yalnız geçici, tmpfs PostgreSQL 16 test DB'lerine uygulandı.
  **Kişisel DB'nin migrate edildiği iddia edilmez**; normal proje migrate/startup
  akışında head'e alınmalıdır.
- Canlı effort güncel `pomodoro_session`; tarihsel işlem zamanı Event'tir.
  Oturum gece yarısını aşsa da başlangıç gününe aittir. Interrupted kayıtların
  gerçekten çalışılan süresi sayılır; break/aktif kayıtlar focus değildir.
  Timer/manual source ve pause/interruption bilgileri edit sırasında korunur.
- Kaydedilmiş Review snapshot'ları değiştirilmedi. Project timeline ve agent
  action delta audit'tir; canlı Review önizlemesi ve dönem effort'u güncel kayıttır.
- Google OAuth yeni bağlantıda yalnız Calendar izni ister. Eski hesap Drive
  grant'i otomatik revoke edilmez; local disconnect token'i yerelde kaldırır.
  Gerçek Google hesabında reconnect/revoke/remote mutation yapılmadı.

## E. Doğrulama

Python 3.12.15, kilitli backend dev bağımlılıkları, OrbStack PostgreSQL 16.
`DATABASE_URL` yalnız `127.0.0.1:55432/forkos_test`; UI ayrı `forkos_ui_test` ve
geçici fixture Vault kullandı. Host Python 3.9 ile API export çalışmaz;
kontroller uygun Python 3.12 ortamıyla tekrar çalıştırıldı.

| Komut / kontrol | Sonuç |
|---|---|
| Backend `pytest -q -rs` | 2613 passed, 36 skipped; 192.01 saniye |
| Son Learning/Review/agent kapsam testi | 96 passed |
| Frontend `npm test` | 145 dosya, 985 test passed |
| Frontend `npm run build` | TypeScript ve üretim build başarılı; 65 asset |
| Extension `node --test extension/tests/*.test.mjs` | 19 passed |
| `npm run api:check` | Runtime OpenAPI güncel; generated TS senkron |
| Endpoint coverage | 2 referanssız uç, mevcut eşik 3; recover ve career-ops doctor |
| Dead export kontrolü | 10, mevcut eşik 10; agent semantic/continuity/episode/lifecycle tipleri ve opportunity KIND_LABELS |
| `ruff check backend` | 69 başlangıç bulgusu → 0 |
| Frontend `npm run format:check` | Başarılı; başlangıçtaki 8 dosya biçim sorunu giderildi |
| `git diff --check` | Başarılı |
| Gerçek tarayıcı, isolated runtime | Invalid focus hata; missing item fallback/retry; no-focus→brain; 390px viewport scrollWidth=390; klavye Tab; wide viewport |

Calendar-to-Todo, retained RSS/Bookmarks/Flashcards/Diagnostics, manual Pomodoro
CRUD, Obsidian capture, attachment, backup/restore, migration, worker ve 37 MCP
aracı testlerle doğrulandı. Bunların tamamı için manuel tarayıcı akışı yapıldığı
iddia edilmez. Obsidian URI açma helper'ı fixture ile test edildi; gerçek desktop
Vault açılışı kişisel ortamda denenmedi.

Eksik Chromium mevcut `make career-ops-browser-setup` ile kuruldu; varsayılan
suite içindeki scraper testi çalıştı. Chromium/ffmpeg cache'i gerekli runtime
bağımlılığıdır. Opt-in canlı ağ/gerçek credential testleri varsayılan skip
sözleşmelerini korur; skip'ler başarı olarak sayılmaz.

36 skip: 28 kaynak/LinkedIn batch canlı opt-in, 2 career-ops canlı validation,
3 A5 gerçek yerel model, 3 H4 gerçek yerel model. Eksik DB veya Chromium nedeniyle
skip yoktur. Toplu `make verify` güvenlik kapısı kalan npm audit bulguları nedeniyle
yeşil değildir; alt kontroller ayrı çalıştırılarak sonuçları yukarıda raporlandı.

Bir tam turda Goals/Strategy alignment testi aralığının üst sınırı host saati,
Event zamanı DB/VM saati olduğundan yeni olay pencere dışında kalabildi.
Tek başına 24 Goals testi geçti. Fixture artık mevcut `now` parametresini
DB'nin ürettiği olay zamanından türetiyor; linked count/percent/confidence
iddiaları aynen korunuyor. Ürün clock veya Event semantiği değiştirilmedi.

## F. Güvenlik ve kalan sınırlar

`npm audit fix` yalnız uyumlu lockfile güncellemeleri yaptı (brace-expansion,
fast-uri, source-map-js, undici); force kullanılmadı. **11 → 7 bulgu**:
5 high, 2 moderate, 0 critical. Bunlar 7 ayrı kök kusur değildir; iki advisory
Tailwind geliştirme araç zincirine yayılır.

| Paket / yol | Seviye | Kalan durum |
|---|---|---|
| tailwindcss 3.4.19 → chokidar 3.6.0 → braces 3.0.3 | high | Derin pattern stack exhaustion; advisory patched sürüm bildirmiyor |
| tailwindcss → fast-glob 3.3.3 → micromatch 4.0.8 → braces | high | Aynı kök kusurun bağımlılık yolları |
| tailwindcss → postcss-nested 6.2.0 → postcss-selector-parser 6.1.4 | moderate | Selector parser CPU exhaustion; patched ≥7.1.6 |
| tailwindcss 3.4.19 | high | Yukarıdaki bağımlılıklardan gelen toplu bulgu |

Kaynaklar: [braces advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm),
[selector parser advisory](https://github.com/advisories/GHSA-rj75-hqrm-r3gf).
`npm audit` çözüm olarak Tailwind 4.3.3 major upgrade öneriyor. Uyumsuz CSS/build
migrasyonu bu kapanışta yapılmadı. Risk geliştirme/build aşamasında güvenilmeyen
pattern/selector işlenmesidir; local-only olmak bulguyu ortadan kaldırmaz.
Sonraki adım ayrı Tailwind migration ve tasarım/build regresyon doğrulamasıdır.

Yeni dış servis veya telemetri yok; UI/API yalnız loopback fixture üzerinde
çalıştırıldı. Son Git teslimi fetch sonrası mevcut main'e normal push ile yapılır.
Geçici UI/API/DB ve fixture dosyaları doğrulama sonunda temizlendi; kişisel
`forkos_pgdata` ve gerekli Chromium runtime cache'i korunur.
