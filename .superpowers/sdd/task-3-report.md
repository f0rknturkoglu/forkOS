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

## İkinci review düzeltmeleri — 2026-08-23

### RED kanıtı

- Yedi odak testin ilk koşusu `6 failed, 1 passed` verdi: existing unit upcoming
  bildirimi `0 != 1`, missed release cycle reopen `False`, TMDB aggregate
  capability `False`, concurrent batch'lerde iki ayrı UUID, MusicBrainz eski
  position identity ve release sıra bağımlılığı.
- Fetch-count fixture'ı provider'ın gerçek filter davranışıyla sıkılaştırılınca
  ilk koşuda `unit_calls=4 != 2` verdi; adapter aynı snapshot için units'i iki
  kere çekiyordu.

### Uygulama özeti

- Upcoming bildirimi yalnız `result.created` dalından çıkarıldı. Her snapshot'ta
  window değerlendirilirken notification dedup key'i tam bir kez kalıcılık
  sağlıyor; far-future unit sonradan pencereye girdiğinde bildirim oluşuyor.
- Yeni keşfedilmiş ve zaten yayınlanmış unit, yalnız release timestamp'i latest
  completed cycle'ın completion timestamp'inden kesin sonra ise aynı cycle'ı
  açıyor. Pre-completion historical backfill açmıyor ve pending checkpoint bir
  kez tüketiliyor.
- Provider status registry variant'larını provider ID bazında grupluyor;
  capabilities kind adapter'ları üzerinde union, kinds ise configured adapter
  sırasıyla aggregate ediliyor. TMDB movie/show satırı show units/upcoming
  desteğini artık kaybetmiyor.
- `create_or_extend_batch()` empty-row yarışı scope-bazlı PostgreSQL transaction
  advisory lock ile serialize edildi; iki session tek active batch ve source
  union'ı üretiyor.
- `upcoming()` contract'ı önceden çekilmiş units snapshot'ını kabul ediyor;
  adapter bu snapshot'ı geçirerek upstream'i poll başına bir kez çağırıyor ve
  aynı gün filtresini koruyor.
- MusicBrainz deterministik release seçiyor; track ID, sonra recording ID,
  sonunda group/disc/position/title hash fallback'i stabil unit identity olarak
  kullanılıyor.

### GREEN ve final doğrulama

- Yeni odak review testleri: `7 passed in 0.48s`.
- Geniş media/source odak paketi: `90 passed in 5.10s`.
- Fresh tam backend: `173 passed in 20.02s`.
- `ruff check app tests scripts`: `All checks passed!`.
- `python -m compileall -q app tests scripts`: exit 0.
- `git diff --check`: exit 0.
- Worktree dependency policy kontrolü: `backend/uv.lock` yok.

### İkinci review commit'i

- `7edc24e` — `Close remaining media sync review gaps`

### Kalan concern

- Canlı upstream davranışı halen bilinçli olarak mock HTTP testleriyle izole;
  bilinen backend/test bloklayıcısı yoktur.

## Final cleanup — 2026-08-23

### RED kanıtı

- Dört odak test ilk koşuda `4 failed` verdi. MusicBrainz disc/fallback testi
  edition track ID'lerini (`track:a`, `track:b`) döndürdü; release-group'a yeni
  küçük ID'li edition eklendiğinde aynı logical track'ler farklı provider ID
  üretti.
- TMDB adapter'ı iki snapshot için `/3/tv/42` endpoint'ini beklenen 2 yerine 4
  kez çağırdı. Podcast adapter testi de lookup tekrarını çalıştırırken kurulu
  feedparser API'sinde bulunmayan `loads` çağrısını görünür kıldı.

### Uygulama özeti

- MusicBrainz unit identity artık edition track ID'sine bağlı değil: recording
  ID varsa canonical identity odur; yoksa release-group + medium position +
  track position + title hash fallback'i kullanılır. Edition track ID yalnız
  provider metadata'sında tutulur. Release-group membership büyüse ve seçilen
  edition değişse bile logical unit provider ID'leri sabit kalır.
- HTTP provider tabanı adapter snapshot kapsamına özel, `ContextVar` tabanlı GET
  response reuse ekledi. Cache her `MediaSourceAdapter.fetch()` çıkışında reset
  edilir; concurrent task'lar state paylaşmaz ve sonraki poll upstream'i yeniden
  çağırır.
- TMDB details/units aynı `/tv/{id}` yanıtını snapshot içinde paylaşır. Podcast
  details/units aynı iTunes lookup yanıtını paylaşır; RSS feed yine snapshot
  başına bir kez alınır. Publisher feed parsing kurulu feedparser sözleşmesine
  uygun olarak `parse()` kullanır.

### GREEN ve final doğrulama

- Yeni odak regresyonları: `4 passed in 0.02s`.
- Geniş media/source odak paketi: `93 passed in 4.95s`.
- Fresh tam backend: `176 passed in 19.73s`.
- `ruff check app tests scripts`: `All checks passed!`.
- `python -m compileall -q app tests scripts`: exit 0.
- `git diff --check`: exit 0.
- `backend/uv.lock` yok; Task 4/5 değiştirilmedi.

### Final cleanup commit'i

- `0347d7b` — `Stabilize provider snapshots and MusicBrainz units`

### Kalan concern

- Canlı third-party credential/rate-limit davranışı mock test kapsamı dışında;
  bilinen backend/test bloklayıcısı yoktur.

## Settings Source Health Disclosure — 2026-08-25

### Status

Implemented and verified.

### Implementation

- Added and exported `SettingsSourceHealth({ sources })` from `frontend/src/modules/settings/SettingsPage.tsx`.
- The wrapper owns the disclosure state and delegates rendering to the shared `SourceHealthAccordion`.
- Preserved the existing Settings label as `Kaynak sağlığı`.
- Replaced the final always-visible source-health table with the collapsible wrapper.
- Kept `Badge` and `relativeTime` imports because they remain used by integration and backup sections.

### TDD evidence

#### RED

Added `frontend/src/modules/settings/SettingsSourceHealth.test.tsx` before the implementation. Ran:

```bash
cd frontend && npm test -- --run src/modules/settings/SettingsSourceHealth.test.tsx
```

Result: failed as expected because `SettingsSourceHealth` was not exported yet (React reported an invalid/undefined element type).

#### GREEN

After the minimal wrapper and table replacement, ran:

```bash
cd frontend && npm test -- --run src/core/SourceHealthAccordion.test.tsx src/modules/settings/SettingsSourceHealth.test.tsx
```

Result: 2 test files passed, 3 tests passed.

Also ran:

```bash
cd frontend && npm run build
```

Result: TypeScript compile, Vite production build, PWA generation, and bundle check all exited successfully.

### Files

- Modified: `frontend/src/modules/settings/SettingsPage.tsx`
- Added: `frontend/src/modules/settings/SettingsSourceHealth.test.tsx`

### Self-review

- The wrapper starts closed (`useState(false)`).
- The test verifies `details[data-source-health]`, the `2 kayıt` summary, opening via `Kaynak sağlığı`, and both source names.
- The shared accordion’s existing native disclosure behavior and status presentation are reused.
- `git diff --check` passed.
- No media files or unrelated modules were changed.

### Concerns

None. The wrapper passes an explicit lowercase title to preserve the existing Settings UI wording while the shared component remains reusable elsewhere.

## Duplicate occurrence ve concurrent cache edge — 2026-08-23

### RED kanıtı

- İki yeni odak testin ilk koşusu `1 failed, 1 passed` verdi. Aynı MusicBrainz
  recording'i iki track occurrence'ında kullanıldığında iki unit de
  `recording:recording-same` kimliğine collapse oldu. Aynı provider instance'ını
  paylaşan eşzamanlı iki adapter snapshot cache isolation testi mevcut
  `ContextVar` tasarımıyla ilk koşuda geçti.

### Uygulama özeti

- MusicBrainz media ve track listeleri explicit position, yoksa kaynak ordinal
  ile normalize ediliyor. Recording occurrence sayacı bu stabil logical sırada
  ilerliyor; ilk occurrence migration-compatible `recording:<id>`, sonraki
  occurrence'lar `recording:<id>:oN` kimliği alıyor.
- Recording ID bulunmayan unit'ler önceki release-group/disc/track/title-hash
  fallback'ini koruyor. Release-group membership growth ve edition reorder
  testleri değişmeden geçerken aynı recording'in tekrarları ayrı unit kalıyor.
- Eşzamanlı cache regresyonu iki farklı provider ID ile aynı provider instance'ı
  üzerinde gerçek `asyncio.gather` overlap oluşturuyor; title/unit payload'ları
  task'lar arasında sızmıyor ve her base endpoint snapshot başına bir kez
  çağrılıyor.

### GREEN ve final doğrulama

- MusicBrainz + concurrent cache odak paketi: `5 passed in 0.02s`.
- Geniş media/source odak paketi: `95 passed in 4.86s`.
- Fresh tam backend: `178 passed in 19.58s`.
- `ruff check app tests scripts`: `All checks passed!`.
- `python -m compileall -q app tests scripts`: exit 0.
- `git diff --check`: exit 0.
- `backend/uv.lock` yok; Task 4/5 değiştirilmedi.

### Edge cleanup commit'i

- `2a9bb55` — `Distinguish repeated MusicBrainz recordings`

### Kalan concern

- Canlı third-party credential/rate-limit davranışı mock test kapsamı dışında;
  bilinen backend/test bloklayıcısı yoktur.

## Same-key concurrent cache test adequacy — 2026-08-23

### RED kanıtı

- Güçlendirilmiş test iki eşzamanlı task'ta aynı provider instance, aynı
  `GET /3/tv/42` cache key'i ve task-local olarak farklı mocked response kullandı.
- Bilinçli shared mutable cache kontrolünde doğru isolation beklentisiyle ilk
  koşu RED verdi: `shared_seasons == [2, 2]`, beklenen task-distinct değer
  `[1, 2]` idi. Böylece testin shared-cache implementasyonunu gerçekten
  yakaladığı doğrulandı.

### Uygulama özeti

- Test, iki details çağrısını barrier ile overlap ettiriyor ve details/units
  arasına kontrollü scheduling noktası koyuyor. Production `ContextVar` cache
  task A/B için aynı key'de kendi payload'ını koruyor ve base endpoint toplam
  iki kez çağrılıyor.
- Aynı senaryo test içindeki shared mutable slot kontrolüyle de çalıştırılıyor;
  kontrolün `[2, 2]` sızıntısı kalıcı assertion olarak test sensitivity'sini
  belgeliyor. Production değişikliği gerekmedi.

### GREEN ve final doğrulama

- Same-key cache + TMDB/Podcast request-count odak paketi: `3 passed in 0.03s`.
- Geniş media/source odak paketi: `95 passed in 5.00s`.
- Fresh tam backend: `178 passed in 20.22s`.
- `ruff check app tests scripts`: `All checks passed!`.
- `python -m compileall -q app tests scripts`: exit 0.
- `git diff --check`: exit 0.
- `backend/uv.lock` yok; Task 4/5 değiştirilmedi.

### Test adequacy commit'i

- `a1d4a4c` — `Strengthen concurrent provider cache regression`

### Kalan concern

- Canlı third-party credential/rate-limit davranışı mock test kapsamı dışında;
  bilinen backend/test bloklayıcısı yoktur.
