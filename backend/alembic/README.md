# Alembic migration rehberi

forkOS migration zincirinin gerçeği dosya adları değil, her revision içindeki `revision` ve `down_revision` alanlarıdır.

## Güncel durum

- Tek head: `0068_semantic_memory_candidates`
- Taban: `0001_core`
- Zincir doğrulaması: `backend/tests/test_migrations.py::test_revisions_form_a_single_chain`

Güncel zinciri her zaman komutla oku:

```bash
cd backend
alembic heads
alembic history --indicate-current
```

Container içinden:

```bash
docker compose exec api alembic heads
docker compose exec api alembic current
docker compose exec api alembic history --indicate-current
```

## Yeni migration

1. `alembic heads` ile gerçek head'i doğrula.
2. Revision'ı oluştur ve `down_revision` değerini bu head'e bağla.
3. Autogenerate kullandıysan çıktının tamamını elle incele.
4. Her SQL komutunu ayrı `op.execute()` çağrısına koy.
5. Hem `upgrade()` hem mümkünse güvenli `downgrade()` yolunu yaz.
6. Entity-backed bir ana tabloysa PK'nin `entity.id` alanına FK olduğunu doğrula.
7. Son tarih için SQL view yazma; ilgili modüle `deadline_provider` ekle.
8. İzole test veritabanında migration ve model karşılaştırma testlerini çalıştır.

```bash
make test CO="docker compose"
```

## Bilinen adlandırma geçmişi

Eski zincirde dosya sırası ile revision sırası tam örtüşmez. Özellikle:

- `0022_finance_sub.py`, revision `0026_media_domain` sonrasındadır.
- `0023_application_crm.py`, `0022_finance_sub` revision'ından sonradır.
- `0024_remove_habit.py` ve `0025_drop_deadline_v.py` aynı tarihsel zinciri sürdürür.
- `0032_refine_opportunity_categories.py` dosyasının revision kimliği `0032_refine_categories` değeridir.

Bu dosyaları yalnızca isimleri düzenlemek için yeniden adlandırma. PostgreSQL `alembic_version` tablosu revision kimliğini saklar; zinciri test ve `alembic history` ile doğrula.

## Güvenlik notu

Kişisel `lifeos` veritabanını migration denemesi için sıfırlama. `make test`, adı `_test` ile biten geçici PostgreSQL veritabanı kullanır ve test projesini iş bitince `down -v` ile temizler.
