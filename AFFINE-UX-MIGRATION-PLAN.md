# forkOS — AFFiNE esinli arayüz ve çalışma alanı geçiş planı

Tarih: 2026-09-04  
Durum: Aktif uygulama — Paket 0–3 ve 5–7 tamamlandı; Edgeless son entegrasyonları ile Sistem paketi sürüyor  
Kapsam: Uygulama kabuğu, sol kenar çubuğu, bütün modüller, not belge yüzeyi, Edgeless/Excalidraw tuvali, responsive davranış ve kalite kapıları

## 1. Sonuç cümlesi

forkOS, veri modelini ve mevcut işlevlerini koruyarak iki yatay navigasyon satırından AFFiNE benzeri tek bir çalışma alanı kabuğuna geçecek. Masaüstünde kalıcı ve daraltılabilir sol kenar çubuğu; içerikte sade bir çalışma alanı başlığı; gerektiğinde açılan sağ denetçi; belge, liste, pano ve tuval için ortak yüzeyler kullanılacak. Notlar, Markdown'ı ana veri biçimi olarak tutacak; aynı not tek tıkla yazma, render ve Edgeless/Excalidraw görünümüne geçebilecek.

Bu bir AFFiNE kod kopyası veya BlockSuite göçü değildir. AFFiNE'in bilgi mimarisi ve etkileşim ilkeleri forkOS'un mevcut React/FastAPI/Postgres mimarisine uyarlanacaktır.

## 2. Kilitlenen ürün kararları

- Mevcut bütün URL'ler ve derin bağlantılar korunacak.
- Bütün modüller `src/modules/index.ts` ve `registerModule()` üzerinden kayıtlı kalacak; navigasyon için ikinci bir sabit liste oluşturulmayacak.
- Üstteki grup ve modül sekmelerinden oluşan iki satırlı ana navigasyon kaldırılacak; yerini tek sol kenar çubuğu alacak.
- Masaüstünde sidebar varsayılan olarak açık, tablette ray biçiminde, telefonda modal çekmece biçiminde olacak.
- “Bugün” ana çalışma merkezi olarak üstte sabit kalacak.
- Pomodoro ayrı ana navigasyon öğesi olmayacak; küresel yüzen yüzey olarak kalacak.
- Günlük ve haftalık değerlendirme ana sidebar'ı kalabalıklaştırmayacak; Bugün, komut menüsü ve ilgili bağlamsal bağlantılardan açılacak.
- Not gövdesinde Markdown tek kaynak olmaya devam edecek. Görsel tuval Markdown'ın yerine geçmeyecek; aynı nota bağlı ikinci bir görünüm olacak.
- Kişisel notlar ve proje notları aynı Notlar çalışma alanında, ayrı ve düzenli bölümlerde gösterilecek.
- Uygulama local-only kalacak. AFFiNE Cloud, ortak çalışma, telemetri, uzaktaki AI servisleri ve dış CDN eklenmeyecek.
- Renk yalnızca vurgu ve anlam taşıyan durumlarda kullanılacak. Navigasyon, bilgi grafı ve belge yüzeyleri nötr/tek renk ağırlıklı olacak.
- İlk aşamada mevcut IBM Plex Sans ve Newsreader yerel fontları korunacak; sırf benzer görünmek için uzaktan font indirilmesi yapılmayacak.

## 3. Referansın hangi tarafları alınacak

AFFiNE kaynakları ve canlı uygulaması şu tasarım kararlarını doğruluyor:

- Minimal ve dikkat dağıtmayan okuma/yazma yüzeyi.
- Yalnızca gerektiğinde görünen floating sidebar.
- Page ve Edgeless arasında aynı belge bağlamını koruyan geçiş.
- Mod değişse de sidebar, yardım ve temel araçların aynı yerde kalması.
- Belge özellikleri, geri bağlantılar ve sayfa genişliği gibi ikincil bilgilerin içerikten ayrılması.
- Sidebar veya belge listesinden sürükleyerek açılabilen split view.
- Tuvalde dosya eklerinin gömülü bir nesne gibi görüntülenmesi.
- Araçların sürekli büyük paneller halinde durması yerine bağlamsal ve yüzen sunulması.

Kaynaklar:

- AFFiNE ana depo ve ürün yaklaşımı: <https://github.com/toeverything/AFFiNE>
- Minimal arayüz, Block Hub ve Page/Edgeless tutarlılığı: <https://affine.pro/blog/affine-recap-uiux-introduction-for-new-collaborative-version>
- Floating sidebar, geri bağlantılar, sayfa genişliği ve belge modu: <https://affine.pro/blog/whats-new-affine-nov-update>
- Split view ve Edgeless dosya gömme: <https://affine.pro/blog/whats-new-feb-update>
- Excalidraw React API, `onChange`, tema ve özel element verisi: <https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/props/>

## 4. Mevcut durum özeti

### Güçlü taraflar

- Modül kaydı zaten merkezi ve sidebar üretmeye uygun.
- Entity rotaları merkezi kayıttan çözülüyor.
- Komut paleti, hızlı yakalama, bildirim paneli, tema ve küresel Pomodoro yüzeyi hazır.
- Tasarım tokenları ve temel UI bileşenleri var.
- Notlar Markdown, wikilink, etiket, backlink, kişisel/proje ayrımı, fotoğraf, ses ve Excalidraw eki destekliyor.
- Offline davranış açık: okuma serbest, yazma kapalı.

### Yapısal sorunlar

- Üstte iki navigasyon satırı içerik yüksekliğini azaltıyor ve grup/modül ayrımını gereğinden fazla görünür kılıyor.
- Her sayfa kendi toolbar, sekme ve filtre kompozisyonunu tekrar kuruyor.
- Liste ile ayrıntı arasındaki geçişler modüller arasında tutarsız; kimi yerde tam sayfa, kimi yerde kart içi ayrıntı kullanılıyor.
- Çok sayıda çerçeveli `Section` ve `Surface`, ana hiyerarşiyi düzleştiriyor.
- Dashboard, belge, liste, ayar ve tuval ekranlarının aynı `PageFrame` varsayımına sıkışması bazı sayfalarda gereksiz boşluk veya yoğunluk yaratıyor.
- Sidebar olmadığı için favoriler, son açılanlar, modül içi koleksiyonlar ve bağlam görünür değil.
- Notlar için temiz Markdown yüzeyi mevcut olsa da gerçek Edgeless düzenleme, canvas state ve belge/tuval birlikte görüntüleme henüz yok.

## 5. Hedef bilgi mimarisi

```text
forkOS çalışma alanı
├── Ara / Komut                         Ctrl/Cmd+K
├── Yeni                               hızlı yakalama menüsü
├── Bugün                              /
├── YAKALA
│   ├── Gelen Kutusu                   /inbox
│   ├── Yer İmleri                     /bookmarks
│   ├── RSS                            /rss
│   ├── Belgeler                       /documents
│   └── Notlar                         /notes
│       ├── Bilgi Grafı                /graph
│       ├── Vurgular                   bookmark selection kayıtları
│       ├── Klasörler                  dinamik not klasör ağacı
│       └── Proje Notları              projelerden gelen ortak notlar
├── PLANLA
│   ├── Görevler                       /todos
│   ├── Rutinler                       /habits
│   ├── Haftalık Plan                  /planner
│   ├── Takvim                         /calendar
│   └── Projeler                       /projects
├── TAKİP
│   ├── Fırsatlar                      /opportunities
│   ├── Öğrenme                        /learning
│   ├── Medya                          /media
│   ├── Kartlar                        /flashcard
│   └── Finans                         /finance
└── SİSTEM
    ├── Etkinlik                       /activity
    ├── İstatistikler                  /statistics
    ├── Sağlık                         /health
    ├── Kaynaklar                      /sources
    └── Ayarlar                        /settings
```

Hidden modüller:

- `/pomodoro`: rota uyumluluğu için kalır; normal kullanım küresel dock üzerinden olur.
- `/review/daily` ve `/review/weekly`: Bugün, komut paleti ve değerlendirme kartlarından açılır.
- `/day`: Etkinlik ve ısı haritasından açılan günlük ayrıntıdır.

Sidebar'a daha sonra “Favoriler” ve “Son açılanlar” eklenebilir; bunlar modül rotalarının kopyası olmayacak, entity kayıtlarından türetilen dinamik bölümler olacaktır.

## 6. Hedef uygulama kabuğu

### Masaüstü — 1280 px ve üzeri

- Sidebar genişliği: token ile yönetilen yaklaşık 248 px.
- Daraltılmış ray: yaklaşık 52–56 px; yalnızca ikonlar, tooltip ve aktif işaret görünür.
- Sidebar'ın sağında tek bir içerik sütunu.
- İçerik başlığı 48–56 px; breadcrumb, görünüm seçimi ve sayfa eylemleri burada.
- Sağ denetçi varsayılan kapalı; özellik, backlink, ek veya filtre ihtiyacında 304–360 px açılır.
- Belge içeriği `compact`, `wide`, `full` genişlik seçeneklerine sahip olur.
- Floating toolbar yalnızca seçim, canvas veya düzenleme bağlamında görünür.

### Tablet — 768–1279 px

- Sidebar ray olarak başlar, kullanıcı isterse overlay halinde genişletir.
- Sağ denetçi overlay drawer olur; içerik alanını kalıcı daraltmaz.
- İki panelli modüller tek panel + peek/inspector davranışına iner.

### Telefon — 0–767 px

- Sidebar modal drawer'dır.
- Çalışma alanı başlığında sidebar açma, sayfa başlığı ve birincil eylem kalır.
- Filtreler bottom sheet, denetçi tam ekran sheet olur.
- Tuval tam ekran açılır; Pomodoro dock ekran kenarına çarpmayacak safe-area kullanır.

### Kabuk hiyerarşisi

```text
App
└── AppShell
    ├── AppSidebar
    ├── Workspace
    │   ├── GlobalBannerStack
    │   ├── WorkspaceHeader
    │   └── RouteOutlet
    ├── InspectorHost
    ├── CommandPalette
    ├── CaptureDialog
    └── GlobalSurfaces
```

`AppHeader.tsx` geçiş sırasında uyumluluk bileşeni olarak tutulabilir; son aşamada üst navigasyon satırlarını üretmez ve yalnızca `WorkspaceHeader` yardımcılarına ayrılır.

## 7. Görsel sistem

### Yüzey katmanları

Yeni semantik katmanlar mevcut token sistemine eklenir:

| Token              | Kullanım                                |
| ------------------ | --------------------------------------- |
| `canvas`           | Uygulama arka planı                     |
| `sidebar`          | Sidebar arka planı                      |
| `surface`          | Ana içerik yüzeyi                       |
| `surface-sunken`   | Liste/filtre alt yüzeyi                 |
| `surface-raised`   | Floating toolbar, popover, context menu |
| `surface-selected` | Seçili liste satırı veya canvas nesnesi |
| `scrim`            | Drawer/modal arkası                     |

Kurallar:

- Çerçeve, her kutuyu ayırmak için değil gerçek sınır gerektiğinde kullanılır.
- Kart gölgesi sadece raised/floating katmanda kullanılır.
- Ana içerik beyaz/koyu yüzey üzerinde ferah kalır; arka plan farkı sidebar ve workspace ayrımını verir.
- Aktif sidebar öğesi renkli dolu kapsül yerine hafif nötr yüzey + ince vurgu kullanır.
- Durum renkleri sadece başarı, uyarı, hata, finansal yön ve zorunlu veri görselleştirmesinde kullanılır.
- Bilgi grafı düğümleri varsayılan olarak tek nötr renktir; hover, seçili ve komşu durumları ton farkıyla gösterilir.

### Tipografi

- Uygulama ve veri yüzeyleri: IBM Plex Sans.
- Uzun belge başlığı veya editoryal vurgu: mevcut Newsreader yalnızca gerektiğinde.
- Belge gövdesi rahat okuma satır yüksekliğiyle 16 px taban ölçeğini kullanır.
- Sidebar ve metadata küçük ama erişilebilir kalır; 12 px altına inilmez.
- Sayısal dashboard verileri tabular nums kullanır.

### Ölçü ve hareket

- Boyut, radius ve gölge yalnızca `index.css` + `tailwind.config.js` tokenlarından gelir.
- Kontrol yüksekliği mevcut 32/36/44 px ölçeğine oturur.
- Küçük yüzey radius'u 6–8 px, floating yüzey radius'u 10–12 px aralığında tokenlaştırılır.
- Sidebar açma/kapatma 160–220 ms; içerik kaydırmadan, `prefers-reduced-motion` uyumlu.
- Sürüklenen nesne için hafif yükselme/gölge; dekoratif sürekli animasyon yok.

## 8. Ortak frontend mimarisi

### Yeni temel bileşenler

Önerilen dizin:

```text
frontend/src/core/shell/
├── AppShell.tsx
├── AppSidebar.tsx
├── SidebarGroup.tsx
├── SidebarItem.tsx
├── SidebarFooter.tsx
├── WorkspaceHeader.tsx
├── ShellState.tsx
└── shellStorage.ts

frontend/src/core/workspace/
├── DocumentSurface.tsx
├── InspectorPanel.tsx
├── SplitPane.tsx
├── FloatingToolbar.tsx
├── ViewSwitcher.tsx
├── EntityPeek.tsx
├── PropertyList.tsx
└── WorkspaceEmpty.tsx
```

### Registry genişletmesi

`ModuleSpec` hard-coded sidebar verisi yaratmadan aşağıdaki opsiyonel bilgileri taşıyabilir:

```ts
navigation?: {
  order?: number;
  children?: { label: string; path: string; icon?: LucideIcon }[];
  compactLabel?: string;
}
```

- `group`, `hidden`, `routes` ve `icon` mevcut anlamını korur.
- Route listesi hem router hem sidebar çocuklarını üretir.
- Aynı rota/etiket iki yerde yazılmaz.
- Entity linkleri her zaman `entityRoute()` üzerinden açılır.

### Kabuk durumu

Yalnızca görünüm tercihi olan şu alanlar localStorage'da tutulabilir:

- sidebar açık/daraltılmış,
- kullanıcı seçmişse sidebar bölüm açık/kapalı durumu,
- son kullanılan belge genişliği,
- sağ denetçi açık/kapalı durumu.

İçerik, görev veya kullanıcı verisi localStorage'a taşınmaz. Bu tercihler için veritabanı migration'ı gerekmez.

### Ortak sayfa kalıpları

1. `dashboard`: Bugün, İstatistikler, Sağlık.
2. `master-detail`: Inbox, RSS, Öğrenme, Fırsatlar.
3. `collection`: Yer İmleri, Belgeler, Medya, Kartlar.
4. `database`: Görevler, Projeler, Finans.
5. `document`: Notlar, günlük ve haftalık değerlendirme, proje günlüğü.
6. `canvas`: Not Edgeless ve Bilgi Grafı.
7. `settings`: Ayarlar ve Kaynak Sağlığı.

Her modül bu kalıplardan birini kullanır; kendi başına yeni shell veya toolbar icat etmez.

## 9. Notlar — hedef deneyim

### 9.1 Ana görünüm

- Notlar için ikinci bir iç ray bulunmaz; klasörler, vurgular, bilgi grafı ve not kayıtları ana uygulama sidebar'ında Notlar'ın altında yaşar.
- Kişisel not klasörleri ile proje notları aynı ağaçta ayrı ve daraltılabilir konteynerlerdir.
- Proje notu satırında proje adı ve günlük tarihi görünür.
- Orta alan tek belge yüzeyidir.
- Sağ denetçi sekmeleri: `Bilgi`, `Bağlantılar`, `Ekler`.
- Üstte görünüm anahtarı: `Yaz`, `Render`, `Tuval`.
- `Yaz → Render` tek tıkla ve `Ctrl/Cmd+Shift+P` kısayoluyla geçer.
- `Ctrl/Cmd+S` açıkça kaydeder; otomatik kayıt ayrıca durum metniyle görünür.

### 9.2 Markdown belge yüzeyi

- Markdown gövde kanonik veridir.
- Başlık ilk anlamlı Markdown satırından türemeye devam eder.
- Wikilink ve etiketler mevcut parser ve backend senkronizasyonunu kullanır.
- Slash menüsü temel blok ekler: başlık, görev kutusu, liste, alıntı, kod, tablo, bağlantı, görsel, ses, çizim.
- Slash menüsü metni gizli bir özel formata çevirmeyecek; geçerli Markdown ekleyecek.
- Seçim toolbar'ı yalnızca metin seçiliyken görünür.
- Render sırasında dış görseller otomatik çekilmez; yalnızca yerel ek URL'leri medya olarak açılır.
- İleride blok tabanlı düzenleme istenirse bu, Markdown round-trip kaybı olmadan ayrı bir değerlendirme gerektirir.

### 9.3 Ekler

- Sürükle-bırak, dosya seçici ve ses kaydı korunur.
- Görsel, ses ve `.excalidraw` dosyaları aynı note attachment API'sine gider.
- Ekler sağ denetçide listelenir; imlece ekleme, indir, yeniden adlandır ve sil eylemleri olur.
- Canvas'a bırakılan görsel dosyası önce note attachment olarak kaydedilir; Excalidraw scene yalnızca attachment kimliğine referans verir.
- İlk sürüm mevcut 25 MB dosya sınırını ve JSON yedek uyumluluğunu korur.
- Büyük medya kullanımında JSONB büyümesi ölçülür. Ayrı bir asset tablosu/filesystem store ancak entity/support-table kuralı ayrıca karara bağlandıktan sonra açılır.

### 9.4 Edgeless/Excalidraw görünümü

Excalidraw bir lazy-loaded React bağımlılığı olarak entegre edilir. BlockSuite tümüyle alınmaz.

- Aynı `/notes?focus=<id>` rotasında görünüm `Tuval` olur; yeni rota zorunlu değildir.
- Scene, Note satırındaki `canvas_state` JSONB alanında saklanır.
- Notun ana Markdown içeriği canvas içinde düzenlenebilir bir belge kartı olarak temsil edilebilir; ilk iterasyonda kart Markdown preview gösterir ve tıklanınca Page görünümüne döner.
- Excalidraw `customData` içinde `entityId`, `entityType` ve `attachmentId` kullanılabilir.
- Bir entity düğümüne tıklama `entityRoute()` ile ilgili forkOS kaydını açar.
- `onChange(elements, appState, files)` değişiklikleri debounce ile yerel API'ye kaydeder.
- Tema forkOS theme tokenıyla kontrol edilir.
- `handleKeyboardGlobally` kapalı tutulur; uygulama kısayollarıyla çakışmaz.
- Harici embed varsayılan kapalıdır; izin verilecek hedefler yalnızca local URL ve note attachment URL'leridir.
- Excalidraw library market bağlantısı kapalıdır; dışarı veri veya istek gönderilmez.
- Import/export `.excalidraw` biçimini destekler.
- Tuval araçları alt-orta floating toolbar; zoom ve minimap sağ-alt; görünüm anahtarı üst başlıkta olur.
- Canvas değişikliklerinde “Kaydediliyor / Kaydedildi / Hata” durumu görünür.

### 9.5 Not veri modeli

Mevcut `note.id -> entity.id` kuralı değişmez. Aynı tabloda önerilen alanlar:

| Alan           | Tür          | Varsayılan | Amaç                                    |
| -------------- | ------------ | ---------- | --------------------------------------- |
| `canvas_state` | JSONB        | `{}`       | Excalidraw elements + güvenli app state |
| `default_view` | text + check | `page`     | Not yeniden açıldığında Page veya Tuval |
| `page_width`   | text + check | `compact`  | compact/wide/full belge genişliği       |

Migration elle yazılır; her DDL ayrı `op.execute()` kullanır. Service mutation'ları `touch_entity()` ve `log_event()` çağırır. Pydantic schema, OpenAPI ve frontend API tipi birlikte güncellenir.

### 9.6 Not kabul kriterleri

- Yeni ve mevcut Markdown notları veri kaybı olmadan açılır.
- Kişisel ve proje notları ayrı listelenir ama tek aramada bulunur.
- Proje notundan proje sayfasına; proje sayfasından aynı nota gidilir.
- Yaz/Render/Tuval arasında geçiş not kimliğini ve kaydırma bağlamını kaybetmez.
- Görsel ve ses Page görünümünde render olur; aynı dosya Tuval'e bırakılabilir.
- Canvas entity bağlantısı doğru module route'una gider.
- Offline iken not okunur, düzenleme kontrolleri kilitlenir ve kullanıcı nedenini görür.
- 25 MB sınırı hem UI hem API hata durumunda anlaşılır mesaj verir.
- Light/dark, masaüstü/tablet/mobil ve klavye akışları doğrulanır.

## 10. Modül bazlı geçiş matrisi

| Modül / rota                            | Hedef kalıp           | AFFiNE esinli değişim                                                                      | Korunacak davranış                                                           |
| --------------------------------------- | --------------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Bugün `/`                               | Dashboard + journal   | Sade günlük başlık, tek ritim özeti, plan akışı, ısı haritası; kart yoğunluğunu azalt      | Açık görevler, görev düzenlemeye yönlenme, 10–15 öğelik okuma akışı, heatmap |
| Gelen Kutusu `/inbox`                   | Master-detail         | Solda triage listesi, ortada içerik, sağda eylem/özellik denetçisi                         | Yakala, koleksiyona taşı, kaynak bağlantısı                                  |
| Yer İmleri `/bookmarks`                 | Collection            | All Docs benzeri tarih/koleksiyon gruplu liste, görünüm seçici, filtre drawer              | Inbox ve Bookmark aynı tablo/collection kuralı                               |
| RSS `/rss`                              | Üç panel okuyucu      | Feed sidebar, makale listesi, dikkat dağıtmayan okuyucu; paneller daraltılabilir           | Okundu, kaydet, tam metin, kaynak durumu                                     |
| Belgeler `/documents`                   | Collection            | Dosya türü/gün grupları, liste/grid, önizleme denetçisi                                    | Drive senkronu ve yerel cache davranışı                                      |
| Notlar `/notes`                         | Document + canvas     | Yaz/Render/Tuval, not rayı, property/backlink/ek denetçisi, floating araçlar               | Markdown, kişisel/proje konteynerleri, wikilink, ekler                       |
| Görevler `/todos`                       | Database              | Liste/board görünümü, filtre barı, sağ görev denetçisi                                     | Learning ve proje geri bağlantıları, rutin mantığı                           |
| Rutinler `/habits`                      | Database              | Günlük rutin şeridi ve tekrar planı denetçisi                                              | Tamamlanan rutinin aynı gün açık göreve geri dönmemesi                       |
| Haftalık Plan `/planner`                | Planner               | Sidebar bağlamı korunarak haftalık sütunlar, sürükle-bırak, görev peek                     | Plan slot ile due date ayrımı                                                |
| Takvim `/calendar`                      | Calendar              | Ay/hafta/gündem switch, sağ event denetçisi                                                | Google takvim ve plan slot entegrasyonu                                      |
| Projeler `/projects`                    | Collection + document | Proje listesi + proje workspace; genel bakış, görevler, günlük, notlar, dosyalar sekmeleri | Proje notlarının Notlar'da da görünmesi                                      |
| Fırsatlar `/opportunities`              | Database              | Sade kayıt listesi, skor range slider, saved views, sağ ilan denetçisi                     | Kaynak çekme, skor, durum, CRM; gereksiz iş alanı filtresi yok               |
| Öğrenme `/learning`, `/study`           | Master-detail         | Sol konu ağacı ve kompakt XP özeti, orta içerik, sağ kaynak/not denetçisi                  | Todo ↔ learning topic çift yönlü bağlantı                                    |
| Bilgi Grafı `/graph`                    | Canvas                | Tek renk, fizik motorlu sakin floating düğümler, seçili komşu vurgusu, inspector           | Node tıklayınca entityRoute ile gerçek kaydı açma                            |
| Medya `/media/*`                        | Collection            | Library sidebar, list/grid, koleksiyonlar, ayrıntı peek; görsel zenginlik içerikte kalır   | Kütüphane, yaklaşanlar, istatistik, çöp, detay rotaları                      |
| Kartlar `/flashcard`                    | Collection + focus    | Deck listesi, sağ deck bilgisi, tam odak çalışma modu                                      | Tekrar kuyruğu ve öğrenme ilişkisi                                           |
| Finans `/finance`                       | Database + dashboard  | Özet başlık, akış/abonelik tabları, satır denetçisi                                        | Gelir/gider/abonelik; semantik finans renkleri                               |
| Günlük değerlendirme `/review/daily`    | Document wizard       | Üç adımı aynı belge yüzeyinde progress rail ile sun                                        | Mevcut değerlendirme verisi ve olay kayıtları                                |
| Haftalık değerlendirme `/review/weekly` | Document report       | Yapılanlar/yapılmayanlar, Pomodoro, odak, görev, rutin, öğrenme ve medya özeti             | Tamamlama akışı, hafta seçimi                                                |
| Etkinlik `/activity`, `/day`            | Journal               | Tarih gruplu olay akışı + heatmap; gün ayrıntısı inspector/split                           | Append-only event görünümü                                                   |
| İstatistikler `/statistics`             | Dashboard             | Daha az kutu, ortak filtre, karşılaştırma ve trend bölümleri                               | Mevcut metrikler ve chart tokenları                                          |
| Sağlık `/health`                        | System dashboard      | Servis durum özeti, sorunları önceleyen sakin tablo                                        | API/DB/worker kontrolleri                                                    |
| Kaynaklar `/sources`                    | System list           | Kaynak sağlığı, son koşu ve hata ayrıntısı inspector                                       | 3 empty bildirimi ve source_run görünürlüğü                                  |
| Ayarlar `/settings`                     | Settings              | İç sol kategori navigasyonu, tek sütun formlar, sticky kaydet durumu                       | Mevcut tüm yerel ayarlar                                                     |
| Pomodoro                                | Global surface        | Sağ-alt dock, bağlam seçimi, kompakt/expanded/focus durumları                              | Sayfa değiştirmeden çalışma, mevcut context                                  |

## 11. Uygulama paketleri

Her paket tek başına test edilebilir ve geri alınabilir olmalıdır. Büyük tek commit yapılmayacaktır.

### Paket 0 — Baseline ve görsel sözleşme

Amaç: Geçiş sırasında mevcut davranışın kaybolmaması.

İşler:

- Kritik rotaların masaüstü ve mobil ekran görüntülerini sabitle.
- Mevcut route, module registry ve entity routing testlerini baseline olarak kaydet.
- Notlar için mevcut Yaz/Render, kişisel/proje listesi ve ek akışını referans kabul et.
- Tasarım QA belgesini yeni shell karşılaştırmaları için bölümlemeye hazırla.

Çıkış kriteri:

- Baseline build ve ilgili test sonuçları kaydedilmiş.
- Bilinen alakasız test hataları ayrı listelenmiş.

### Paket 1 — Tokenlar ve ortak çalışma alanı bileşenleri

Bağımlılık: Paket 0.

Değişecek ana dosyalar:

- `frontend/src/index.css`
- `frontend/tailwind.config.js`
- `frontend/src/core/ui.tsx`
- yeni `frontend/src/core/workspace/*`
- design system testleri

İşler:

- Sidebar, raised surface, selected surface, shadow ve motion tokenlarını ekle.
- `DocumentSurface`, `InspectorPanel`, `ViewSwitcher`, `FloatingToolbar` bileşenlerini oluştur.
- Mevcut Button/Input/Select/Range/FileInput kurallarını koru.
- Rastgele sabit renk, boyut ve radius kullanımını testle engelle.

Çıkış kriteri:

- Henüz navigasyon değişmeden yeni bileşenler izole testte çalışır.
- Light/dark kontrast ve focus görünümü geçer.

### Paket 2 — AppShell ve sidebar

Bağımlılık: Paket 1.

Değişecek ana dosyalar:

- `frontend/src/app/App.tsx`
- `frontend/src/core/AppHeader.tsx`
- `frontend/src/core/navigation.ts`
- `frontend/src/core/registry.ts`
- `frontend/src/core/types.ts`
- yeni `frontend/src/core/shell/*`

İşler:

- İki üst navigasyon satırını AppSidebar ile değiştir.
- Registry'den grup ve route çocukları üret.
- Workspace header'a arama, bildirim, tema ve sayfa eylemi slotlarını taşı.
- Offline ve source-health banner'larını workspace içine yerleştir.
- Desktop/tablet/mobile sidebar durumlarını uygula.
- Sidebar tercihini localStorage'da tut.

Çıkış kriteri:

- Bütün mevcut rotalar sidebar ve Ctrl/Cmd+K ile açılır.
- Browser back/forward ve hash query parametreleri bozulmaz.
- Daraltılmış/sidebar drawer durumları klavye ve ekran okuyucuyla kullanılabilir.

### Paket 3 — Not belge yüzeyi

Bağımlılık: Paket 2.

İşler:

- Mevcut NotesPage'i `DocumentSurface` ve `InspectorPanel` üzerine taşı.
- Kişisel/proje not konteynerlerini yeni note rail içine yerleştir.
- Yaz/Render görünüm anahtarını workspace header'a al.
- Bağlantı, backlink ve ekleri sağ denetçide birleştir.
- Slash ekleme menüsü ve seçim floating toolbar'ını Markdown üretecek biçimde ekle.
- Otomatik kayıt durumu ve unsaved guard ekle.

Çıkış kriteri:

- Mevcut note backend'i ve veri biçimi değişmeden tüm not akışları geçer.
- Uzun notlarda belge yüzeyi ve sidebar bağımsız doğru scroll eder.

### Paket 4 — Note Edgeless/Excalidraw

Bağımlılık: Paket 3.

İşler:

- Paketi eklemeden önce lisans, bundle ve local-privacy audit yap.
- `@excalidraw/excalidraw` lazy chunk olarak ekle.
- Note model/schema/service için `canvas_state`, `default_view`, `page_width` alanlarını ekle.
- Alembic migration'ı elle yaz; OpenAPI ve frontend API şemasını yenile.
- Attachment-to-canvas, entity node, import/export ve save state akışlarını ekle.
- Canvas ekranını forkOS tema, sidebar ve kısayollarıyla uyumlu hale getir.

Çıkış kriteri:

- Canvas açılmadığında Excalidraw ana bundle'a yüklenmez.
- Aynı not Page/Render/Tuval arasında veri kaybetmeden geçer.
- Yenileme sonrası scene birebir geri gelir.
- Dış ağ çağrısı oluşmaz.

### Paket 5 — Yakala modülleri

Bağımlılık: Paket 2; Notes için Paket 3.

Sıra: Inbox → RSS → Yer İmleri → Belgeler.

İşler:

- Master-detail ve collection kalıplarını gerçek verilerle doğrula.
- Filtreleri toolbar kalabalığı yerine drawer/popover'a taşı.
- Liste satırları, peek ve inspector davranışını standardize et.

Çıkış kriteri:

- Yakalama ve okuma iş akışlarında ekstra sayfa geçişi yok.
- Klavye triage ve selected-row durumları tutarlı.

### Paket 6 — Planlama modülleri

Bağımlılık: Paket 2 ve ortak workspace bileşenleri.

Sıra: Görevler/Rutinler → Haftalık Plan → Takvim → Projeler → Değerlendirme.

İşler:

- Görev sağ denetçisi ve ilişkili entity linklerini ortaklaştır.
- Plan slot, due date ve recurrence kavramlarını görsel olarak ayır.
- Proje workspace'inde günlük/not entegrasyonunu görünür kıl.
- Haftalık değerlendirmeyi tek, okunabilir rapor akışına taşı.

Çıkış kriteri:

- Learning todo, project todo, rutin ve Today akışı arasındaki bütün geri bağlantılar geçer.
- Drag/drop işlemleri klavye alternatifi sunar.

### Paket 7 — Takip modülleri

Bağımlılık: Paket 2.

Sıra: Fırsatlar → Öğrenme/Graph → Medya → Kartlar → Finans.

İşler:

- Fırsatlar ve Finans için ortak database/list header kullan.
- Öğrenme tree + detail yapısını yeni split/inspector kalıbına al.
- Bilgi grafını tek renk ve sakin fizik ayarlarıyla canvas kalıbına geçir.
- Medya görsellerini shell'den değil içerik verisinden türet.

Çıkış kriteri:

- Büyük kayıt listeleri ve graph düşük donanımda kullanılabilir kalır.
- Entity node ve kart linkleri doğru hedefi açar.

### Paket 8 — Sistem ve son bütünleştirme

Bağımlılık: Paket 2.

Sıra: Etkinlik → İstatistikler → Sağlık/Kaynaklar → Ayarlar.

İşler:

- Sistem sayfalarını aynı düşük yoğunluklu yapı ve iç sidebar ile birleştir.
- Tüm modüllerde ortak empty/loading/error/offline durumlarını uygula.
- Responsive, erişilebilirlik, performans ve görsel karşılaştırma turunu tamamla.
- Eski header ve kullanılmayan UI varyantlarını kaldır.

Çıkış kriteri:

- Eski iki satırlı navigasyon kodu ve ölü component varyantları kalmaz.
- Tam test/build/bundle kontrolü geçer.

## 12. Test ve doğrulama matrisi

### Otomatik testler

- Registry: bütün görünür modüller sidebar'da tam bir kez görünür.
- Routing: mevcut hash rotaları ve query parametreleri korunur.
- Entity routing: node, backlink, project note ve learning todo doğru route'a gider.
- Invalidation: mutation sonrası yalnızca `invalidateAfter()` kullanılır.
- Design system: ham form elemanı, sabit hex, keyfi px/radius eklenmez.
- Sidebar: aç/kapat, aktif öğe, grup toggle, mobil focus trap, Escape.
- Split view: aç, resize, kapat, route değişimi ve geri tuşu.
- Notes: create/update/pin/archive/delete, Yaz/Render, upload/delete/insert attachment.
- Canvas: initialData, debounce save, reload, import/export, attachment refs, invalid scene.
- Backend: migration sırası, entity FK, event append-only ve OpenAPI uyumu.

### Browser akışları

Her ana paket en az şu viewport'larda doğrulanır:

- 1440 × 900 masaüstü,
- 1024 × 768 tablet,
- 390 × 844 mobil,
- açık ve koyu tema.

Kritik yol:

1. Sidebar'dan modüle git.
2. Ctrl/Cmd+K ile aynı modülü aç.
3. Entity seç ve denetçiyi aç.
4. Geri/ileri ile bağlamı koru.
5. Offline duruma geç; veriyi oku, yazmanın kilitlendiğini gör.
6. Not oluştur, Markdown yaz, render et, ek yükle, Tuval'e geçir, yenile.
7. Proje notunu hem Projeler hem Notlar üzerinden aç.
8. Learning todo'dan konuya ve konudan göreve geri dön.
9. Pomodoro'yu bağlam seçerek herhangi bir sayfada başlat.

### Görsel QA

- AFFiNE referans görüntüsü ve forkOS uygulama görüntüsü aynı viewport/state ile yan yana karşılaştırılır.
- Kontrol başlıkları: shell oranı, sidebar yoğunluğu, içerik genişliği, boşluk ritmi, font ağırlığı, border/radius, floating gölge, responsive kırılım.
- Ekran görüntüsü tek başına “geçti” sayılmaz; kritik etkileşimler erişilebilirlik ağacı ve gerçek tıklamalarla doğrulanır.

## 13. Performans bütçesi

- App shell ilk yüklemede ağır editör veya canvas paketi içermez.
- Excalidraw yalnızca Tuval ilk açıldığında lazy-load edilir.
- Sidebar sayaçları için her modül ayrı sorgu başlatmaz; mevcut query cache veya toplu bir özet endpoint kullanılır.
- Note listesi attachment base64 verisini taşımamaya devam eder.
- 1.000+ kayıtlı listeler sanallaştırma ihtiyacı açısından ölçülür; ölçüm olmadan kütüphane eklenmez.
- Graph node sayısı için render limiti/LOD tanımlanır; seçili komşular önceliklendirilir.
- Bundle guard yeni chunk boyutlarını ayrı raporlar.

## 14. Erişilebilirlik ve klavye sözleşmesi

- Sidebar `nav`, gruplar açıklamalı başlık, aktif rota `aria-current=page` kullanır.
- Dar raydaki her ikon erişilebilir isim ve tooltip taşır.
- Floating toolbar odak sırasını çalmaz; seçim kaybolmadan klavyeyle erişilir.
- Canvas için görünür olmayan ama erişilebilir bir “scene öğeleri” listesi sağlanır; entity düğümleri oradan da açılabilir.
- Drag/drop işlemlerinin menü veya buton alternatifi vardır.
- Modal sidebar, drawer ve inspector focus trap + Escape uygular.
- Renk tek başına durum anlatmaz; ikon/metin/şekil eşlik eder.
- `prefers-reduced-motion` bütün shell ve canvas geçişlerinde uygulanır.

## 15. Local-only ve güvenlik sözleşmesi

- Yeni font, ikon, görsel, embed veya canvas library asset'i CDN'den yüklenmez.
- Excalidraw telemetry/collaboration/library URL davranışları kapatılır veya kullanılmaz.
- Harici iframe/embed varsayılan reddedilir.
- Markdown HTML ham olarak çalıştırılmaz; mevcut güvenli parser genişletilir.
- Attachment mime, boyut ve dosya adı backend'de doğrulanmaya devam eder.
- Canvas JSON'u Pydantic boyut ve şekil sınırlarıyla doğrulanır.
- Uygulama servisleri `127.0.0.1` binding kuralını korur.
- JSON backup, note body, attachment ve canvas state'i birlikte taşır; restore testi eklenir.

## 16. Riskler ve önlemler

| Risk                                                          | Etki   | Önlem                                                                           |
| ------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------- |
| Büyük kabuk değişimi tüm sayfaları aynı anda bozabilir        | Yüksek | Paket 1/2'yi route davranışından ayır; her paket sonrası route smoke test       |
| Sidebar için ikinci bir modül listesi oluşması                | Yüksek | Yalnızca registry'den üret; tutarlılık testi                                    |
| Excalidraw bundle'ı PWA'yı ağırlaştırabilir                   | Yüksek | Lazy chunk, bundle budget, önceden yükleme yok                                  |
| Canvas JSON çok büyüyebilir                                   | Orta   | Scene boyut sınırı, debounce, attachment binary'lerini scene'e gömmeme          |
| JSONB attachment yapısı çok medya ile DB'yi büyütebilir       | Orta   | Liste sorgusunda defer sürsün, ölçüm ve depolama eşiği; ayrı store kararı sonra |
| Page ve Canvas aynı içeriğin iki farklı kopyasına dönüşebilir | Yüksek | Markdown kanonik; canvas belge kartı yalnızca referans/preview                  |
| Modül içi toolbar'lar yeni header'la çakışabilir              | Orta   | Sayfa kalıpları ve `WorkspaceHeader` slot sözleşmesi                            |
| Mobilde sidebar + inspector + Pomodoro çakışabilir            | Orta   | Tek overlay yöneticisi, safe-area, z-index tokenları                            |
| D3 graph ve Excalidraw klavye olayları çakışabilir            | Orta   | Container-scoped keyboard handling ve focus testleri                            |
| Görsel benzerlik uğruna forkOS karakteri kaybolabilir         | Düşük  | Mevcut tipografi, Türkçe dil, local-only davranış ve semantik tokenlar korunur  |

## 17. Geri alma stratejisi

- Paket 1 yalnızca yeni token ve bileşen ekler; eski shell çalışmaya devam eder.
- Paket 2 shell'i değiştirir ama rotaları değiştirmez; eski `NavigationRows` bir geçiş commit'i boyunca tutulabilir.
- Modül paketleri birbirinden ayrı commit/PR olarak ilerler.
- Note migration'ındaki yeni alanlar nullable/default'lıdır; eski frontend bunları görmezden gelebilir.
- Canvas verisi Markdown gövdeyi değiştirmediği için Paket 4 geri alınsa bile not içeriği kaybolmaz.
- Veri silen migration veya otomatik dönüştürme yapılmaz.

## 18. Tamamlanma tanımı

Çalışma ancak aşağıdakilerin tamamı gerçekleştiğinde bitmiş sayılır:

- Bütün görünür modüller yeni sidebar'dan erişilebilir.
- Eski iki satırlı ana header kaldırılmış.
- Masaüstü, tablet ve mobil shell davranışları tamam.
- Ortak document/master-detail/collection/database/canvas/settings kalıpları gerçek modüllerde kullanılıyor.
- Notlar Yaz, Render ve Tuval görünümünde çalışıyor; ekler, proje notları, wikilink ve backlink korunuyor.
- Bilgi grafı tek renk ve node tıklaması doğru entity route'una gidiyor.
- Today, görev, rutin, learning, proje ve Pomodoro entegrasyonları regresyonsuz.
- Offline okuma/yazma kısıtı bütün yeni yüzeylerde açıkça uygulanıyor.
- Backend, frontend, registry, migration, API schema, bundle ve browser testleri geçiyor.
- Light/dark ve üç viewport için görsel QA kaydı var.
- Yeni harici ağ çağrısı veya telemetri yok.
- Kullanılmayan eski shell/component kodu temizlenmiş.

## 19. Uygulama sırası — kısa kontrol listesi

- [x] Paket 0: baseline ekranlar ve test sonuçları
- [x] Paket 1: tokenlar + workspace primitives
- [x] Paket 2: AppShell + responsive sidebar
- [x] Paket 3: Not belge yüzeyi
- [ ] Paket 4: Excalidraw/Edgeless
- [x] Paket 5: Inbox, RSS, Yer İmleri, Belgeler
- [x] Paket 6: Görevler, Rutinler, Planner, Takvim, Projeler, Review
- [x] Paket 7: Fırsatlar, Öğrenme, Graph, Medya, Kartlar, Finans
- [ ] Paket 8: Etkinlik, İstatistikler, Sağlık, Kaynaklar, Ayarlar
- [ ] Tam regresyon, görsel QA ve ölü kod temizliği

Güncel uygulama notu:

- Paket 3 tamamlandı: tek yüzeyli Markdown editörü, ana sidebar ile birleşik klasör/proje ağacı, sürükleyerek klasörleme, slash menüsü, GFM tablo, bookmark seçimlerinden Vurgular, zengin ek kartları, sayfa genişliği ve uygulama rotalarını da kapsayan kaydedilmemiş değişiklik koruması çalışıyor.
- Paket 4'ün veri modeli, migration, API kontratı, lazy-load Excalidraw, yerel font varlıkları, tema uyumu ve kalıcı sahne akışı çalışıyor. Attachment-to-canvas, entity kartı ve import/export akışları kaldığı için paket henüz kapatılmadı.
- Paket 5 tamamlandı: ortak rail/list/inspector çalışma alanı primitive'leri devrede. Gelen Kutusu, Yer İmleri ve Belgeler yeni yüzeye taşındı; RSS'nin çalışan üç bölmeli okuyucusu aynı ölçü tokenlarına bağlandı. Dört rota gerçek tarayıcıda açıldı, responsive eşik düzeltildi ve tam regresyon geçti.
- Paket 6 tamamlandı: Görevler/Rutinler ortak rail + liste + inspector yapısında; Haftalık Plan ayrı backlog ve sürükle/klavye planlama akışında; Takvim dönem odaklı tek çalışma yüzeyinde; Projeler proje rail'i ve bağımsız scroll eden çalışma alanında. Günlük/haftalık değerlendirme yapılanlar, yapılmayanlar, Pomodoro/odak ve diğer ritim metrikleriyle üç aşamalı belge akışını koruyor.
- Paket 7'nin Bilgi Grafı dilimi tamamlandı: rota Notlar bağlamına taşındı; tüm entity'ler tek renk, fizik motorlu, çerçevesiz tam ekran canvas üzerinde açılıyor ve düğüm tıklaması merkezi `entityRoute()` çözümünü kullanıyor.
- Paket 7 tamamlandı: Fırsatlar, Öğrenme, Medya, Kartlar ve Finans ortak `Workspace` yüzeylerine taşındı. Öğrenme XP özeti + alanlar + konu ağacını sol raya, konu içeriğini bağımsız ana yüzeye ayırıyor; Medya alt görünümleri ana sidebar altında; Fırsatlar'ın çift yönlü skor aralığı ve mevcut filtreleri korunuyor. 93 dosyada 484 frontend testi, API sözleşmesi, endpoint kapsamı, üretim/PWA/bundle derlemesi ve yüksek seviye bağımlılık denetimi geçti.
- Güncel doğrulama: backend 372 test, frontend 484 test, TypeScript, production/PWA build, bundle guard ve üretim bağımlılık denetimi geçti.

## 20. İlk uygulanacak dilim

İlk uygulama dilimi Paket 0 + Paket 1 + Paket 2 olmalıdır. Bunun nedeni sidebar ve çalışma alanı başlığının sonraki her modülün yerleşim sözleşmesini belirlemesidir. Not canvas'ına bundan önce başlamak, aynı yüzeyi yeni shell'e ikinci kez taşımaya ve gereksiz yeniden işçiliğe yol açar.

İlk dilimin somut çıktısı: gerçek verilerle çalışan, responsive ve daraltılabilir AFFiNE-esinli forkOS sidebar; sade workspace header; bütün mevcut rotalara erişim; mevcut sayfaların içerik davranışında değişiklik olmadan yeni kabuk içinde çalışması.
