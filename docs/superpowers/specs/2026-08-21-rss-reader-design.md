# RSS Okuyucu — NetNewsWire Tarzı Üç Bölmeli Tasarım

Tarih: 2026-08-21 · Durum: onaylandı (3 bölme, feed içeriği, import sonrası tazeleme, yer imi entegrasyonu, klavye)

## Amaç

forkOS'un RSS sayfasını basit bir "yazı listesi + genişlet" ekranından, NetNewsWire
benzeri **üç bölmeli** bir okura dönüştürmek: solda akıllı görünümler + kategori
klasörleri + feed'ler (okunmamış sayılarıyla), ortada yazı listesi, sağda içerik
okuma bölmesi. OPML import sonrası içeriğin hiç çekilmemesi sorunu da bu işte
çözülür: import sonrası anında arka plan çekimi + arayüzde "Tümünü tazele".

Her şey local-only kalır; yeni harici servis yok.

## Tespit edilen kök neden (OPML sorunu)

- OPML import yalnızca feed satırları yazar (add_feed, probe=False).
- Hiçbir şey çekim tetiklemez; worker 30 dk'da bir tur atar, catch-up yalnızca
  worker AÇILIŞINDA koşar.
- Sonuç: 207 feed last_fetched_at=NULL ile bekler, hiçbir source_run yok.
- Doğrulama: iki feed'i elle tazeledim → Hacker News 30, .NET Blog 10 yazı geldi;
  pipeline sağlamdır, sorun zamanlama/UX'tir.

## Kapsam

### Backend

1. **Migration 0019_rss_reader**: feed_item.content text kolonu.
   (content:encoded tam metin; özet listelerde kalır.)
2. **rss_source.py**: _content(entry) — önce content[0].value, yoksa summary;
   kapak 200.000 karakter.
3. **rss/service.py**:
   - ingest: content'i de yazar (raw.extra["content"]).
   - list_items: yeni filtreler saved_only (bookmark link'i var), since
     (Bugün görünümü); listede content dönmez (hafif).
   - get_item: content ile birlikte döner (okuma bölmesi burayı çağırır).
   - stats: today ve saved sayaçları ekler.
   - refresh_all(): due_feeds(interval_minutes=0) listesini 8 iş birlikte
     çeker; her feed kendi session'ında poll_feed. Worker'dan bağımsız.
4. **rss/router.py**:
   - GET /rss/items/{item_id} (content'li detay).
   - POST /rss/refresh-all → BackgroundTasks ile arka planda refresh_all.
   - OPML import başarılıysa aralarına aynı arka plan tazeleme görevi.
5. **bookmark**: liste endpoint'ine source filtresi (Bookmark.source == x)
   — "kaynak: RSS" chip'i için.

### Frontend (RssPage → üç bölme)

- **Sol kenar çubuğu**: Akıllı görünümler (Tüm Okunmamışlar, Bugün,
  Kaydedilenler, Tümü) sayaçlarıyla; altında kategori klasörleri
  (açılır/kapanır) ve feed satırları (okunmamış rozeti, pasif/hata durumu,
  hover'da tazele/çöp kutusu). En altta "Besleme ekle / OPML içeri aktar".
- **Orta panel — yazı listesi**: başlık (akıllı görünüm ya da feed adı), başlık
  çubuğunda "okunmamış/hepsi", "tümünü okundu işaretle", "Tümünü tazele".
  Satır: başlık (okunmamışsa koyu), feed adı, tarih, kaydedildi rozeti.
  Tıklanınca okuma bölmesinde açılır + otomatik okundu işaretlenir.
- **Sağ panel — okuma bölmesi**: toolbar (okundu/okunmadı, koleksiyon seç +
  "Yer işaretine kaydet", orijinalini aç), içerik HTML olarak (script/style
  temizlenmiş). İçerik yoksa özet + "Orijinalini aç".
- **Klavye**: j/k listede gez, Enter/U okundu değiştir, S kaydet (Read Later),
  ⇧+J bir sonraki okunmamışa atla.
- **Yer imi entegrasyonu**: okuma bölmesinden read_later/learning/...
  koleksiyonuna kaydet → saved_from link; Yer İmleri sayfasına "RSS" filtresi.

## Yapma (bu işte yapılmayacaklar)

- Tam metin için makale sayfası çekimi (kullanıcı "feed içeriği" seçti).
- Worker zamanlama değişikliği / APScheduler yapısına dokunma.
- event, entity, link şemasına dokunma.

## Doğrulama

- alembic upgrade head temiz; test_migrations yeni kolonu görür.
- pytest test_sources test_source_sync yeşil.
- tsc -b + vite build yeşil.
- Manuel: OPML import → yazılar otomatik gelir; "Tümünü tazele" çalışır;
  okuma bölmesinde içerik görünür; kaydet → Yer İmleri'nde "RSS" chip'i ile görünür.
