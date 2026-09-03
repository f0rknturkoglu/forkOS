---
name: api-contract-sync
description: FastAPI endpoint'i veya Pydantic şeması değiştiğinde uygulanır. openapi.json ve api-schema.ts üretim adımlarını tetikler; TypeScript sözleşme uyumsuzluklarını ve CI kırılmalarını önceden yakalar.
globs: ["backend/app/**/router.py", "backend/app/**/schemas.py"]
---

# api-contract-sync — OpenAPI ↔ TypeScript sözleşmesi

## Ne zaman

Bir `@router` ucu eklediğinde/sildiğinde/imzasını değiştirdiğinde, Pydantic şema (in/out) değiştirdiğinde ya da yeni entity tipi rotası açtığında.

## Zorunlu adımlar (sırayla)

1. **Uç kullanılmalı (KURAL 17).** Yeni uç frontend'de çağrılır — yoksa `check-endpoint-coverage` kızar. Değişken-tabanlı çağrı (`const path = ...` sonra `api.get(path)`) statik tarayıcıda görünmez: `frontend/scripts/check-endpoint-coverage.mjs` içindeki `DYNAMIC_KNOWN` listesine açıklamayla ekle.
2. **openapi.json üret:** `cd backend && ../backend/.venv/bin/python scripts/export_openapi.py` (api container ayakta değilken host venv ile çalışır).
3. **api-schema.ts üret:** `cd frontend && npm run api:generate`.
4. **Kontrat kontrolü:** `cd frontend && npm run api:check` → "runtime sözleşmesiyle güncel" çıktısı şart. CI'da `api:check` ayrı iş olarak koşar — bayat bırakırsan CI kırmışsın demektir.
5. **Entity rotası eklediysen** (EntityTypeSpec.route): `backend/tests/test_registry.py` içindeki `FRONTEND_ROUTES` setine yeni rotayı ekle (guardrail: her tip rotası frontend'de kayıtlı olmalı).
6. **Kapsam:** `cd frontend && node scripts/check-endpoint-coverage.mjs` → referanssız uç sayısı eşik (3) altında.

## Frontend tip kullanımı

- Elle yazılan tipler `frontend/src/core/types.ts`'te (modül tipleri modül içinde olabilir).
- Üretilen tipler `frontend/src/generated/api-schema.ts`'ten (`ApiSchemas["..."]`); `apiSchema.test.ts` yüksek riskli şemaların varlığını doğrular.
- `frontend/src/core/api.ts` çağrıları path'i `/api` PREFIX'SİZ yazar (`api.get("/todos")`).

## Kaçın

- `export_openapi.py` yerine elle openapi.json düzenlemek.
- Üretilmiş dosyayı elle düzeltmek (sonraki üretimde ezilir).
- Rotayı silerken aynı dosyada komşu rotayı ezmek (append-only disiplini: yeni uç dosya sonuna/yanına, mevcut blokları değiştirme — geçmişte agent'lar mevcut `/news/github-trending` ve `/rss/items/{id}` rotalarını bu şekilde silmişti; bitince `git diff | grep '^-'` ile doğrula).
