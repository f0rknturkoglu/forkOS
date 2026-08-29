# forkOS

Tek kullanicilik, **local-only** kisisel isletim sistemi.
Ayrintili yol haritasi: [`forkOS-PLAN.md`](forkOS-PLAN.md) · calisma kurallari: [`CLAUDE.md`](CLAUDE.md)

**Faz 0-7 tamamlandi** (entegrasyon + temizlik + tasarim teklestirme):
Browser Extension → Universal Inbox → Bookmark Library → RSS Reader → Today/Activity
→ Todo → Weekly Planner → Pomodoro → Rutinler → Daily/Weekly Review
→ Firsatlar → Calisma/Ogrenme → Dokuman/Takvim → Projeler → Finans → Ayarlar/Yedekleme.

Ayrica: moduller arasi baglar (`saved_from`, `belongs_to`, `application_step`,
`prepares_for`...), ilgili kayitlar paneli, her yerden yer imi kaydetme,
merkezi invalidation ve son-tarih saglayici sozlesmesi. Ayrinti:
[`docs/mimari.md`](docs/mimari.md) + [`forkOS-ENTEGRASYON-PLANI.md`](forkOS-ENTEGRASYON-PLANI.md).

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
| Modüller arası bağlar | Her detay sayfasında "İlgili kayıtlar" paneli; yer imi her yerden (`SaveToLibrary`); görev↔proje↔fırsat↔belge zinciri; medya koleksiyonları |
| Capture | `POST /api/capture` (idempotent), Universal Inbox, Bookmark Library, koleksiyonlar, etiketler, kayitli gorunumler |
| RSS | Feed CRUD, OPML import, conditional GET'li worker, okundu/kaydet akisi, `feed_item → bookmark` link'i |
| Frontend | Today (modullerden beslenen widget'lar), Inbox (dnd-kit surukle-birak), Bookmarks, RSS Reader, Activity, `Ctrl+K` command palette + global arama |
| Extension | MV3 popup, `Ctrl+Shift+S`, context menu, offline outbox + retry |
| Offline | PWA precache + `GET /api/**` StaleWhileRevalidate; yazma offline'da kapali (UI banner + disable) |
| Productivity | Todo/subtask, tekrarli rutinler, birlesik Gun akisi, 7 gunluk planner, sunucu tabanli Pomodoro, event tabanli review |
| Firsatlar | forkjob altyapisi ve LinkedIn scraper, OSYM duyurulari, YLSY burs ilanlari, gereksinim/todo/bildirim/deadline akisi |
| Ogrenme | Calisma oturumlari, konu/kurs/kitap takibi, alan bazli istatistikler |
| Dokuman ve takvim | Yerel dokumanlar, Google Drive metadata senkronu, Google Calendar salt-okunur ayna ve plan slotu gonderme |
| Projeler | Proje/milestone/todo baglantilari, GitHub contribution ve commit senkronu |
| Finans | Harcama ozeti, kategoriler, tekrarlayan odemeler ve deadline entegrasyonu |
| Sistem | DB tabanli ayarlar, gruplu global arama, JSON/CSV/Markdown/Netscape/OPML/ICS export ve gzip yedek |

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
GET  /api/today/agenda?day=2026-08-23        takvim + plan + gorev + RSS tek gun akisi
GET  /api/plan?week=2026-08-17                haftalik plan slotlari
GET  /api/pomodoro/active                     sekme kapansa da suren aktif session
GET  /api/reviews/preview?kind=weekly         event tabanli canli review ozeti
GET  /api/opportunities?kind=exam             OSYM sinav/duyurulari
GET  /api/opportunities?kind=scholarship      YLSY burs ilanlari
POST /api/sources/refresh                     secilen kaynaklari kalici worker kuyruguna al
GET  /api/sources/sync                        aktif batch, kaynaklar ve kesin ilerleme
GET  /api/search?q=&grouped=true              turune gore gruplanmis global arama
POST /api/backup                              yerel gzip yedek olustur
```

## Extension

`chrome://extensions` → Developer mode → **Load unpacked** → `extension/`.
Eklentinin **Ayrintilar → Uzanti secenekleri** ekranindan sunucu adresini ayarla;
varsayilan `http://127.0.0.1:8787/api`. Farkli Podman machine adresi girildiginde
yalnizca o origin icin Chromium izni istenir. Cikan extension ID'yi `.env` icindeki
`EXTENSION_ID`'ye yaz, `make down && make up` (CORS origin'i oradan uretilir).

Backend kapaliyken kaydedebilirsin: kayit `chrome.storage` outbox'ina yazilir,
rozet bekleyen sayisini gosterir, `chrome.alarms` her dakika + tarayici acilisinda
kuyrugu bosaltmayi dener. Kalici hatalar ayri listede gorulur; yeniden denebilir veya
temizlenebilir. `client_uuid` sayesinde retry cift kayit uretmez.

## Worker

- Feed basina `RSS_DEFAULT_INTERVAL_MINUTES` (varsayilan 30dk) + jitter
- **Conditional GET:** `ETag` / `If-Modified-Since` → 304'te hic parse edilmez
- **Catch-up:** worker acilista bekleyen tum aktif feed'leri hemen bir tur ceker
- Her kosum `source_run`'a yazar; ust uste 3 bos kosum → `source.stalled` event'i
- 5 ardisik hata → feed `active=false` + `rss.feed_disabled` event'i
- Her gece 04:00: okunmamis + kaydedilmemis item'lari `RSS_RETENTION_DAYS` sonrasi siler
- OSYM/YLSY ve is kaynaklari artimli dilimler halinde taranir; baslangicta tam forkjob senkronu yapilmaz
- Manuel toplu cekimler API prosesi icinde calismaz; kalici batch'e yazilir ve worker
  kaynaklari tek tek sahiplenir. Worker kapanirsa yarim kalan kosular zaman asimindan
  sonra yeniden denenir; ilerleme `/api/sources/sync`, heartbeat `/api/system/stats` ile izlenir.
- Kaynaklar kendi `interval_minutes` degerine gore calisir. LinkedIn otomatik turlara
  dahil edilmez; yalnizca acik secimle manuel calistirilir.
- Google Calendar 30 dakikada, GitHub 3 saatte bir yenilenir; yedek geceleri alinir

Uzun surecek tum is kaynagi senkronu yerine yukaridaki tek-kaynak refresh endpoint'lerini
kullan. Worker duruyken de OSYM ve YLSY arayuzden ayri ayri yenilenebilir.

Uyarilar Activity ekraninda ve her sayfanin ustundeki seritte gorunur --
"sessiz olum" kabul edilmez.

## Gunluk ritmi

Gunluk dongu: **Yakala → Ayristir → Bugune planla → Odaklan → Tamamla →
Degerlendir**. Butun akis local; disari veri gidmez.

- **Hizli yakala** (Ctrl+K → "Hizli yakala" ya da metni pencereye birak):
  ayni kutudan Gorev / Not / Baglanti. Metin otomatik cozumlenir ("yarin
  14:00 disciyi ara", "cuma projeyi gonder", "son tarih bugun rapor") --
  onerileri onaylamadan once duzenleyebilirsin (Faz 22/23).
- **Bugune al**: gorevi planlar, son tarih VERMEZ (plan != teslim). Tercih
  hatirlanir; butun giris noktalarinda aynidir (Faz 13/17).
- **Gunun ritmi** (Today): sabah ilk 3 planli is + ilk odak; gun icinde
  siradaki is + aktif pomodoro; aksam degerlendirme + acik planli
  gorevleri yarina tasi (Faz 25). Kapatmak istersen Ayarlar → Bugun
  widget'lari → gizle.
- **Yerel notlar**: Documents sayfasinda "Yerel Notlar" (Drive belgeleri
  metadata aynasi olarak yaninda durur); herhangi bir kayda baglanabilir
  ve o kaydin "Hakkında" panelinde gorunur (Faz 21).
- **Rutin gorevler**: tamamlaninca bir sonraki olusur (proje/milestone/
  tag kopyalanir, plan kopyalanmaz); "Rutini durdur" gelecekteki uretimi
  kapatir, gecmis Activity'de kalir (Faz 24).
- **Masaustu bildirimler**: yeni + yuksek onemli bildirimler OS bildirimi
  olur (izin Ayarlar'dan istenir). Tarayici tamamen kapaliyken bildirim
  gelmez -- garanti icin makine acik ve tarayici calisiyor olmali
  (Faz 26; macOS launchd tarifi `docs/mimari.md`'de).

Yedek: gunluk gzip + istege bagli Drive; secret ayarlar yedekten cikar.
`/backup/restore` "Birleştirerek içe aktar"dir (mevcut veriye dokunmaz);
tam geri donus `make disaster-restore` (Faz 15/16).

Local-only oldugu icin worker sadece makine acikken calisir.
Sabah `make up` → catch-up turu kacirilan her seyi tek seferde toplar.

## Test

```bash
make test                    # gecici forkos-test projesi + forkos_test DB
make verify                  # backend + frontend + extension + audit + build
```

Testler kisisel `lifeos` veritabanina baglanmayi reddeder; yalnizca adi `_test` ile
biten gecici veritabaninda calisir ve test bitince volume kaldirilir.
`tests/test_migrations.py` elle yazilan migration'lar ile modelleri karsilastirir --
kolon eklemeyi unutursan burada patlar.

Frontend API tipleri `backend/openapi.json` dosyasindan uretilir. Backend semasi
degisince `python scripts/export_openapi.py` ve `frontend/` icinde
`npm run api:generate` calistirilir; CI `npm run api:check` ile drift'i reddeder.
Sayfa rotalari lazy chunk'tir ve production build giris chunk'ini 500 KB ile sinirlar.

## Harici entegrasyonlar ve yedek

- Google OAuth icin `.env` dosyasina `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
  ve `GOOGLE_REDIRECT_URI` ekle. Baglanti yoksa Drive/Calendar ozellikleri sessizce
  devre disi kalir; yerel ozellikler calismaya devam eder.
- GitHub token'i Ayarlar ekranindan yerel DB'ye kaydedilir. Proje `owner/repo`
  bilgisiyle contribution ve son commitler cekilir.
- `make backup` PostgreSQL dump'i alir. `POST /api/backup` ise
  `backend/backups/` altinda 14 gun saklanan, export edilebilir gzip JSON yedegi uretir.
  `backup.drive_folder_id` ayarlanirsa ayni dosya Drive'a da yuklenir (gece 03:00'te
  otomatik; durum `GET /api/backup/status` ile izlenir).
- Makine tasima (macOS -> Windows): Drive'daki `lifeos-*.json.gz` dosyasini indir,
  yeni makinede `git clone` -> `.env` kopyala -> `make up && make migrate` ->
  **`POST /api/backup/restore`** (Ayarlar veya Saglik panelindeki "Geri yukle").
  Restore idempotent ve cakismasizdir: eksik kayitlar eklenir, var olanlara
  dokunulmaz; entity/link/event + tum modul tablolari + ayarlar + etiketler geri gelir.
  Yedek kapsami metadata'dan denetlenir ve round-trip test edilir. OAuth tokenlari
  bilerek yedeklenmez; yeni makinede "bagla" ile yeniden alinir.

## Saat dilimi ve offline yazma

Gun, review, takvim, rutin ve son-24-saat sinirlari backend'de yapilandirilmis
`Europe/Istanbul` saat diliminde hesaplanir. Tarayicinin UTC tarih kesmesi gun
secimlerinde kullanilmaz. PWA offline cache'i yalnizca okumadir: ortak API katmani
buton unutulsa bile mutation istegini fetch'ten once durdurur ve Turkce hata gosterir.

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
