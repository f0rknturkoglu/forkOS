# forkOS — U3 Pilot Screens

## 1. Executive Summary

U3, U2 kabuğu üzerinde üç günlük çalışma yüzeyini yeniden düzenler: Home/Today, Projeler ve Kariyer/Fırsatlar. Kapsam yalnızca frontend sunumudur. Backend, API sözleşmesi, veritabanı, kalıcı iş kuralları ve paket listesi değişmedi.

## 2. Ortak ilkeler

- Kullanıcının o ekrandaki birincil işi ilk bakışta görünürdür; ikincil bilgi aşağıya veya detay paneline taşınır.
- Modül registry kimlikleri, kayıt URL'leri, filtre ve görünüm tercihleri korunur.
- Geniş ekranlarda liste ile detay yan yana kalabilir. Dar ekranda detay çekmecesi kullanılır.
- Durum ve risk düz metinle de anlatılır; çok sayıda eşit ağırlıklı rozet ana listeyi doldurmaz.

## 3. Today

**Önce:** Büyük saat/hava/metrik bloğu ve eşit ağırlıklı üç sütun günlük planı geriye itiyordu.

**Kullanıcı işi:** “Şimdi ne yapacağım?” sorusuna yanıt bulmak, sonra dikkat isteyenleri ve bağlamı görmek.

**Yeni sıra:** Kısa kişisel selamlama ve mevcut hava → varsa “Şimdi” → günlük plan → dikkat isteyenler → kariyer/okuma/öğrenme gibi bağlam → küçük metrik özeti. Dikkat widget'ları veri olmadığında sütun bırakmaz. Plan satırı geniş ekranda okunabilir genişlikle sınırlıdır.

**Widget sözleşmesi:** Var olan widget ID'leri ve `core`/`defaultVisible` anlamı korunur. `TodayPlacement` artık `now | plan | attention | context`; çekirdek widget'lar `core`, isteğe bağlı widget'lar `placement` alanını kullanır. Gizleme, hazır düzen ve sıra tercihleri aynı registry üzerinden sürer. Ayarlarda sıra aynı bölge içindeki widget'lar arasında değiştirilebilir. Hava izni verilmediğinde konum çağrısı görünür kalır; dört günlük tahmin kısa hava özetinden açılır.

**Duyarlılık:** 1440 ve 1100 genişliklerinde ana plan ve dikkat alanı iki sütunlu hiyerarşiyi korur. Yaklaşık 850px dar masaüstünde yerleşim tek sütuna iner ve Şimdi → Plan → Dikkat → Bağlam DOM/okuma sırası korunur; yatay taşma yoktur. Dikkat widget'ları boş döndüğünde ayrılmış sütun gösterilmez.

## 4. Projects

**Önce:** Proje bilgisi, GitHub, kilometre taşları, görevler, Obsidian, geçmiş ve ilişkiler tek uzun akışta eşit öncelikteydi.

**Kullanıcı işi:** Seçili projenin sıradaki adımını görmek, işlerini yürütmek, gerektiğinde geçmişe ve meta veriye bakmak.

**Yeni model:** Sol proje rayı + seçili proje + isteğe bağlı inspector. Yerel sekmeler `Genel`, `İşler`, `Geçmiş`: Genel sıradaki adım, ilerleme ve bilgi notunu; İşler görev, kilometre taşı ve GitHub işlerini; Geçmiş aktivite ile günlük bağlantılarını gösterir. Obsidian notu hâlâ Vault'a ait kalır.

**Inspector:** Durum, GitHub deposu, proje bağlantısı, bağlı kayıtlar ve onay gerektiren silme eylemi buradadır. Yeni proje kısa modalde ad ve isteğe bağlı depo ile oluşturulur. `?focus=` seçimi korunur ve raydan seçim URL'yi günceller. Kayıt yok olduğunda ilk geçerli projeye dönülür.

**Duyarlılık:** 1440'ta üç panel; 1100'de ray + iş ve detay düğmesi; 850'de kısa proje listesi üstte, iş altında, detay Drawer'da. Rayın dar ekranda gereksiz yüksek alan kaplaması giderildi.

## 5. Opportunities

**Önce:** Her satırda birden çok skor, chip, kaynak sinyali ve işlem aynı anda gösteriliyordu; detay masaüstünde listeyi örten Drawer açıyordu.

**Kullanıcı işi:** Çok sayıda ilanı hızla karşılaştırmak ve seçili ilanı tarama bağlamını kaybetmeden incelemek.

**Yoğun liste:** Varsayılan satır kalite skoru/tür, başlık, kurum, konum/çalışma biçimi, yaş/son tarih, durum ve tek işlem menüsünü gösterir. Konum uyuşmazlığı ve kapalı kaynak gibi doğrudan önemli riskler kısa metin olarak kalır. Filtreleme kısayolları, kaydetme, dış bağlantı ve çöp işlemi satırın erişilebilir işlem menüsündedir. Grid kartları daha zengin kalır; Kanban ve mevcut filtre mantığı korunur. Çöp düğmesi filtre araç çubuğuna alınmıştır; aktif filtreler yalnızca varsa ikinci satırı oluşturur.

**Inspector:** 1280 ve üzerinde seçim, aynı `JobDetail`/`AnnouncementDetail` içeriğini sağdaki kalıcı olmayan panelde gösterir. Daha dar ekranda mevcut Drawer odak/Escape davranışı sürer. `?focus=`, görünüm ve filtre URL durumu korunur; açık grid/kanban tercihi zorla satıra dönüştürülmez.

**Duyarlılık:** 1440'ta liste ve seçili detay yan yana; 1100 ve 850'de liste tam genişlikte, detay Drawer'da. 850'de filtre araçları iki satıra kayar; yatay sayfa taşması yoktur. Grid ve Kanban geçişleri gerçek tarayıcıda kontrol edildi.

## 6. Ortak etkileşim modeli

Proje rayındaki kayıt seçimi `aria-pressed` ile anlatılır; kayıt seçimi sayfa gezinmesi gibi `aria-current="page"` kullanmaz. Proje rayında ve Fırsatlar satır başlıklarında yukarı/aşağı ok komşu kayda geçer. Enter, odaktaki kayıt düğmesini açar; durum geçişini veya silmeyi tetiklemez. Proje ve fırsat inspector'ları masaüstünde modal değildir ve odak tuzağı kurmaz. Dar ekran çekmeceleri mevcut `Drawer` odak yönetimini kullanır. Proje sekmeleri ortak `Tabs`, yerel eylemler `WorkspaceToolbar` üzerindedir.

## 7. Native macOS mapping

Sidebar → modül geçişi; proje rayı → kaynak listesi; orta panel → seçili iş; inspector → bağlamsal meta veri; Drawer → dar pencere geçici detayı. Bu eşleme, macOS üç bölmeli çalışma kalıbını web uygulamasının mevcut U2 `Workspace` primitive'leri ile ifade eder; platforma özel yeni API gerektirmez.

## 8. Erişilebilirlik

Sekmeler `role=tab` ve ok tuşu davranışını mevcut UI primitive'inden alır. Seçili proje ve fırsat düğmeleri seçim durumunu sunar. Inspector'da açık başlık ve kapatma/gizleme denetimi vardır. Fırsat işlem menüsü klavyeyle açılabilir ve Escape ile kapanır. Silme ve kalıcı silme mevcut onay diyaloglarını kullanır. Bilgi sırası dar ekranda da DOM sırasıdır.

## 9. Görsel doğrulama

Yerel Chromium render'ında gerçek kullanıcı verisiyle kontrol edildi; test/seed verisi yazılmadı.

| Ekran | Durum | Sonuç |
| --- | --- | --- |
| Today açık 1440 / 1100 / 850 | PASS | Plan ilk odakta, 850'de yatay taşma yok. |
| Today koyu 1440 | PASS WITH NOTE | Hiyerarşi korunuyor; ikincil metnin koyu tema kontrastı ortak token sisteminin konusu. |
| Projects açık 1440 / 1100 / 850 | PASS | Inspector 1440'ta yan panel, 850'de Drawer; dar ray yüksekliği düzeltildi. |
| Projects koyu 1440 | PASS | Seçim ve panel sınırları görünür. |
| Opportunities açık 1440 / 1100 / 850 | PASS | Liste yoğunluğu belirgin biçimde azaldı; inspector/Drawer geçişi çalışıyor. |
| Opportunities koyu 1440 | PASS WITH NOTE | Seçim görünür; ikincil metin kontrastı ortak tema tokenlarına bağlı. |
| Opportunities grid / Kanban | PASS | İki görünüm açılıyor ve kayıtlar görünüyor. |

## 10. Testler ve paket boyutu

Kapanış doğrulaması: `npm run format:check` PASS; `npm test` 161 dosya/1175 test PASS; `npm run api:check` PASS; endpoint coverage 1/3 eşiği PASS; dead export guard 3/10 eşiği PASS; `npm run build` içindeki TypeScript, üretim derlemesi ve bundle guard PASS; `npm audit --audit-level=moderate` 0 açık; `git diff --check` PASS. Entry chunk 467.67 KB ile 500 KB sınırının altında. Yeni runtime bağımlılığı, backend diff'i veya API şeması değişikliği yok.

## 11–13. Sonraki fazlara bırakılanlar

- **U4 — Dogfood & UX Validation:** Pilot ekranlar gerçek günlük kullanımda değerlendirilir. Sürtünme, hiyerarşi, etkileşim ve responsive sorunları kaydedilir; büyük geçişten önce pilot kalıplarının işe yaradığı doğrulanır.
- **U5 — Full UI Migration:** U0–U4'te doğrulanan kabuk, tasarım temeli ve pilot kalıpları kalan forkOS ekranlarına taşınır.
- **U6 — Performance & Cruft Sweep:** Eski UI kodu, uyumluluk parçaları, import/bundle borcu, gereksiz mount'lar ve genel frontend artıkları temizlenir. U3 kapsamında yeni bir uyumluluk katmanı eklenmedi.

U6 ertelenen notu: Projeler'de 1280px altında masaüstü inspector CSS ile gizlenirken bile component ağacında mounted kalabilir. Drawer açıldığında ikinci `ProjectInspector` örneği oluşabilir. React Query cache/dedup nedeniyle bu bir doğruluk engeli değildir; conditional mounting ve responsive inspector yaşam döngüsü U6'da performans ve cruft açısından değerlendirilebilir.

## U3 ✅ CLOSED

Pilot ekranlar U3 kapsamı ve kalite kapıları açısından kapatıldı. Sonraki ayrı görev U4 — Dogfood & UX Validation'dır.
