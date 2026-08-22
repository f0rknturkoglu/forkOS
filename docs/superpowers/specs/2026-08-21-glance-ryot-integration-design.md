# Glance Tarzı Dashboard + Ryot Tarzı Medya Takibi

Tarih: 2026-08-21 · Durum: kullanıcı kararları onaylandi (Faz 1 ve Faz 2 tamamlandi)

## Referanslar ve yaklaşım

- **Glance** (glanceapp/glance, Go, AGPL-3.0): hafif, yapılandırılabilir dashboard.
  Widget kataloğu: RSS, Hacker News, Reddit, hava durumu, borsa, saat, takvim,
  todo, hızlı linkler, arama, sunucu istatistikleri, GitHub repo, monitor...
- **Ryot** (IgnisDa/ryot, Rust, GPL-3.0): medya takibi — film/dizi/anime/manga/
  kitap/oyun; durum, ilerleme, puan, inceleme, listeler, istatistikler.

**Yaklaşım (kullanıcı onayı):** Kod kopyalanmaz (Go/Rust + AGPL/GPL; yığınımız
Python+FastAPI+React). Özellik seti ve görsel dil yerel implemente edilir;
lisans temiz, mimari tutarlı kalır.

## Kararlar

| Konu | Karar |
|---|---|
| Dashboard yeri | Today sayfası Glance düzenine dönüştürülür (ayrı sayfa yok) |
| İlk widget paketi | Hava durumu (Open-Meteo, anahtarsız), RSS akışı, Saat+Tarih, Sunucu istatistikleri, Hızlı linkler + Arama |
| HN / Borsa | ilk pakette yok (sonra eklenebilir) |
| Medya kapsamı | Film/dizi/anime/manga/kitap: durum, ilerleme, puan 0-10, not/inceleme, listeler, istatistikler |
| Medya metadata | AniList + OpenLibrary (anahtarsız) + TMDB (kullanıcı key verecek) |
| Medya kısayolları | Letterboxd, RateYourMusic, AniList, MyAnimeList, Goodreads vb. dış site linkleri |
| Sıra | Faz 1: dashboard · Faz 2: medya |

## Faz 1 — Glance tarzı Today (uygulanıyor)

- Düzen: üstte kompakt istatistik şeridi + sütunlu duzen (today.columns ayarı,
  varsayılan 3; sıra today.widget_order). Bölge kavramı görselde sadeleşir.
  Ayarlar: satir sayisi + hava durumu konumu.
- Yeni widget'lar (src/modules/today/widgets/, registry'ye kayitli):
  - ClockWidget: buyuk dijital saat + Turkce tarih.
  - WeatherWidget: Open-Meteo (geocode + forecast, tarayicidan); konum ayardan.
  - RssPanelWidget: son 10 yazi + toplam okunmamis rozeti.
  - ServerStatsWidget: GET /api/system/stats -> RAM/CPU/disk barlari.
  - QuickLinksWidget: media.links + Cmd+K arama.
- Backend: GET /api/system/stats (system modulu, /proc tabanli, bagimlilik yok).

## Faz 2 — Medya modulu (tamamlandi)

- media modulu: media_item (entity-backed) — tur, durum, ilerleme, puan,
  not, tarihler, metadata jsonb, dis site linkleri.
- Metadata arama: OpenLibrary (kitap), AniList GraphQL (anime/manga),
  TMDB (film/dizi, kullanici key) — yalnizca inbound OKUMA.
- Istatistikler + liste/detay/form UI.

## Yapma

- Glance/Ryot kodunu kopyalama.
- Harici API'ye veri gonderme (aramalar inbound GET).
- Belgelenmis istisnalar disinda sema kurali ihlali yok (media_item entity-backed).
