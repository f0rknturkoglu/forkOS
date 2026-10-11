# Invisible Intelligence & Workflow Cohesion

Başlangıç: `main`, `c4b7a6fac5d910fcc371c3c9524b1d0ba24e8db7`; temiz çalışma ağacı. Ekli brief'teki eski baseline yerine gerçek checkout incelendi. Goal Studio, araçsız yerel Hermes taşıması ve Capture V1 zaten mevcut; bu çalışma bunları yeniden kullanır. Doğrulama: 11 Ekim 2026, yerel macOS/OrbStack.

## 1. Yetenek → deneyim envanteri

| Yetenek | Backend sahibi | Mevcut UI | Boşluk | Değişiklik |
|---|---|---|---|---|
| Haftalık değerlendirme | review + review_intelligence | Review, agent özeti kopyala | Harici aktarım | Aynı dönemde yerel özet, isteğe bağlı görüşme |
| Proje sürekliliği | project context + H5 continuity | Projects timeline/journal/GitHub | Dönüş özeti | Nerede kalmıştım? ve mevcut göreve bağlantı |
| Plan hazırlama/onay | execution + H1 write_registry | Today PendingDecisions | UI'dan hazırlama | Görev/gün seçimi → mevcut H7 önizleme/onay/yürütme |
| Hatırlatıcılar | proactivity rules/policy/service | Settings | Teknik dil, belirsiz worker | İnsan dili, opt-in, heartbeat durumu, Review bildirimi |
| Hafıza adayları | semantic_memory | Settings aday listesi | Bağlama göre keşif | Aynı adayların filtreli görünümü ve açık onay |
| Bookmark → konu | learning.attach_bookmark | Topic ResourceList | Okuyucudan ters yol | Mevcut konu ağacında arama ve bağlama |
| Career → Goals/Todo | opportunity + canonical links | JobDetail/CRM | Sonraki adıma geçiş | İlgili kanonik kayıtlar ve mevcut görevi planlama |

## 2. Önce/sonra kullanıcı yolculukları

| Yolculuk | Önce | Sonra | Gerçek doğrulama |
|---|---|---|---|
| A — Haftalık değerlendirme | Ölçümler, ham strateji, agent'a kopyalama | Canlı dönem özeti, insan dilinde strateji, mevcut görevleri taşıma; isteğe bağlı ortak görüşme | Tarayıcıda yerel özet; H7 görev taşıma. Model görüşmesi fixture ile; canlı Hermes yok |
| B — Projeye dönüş | Timeline, görev ve notları ayrı inceleme | Projeye scoped H5, bilinmeyen çalışma zamanı açık, kayıtlı sonraki adım, Buradan devam et | Gerçek tarayıcı → seçili mevcut Todo |
| C — Okuma → öğrenme | Kart oluşturma var; konu bağlama ters yönde | Okuyucudan kart ve mevcut konu seçimi; kanonik deep link'ler | Gerçek metin seçimi → kart → konu → kaynak → deck |
| D — Proaktivite | Teknik ayarlar; entity'siz Review bildirimi Etkinlik'e gider | Açık opt-in, worker uyarısı, kayıtlı Review komutuna yönlendirme | İzole DB'de iki service tick; tek bildirim; tarayıcıda weekly Review |
| E — Hafıza | Settings üzerinden aday yönetimi | İlgili mevcut adayı incele → Hatırla | Tarayıcıdan onay/promote, yalnız fixture Vault'a bir kart |
| F — Hermes kapalı | Manuel ürün kullanılabilir | Yerel özetler de kullanılabilir; görüşme gönderimi dürüstçe engellenir | Tarayıcı + hata durumları testleri |
| G — Uzak inference | Goal Studio yalnız güvenli yerel profil kabul eder | Aynı sınır korunur; cloud profile kabul edilmez | Yerel profil/capability testleri; uzak consent akışı uygulanmadı |

### Etkileşim sayıları

Eski akışların süreleri/tıklamaları geçmişte ölçülmedi. Kodda görülen Review aktarımı kopyalama → harici uygulamaya geçme → yapıştırma gerektiriyordu. Yeni yerel özet bir tıklamada görünür; görüşme ayrıca isteğe bağlıdır. Tarayıcıda proje özeti → mevcut görev iki eylem; planlama aç → gün seç → önizleme → uygula dört eylem (varsayılan günde üç); hafıza incele → Hatırla iki eylem. İki sunucu adımı olan confirm/promote ve approve/execute, tek kullanıcı onayı içinde korunur. Reader konu akışı aç → alan → arama → konu → bağla beş eylem; arama gerekmiyorsa dört. Bu sayılar modelle konuşma turunu içermez.

## 3. Ekranlar ve kesin giriş noktaları

Bütün yollar `frontend/src/` altındadır; yeni üst seviye modül veya navigasyon yoktur.

| Route / ekran | Dosya | Giriş |
|---|---|---|
| `/review/:kind` | modules/review/ReviewPage.tsx | Haftayı birlikte değerlendirelim; Gelecek haftaya taşı; kaydedilmiş/canlı strateji açıklaması |
| `/projects` | modules/projects/ProjectsPage.tsx | Seçili proje: Nerede kalmıştım? → Buradan devam et |
| `/goals` | modules/goal/GoalsPage.tsx | Seçili hedef: Bu hedefte ilerliyor muyum? |
| `/learning` | modules/learning/TopicDetail.tsx | Bu konudan nasıl devam edebilirim? |
| `/opportunities` | modules/opportunity/JobDetail.tsx | Sonraki adımım ne? |
| `/planner` | modules/todo/WeeklyPlannerPage.tsx | Seçili mevcut planlanmamış görevleri planla |
| Today | modules/today/TodayAgendaWidget.tsx | Mevcut görevler için küçük planlama eylemi |
| Bekleyen kararlar | modules/today/PendingDecisions.tsx | Değişiklikleri uygula; durum okuma; gerektiğinde makbuzla kurtarma |
| Bookmark okuyucu | modules/bookmarks/BookmarkReaderModal.tsx + BookmarkLearningAttach.tsx | Öğrenme konusuna ekle; kart sonrası deck/tekrar bağlantıları |
| Settings | modules/settings/ProactivitySection.tsx | forkOS ne zaman yardımcı olsun?; mevcut kurallar ve worker durumu |
| Bildirimler | core/NotificationPanel.tsx | Entity'siz weekly/daily bildirimi registry Review komutu |

`core/ContextualHelp.tsx` kapalıyken sorgu bileşenini mount etmez. Açılan özet, kanıt açıklaması, hafıza inceleme ve planlama aynı UI primitive'lerini kullanır. Görüşme `modules/goal/GoalStudio.tsx` üzerinden lazy yüklenir. Normal Review kaydetme ve agent'a kopyalama seçenekleri korunur.

## 4. Yeniden kullanılan altyapı

- H3 köken/source-reference modeli ve mevcut entity/project context okuyucuları; H5 kendi mevcut evidence reader'larını kullanır. Backend kendisine HTTP/MCP isteği atmaz. Yeni genel retrieval/agent framework yoktur.
- H5 `weekly_review`, `daily_close`, `continuity`; continuity aynı `focus_entity_id` ve mevcut pencere kurallarıyla çalışır. Knowledge body okuması kapalıdır.
- Goals `strategy.overview`, Review `preview` ve kaydedilmiş `stats`; Career Opportunity/Application ayrımı ve kanonik links.
- H7 `prepare`, exact revision approval, execution, durable receipts, recovery; H1 kapalı `todo_plan` işlemi. Yeni domain mutation yolu yoktur.
- H6 mevcut config, rules, policy, history, dedup ve worker heartbeat. Yeni scheduler yoktur.
- A4 mevcut candidate inspect/confirm/promote; H2 hot-memory ve Vault mevcut destination servisleri üzerinden kalır. Context özeti aktif H2 hafızanın tamamını otomatik eklemez.
- Learning `attach_bookmark`, Bookmark highlights/capture receipts, Flashcard create_card ve kaynak link helper'ları.

## 5. Hermes taşıması ve güvenlik kararları

Mevcut Goal Studio session/run taşıması ortak kullanılır. Server-side credentials tarayıcıya verilmez. Yalnız doğrulanmış numeric loopback model adresi ve ayrı araçsız profil kabul edilir. Tool, MCP/plugin, hook, cron, curator, background review, model route, fallback/custom provider ve multiplex yetkileri kapalı olmalıdır. Capability discovery profil/run kimliği, idempotency, SSE ve stop desteğini doğrular; güvenlik prompt'a bırakılmaz.

Contextual oturum ile Goal taslak oturumu birbirine dönüştürülemez. Her yeni kullanıcı turunda bounded context yenilenir; kayıp yanıtın tekrarı aynı kalıcı tur kimliği/request'i kullanır. Contextual model çıktısındaki non-null proposal kabul edilmez; görüşme Goal/Todo yazma yetkisi kazanmaz. Kullanıcı mevcut görev ve günü ayrı deterministik planlama eyleminde seçer. SSE/cancel mevcut taşımanın sınırlarıyla korunur, run polling yalnız aktif koşuda 10 saniyedir.

Bu çalışmada kişisel Hermes profili değiştirilmedi. Canlı model yanıtı, canlı streaming/cancellation doğrulanmadı; fixture transport testleri geçti. Güvenli profil eksikse deterministic mode kullanılabilir.

## 6. Kanonik sahiplik

forkOS entity/domain servisleri operasyonel gerçektir. Obsidian insan bilgisi ve onaylı semantic kartların sahibidir. Hermes yorum/görüşme üretir; yazma yetkisi değildir. Goals hedef/sonuç, Career başvuru/kanıt, Learning konu kaynak/öğrenme tekrarı, Flashcards bağımsız SRS sahibidir. ContextualHelp yeni kalıcı iş nesnesi oluşturmaz. Yeni migration, tablo, module registry veya çekirdek entity/event/link şema değişikliği yoktur.

## 7. Consent ve uzak inference

Yerel özet modeli çağırmaz. Kullanıcı görüşmeyi açıp bir tur gönderirse yalnız güvenli yerel profil kullanılabilir. Bu sınır, cloud consent varmış gibi gevşetilmedi; mevcut taşıma cloud profili reddeder. Journey G'nin uzak provider opt-in/persist/revoke akışı uygulanmadı. İleride böyle bir taşıma desteklenirse bağımsız privacy/consent işi gerekir.

H6 master opt-in ve kural seçimleri mevcut kalıcı config'tedir. A4 adayı görmek veya incelemek onay değildir. Hafıza onayı açık kullanıcı eylemidir. Model önerisi hiçbir akışta onay yerine geçmez.

## 8. Tipli bağlam ve kaynak kökeni

`backend/app/integrations/contextual_schemas.py` kapalı discriminated context'ler tanımlar: Review tür/başlangıç/opsiyonel saved ID; Project/Goal/Career/Learning kanonik ID; Planning 1–10 seçili Todo ve gün. Entity varlığı, arşiv ve tip doğrulanır. Summary olgu/aday/eksik, timestamp, support_refs, coverage, warnings ve canonical links taşır.

Builder en fazla 16 olgu, 20 bağlantı, 30 kaynak ve 24 KB JSON üretir. Tam kayıtlar çıkarılarak sınır uygulanır; truncation görünürdür. Kaynak gövdeleri, tüm journal geçmişi, provider secrets ve key'ler gönderilmez. Project H5 ifadelerinin bütün support_refs seçili projeyle ilişkilendirilmiş kaynaklara ait olmalıdır. Commit hareketi kişisel çalışma veya sonuç sayılmaz.

Kaydedilmiş Review `stats` snapshot'ını okur; bugünün H5 verileriyle tarih yeniden yazılmaz. Eksik/eski KR sonucu bilinmeyendir; odak saati Goal sonucu değildir. Partial dönem tam dönemle karşılaştırılmaz. Learning kaynak bağlantısı mastery değildir. Hafıza adaylarının UI inceleme metadatası inference context'inden çıkarılır. Harici kaynak/model metni veri olarak tutulur, yetki vermez.

## 9. Onay, idempotency ve kurtarma

`POST /execution/planning` yalnız açık/doing mevcut görevleri kabul eder. Birden fazla gelecek slot varsa belirsiz seçimi reddeder. Tek slotun saat/süresini korur, yalnız plan gününü değiştirir; deadline/status değişmez. UI seçim kimliğini POST öncesi localStorage'da saklar. Aynı UUID/seçim aynı planı döndürür; farklı seçim 409'dur. Prepare domain kaydını değiştirmez.

H7 v3 revision mevcut hedef stamp'ine ek olarak gelecekteki PlanSlot projection fingerprint'ini bağlar. Approval ve her execution step'te güncellik kontrol edilir. Tarihî v1/v2 revision'lar korunur. Önizleme exact revision'ı onaylar, sonra aynı revision yürütülür. Başarı yalnız gerçek receipt durumuna göre gösterilir. Son durum okunamazsa tekrar yürütmek yerine durum kontrolü istenir. Server `needs_recovery` bildirirse kullanıcı mevcut recover endpoint'ini çağırır; tamamlanan adımlar tekrarlanmaz, unknown receipt kör replay edilmez.

Bookmark highlight POST isteği opsiyonel kalıcı UUID ve existing capture receipt kullanır. Reader pending selection digest/UUID'yi istekten önce saklar, başarıdan sonra kaldırır. Aynı kayıp yanıta tekrar aynı highlight; farklı içerik/UUID kullanımı conflict. Highlight→card deterministic UUID ile tek transaction'da card/event/source link/receipt yazar. SRS reps değişmez.

A4 source revision mevcutsa promote öncesi tekrar doğrulanır; missing/mismatch stale + append-only event/409 üretir. Contextual candidates yalnız normal sensitivity, uygun explicit-user/canonical-source, geçerli dönem ve fresh destek kaynaklarıdır. Desteklenmeyen legacy candidate Settings'te kalır. En fazla üç aday; dismissal localStorage ile hatırlanır. Ham transkript veya yeni model speculation kaydedilmez.

## 10. Modüller arası ilişkiler

Bookmark Learning topic'e mevcut Resource servisiyle bağlanır; yeniden bağlamak duplicate üretmez. Inbox collection korunur. Kaynakta bookmark canonical ID/provenance korunur. Card kanonik deck ve `/learning?view=review` girişinden erişilebilir; kaynak eklemek Learning review veya SRS review değildir.

Career özeti keşif/başvuru durumunu ayrı gösterir; mevcut ilgili Goal/Topic/Todo'ya gider, otomatik başvuru veya Goal kopyası üretmez. Review/Project/Today aynı seçili mevcut görev planlamasını kullanır. Entity deep link'leri backend registry resolver'dan gelir. Entity'siz H6 ritüel bildirimi frontend registry'deki mevcut Review komutunu çalıştırır.

## 11. Performans ölçümleri

Ölçümler izole yerel API/Vite, fixture DB, gerçek in-app browser üzerindedir; production SLA veya React profiler sonucu değildir.

| Kontrol | Sonuç |
|---|---|
| Proje help action → görünür yerel olgular | 289 ms, bir gözlem; browser automation süresi dahil |
| Weekly help action → görünür yerel olgular | 271 ms, bir gözlem; browser automation süresi dahil |
| Pasif Home → Projects → Learning → Review | context 7→7, Hermes turn 0→0, planning 3→3; yeni request delta 0/0/0 |
| Kapalı assistance | ContextSummary mount edilmez; fixture testinde sıfır yardım çağrısı |
| Özet cache | Mevcut domain query key owner, 60 saniye staleTime; mutation sonrası invalidateAfter |
| Hermes polling | Aktif koşuda 10 saniye; passive inference yok |
| H6 Settings polling | Özellik etkinse; kapalı özellik polling yapmaz |
| Production bundle | 68 asset, giriş chunk guard 500 KiB sınırında; 64 PWA precache girdisi, 1319.18 KiB |

Normal domain sorguları ve önceden var olan polling devam eder; toplam sayfa istekleri sıfır diye raporlanmaz. Değişiklik öncesi wall-clock latency baseline'ı yoktur. Bounded context verisi yeni summary için deliberate action ile alınır; model yanıtını beklemez.

## 12. Test sonuçları ve yöntem

| Gate | Sonuç |
|---|---|
| PostgreSQL'li tam backend suite | 2649 passed, 36 skipped, 215.43 s |
| Son contextual turn/copy değişikliklerinden sonra targeted backend | 42 passed, 3.67 s |
| Tam frontend Vitest | 151 dosya, 1028 test passed, 12.94 s |
| Son UI metinleri sonrası targeted frontend | 5 dosya, 29 test passed |
| TypeScript + Vite + bundle guard | Passed |
| Ruff | Passed |
| OpenAPI/api-schema sync + api:check | Passed |
| Endpoint coverage | 1 mevcut career-ops doctor orphan; 3 sınırının altında. Yeni endpoint'ler tüketilir |
| Registry/migration/design/invalidation guardrail | Tam test suite'lerinde passed |
| git diff --check | Passed |

DB testleri kendi `forkos-cohesion-test-db` PostgreSQL 16 container'ında tmpfs/no volume ile çalıştı. `forkos_test` pytest, `forkos_ui_test` browser verileri ayrıydı. Her ikisi mevcut Alembic head'e yükseltildi. Browser API lifespan kapalıydı: fixture akışlar otomatik scrape, worker veya kişisel MCP startup tetiklemedi. H6 service tick ayrıca açıkça fixture DB üzerinde çağrıldı; APScheduler/OS delivery canlı testi yapılmadı.

Gerçek tarayıcıda: project facts/canonical Todo, weekly period/Goal deep link, unknown Goal progress, exact H7 apply ve slot değişimi, A4 inspect/onay/promote, gerçek reader metin seçimi/card/topic/deck, Learning mastery ayrımı, Hermes unavailable, weekly notification→Review doğrulandı. DB before apply 12 Ekim 10:00/45 dk, after apply 13 Ekim 10:00/45 dk, tek slot. Reader sonunda Bookmark 1, Resource 1, Card 1, reps 0; bookmark inbox'ta kaldı. H6 ilk tick surfaced 1, aynı koşul ikinci tick surfaced 0.

390 mobile, 768 tablet, 1280 desktop; light/dark; uzun Türkçe ve yatay overflow kontrol edildi. Project entry Enter ile açılıp kapanır, focus entry'ye döner; Modal/core primitive focus davranışları korunur. Loading/empty/error/unavailable/recovery durumları fixture testlerindedir. Tam screen-reader ve işletim sistemi reduced-motion oturumu çalıştırılmadı; mevcut primitives/token/CSS davranışı kullanılır. Kanıt ekran görüntüleri yerel Codex artifact klasöründedir; test verisi Git'e eklenmedi.

## 13. Sınırlar ve blokajlar

- Canlı güvenli Hermes görüşmesi/stream/cancel bu koşuda doğrulanmadı; profile bağlantısı olmadan gönderim engellenir. Journey A'nın model bölümü fixture-tested, live-ready olduğu iddia edilmez.
- Uzak inference consent Journey G uygulanmadı; cloud profile fail-closed. Yerel ürün kullanılabilir.
- Contextual chat serbest model action proposal yürütmez. Görev/gün seçimi kullanıcıya ait kapalı deterministik H7 akışıdır.
- Career giriş Opportunity detayında; Application bağımsız yardım yüzeyi eklenmedi. Mevcut bağlı Application durumu okunur.
- Source pointer özetlenir; Project journal gövdesi/Vault kapsamlı arama otomatik okunmaz. GitHub issue/PR zengin yorumu yalnız mevcut kayıt ilişkileri kadar mümkündür.
- H6 browser weekly/daily bildirimi doğrulandı; native OS entity'siz ritüel notification click davranışı ayrıca değiştirilmedi/doğrulanmadı. Worker varsayılan kapalı kalır.
- A4 kaynak revision'sız/legacy adaylar contextual öneriden dışlanır; Settings mevcut yönetim yolu korunur.
- Dismissal ve pending UUID'ler mevcut localStorage sınırında; yeni tarayıcı DB veya consent deposu yoktur.
- Dar ekran ve klavye kontrolleri odaklıdır; tüm ekran/reader kombinasyonları için kapsamlı accessibility sertifikasyonu değildir.

## 14. Henüz bu deneyime bağlanmayan yetenekler

Genel H3 çok kanallı arama, H4 model lane seçimi, A2/A3 episodic bootstrap, tam H2 memory injection, Career interview/package/cover-letter araçları, geniş H1 write registry ve Project journal düzenleme burada yeni otomatik akışa bağlanmadı. Bunların mevcut ürün/MCP yüzeyleri korunur; yeni contextual UI onları kullanıyor gibi göstermez. Yerel ve kanıtlı deneyimler tamamdır; güvenli Hermes canlı bağlantısı ve gelecekteki remote consent ayrı kalan doğrulama/ürün işleridir.
