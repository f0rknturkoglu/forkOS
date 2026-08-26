# forkOS Mimarisi — yeni modül ekleme rehberi

Bu doküman, yeni bir modül ekleyecek kişinin okuyacağı TEK dokümandır.
Her bölümde gerçek dosya referansları vardır; davranış buradan öğrenilir,
koddan çıkarılmaz.

## 1. entity / link / event üçlüsü

- **`entity`** (`backend/app/core/models.py::Entity`): sistemdeki her kaydın
  kimliği. `id`, `type`, `title`, `search_text`, `archived_at`. Modül
  tablolarının PK'sı `entity.id`'ye FK'dır (kural 1).
- **`link`**: iki entity arasında yönlü ilişki (`from_id → to_id`, `relation`).
  İlişki sözlüğü TEK yerde: `backend/app/core/links.py::RELATIONS`
  (ileri/geri etiket çifti). Yeni ilişki = oraya bir satır.
- **`event`**: append-only aksiyon logu. Anlamlı her aksiyondan sonra
  `log_event(session, verb=..., entity_id=..., entity_type=..., payload=...)`
  çağrılır (`backend/app/core/events.py`). ASLA UPDATE/DELETE edilmez.

Helper'lar: `backend/app/core/entity.py` (`create_entity`, `touch_entity`,
`archive_entity`, `delete_entity`), `backend/app/core/links.py`
(`link`, `unlink`, `related`).

## 2. Kayıt defterleri

| Kayıt defteri | Yer | Görevi |
|---|---|---|
| `MODULES` | `backend/app/modules/__init__.py` | Modül listesi; main.py'ye dokunmadan router'lar otomatik bağlanır |
| `EntityTypeSpec` | aynı dosya | Tip → etiket/rota/ikon (kural 13). Frontend `GET /api/registry/entity-types`'tan beslenir |
| `event_verbs` | `ModuleSpec.event_verbs` | Modülün ürettiği verb'ler |
| `deadline_provider` | `ModuleSpec.deadline_provider` | Son tarih sağlayıcı (kural 16); `GET /api/deadlines` toplar |
| Frontend `registerModule` | `frontend/src/modules/<ad>/index.ts` | Router, Today widget'ları, komut paleti, sidebar |
| İnvalidation haritası | `frontend/src/core/invalidation.ts::AFTER` | Mutation sonrası hangi query key'lerinin tazeleneceği (kural 14) |

**Yeni modül = backend'e bir klasör + `MODULES`'a satır; frontend'e bir klasör +
`src/modules/index.ts`'e import.** Router, arama, Bugün, komut paleti otomatik dolar.

## 3. Bugün widget sözleşmesi

`registerModule({ todayWidgets: [{ component, slot, order }] })`:
- `slot`: `"left" | "center" | "right"` (sütun).
- `order`: zorunlu, küçük önce.
- Widget veri yokken `Empty` bileşenini `variant="inline"` ile gösterir
  (kural: boş durum düz metin değil).
- Agenda `kind`'ları: `calendar | todo | rss | media | opportunity | interview |
  payment | study` (`backend/app/modules/today/schemas.py::AgendaKind`).

## 4. Tasarım tokenları

- Renkler `frontend/src/index.css`'teki CSS değişkenlerinden gelir; JSX'e
  sabit hex yazılmaz (kural 15). Semantik: `accent/ok/warn/danger`; kimlik:
  `kind-*` / `src-*` / `feed-*`; grafik: `chart-1..8`.
- Bileşenler: `frontend/src/core/ui.tsx` — `Chip` (tone semantik, identity
  kimlik rengi; ikisi aynı anda olmaz), `Button/IconButton/Input/Select/
  Textarea/Checkbox/Range/NumberInput/FileInput/Field`.
- Tipografi: `tailwind.config.js` ölçeği (`micro…display-2xl`); keyfi
  `text-[Npx]` yasak.
- Koruyan test: `frontend/src/core/designSystem.test.ts`.

## 5. Tazeleme (kural 14)

Mutation `onSuccess`'inde `invalidateAfter("<olay>")` çağrılır
(`frontend/src/core/invalidation.ts::AFTER`). Olaylar modül yazmasını temsil
eder; hangi key'lerin tazeleneceğine harita karar verir. Ham
`invalidate("a","b")` yasak — koruyan test `frontend/src/core/invalidation.test.ts`.

## 6. Uç disiplini (kural 17)

Backend'de kayıtlı her HTTP ucu frontend'den çağrılmalı ya da silinmeli.
Kontrol: `node frontend/scripts/check-endpoint-coverage.mjs` (eşik 3;
auth yönlendirmeleri + registry sözleşmeleri muaftır).

## 7. Migration

- Elle yazılır, gözden geçirilir (`--autogenerate` çıktısı kontrol edilmeden
  commit edilmez). Her SQL komutu ayrı `op.execute()` (kural 10;
  `tests/test_migrations.py` doğrular).
- `down_revision` her zaman `alembic heads`'teki gerçek head'e verilir;
  dosya adı numarasına güvenilmez (gerçek zincir: `backend/alembic/README.md`).
- View/trigger yazılmaz; son tarihler `deadline_provider` ile toplanır (kural 16).

## 4. Faz 12: study + learning tek modül

- `study` modülü `learning`'e birleştirildi (`backend/app/modules/learning/`).
  Tablolar AYNEN durur (`study_area`, `study_topic`, `course`); birleşen
  şey modül ve sayfa. `MODULES`'ta tek `learning` kaydı var.
- Uç yolları korunur: `/study/*` (alanlar/konular) ve `/courses` aynı
  router altında, yollar değişmedi. Frontend'de `/learning` ve `/study`
  aynı sayfaya gider.
- Konu ↔ kaynak bağı link üzerinden kurulur:
  `link(from=study_topic, to=course|media_item, relation="learns_from")`.
  İlişki sözlüğüne `RELATIONS["learns_from"]` eklendi; frontend'de
  `RelatedPanel` `relation` prop'u ile yalnız o ilişkiyi gösterir ve
  yeni bağları o ilişkiyle kurar.
- Eski modül klasörleri tamamen silindi (`backend/app/modules/study/`,
  `frontend/src/modules/study/`); sidebar "Takip" grubunda tek giriş var.
- Not: `learning.write` invalidation'ı `related` anahtarını da tazeler
  (bağ kurma konu detayına anında yansır).
