# forkOS — A3 Session Handoff & Episodic Memory Implementation Plan

**Tarih:** 2026-09-22
**Branch:** `main`
**Taban:** `c9f43cc`
**Spec:** `docs/superpowers/specs/2026-09-22-a3-episodic-session-handoff-design.md`

---

## 1. İş kalemleri

| # | İş | Dosyalar |
|---|---|---|
| 1 | H4 sözleşmesi | `local_cognition/{models,contracts,prompts}.py`, `docs/hermes/h4-tool-contract.md` |
| 2 | Şema + migration | `alembic/versions/0066_agent_episode.py`, `app/modules/agent_episode/models.py`, `tests/test_migrations.py` |
| 3 | A3 sözleşmeleri | `app/modules/agent_episode/schemas.py` |
| 4 | Damıtma | `app/modules/agent_episode/distill.py` |
| 5 | Servis | `app/modules/agent_episode/service.py` |
| 6 | Render | `app/modules/agent_episode/renderer.py`, `app/core/prompt_safety.py` |
| 7 | Uçlar + registry | `app/modules/agent_episode/router.py`, `__init__.py`, `app/modules/__init__.py` |
| 8 | `/turn` entegrasyonu | `app/modules/agent_lifecycle/router.py`, `app/modules/agent_continuity/schemas.py` |
| 9 | Plugin | `tools/hermes/forkos-lifecycle/{__init__.py,plugin.yaml}` |
| 10 | Frontend tanılama | `frontend/src/core/agentEpisode.ts`, `modules/settings/BrainAgentSection.tsx`, `scripts/check-endpoint-coverage.mjs` |
| 11 | Testler | `tests/a3_fixtures.py`, `tests/test_agent_episode_*.py`, `tests/test_hermes_lifecycle_plugin.py`, `tests/test_agent_lifecycle_invariants.py` |
| 12 | Doküman | `docs/hermes/a3-episodic-handoff.md`, `docs/hermes/walkthrough.md`, `README.md`, `roadmap.md` |

## 2. Sıra ve bağımlılıklar

```
1 (H4 sözleşmesi) ─┐
                   ├─→ 4 (damıtma) ─→ 5 (servis) ─→ 7 (uçlar) ─→ 8 (/turn)
2 (şema) ─→ 3 (A3 sözleşmeleri) ─┘                        │
                                                          └─→ 9 (plugin, HTTP sözleşmesine bağlı)
6 (render) ─→ 7
10 (frontend, OpenAPI'ye bağlı) ─→ 11 ─→ 12
```

## 3. Uygulama kararları (küçük seçimler, gerekçeli)

| Karar | Gerekçe |
|---|---|
| **Üçüncü tablo** (`agent_session_episode_turn`) | A2'nin `agent_session_source.turn_id`'si turn bazlı teslimi deterministik vermiyor (bkz. spec §9). Tur başına degrade kodu ve digest de burada; item tablosuna kopyalanmaz (tek doğruluk kaynağı). |
| **`source_excerpt` kalıcılaşmaz** | Grounding kapısı için gerekli, ham transkript parçası olduğu için saklanamaz. |
| **`observed_during_session` üçüncü epistemik sınıf** | §7'nin iki sınıfı kanonik gözlemi ifade edemiyor; §10 nedensellik iddiasını yasaklıyor. |
| **Kapsam teslim edilen kaynaklardan türetilir** | Hermes `scope_project` göndermiyor; A2 kaynakları `scope_project` taşıyor. İki farklı kapsam görülürse `NULL` (belirsiz). |
| **Ortak kaçış yardımcıları `app/core/prompt_safety.py`'ye taşındı** | A2 ve A3 render'ı aynı kuralları kullanmalı; modül-düzeyi döngüyü de kırar. İkinci kaçış kopyası yok. |
| **`_check_source_freshness` → `check_source_freshness`** | A3 tazelik probunu yeniden kullanıyor (§22); ikinci kopya yazılmaz. |
| **Tazelik probu ≤ 6 ref** | İlk tur sıcak yolu; sınırsız prob deadlined profili bozardı. |
| **`EPISODE_SEALED` reason kodu eklendi** | Mühürlenmiş devre gelen tur sessizce yutulmaz, sınırlı kodla bildirilir. |

## 4. Doğrulama kapıları

- `pytest -q tests/test_migrations.py` — yeni tablolar allowlist'te, tek head, tek komut/execute.
- `pytest -q tests/test_h4_episodic_contract.py tests/test_h4_models.py tests/test_h4_grounding.py` — sözleşme + grounding.
- `pytest -q tests/test_agent_episode_*.py` — privacy, provenance, extraction, finalize, handoff, renderer.
- `pytest -q tests/test_hermes_lifecycle_plugin.py` — hook kaydı, `conversation_history` yokluğu, hata izolasyonu.
- `pytest -q tests/test_agent_lifecycle_invariants.py` — sıfır kanonik mutasyon (H7 dahil).
- `pytest -q tests/test_agent_lifecycle_turn_endpoint.py tests/test_agent_continuity_*.py` — A1/A2 regresyonu.
- Frontend: `npx tsc -b`, `npm run api:check`, `node scripts/check-endpoint-coverage.mjs`.
- Gerçek runtime: iki oturumluk Hermes walkthrough + gecikme ölçümleri.

## 5. Bilinçli olarak kapsam dışı

A4 (semantic promotion / durable memory) ve A5 (context judge) **başlatılmaz**. Roadmap yalnız sınırı dürüstçe gösterir. Legacy not tabloları DÜŞÜRÜLMEZ (o iş fiziksel temizlik fazına aittir).
