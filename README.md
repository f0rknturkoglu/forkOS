# forkOS

Tek kullanicilik, **local-only** kisisel isletim sistemi.
Ayrintili yol haritasi: [`forkOS-PLAN.md`](forkOS-PLAN.md) · calisma kurallari: [`CLAUDE.md`](CLAUDE.md)

Su an **Faz 0-2** tamamlandi:
Browser Extension → Universal Inbox → Bookmark Library → RSS Reader → Today/Activity
→ Todo → Weekly Planner → Pomodoro → Habits → Daily/Weekly Review.

## Kurulum

```bash
cp .env.example .env
make up          # Docker kullaniyorsan: make up CO="docker compose"
make migrate
```

- API      → http://127.0.0.1:8787  (docs: `/docs`)
- Frontend → http://127.0.0.1:5173
- Postgres → 127.0.0.1:5433

`Makefile` varsayilan olarak `podman compose` cagirir. Docker icin ya her komuta
`CO="docker compose"` ekle ya da `export CO="docker compose"` yap.

## Ne var

| Alan | Icerik |
|---|---|
| Cekirdek | `entity` / `link` / `event` / `tag` / `saved_view` / `source_run`, global arama (FTS + trigram), activity log |
| Capture | `POST /api/capture` (idempotent), Universal Inbox, Bookmark Library, koleksiyonlar, etiketler, kayitli gorunumler |
| RSS | Feed CRUD, OPML import, conditional GET'li worker, okundu/kaydet akisi, `feed_item → bookmark` link'i |
| Frontend | Today (modullerden beslenen widget'lar), Inbox (dnd-kit surukle-birak), Bookmarks, RSS Reader, Activity, `Ctrl+K` command palette + global arama |
| Extension | MV3 popup, `Ctrl+Shift+S`, context menu, offline outbox + retry |
| Offline | PWA precache + `GET /api/**` StaleWhileRevalidate; yazma offline'da kapali (UI banner + disable) |
| Productivity | Todo/subtask, 7 gunluk planner, sunucu tabanli Pomodoro, habit grid, event tabanli review |

### Onemli endpoint'ler

```
GET  /health                                  modul listesi + durum
POST /api/capture                             extension/quick capture (client_uuid ile idempotent)
GET  /api/bookmarks?collection=&q=&tag=       liste + arama + filtre
PATCH /api/bookmarks/{id}/collection          surukle-birak buraya duser
GET  /api/bookmarks/stats                     Today kutucuklari
POST /api/rss/import                          OPML (multipart)
POST /api/rss/feeds/{id}/refresh              worker'i beklemeden tek feed cek
POST /api/rss/items/{id}/save                 item -> bookmark + 'saved_from' link
GET  /api/search?q=                           global arama
GET  /api/activity                            append-only event akisi
GET  /api/sources/health                      her kaynagin son kosumu
GET  /api/todos                               gorevler ve filtreler
GET  /api/plan?week=2026-08-17                haftalik plan slotlari
GET  /api/pomodoro/active                     sekme kapansa da suren aktif session
GET  /api/habits/grid?weeks=8                 habit isi haritasi
GET  /api/reviews/preview?kind=weekly         event tabanli canli review ozeti
```

## Extension

`chrome://extensions` → Developer mode → **Load unpacked** → `extension/`
Cikan ID'yi `.env` icindeki `EXTENSION_ID`'ye yaz, `make down && make up`
(CORS origin'i oradan uretilir).

Backend kapaliyken kaydedebilirsin: kayit `chrome.storage` outbox'ina yazilir,
rozet bekleyen sayisini gosterir, `chrome.alarms` her dakika + tarayici acilisinda
kuyrugu bosaltmayi dener. `client_uuid` sayesinde retry cift kayit uretmez.

## Worker

- Feed basina `RSS_DEFAULT_INTERVAL_MINUTES` (varsayilan 30dk) + jitter
- **Conditional GET:** `ETag` / `If-Modified-Since` → 304'te hic parse edilmez
- **Catch-up:** worker acilista bekleyen tum aktif feed'leri hemen bir tur ceker
- Her kosum `source_run`'a yazar; ust uste 3 bos kosum → `source.stalled` event'i
- 5 ardisik hata → feed `active=false` + `rss.feed_disabled` event'i
- Her gece 04:00: okunmamis + kaydedilmemis item'lari `RSS_RETENTION_DAYS` sonrasi siler

Uyarilar Activity ekraninda ve her sayfanin ustundeki seritte gorunur --
"sessiz olum" kabul edilmez.

## Gunluk ritmi

Local-only oldugu icin worker sadece makine acikken calisir.
Sabah `make up` → catch-up turu kacirilan her seyi tek seferde toplar.

## Test

```bash
make test                    # compose icinde: Postgres'li uctan uca testler dahil
```

DB'siz de calisir; `tests/test_api.py` Postgres yoksa kendini atlar.
`tests/test_migrations.py` elle yazilan migration'lar ile modelleri karsilastirir --
kolon eklemeyi unutursan burada patlar.

## Podman notlari

- Podman 4.7+ ile `podman compose` kullan (`podman-compose` degil).
- Postgres verisi **named volume**'da; rootless bind mount `initdb`'yi patlatir.
- Windows: `podman machine init && podman machine start` (WSL2 uzerinde calisir).
- SELinux'lu sistemlerde bind mount'larda `:z` sart (compose.yaml'da var).

### Podman machine (Windows/macOS) ile port erisimi

Podman machine kullanirken servisler bir VM'in icinde kosar ve
`127.0.0.1:PORT:PORT` yayini **VM'in loopback'ine** baglanir; host tarayicisi
oraya ulasamaz. Iki secenek var:

1. **Onerilen (tek seferlik):** user-mode networking ac, sonra her sey
   `127.0.0.1` uzerinden docker'daki gibi calisir.
   ```bash
   podman machine stop
   podman machine set --user-mode-networking
   podman machine start
   ```
2. `.env` icinde `BIND_ADDR=0.0.0.0` yap ve VM'in IP'sinden bagla
   (`podman machine ssh "ip -4 -o addr show eth0"`). VM NAT'li oldugu icin
   bu servisi LAN'a **acmaz** -- ama native Linux'ta `0.0.0.0` gercekten disari
   acar, orada `127.0.0.1` birak.

### HMR / hot reload

Container icinde inotify guvenilir calismiyor: dosyayi degistiriyorsun, Vite
hic tepki vermiyor. compose `WATCH_POLLING=1` gonderir, Vite polling'e gecer
(`vite.config.ts`). Native Linux'ta `WATCH_POLLING=0` ile CPU'yu geri alabilirsin.
Backend tarafinda uvicorn'un WatchFiles'i sorunsuz calisiyor, ayar gerekmiyor.
