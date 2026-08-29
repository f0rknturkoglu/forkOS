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

## Faz 13: "bugüne al" — plan, son tarih değil

- Plan (`plan_slot`) ile son tarih (`due_at`) ayrı kavramlardır:
  plan = "bugün yapmayı planlıyorum", due_at = "teslim". Göreve plan
  vermek ASLA `due_at` yazmaz — yarın gecikmiş görünmemesi için.
- Görev eklerken `POST /todos` gövdesine `plan_day` (ISO tarihi) verilirse
  `todo_service.create()` aynı transaction içinde o gün için plan slotu da
  yazar (desen: `backend/app/modules/review/service.py` — `create()` +
  `schedule()` tek commit). İki ayrı istek yoktur; ikincisi başarısız olursa
  görev yarı yazılmış kalırdı. Event'ler ikisi de yazılır: `todo.created` +
  `plan.scheduled` (kural 3), yeni verb uydurulmaz.
- `plan_day` geçmiş bir gün olabilir — `schedule()` ile aynı semantik
  (kısıt yok); planner geçmişe de yazabilir. "Bugün"ü FRONTEND üretir ve
  tek kaynağı vardır: `frontend/src/lib/date.ts::localDateKey`
  (Europe/Istanbul) — agenda'nın sorduğu günle aynı helper. Tarayıcının
  yerel saatine göre gün üreten ikinci bir helper yoktur (Faz 13'te
  `TodayAgendaWidget`'taki `localDay` kaldırıldı; koruyan test
  `frontend/src/lib/dateUsage.test.ts`).
- Mutation sonrası tazeleme, tek istek iki yazma içerdiği için
  `invalidateAfter("todo.write", "plan.write")` ile yapılır (kural 14).
- `TodoComposer` "bugüne al" onay kutusu gönderir: varsayılan KAPALI, son
  seçim `localStorage["todo.planToday"]`'da hatırlanır. Formda plan ile son
  tarih ayrı etiketlenir ("bugüne al" vs "Son tarih").

## Faz 15: secret güvenli yedekleme

- Secret ayar sınıflandırması TEK kaynakta: `backend/app/modules/system/
  secrets.py::SECRET_SETTING_KEYS`. İsimde "key" geçmesine güvenilmez;
  açık listedir. Yeni secret ayar eklenirken key bu listeye yazılmalıdır
  (koruyan test `backend/tests/test_backup_secrets.py` kod taraması yapar).
- Yedek/export aynı politikayı kullanır (`export.public_rows`): secret
  setting satırları payload'a HİÇ yazılmaz — boş veya maskeli değer bile
  değil. Tema, widget düzeni, Pomodoro ve kaynak aralıkları yedekte kalır.
  `oauth_token` tablosu ayrıca dışlanmaya devam eder.
- Eski yedeklerdeki secret satırları restore/import tarafından atlanır
  (`restore` `secret_skipped` sayacı bildirir).
 - **Eski yedekler otomatik güvenli hâle gelmez**: diskteki dosya içeriği
   değişmez. Geçmişte alınmış yedeklerdeki API anahtarlarının döndürülmesi
   (rotation) önerilir.

## Faz 16: merge import ile gerçek disaster restore ayrımı

- `/backup/restore` **birleştirerek içe aktarır**: `ON CONFLICT DO NOTHING`,
  mevcut kayıtlara dokunulmaz, eksikler eklenir; idempotent. UI'da "Geri
  yükle" değil "Birleştirerek içe aktar" olarak adlandırılır.
- `/backup/inspect` preflight'tır: hiçbir şey yazmadan versiyon, tablo/satır
  sayıları, bilinmeyen tablolar, eksik bölümler, secret setting satırları ve
  manifest bütünlüğünü raporlar. Frontend bu raporu gösterip onaylatır.
- Backup formatı v2: `manifest` (app, exported_at, row_counts) eklendi —
  payload'ın kendi kendini doğrulaması. v1 yedekler okunmaya devam eder;
  v3+ bilinmeyen sürümler reddedilir.
- **Gerçek felaket kurtarması app dışıdır**: `make disaster-restore
  FILE=... CONFIRM=DISASTER-RESTORE`. Sıra: API/worker durur → mevcut DB'nin
  pg_dump güvenlik yedeği → temiz schema → migration → yedek yükleme →
  entity/link/event + self-FK bütünlük doğrulaması. Hata durumunda güvenlik
  yedeğinin yolu raporlanır. Normal FastAPI endpoint'inden tablo
  truncate/event DELETE yapılmaz; bu CLI, dokümante edilmiş ayrı bir
     disaster recovery sınırıdır. UI'da tek tık destructive buton yoktur.

## Faz 17: ortak task creation intent'i

- Backend'de görev oluşturmanın TEK sınırı `todo.service.create()`'dir.
  Context adapter'ları delege eder ve kendi ilişkisini aynı transaction'da
  yazar: opportunity (`application_step` link'i), learning
  (`/study/topics/{id}/todos` → `prepares_for` link'i, tek istek), project
  GitHub import (tag + proje bağı `search_text` kwarg'ı ile). Koruyan test
  `backend/tests/test_todo_creation_boundary.py`: todo modülü dışında
  `Todo(...)` kurulumu / `create_entity(type='todo')` yasaktır.
- Frontend'de ortak katman `frontend/src/core/tasks.ts::createTask`:
  intent (title, description, priority, due_at, plan_day, recur, tags,
  parent/project/milestone) → tek POST /todos. "Bugüne al" tercihi burada
  yaşar (`localStorage["todo.planToday"]`): `plan_day` üretir, ASLA `due_at`
  üretmez. Koruyan test `frontend/src/core/taskCreation.test.ts` bileşen
  dosyalarında dağınık `post("/todos"` kullanımını yasaklar.
- Bütün manuel girişler (TodoComposer, alt görev, ProjectTodos, DropCapture,
  `todo.quick`) aynı tercihi ve `invalidateTaskWrite()`'ı kullanır
  (`todo.write` + `plan.write`). Command Palette artık zorla /todos'a
  yönlendirmez; başarı toast'ı verir ("bugüne planlandı" rozetli).
- Otomatik üretilen rutin occurrence'ları (`_spawn_next_occurrence`) bu
  katmandan geçmez ve kullanıcı istemedikçe plana yazılmaz.
## Faz 18: sistem genelinde görünür entity ilişkileri

- `RelatedPanel` (`frontend/src/core/RelatedPanel.tsx`) her linklenebilir
  entity'nin detay/focus yüzeyinde ilişkileri gösterir: Todo (`?focus`),
  Project (detay kolonu), Opportunity, Learning konu, Media detay,
  Bookmark (`?focus`), Document (`?focus`), Finance harcama/ödeme (`?focus`).
  Liste satırlarına büyük panel basılmaz; yalnız seçili/focused entity için.
- İlişki etiketleri ve yönü yalnızca backend `RELATIONS` sözlüğünden gelir;
  frontend'de relation/type→route sabiti yoktur (`entityRoute`/`typeLabel`).
- Link ekleme/kaldırma `invalidateAfter("link.write")` kullanır; kendine
  bağlama ve duplicate (`link_uniq`) backend'de engellenir. Koruyan testler:
  `frontend/src/core/relatedSurfaces.test.ts` (tip→yüzey matrisi),
  `backend/tests/test_links_api.py` (self/duplicate/direction/labels).

