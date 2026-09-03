---
name: postgres-alembic-guardian
description: Model, migration veya SQL yazarken uygulanır. entity.id PK kuralını, asyncpg için migration'larda tek SQL per op.execute kuralını ve Türkçe arama için simple + unaccent + pg_trgm standardını korur.
globs: ["backend/app/**/models.py", "backend/alembic/versions/*.py", "backend/app/**/*.sql"]
---

# postgres-alembic-guardian — forkOS veri katmanı

## Kurallar (AGENTS.md KURAL 1, 9, 10, 12)

1. **KURAL 1 — PK = entity.id FK.** Aranabilir/linklenebilir her modül nesnesi `EntityBacked` (FK `entity.id ondelete=CASCADE`) olmalı. Yalnızca bir entity'yi yerleştiren/ölçen destek tabloları istisnadır — listesi `backend/tests/test_migrations.py`'de; yeni istisna eklemeden ÖNCE kullanıcıyla konuş. Model deseni: `backend/app/modules/learning/models.py`.
2. **Entity yazımı helper'dan.** `Entity(...)`'i elle KURMA: `app/core/entity.py` → `create_entity`, `touch_entity`, `archive_entity`, `restore_entity`, `delete_entity`. Yeni entity açarken aynı id'de modül satırı + `log_event` (KURAL 3).
3. **KURAL 9/10 — migration'lar elle, tek komut per execute.** `make revision m="..."` çıktısını asla körlemesine commit etme; elle yaz ve gözden geçir. **Her SQL komutu AYRI `op.execute()`** — asyncpg tek prepared statement'a birden fazla komut almaz. Koruyan test: `backend/tests/test_migrations.py` (multi-command + istisna listesi + SQL yorum satırında `;` bile yakalar).
4. **KURAL 12 — Türkçe arama.** `to_tsvector('turkish', ...)` YAZMA. Standart: `'simple'` config + `immutable_unaccent()` + `pg_trgm`. `entity.search_vec` generated sütunu bu kuralın örneği.
5. **İndeks disiplini.** JSONB içi arama (örn. `payload->>'oid'`) indekssiz bırakılmaz — kısmi indeks (`create index ... where verb = '...'`). Zaman sorguları `(kolon at time zone 'Europe/Istanbul')::date` biçiminde app-gününe çevrilir (config.timezone).

## Migration akışı

1. `docker compose exec -T api python -m alembic revision -m "<aciklama>"` ile boş dosya (veya elle `alembic/versions/NNNN_ad.py` oluştur; `revision`/`down_revision` zinciri: sonuncuyu `alembic/versions/` son dosyadan al).
2. UPGRADE/DOWNGRADE listelerini `op.execute` ile yaz (yukarıdaki kurallar).
3. Test DB'de dene: `DATABASE_URL=...forkos_test ... python -m alembic upgrade head`, ardından `tests/test_migrations.py` + ilgili modül testleri.
4. Canlı DB'ye uygulamadan önce eklemeli/geri dönüşümlü olduğunu doğrula; kullanıcıya bildir.

## Doğrulama

- `docker compose exec -T api env DATABASE_URL=postgresql+asyncpg://lifeos:lifeos@db-test:5432/forkos_test python -m pytest tests/test_migrations.py tests/test_registry.py -q`
- Migration zinciri tek head: `python -m alembic heads` → tek satır.
