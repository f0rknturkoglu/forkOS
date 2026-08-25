# Faz 0 — Baseline

**Tarih:** 25 Ağustos 2026
**Makine:** macOS (Apple M4 Pro), Docker Compose ile

## Frontend

| Komut | Sonuç |
|---|---|
| `npx vitest run` | **39 dosya geçti, 1 dosya skip** (147 geçti, 9 skip) |
| `npm run build` | Geçti; giriş chunk'ı **290.52 kB** (gzip 91.92 kB) — 500 KB sınırının altında |

Vitest skip: `MediaFrontend.test.tsx` (`describe.skip` — plan D2, Faz 4'te kurulacak).

## Backend (`make test CO="docker compose"`)

| Durum | Değer |
|---|---|
| İlk koşu (değişiklik öncesi) | 139 geçti, **62 hata** |
| Son koşu (düzeltmeler sonrası) | **201 geçti, 0 hata** |

### Bulunan ve düzeltilen pre-existing hatalar

1. **`tests/test_media_domain_migration.py` — 62 hatanın kaynağı.**
   Migration zinciri Y1'e göre `…0025 → 0026 → 0022_finance_sub → 0023_application_crm`
   şeklinde. Testler `alembic downgrade 0025` ile eski şemaya iniyor (bu sırada
   0023'ün downgrade'i `interview`/`application`/`application_history` tablolarını
   düşürüyor) ve `finally`'de yalnızca `0026`'ya geri upgrade ediyordu — 0022/0023
   hiç geri gelmiyordu. `alembic_version` 0026'da kaldığı için sonraki HER DB
   testinin `clean_database` TRUNCATE'i `relation "interview" does not exist` ile
   patlıyordu (62 hatanın tamamı bu zincir).
   **Düzeltme:** her test kendi başlangıç durumunu kuruyor
   (`downgrade 0025` → `upgrade 0026`) ve `finally`'de `alembic upgrade head`
   ile tam şemaya dönüyor. Testler artık self-contained.

2. **`tests/test_migrations.py::test_module_tables_reference_entity` — 1 fail.**
   Kural 1 ihlalleri: `application_history` (append-only durum geçiş logu —
   `event` ile aynı kategori) ve `interview` (opportunity'nin 1:N alt kaydı —
   `plan_slot` gibi destek tablosu). İkisi de istisna listesine yorumlarıyla
   eklendi. (Schema değişmedi; istisna listesi gerçeği belgeliyor.)

## Not

- `.gitignore` zaten kapsıyor: `dist/`, `backend/backups/`, `*.py[cod]`,
  `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `*.tsbuildinfo`, `.DS_Store`,
  `output/`. Git'te takip edilen kirli dosya yok (Faz 1'in 13. maddesi gereksiz).
- Docker image'ları `--build` ile yeniden derlenmeden koştu; sonuçlar güncel kaynakla.
