# Sinematik Medya Kütüphanesi Tasarımı

**Tarih:** 2026-08-25  
**Durum:** Kullanıcı tarafından onaylandı

## Amaç

Medya sayfasını küçük satırlardan ve tür seçicili aramadan çıkarıp Plex/Kodi
hissine yakın, büyük afişli ve sakin bir kütüphaneye dönüştürmek. Arama tek bir
composer üzerinden hem kullanıcının kütüphanesini hem de tüm hazır metadata
provider'larını tarar. İlerleme ve senkronizasyon arayüzü mevcut append-only
backend sözleşmelerine uygun, kompakt ve güvenilir olur.

## Kapsam

- Büyük, responsive 2:3 poster grid'i.
- Kompakt üst metrikler ve ortalanmış global arama composer'ı.
- Kütüphane eşleşmeleriyle tüm hazır provider kataloglarını birleştiren arama.
- Canonical provider renginde kaynak chip'leri.
- Tür bazlı dış bağlantılar için erişilebilir üç nokta menüsü.
- Kart üstünde hızlı `+1`; ayrıntıda kesin ilerleme, bitirme ve tur işlemleri.
- Provider/sync durumunu tek satır özetleyen, açılabilir log alanı.
- Mevcut medya sayfasının odaklı bileşenlere ayrılması.

Koleksiyon, çöp, upcoming ve istatistik özelliklerinin tam bilgi mimarisi bu
çalışmanın dışında kalır. Mevcut backend yetenekleri korunur; bu tasarım canlı
kütüphane, arama, detay, ilerleme ve kaynak görünümünü düzeltir.

## Bilgi Mimarisi ve Yerleşim

Sayfa sırası:

1. `Medya` başlığı ve aynı satırda dört küçük metrik: Toplam, Devam ediyor,
   Tamamlandı, Planlandı.
2. Sayfanın merkezinde geniş, tür seçicisiz global arama composer'ı.
3. Arama aktifken birleşik sonuç alanı:
   - önce `Kütüphanende`,
   - sonra `Katalog sonuçları`.
4. Arama kapalıyken kütüphane filtreleri ve büyük poster grid'i.
5. Tek satırlık kaynak/senkronizasyon özeti.

Poster grid'i mobilde iki, tablette üç veya dört, geniş masaüstünde yaklaşık beş
veya altı kolon kullanır. CSS `auto-fill/minmax` ile ekran genişliğine uyum
sağlar; sabit cihaz kırılımlarına bağımlı olmaz. Posterler gerçek 2:3 oranını
korur.

Kart yüzünde yalnızca poster, başlık, tür chip'i, provider chip'i, ilerleme
çubuğu ve uygulanabiliyorsa hızlı `+1` bulunur. Büyük kutu gölgeleri, gradient,
gereksiz açıklama ve sürekli görünür dış linkler kullanılmaz. Poster veya başlık
`/media/:id` detayına gider.

## Global Arama Sözleşmesi

Mevcut `/media/search?kind=...` endpoint'i geriye uyumluluk için korunur. Yeni
`GET /media/search/global?q=...` endpoint'i eklenir.

Global endpoint:

- hazır provider/kind çiftlerini paralel sorgular;
- yapılandırılmamış provider'ları çağırmaz;
- tek provider hatasında tüm isteği düşürmez;
- duplicate provider sonuçlarını canonical provider kimliğiyle ayıklar;
- her sonuçta zorunlu `kind`, `provider`, `provider_id`, `provider_ids`, başlık,
  kapak ve ilerleme ölçüsü döndürür;
- `results` yanında kullanıcıya gösterilebilir kısa `warnings` döndürür.

Frontend aynı arama terimiyle kütüphane endpoint'ini ve global katalog
endpoint'ini paralel çağırır. İki karakterden kısa sorguda dış katalog çağrısı
yapılmaz. Kütüphane eşleşmeleri üstte, provider sonuçları altta görünür.
Provider uyarıları sonuçları kapatmaz; sonuç alanının altında tek sakin bilgi
satırı olarak gösterilir.

Arama sonucundan ekleme, legacy `metadata` torbasıyla sınırlı kalmaz. İstek
`source: "provider"`, doğru `kind`, üst düzey `provider`, `provider_id`,
`provider_ids`, kapak ve ilerleme ölçüsü alanlarını taşır. Duplicate yanıtında
arayüz mevcut kayda giden `Kütüphanede aç` bağlantısını gösterir.

## Bileşen Sınırları

- `MediaSearchComposer`: debounce, kütüphane ve katalog sorguları, arama durumu.
- `MediaSearchResults`: iki sonuç grubunu ve partial warning satırını sunar.
- `MediaLibraryControls`: yalnızca kaydedilmiş kütüphane filtrelerini yönetir.
- `MediaPosterGrid`: responsive grid ve boş/yükleniyor/hata durumları.
- `MediaPosterCard`: poster, kimlik chip'leri, ilerleme ve hızlı aksiyon.
- `MediaActionsMenu`: tür-spesifik dış linkler ve ikincil kart eylemleri.
- `MediaProgressActions`: append-only tüketim komutları.
- `MediaSyncSummary`: kompakt provider sağlığı, tarama eylemi ve log disclosure.
- `MediaDetailPage`: kesin ilerleme, tamamla, yeni tur, puan ve not düzenleme.

`MediaPage` bu parçaları orkestre eder; provider link haritaları, kapak çözümü ve
durum adları `shared.tsx` gibi saf/test edilebilir yardımcı katmanda kalır.

## Kaynak Kimliği ve Renkler

Kaynak chip'i öncelikle `item.provider` veya arama sonucunun `provider` alanını
kullanır. Legacy kayıtlarda yalnız canonical alan yoksa `meta.source` fallback
olur. TMDB, AniList, Kitsu, OpenLibrary, Google Books, MusicBrainz, iTunes,
RAWG ve IGDB için mevcut tasarım token diline uygun, düşük doygunluklu renk
token'ları bulunur. Renk tek bilgi değildir; chip her zaman kaynak adını yazar.

Kapak çözüm sırası:

1. `cover_path` üzerinden local `/api/media/assets/...`,
2. `cover_url`,
3. legacy `meta.cover_url`,
4. başlığın ilk harfiyle nötr 2:3 placeholder.

## Tür Bazlı Dış Bağlantılar

Üç nokta menüsü yalnız ilgili türe ait bağlantıları gösterir:

| Tür | Bağlantılar |
| --- | --- |
| Film | TMDB, IMDb, Rotten Tomatoes, Letterboxd |
| Dizi | TMDB, IMDb, Rotten Tomatoes |
| Anime / Manga | AniList, MyAnimeList |
| Kitap | OpenLibrary, Goodreads |
| Sesli kitap | Audible, Apple Books |
| Podcast | Apple Podcasts, Spotify |
| Müzik | Apple Music/iTunes, MusicBrainz, RateYourMusic |
| Oyun | RAWG, HowLongToBeat |

Doğrudan provider kimliği varsa canonical detay URL'si, yoksa İngilizce orijinal
başlık tercih edilerek arama URL'si üretilir. Menü klavyeyle açılır; Escape,
dışarı tıklama ve öğe seçimiyle kapanır; açan kontrole odak geri döner.

## İlerleme ve Genel Loglama Hissi

Karttaki `+1`, `POST /media/{id}/consumptions` endpoint'ine `action: "quick"`
ile gider. Her yazma yeni `client_uuid` taşır. Kesin değer `set`, bitirme
`finish` komutuyla yazılır. İlerleme alanları PATCH edilmez. Başarılı mutasyon
kart, detay, istatistik, Today ve activity sorgularını yeniler.

Detay ekranı liste kutusu gibi sürekli açık bir form değildir. Mevcut durum ve
ilerleme önce okunur özet olarak görünür; `İlerlemeyi ayarla`, `Tamamla`, `Yeni
tur`, puan ve not gibi eylemler küçük, bağlamsal kontrol gruplarında açılır.
Offline durumda tüm yazmalar devre dışı kalır; mevcut veriler okunabilir kalır.

Kaynak/sync satırı varsayılan olarak şu özeti gösterir: kaynak sayısı, sağlıklı
kaynak sayısı ve son tarama zamanı. Sağda `Şimdi tara` ve disclosure kontrolü
bulunur. Açıldığında provider bazında durum, son tarama, bulunan öğe ve son hata
görünür. Yalnız hata/boş koşum varsa uyarı tonu kullanılır; normal durumda alan
nötr kalır.

## Hata, Boş ve Yüklenme Durumları

- Poster grid'i ölçüsünü koruyan skeleton'lar kullanır; layout zıplamaz.
- Kütüphane hatası retry eylemi sunar.
- Boş kütüphane global aramaya yönlendiren kısa bir metin gösterir.
- Global katalogda partial provider hatası mevcut sonuçları gizlemez.
- Hiç hazır provider yoksa Ayarlar'daki medya bağlantılarına yönlendirilir.
- Kapak hatası kartı bozmaz; placeholder'a düşer.
- Duplicate ekleme, hata toast'ı yerine mevcut kayda yönlendiren açıklama verir.
- Mutasyon başarısızlığında optimistic görüntü geri alınır ve kısa hata mesajı
  gösterilir.

## Erişilebilirlik ve Görsel Dil

- Büyük poster görsel hiyerarşinin ana öğesidir; renk yalnız semantik vurgu için
  kullanılır.
- Arama composer'ının görünür etiketi veya erişilebilir adı vardır.
- Chip'ler metin taşır; durum yalnız renkle anlatılmaz.
- Üç nokta menüsü doğru `aria-expanded`, menü rolleri ve focus yönetimine
  sahiptir.
- Kartın tamamı iç içe buton olmaz; başlık linki ile aksiyonlar ayrı odaklanır.
- Hareket yalnız opacity/transform ile kısa ve düşük yoğunluklu olur;
  `prefers-reduced-motion` dikkate alınır.
- Mevcut Newsreader ve IBM Plex Sans tipografisi ile sıcak nötr token'lar
  korunur; yeni icon paketi veya görsel bağımlılık eklenmez.

## Test Stratejisi

Backend testleri:

- global aramanın hazır provider'ları paralel çağırması;
- sonuçların `kind` ve canonical provider kimliği taşıması;
- partial provider hatasının başarılı sonuçları koruması;
- yapılandırılmamış provider'ın warning üretmesi;
- duplicate sonuç ayıklama ve mevcut tek-kind endpoint uyumluluğu.

Frontend testleri:

- kütüphane sonuçlarının katalogdan önce gösterilmesi;
- birleşik sonuçlarda tür/provider chip'leri;
- doğru provider create payload'ı ve duplicate yönlendirmesi;
- 2:3 poster grid'i ve kapak fallback sırası;
- tür bazlı dış link menüsü, klavye/Escape/focus davranışı;
- `quick`, `set`, `finish` komutlarının benzersiz `client_uuid` üretmesi;
- sync özetinin varsayılan kapalı ve hata durumunda açıklayıcı olması;
- offline yazmaların kapalı, okumaların açık kalması;
- loading, retry ve empty durumları.

Tam frontend/backend testleri, API schema üretim kontrolü, production build ve
çalışan container üzerinden tarayıcı doğrulaması tamamlanmadan iş bitmiş
sayılmaz.

## Kabul Kriterleri

- Arama alanında kategori seçimi bulunmaz ve tek sorgu tüm hazır katalogları
  tarar.
- Kütüphane eşleşmeleri global provider sonuçlarından önce görünür.
- Kütüphane görünümü küçük satırlar yerine büyük 2:3 poster grid'idir.
- Her kart türü ve canonical kaynağı metinli, marka renkli chip ile gösterir.
- Dış linkler kart yüzünü kirletmez; üç nokta menüsünde türe göre değişir.
- Kart `+1` ve detay ilerleme eylemleri append-only consumption API'sini doğru
  `client_uuid` ile kullanır.
- Üst metrikler kompakt, arama composer'ı ortalanmış ve görsel olarak baskın ama
  sade olur.
- Sync/log alanı varsayılan kompakt, açılabilir ve partial hataları anlaşılırdır.
- Offline read-only kuralı korunur; yeni harici veri gönderimi veya ağır frontend
  bağımlılığı eklenmez.
