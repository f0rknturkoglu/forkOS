# forkOS Global Glance UI Redesign

Tarih: 2026-08-21
Durum: kullanıcı tarafından onaylandı

## Amaç

forkOS'un bütün web arayüzünü aynı görsel dile taşımak. Dashboard, Glance'ın
yoğun fakat sakin bilgi yerleşimini temel alacak; diğer modül sayfaları da
tekrarlanan kart yığınları yerine bölüm başlıkları, ince ayraçlar, kompakt
satırlar ve anlamlı yüzeyler kullanacak.

Referanslar ilham ve bilgi mimarisi içindir. Glance veya Ryot kodu
kopyalanmayacak; mevcut React, Tailwind ve modül registry mimarisi korunacak.

## Mevcut durum ve problem

- `Panel` ve `Stat` bileşenleri hemen her içeriği ayrı çerçeveli karta
  dönüştürüyor. İçerik hiyerarşisi yerine çok sayıda eşit ağırlıklı kutu
  oluşuyor.
- Header bütün grup adlarını, modülleri ve araçları tek satıra yerleştiriyor.
  Modül sayısı arttığında navigasyon sağdaki araçlarla yarışıyor ve yatay
  kayıyor.
- Today sayfası üç sütuna geçmiş olsa da orta sütun yeniden iki kolonlu kart
  ızgarasına bölünüyor. Bu, Glance'taki geniş ana akış etkisini zayıflatıyor.
- Liste ağırlıklı sayfalar, ayarlar ve medya aynı `Panel` görünümünü tekrar
  ettiği için modüllerin içeriği farklı olsa da ekranlar kutu koleksiyonuna
  benziyor.

## Tasarım ilkeleri

1. **İçerik önce gelir.** Çerçeve, gölge ve yüzey yalnızca ilişkiyi gerçekten
   açıklıyorsa kullanılır.
2. **Başlıklar kutunun dışında durur.** Widget ve bölüm başlıkları küçük büyük
   harflerle, içerikten önce ve ince bir ayraçla gösterilir.
3. **Yoğunluk kontrollüdür.** Daha fazla veri aynı ekrana sığar; buna rağmen
   satır ritmi, klavye odağı ve kontrast korunur.
4. **Tek görsel dil, farklı içerik kalıpları.** Liste, planlama, ayar ve medya
   ekranları aynı tokenları kullanır fakat aynı yerleşime zorlanmaz.
5. **Responsive davranış tasarımın parçasıdır.** Masaüstü düzeni mobilde
   yalnızca daralmaz; önem sırasına göre yeniden akar.
6. **Modüler kayıt sistemi korunur.** Header, router, Today ve komut paleti
   modül adlarını yine registry'den alır.

## Uygulama kabuğu ve navigasyon

Header iki katmanlı olacak.

### Birinci satır

- Sol: forkOS işareti ve adı.
- Orta: `Bugün` bağlantısı ile `Yakala`, `Yap`, `Takip`, `Sistem` ana grup
  sekmeleri.
- Sağ: sunucu durumu, arama/komut paleti, bildirim ve tema kontrolü.
- Aktif grup mevcut rotanın sahibi olan modülden türetilir.
- Bir grup sekmesine tıklamak o grubun ilk etkin modülüne gider; `Bugün`
  doğrudan `/` rotasına gider.

### İkinci satır

- Aktif grubun bütün modüllerini gösterir.
- Bir modülün birden fazla rotası varsa ana modül bağlantısı görünür; alt
  rotalar ilgili sayfanın yerel sekmeleri olarak kalır.
- Geniş ekranda tek satırdır. Dar alanda yatay kaydırılabilir; sağ araçlarla
  aynı satırı paylaşmadığı için içerik itilmez.
- Aktif modül ince alt çizgi ve metin rengiyle belirtilir.

### Sunucu durumu

- Çerçeveli kare ikon butonu kaldırılır.
- Normal durumda 7-8 px yeşil nokta ve `yerel` etiketi gösterilir.
- Uyarı durumunda amber, kritik durumda kırmızı, veri yokken nötr gri olur.
- Dar ekranlarda yalnızca nokta kalabilir.
- Tıklama mevcut CPU, RAM, disk ve çalışma süresi popover'ını açar.
- Popover gerçek bir katman olduğu için yüzey, çerçeve ve gölge kullanmaya
  devam eder.

## Sayfa çerçevesi ve breakpoint'ler

- Ana içerik geniş ekranda yaklaşık `1600px` maksimum genişlikte ortalanır.
- Dış boşluk masaüstünde 24-32 px, tablette 20 px, mobilde 14-16 px olur.
- `>= 1280px`: Glance tipi üç kolon.
  `300px minmax(0, 1fr) 300px`.
- `768px - 1279px`: ana akış ve tek yan ray. Ana içerik önce, sol ve sağ
  widget'lar ikinci rayda kendi sıralarını korur.
- `< 768px`: tek kolon. Önem sırası özet, merkez, sol, sağdır.
- Sabit genişlikli çocuklar taşmayı zorlamaz; liste ve toolbar'lar kendi
  içinde kontrollü yatay kaydırma veya alt satıra geçme kullanır.

## Global görsel dil

### Renk ve tipografi

- Mevcut semantik renk tokenları ve açık/koyu tema korunur.
- Koyu temada Glance referansındaki nötr kömür yüzey ve sıcak, bastırılmış
  altın vurgu yaklaşımı güçlendirilir.
- Açık tema aynı hiyerarşiyi sıcak kağıt tonlarıyla sürdürür.
- Gövde metni IBM Plex Sans kalır. Sayısal göstergelerde mevcut serif/tabular
  rakam yaklaşımı korunur. Monospace yalnızca metadata, teknik değer ve kısa
  durum metinlerinde kullanılır; bütün arayüze uygulanmaz.

### Yüzey ve ayraçlar

- Normal bölüm ve widget'larda arka plan, yuvarlatılmış kart ve dış çerçeve
  varsayılan değildir.
- Bölüm başlığı içerikten önce gelir; başlık ile yardımcı bilgi arasında ince
  çizgi uzanabilir.
- Liste öğeleri ayrı kart olmak yerine yatay ayraçlı satırlardır.
- Hover durumu düşük kontrastlı yüzey değişimiyle gösterilir.
- Seçili satır, form, modal, popover, açılır liste ve sürükleme hedefleri
  anlamlı yüzey kullanmaya devam eder.
- Gölge yalnızca ekran üstü katmanlarda kullanılır.
- Küçük radius kontrollerde korunur; büyük, yumuşak dashboard kartları
  kullanılmaz.

## Ortak UI bileşenleri

Mevcut bileşenler tek seferde körlemesine değiştirilmek yerine açık
rollerle ayrılır.

- `PageFrame`: maksimum genişlik, responsive padding ve sayfa ritmi.
- `AppHeader`: iki katmanlı registry tabanlı navigasyon.
- `Section`: dış başlık, opsiyonel yardımcı metin/aksiyon ve borderless içerik.
- `Surface`: form, modal içeriği veya gerçek gruplama gereken yerler için
  çerçeveli yüzey.
- `MetricStrip`: kart olmayan, ince ayraçlarla ayrılan sayısal özetler.
- `RowList` / `DataRow`: kompakt, ayraçlı ve klavye odağı görünür liste.
- `Toolbar`: arama, filtre, sıralama ve ana eylemleri tek responsive şeritte
  toplar.
- `Panel`: geçiş sırasında uyumluluk için kalabilir; yeni varsayılan davranış
  `Section` olur. Gerekli yerler bilinçli olarak `Surface` kullanır.

Bu ayrım, global bir `Panel` CSS değişikliğinin formları ve karmaşık modülleri
tesadüfen bozmasını engeller.

## Today dashboard

### Masaüstü yerleşimi

| Sol ray (300px) | Ana akış (esnek) | Sağ ray (300px) |
|---|---|---|
| Takvim | Metrik özeti | Hava durumu |
| RSS | Görevler ve plan | Sunucu / sağlık |
| Okuma listesi | Fırsatlar ve son tarihler | GitHub |
|  | Etkinlik akışı | Hızlı erişim |
|  | Devam edilen medya |  |

- Registry'deki `left`, `center`, `right` slot sözleşmesi korunur.
- Orta alandaki `today.columns` ile oluşturulan iç içe kart ızgarası kaldırılır;
  ana akış tek, geniş içerik kolonu olur.
- `todayStats` ayrı kartlar yerine `MetricStrip` içinde gösterilir.
- Widget başlıkları kutu dışı `Section` başlığına dönüşür.
- Widget boşsa gereksiz büyük bir kart üretmez; ya gizlenir ya da kısa bir boş
  durum satırı gösterir.
- Yükleme ve hata durumları kararlı, kompakt yükseklik kullanır.

## Modül sayfası kalıpları

### Liste ve akış sayfaları

Gelen Kutusu, Yer İmleri, RSS, Fırsatlar ve Etkinlik:

- Üstte sayfa başlığı ve `MetricStrip`.
- Altında tek `Toolbar`.
- İçerik kartları yerine ayraçlı satırlar.
- Satırın birincil başlığı solda; metadata ve durumlar ikincil satırda;
  eylemler sağda veya satır açıldığında görünür.
- Mobilde metadata alt satıra iner, ikincil eylemler taşma menüsüne geçer.

### Planlama ve hiyerarşi sayfaları

Görevler, haftalık plan, takvim, projeler ve çalışma:

- Kolonlar yüzey gölgeleri yerine ince dikey/yatay sınırlarla ayrılır.
- Sürükleme ve seçili durumlar yüzey kullanabilir.
- Detay paneli dar ekranda kolon olmaktan çıkıp alt bölüme veya tam ekran
  katmana dönüşür.

### Ayar, sağlık ve form sayfaları

- Ayarlar anlamlı başlıklara bölünür; her ayar grubu ayrı büyük kart olmaz.
- Etiket ve kontrol iki kolonlu satır düzeni kullanır, mobilde üst üste gelir.
- Yedekleme, kaynak sağlığı ve entegrasyon durumları ayraçlı veri satırlarıdır.
- Tehlikeli eylemler ayrı ve belirgin bir bölümde kalır.

### Medya

Bu redesign içinde medya sayfası ortak forkOS diline geçirilir:

- Kart yığını yerine kompakt kapak + metadata satırları veya ekran genişliğine
  göre kontrollü kapak rafı.
- Tür ve durum filtreleri tek toolbar'da birleşir.
- Arama/ekleme alanı sürekli büyük bir kart olmak yerine açılabilir bir bölüm
  veya belirgin bir araç şeridi olur.
- İlerleme, puan ve durum aynı görsel hiyerarşide okunur.

Ryot'a daha derin benzetme ayrı takip fazıdır. O fazda kütüphane ana sayfası,
`devam edilenler`, yakın geçmiş, koleksiyonlar, istatistikler ve medya detay
akışı ayrıca tasarlanacaktır. Bu ayrım global redesign'ın kapsamını kontrol
altında tutar ve mevcut medya verisini riske atmaz.

## Etkileşim ve erişilebilirlik

- Bütün interaktif öğeler klavyeyle erişilebilir kalır.
- Aktif sekme `aria-current`, popover `aria-expanded`, ikon butonları anlamlı
  `aria-label` kullanır.
- Focus ring bütün temalarda görünür olur.
- Yalnız renkle anlam verilmez; sunucu durumu tooltip/popover metniyle
  desteklenir.
- Hareket yalnız kısa açılma/kapanma geçişlerinde kullanılır; dashboard
  widget'larına dekoratif animasyon eklenmez.

## Veri, backend ve hata davranışı

- Bu iş öncelikle frontend redesign'ıdır; veri modeli ve API sözleşmeleri
  değişmez.
- Mevcut sorgu anahtarları ve invalidation davranışı korunur.
- Offline durumda yazma kontrolleri devre dışı kalmaya devam eder.
- Kaynak hatası ve offline banner'ları header'ın altında, içerik genişliğini
  bozmayan tam satır bildirim olarak kalır.
- Widget hatası bütün dashboard'u düşürmez; ilgili bölüm kompakt hata satırı
  gösterir.

## Kapsam dışı

- Glance veya Ryot kodunu kopyalamak.
- Yeni backend modülü ya da migration eklemek.
- Widget sürükle-bırak editörü oluşturmak.
- Ryot'ın import ve otomatik takip entegrasyonlarını bu redesign'a eklemek.
- Mevcut commitlenmemiş backend/RSS/medya geliştirmelerini yeniden yazmak.

## Uygulama sırası

1. Tokenlar, `PageFrame`, `Section`, `Surface`, `MetricStrip`, `RowList` ve
   `Toolbar` temelleri.
2. İki katmanlı header ve minimalist sunucu durumu.
3. Today üç kolon yerleşimi ve widget dönüşümü.
4. Liste/akış modülleri.
5. Planlama/hiyerarşi modülleri.
6. Ayarlar, sağlık ve form modülleri.
7. Medya sayfasının ortak dile geçirilmesi.
8. Responsive, tema, klavye ve tüm rota doğrulaması.

## Doğrulama ölçütleri

- `frontend` TypeScript ve Vite build hatasız tamamlanır.
- Bütün etkin modüllere header üzerinden ulaşılır.
- Header 375, 768, 1024, 1280 ve 1600 px genişliklerde araçları içerik dışına
  itmez.
- Today 1280 px ve üstünde gerçek küçük/esnek/küçük kolon düzeni gösterir.
- Açık ve koyu tema bütün ana sayfa kalıplarında kontrol edilir.
- Offline, kaynak hatası, boş, yükleniyor ve hata durumları görsel olarak
  doğrulanır.
- Popover, modal, komut paleti ve bildirim panelinin katman sırası kontrol
  edilir.
- Mevcut commitlenmemiş kullanıcı değişiklikleri korunur; redesign commitleri
  yalnız ilgili frontend ve belge dosyalarını içerir.
