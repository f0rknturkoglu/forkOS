# forkOS — Claude Code Talimatlari

Tek kullanicilik, **local-only** kisisel isletim sistemi.
Yol haritasi: `forkOS-PLAN.md`. Bu dosya *nasil* yazilacagini anlatir.

## Baglam

- Sadece local makinede calisir. Auth yok, her sey `127.0.0.1`'e bind.
- Podman/Docker Compose: `db` (Postgres 16), `api` (FastAPI :8787), `worker` (APScheduler), `web` (Vite :5173).
- Offline **sadece okuma**. Yazma offline'da kapali; capture'i extension outbox cozer.
- Kullanici Turkce konusur; kod ve degisken adlari Ingilizce, yorumlar Turkce olabilir.

## Degismez kurallar

1. **Her aranabilir/linklenebilir modul nesnesinin PK'si `entity.id`'ye FK olmali.**
   `plan_slot` ve `habit_log` gibi yalnizca bir entity'yi yerlestiren/olcen destek
   tablolari dokumante edilmis istisnadir; yeni istisna eklemeden once konus.
2. **Entity yazan her yer `app/core/entity.py` helper'larini kullanir.** `Entity(...)` nesnesini elle olusturma.
3. **`event` tablosu append-only.** Asla UPDATE/DELETE etme. Anlamli her aksiyondan sonra `log_event()` cagir.
4. **Modul eklemek main.py'ye dokunmayi gerektirmez.** Backend'de `app/modules/__init__.py`'deki `MODULES`, frontend'de `src/modules/index.ts` tek kayit noktasidir.
5. **Yeni scraper = `SourceAdapter`.** (`app/sources/base.py`) Worker'in icine gomme; ileride VPS'e tasinabilmeli.
6. **Her scraper/feed kosusu `source_run`'a yazar.** Ust uste 3 `empty` -> bildirim. Sessiz olum kabul edilemez.
7. **Inbox ve Bookmark ayni tablo.** Ayirici alan `collection`. Ikinci tablo acma.
8. **Extension'a giden her yazma idempotent olmali** (`client_uuid`).
9. Migration'lar elle yazilir ve gozden gecirilir; `--autogenerate` ciktisini kontrol etmeden commit etme.
10. **Migration'da her SQL komutu ayri `op.execute()`.** asyncpg tek prepared
    statement'a birden fazla komut almaz; alt alta yapistirilan DDL calisma
    aninda patlar. `tests/test_migrations.py` bunu kontrol eder.
11. **`@/` alias'i iki yerde tanimli olmali:** `tsconfig.json` (TypeScript icin)
    ve `vite.config.ts` `resolve.alias` (Vite icin). Sadece birine yazarsan
    `tsc` gecer ama uygulama tarayicida acilmaz.
12. Postgres'te **Turkce stemmer yok**: `'simple'` config + `immutable_unaccent()` + `pg_trgm`. `to_tsvector('turkish', ...)` yazma.

## Yeni modul ekleme receti (backend)

```
app/modules/<ad>/
├── __init__.py     MODULE = ModuleSpec(...)
├── models.py       EntityBacked + Base, PK -> entity.id FK
├── schemas.py      Pydantic in/out
├── service.py      is mantigi; create_entity/touch_entity/log_event burada
└── router.py       APIRouter, prefix YOK (main.py /api ekler)
```
Sonra `app/modules/__init__.py` icindeki `MODULES` listesine ekle + Alembic revision.

## Yeni modul ekleme receti (frontend)

```
src/modules/<ad>/
├── index.ts        registerModule({ id, title, routes, todayWidgets, commands })
└── <Ad>Page.tsx
```
Sonra `src/modules/index.ts`'e `import "./<ad>";` ekle. Sidebar, router, Today
(`todayStats` + `todayWidgets`) ve Command Palette otomatik dolar.

## Komutlar

```bash
make up | down | logs | migrate | psql | test
make revision m="aciklama"
make reset            # DB'yi sifirla (veri gider)
```

Docker kullaniyorsan: `make up CO="docker compose"` (varsayilan `podman compose`).
DB'siz hizli test: `backend/` icinde `pytest -q` -- Postgres isteyen testler kendini atlar.

## Yapma

- Multi-user / tenant mantigi ekleme.
- Harici API'ye veri gonderme (LLM dahil) — her sey local kalir.
- LangChain benzeri agir soyutlama katmani ekleme; httpx ile dogrudan cagri yeterli.
- `event`, `entity`, `link` semasini modul ihtiyaci icin degistirme; once konus.
- Frontend'de `localStorage` disinda kalici depolama varsayma.
