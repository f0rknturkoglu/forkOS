# Task 3 Report — Provider, artwork ve media sync

## RED kanıtı

- Provider/artwork testleri önce eklendi. İlk odak koşu, üretim modülleri henüz
  olmadığı için `ModuleNotFoundError: app.modules.media.providers` ve
  `ModuleNotFoundError: app.modules.media.artwork` ile RED oldu.
- Worker testleri önce `poll_media_source`/`poll_media_sources` bulunmadığı için
  collection RED verdi.
- Başarılı fakat değişikliksiz provider snapshot testi ilk koşuda
  `['ok', 'empty'] != ['ok', 'ok']` ile RED oldu; health sinyali değişiklikten
  ayrıldı.
- Beklenmedik boş snapshot testi ilk koşuda `media.sync_empty` yerine
  `media.sync_failed` üretildiğini göstererek RED oldu.
- Google Books fallback kimliğinin sonraki sync'i için test önce
  `ImportError: GoogleBooksProvider` ile RED oldu.

## Uygulama özeti

- Ortak provider dataclass/Protocol sözleşmesi ve registry eklendi. Dokuz kind;
  TMDB, AniList, OpenLibrary + yalnız sıfır sonuçta Google Books fallback,
  MusicBrainz + Cover Art Archive, iTunes discovery + publisher RSS ve
  Twitch client-credentials kullanan IGDB implementasyonlarına bağlandı.
- `/media/search` registry üzerinden normalize/dedup sonuç döndürüyor;
  `/media/providers` readiness, capability, missing setting ve son run health'i
  sunuyor. Eski HTTP kodu domain servisinden çıkarıldı.
- Artwork cache JPEG/PNG/WebP, 8 MB stream sınırı, SHA256 ad, temp + atomic
  replace ve traversal korumasıyla eklendi. Cache edilen yollar
  `/api/media/assets/{name}` üzerinden immutable cache header'larıyla sunuluyor;
  iTunes promo policy'si kapalı, RSS publisher artwork istisnası açık.
- Source sync orchestration `app/core/source_sync.py` içine taşındı; scope default
  `opportunity` korunurken status/history/batch çıktısı media scope'u destekliyor.
  Aktif batch extension scope dışına sızmıyor ve worker en eski scope'u dispatch
  ediyor.
- `/media/sync`, provider veya tek item kuyruğu oluşturuyor. Media polling
  SourceAdapter-compatible adapter, `source_run`, unit upsert/dedup,
  `media.release_discovered`, artwork/metadata refresh ve batch ilerlemesiyle
  çalışıyor. Saatlik scheduler 24 saatlik due setting'ini denetliyor ve startup
  catch-up yapıyor; monitored item yoksa run yazmıyor.
- Üç ardışık unexpected empty/error provider health notification'ı core `notify`
  ile provider bazında dedup ediliyor; media sync event verb'leri kaydedildi.

## GREEN ve final doğrulama

- Provider + artwork odak paketi: `8 passed`.
- Scope/API/worker/provider/artwork odak paketi: `12 passed`; worker health paketi:
  `4 passed`.
- Fresh tam backend:

  ```bash
  docker compose -p forkos-task3-final -f compose.yaml -f compose.test.yaml \
    run --rm --build backend-test sh -c 'alembic upgrade head && pytest -q'
  ```

  Sonuç: `150 passed in 17.19s`.
- `ruff check app tests scripts`: `All checks passed!`.
- `python -m compileall -q app`: exit 0.
- `git diff --check`: exit 0.

## Commit

- `8d84bce` — `Implement media providers artwork and sync`

## Concerns

- Provider testleri tüm HTTP çağrılarını mocklar; canlı üçüncü taraf çağrısı test
  suite'inde yapılmaz. Gerçek credential ve upstream rate-limit davranışı ancak
  kullanıcının yerel ayarlarıyla gözlemlenebilir; provider hataları library read
  yollarını bloke etmez ve `source_run` health olarak kalıcılaştırılır.

## Review düzeltmeleri — 2026-08-23

### RED kanıtı

- Provider/artwork review paketi ilk koşuda `7 failed, 8 passed` verdi: TMDB
  kind identity, AniList gün aralığı, IGDB capability, MusicBrainz disc identity,
  kaybolan iTunes sonucu, OpenLibrary partial date ve artwork redirect.
- Sync/domain review paketi ilk koşuda `9 failed, 12 deselected` verdi: provider
  unit identity, release transition, TMDB create identity, readiness hatası,
  upcoming persistence, item-level due, kaybolan provider batch'i, atomik
  rollback ve worker source reservation.
- Sabit provider release timestamp'inin duvar saatiyle geçmişe düşmesi için
  eklenen regresyon önce `cycle_reopened=False` ile RED oldu.
- TMDB movie serial capability testi önce `units=True`, legacy raw identity
  testi önce `201 != 409` ile RED oldu.

### Uygulama özeti

- Provider `upcoming(days)` akışı gerçek polling'e bağlandı; gün ayarı uygulanıp
  unit'lerle normalize/dedup edildi ve upcoming notification dedup anahtarıyla
  kalıcılaştırıldı. IGDB ve TMDB movie capability bildirimleri düzeltildi.
- Unit kimliği provider ID varken yalnız stabil provider identity ile eşleşiyor;
  TMDB season ve MusicBrainz disc kimlikleri number çakışmalarını engelliyor.
- Gelecekte keşfedilen release'ler kalıcı pending checkpoint ile saat geçişinde
  tam bir kez işleniyor; aynı completed cycle açılıyor, historical backfill
  açmıyor.
- TMDB `movie:<id>` / `tv:<id>` kimliği search/details/create/sync yollarında
  canonical hale getirildi; raw provider ID API metadata'sında korunup legacy
  aynı-kind kayıtlar dedup kapsamına alındı.
- Provider batch'lerinin item'ları kaybolduğunda empty run ile kapanması,
  item-bazlı due cutoff, atomik snapshot+unit+event transaction'ı ve iTunes
  vanished feed empty health davranışı tamamlandı.
- Worker reservation batch row lock altında running `source_run` yazarak iki
  worker arasında exclusive hale getirildi. Explicit not-ready provider hatası
  ve typed `/media/providers` + `/media/sync` response modelleri eklendi.
- Artwork HTTP istemcisi redirect takip ederken MIME, boyut, atomic replace ve
  traversal korumalarını koruyor; OpenLibrary partial tarihler güvenle parse
  ediliyor.

### GREEN ve final doğrulama

- Odak review paketi: `82 passed in 4.29s`.
- Fresh tam backend: `168 passed in 19.02s`.
- `ruff check app tests scripts`: `All checks passed!`.
- `python -m compileall -q app tests scripts`: exit 0.
- `git diff --check`: exit 0.
- `backend/uv.lock` mevcut değil; dependency lock policy değişmedi.

### Review commit'i

- `faf6bc8` — `Fix media sync review findings`

### Kalan concern

- Yeni provider davranışlarının tüm HTTP testleri mock'ludur; canlı upstream
  credential/rate-limit davranışı test sırasında çağrılmamıştır. Bilinen kod
  veya test bloklayıcısı yoktur.
