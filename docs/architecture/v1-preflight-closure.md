# V1.1 Preflight Closure

Doğrulama: 11 Ekim 2026. Başlangıç: `main`, `b8124a9`; çalışma başında checkout temizdi. Bu çalışma mevcut Academic & Career LifeOS kapsamını korur.

## A. Doğrulanan başlangıç sorunları

- Tek kaynak seçimi de dört Feed veri sorgusunu ve RSS istatistiğini çalıştırıyordu; görünmeyen kaynaklar periyodik yenileniyordu.
- Kaydedilmiş boş Reddit listesi backend'de varsayılan listeye çevriliyordu.
- Kullanılmayan Weather, Home'da kurulum mesajı gösteriyordu; ayar değişiklikleri forecast hook'unda ortak settings cache'inden izlenmiyordu.
- Konu ve kart tekrarları ayrı girişlerden keşfediliyordu. Kart kuyruğu desteler yüklenmeden boş görünebiliyor, cache yenilemesi devam eden oturumu yeniden başlatabiliyordu. Askıya alınmış yeni kartlar yeni-kart toplamına giriyordu.
- Career önerisi kabulü Learning cache anahtarlarını yeterince tazelemiyordu; kanonik hedef okuma hatası dürüst bir durum göstermiyordu.
- Migration README güncel head yerine eski revision bildiriyordu. npm audit gerçekten 5 high + 2 moderate bulgu üretti.

## B. Kök nedenler

Query mount ile aktif filtre birbirinden ayrılmamıştı; boş liste ile eksik ayar aynı kabul ediliyordu. İki bağımsız SRS için ortak keşif yüzeyi yoktu. Kart oturumunun kimliği cache verisine bağlıydı. Invalidation kataloğunda Learning tüketicileri eksikti. Güvenlik bulguları Tailwind 3'ün geliştirme bağımlılık zincirindeydi.

## C. Uygulanan düzeltmeler

Feed hook'ları koşulsuz çağrılır, sorgular mevcut `enabled` mekanizmasıyla filtrelenir. RSS ve settings ortak cache ve 60 saniye stale süresi kullanır; boş Reddit tercihi istemcide ve sunucuda korunur. Sıralama, kota, dedup, RSS mutation ve SourceRun sözleşmeleri değişmedi.

Weather kullanılmıyorsa Home göstergesi render edilmez. Sunucu ayarları ortak settings cache'inden izlenir; gizli/config edilmemiş forecast sorgulanmaz. Mevcut ayarlara açık `Konumumu kullan` eylemi eklenir; otomatik izin istenmez. Dar ekranda tahmin popup'ının taşması düzeltildi.

Mevcut `/learning?view=review` konu ve kart iş yüklerini ayrı gösterir; mevcut deste API'si yeniden kullanılır. Kart kuyruğu deste sorgusunu bekler, hata/yeniden deneme gösterir, oturum boyunca sabitlenir ve birleşik girişe dönüş desteklenir. Askıya alınmış yeni kart sayımı düzeltildi. Career onayı Learning cache'lerini de yeniler; Goals okuma hatası açık gösterilir.

Tailwind 4 geçişinde tokenlar, V3 radius/shadow/outline/backdrop ve kardeş aralık/ayraç yerleşimi korundu. `stack-y-*` / `stack-divide-*` sadece V3 görünüm uyumluluğudur. V4 bağımsız `translate` özelliği nedeniyle masaüstünde gizlenen sidebar `md:translate-x-0` ile düzeltildi; geçiş animasyonu translate'i de kapsar. Sidebar masaüstünde 248px, mobilde açılır menü olarak doğrulandı.

## D. Değişen dosyalar

Davranış: `core/feedStream.ts`, `runtimeQueries.ts`, `invalidation.ts`, Today Weather/hero, Learning review/widget/commands, Flashcard page/session, CareerGoalsPanel; backend system news/router ve flashcard service. İlgili testler genişletildi.

Güvenlik: frontend package/lock, PostCSS, global CSS, Tailwind config ve mevcut `space-y`/`divide` utility kullanan bileşenlerde mekanik sınıf uyumluluğu. AppSidebar translate düzeltmesi bu geçişin parçasıdır. Dokümantasyon: Alembic README ve bu rapor. Yeni API, tablo veya ürün modülü eklenmedi.

## E. Ölçülen ağ davranışı

Ölçüm aynı başlangıç revision hook'u ve yeni hook ile izole React Query/fetch testlerinde yapıldı. Sayılar GET sayısıdır; yardımcı istekler dahil:

| Yüzey | Önce | Sonra | Sonraki istekler |
|---|---:|---:|---|
| RSS | 5 | 2 | RSS öğeleri + RSS stats |
| Reddit | 5 | 2 | ortak settings + Reddit; settings cache'deyse 1 |
| Hacker News | 5 | 1 | HN |
| GitHub | 5 | 1 | GitHub |
| Tümü, soğuk cache | 5 | 6 | dört veri kaynağı + stats + settings |
| HN, 16 dakika toplam | 7 | 2 | ilk HN + HN yenilemesi |

Tek kaynakta veri kaynağı sayısı 4→1; Tümü'nde 4→4. Yeni ayar kontrolü soğuk Tümü toplamına bir ortak GET ekler; toplam düşüş iddiası yoktur. Yeni hook'un iki eşzamanlı tüketicisi toplam 6 GET paylaşır. Tümü→HN→RSS→Tümü geçişi geçerli cache ile 0 ek GET üretir. Pasif kaynakların polling'i 0'dır. Offline cache ve bir kaynak hata verdiğinde diğerlerinin gösterilmesi test edildi.

Bağımsız TodayPage soğuk mount: 18→19 benzersiz GET; ek istek ortak settings okumasıdır. App shell de bu anahtarı paylaşır; tüm uygulama için sayısal azalma iddiası yapılmaz. Yapılandırılmamış Weather forecast 0→0; gizli Weather 0. Home'da yeni varsayılan kart hatırlatıcısı yok: mevcut Flashcard widget varsayılan kapalı ve kullanıcı tercihleri korunur.

## F. Learning / Flashcard UX sözleşmesi

`3 konu` ile `18 kart` ayrı birimlerdir; 21 tekrar gibi yanıltıcı toplam yoktur. Konu engine'i, mastery ve kart engine'i/deck ilişkileri bağımsızdır. Birleşik giriş konu detayı, ilgili deste ve tüm kart kuyruğuna gider. Eski Learning/Flashcard deep link ve direkt palette komutları korunur. Browser'da 3 konu/18 kart → kartı klavyeyle çevir/puanla → 17 kart → birleşik giriş → konu puanla → 2 geciken/1 sonraki konu akışı doğrulandı. Kart değerlendirmesi konu sayısını, konu değerlendirmesi kart sayısını değiştirmedi.

## G. Career / Goals sahipliği

Goals mevcut strateji, pillar, goal, KR, milestone ve kanonik ilerlemenin sahibidir. Career kanonik `/goals` verisini okur ve bu workspace'e bağlanır. Mevcut proposal materialization row lock/idempotency sözleşmesi doğruydu; ikinci editör/model eklenmedi. Onay/retry, ret, stale evidence ve Goals hesapları backend suite'inde doğrulandı. Learning ve Goals invalidation/navigation frontend testlerinde doğrulandı. Gerçek kullanıcı verisiyle öneri üretilmedi veya kabul edilmedi.

## H. Kasıtlı tutulan legacy envanteri

Media/Finance/Note/Document modelleri, geçmiş entity/event tipleri, backup restore uyumluluğu ve eski Vault deep link yönlendirmeleri korunur. Career dosyaları ve attachment/upload altyapısı aktif sorumluluktur; standalone Documents/Knowledge veya Drive ürünü değildir. Retired navigasyon, scheduler ve MCP product scope contract testleri geçti.

agent_lifecycle, continuity, episode, semantic_memory, execution, proactivity, statistics, sources ve system mevcut bağımsız iç sorumluluklarını korur. Modül sayısı düşürmek için birleştirilmedi.

Endpoint coverage heuristiği 2 frontend referansı bulamadı (eşik 3): execution plan recovery mevcut iç operasyon/uyumluluk yüzeyi; career-ops doctor `scripts/forkos_doctor.sh` tarafından tüketilir. Export taraması 10 (eşik 10): 8 dahili tip, içeride kullanılan KIND_LABELS ve mevcut kullanılmayan tekil getSemanticCandidate wrapper'ı. API uyumluluğunu sırf heuristik sayısını düşürmek için silmedik. Bunlar yeni ürün yüzeyi değildir.

## I. Güvenlik audit'i

Önce 7 bulgu: 5 high, 2 moderate, 0 critical. Zincirler Tailwind 3.4.19→chokidar→braces; fast-glob→micromatch→braces; postcss-nested→postcss-selector-parser. Runtime browser/backend bağımlılığı değil, geliştirme/build zinciridir.

[braces advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) için yayımlanmış düzeltme yoktu; [selector-parser advisory](https://github.com/advisories/GHSA-rj75-hqrm-r3gf) 7.1.6 ile düzeltilmiştir. Eski zinciri kaldırmak için Tailwind/@tailwindcss/postcss 4.3.3 geçişi yapıldı. `npm audit fix --force`, advisory suppression veya yeni override kullanılmadı; mevcut lodash override korundu. Son audit: **0 bulgu**.

[Resmî upgrade guide](https://tailwindcss.com/docs/upgrade-guide) doğrultusunda PostCSS/import/config ve değişen utility davranışları incelendi. V3/V4 için 85 görünür review öğesinin computed stilleri karşılaştırılarak aralık farkları giderildi; Home, review, Feed, Career, Goals, Weather/Settings dar/geniş ve açık/koyu temada kontrol edildi. Sidebar translate regresyonu ayrıca gerçek tarayıcıda düzeltildi. Tüm ekranlarda piksel bazlı otomatik golden karşılaştırma yapılmadı. V4 minimum tarayıcıları Safari 16.4, Chrome 111, Firefox 128; ayrı çapraz tarayıcı çalıştırılmadı. Yeni CDN/telemetri veya dış kişisel veri aktarımı eklenmedi.

## J. Migration readiness

Tek head `0079_retire_media_batches`. PostgreSQL 16 tmpfs test DB'sinde boş→0078→0079 gerçek Alembic upgrade çalıştırıldı. 0078'de seed edilen Media, Finance, Note, Document satırları ve entity ID'leri upgrade sonrası aynı kaldı; eski event'ler aynı kaldı. Çalışan eski Media batch completed_with_errors, source run abandoned oldu; tek retirement event oluştu. Migration SQL'inin iki kez uygulanması idempotent test edildi. Yeni migration yok.

Normal FastAPI lifespan ayrıca migration test DB'sinde başlatıldı; health/settings/cards/learning review 200 döndü. Compose migrate servisi `upgrade head` çalıştırır, API/worker başarılı migrate'i bekler; startup script bu sırayı kullanır. Kişisel DB'nin revision'ı okunmadı veya migrate edilmedi.

### Kullanıcı runtime'ı için preflight (bu çalışmada yürütülmedi)

1. Writer/worker'ı güvenli durdur; mevcut SQL backup ve uygulama JSON backup'ını al, Vault'u ayrıca yedekle. `make backup CO="docker compose"` dosyayı `backend/backups/forkos.dump` içine yazar; mevcut aynı adlı dosyayı önce ayrı zaman damgalı adla koru. Dump'ı `pg_restore --list` ile, JSON backup'ını mevcut restore validation ile kontrol et.
2. `docker compose run --rm --no-deps api alembic current` ve `... alembic heads` ile revision/tek head'i kontrol et. DB servisi açık olmalıdır.
3. `make migrate CO="docker compose"` çalıştır veya mevcut normal `forkos` startup'ın migrate gate'ini kullan. Hata varsa writer'ları açma.
4. `alembic current` head, `/api/system/health`, doctor, eski entity kayıtları ve emek/Goals sayımlarını kontrol et; retired Media işlerini başlatma.
5. Hata halinde log ve revision'ı koru; DB/Vault sıfırlama. 0079 downgrade no-op'tur, audit veya retired işleri geri döndürmez. Sorun giderildikten sonra upgrade'i yeniden dene; gerektiğinde doğrulanmış SQL backup veya mevcut açık onay gerektiren disaster-restore akışından geri dön. Normal JSON merge restore tam rollback değildir.

## K. Entegrasyon doğrulaması

Google Calendar OAuth/sync, Calendar→Todo, retired Drive scope sınırı; geçici Vault resolution/deep links/capture idempotency/conflict/unavailable fallback; career-ops/acquisition/source health; historical backup/restore backend fixture suite'inde doğrulandı. Extension'ın outbox/capture testleri geçti. Normal lifespan MCP initialize/list_tools başarılı: 37 mevcut araç, brain_capture ve forkos_execution dahil. Gerçek Google hesabı, kişisel Vault/DB, gerçek OAuth, Hermes desktop veya canlı Ollama/Qwen doğrulaması yapılmadı; dış kaynaklar kontrolsüz scrape edilmedi.

## L. Test özeti

- Backend, izole PostgreSQL ile: **2614 passed, 36 skipped**. Skips yalnızca açık opt-in canlı scraper/yerel model testleri; PostgreSQL isteyen testler ortam eksikliğiyle atlanmadı.
- Frontend: **149 dosya / 1015 passed**; TypeScript + production build geçti. PWA: 63 precache entry; giriş chunk bütçesi geçti.
- Extension: **19 passed**.
- Ruff, API/schema sync check, format, design system, navigation, invalidation, endpoint/export quality gates ve diff whitespace kontrolleri geçti.
- Browser: 390px ve 1280px, açık/koyu tema; review klavye/puanlama/dönüş, Weather popup, Feed kaynak seçimi/klavye, Home, kanonik Goals/Career navigation ve sidebar. Loading/empty/error davranışları component/query testlerinde ayrıca doğrulandı.

## M. Kalan sınırlar

Canlı OAuth/scraping/model/Hermes bağlantısı için bu test çalışması kanıt değildir. Kişisel DB migration durumu bilinmiyor. Tailwind geçişi için tüm ekranlarda golden screenshot ve ayrı Safari/Firefox oturumu yoktur. Tekil unused semantic helper uyumluluk için korundu. Normal başlangıç testinde manual automation profili kullanıldı; internet catch-up davranışı canlı tetiklenmedi.

## N. V1.1 readiness kararı

**Mevcut kodun V1.1 öncesi closure'ı izole test ortamında doğrulandı.** Yeni feature phase'e geçiş için kod/regresyon/audit gate'leri geçti; kişisel runtime'ın yedek/revision/migration preflight'ı ve canlı entegrasyon kontrolleri ayrı operasyon adımlarıdır. Kullanıcı verisiyle tamamlanmamış bir doğrulamaya READY denmedi. Ürün sınırı ve iki bağımsız SRS korundu.
