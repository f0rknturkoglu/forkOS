# Design QA — Öğrenme özeti

- Source visual truth path: `conversation://browser-annotation/comment-1` (kullanıcının işaretlediği 1280 × 864 ekran görüntüsü)
- Implementation screenshot path: `/Users/furkanturkoglu/Desktop/Projeler/forkOS/design-qa-learning-summary.png`
- Responsive screenshot path: `/Users/furkanturkoglu/Desktop/Projeler/forkOS/design-qa-learning-summary-mobile.png`
- Source pixels: 1280 × 864
- Implementation pixels: 1270 × 714, desktop viewport override 1280 × 864, browser content inset 10 px, density 1×
- Responsive pixels: 380 × 822, mobile viewport override 390 × 844, browser content inset 10 px, density 1×
- State: `/learning`, `git/github` alanı seçili, özet açık, konu seçilmemiş

## Findings

P0/P1/P2 bulgu yok.

- Fonts and typography: Mevcut IBM Plex Sans / Newsreader hiyerarşisi korundu. Yüzde ve XP değerleri ürünün `numeral` ölçeğini kullanıyor; küçük etiketler mevcut `label-caps` ve `text-meta` adımlarında.
- Spacing and layout rhythm: Tam genişlikteki dört hücreli şerit kaldırıldı. Özet 20 rem sol sütuna taşındı, konu ağacıyla hizalandı ve sağdaki ayrıntı alanı yeniden yukarı taşındı. Masaüstü ve 390 px dar görünümde yatay taşma yok.
- Colors and visual tokens: Yalnızca semantik `surface`, `accent`, `ok`, `subtle`, `primary`, `secondary` ve `muted` tokenları kullanıldı. Kaynak görüntü koyu, doğrulama oturumu açık temadaydı; tema farkı kullanıcı durumundan kaynaklanıyor ve yerleşimi değiştirmiyor.
- Image quality and asset fidelity: Değiştirilen bölgede raster/görsel varlık yok. Chevron mevcut ürün ikon setinden geliyor.
- Copy and content: “Öğrenme seviyesi”, “XP ilerlemesi” ve konu/kaynak/odak alt değerleri, önceki dört metriğin anlamını daha sıkı bir hiyerarşide koruyor.

## Full-view comparison evidence

Kaynakta 104 px yüksekliğinde, sayfanın tamamına yayılan dört metrik hücresi bulunuyordu. Uygulamada bu alan kaldırıldı; aynı bilgi sol sütundaki tek kartta toplandı. Sağ ayrıntı yüzeyi kartın yanında başlıyor ve üstteki gereksiz dikey boşluk ortadan kalkıyor.

## Focused region comparison evidence

Özet kartı ayrı incelendi: alan adı ve yüzde kapalı durumda da görünür; XP bar 0–100 erişilebilir progressbar olarak sunulur; ikincil üç metrik açılır bölümde kalır. Kartın `<details>` kontrolü açık → kapalı → açık akışında çalıştı.

## Interaction and runtime checks

- Accordion toggle: passed.
- Desktop layout: passed.
- 390 px responsive layout: passed; document scroll width 380 px, inner width 390 px.
- Browser console errors: none.
- Focused component tests: 12 passed.
- Production build and bundle guard: passed.

## Comparison history

İlk karşılaştırmada P0/P1/P2 fark bulunmadı; ek düzeltme turu gerekmedi.

## Follow-up polish

Kalan P3 yok.

final result: passed

---

# Design QA — AFFiNE esinli Planla çalışma alanları

- Reference: `/Users/furkanturkoglu/Desktop/Projeler/forkOS/design-qa-affine-reference.jpg`
- Routes: `/todos`, `/habits`, `/planner`, `/calendar`, `/projects`, `/review/daily`, `/review/weekly`
- Browser viewport: 836 × 782 CSS px, açık tema

## Findings

P0/P1/P2 bulgu yok.

- Görevler/Rutinler: Durum, tür ve etiketler ortak workspace rail'inde; görev kompozisyonu, zaman grupları ve seçili entity bağlantıları aynı yüzeyde.
- Haftalık Plan: Planlanmamış işler üst/sol backlog'a ayrıldı, dönem başlığı ve hafta kontrolleri pane header'a taşındı. Geniş ekranda rail + board, dar ekranda kısa backlog + yatay kaydırılabilir hafta düzeni kullanılıyor.
- Planner accessibility: Drag/drop korunurken aynı iş klavyeyle de yapılabiliyor: backlog satırındaki planlama düğmesi görevi seçiyor, yedi gün başlığındaki erişilebilir düğmeler seçili görevi hedef güne yerleştiriyor.
- Takvim: Yinelenen sayfa başlığı ve ayrı toolbar kaldırıldı. Dönem, kayıt sayısı, Google sync, gezinme ve Ay/Hafta görünümü tek workspace header'da; takvim grid'i tek scroll yüzeyinde.
- Projeler: Üstte ayrı proje kartı yerine aynı workspace'in rail'i kullanılıyor. Seçili proje başlığı/statusu pane header'da; proje bilgisi, GitHub, kilometre taşları, görevler, günlük ve bağlantılar bağımsız ana scroll alanında.
- Review: Yapılanlar/yapılmayanlar, tamamlama, Pomodoro/odak, rutin, not, bookmark, RSS, GitHub ve fırsat sinyalleri üç aşamalı karar akışında kalıyor.

## Runtime and regression checks

- Takvim ay görünümü gerçek 20 etkinlikle açıldı; dönem gezinmesi, Ay/Hafta ve Google sync kontrolleri görünür.
- Planner gerçek 11 blok + 3 planlanmamış görevle açıldı; seç/deselect ve yedi güne yerleştirme kontrolleri tarayıcıda doğrulandı, mutation tetiklenmedi.
- Projeler gerçek forkOS verisiyle rail + çalışma alanı biçiminde açıldı; mevcut proje alt modülleri erişilebilirlik ağacında korundu.
- Focused component tests, TypeScript and design-system guard: passed.
- Full frontend suite: 484 passed.

final result: passed

---

# Design QA — Not bilgi mimarisi, zengin ekler ve second-brain grafı

- Reference: AFFiNE workspace/page-edgeless yaklaşımı ve Obsidian'ın klasör + tek renk graph davranışı
- Browser routes: `/notes`, `/notes?highlights=1`, `/graph`
- Verified viewport: 836 × 782 CSS px, açık tema, kalıcı uygulama sidebar'ı açık

## Findings

P0/P1/P2 bulgu yok.

- Information architecture: Notlar'ın ikinci sidebar'ı kaldırıldı. Bilgi Grafı, Yeni not, Vurgular, iç içe klasörler, kök notlar ve proje notları doğrudan ana sidebar'da Notlar'ın çocukları olarak görünüyor.
- Folders: Klasör oluşturma, yeniden adlandırma, silme, iç içe klasör ve notu sürükleyerek köke/klasöre taşıma gerçek API ve entity/event kurallarıyla çalışıyor. Klasör silindiğinde alt klasörler ve notlar güvenli biçimde bir üst seviyeye taşınıyor.
- Markdown blocks: Satır başındaki `/` menüsü başlık, todo kutusu, liste, tablo, alıntı, vurgu, kod, ayraç, medya ve yeni not eylemlerini filtreleyerek ekliyor. Tablolar hizalama bilgisiyle render ediliyor; `==metin==` vurguları semantik `mark` yüzeyi kullanıyor.
- Attachments: Resim, ses, video, PDF, ofis belgesi, metin, ZIP ve Excalidraw ekleri yerel note attachment API'sinden geliyor. Ses oynatıcı native kontrol görünümünü kullanmıyor; oynat/duraklat, süre, scrub, indir ve sil eylemleri forkOS yüzeyine sarıldı.
- Highlights: Bookmark `selection` kayıtları Vurgular panelinde kaynaklarıyla listeleniyor ve tek eylemle nota alıntı + highlight + kaynak bağlantısı olarak ekleniyor.
- Knowledge graph: Eski dış Section/Surface çerçevesi kaldırıldı. Graph çalışma alanını tamamen dolduruyor; düğüm ve bağlar nötr tek renk, fizik simülasyonu sakin, zoom/reset araçları ve durum metni yüzen ikincil yüzeyler. Not, görev, kaynak, öğrenme ve diğer entity düğümleri merkezi `entityRoute()` ile gerçek kayıtlarına gidiyor.
- Data-loss protection: Notlar arası geçişe ek olarak ana sidebar'dan Bilgi Grafı veya başka modüle geçiş de kirli taslakta onay istiyor. Canlı kontrolde iptal ve “değişiklikleri at” akışları doğrulandı; QA taslağı kaydedilmedi.

## Verification

- Live graph: 161 düğüm, 94 bağ; sürükleme/zoom/reset yüzeyi ve Notlar sidebar bağlamı görünür.
- Live notes: Slash tablo ekleme, Vurgular boş durumu ve özel ses kartı doğrulandı.
- Backend suite: 372 passed.
- Frontend suite: 482 passed.
- TypeScript, format, API contract, endpoint coverage, dead-export check, production/PWA build, bundle guard and dependency audit: passed.

final result: passed

---

# Design QA — AFFiNE esinli Yakala çalışma alanları

- Source visual truth path: `/Users/furkanturkoglu/Desktop/Projeler/forkOS/design-qa-affine-reference.jpg`
- Implementation evidence: `conversation://cua/inbox-workspace`, `conversation://cua/bookmarks-workspace`, `conversation://cua/documents-workspace`, `conversation://cua/rss-workspace`
- Verified viewport: 836 × 782 CSS px, açık tema, kalıcı uygulama sidebar'ı açık
- Routes: `/inbox`, `/bookmarks`, `/documents`, `/rss`

## Findings

P0/P1/P2 bulgu yok.

- Information architecture: Dört Yakala ekranı artık ayrı sayfa başlıkları ve dağınık kart yığınları yerine ortak bir çalışma alanı sözleşmesi kullanıyor. Sol rail görünüm/koleksiyon seçer, orta pane asıl işi taşır, gerekli olduğunda inspector bağlamı tamamlar.
- Inbox: Hızlı yakalama formu Bekleyenler pane başlığına alındı. Taşıma hedefleri ayrı inspector yüzeyinde; sürükleme, tıklama, ok tuşu ve sayı kısayolları korunuyor.
- Bookmarks: Koleksiyon, okuma durumu ve etiket filtreleri üstte üç kalabalık sıra olmak yerine tek sol rail içinde. Arama ile yalnız sık kullanılan Favoriler/RSS filtreleri içerik başlığında kaldı.
- Documents: Kategori seçimi ve yerel/Drive içe aktarma sol rail içinde. Belgeler tek listede; satır seçimi doğru `?focus=` bağlamını açıyor. Eski “Yerel Notlar” kopyası kaldırıldı; notların tek ana çalışma alanı `/notes`.
- RSS: Çalışan üç bölmeli okuyucu korunurken ölçüler ortak workspace tokenlarına bağlandı ve içerikteki yinelenen sayfa başlığı kaldırıldı.
- Responsive behavior: İlk tarayıcı turunda Yer İmleri rail'i 836 px görünümde listenin üstüne yığılıp ana içeriği aşağı itiyordu. Workspace eşiği `lg` yerine `md` olarak düzeltildi; ikinci turda rail ve liste aynı görünümde yan yana ve bağımsız scroll ile doğrulandı. Inspector dar görünümde alt sıraya, geniş görünümde üçüncü kolona geçiyor.
- Visual language: Seçimler nötr `surface-selected`, hover yüzeyleri `surface-hover`, ayraçlar `border-subtle`; yeni sabit renk, keyfi radius veya ham form elemanı eklenmedi.

## Interaction and runtime checks

- Gelen Kutusu hızlı yakalama ve taşıma mutation kontratları: passed.
- Yer İmleri arama, koleksiyon, okuma durumu, etiket ve kayıtlı görünüm akışları: passed.
- Belgeler kategori rail'i, yerel yükleme/Drive paneli, satır odağı ve dosya eylemleri: passed.
- RSS görünüm/feed/list/reader üçlüsü: browser passed.
- Tablet breakpoint düzeltmesi sonrası browser recapture: passed.
- Full frontend suite: 90 dosyada 476 test passed.
- Backend suite: 370 test passed.
- TypeScript, format, design-system guard, endpoint coverage, dead-export guard, production/PWA build ve bundle guard: passed.

## Comparison history

1. Mevcut dört ekran yeni sidebar içinde incelendi; içerik seviyesinde başlık ve filtre tekrarları belirlendi.
2. Ortak `Workspace`, rail, pane header, scroll area ve inspector primitive'leri uygulandı.
3. İlk 836 px Yer İmleri görüntüsünde rail'in tek kolon kaldığı görüldü.
4. Responsive grid eşiği düzeltildi, web container yeniden başlatıldı ve dört rota yeniden açıldı.

## Follow-up polish

- P3: Tam 1280 px masaüstünde üçüncü inspector kolonu, Codex paneli yeniden genişlediğinde ayrıca arşivlenebilir. Mevcut tablet ve alt-satır inspector davranışı gerçek tarayıcıda çalışıyor.

final result: passed

---

# Design QA — AFFiNE esinli uygulama kabuğu ve sidebar

- Source visual truth path: `/Users/furkanturkoglu/Desktop/Projeler/forkOS/design-qa-affine-reference.jpg`
- Previous forkOS baseline: `/Users/furkanturkoglu/Desktop/Projeler/forkOS/design-qa-shell-before.jpg`
- Implementation screenshot: `/Users/furkanturkoglu/Desktop/Projeler/forkOS/design-qa-shell-wide.jpg`
- Collapsed rail screenshot: `/Users/furkanturkoglu/Desktop/Projeler/forkOS/design-qa-shell-collapsed.jpg`
- Dark theme screenshot: `/Users/furkanturkoglu/Desktop/Projeler/forkOS/design-qa-shell-dark.jpg`
- Source size: 1280 × 720; implementation size: 1270 × 714 (in-app browser content inset)
- State: `/notes`, gerçek not ve proje günlüğü verileri, açık/koyu tema

## Findings

P0/P1/P2 bulgu yok.

- Information architecture: İki yatay navigasyon sırası kaldırıldı. Registry'den üretilen tek sidebar; Bugün, Yakala, Planla, Takip ve Sistem hiyerarşisini gösteriyor. Rutinler, Haftalık plan, Bilgi grafı ve Kaynaklar yalnız bilinçli çocuk rota olarak yer alıyor; Pomodoro ve değerlendirme hidden davranışını koruyor.
- Shell proportions: Kalıcı sol çalışma alanı, 52 px içerik başlığı, bağımsız içerik scroll'u ve sağ üst küresel araçlar AFFiNE referansındaki ana yerleşim mantığıyla eşleşiyor. forkOS'ta daha fazla birinci sınıf modül bulunduğu için sidebar referanstan daha yoğun; gruplar akordeon ve içerik alanı scroll edilebilir.
- Visual language: Workspace arka planı beyaza, sidebar çok hafif nötr yüzeye taşındı. Seçim dolu mavi kapsül yerine nötr seçili yüzey ve küçük vurgu noktası kullanıyor. Radius, yüzey ve sidebar ölçüleri tasarım tokenlarına bağlandı.
- Responsive behavior: Masaüstünde 248 px sidebar ve 56 px ikon rayı çalışıyor. 768 px altında sidebar off-canvas drawer ve scrim olur; daraltılmış masaüstü tercihi mobil etiketi gizlemiyor. Bu davranış component testiyle doğrulandı.
- Dark theme: Sidebar, seçili kayıt, workspace, uyarı ve kontrol katmanları koyu temada birbirinden ayrılıyor; sabit JSX rengi eklenmedi.
- Route fidelity: Mevcut hash rotaları ve query parametreleri korunuyor; aktif ikincil rota kendi grubunu otomatik açıyor.

## Full-view comparison evidence

AFFiNE All Docs ve forkOS Notlar aynı in-app browser karşılaştırma girdisinde açıldı. Her ikisinde de sol çalışma alanı sabit, içerik başlığı tek satır, ana yüzey sade ve ikincil araçlar sağda. AFFiNE'in doküman listesi yerine forkOS'un gerçek not editörü kullanıldığı için orta alan içerik yapısı bilinçli olarak farklı; karşılaştırmanın konusu kabuk, navigasyon oranı ve yüzey hiyerarşisidir.

## Interaction and runtime checks

- Sidebar expand → collapsed rail → expand: passed.
- Active module and active child route state: passed.
- Closed group auto-open for `/sources`: passed.
- Mobile scrim close callback: passed.
- Light/dark theme switch: passed in browser.
- Focused shell/navigation/design-system tests: 24 passed.
- Full frontend suite: 90 files, 477 tests passed.
- Production build, TypeScript and bundle guard: passed.
- Browser runtime: hata ekranı veya shell kaynaklı console-visible arıza gözlenmedi.

## Follow-up polish

- P3: Tam 390 px mobil ekran görüntüsü, in-app browser viewport değiştirme API'si sunulduğunda final responsive turunda eklenecek. Drawer davranışı ve erişilebilirlik şu anda DOM/component testiyle korunuyor.

final result: passed

---

# Design QA — Notlar tek sayfa Markdown çalışma alanı

- Source visual truth path: `/Users/furkanturkoglu/.codex/generated_images/01a057d5-055e-77b3-8e01-b0a16d79b173/exec-e83dcf3d-184e-4248-b073-2c4f910218c2.png`
- Additional product reference: `https://github.com/toeverything/AFFiNE`
- Implementation screenshot path: `/Users/furkanturkoglu/Desktop/Projeler/forkOS/design-qa-notes-edit.jpg`
- Render-state screenshot path: `/Users/furkanturkoglu/Desktop/Projeler/forkOS/design-qa-notes-preview.jpg`
- Source pixels: 1676 × 940
- Implementation pixels: 1270 × 714, density 1×
- Implementation viewport: 1270 × 714 CSS px; source and implementation have the same 1.78:1 aspect ratio, so no crop normalization was required.
- State: `/notes`, gerçek not seçili, açık tema; yazma, render ve Tuval durumları

## Findings

P0/P1/P2 bulgu yok.

- Information architecture: Sol ray aynı çalışma alanında iki ayrı yüzeye bölündü: “Kişisel notlar” ve “Proje notları”. Proje notu kendi proje adı ve günlük tarihiyle görünür; editör başlığındaki proje bağlantısı kaynağa geri götürür.
- Editor focus: Bölünmüş editör/önizleme kaldırıldı. Tek belge yüzeyi; `Yaz / Önizle / Tuval` görünüm anahtarı ve `Cmd/Ctrl+S` kaydı seçilen görsel yönle eşleşiyor. Son kullanılan Page/Tuval görünümü not bazında saklanıyor.
- Attachments: Görsel, ses dosyası, tarayıcıdan ses kaydı ve Excalidraw ekleri imleç konumuna Markdown olarak yerleşir. Metinde henüz bulunmayan eski ekler aynı yüzeyde “Ek havuzu” bölümünde erişilebilir kalır.
- Canvas: Tuval görünümü gerçek Excalidraw yüzeyini lazy-load eder. Çizimler, güvenli görünüm durumu ve yerel dosya verisi aynı notun `canvas_state` alanına gecikmeli otomatik kaydedilir; sayfa yenilemesinden sonra sahne geri yüklenir.
- Visual fidelity: Sol ray / ana belge oranı, sade tek renk araç şeridi, geniş yazı alanı, hafif sınırlar ve ürünün mevcut tipografi/tasarım tokenları korunmuştur. Kaynak görseldeki örnek içerik yerine gerçek kullanıcı verisi kullanıldığı için belge yoğunluğu doğal olarak daha düşüktür.
- Local privacy: Excalidraw'ın font varlıkları paket içinden `public/excalidraw-assets` altına kopyalanır; CDN kullanılmaz. Harici embed doğrulaması kapalıdır. Markdown görselleri yalnızca notun yerel ek meta verisiyle eşleştiğinde medya olarak yüklenir; harici görsel URL'leri otomatik çekilmez. Üretim bağımlılık denetimi 0 açık bulgu verdi.

## Full-view comparison evidence

Kaynak ve uygulama ekran görüntüleri aynı karşılaştırma girdisinde incelendi. İlk turda ana hiyerarşi eşleşti; son kullanıcı ek isteği üzerine sol ray, kişisel ve proje notlarını iki sınırlandırılmış konteynere ayıracak şekilde düzeltildi. Proje notu seçildiğinde bağlamın başlıkta ve liste satırında görünmesi doğrulandı.

## Focused region comparison evidence

Sol ray ve belge araç şeridi tam boy görüntüde okunabilir büyüklükteydi; ayrıca kırpılmış bir bölge gerekmiyordu. Kişisel/proje başlıkları, sayaçları, seçili satır yüzeyi, proje etiketi, tarih, ek araçları ve üç görünüm durumu ayrı ayrı erişilebilirlik ağacından doğrulandı. Tuvalde floating araç grubu, seçim aracı ve yakınlaştırma kontrolleri gerçek tarayıcıda görünür ve çalışır durumdaydı.

## Interaction and runtime checks

- Kişisel / proje notu ayrımı: passed.
- Markdown “Önizle → Düzenle” geçişi: passed.
- `Yaz / Önizle / Tuval` geçişi ve varsayılan görünüm saklama: passed.
- Tuvale şekil ekleme → otomatik kayıt → sayfa yenileme → sahneyi geri getirme: passed.
- Dar / Geniş / Tam belge genişliği tercihi: passed.
- Gerçek proje günlüğü notunun proje bağlantısı ve tarihi: passed.
- Focused frontend tests: 35 passed.
- Backend suite: 370 passed.
- Production build and bundle guard: passed.
- Full frontend suite: 90 dosyada 478 test geçti; önceki `flashcard_deck` registry hataları artık gözlenmiyor.
- Browser runtime: hata ekranı veya etkileşim kesintisi gözlenmedi.

## Comparison history

1. Seçilen tek-sayfa Markdown hedefiyle ilk uygulama karşılaştırıldı.
2. Kullanıcı isteğiyle proje notları ayrı sol-ray konteynerine taşındı ve proje bağlamı eklendi.
3. Yazma ve render durumları gerçek veriyle yeniden açılıp doğrulandı.
4. Tuval gerçek Excalidraw bileşenine geçirildi; ilk eski-sürüm entegrasyonundaki Vite runtime uyumsuzluğu güncel ESM sürümü ve yerel asset yolu ile giderildi.
5. Kalıcı sahne testi gerçek API ve tarayıcıda tamamlandı; test şekli sonrasında temizlendi.

## Follow-up polish

Kalan P3 yok.

final result: passed
# Paket 7 — Takip çalışma alanları

- Fırsatlar: arama, CRM, kaynak çekme ve görünüm seçimi tek çalışma başlığında; skor/CV/konum filtreleri içerikten ayrışan sakin yüzeylerde. İş alanı filtresi geri eklenmedi, çift yönlü skor kontrolü korundu ve belirsiz değerler anlamlı etiketlere dönüştürüldü.
- Öğrenme: XP özeti, alanlar ve konu ağacı sol çalışma rayında; seçili konu, kaynaklar, notlar ve bağlantılar sağ ana yüzeyde. Konu seçimi canlı veride doğrulandı.
- Bilgi grafı: Notlar bağlamında, çerçevesiz tam canvas, tek renk düğümler ve merkezi entity yönlendirmesi.
- Medya: Kütüphane/Koleksiyonlar/Yaklaşanlar/İstatistikler/Çöp ana sidebar'ın bağlamsal alt menüsünde; kütüphane metrikleri ve arama tek yüzeyde.
- Kartlar ve Finans: deck/görünüm rayları ile ana içerik ayrıldı; boş deck halinde gereksiz ray gösterilmiyor.
- Canlı kontrol: 836×782 açık tema; Öğrenme, Fırsatlar ve Medya gerçek yerel veriyle açıldı. Taşma, kırpılma veya kopuk ana eylem görülmedi.
- Otomatik kontrol: 93 test dosyası / 484 test, Prettier, TypeScript/build, API sözleşmesi, 0 referanssız endpoint, PWA/bundle bütçesi ve `npm audit` geçti.
