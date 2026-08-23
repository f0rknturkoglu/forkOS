# forkOS — Faz 0 + Faz 1 Teknik Plan

> **Durum (Faz 0–5 tamamlandı):** Bu dosyanın alt bölümü ilk iki haftalık tarihsel
> uygulama planını korur. Güncel çalışma biçimi, endpoint'ler ve kurulum için
> `README.md`; değişmez geliştirme kuralları için `AGENTS.md` esas alınır.

**Kapsam:** Çekirdek altyapı (entity / link / event / saved view) + Capture dikey dilimi
(Browser Extension → Universal Inbox → Bookmark Library → RSS Reader)

**Verilen kararlar**

| Karar | Seçim | Sonucu |
|---|---|---|
| Çalışma ortamı | Sadece local makine | Scraper'lar makine kapalıyken durur; RSS catch-up ile telafi edilir |
| Offline | Read-only cache | PWA + Workbox; yazma offline'da kapalı, capture'ı extension outbox çözer |
| İlk dilim | Capture | Extension + Inbox + Bookmark + RSS |
| Auth | Yok (127.0.0.1 bind) | Drive/Calendar OAuth'u Faz 4'te loopback redirect ile eklenecek |

### Güncel sağlamlık tabanı

- Testler ayrı `forkos_test` veritabanında çalışır; kişisel DB adı test sürecinde
  açıkça reddedilir ve Compose projesi her turdan sonra volume ile kaldırılır.
- Gün sınırları ve rutin ilerletme `Europe/Istanbul` saat diliminde hesaplanır.
- Kaynak senkronu kalıcı batch kuyruğudur: API kuyruğa yazar, worker sahiplenir,
  heartbeat ve stale-run uzlaştırması çökme sonrası devamlılığı sağlar.
- Her scraper `SourceAdapter` sözleşmesine ve yerel fixture testlerine tabidir;
  her gerçek çekim `source_run` üretir.
- Gzip JSON yedek, entity/link/event ve modül tablolarını metadata kontrollü taşır;
  OAuth sırları kapsam dışıdır ve restore round-trip test edilir.
- Frontend mutation'ları ortak offline guard'dan geçer. API sözleşmeleri FastAPI
  OpenAPI snapshot'ından üretilir; sayfalar lazy chunk, giriş bütçesi 500 KB'dır.
- Python ve npm bağımlılıkları lock'lanır; CI migration, test, Ruff, audit, build,
  API şema drift'i ve extension testlerini ayrı işler halinde doğrular.

---

## 1. Mimari

```
┌─────────────────┐
│ Browser Ext.    │  chrome.storage outbox (backend kapalıyken kuyruk)
└────────┬────────┘
         │ POST /api/capture  (client_uuid ile idempotent)
         ▼
┌─────────────────────────────────────────┐
│ FastAPI  (127.0.0.1:8787)               │
│  core/    entity · link · event · tag   │
│  modules/ inbox · bookmark · rss        │
└────────┬────────────────────┬───────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────────┐
│ Postgres 16     │  │ Worker (APScheduler)│
│ + pg_trgm       │  │  RSS fetch loop     │
│ + unaccent      │  │  scraper_run log    │
└─────────────────┘  └─────────────────────┘
         ▲
         │
┌────────┴────────┐
│ React PWA       │  Vite · TanStack Query · Tailwind · cmdk · dnd-kit
└─────────────────┘
```

Hepsi tek `docker compose up` ile ayağa kalkar. macOS ve Windows'ta aynı komut.

---

## 2. Klasör yapısı

```
lifeos/
├── docker-compose.yml
├── .env.example
├── CLAUDE.md
├── backend/
│   ├── pyproject.toml
│   ├── alembic/versions/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── db.py
│       ├── core/
│       │   ├── models.py        # Entity, Link, Event, Tag, SavedView
│       │   ├── entity.py        # create_entity / touch_entity / archive
│       │   ├── events.py        # log_event()
│       │   ├── links.py         # link() / unlink() / related()
│       │   ├── search.py        # entity_search sorguları
│       │   └── router.py        # /api/search, /api/activity, /api/views
│       ├── modules/
│       │   ├── bookmark/        # models.py schemas.py router.py service.py
│       │   ├── rss/
│       │   └── __init__.py      # MODULES registry
│       ├── sources/
│       │   ├── base.py          # SourceAdapter protokolü
│       │   └── rss_source.py
│       └── worker/
│           ├── scheduler.py
│           └── jobs.py
├── frontend/
│   ├── vite.config.ts           # vite-plugin-pwa
│   └── src/
│       ├── app/                 # router, layout, providers
│       ├── core/
│       │   ├── registry.ts      # registerModule()
│       │   ├── CommandPalette.tsx
│       │   ├── GlobalSearch.tsx
│       │   └── api.ts
│       ├── modules/
│       │   ├── today/
│       │   ├── inbox/
│       │   ├── bookmarks/
│       │   └── rss/
│       └── lib/
└── extension/
    ├── manifest.json            # MV3
    ├── background.js            # outbox + retry alarm
    ├── outbox.js
    └── popup/
```

---

## 3. Çekirdek şema — Alembic `0001_core`

```sql
create extension if not exists pgcrypto;   -- gen_random_uuid()
create extension if not exists pg_trgm;
create extension if not exists unaccent;

-- ── Entity registry ────────────────────────────────────────────
-- Her modül tablosunun PK'sı buraya FK. Link, event, tag, search,
-- attachment bu sayede tek ve generic kalır.
create table entity (
  id           uuid primary key default gen_random_uuid(),
  type         text        not null,        -- 'bookmark' | 'feed_item' | 'todo' ...
  title        text        not null default '',
  search_text  text        not null default '',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  archived_at  timestamptz,
  search_vec   tsvector generated always as (
                 to_tsvector('simple', unaccent(title || ' ' || search_text))
               ) stored
);
create index entity_type_idx    on entity (type) where archived_at is null;
create index entity_search_idx  on entity using gin (search_vec);
create index entity_trgm_idx    on entity using gin (title gin_trgm_ops);
create index entity_updated_idx on entity (updated_at desc);

-- ── İlişkiler ──────────────────────────────────────────────────
create table link (
  id         uuid primary key default gen_random_uuid(),
  from_id    uuid not null references entity(id) on delete cascade,
  to_id      uuid not null references entity(id) on delete cascade,
  relation   text not null default 'related',
  created_at timestamptz not null default now(),
  constraint link_no_self check (from_id <> to_id),
  unique (from_id, to_id, relation)
);
create index link_to_idx on link (to_id);

-- ── Activity log (append-only, ASLA update etme) ───────────────
create table event (
  id          bigserial primary key,
  entity_id   uuid references entity(id) on delete set null,
  entity_type text,                          -- denormalize: entity silinse de kalır
  verb        text        not null,          -- 'bookmark.saved', 'pomodoro.finished'
  payload     jsonb       not null default '{}',
  occurred_at timestamptz not null default now()
);
create index event_time_idx on event (occurred_at desc);
create index event_verb_idx on event (verb, occurred_at desc);

-- ── Tag ────────────────────────────────────────────────────────
create table tag (
  id    uuid primary key default gen_random_uuid(),
  name  text not null,
  color text
);
create unique index tag_name_uniq on tag (lower(name));

create table entity_tag (
  entity_id uuid references entity(id) on delete cascade,
  tag_id    uuid references tag(id)    on delete cascade,
  primary key (entity_id, tag_id)
);

-- ── Saved views ────────────────────────────────────────────────
create table saved_view (
  id       uuid primary key default gen_random_uuid(),
  name     text    not null,
  module   text    not null,          -- 'bookmark' | 'rss' | 'opportunity'
  filter   jsonb   not null default '{}',
  sort     text,
  pinned   boolean not null default false,
  position int     not null default 0
);
```

**`title` neden `entity`'de?** Global search, Command Palette ve link listelerinin
15 tabloya join atmadan bir etiket gösterebilmesi için. Modüller yazarken
`entity.title`'ı da günceller (`touch_entity()` helper'ı bunu tek yerde yapar).

---

## 4. Capture modülü — Alembic `0002_capture`

```sql
-- Universal Inbox ve Bookmark Library AYNI tablo.
-- collection='inbox' → Inbox ekranı, diğerleri → Bookmark Library.
-- Sürükle-bırak = tek UPDATE, link ve event kopmaz.
create table bookmark (
  id           uuid primary key references entity(id) on delete cascade,
  url          text        not null,
  url_hash     text        not null,        -- normalize edilmiş URL'in sha256'sı
  description  text,
  selection    text,                        -- "save selected text"
  note         text,
  collection   text        not null default 'inbox',
                 -- inbox | read_later | learning | reference | projects | archive
  source       text        not null default 'extension',
                 -- extension | manual | rss | youtube
  read_status  text        not null default 'unread',
  favorite     boolean     not null default false,
  saved_at     timestamptz not null default now(),
  client_uuid  uuid unique                  -- extension retry idempotency
);
create index bookmark_collection_idx on bookmark (collection, saved_at desc);
create index bookmark_urlhash_idx    on bookmark (url_hash);
```

`url_hash` **unique değil**: aynı sayfayı ikinci kez kaydetmek hata değil.
API `409` yerine `200 + {duplicate: true, existing_id}` döner, extension popup'ı
"zaten kayıtlı — Learning'e taşı?" gösterir.

```sql
create table feed (
  id              uuid primary key references entity(id) on delete cascade,
  url             text not null unique,
  site_url        text,
  category        text,                     -- Development | AI/LLM | YouTube ...
  etag            text,                     -- conditional GET
  last_modified   text,
  last_fetched_at timestamptz,
  last_status     text,
  error_count     int  not null default 0,
  active          boolean not null default true
);

create table feed_item (
  id           uuid primary key references entity(id) on delete cascade,
  feed_id      uuid not null references feed(id) on delete cascade,
  guid         text not null,               -- yoksa sha256(url + title)
  url          text,
  author       text,
  summary      text,
  published_at timestamptz,
  fetched_at   timestamptz not null default now(),
  read_at      timestamptz,
  unique (feed_id, guid)
);
create index feed_item_unread_idx on feed_item (feed_id, published_at desc)
  where read_at is null;
```

**Retention:** okunmamış + kaydedilmemiş `feed_item`'ları 90 günden sonra sil
(cascade `entity`'yi de temizler). Yoksa `entity` tablosu yılda ~50k satır şişer.

```sql
-- Scraper/feed sağlığı — sessiz ölümleri yakalamak için
create table source_run (
  id          bigserial primary key,
  source      text not null,               -- 'rss:<feed_id>' | 'osym' | 'jobhunter'
  started_at  timestamptz not null default now(),
  finished_at timestamptz,
  status      text not null,               -- ok | error | empty
  items_found int  not null default 0,
  error       text
);
```

---

## 5. Extension akışı (MV3)

```
Ctrl+Shift+S / popup / context menu
        ↓
outbox.push({ client_uuid, url, title, selection, collection, tags, note })
        ↓
POST http://127.0.0.1:8787/api/capture
   ├─ 2xx  → outbox'tan sil
   └─ hata → outbox'ta kalır
             chrome.alarms her 60sn + onStartup + onInstalled → flush
```

- `manifest.json` varsayılan localhost iznini taşır; farklı yerel sunucu adresi
  Options ekranından seçildiğinde ilgili origin izni ayrıca istenir.
- Backend `CORSMiddleware` ile `chrome-extension://<id>` origin'ine izin verir
- Popup, backend'e ping atıp offline'sa "kuyruğa alındı (3 bekliyor)" gösterir
- Hızlı kayıt her zaman `collection='inbox'` — kategorizasyon Life OS içinde

---

## 6. RSS worker

- `feedparser` + `httpx`, APScheduler ile feed başına 30dk interval + jitter
- **Conditional GET:** `If-None-Match` / `If-Modified-Since` → 304'te iş yok
- **Catch-up:** worker açılışta bekleyen tüm feed'leri hemen bir tur çeker
  (local-only mimarinin telafisi burada)
- `error_count >= 5` → `active=false` + notification
- OPML import: `POST /api/rss/import` (multipart) → kategori = OPML `outline` grubu
- Item aksiyonları (`Save → Read Later` / `Learning`) **bookmark tablosuna** yazar
  ve `link(feed_item → bookmark, 'saved_from')` kurar

---

## 7. Offline (read-only)

`vite-plugin-pwa` + Workbox:

| Kaynak | Strateji |
|---|---|
| App shell (js/css/html) | precache |
| `GET /api/**` | StaleWhileRevalidate, 200 entry / 7 gün |
| Mutation'lar | offline'da UI disable + banner |

UI disable görünürlüğü iyileştirir; asıl garanti ortak API katmanındadır. Offline
mutation fetch'e ulaşmadan `OfflineWriteError` ile durur.

macOS ve Windows'ta Chrome/Edge → "Install app" ile ayrı pencere.
`localhost` secure context sayıldığı için PWA kurulumu HTTPS olmadan çalışır.

---

## 8. İki haftalık plan

**Hafta 1 — çekirdek + bookmark**

| Gün | İş | Bitti sayılır |
|---|---|---|
| 1 | Repo, docker-compose (postgres/api/worker/web), `.env`, `/health` | `docker compose up` çalışıyor |
| 2 | Alembic `0001_core`, SQLAlchemy modelleri | `alembic upgrade head` temiz |
| 3 | `core/`: `create_entity`, `touch_entity`, `log_event`, `link()`, search sorgusu | pytest ile 5 unit test |
| 4 | `0002_capture` + `POST /api/capture` (idempotent) + `GET /api/bookmarks` | curl ile kayıt + duplicate testi |
| 5 | Frontend iskelet: Vite, Tailwind, TanStack Query/Router, `registerModule()` | boş layout + 2 route |
| 6 | Inbox ekranı: liste, collection'a taşı (dnd-kit), tag ekle | sürükle-bırak çalışıyor |
| 7 | Bookmark Library: filtre, arama, favorite, `saved_view` kaydet | "Unread AI articles" view'ı kaydediliyor |

**Hafta 2 — extension + RSS + Today**

| Gün | İş | Bitti sayılır |
|---|---|---|
| 8 | Extension MV3: popup, kısayol, context menu | tek tıkla kayıt |
| 9 | Extension outbox + retry + offline göstergesi | backend kapalıyken kaydet, açınca gelsin |
| 10 | `0003_rss`, feed CRUD, OPML import | 30 feed import |
| 11 | Worker fetch loop, conditional GET, `source_run` | 10dk'da bir yeni item düşüyor |
| 12 | RSS Reader UI + `Save → Read Later / Learning` + link | item → bookmark akışı |
| 13 | Today v0 (inbox sayısı, unread RSS, son 10 event) + `cmdk` palette | Cmd+K ile "Save bookmark" |
| 14 | PWA/offline cache, `/api/activity` timeline ekranı | uçak modunda liste açılıyor |

**Faz 1 bitti demek:** Tarayıcıda makale görüyorsun → Ctrl+Shift+S (Life OS kapalı
olsa bile) → açınca Inbox'ta → Learning'e sürüklüyorsun → Today'de "3 new" →
Activity'de `bookmark.saved` event'i duruyor.

---

## 9. Sonraki fazlar

| Faz | İçerik | Neden bu sırada |
|---|---|---|
| 2 | Todo + Pomodoro + tekrarli rutinler + Daily/Weekly Review | Tamamlandi; ayri Habit UI yerine Todo rutinleri kullanilir |
| 3 | Opportunity modeli + Job Hunter `SourceAdapter` + Deadline + Notification | Tamamlandi; durable worker batch'i ile calisir |
| 4 | Study Tracker + Courses + Google Calendar + Drive/Documents | Tamamlandi; OAuth yerel loopback'tir |
| 5 | Projects + GitHub, Expenses, Books, Media linkleri | Temel moduller tamamlandi; Media urun gelistirmesi suruyor |

---

## 10. Karara bağlanacaklar

- Port: `8787` (öneri) — 8000 çakışabilir
- Docker Desktop mu native mi? (Windows'ta WSL2 gerekiyor)
- Extension Firefox'ta da lazım mı? (MV3 farkları var, sadece Chromium önerilir)
- Faz 3'te deadline worker için €4 VPS mi, "her sabah aç" disiplini mi?
