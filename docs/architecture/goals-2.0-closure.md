# Goals 2.0 — Yerel doğrulama kaydı

Tarih: 13 Ekim 2026. Doğrulama başlangıç HEAD `0b3bd9154aaf0dcabc103b31b759365d45d110f5`.
Önceki annotation düzeltmeleri bu commit ile uzak `main` üzerindedir; `git ls-remote`
ile kontrol edildi. Doğrulama sırasında Goals 2.0 çalışma ağacı commit/push
edilmedi. Kullanıcı 13 Ekim 2026 tarihinde tüm değişikliklerin commit ve push
edilmesini açıkça istedi. Manuel CI, release, tag ve deploy çalıştırılmadı.

**GOALS 2.0 IMPLEMENTED — LOCALLY VERIFIED**

Primary canonical kullanıcı akışları, gerçek yerel Hermes ve izolasyonlu test
ortamında doğrulandı. Aşağıdaki model/entegrasyon sınırları bu verdict ile saklanmaz.

## Uygulanan mimari

Tek Goals composer, normal ve uzun vadeli tercih; kapalı V2 semantik package
compiler; düzenlenebilir insan önizlemesi; mevcut V1 Studio session/revision,
fingerprint, expiry, stale kontrolü, concurrent approval ve durable idempotent
receipt. Apply, gerçek Goal/Todo/Learning/PlanSlot/Link servisleriyle tek transaction
kullanır. Hata veya geçersiz model cevabı yarım operasyonel kayıt bırakmaz.

Yeni Entity-backed `GoalRoadmapNode` yalnız yapı ve kanonik target referansı saklar;
Todo/Topic/Project tamamlanma durumunu kopyalamaz. SVG/list graph; collapse, pan,
zoom, fit, keyboard, canonical deep link ve onaylı node düzenleme/ayırma vardır.
Ortak ilerleme helper'ı kanonik işleri tekilleştirir, Project milestone ağırlıklarını
korur, parent container'ı tekrar saymaz. Gerçek sonuç ölçümü ayrı kalır.

İlk plan 14 gündür: gerçek günlük kapasite, mevcut PlanSlot ve local Calendar
çakışmaları, uygun gün ve açık saat aralıkları denetlenir. Kullanıcının manuel
bloğunu açıkça taşıma eski saati/süreyi/notu korur; eski ve yeni gün verisi stale
kontrolüne dahildir. Google bağlantılı blok normal Planner akışında düzenlenir.

Her soru yeni scoped snapshot alır: accepted graph alt hedefleri, gerçek Todo,
Topic, kaynak, Project, KR, 7/30/90 hareket ve ilgili kabul edilmiş Review geçmişi.
Ayrılmış iş legacy bağlardan geri gelmez. Yerel aday keşfi, reuse, provenance ve
henüz bulunmamış kaynak ihtiyacı görünürdür. URL veya ölçüm uydurulmaz.

### V1 uyumluluğu ve migration

Goal/StrategicPlan/Pillar/KR/Review/Studio geçmişi, canonical Todo/Planning,
Learning resource bridge, registry/type routes ve `invalidateAfter()` tekrar
kullanılır. Teknik paneller isteğe bağlıdır; kullanıcı UUID veya KR provider
kurmak zorunda değildir. Önizleme öncelikleri Todo modülünün ortak ölçeğini kullanır. Todo'nun tamamlanmış satırı aynı kayıt üzerinde yeniden
açılabilir; `completed_at` temizlenir ve append-only `todo.reopened` olayı yazılır.

`0081_goal_roadmap`, 0080 sonrası tek additive head: entity FK, index/checks,
canonical target SET NULL. Boş graph downgrade edilebilir; kabul edilmiş graph
0080'a dönüldüğünde korunur ve reupgrade idempotent'tir. Daha eski Goal tablosunu
düşüren derin downgrade kabul edilmiş graph verisinde FK tarafından engellenir.
Üretim upgrade öncesi doğrulanmış `backend/backups/pre-goals-2-20261013.dump`
Git dışında saklandı. Migration kişisel DB'ye uygulanmıştır; sağlık/overview 200.

## Veri ve test izolasyonu

Otomatik testler `forkos_test`, tarayıcı `forkos_browser_test` DB'sinde çalıştı.
İkisi yalnız `forkos-living-goals` tmpfs PostgreSQL projesindedir. API 18888, Vite
5174 ve boş test Vault kullanıldı. Kişisel DB, Vault veya attachment test verisi
olarak kullanılmadı. Normal 5173/8787, kişisel `forkos_pgdata`, native Hermes/model,
profil, credentials ve sağlayıcı tercihi korunmuştur. Test worker/catchup kapalıdır;
kişisel veriye bağlanan maintenance işleri çalıştırılmadı.

## Yerel test sonuçları

- Tam backend: **2815 geçti, 43 atlandı**, 225.91 s. Todo reopen, registry ve
  activity filtre düzeltmeleri bu son tam tekrarın içindedir. Guard
  düzeltmelerinden sonra odaklı grupta ayrıca 67 test geçti (8.11 s).
- Tam frontend: **161 dosya, 1083 test geçti**, 16.57 s.
- Extension: **27 geçti**, 0 hata.
- Python `ruff check app tests scripts`: geçti.
- Prettier tam kontrol: geçti. TypeScript ve Vite/PWA build: geçti; 1 giriş chunk,
  74 asset, 90 precache girdisi ve mevcut bundle limitleri içinde.
- OpenAPI/TypeScript API sync: geçti; Docker Python wrapper yalnız ortamın Python
  sürümünü sağladı, kontrol kuralları değiştirilmedi.
- Endpoint coverage: 1 eski kullanılmayan `/api/system/career-ops/doctor`, eşik 3;
  yeni Goals endpoint'lerinin hepsi tüketilir. Dead exports: 2 eski kayıt, eşik 10.
- npm audit: 0 güvenlik açığı. `git diff --check`: temiz.

Yeni/odaklı kabul testleri atomik apply, rollback-after-slot, concurrent/replayed
approval, response sonrası tekrar, stale canonical/calendar, sahte token/ID,
hierarchy/dependency cycle, shared task ve child scope, Project milestone ağırlığı,
archived/missing target, recurring template/occurrence, manuel KR=32 korunması,
kaynak reuse, detach ve nested context, capacity splitting, clock/calendar çakışması,
user-authored date/quantity ve native preview edit yarışını doğrular. Mevcut registry,
migration, design system, endpoint, invalidation ve extension guard'ları korunur.

## Gerçek Hermes ve tarayıcı akışları

**Gerçek Hermes 0.21.6 / yerel custom Qwen3.5-9B-Q4_K_M / sıfır etkin araç** ile
çalıştı. Aşağıdaki authoring ve coaching sonuçları inference fixture değildir.
Modelin ilk bozuk/eksik/duplicate alanlı çıktıları kapalı validator tarafından
reddedildi; bunlarda domain yazımı olmadı. Bir tur için en fazla bir yapısal
düzeltme yapılır. Kusurlu geçmiş yanıtlar sonradan başarılı gibi yeniden yazılmadı.

### A — Normal hedef

1. Tarayıcıdan “YDS'den en az 55 almak istiyorum. Günde iki saat çalışabilirim.”
   gönderildi. Mevcut seviye, puan ve sınav tarihi bilinmiyor kaldı.
2. Gerçek model taslağı üç aşama, milestone, dört Todo, iki StudyTopic, StudyArea,
   üç kaynak ihtiyacı ve dört day-level PlanSlot sundu. Önizlemede hedef başlığı
   ve görev açıklaması düzenlendi, kaydedilip açıkça onaylandı.
3. Gerçek Todo/Calendar/Weekly Planner/Learning ekranlarından kayıtlar açıldı.
   Goal ID `db664ce0-092b-442b-9813-00496377c35e` yalnız sentetik DB'ye aittir.
4. Todo sayfasından ilk iş tamamlandı: başlangıç aşaması %17, hedef %6; gerçek
   sınav sonucu hâlâ “Henüz ölçülmedi”.
5. Aynı kalıcı görüşmede iki yeni pratik işi istendi. Doğru taslak yalnız iki
   yeni Todo ve iki 30 dk slot içerdi; eski işler/aşamalar çoğaltılmadı. Önizlemede
   iki slot 20 Ekim'e taşındı, kayıt sonrası iki tarih de korunarak onaylandı.
   Toplam altı Todo/altı slot, aynı eski tamamlanma durumu korundu. Haftalık
   Plan sonraki haftaya çevrilince Salı 20 Ekim tarihinde tam iki blok gösterdi.
6. Hermes güncel snapshot ile “1 görev tamamlandı, genel ilerleme %3” dedi ve
   bekleyen yeni kelime işini önerdi. Kapsam eklenince yüzde paydası değişti;
   bu tamamlanmış işin kaybolduğu anlamına gelmez.
7. Learning sayfasında konu “Öğrenildi” yapıldı: yüzde %6 oldu. Todo yeniden
   açıldığında %3'e düştüğü gerçek tarayıcıdan doğrulandı. Tekrar tamamlama da
   aynı kanonik kayıt üzerinden yapılır. Sonuç puanı değiştirilmedi.
8. Sayfa reload ve “Son görüşme” kayıtlı taslağı/uygulama receipt'ini sürdürdü;
   otomatik ikinci apply veya duplicate operasyonel kayıt oluşmadı.

### B — Uzun vadeli hedef

Aynı composer ile beş yıllık yazılım mühendisliği planı ve günde bir saat istendi.
Gerçek model beş yıl çocuğu sundu; insan önizlemesinde istenen üç döneme indirildi
(İlk Yıl, 2–3. yıllar, 4–5. yıllar), gereksiz iki root aşaması çıkarıldı ve kaydedildi.
Bu düzenleme modelin başlangıç çıktısını kusursuz saymak için gizlenmedi.

Onay gerçek root + üç child Goal ve yalnız ilk child'ın dört Todo/dört day-level
bloğunu oluşturdu. Gelecek dönemler detaylı günlük görevlerle doldurulmadı.
Root grafiğinden canonical ilk dönem Goal'u açıldı. Todo sayfasından ilk dönem işi
tamamlanınca child %6, root %2 oldu; sonraki iki dönem %0 kaldı. Hermes aynı kalıcı
görüşmede 30/90 gün için bir tamamlanmış iş, child %6/root %2 ve günlük 60 dk
kapasiteyi kullandı. Ölçülmemiş sonucu başarı diye sunmadı.

Son sentetik domain sayımı: **5 Goal, 10 Todo, 6 StudyTopic, 10 PlanSlot**. Bu,
normal hedef + onaylı iki iş revizyonu + uzun vadeli root/üç dönem toplamıdır.

### Arayüz ve hata kontrolleri

- Desktop, açık/koyu tema, uzun Türkçe adlar, collapsible graph ve canonical node
  inspector/deep link gerçek tarayıcıda açıldı.
- Graph keyboard ArrowRight, expand ve zoom/fit çalıştı; inspector odak alır ve
  Escape/kapama sağlar. 400 düğümlü collapse görünümü frontend testiyle doğrulandı.
- Chrome cihaz toolbar'ından **390 px** gerçek viewport: document width 390,
  yatay taşma yok; graph otomatik erişilebilir listeye geçti. Browser capability
  override etkisiz olduğundan native Chrome device UI kullanıldı.
- Chrome menüsünden **%200 zoom**: 900 px viewport/document 890, taşma yok.
- `prefers-reduced-motion: reduce` gerçek Chrome Rendering panelinde doğrulandı;
  roadmap hareket gerektirmeyen SVG/list gösterimidir. Emülasyon geri alındı.
- İzole API kesildi: loading → “Hedefler alınamadı” ve yeniden dene görüldü.
  API geri geldiğinde retry registry'yi de yenileyerek gerçek record linklerini
  geri getirdi. Sessiz yanlış başarı veya onaysız yazım olmadı.
- Empty/partial, provider unavailable, invalid output, canonical unknown/archived,
  concurrency, resource/measurement preservation ve reduced-motion CSS davranışı
  mevcut otomatik testler/source guard'larıyla birlikte doğrulandı.

Native screenshot kanıtları `.codex/artifacts/goals-2/`: `live-package-preview.png`,
`live-goal-created.png`, `live-todo-completed.png`, `live-progress.png`,
`live-calendar.png`, `live-weekly-planner.png`, `live-coaching.png`,
`live-long-term-created.png`, `live-mobile.png`, `live-zoom200.png`,
`live-light.png`, `live-reopened.png`, `live-network-error.png`,
`live-revision-planner.png`, `live-final-goal.png`, `live-final-long-term.png` ve
`live-long-term-coaching.png`.
Test logları `.codex/goals-2-*.log` dosyalarındadır; bunlar git'e eklenmez.

## Açık sorunlar ve sınırlar

- P0: bilinen çözülmemiş veri/onay güvenliği sorunu yok.
- P1: bilinen primary canonical akışı engelleyen çözülmemiş sorun yok.
  Authoring/apply/progress/coaching/revision ve long-term akışları tamamlandı.
- P2: küçük yerel model ilk istekte geçerli ve tam uygun planı her zaman üretmiyor;
  bounded correction veya yeni tur ve insan önizleme düzenlemesi gerekebilir.
  Koçluk metninin kapsam adlandırması zaman zaman muğlak olabilir; deterministik
  UI yüzdeleri ve kayıtlı veri temel alınır.
- P2: çok büyük kapsam bounded/truncated, serbest görsel layout kalıcılığı yok.
  Doğal dilde tüm müsaitlik cümleleri çözümlenmez; kullanıcı typed preview'de
  gün/saat/kısıtları düzenleyebilir. Bilinmeyen saat day-level plan olarak kalır.
- Otomatik internet kaynak araştırması, Anki indirme, Google Calendar push yok.
  Canlı cloud consent/Google OAuth akışı bu yerel denemede çalıştırılmadı;
  mevcut korumalar ve ilgili otomatik testler korunur.
- Tarayıcı sürecini yeniden başlatmak yerine page reload + persisted server
  conversation resume test edildi. Kişisel Chrome oturumu kapatılmadı.

## Kapanış ve temizlik

Görev için açılan Chrome sekmeleri kapatıldı; cihaz/reduced-motion emülasyonu ve
yakınlaştırma geri alındı. Vite 5174, izole API/backend/DB container'ları ve
`forkos-living-goals_default` ağı kaldırıldı. İki geçici `/tmp/forkos-living-*`
harness/wrapper dosyası silindi. Sentetik DB yalnız tmpfs içindeydi. Screenshot ve
log kanıtları `.codex/` altında, güvenlik dump'ı `backend/backups/` altında kaldı.
Normal 5173/8787/5433 uygulaması ve kişisel volume korundu.

Doğrulama tamamlandıktan sonra kullanıcı tüm mevcut değişiklikler için commit
ve push yetkisi verdi. Bu rapor da uygulama, test ve mimari dosyalarıyla aynı
commit içinde saklanır.
