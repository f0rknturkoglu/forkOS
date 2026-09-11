# Mozilla Pocket Tarzi Yer Imleri ve Okuma Motoru (Pocket Engine) Tasarim Dokumani

Tarih: 2026-09-11  
Durum: Onay Bekliyor  
Konum: `docs/superpowers/specs/2026-09-11-bookmark-pocket-engine-design.md`

---

## 1. Amac ve Vizyon

forkOS Yer Imleri (Bookmarks / Kutuphane) modulunu basit bir "URL ve etiket dizini" olmaktan cikarip; harici sitelerin reklamlarindan, pop-up'larindan ve baglanti zorunlulugundan bagimsiz, yerel (local-only), dikkat dagitmayan bir **Mozilla Pocket tarzi okuma, arsivleme ve vurgulama motoruna** donusturmek.

### Temel Hedefler
1. **Dahili Okuma Deneyimi (Reader View):** Kullaniciyi harici sekmelere gondermeden, temizlenmis makale govdesini `@fontsource-variable/newsreader` (serif) veya sans-serif tipografi, ayarlanabilir punto ve genislik kontrolleriyle sunmak.
2. **Cevrimdisi Kalicilik ve Icerik Cikarimi:** `selectolax` tabanli yerel motorla makale HTML'ini, duz metnini, one cikan kapak gorselini (hero image), yazarini ve tahmini okuma suresini Postgres'te saklamak.
3. **Derinlemesine Arama:** Makale govde metnini `entity.search_text` uzerinden Turkce karakter duyarsiz (unaccent + simple config) tam metin ve trigram aramasiyla taranabilir kilmak.
4. **Coklu Metin Vurgulama (Highlights) ve Ikinci Beyin Baglari:** Okuma esnasinda secilen parcalari farkli renklerle vurgulamak, not eklemek ve tek tikla Flashcard veya Goreve (Todo) aktarmak.
5. **Magazin / Kart Izgarasi (Magazine Grid) ve Kompakt Liste:** Kapak gorselli, favicon'lu ve okuma sureli gorsel kart izgarasi ile seri taramalar icin kompakt liste secenegini sunmak.
6. **Ice / Disa Aktarim (Import/Export):** Standart Netscape Bookmark HTML ve Pocket JSON arsivlerini ice aktarma ve kisisel kutuphaneyi disa aktarma destegi.

---

## 2. Mimari Prensipler ve Kisitlar

- **Kural 1 & 2 (Entity Mimarisi):** Bookmark nesnesi `entity.id` PK/FK baglantisini korur. Varlik olusturma ve guncellemeleri `app/core/entity.py` helper'lari uzerinden yapilir.
- **Kural 3 (Append-Only Event):** Anlamli aksiyonlar (`bookmark.highlighted`, `bookmark.read`, `bookmark.scrolled`) `event` tablosuna append-only yazilir.
- **Kural 7 (Tek Tablo Birlikteligi):** Universal Inbox ve Bookmark Library ayni `bookmark` tablosunda kalir; ayrilma `collection` sutunuyla surdurulur.
- **Kural 10 (Alembic Migration):** Migration dosyasinda her DDL komutu ayri bir `op.execute()` cagirisi ile calistirilir (asyncpg prepared statement kisiti).
- **Kural 12 (Turkce Arama Standardi):** `to_tsvector('turkish', ...)` kullanilmaz; `'simple'` config + `immutable_unaccent()` + `pg_trgm` kullanilir.
- **Kural 15 (Tasarim Sistemi ve Sifir Emoji):** Ham form elemani, sabit hex ve metin boyutu yasaktir. Hicbir yerde emoji kullanilmaz.
- **Local-Only ve Gizlilik:** Hicbir veri dis sunuculara veya telemetri servislerine gonderilmez; ag istekleri yalnizca kullanicinin talep ettigi URL'in icerigini getirmekle sinirlidir.

---

## 3. Backend Mimarisi ve Veri Modeli

### 3.1. `bookmark` Tablosu Genisletmesi

Alembic migration (`0025_bookmark_pocket_engine.py`) ile mevcut `bookmark` tablosuna su sutunlar eklenir:
- `content_html`: Text, nullable=True (temizlenmis, reklamsiz makale HTML'i).
- `content_text`: Text, nullable=True (duz metin makale govdesi).
- `hero_image_url`: Text, nullable=True (one cikan kapak gorseli, og:image).
- `favicon_url`: Text, nullable=True (kaynak sitenin favicon baglantisi).
- `author`: String(128), nullable=True (yazar veya yayinci adi).
- `published_at`: DateTime(timezone=True), nullable=True (yayinlanma tarihi).
- `reading_time_min`: Integer, nullable=False, server_default="1" (tahmini okuma suresi).
- `word_count`: Integer, nullable=False, server_default="0" (toplam kelime sayisi).
- `scroll_progress`: Integer, nullable=False, server_default="0" (0-100 arasi kaydirma yuzdesi).

### 3.2. Yeni Destek Tablosu: `bookmark_highlight`

Makale ici coklu vurgulari saklamak icin destek tablosu (Kural 1 kapsaminda dokumante edilmis destek tablosu istisnasi):
- `id`: UUID, primary_key=True (varsayilan `uuid.uuid4`).
- `bookmark_id`: UUID, ForeignKey("bookmark.id", ondelete="CASCADE"), nullable=False, index=True.
- `text`: Text, nullable=False (vurgulanan metin).
- `note`: Text, nullable=True (vurguya ozel kullanici notu).
- `color`: String(16), nullable=False, server_default="yellow" ("yellow", "green", "blue", "pink").
- `anchor_index`: Integer, nullable=False, server_default="0" (metin ici siralama/konum belirteci).
- `created_at`: DateTime(timezone=True), nullable=False, server_default=func.now().

### 3.3. Ortak Readability Modulu (`app/core/readability.py`)

RSS ve Bookmark modullerinin paylasacagi merkezi icerik cikarici:
- `selectolax` parser'i ile HTML temizligi:
  - Silinen etiketler: `script, style, iframe, form, nav, footer, header, aside, noscript, svg, button`.
  - Cikarilan temel gorsel: `meta[property="og:image"]` veya ilk anlamli `img[src]`.
  - Yazar ve tarih: `meta[name="author"]`, `meta[property="article:author"]`, `time[datetime]`.
  - Govde tespiti: `article, [role="main"], [itemprop="articleBody"], main` veya en cok `<p>` iceren blok.
  - Kelime sayisi ve sure: `words = len(text.split())`, `reading_time_min = max(1, math.ceil(words / 200))`.
- Guvenli HTML temizligi: Yalnizca `http(s)` gorseller ve temel etiketler (`p, h1-h6, blockquote, pre, code, ul, ol, li, img, a, strong, em`) kalir.

### 3.4. Arama Indeksi Guncellemesi

`app/modules/bookmark/service.py`:
- `_search_text` fonksiyonuna `content_text`'in ilk 5000 karakteri dahil edilir.
- Bir yer imi kaydedildiginde veya govdesi zenginlestirildiginde `entity.search_text` otomatik guncellenir; boylece global komut paleti ve yer imi arama cubugu makalenin icindeki kelimeleri bulur.

### 3.5. Yeni ve Guncellenen API Uclari

- `GET /bookmarks/{id}/fulltext` -> Makalenin temiz HTML'ini, duz metnini ve vurgularini dondurur. Cache'te yoksa aninda arka planda `readability` ile cekip kaydeder.
- `PATCH /bookmarks/{id}/progress` -> `{"scroll_progress": 65}` guncellemesi yapar. Eger progress >= 90 ise ve unread ise, read_status otomatik "read" yapilir.
- `POST /bookmarks/{id}/highlights` -> Yeni metin vurgusu ekler (`text`, `note`, `color`, `anchor_index`).
- `DELETE /bookmarks/{id}/highlights/{highlight_id}` -> Belirtilen vurguyu siler.
- `POST /bookmarks/{id}/highlights/{highlight_id}/convert-to-flashcard` -> Vurguyu dogrudan bir flashcard'a donusturur (`front`: yazi basligi/alinti baglami, `back`: vurgulanan metin).
- `POST /bookmarks/import` -> Netscape Bookmark HTML veya Pocket JSON dosyasini topluca ice aktarir.
- `GET /bookmarks/export` -> Kutuphaneyi standart Netscape Bookmark HTML formatinda indirir.

---

## 4. Frontend Mimarisi ve Kullanici Deneyimi

### 4.1. Odak Okuma Modali (`BookmarkReaderModal.tsx`)

Kullanici bir karta veya listedeki basliga tikladiginda kütüphane baglamini kaybetmeden uzerine acilan dikkat dagitmayan okuma arayuzu:
- **Ust Arac Cubugu:**
  - Kapat (ESC veya x butonu).
  - Tipografi secimi: Newsreader (serif) / Sans font gecis dugmesi.
  - Punto ayarlayici: 3 kademe (Kucuk 16px, Normal 18px, Genis 20px).
  - Sutun genisligi: Standart (`max-w-2xl`) / Genis (`max-w-3xl`).
  - Okuma durumu: Okundu / Okunmadi toggle butonu.
  - Koleksiyon secici ve Arsivle butonu.
  - Orijinal sayfada ac baglantisi.
- **Makale Baslik Alani:**
  - Mecra favicon'u + domain adi.
  - Buyuk, net baslik.
  - Yazar bilgisi, yayinlanma tarihi, tahmini okuma suresi rozeti ("5 dk okuma").
  - Hero kapak gorseli (varsa ustte veya basligin hemen altinda).
- **Govde Alani:**
  - Temizlenmis, cizgili ve rahat okunan tipografi.
  - Metin ici secim araci (Floating Highlight Toolbar): Metin fareyle secildiginde ustunde beliren mini cubuk.
    - Sari, Yesil, Mavi, Pembe vurgu renkleri.
    - "Not Yaz": Vurgunun yanina kisisel dusunce ekleme.
    - "Karta Donustur": Flashcard yap.
    - "Gorev Yap": Todo yap.
- **Alt Ilerleme Takip Cubugu:**
  - Sayfa kaydirildikca dolan ince ilerleme gostergesi (% progress).

### 4.2. Magazin / Kart Izgarasi (`BookmarkCard.tsx` & `BookmarksPage.tsx`)

`BookmarksPage.tsx` bileseni guncellenerek iki ayri gorunum modu desteklenir:
- **Gorunum Modu Dugmesi:** Sag ust barda "Kart Izgarasi (Grid)" ve "Kompakt Liste (List)" secimi.
- **BookmarkCard Bileseni (Grid View):**
  - Orantili kapak gorseli (hero image), gorsel yoksa zarif bir tipografik mecra yer tutucusu.
  - Sol alt kosede favicon ve site domain'i.
  - 2 satirla sinirlandirilmis baslik.
  - 2 satirlik kisa ozet / aciklama.
  - Alt kosede "X dk okuma" rozeti, favori yildizi, koleksiyon etiketi ve okundu isareti.
  - Coklu secim icin sol ust kosede checkbox.

### 4.3. Today Dashboard Okuma Kuyrugu (`ReadingQueueWidget.tsx`)

- `read_later` koleksiyonundaki okunmamis yazilari siralar.
- Artik sadece dis link acmaz; basliga tiklandiginda dogrudan `BookmarkReaderModal` icinde acar.
- Her satirin yaninda tahmini okuma suresi ("4 dk") ve baslanmissa yuzdesi ("%40") gorunur.

---

## 5. Tarayici Eklentisi (Extension) Gelistirmesi

`extension/extractor.js` ve `extension/popup/popup.js`:
- `collectPageDom` ve `extractPageMetadata` tarafindan cikarilan `og:image`, `readingTimeMinutes`, `favicon` ve `author` alanlari capture sirasinda sunucuya gonderilir.
- Sunucu boylece ek bir ag istegi atmadan, sayfanin o anki gorselini ve meta verisini ilk kayit aninda alir.

---

## 6. Test ve Dogrulama Plani

1. **Alembic ve Model Testleri:**
   - `tests/test_migrations.py`: Tek SQL per op.execute kuralinin, view olmamasinin ve FK baglantilarinin kontrolu.
   - `test_bookmark_pocket_engine.py`: Yeni kolonlarin, highlight tablosunun, cascade silme kurallarinin ve `readability` cikariminin testi.
2. **Frontend Testleri:**
   - `BookmarkReaderModal.test.tsx`: Modal acilisi, font degisimi, metin vurgulama, scroll event'leri ve Flashcard'a donusturme testleri.
   - `BookmarksPage.test.tsx`: Grid ve List modlari arasinda gecis, bulk action cubugu ve filtrelerin testi.
   - `designSystem.test.ts` ve `invalidation.test.ts`: Sifir ham eleman, token uyumu ve cache temizleme denetimleri.
3. **Sifir Emoji Denetimi:**
   - Tum kod, arayuz etiketleri ve test dosyalarinda sifir emoji kuralinin statik olarak dogrulanmasi.
