# Alembic migration rehberi

forkOS migration zincirinin gerçeği dosya adları değil, her revision içindeki `revision` ve `down_revision` alanlarıdır.

## Güncel durum

- Tek head: `0081_goal_roadmap`
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

Tarihsel predecessor: `0079_retire_media_batches` (öncesi `0078_pomodoro_source`).
0078 kaynak kanıtına göre timer/manual ayrımını korur. 0079 yalnız emekli Media
kuyruklarını gerekçeli terminal duruma geçirir ve retirement audit ekler; tarihsel
tablo, dosya veya Event silmez. Başlangıç/migration preflight ve recovery adımları
[preflight kapanış raporunda](../../docs/architecture/v1-preflight-closure.md).


## 0080 ve güvenli geri dönüş

`0080_goal_studio_capture`, `0079_retire_media_batches` sonrasındadır. Capture teslim
makbuzu, Goal Studio oturumu/revizyonu ve ilgili indeksleri yoksa oluşturur.
`downgrade()` kasıtlı no-op'tur: Alembic revision pointer `0079` olur; bu üç tablonun
şeması ve geçmiş verisi **korunur**. Tam şema geri alma değildir. Yeniden upgrade
`has_table` / `IF NOT EXISTS` kontrolleriyle kayıtları korur. Tarihsel revision'ları değiştirmeyin.

Normal Compose `migrate` servisi API başlamadan `alembic upgrade head` çalıştırır.
Manuel `make migrate CO="docker compose"` aynı zinciri operatörün seçtiği zamanda
çalıştırır; ikinci bir migration mekanizması yoktur. Downgrade bir başlangıç adımı değildir.

İzole PostgreSQL 16 testi: `tests/test_v1_migration_roundtrip.py`. Clean install için
boş `compose.test.yaml` DB'sinde `alembic upgrade head`; mevcut kayıtların korunması
ve `0079 → 0080 → 0079 → 0080` / export-restore roundtrip için ilgili testi çalıştırın.
Güncel test sonuçları [V1 final kapanış raporundadır](../../docs/architecture/v1-final-closure.md).
