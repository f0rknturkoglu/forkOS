> Bu belge 2c55ff5 konsolidasyonunun tarihsel uygulama raporudur.
> Güncel kararlar [V1 ürün kapsamı](v1-product-scope.md), kalan düzeltmeler
> [V1 kapanış raporu](v1-scope-closure-report.md) içindedir.

# V1 kapsam birleştirmesi — Academic & Career LifeOS

## Kararlar

| Durum | Ürün / altyapı |
| --- | --- |
| Korundu | Home / Today, görevler, plan, projeler, hedefler ve strateji |
| Korundu | Kariyer, akademik fırsatlar, forkjob_core ve career-ops |
| Korundu | Öğrenme, bağımsız kartlar ve mevcut SRS/review geçmişi |
| Korundu | Takvim ve Takvim → görev oluşturma |
| Korundu | Pomodoro sayacı, bağımsız geçmiş, elle seans ekleme/düzenleme/silme |
| Korundu | RSS / Feed ve Yer İmleri, birbirinden ayrı ürünler |
| Korundu | Tanılama, kaynak sağlığı, doctor, worker ve MCP |
| Emekli | Medya, Finans, bağımsız Belgeler ve Bilgi arayüzü |
| Emekli | Google Drive entegrasyonu; Calendar OAuth korunur |

Bilgi sahibi Obsidian'dır. Obsidian Vault, indeks, arama, agent bağlamı/hafızası,
semantik hafıza, proje ve öğrenme not köprüleri korunur. Yeni bir Obsidian editörü
veya ikinci bilgi uygulaması eklenmedi.

## Ön inceleme ve bağımlılık haritası

Frontend kayıt noktası `src/modules/index.ts`; rota/widget/komutlar modül registry'sinden,
sidebar alanları `core/navigation.ts` üzerinden türetilir. Ayarlar, Home, global arama,
ilişki paneli, bildirim hedefleri ve hızlı işlemler de incelendi.
Backend kayıt noktası `app/modules/__init__.py::MODULES`. Entity tipleri, son tarih
sağlayıcıları ve olay sözlüğü registry'dedir. FastAPI ve worker bu kayıtları kullanır.
MCP araçları `integrations/agent/tools.py` üzerinden kayıtlıdır.

| Tüketici | Gerçek bağımlılık | Uygulanan sınır |
| --- | --- | --- |
| RSS / Bookmark | Entity, link, SourceRun; bilgi notları için Obsidian | Belge/Medya/Finans runtime bağımlılığı yok; ayrı servisleri korundu |
| Öğrenme | PomodoroSession, Vault, SRS | Aynı seans tablosu ve bilgi altyapısı korundu |
| Flashcards | mevcut review/SRS, entity, Obsidian | Algoritma ve geçmiş değiştirilmedi |
| Kariyer / Academia | Document modeli, CV bağları, yerel dosya/metin çıkarma | Yerel liste/yükleme/indirme ve paket üretimi korundu; Drive sync kaldırıldı |
| Takvim | Todos, external_event, Google OAuth | OAuth belge router'ından entegrasyon router'ına taşındı; Takvim registry'si üzerinden kayıtlı |
| Pomodoro | Entity bağlamları, görev/proje/öğrenme | Medya kapak JOIN'i ve seans → medya transferi kaldırıldı; eski bağlam FK'leri korundu |
| Hedef / Strateji | retained modüller ve append-only tarihsel aktivite | İlerleme sağlayıcıları ve bağlantılar değişmedi |
| Tanılama | yedek/runtime/kaynak/agent/Vault durumları | Drive uyarıları ve bulut yedek paneli kaldırıldı; tarihsel depolama raporu korundu |
| Backup / restore | Base.metadata ve yerel dosyalar | Emekli tablolar metadata'da; yedek ve geri yükleme için görünür kalır |
| Home / deadlines | Medya ve abonelik sağlayıcıları | Aktif sağlayıcılar, öneriler ve emekli nesnelerin plan gösterimi kaldırıldı |

### Modül sınıfları

- **Ürünler:** yukarıdaki retained yüzeyler; Academia kariyer/fırsat mimarisinde kalır,
  yeni ayrı modül veya rota oluşturulmaz.
- **Ortak altyapı:** entity/link/event, kaynak kuyruğu, retention, dosya ve backup,
  arama, zaman, registry, Obsidian, agent/MCP/hafıza.
- **İç yardımcılar:** system/statistics/execution ve tanılama toplama servisleri.
- **Bağımsız entegrasyonlar:** Google Calendar, GitHub, yerel modeller, Obsidian,
  forkjob_core, career-ops.
- **Soğuk uyumluluk:** Medya/Finans/legacy Note modelleri ve olay etiketleri;
  Document'ın Drive kökenli kolonları. Bunlar aktif emekli ürün servisleri değildir.

## Frontend

Emekli modül klasörleri, kayıtları, widget'ları, komutları ve ayar panelleri kaldırıldı.
Kütüphane RSS/Feed ve Yer İmleri'ni içerir. Finans alanı yoktur. Eski Medya/Finans
URL'leri Home'a, Belgeler başvuru çalışma alanına, Notes/Knowledge Agent & Bilgi
ayarlarına yönlenir. Eski entity tipleri backend registry'sinde güvenli tarihsel
hedeflere gider; global aramada ve yeni ilişki seçiminde görünmez.
Mevcut tasarım primitive'leri, tokenlar ve invalidation sözleşmesi korunur.

## Backend ve entegrasyon emekliliği

- Medya/Finans runtime implementasyonları kaldırıldı; boş HTTP registry ve açık model
  kayıtları yalnız şema ve tarihsel olay sözlüğünü korur. Son tarih sağlayıcıları yoktur.
- Medya sağlayıcıları, sync/search/progress/artwork mutation servisleri ve scheduler işi
  kaldırıldı. Günlük bakım emekli medya dosyalarını budamaz.
- Manuel yenileme medya işi üretmez. Kuyruk sahiplenmesi yalnız `opportunity` kapsamını
  tüketir; eski medya batch'leri yeniden çalıştırılmaz.
- Google Drive liste/sync ve yedek upload kodu kaldırıldı. Yerel yedek üretimi devam eder.
- Google OAuth yalnız `calendar.events` ister (`include_granted_scopes=false`). Ortak
  kimlik bilgileri ve Calendar token'ı otomatik silinmez veya revoke edilmez.
- Drive'a özel MCP aracı kayıtlı değildi. Aktif agent araçları retained ürünler ve
  Obsidian bağlamını kullandığı için korunur.
- Yeni bağımlılık, framework veya dış ağ servisi eklenmedi. `httpx`, multipart ve pypdf
  retained kaynaklar ve kariyer dosyaları tarafından kullanılır; bu nedenle korunur.
- Eski medya/finans/Drive ayar satırları DB'de korunur; aktif settings yanıtında sunulmaz,
  bu anahtarlara yeni yazma reddedilir.

## Pomodoro geçmişi

Tek kaynak `pomodoro_session` + entity'dir; ikinci manuel seans tablosu yoktur.
`0078_pomodoro_source` yalnız `source` kolonunu ekler. Eski kayıtlar timer olarak
korunur; append-only olayda `manual=true` kanıtı bulunanlar manual işaretlenir.

Geçmişte **elle ekle**, **seansı düzenle**, onaylı **seansı sil** kullanılabilir.
Başlangıç (yerel arayüzden offset içeren ISO zamanına çevrilir), süre, isteğe bağlı
konu/not ve görev/proje/öğrenme bağlamı desteklenir. Backend offset'siz manuel zamanları,
1–600 dakika dışında süreyi ve gelecekte biten tamamlanmış seansı reddeder.
Aktif sayacı geçmişten düzenlemek/silmek reddedilir. Sayaç seansı düzenlendiğinde
kaynak, yarıda kesilme ve duraklama bilgisi korunur. Tarihçe düzenlemeleri entity
helper'ını ve yeni `pomodoro.updated` olayını kullanır. Silme yalnız gerçek bir
Pomodoro kaydına uygulanır; başka entity'yi bu endpoint'ten silmek mümkün değildir.
Analiz ve öğrenme süreleri aynı seans tablosundan hesaplanır.

Olay geçmişi bir denetim izidir: eski tamamlanma olayları düzenlenmez/silinmez.
Genel olay tabanlı emek haritası/tarihsel sayaçlar, güncel seans analiziyle aynı
anlama gelmez; bunlar tarihsel aksiyonları göstermeye devam eder.

## Veri güvenliği

Hiçbir emekli tablo DROP edilmedi; entity, event, link, kullanıcı dosyaları ve Vault
korundu. Finans/Medya/legacy Note şemaları Alembic metadata ve tam yedekte kalır.
Eski Drive dosya kimlikleri yalnız tarihsel alanlardır; uzak dosyalar değiştirilmez.
İzole test DB'si tmpfs kullanır; kişisel lifeos/forkos_pgdata test veya seed değildir.

## Kalan teknik borç / sınırlar

- Soğuk arşiv tablolarının fiziksel temizliği ayrı veri-silme yetkisi gerektirir.
- Önceden verilmiş Google hesabı Drive izinleri sunucuda revoke edilmez; ortak Calendar
  erişimini bozmamak için mevcut token korunur. Yeni bağlantı yalnız Calendar ister;
  eski hesabın grant temizliği Google hesap izinlerinden ayrıca yönetilebilir.
- Genel olay bazlı analitik append-only aksiyon geçmişidir; seans düzenleme/silme
  geçmiş eylemi geri almış gibi gösterilmez. Pomodoro analizi güncel kayıtları kullanır.

## Doğrulama

Doğrulama: 11 Ekim 2026, izole PostgreSQL 16 tmpfs veritabanı.

| Kontrol | Sonuç |
| --- | --- |
| Backend geniş tur (`pytest -q -k 'not test_live_liveness_and_extraction_smoke'`) | 2604 geçti, 36 atlandı, 1 canlı test ayrıldı |
| Son Today sözleşmesi + V1 kapsam/CRUD/migration/Calendar→Todo (`test_today_kinds`, `test_v1_scope`) | 18 geçti; son eklemeler geniş turdan sonra ayrıca doğrulandı |
| Frontend tüm Vitest | 144 dosya / 978 test geçti |
| TypeScript + Vite + PWA/bundle | Geçti, 65 asset |
| Runtime OpenAPI / TypeScript sözleşmesi (`api:check`) | Geçti |
| Endpoint coverage | Geçti, 2 referanssız uç / izin verilen 3 |
| Ölü export kontrolü | Geçti, 10 / izin verilen 10 |
| Değişen ve yeni Python dosyalarında Ruff | Geçti |
| `git diff --check` | Geçti |
| Dolu veriyle 0077→0078 migration | Eski timer/manual seanslar, süreler, olaylar ve medya arşivi korundu |
| Worker job kayıt kontrolü | Medya işi yok; RSS, Calendar, GitHub, kaynak kuyruğu ve yedek işleri duruyor |

Tarayıcıda izole API üzerinden manuel Pomodoro ekleme, tarih/süre düzenleme,
yenileme sonrası kalıcılık, silme onayı/iptal ve eski Media→Home yönlendirmesi
kontrol edildi. Dar görünüm ve 1280×900 görünüm incelendi. Takvim gününden görev
formu açıldı, seçilen gün doğrulandı; kayıt ve yenilemeden sonra aynı hücrede Todo
bağlantısı görüldü. Kişisel DB veya Vault'a test kaydı yazılmadı.

Takvim incelemesinde doğrudan gün→görev girişinin bulunmadığı görüldü. Mevcut
`TodoComposer` ve atomik `createTask(plan_day)` akışı gün hücresine bağlandı;
görev/plan modeli ve Google salt-okunur aynası değişmedi.

Eski MCP testlerinin 36 araç beklentisi, zaten kayıtlı Goals/Strategy aracıyla 37
olan mevcut sözleşmeye düzeltildi. Haftalık review testi, korunması gereken olgusal
Goals alignment çıktısını kişisel üretkenlik puanı saymayacak şekilde güncellendi;
score/grade/discipline yasakları korunuyor. Bu nedenle runtime araçları veya
Goals çıktıları test geçirmek için değiştirilmedi.

### Doğrulama sınırları ve repo durumu

- Canlı career-ops extraction testi kurulu olmayan `chromium_headless_shell-1243`
  yüzünden ilk geniş turda başarısız oldu. Son turda yalnız bu test ayrıldı; canlı
  dış site extraction başarısı iddia edilmez.
- Tam repo Ruff kontrolünde değişmeyen dosyalarda 68 bulgu var; bu görevde değişen
  Python dosyaları temiz. Tam `make verify` yeşil olarak raporlanmaz.
- Mevcut npm lockfile denetimi 11 bulgu (3 moderate, 8 high) raporladı. Bu kapsamda
  bağımlılık sürümü veya lockfile değiştirilmedi; yeni paket eklenmedi.
- Gerçek Google hesabında OAuth yeniden bağlama veya dış Calendar sync yapılmadı;
  retained Calendar akışı sözleşme/fixture testleriyle doğrulandı.
- Kişisel veritabanına migration uygulanmadı. Mevcut `forkos` açılış komutu migrate
  servisini çalıştırarak 0078'i sonraki açılışta uygular.
- Geçici API/web servisleri ve tmpfs test container'ı kapatılır; kişisel volume ve
  servis durumu korunur.
- Başlangıç checkout'u temizdi. Konsolidasyon tek kapsam commit'inde teslim edilir;
  commit ve push sonucu teslim mesajında belirtilir.

