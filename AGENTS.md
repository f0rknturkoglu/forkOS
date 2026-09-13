# forkOS — Agent geliştirme sözleşmesi

forkOS tek kullanıcılı, **local-only** bir kişisel işletim sistemidir. Bu dosya Codex, Claude Code ve diğer kod ajanları için kanonik çalışma sözleşmesidir. Ürün ve kurulum özeti `README.md`, yaşayan mimari `docs/mimari.md` içindedir.

## Bağlam

- Servisler: PostgreSQL 16 (`db`), FastAPI (`api`), React/Vite (`web`) ve isteğe bağlı APScheduler (`worker`).
- Auth veya tenant katmanı yoktur. Servisler varsayılan olarak yalnızca `127.0.0.1` üzerinde yayınlanır.
- Offline mod yalnızca okumadır. Extension capture işlemleri kendi idempotent outbox'ında bekletir.
- Kullanıcı Türkçe konuşur. Kod ve değişken adları İngilizce; açıklama ve kullanıcı metinleri Türkçe olabilir.
- Worker varsayılan olarak kapalıdır. Manuel yenileme API'nin kalıcı kaynak kuyruğu üzerinden çalışır.

## Çalışmaya başlamadan önce

1. `git status --short` ile kullanıcıya ait mevcut değişiklikleri gör ve koru.
2. İlgili modülün backend/frontend registry girişini ve testlerini incele.
3. Görev aşağıdaki proje becerilerinden birine uyuyorsa önce ilgili `.agents/skills/*/SKILL.md` dosyasını oku:
   - API/Pydantic değişikliği: `api-contract-sync`
   - UI/CSS değişikliği: `frontend-design`
   - model/migration/SQL: `postgres-alembic-guardian`
   - scraper/RSS/kaynak: `resilient-scraping`
   - paket/ağ/entegrasyon: `local-privacy-audit`
4. Kişisel DB, yedek, attachment, belge ve cache dosyalarını test verisi gibi kullanma veya silme.

## Değişmez kurallar

1. **Her aranabilir veya linklenebilir modül nesnesinin PK'si `entity.id` alanına FK olmalıdır.** `plan_slot` gibi yalnızca bir entity'yi yerleştiren/ölçen destek tabloları belgelenmiş istisnalardır. Yeni istisna eklemeden önce kullanıcıyla konuş.
2. **Entity yazan her yer `backend/app/core/entity.py` helper'larını kullanır.** Elle `Entity(...)` oluşturma.
3. **`event` append-only'dir.** UPDATE/DELETE yapma; anlamlı her aksiyondan sonra `log_event()` çağır.
4. Backend modüllerinin tek kayıt noktası `backend/app/modules/__init__.py::MODULES`, frontend modüllerinin tek kayıt noktası `frontend/src/modules/index.ts` dosyasıdır. Yeni modül için `main.py` içine özel bağlantı ekleme.
5. **Yeni scraper = `SourceAdapter`.** Adaptörü `backend/app/sources/base.py` sözleşmesine göre yaz; worker içine gömme.
6. Her scraper/feed çalışması `source_run` kaydı üretir. Art arda üç `empty` sonucu görünür uyarıya dönüşür; sessiz ölüm kabul edilmez.
7. Inbox ve Bookmark aynı tablodur; ayrım `collection` alanıyla yapılır. İkinci tablo açma.
8. Extension kaynaklı bütün yazmalar `client_uuid` ile idempotent olmalıdır.
9. Migration'ları elle yaz ve gözden geçir. Autogenerate çıktısını kontrol etmeden kullanma.
10. Migration içinde her SQL komutu ayrı `op.execute()` çağrısıdır. asyncpg tek prepared statement içinde çoklu DDL kabul etmez.
11. `@/` alias'ı hem `frontend/tsconfig.json` hem `frontend/vite.config.ts` içinde tanımlı kalmalıdır.
12. PostgreSQL metin aramasında `'simple'` config + `immutable_unaccent()` + `pg_trgm` kullan. `to_tsvector('turkish', ...)` yazma.
13. Entity tipi, etiketi, ikonu ve rotası yalnızca `EntityTypeSpec` içinde tanımlanır. Frontend'de tip→rota veya tip→etiket sabiti yazma; `entityRoute()` ve `typeLabel()` kullan.
14. Mutation sonrası tazeleme `invalidateAfter()` ile yapılır. Dağınık ham `invalidate("a", "b")` çağrıları yazma.
15. Renk, tipografi, boyut ve yarıçap tasarım tokenlarından gelir. Sabit hex, `text-[Npx]` ve ham `<input>/<select>/<textarea>` kullanma; `@/core/ui` primitive'lerini kullan.
16. Son tarih üreten modül `ModuleSpec.deadline_provider` sağlar. `deadline_v` benzeri SQL view oluşturma.
17. Backend'de kayıtlı ama frontend'de kullanılmayan endpoint bırakma; endpoint ya tüketilir ya kaldırılır.

Bu kuralları koruyan temel testler:

- `backend/tests/test_migrations.py`
- `backend/tests/test_registry.py`
- `frontend/src/core/designSystem.test.ts`
- `frontend/src/core/invalidation.test.ts`
- `frontend/src/core/mediaRouting.test.ts`
- `frontend/scripts/check-endpoint-coverage.mjs`

## Backend modülü

```text
backend/app/modules/<name>/
├── __init__.py     ModuleSpec ve EntityTypeSpec
├── models.py       EntityBacked + Base; PK → entity.id FK
├── schemas.py      Pydantic giriş/çıkış sözleşmeleri
├── service.py      İş mantığı, entity helper'ları ve event'ler
└── router.py       APIRouter; /api prefix'i ekleme
```

Modülü `backend/app/modules/__init__.py::MODULES` listesine ekle. Model değişikliği varsa tek-head Alembic migration yaz.

## Frontend modülü

```text
frontend/src/modules/<name>/
├── index.ts        registerModule(...)
├── <Name>Page.tsx
└── *.test.ts(x)
```

Modülü `frontend/src/modules/index.ts` içinde import et. Navigasyon, route, Today widget'ları ve komutlar registry üzerinden türemelidir. Ortak çalışma alanı ve form primitive'lerini `frontend/src/core` içinden kullan.

## Sık kullanılan komutlar

```bash
# Varsayılan: Podman Compose
make up
make migrate
make logs
make down

# Docker / OrbStack
make up CO="docker compose"
make migrate CO="docker compose"
make logs CO="docker compose"
make down CO="docker compose"

# Worker yalnız gerektiğinde
make worker-up CO="docker compose"
make worker-down CO="docker compose"

# Doğrulama
make test CO="docker compose"
make verify CO="docker compose"
```

Backend DB'siz hızlı testleri `backend/` içinde `pytest -q` ile çalıştırabilirsin; PostgreSQL isteyen testler kendini atlar. Migration gerçeği ve güncel head için `backend/alembic/README.md` dosyasına bak.

## Bitirme kontrolü

- Değişiklik kapsamına uygun testleri çalıştır.
- FastAPI/Pydantic değiştiyse `backend/openapi.json` ve `frontend/src/generated/api-schema.ts` dosyalarını senkronla.
- Migration varsa hem upgrade'i hem migration guardrail testlerini doğrula.
- UI değiştiyse dar ve geniş viewport'u, klavye akışını, loading/empty/error durumlarını kontrol et.
- Yeni ağ veya paket davranışında local-only sınırını ve dış istekleri denetle.
- `git diff --check` çalıştır; kullanıcı istemedikçe commit/push yapma.
- Görev için açılan geçici container, network, volume ve test çıktısını temizle; kişisel `forkos_pgdata` volume'üne dokunma.

## Yapma

- Multi-user, tenant veya uzaktan erişim katmanı ekleme.
- Harici LLM/telemetri servisine kişisel veri gönderme.
- LangChain benzeri ağır bir soyutlama katmanı ekleme; gereken dış GET çağrılarında doğrudan `httpx` kullan.
- `entity`, `event` veya `link` çekirdek şemasını modül kolaylığı için değiştirme; önce kullanıcıyla konuş.
- Frontend kalıcılığı için `localStorage` dışında tarayıcıya özel yeni bir veri deposu varsayma.
- Kullanıcının kişisel DB'sini test, seed veya ekran görüntüsü üretimi için sıfırlama.
