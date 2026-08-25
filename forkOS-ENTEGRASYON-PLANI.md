# forkOS — Bütünleşme, Temizlik ve Tasarım Tekleştirme Planı

> **Hazırlanma tarihi:** 25 Ağustos 2026
> **Kapsam:** `backend/`, `frontend/`, `extension/`, `db/migrations`
> **Amaç:** Birbirine değmeyen 16 backend + 18 frontend modülünü tek bir programa
> dönüştürmek; ölü kodu ayıklamak; tüm çip/rozet/buton/etiket dilini tekleştirmek.
>
> Bu doküman üç parçadan oluşur:
> 1. **Bölüm 1–2** — kanıta dayalı mevcut durum analizi (dosya/satır referanslı)
> 2. **Bölüm 3–4** — 8 faza bölünmüş, bağımlılık sırasına dizilmiş plan
> 3. **Bölüm 5** — her faz için doğrudan bir agent'a verilebilir prompt

---

## 1. Mevcut durum — ölçümler

| Ölçüm | Değer |
|---|---|
| Backend uygulama kodu (vendored hariç) | ~15.100 satır |
| Vendored `app/sources/forkjob_core/` | ~14.700 satır (backend'in yarısı) |
| Frontend `src/` | ~16.900 satır |
| Backend modülü | 16 (`app/modules/__init__.py`) |
| Frontend modülü | 18 (`src/modules/index.ts`) |
| OpenAPI path sayısı | 138 |
| **Frontend'de hiç çağrılmayan path** | **~30** |
| Alembic migration | 28 |
| Frontend testi | 39 dosya / 147 geçiyor · **1 dosya tamamen `describe.skip`** |
| Backend testi | 23 dosya (Postgres gerektirenler `make test` ile) |
| `link()` çağrısı (modüller arası bağ) | **6 yer** |
| `log_event()` verb'ü | 78 |

**Baseline doğrulandı:** `npx vitest run` → 39 dosya geçiyor, 1 dosya skip.
Backend testleri `_test` ile biten DB ister (`app/core/test_guard.py`), yerelde
`make test` ile koşar.

### Modül haritası (backend ↔ frontend eşleşmesi)

| Backend modülü | Frontend modülü | Durum |
|---|---|---|
| bookmark | bookmarks + inbox | ✅ eşleşiyor (tek tablo, `collection` ayırıcı) |
| rss | rss | ✅ |
| todo | todo | ✅ |
| today | today | ✅ |
| pomodoro | pomodoro | ✅ |
| **habit** | **— yok** | ❌ **Tam ölü**: `/habits` rotası `TodoPage`'e gidiyor |
| review | review | ✅ |
| opportunity | opportunity | ✅ (ama `/sources` sayfası da burada) |
| study | study | ✅ |
| learning | learning | ✅ |
| document | documents | ✅ |
| calendar | calendar | ✅ |
| media | media | ⚠️ Backend 7 yüzey sunuyor, frontend 2 rota kayıtlı |
| project | projects | ✅ |
| finance | finance | ✅ |
| system | settings + health | ⚠️ İki frontend modülü tek backend modülünü paylaşıyor |
| — | activity | Çekirdek (`core/router.py`) tüketiyor |

---

## 2. Bulgular

### 2.1 Entegrasyon boşlukları (asıl sorun)

#### B1 — Çekirdek `link` altyapısı frontend'de hiç kullanılmıyor
`entity`/`link` şeması projenin temel taşı; `POST /api/links`, `DELETE /api/links`
ve `GET /api/entities/{id}/related` uçları çalışıyor. **Frontend'de tek bir çağrı yok.**

```
backend/app/core/router.py     → create_link / delete_link / related
frontend/src/**                 → "/links" ve "/entities/" araması: 0 sonuç
```

Sonuç: "her şey birbirine bağlanabilir" vaadi veritabanında duruyor, ekranda yok.
Hiçbir detay sayfasında "İlgili kayıtlar" paneli bulunmuyor.

#### B2 — Modüller arası bağ sadece 6 yerde, hepsi tek yönlü ve gizli

| Bağ | Yer | Frontend'de görünür mü? |
|---|---|---|
| `feed_item → bookmark` (`saved_from`) | `modules/rss/service.py:307` | Kısmen (RSS'te "kaydet") |
| `todo → project` (`belongs_to`) | `modules/todo/service.py:177,198` | Rozet var, hedefi yanlış (aşağıda) |
| `opportunity → todo` (`application_step`) | `modules/opportunity/router.py:203` | ❌ **UI yok** |
| `payment → expense` (`paid_as`) | `modules/finance/service.py:124` | ❌ UI yok |
| `collection → item` (media) | `modules/media/service.py:1384` | ❌ UI yok |
| `entity → project` (`belongs_to`) | `modules/project/service.py:240` | Kısmen |

Olması gerekip **hiç olmayan** bağlar:
- Fırsat → yer imi (kullanıcının açıkça istediği: "fırsat sekmesinde bookmark'ladığımda nereye gider")
- Medya ↔ yer imi / todo
- Belge ↔ proje
- Çalışma konusu (`study_topic`) ↔ todo / pomodoro
- Kurs / kitap (`learning`) ↔ yer imi kuyruğu dışında hiçbir şey
- Takvim olayı ↔ görev

#### B3 — Proje todo'su ile normal todo listesi arasındaki bağ yarım
Backend doğru: `ProjectTodos`'tan eklenen görev `todo` tablosuna düşüyor ve
`/api/todos` hepsini döndürüyor. Ama:

- `TodoRow.tsx:160` — proje rozeti `#/projects` genel sayfasına gidiyor,
  **o projeye değil**. Tıklayınca kullanıcı hangi projeye ait olduğunu kaybediyor.
- `ProjectTodos.tsx` yazınca `invalidate("project-todos", "todos", "activity", "tags")`
  çağırıyor; **`today-agenda` yok**. Yani projeye eklenen görev Bugün panelinde
  sayfa yenilenene kadar görünmüyor.
- `TodoPage`'de "projeye göre filtrele" yok.

#### B4 — `today-agenda` cache'ini kimse geçersiz kılmıyor
```
frontend/src/modules/today/TodayAgendaWidget.tsx:85  queryKey: ["today-agenda", day]
```
Bu anahtarı `invalidate()` ile tazeleyen **tek yer widget'ın kendisi**. Todo, plan,
medya, RSS ya da takvim yazan hiçbir modül Bugün'ü tazelemiyor. Agenda 5 kaynağı
birleştiriyor (`modules/today/service.py`) ama hiçbirinin yazması ona ulaşmıyor.

Daha genel sorun: **merkezi bir invalidation haritası yok**. 40+ farklı
`invalidate("a","b","c")` çağrısı elle yazılmış; yeni bir tüketici eklenince
hangi çağrı yerlerinin güncelleneceğini kimse bilmiyor.

#### B5 — `deadline_v` görünümü elle yazılmış SQL union, kayıt defteri değil
```
backend/alembic/versions/0016_finance.py:35  create view deadline_v as ... union all ...
```
Şu an sadece `opportunity`, `todo`, `recurring_payment` var. Eksikler:
proje milestone'ları, medya çıkış tarihleri, mülakat (`opportunity_interview.scheduled_at`),
takvim olayları. Yeni bir son-tarihi olan modül eklemek **migration yazmayı**
gerektiriyor — bu, "modül eklemek main.py'ye dokunmayı gerektirmez" kuralının
veritabanı tarafındaki ihlali.

#### B6 — Üç ayrı, elle senkronize edilen tip→etiket/rota haritası
| Dosya | İçerik | Kapsadığı tip |
|---|---|---|
| `backend/app/core/search.py:60` `SEARCH_LABELS` | tip → İngilizce grup adı | 14 |
| `frontend/src/core/GlobalSearch.tsx:8` `ROUTE_FOR` | tip → hash rota | 15 |
| `frontend/src/core/GlobalSearch.tsx:41` `TYPE_LABELS` | tip → Türkçe etiket | 14 |

Üçü de birbirinden habersiz. Eksik tipler: `habit`, `review`, `media_collection`,
`media_cycle`, `external_event`, `pomodoro_session`, `milestone`. Yani global
aramada bu kayıtlar ya çıkmıyor ya da tıklanınca `#/` ana sayfaya atıyor.

`ModuleSpec.entity_types` alanı backend'de zaten tanımlı ve doğru dolu —
**ama hiç okunmuyor**.

#### B7 — Bugün paneline hiç katkı vermeyen modüller
Widget veren: today(3), activity(2), opportunity(3), bookmarks(1), inbox(1+stat),
rss(stat), pomodoro(1), review(1), study(1), media(1), projects(1), finance(1).

**Hiç katkı vermeyen:** `calendar`, `documents`, `learning`, `todo`, `health`, `settings`.
(`todo` ve `calendar` dolaylı olarak agenda'ya giriyor ama kendi widget'ları yok;
`learning` ve `documents` Bugün'de tamamen görünmez.)

#### B8 — `health` modülü `opportunity` modülünden import ediyor
```
frontend/src/modules/health/widgets/SourceHealthWidget.tsx:7
  import { sourceLabel } from "@/modules/opportunity/labels";
```
Modüller arası doğrudan import. `sourceLabel` çekirdeğe (core) ait bir yardımcı.
Ayrıca aynı `MiniStat` bileşeni `SourceHealthWidget.tsx` ve `RssHealthWidget.tsx`
içinde iki kez kopyalanmış.

Buna ek olarak kaynak sağlığı **üç yerde** gösteriliyor:
`/sources` (opportunity modülü), `/health` (health modülü), `SettingsPage`
(SettingsSourceHealth). Üçü de farklı görünüyor.

---

### 2.2 Ölü kod ve referanssız yüzey

#### D1 — `habit` modülü tamamen ölü
```
backend/app/modules/habit/          (models, router, schemas, service)
backend/alembic/versions/0007_habit_review.py   (habit, habit_log tabloları)
API: GET/POST /api/habits, PATCH/DELETE /api/habits/{id},
     POST /api/habits/{id}/check, GET /api/habits/grid
```
Frontend'de tek çağrı yok. `/habits` rotası `TodoPage`'i `routineOnly` filtresiyle
açıyor (`modules/todo/index.ts:15`, `TodoPage.tsx:42`). İşlevi `todo.recur`
kolonu devralmış (`0023_todo_recur.py`).

**Karar gerekiyor:** modülü + tabloları kaldır, ya da alışkanlık ızgarasını
(`/habits/grid`) gerçekten ekrana getir. Ara durum kabul edilemez.

#### D2 — `MediaFrontend.test.tsx` tamamen skip — yazılmış ama kurulmamış bir IA
```
frontend/src/modules/media/MediaFrontend.test.tsx:171  describe.skip(...)
```
Test 7 rota bekliyor:
`/media`, `/media/library`, `/media/collections`, `/media/upcoming`,
`/media/stats`, `/media/trash`, `/media/:id`
`modules/media/index.ts` sadece **2 tanesini** kaydediyor.

Karşılık gelen backend uçları **çalışır durumda ve frontend'den hiç çağrılmıyor:**
```
GET/POST   /api/media/collections
PATCH/DEL  /api/media/collections/{id}
POST/DEL   /api/media/collections/{id}/items/{item_id}
GET        /api/media/dashboard
GET        /api/media/upcoming
POST       /api/media/{id}/restore
DELETE     /api/media/{id}/permanent
```
352 satırlık bir test dosyası, kurulmamış bir ürünün sözleşmesini tutuyor.

#### D3 — Frontend'den hiç çağrılmayan diğer uçlar

| Uç | Not |
|---|---|
| `POST /api/links`, `DELETE /api/links` | B1 — çekirdek bağ API'si |
| `GET /api/entities/{id}/related` | B1 |
| `GET/POST /api/views`, `DELETE /api/views/{id}` | Saved view: tablo + API var, UI yok |
| `GET/POST /api/opportunities/{id}/todos` | B2 — başvuru adımı |
| `POST /api/opportunities/{id}/trash` · `/restore` | Çöp akışı yarım |
| `POST /api/pomodoro/{id}/pause` · `/resume` | Migration `0022_pomodoro_pause` boşa gitmiş |
| `POST /api/recurring-payments/{id}/pay` | `recurring.paid` verb'ü hiç üretilemiyor |
| `DELETE /api/study/areas/{id}` | Alan silinemiyor |
| `GET /api/habits/*` | D1 |
| `GET /api/bookmarks/collections` | `COLLECTIONS` sabiti frontend'de hardcoded |
| `POST /api/notifications/dismiss-all` | Panelde "tümünü kapat" yok |
| `GET /api/github/activity`, `POST /api/github/sync` | `core/contributions.py` — proje bazlı uçtan farklı |
| `GET /api/documents/{id}/open` | Belge açma |

#### D4 — Kullanılmayan frontend export'ları

```
core/registry.ts   :: enabledModules, todayColumns, todayWidgetsIn,
                      pinnedModules, groupedModules          → hiç çağrılmıyor
core/api.ts        :: isOnline, assertOnlineWrite             → dışarıdan çağrılmıyor
core/ui.tsx        :: Card, Toast                             → kullanılmıyor
core/types.ts      :: DayEvent, GithubCommit, GithubActivity,
                      MediaLink, SavedView, SourceSyncItem    → ölü tip
lib/date.ts        :: APP_TIME_ZONE
modules/rss/RssWidget.tsx :: RssWidget                        → dosya hiç import edilmiyor
modules/media/shared.tsx  :: kindColor, srcColor
modules/opportunity/labels.ts :: KIND_ORDER, StatusTone
modules/opportunity/SyncProgress.tsx :: useSourceSync
modules/rss/RssPage.tsx :: RSS_SAVE_REFRESH_KEYS
modules/finance/RecurringWidget.tsx :: RECURRING_WIDGET_KEY
modules/today/weather.ts :: Forecast
```

#### D5 — `ModuleSpec`'te hiç okunmayan alanlar
```
frontend/src/core/types.ts
  icon?           → 18 modülün hepsi lucide ikonu import ediyor.
                    AppHeader.ModuleTab ikonu ÇİZMİYOR. Bundle'da boşuna duruyor.
  searchLabel?    → 2 modülde tanımlı, hiçbir yerde okunmuyor
  enabledByDefault? → hiç kullanılmıyor
  TodayWidget.zone → her widget'ta yazılı; sadece ölü todayWidgetsIn() okuyor.
                     Gerçek yerleşim `slot` + `order` ile yapılıyor.
```

#### D6 — Vendored `forkjob_core` içinde erişilmeyen modüller
```
app/sources/forkjob_core/balance.py   255 satır   0 referans
app/sources/forkjob_core/dedup.py     223 satır   0 referans
app/sources/forkjob_core/discover.py  239 satır   0 referans
app/sources/forkjob_core/sponsors.py             0 referans
```
(Scraper dosyaları `scrapers/index.py` üzerinden dinamik yükleniyor — onlar ölü değil.)

#### D7 — `today_count()` (`modules/todo/service.py`) ve `get_entities()`
(`core/entity.py`) hiçbir yerden çağrılmıyor.

---

### 2.3 Tasarım tutarsızlıkları

**İyi haber:** token altyapısı sağlam. `src/index.css` semantik değişkenleri
(`--accent`, `--success`, `--warning`, `--danger`, `--kind-*`, `--src-*`, `--heat-*`)
hem açık hem koyu tema için kontrast oranlarıyla tanımlı; `tailwind.config.js`
bunları semantik sınıflara bağlıyor; JSX'te ham palet sınıfı (`bg-blue-500` gibi)
**yok**. Sorun tokenlarda değil, **onları kullanan katmanda**.

#### T1 — Üç ayrı çip/rozet sistemi yan yana yaşıyor

| Sistem | Yer | Görünüm |
|---|---|---|
| `Badge tone=` | `core/ui.tsx:BADGE_STYLES` | dolgu + kenarlık + semantik renk |
| `kindChip(kind)` | `modules/media/shared.tsx:52` | sadece kenarlık + kimlik rengi, dolgu yok |
| `PRIORITIES[].chip` | `modules/todo/priority.ts:7` | kendi string'i, `Badge` kullanmıyor |
| `STATUS_TONES` | `modules/opportunity/labels.ts:36` | `Badge`'e ton besliyor (tek doğru olan) |

Aynı ekranda medya çipi (içi boş) ile fırsat rozeti (içi dolu) yan yana çıkıyor.

#### T2 — Ham HTML kontrolleri tasarım sistemini es geçiyor
`core/ui.tsx` içinde `Button`, `IconButton`, `Input`, `Select`, `Textarea`, `Field`
tanımlı. Buna rağmen:

```
Ham <input>  : 21 dosyada 40+ kullanım (SettingsPage 6, JobhunterSettings 4, RssPage 3…)
Ham <select> : 10 dosyada (OpportunityDetail tek başına 5)
Ham <button> : 43 dosyada
```
Örnek — `modules/learning/LearningPage.tsx:23`:
```tsx
<input ... className="min-w-0 flex-1 rounded border border-subtle bg-canvas px-3 py-2 text-body"/>
```
`Input` bileşeni `h-9 rounded-control ... focus:ring-accent` kullanıyor. İkisi
farklı yükseklikte, farklı köşe yarıçapında ve farklı focus halkasında.

#### T3 — Ölçek dışına çıkan tipografi
`tailwind.config.js` altı adımlı bir ölçek tanımlıyor (`micro/meta/body/heading/title/display`)
ve "keyfi değer yazma" diyor. Buna rağmen **28 dosyada 60+ `text-[Npx]`** var:
```
TodoRow.tsx 8 · CalendarPage.tsx 6 · TodayHero.tsx 5 · OpportunityList.tsx 5
ui.tsx 4 · CommandPalette.tsx 4 · AppHeader.tsx 3 …
```
Kullanılan değerler: 10px, 10.5px, 11px, 13px, 17px, 22px, 24px, 26px — yani
ölçeğin yanına ikinci bir gayrıresmi ölçek doğmuş.

#### T4 — Köşe yarıçapı iki dilde
`borderRadius: { control: 4px, card: 5px, overlay: 6px }` tanımlıyken
20 dosyada `rounded-md/lg/xl/2xl/full` kullanılıyor (`TodoRow.tsx` tek başına 10 kez).

#### T5 — JSX'te sabit hex — tema kırılıyor
```
modules/finance/FinancePage.tsx:15-24
  #6C4CFF #FF4E45 #1DB954 #F97316 #3693F6 #F59E0B #EF4444 #14B8A6 #EC4899 #8B5CF6 #64748B
```
`index.css` açıkça "JSX'e ASLA sabit renk yazma" diyor. Bu 11 renk donut/kategori
grafiği için; koyu temada olduğu gibi kalıyor ve kontrastı düşüyor.
**Eksik olan şey:** `--chart-1..--chart-8` gibi bir grafik paleti tokenı.

#### T6 — İsimlendirme kayması
7 dosyada `import { Section as Panel }` yazılmış. `core/ui.tsx` hem `Panel` hem
`Section` hem `Surface` hem `Card` export ediyor; dördü de neredeyse aynı kutuyu
çiziyor (`rounded-card border border-subtle bg-surface shadow-card`). `Card`
zaten hiç kullanılmıyor (D4).

#### T7 — Okunamayan sayfalar (tek satıra sıkıştırılmış JSX)
| Dosya | En uzun satır |
|---|---|
| `modules/learning/LearningPage.tsx` | **2.596 karakter** |
| `modules/settings/SettingsPage.tsx` | **2.171 karakter** |
| `modules/study/StudyPage.tsx` | 1.528 |
| `modules/documents/DocumentsPage.tsx` | 1.038 |
| `modules/finance/RecurringWidget.tsx` | 593 |
| `modules/opportunity/OpportunityWidget.tsx` | 495 |

Bunlar "dağınık modüller"in görünen yüzü: aynı etiket sözlüğü (`{watch:"İzle",…}`)
`LearningPage` içinde **iki kez** kopyalanmış, çünkü satır o kadar uzun ki
tekrar fark edilmiyor.

---

### 2.4 Yapısal borç

#### Y1 — Migration dosya adları gerçek sırayı yalanlıyor
```
0021_media_item      → 0022_pomodoro_pause → 0023_todo_recur → 0024_todo_milestone
→ 0025_document_folder_source → 0026_media_domain → 0022_finance_sub → 0023_application_crm
```
Zincir doğrusal ve sağlam, ama `0022_finance_sub`'ın `down_revision`'ı
`0026_media_domain`. Yani **gerçek head `0023_application_crm`**, dosya adına
bakan biri `0026`yı sanır. Bir sonraki revision'ı yanlış ataya bağlama riski yüksek.

#### Y2 — Dev servisler tek dosyada şişmiş
```
modules/media/service.py     1.545 satır
modules/opportunity/service.py 771 satır
modules/opportunity/router.py  522 satır
modules/rss/service.py         508 satır
modules/media/sync.py          504 satır
modules/todo/service.py        501 satır
modules/media/schemas.py       483 satır
```
`AGENTS.md` reçetesi modül başına `models/schemas/service/router` diyor; media ve
opportunity bu reçeteyi aşmış durumda (media zaten `sync.py`, `artwork.py`,
`providers/` ile bölünmeye başlamış — yarım kalmış).

#### Y3 — Test dağılımı çok dengesiz
```
media 11 · today 4 · opportunity 3 · settings 2 · todo/rss/review/projects/pomodoro/activity 1
study 0 · learning 0 · inbox 0 · health 0 · finance 0 · documents 0 · calendar 0 · bookmarks 0
```
En dağınık sayfaların (learning, study, documents) hiç testi yok.

#### Y4 — `frontend/dist/` ve `backend/backups/*.json.gz` repoda
`dist/` derlenmiş çıktı, `backups/` kişisel veri. `.gitignore` kontrol edilmeli.

---

## 3. Faz planı — genel bakış

Sıralama mantığı:
**önce silmeyeceğin kodu belirle → sonra sil → sonra sildiğin şeyin kalanını
tektipleştir → sonra altyapıyı kur → sonra altyapının üstüne özellik koy → sonra
kilitle.** Silmeden önce restyle etmek, atacağın koda emek harcamak demektir.

| Faz | Ad | Neden bu sırada | Tahmini büyüklük |
|---|---|---|---|
| **0** | Zemin: envanter, kararlar, emniyet ağı | Sonraki her faz bu kararlara dayanıyor | S |
| **1** | Ölü kod ve referanssız yüzey temizliği | Kalan kodu küçült; sonraki fazlar daha az dosyaya dokunsun | M |
| **2** | Tasarım dili tekleştirme | Faz 3–5'te yazılacak yeni UI'ın zemini | L |
| **3** | Çekirdek entegrasyon altyapısı | Modüller arası akışların dayanacağı sözleşmeler | L |
| **4** | Modüller arası akışlar | Kullanıcının asıl istediği bağlar | L |
| **5** | Bugün / Dashboard tam entegrasyonu | Tüm modüllerin tek ekranda buluşması | M |
| **6** | Modül içi toparlama ve sayfa disiplini | Dağınık sayfaların yeniden yazımı | M |
| **7** | Guardrail, test ve dokümantasyon | Kazanımın geri kaymasını engelle | M |

**Bağımlılık grafiği**
```
Faz 0 ──┬── Faz 1 ──┬── Faz 2 ──┬── Faz 4 ── Faz 5 ── Faz 6 ── Faz 7
        │           │           │
        └───────────┴── Faz 3 ──┘
```
Faz 2 ve Faz 3 paralel yürütülebilir (biri frontend tasarımı, diğeri çoğunlukla
backend sözleşmesi). Faz 4 ikisini birden bekler.

---

## 4. Fazlar — detay

### FAZ 0 — Zemin: envanter, kararlar ve emniyet ağı

**Hedef.** Sonraki 7 fazın dayanacağı kararları yazılı hale getirmek ve
"neyi bozduğumu nasıl anlarım" sorusuna cevap üretmek.

**Kapsam**
1. `make test` ve `npx vitest run` ile temiz baseline al, çıktıyı
   `docs/faz0-baseline.md`'ye yaz.
2. Aşağıdaki **karar noktalarını** karara bağla (bunlar kod değil, yön kararı):
   - **K1 — `habit` modülü:** kaldır mı, ekrana getir mi? (Öneri: kaldır; işlevi
     `todo.recur` devralmış. Ama `habit_log`'da veri varsa önce todo'ya taşıyan
     bir migration gerekir.)
   - **K2 — Medya IA'sı:** `MediaFrontend.test.tsx`'in tarif ettiği 7 rota
     kurulacak mı? (Öneri: evet, Faz 4'te — backend zaten hazır.)
   - **K3 — `saved_view`:** kullanılacak mı, kaldırılacak mı? (Öneri: Faz 4'te
     bookmark + fırsat + medya listelerine "görünümü kaydet" olarak bağla.)
   - **K4 — Kaynak sağlığı tek yer:** `/sources`, `/health`, `SettingsPage`'den
     hangisi kalacak? (Öneri: `/health` tek yetkili sayfa; `/sources` ona
     yönlendirsin; Settings'te sadece özet satır kalsın.)
   - **K5 — `pause/resume` ve `recurring pay`:** UI'ya çıkacak mı, uç silinecek mi?
     (Öneri: UI'ya çıkar — ikisi de tek düğmelik iş.)
3. Kararları `docs/faz0-kararlar.md`'ye yaz; her karar için "neden" bir cümle.
4. `.gitignore`'u doğrula: `frontend/dist/`, `backend/backups/`, `*.pyc`,
   `.pytest_cache`, `.ruff_cache`, `tsconfig.tsbuildinfo`, `.DS_Store`.

**Çıktı.** `docs/faz0-baseline.md`, `docs/faz0-kararlar.md`, temizlenmiş `.gitignore`.

**Kabul kriteri.** Beş karar da yazılı ve gerekçeli. Baseline test çıktısı kayıtlı.
Kod davranışı değişmemiş.

---

### FAZ 1 — Ölü kod ve referanssız yüzey temizliği

**Hedef.** `docs/faz0-kararlar.md`'ye göre silinecekleri silmek. **Hiçbir yeni
özellik eklenmez.** Bu fazın tek başarı ölçüsü: satır sayısı düşerken tüm testler
geçiyor.

**Kapsam — Frontend**
1. `src/modules/rss/RssWidget.tsx` sil (hiç import edilmiyor).
2. `core/registry.ts`'ten sil: `todayColumns`, `todayWidgetsIn`, `pinnedModules`,
   `groupedModules`. `enabledModules`'ü `export` olmaktan çıkar (dosya içi kalsın).
3. `core/ui.tsx`'ten `Card`'ı sil (`Surface` ile birebir aynı ve kullanılmıyor).
   `Toast` tipini `ToastProvider` içine al.
4. `core/types.ts`'ten sil: `DayEvent`, `GithubCommit`, `GithubActivity`,
   `MediaLink`, `SourceSyncItem`. (`SavedView` — K3 kararına bak.)
5. `ModuleSpec`'ten `searchLabel` ve `enabledByDefault` alanlarını sil; iki
   modülün index.ts'inden `searchLabel` satırlarını kaldır.
6. **`icon` kararı:** ya `AppHeader.ModuleTab`'da ikonu çiz (öneri: çiz, sekme
   şeridinde `<Icon size={13}/>` + başlık), ya da 18 modülden ikon importunu kaldır.
   Ara durumu bırakma.
7. **`TodayZone` kararı:** `zone` alanını `TodayWidget`'tan ve 18 modülün
   widget tanımından sil (yerleşim `slot` + `order` ile yapılıyor). `TodayZone`
   tipini ve `normalize()` içindeki `zone: "rhythm"` varsayılanını kaldır.
8. Kullanılmayan yerel export'ları sil: `kindColor`, `srcColor` (media/shared),
   `KIND_ORDER`, `StatusTone` (opportunity/labels), `useSourceSync`,
   `RSS_SAVE_REFRESH_KEYS`, `RECURRING_WIDGET_KEY`, `Forecast`, `APP_TIME_ZONE`.
   (`isOnline`/`assertOnlineWrite` **kalsın** — `api.ts` içinde kullanılıyorlar,
   sadece `export` gereksizse kaldır.)

**Kapsam — Backend**
9. K1 kararına göre `habit`:
   - **Kaldırılacaksa:** `app/modules/habit/` sil, `MODULES` listesinden çıkar,
     `habit`/`habit_log` tablolarını düşüren migration yaz (varsa veriyi
     `todo` + `recur` olarak taşıyan adımla birlikte), `verbs.ts`'ten
     `habit.checked`/`habit.deleted` etiketlerini kaldır, `AGENTS.md`'deki
     "`habit_log` dokümante edilmiş istisnadır" cümlesini güncelle.
   - **Kalacaksa:** Faz 4'e "habit grid ekranı" görevi olarak taşı, burada dokunma.
10. `app/sources/forkjob_core/` içinden sil: `balance.py`, `dedup.py`,
    `discover.py`, `sponsors.py` (0 referans). Silmeden önce her biri için
    `grep -rn "<modül_adı>" app/ tests/` ile son bir doğrulama yap.
11. `modules/todo/service.py::today_count` ve `core/entity.py::get_entities` sil.
12. K5 kararına göre `pomodoro pause/resume`, `recurring pay`, `study area delete`
    uçları ya Faz 4'e devredilir ya silinir. Silineceklerden migration gerektiren
    yoksa sadece router+service temizliği yeterli.

**Kapsam — Repo hijyeni**
13. `frontend/dist/` ve `backend/backups/*.json.gz` git takibinden çıkar
    (`git rm --cached`), `.gitignore`'a ekle.
14. `frontend/tsconfig.tsbuildinfo`, `.DS_Store` dosyalarını temizle.

**Kabul kriteri**
- `npx vitest run` → 39 dosya geçiyor (skip sayısı değişmedi).
- `make test` geçiyor.
- `ruff check app tests scripts` temiz.
- `npm run build` geçiyor, giriş chunk'ı hâlâ 500 KB altında (ikon kaldırıldıysa küçülmeli).
- `npm run api:check` — backend şeması değiştiyse `python scripts/export_openapi.py`
  + `npm run api:generate` koşulmuş olmalı.
- Net satır değişimi **negatif**.

---

### FAZ 2 — Tasarım dili tekleştirme

**Hedef.** Tüm etiket, çip, rozet, buton, form kontrolü ve tipografi tek
paletten ve tek bileşen setinden gelsin. Görsel sonuç: hiçbir iki ekranda aynı
anlamı taşıyan iki farklı görünüm olmasın.

**Kapsam**

**2.1 — Token boşluklarını kapat (`src/index.css`)**
- Grafik paleti ekle: `--chart-1` … `--chart-8`, açık ve koyu tema için ayrı.
  `FinancePage`'deki 11 sabit hex bunlarla değişecek. Kategori→renk eşlemesi
  deterministik olmalı (kategori adının hash'i değil, sabit sıra).
- `--kind-*` ve `--src-*` grubunu **kimlik rengi** olarak belgele; semantik
  (`ok/warn/danger/accent`) ile karıştırılmayacağını yorumda yaz.

**2.2 — Tek çip/rozet bileşeni (`core/ui.tsx`)**
`Badge`'i genişlet, `kindChip` ve `PRIORITIES[].chip`'i emekliye ayır:

```tsx
type ChipTone = "neutral" | "accent" | "ok" | "warn" | "danger";
type ChipVariant = "soft" | "outline" | "solid";

export function Chip({
  children, tone = "neutral", variant = "soft", identity, icon, size = "sm",
}: {
  children: ReactNode;
  tone?: ChipTone;
  variant?: ChipVariant;
  /** Kimlik rengi: "kind-movie" | "src-tmdb" | "feed-hn". tone ile birlikte kullanılmaz. */
  identity?: string;
  icon?: ReactNode;
  size?: "xs" | "sm";
}) { … }
```
Kurallar:
- `tone` ⇒ semantik anlam (durum, öncelik, sağlık).
- `identity` ⇒ marka/tür rengi (medya türü, feed kaynağı, sağlayıcı).
- İkisi aynı anda verilemez (tip düzeyinde `never` ile engelle).
- `Badge` geriye dönük uyum için `Chip`'e delege eden ince bir sarmalayıcı
  olsun ya da tümüyle `Chip`'e taşınsın — ikinci seçenek tercih edilir.

Çağrı yerlerini taşı:
- `media/shared.tsx::kindChip` → `<Chip identity={"kind-"+kind} variant="outline">`
- `todo/priority.ts::PRIORITIES[].chip` → `PRIORITIES[].tone` (sadece ton döndürsün)
- `opportunity/labels.ts::STATUS_TONES` → değişmiyor, zaten doğru

**2.3 — Ham HTML kontrollerini kapat**
- 21 dosyadaki ham `<input>` → `Input` / `Field`
- 10 dosyadaki ham `<select>` → `Select`
- `<button>` → `Button` / `IconButton`
- Bileşenin karşılamadığı ihtiyaç varsa (ör. `type="range"`, `type="date"`,
  `type="number"`) **bileşeni genişlet**, çağrı yerinde ham etiket bırakma:
  `Input` `type` propunu zaten alıyor; `Range` ve `NumberInput` için iki yeni
  primitive ekle.
- `<input type="checkbox">` için `Checkbox` primitive'i ekle (şu an her yerde
  ham ve farklı boyutta).

**2.4 — Tipografi ve yarıçapı ölçeğe çek**
- 28 dosyadaki `text-[Npx]` kullanımlarını ölçek adımlarına eşle. Ölçekte
  karşılığı olmayan gerçek bir ihtiyaç varsa **ölçeğe yeni adım ekle**
  (`tailwind.config.js`), çağrı yerinde keyfi değer bırakma.
  Muhtemel yeni adımlar: `micro` zaten var (10px); `numeral-lg` (24px) ve
  `numeral-xl` (26px) `Metric`/`Stat` için.
- `rounded-md/lg/xl/2xl` → `rounded-control` / `rounded-card` / `rounded-overlay`.
  `rounded-full` yalnız avatar/nokta göstergelerinde kalsın.

**2.5 — Yüzey bileşenlerini teke indir**
- `Card` silindi (Faz 1). Kalan: `Section` (başlıklı kutu), `Surface` (çıplak kutu),
  `Panel` (= `Section`, ayrı export). **`Panel` export'unu kaldır**, 7 dosyadaki
  `import { Section as Panel }` takma adını gerçek `Section`'a çevir.
- `MetricStrip`/`Metric` ile `Stat` arasındaki ikilemi çöz: `Stat` tek başına
  duran kutucuk, `Metric` şerit içindeki hücre — bunu JSDoc'ta netleştir veya
  `Stat`'ı `MetricStrip` içinde tek `Metric` olarak yeniden yaz.

**2.6 — Kaynak/etiket yardımcılarını çekirdeğe taşı**
- `modules/opportunity/labels.ts::sourceLabel` → `core/labels.ts`.
  `health` modülünün `opportunity`'den import etmesi bitecek (B8).
- İki kopya `MiniStat` bileşenini `core/ui.tsx`'e tek `MiniStat` olarak taşı.

**2.7 — Tasarım guardrail testi**
Repo zaten kaynak tarayan guard testi kullanıyor (`lib/dateUsage.test.ts`,
`core/ui.test.tsx`). Aynı desende `core/designSystem.test.ts` yaz:
```
- src/modules/**/*.tsx içinde /text-\[\d/ eşleşmesi olmamalı
- src/modules/**/*.tsx içinde /#[0-9a-fA-F]{6}/ olmamalı
- src/modules/**/*.tsx içinde /<(input|select|textarea)\b/ olmamalı
- src/modules/**/*.tsx içinde /rounded-(md|lg|xl|2xl)\b/ olmamalı
- src/**/*.tsx içinde ham tailwind palet sınıfı (bg-blue-500 vb.) olmamalı
```
İstisna listesi dosyanın başında açıkça ve gerekçeli tutulsun.

**Kabul kriteri**
- `core/designSystem.test.ts` yeşil, istisna listesi boş ya da gerekçeli.
- `npx vitest run` tamamı geçiyor.
- Açık ve koyu temada tüm sayfalar taranmış; sabit hex kalmamış.
- Görsel doğrulama: `/finance`, `/media`, `/opportunities`, `/todos`, `/learning`
  ekranlarının açık+koyu ekran görüntüleri `output/` altına alınmış ve
  çip/buton/rozet dilinin aynı olduğu doğrulanmış.

---

### FAZ 3 — Çekirdek entegrasyon altyapısı

**Hedef.** Modüllerin birbirini **isimle tanımadan** birbirine bağlanabileceği
sözleşmeleri kurmak. Bu faz özellik değil altyapı üretir; ekranda görünen tek
şey "İlgili kayıtlar" panelidir.

**Kapsam**

**3.1 — Entity tipi kayıt defteri (B6'yı bitirir)**
Backend'de `ModuleSpec.entity_types` zaten var ama okunmuyor. Onu zenginleştir:
```python
@dataclass(frozen=True)
class EntityTypeSpec:
    type: str                 # "bookmark"
    label: str                # "Yer imi"          (Türkçe, tekil)
    label_plural: str         # "Yer imleri"
    route: str                # "/bookmarks?focus={id}"   — frontend hash rotası
    icon: str                 # lucide adı, ör. "Bookmark"
    searchable: bool = True
    linkable: bool = True
```
- `ModuleSpec.entity_types: list[EntityTypeSpec]` olarak değiştir.
- `core/search.py::SEARCH_LABELS` sabitini **sil**; `grouped_search` etiketleri
  kayıt defterinden okusun.
- Yeni uç: `GET /api/registry/entity-types` → tüm `EntityTypeSpec` listesi.
- Frontend `GlobalSearch.tsx`'teki `ROUTE_FOR` ve `TYPE_LABELS` sabitlerini **sil**;
  ikisi de bu uçtan (uygulama açılışında bir kez, `settings` gibi) dolsun.
- Eksik tipleri kaydet: `review`, `media_collection`, `media_cycle`,
  `external_event`, `pomodoro_session`, `milestone` (+ `habit` yaşıyorsa).

**3.2 — `link` API'sini kullanılabilir hale getir**
- `GET /api/entities/{id}/related` çıktısını zenginleştir: `relation`, `direction`
  (`outgoing`/`incoming`), entity `type`, `title`, `updated_at`.
- Yeni uç: `GET /api/entities/{id}` → tek entity özeti (başlık, tip, arşiv durumu).
- `relation` sözlüğünü kayıt defterine bağla:
  ```python
  RELATIONS = {
    "related":        ("İlgili", "İlgili"),
    "saved_from":     ("Kaynağı", "Buradan kaydedildi"),
    "belongs_to":     ("Ait olduğu", "Alt kaydı"),
    "application_step": ("Başvuru adımı", "Adımı olduğu başvuru"),
    "paid_as":        ("Ödemesi", "Ödendiği harcama"),
    "media.collection_item": ("Koleksiyon", "Koleksiyon öğesi"),
    "prepares_for":   ("Hazırlık", "Hazırlanılan"),   # yeni
    "references":     ("Kaynak", "Kaynak gösterilen"), # yeni
  }
  ```
  Yön çiftini (ileri/geri etiket) tek yerde tut; UI iki yönü de doğru yazsın.
- Yazma uçlarını doğrula: `POST /api/links` gövdesi `{from_id, to_id, relation}`,
  idempotent (`on_conflict_do_nothing` zaten var), `log_event("link.created")` ekle.

**3.3 — Frontend `RelatedPanel` bileşeni (`core/RelatedPanel.tsx`)**
Tek bir bileşen, herhangi bir `entity_id` ile çalışır:
- İlişkili kayıtları ilişki türüne göre gruplayıp listeler.
- Her satır kayıt defterindeki rotaya tıklanabilir gider.
- "Bağla" düğmesi: global arama açar, seçilen kaydı `POST /api/links` ile bağlar.
- "Bağı kaldır": `DELETE /api/links`.
- Offline'da yazma kapalı (mevcut `useOnline` guard'ı).

**3.4 — Merkezi invalidation haritası (`core/invalidation.ts`)**
Elle yazılmış 40+ `invalidate(...)` çağrısını tek bir olay tablosuna bağla:
```ts
export const AFTER = {
  "todo.write":        ["todos", "today-agenda", "plan", "deadlines", "activity", "review-preview"],
  "bookmark.write":    ["bookmarks", "bookmark-stats", "learning-queue", "activity"],
  "rss.write":         ["items", "feeds", "rss-stats", "today-agenda", "activity"],
  "media.write":       ["media", "media-detail", "media-stats", "today-agenda", "activity"],
  "opportunity.write": ["opportunities", "opportunity", "deadlines", "followups",
                        "applications-funnel", "today-agenda", "activity"],
  "project.write":     ["projects", "project-todos", "todos", "today-agenda", "activity"],
  "plan.write":        ["plan", "today-agenda", "calendar-events", "activity"],
  "finance.write":     ["expenses", "expense-summary", "recurring", "deadlines", "activity"],
  ...
} as const;

export function invalidateAfter(...events: (keyof typeof AFTER)[]): void
```
Tüm mutation `onSuccess`'leri bu fonksiyonu çağırsın. Böylece "yeni bir tüketici
eklendi, hangi 12 dosyayı güncelleyeceğim" sorusu ortadan kalkar.
**B4 bu adımda çözülür** — `today-agenda` artık her yazmada tazelenir.

**3.5 — `deadline_v` yerine kayıt defteri tabanlı son tarih toplayıcı (B5)**
İki seçenek, ikincisi tercih edilir:
- (a) Görünümü genişlet — yine migration gerektirir.
- (b) **`ModuleSpec.deadline_provider`** ekle: her modül isteğe bağlı olarak
  `async def deadlines(session) -> list[DeadlineRow]` sağlar; `GET /api/deadlines`
  kayıtlı sağlayıcıları toplayıp sıralar. `deadline_v` görünümünü düşür.
  Eklenecek sağlayıcılar: `project` (milestone), `media` (çıkış tarihi),
  `opportunity` (mülakat tarihi), `calendar` (bugün+3 gün olayları),
  `learning` (kurs hedef tarihi varsa).

**3.6 — Event verb kayıt defteri**
`frontend/src/modules/activity/verbs.ts` elle yazılmış 78 satırlık sözlük.
`ModuleSpec.event_verbs` backend'de zaten dolu. `GET /api/registry/event-verbs`
uç noktası ekleyip verb→Türkçe etiket eşlemesini oraya taşı; `verbs.ts` kalkabilir
veya sadece yedek etiket üretici olarak kalsın.
Eksik verb'leri de doldur: `expense.created`, `recurring_payment.created`,
`media.*` (18 tanesi verbs.ts'te yok), `link.created`.

**Kabul kriteri**
- `GET /api/registry/entity-types` tüm modüllerin tiplerini döndürüyor;
  `SEARCH_LABELS`, `ROUTE_FOR`, `TYPE_LABELS` sabitleri silinmiş.
- Global aramada her sonuç tıklanınca doğru sayfaya gidiyor (hiçbiri `#/`'ye düşmüyor).
- `RelatedPanel` en az bir sayfada (öneri: `OpportunityDetail`) çalışıyor.
- Yeni test: `tests/test_registry.py` — her `ModuleSpec.entity_types` girdisinin
  `route`'u frontend'de kayıtlı bir rotayla eşleşiyor (frontend tarafında
  `registryRouting.test.tsx` deseni genişletilir).
- Yeni test: `core/invalidation.test.ts` — her mutation dosyası ham `invalidate(`
  yerine `invalidateAfter(` kullanıyor (kaynak taraması).

---

### FAZ 4 — Modüller arası akışlar

**Hedef.** Kullanıcının somut olarak istediği bağları kurmak ve Faz 3'te açılan
altyapıyı gerçek akışlara dönüştürmek. Her akış çift yönlü olmalı: A'dan
yapılan işlem B'de görünmeli, B'den A'ya geri gidilebilmeli.

**Kapsam — 4.1 Görev bağlantıları (kullanıcının 1. örneği)**
- `TodoRow` proje rozeti `#/projects?focus={project_id}` hedefine gitsin
  (şu an genel `#/projects`).
- `TodoPage`'e proje filtresi ekle (`?project=<id>` URL parametresi).
- `ProjectTodos`'tan eklenen görev `invalidateAfter("todo.write","project.write")`
  çağırsın → Bugün panelinde anında görünsün.
- Ters yön: `TodoPage`'de bir göreve "projeye bağla" aksiyonu (RelatedPanel'in
  hafif hali) — proje seçici + `POST /api/links` (`belongs_to`).
- Milestone bağı (`todo.milestone_id`) UI'da görünür değil; `TodoRow`'a
  milestone rozeti ekle.

**Kapsam — 4.2 Yer imi her yerden (kullanıcının 2. örneği)**
- `core/SaveToLibrary.tsx`: herhangi bir `{url, title, entity_id?}` alan tek aksiyon.
  `POST /api/capture` + (entity varsa) `POST /api/links` (`saved_from`).
- Bağlanacağı yerler:
  - **Fırsat** (`OpportunityDetail`, `OpportunityList` satır menüsü) → ilan URL'si
    `collection: "reference"` olarak kaydedilir, fırsata `saved_from` ile bağlanır.
  - **Medya** (`MediaDetailPage`) → dış bağlantı yer imine.
  - **RSS** — zaten var; aynı bileşene taşı, tekrarı sil.
  - **Belge** (`DocumentsPage`) → Drive bağlantısı.
  - **Proje** (`ProjectsPage`) → repo/doküman bağlantısı.
- **Kullanıcının sorusunun cevabı ekranda görünmeli:** kaydettikten sonra çıkan
  toast "Gelen Kutusu'na eklendi" + "Aç" aksiyonu içersin. Nereye gittiği tahmin
  edilmesin, yazsın.

**Kapsam — 4.3 Fırsat ↔ görev ↔ belge zinciri (D3'ü kapatır)**
- `GET/POST /api/opportunities/{id}/todos` uçlarını `OpportunityDetail`'de
  "Başvuru adımları" bölümü olarak yayına al.
- Bu görevler `TodoPage`'de fırsat rozetiyle görünsün (proje rozetinin eşi).
- Gereksinim → belge bağı zaten çalışıyor (`requirement_document_bound`);
  ters yönü ekle: `DocumentsPage`'de "bu belge şu başvurularda kullanılıyor".
- Mülakatlar (`opportunity_interview`) son tarih sağlayıcısına girsin (3.5).
- Çöp akışını tamamla: `POST /opportunities/{id}/trash` ve `/restore` uçlarını
  listedeki satır menüsüne bağla (`?view=trash` filtresi zaten var).

**Kapsam — 4.4 Medya IA'sını kur (K2 kararına göre)**
`MediaFrontend.test.tsx`'teki `describe.skip`'i kaldır ve testi yeşile getir:
- Rotalar: `/media/library`, `/media/collections`, `/media/upcoming`,
  `/media/stats`, `/media/trash` (+ mevcut `/media`, `/media/:id`).
- Backend uçları hazır: `collections` CRUD, `upcoming`, `dashboard`,
  `restore`, `permanent`.
- Koleksiyon öğesi ekleme `media.collection_item` link'ini kullanıyor —
  `RelatedPanel` ile aynı dili konuşsun.

**Kapsam — 4.5 Öğrenme / çalışma bağları**
- `study_topic` → todo: "bu konu için görev oluştur" (`prepares_for` ilişkisi).
- `study_topic` → pomodoro: `context_entity_id` ile odak başlat
  (altyapı `PomodoroPage.tsx:60`'ta hazır, sadece giriş noktası yok).
- `course` / `book` → yer imi kuyruğu bağı zaten var (`/learning/queue`);
  ters yönü `BookmarksPage`'de göster.
- `TodoRow`'a "odaklan" düğmesi: seçili görevle pomodoro başlatır.

**Kapsam — 4.6 Kalan kayıp uçları bağla**
- `POST /api/pomodoro/{id}/pause` · `/resume` → `PomodoroWidget` ve `PomodoroPage`.
- `POST /api/recurring-payments/{id}/pay` → `RecurringWidget`'ta "ödendi" düğmesi
  (`recurring.paid` verb'ü nihayet üretilir).
- `DELETE /api/study/areas/{id}` → `StudyPage`.
- `POST /api/notifications/dismiss-all` → `NotificationPanel`.
- `GET /api/documents/{id}/open` → `DocumentsPage`.
- `GET /api/bookmarks/collections` → frontend'deki hardcoded `COLLECTIONS`
  sabitini bu uçtan besle (ya da tersine, sabit kalacaksa ucu sil).
- `GET/POST/DELETE /api/views` → K3 kararına göre: bookmark, fırsat ve medya
  listelerine "görünümü kaydet" çubuğu.

**Kabul kriteri**
- Yukarıdaki her akış için bir frontend testi (mevcut `ProjectTodos.test.tsx`
  ve `TodayAgendaWidget.test.tsx` deseninde).
- `MediaFrontend.test.tsx`'te `describe.skip` kalmadı, 9 test geçiyor.
- OpenAPI'de frontend'in çağırmadığı uç sayısı **≤ 3** (`auth/google/callback`
  gibi tarayıcı yönlendirmeleri hariç). Bunu ölçen bir betik yaz:
  `frontend/scripts/check-endpoint-coverage.mjs`.
- Elle akış testi: Projede görev ekle → `/todos`'ta ve Bugün'de sayfa
  yenilemeden görünüyor. Fırsatta yer imi kaydet → Gelen Kutusu'nda ve
  fırsatın "İlgili" panelinde görünüyor.

---

### FAZ 5 — Bugün / Dashboard tam entegrasyonu

**Hedef.** Bugün sayfası tüm modüllerin buluştuğu tek ekran olsun; hiçbir modül
"Bugün'de görünmez" kalmasın; panel kullanıcı tarafından düzenlenebilsin.

**Kapsam**
1. **Eksik widget'ları yaz** (B7): `calendar` (bugünün olayları — agenda'da var
   ama modülün kendi widget'ı yok, "sonraki 3 gün" için ayrı), `documents`
   (son değişen belgeler), `learning` (devam eden kurs/kitap), `todo`
   (gecikenler — agenda bugünü gösteriyor, gecikmişler ayrı bir uyarı hak ediyor).
2. **`health` modülünü Bugün'e bağla:** kaynak sağlığı özeti sağ sütunda küçük
   bir satır olarak (`StatusLed` zaten üst şeritte; panelde tekrar etmesin —
   sadece bozuk kaynak varsa görünen bir uyarı satırı).
3. **Agenda'yı tamamla** (`modules/today/service.py`): şu an todo + calendar +
   rss + media + plan_slot birleşiyor. Ekle:
   - fırsat son tarihleri (bugün/yarın olanlar)
   - mülakatlar (saatli satır olarak)
   - tekrarlayan ödemeler (bugün vadesi gelen)
   - study/pomodoro planlanmış blokları
   Hepsi mevcut `AgendaRow` sözleşmesine `kind` ekleyerek girsin; kırıcı değişiklik yok.
4. **Panel düzenlenebilirliği:** `today.widget_order` ve `today.columns` ayarları
   backend'de var, `hydrateSettings` okuyor, ama `todayColumns()` ölü (Faz 1'de
   silindi). Kararı ver: ya sütun sayısı ayarını gerçekten uygula
   (`dashboard-grid` CSS'ini değişkenle sür), ya ayarı backend'den de kaldır.
5. **Widget sözleşmesini sıkılaştır:** her `todayWidgets` girdisi artık
   `{ component, slot, order }` (zone Faz 1'de silindi). `order` zorunlu olsun;
   varsayılan 50'ye düşmek çakışma üretiyor.
6. **Boş durum tutarlılığı:** her widget veri yokken `Empty` bileşenini
   `variant="inline"` ile kullansın; şu an bazıları hiç render etmiyor, bazıları
   düz metin basıyor.

**Kabul kriteri**
- `allTodayWidgetsIn()` çıktısında en az 14 modülün katkısı var.
- `today/agenda` uç noktası en az 8 `kind` döndürebiliyor; her biri için test.
- Bugün sayfası boş DB'de çökmüyor, her widget kendi boş durumunu gösteriyor.
- 375px / 768px / 1280px / 1600px ekran görüntüleri `output/playwright/` altına
  alınmış ve üç sütunlu düzenin taşmadığı doğrulanmış.

---

### FAZ 6 — Modül içi toparlama ve sayfa disiplini

**Hedef.** "Dağınık modül" hissini üreten dosyaları okunabilir hale getirmek ve
`AGENTS.md`'deki modül reçetesine geri döndürmek.

**Kapsam**

**6.1 — Tek satıra sıkıştırılmış sayfaları aç**
Öncelik sırası (en uzun satırdan):
1. `modules/learning/LearningPage.tsx` (2.596 kr) — 3 sekme, 3 ayrı bileşene böl:
   `CoursesTab` / `BooksTab` / `QueueTab`. Kopyalanmış `{watch:"İzle",…}` sözlüğünü
   dosya başında tek sabite al.
2. `modules/settings/SettingsPage.tsx` (2.171 kr) — bölümlere ayır:
   `IntegrationsSection`, `BackupSection`, `ModulesSection`, `WeatherSection`,
   `MediaLinksSection`.
3. `modules/study/StudyPage.tsx` (1.528 kr)
4. `modules/documents/DocumentsPage.tsx` (1.038 kr)
5. `modules/finance/RecurringWidget.tsx`, `modules/opportunity/OpportunityWidget.tsx`
6. Modül `index.ts` dosyalarını (7 tanesi tek satır) çok satırlı yaz.

Kural: **hiçbir satır 120 karakteri geçmesin.** Prettier/ESLint yoksa
`printWidth: 120` ile Prettier ekle ve `npm run format:check`'i CI'a al.

**6.2 — Şişmiş backend servislerini böl**
- `modules/media/service.py` (1.545) → `service.py` (CRUD) + `progress.py`
  (cycle/consumption ilerleme) + `collections.py` + `search.py`.
- `modules/opportunity/service.py` (771) → `service.py` + `application.py`
  (CRM: application/history/interview/funnel).
- `modules/opportunity/router.py` (522) → `router.py` + `sources_router.py`
  (kaynak/jobhunter uçları, mantıksal olarak `system` veya yeni `sources` modülüne ait).
- `modules/media/schemas.py` (483) → `schemas.py` + `validators.py`.

**6.3 — Kaynak sağlığını tek yere indir (K4 kararı)**
- `/health` tek yetkili sayfa.
- `/sources` rotası `/health`'e yönlendirsin (ya da tümden kalksın; opportunity
  modülünün ikinci bir rotası olmasın).
- `SettingsPage`'deki `SettingsSourceHealth` bölümü tek satırlık özet + link'e insin.
- Kopyalanmış `MiniStat` Faz 2'de çekirdeğe taşındı; burada sadece çağrı yerleri.

**6.4 — Migration adlandırmasını düzelt (Y1)**
`0022_finance_sub` ve `0023_application_crm` dosyalarını gerçek sıraya göre
`0027_finance_sub`, `0028_application_crm` olarak yeniden adlandır
(`revision` string'i **değişmez**, sadece dosya adı ve içindeki yorum).
`alembic_version` tablosundaki değer korunacağı için üretim verisi etkilenmez —
yine de `docs/`'ta not düş. Alternatif: dosya adlarını olduğu gibi bırakıp
`alembic/README.md`'ye gerçek zinciri yazan bir tablo koy.

**6.5 — Test boşluklarını doldur (Y3)**
Hiç testi olmayan modüller için en az birer akış testi:
`study`, `learning`, `inbox`, `health`, `finance`, `documents`, `calendar`, `bookmarks`.
Mevcut desen: `MediaPage.test.tsx` (fetch stub + `renderView`).

**Kabul kriteri**
- 120 karakterden uzun satır kalmadı (`npm run format:check` yeşil).
- Hiçbir backend servis dosyası 600 satırı geçmiyor.
- Her frontend modülünde ≥1 test dosyası var.
- `make test` ve `npx vitest run` geçiyor.

---

### FAZ 7 — Guardrail, test ve dokümantasyon

**Hedef.** Bu 7 fazın kazanımının bir sonraki özellikte geri kaymasını
engellemek. `AGENTS.md`'nin "değişmez kurallar" listesine yeni maddeler eklemek
ve her birini bir testle desteklemek.

**Kapsam**
1. **`AGENTS.md` + `CLAUDE.md` güncelle** — yeni değişmez kurallar:
   - 13. Entity tipi, etiketi ve rotası **yalnız** `EntityTypeSpec`'te tanımlanır.
     Frontend'de tip→rota sabiti yazma.
   - 14. Mutation sonrası tazeleme `invalidateAfter()` ile yapılır; ham
     `invalidate("a","b")` yasak.
   - 15. Renk, boyut ve yarıçap yalnız tasarım tokenlarından gelir.
     `text-[Npx]`, sabit hex ve ham `<input>/<select>/<button>` yasak.
   - 16. Son tarih üreten modül `deadline_provider` sağlar; `deadline_v`
     benzeri elle SQL yazılmaz.
   - 17. Kayıtlı olup frontend'den çağrılmayan uç bırakma; uç ya kullanılır ya silinir.
2. **CI işleri ekle** (`.github/workflows/ci.yml`):
   - `frontend/scripts/check-endpoint-coverage.mjs` — referanssız uç sayısı eşiği.
   - `npm run format:check`
   - `core/designSystem.test.ts` zaten `vitest run` içinde koşuyor.
   - Ölü export taraması (Faz 0'daki `deadexp.mjs` betiğini `scripts/` altına
     kalıcı taşı, eşikle CI'a bağla).
3. **`README.md` güncelle:** "Ne var" tablosuna modüller arası bağlar bölümü;
   endpoint listesini gerçek durumla eşitle.
4. **`docs/mimari.md` yaz:** entity/link/event üçlüsünün nasıl kullanıldığı,
   ilişki sözlüğü, kayıt defterlerinin listesi, Bugün widget sözleşmesi.
   Yeni modül ekleyen kişinin okuyacağı tek doküman.
5. **Migration testi genişlet:** `tests/test_migrations.py` şu an model↔migration
   karşılaştırıyor; `deadline_v` kalktıysa onu da doğrula.

**Kabul kriteri**
- CI tüm işlerde yeşil.
- `AGENTS.md` ve `CLAUDE.md` senkron ve yeni kuralları içeriyor.
- `docs/mimari.md` var ve bir "yeni modül ekleme" turu bu dokümanla tamamlanabiliyor.

---

## 5. Agent promptları

Her prompt bağımsız çalıştırılabilir. **Sırayla ver**; her fazın sonunda
testleri koştur ve commit al. Prompt'ları olduğu gibi kopyalayabilirsin.

---

### PROMPT — FAZ 0

```
forkOS deposunda (/Users/furkanturkoglu/Downloads/forkOS) çalışıyorsun.
Önce AGENTS.md ve CLAUDE.md dosyalarını oku; oradaki değişmez kurallar bu
görevde de geçerli. forkOS-ENTEGRASYON-PLANI.md dosyasındaki "FAZ 0" bölümünü oku.

GÖREV: Faz 0 — zemin, kararlar ve emniyet ağı. Bu fazda ÜRÜN KODU DEĞİŞMEZ.

1. Baseline al:
   - frontend/ içinde: npx vitest run
   - backend testleri: make test   (çalışmazsa nedenini not et, zorlama)
   - frontend/ içinde: npm run build
   Çıktıların özetini docs/faz0-baseline.md dosyasına yaz (tarih, komut, sonuç).

2. docs/faz0-kararlar.md dosyasını oluştur ve şu 5 karar noktasını incele,
   her biri için repo kanıtı toplayıp bir öneri ve gerekçe yaz:
   K1 habit modülü: app/modules/habit/* backend'de tam, frontend'de HİÇ çağrılmıyor
      (/habits rotası TodoPage'e gidiyor, işlevi todo.recur devralmış).
      Kaldırmak mı, ekrana getirmek mi? habit_log tablosunda veri var mı kontrol et
      (make psql ile bakabilirsin; DB ayakta değilse "bilinmiyor" yaz).
   K2 medya IA'sı: frontend/src/modules/media/MediaFrontend.test.tsx:171 describe.skip;
      7 rota bekliyor, modules/media/index.ts 2 tanesini kaydediyor. Backend uçları
      (collections, upcoming, dashboard, trash, restore) hazır ve çağrılmıyor.
   K3 saved_view: tablo + /api/views uçları var, frontend'de sıfır çağrı.
   K4 kaynak sağlığı 3 yerde: /sources (opportunity modülü), /health (health modülü),
      SettingsPage. Hangisi tek yetkili olacak?
   K5 kullanılmayan uçlar: pomodoro pause/resume, recurring-payments/{id}/pay,
      study/areas/{id} DELETE, notifications/dismiss-all, documents/{id}/open.
      UI'ya çıkacak mı, silinecek mi?

3. .gitignore'u denetle ve gerekiyorsa düzelt: frontend/dist/, backend/backups/,
   *.pyc, __pycache__/, .pytest_cache/, .ruff_cache/, tsconfig.tsbuildinfo, .DS_Store.
   Halihazırda git'te takip edilen böyle dosya varsa SİLME, sadece raporla.

KURALLAR:
- Ürün kodunu değiştirme. Sadece docs/ altına dosya ve .gitignore düzeltmesi.
- Her karar için "öneri + tek cümle gerekçe" yaz; kararı sen verme, seçenekleri net koy.
- Türkçe yaz.

ÇIKTI: docs/faz0-baseline.md, docs/faz0-kararlar.md ve yaptığın .gitignore
değişikliğinin özeti.
```

---

### PROMPT — FAZ 1

```
forkOS deposunda çalışıyorsun. AGENTS.md, CLAUDE.md ve
forkOS-ENTEGRASYON-PLANI.md "FAZ 1" bölümünü oku. docs/faz0-kararlar.md'deki
kararlara uy.

GÖREV: Faz 1 — ölü kod ve referanssız yüzey temizliği.
Bu fazda YENİ ÖZELLİK EKLENMEZ. Başarı ölçüsü: net satır sayısı düşerken
tüm testler geçiyor.

FRONTEND (frontend/src):
1. modules/rss/RssWidget.tsx dosyasını sil (hiçbir yerden import edilmiyor).
2. core/registry.ts: todayColumns, todayWidgetsIn, pinnedModules, groupedModules
   fonksiyonlarını sil. enabledModules'ü dosya-içi (export olmayan) yap.
3. core/ui.tsx: Card bileşenini sil (Surface ile aynı ve kullanılmıyor).
4. core/types.ts: DayEvent, GithubCommit, GithubActivity, MediaLink,
   SourceSyncItem tiplerini sil. SavedView için K3 kararına bak.
5. ModuleSpec'ten searchLabel ve enabledByDefault alanlarını sil; modules/projects
   ve modules/finance index.ts'lerinden searchLabel satırlarını çıkar.
6. ModuleSpec.icon: şu an 18 modül lucide ikonu import ediyor ama
   core/AppHeader.tsx ModuleTab ikonu ÇİZMİYOR. İkonu ModuleTab'da çiz
   (<Icon size={13} className="shrink-0" /> + başlık, aria gereksiz). Ara durum bırakma.
7. TodayWidget.zone alanını sil: core/types.ts'ten TodayZone tipini ve zone
   alanını, core/registry.ts'teki normalize() varsayılanını, ve 18 modülün
   todayWidgets tanımlarındaki zone satırlarını kaldır. Yerleşim slot+order ile
   yapılıyor, zone'u kimse okumuyor.
8. Kullanılmayan yerel export'ları sil:
   media/shared.tsx: kindColor, srcColor
   opportunity/labels.ts: KIND_ORDER, StatusTone
   opportunity/SyncProgress.tsx: useSourceSync
   rss/RssPage.tsx: RSS_SAVE_REFRESH_KEYS
   finance/RecurringWidget.tsx: RECURRING_WIDGET_KEY
   today/weather.ts: Forecast
   lib/date.ts: APP_TIME_ZONE
   core/api.ts: isOnline ve assertOnlineWrite dosya içinde kullanılıyor —
   sadece 'export' anahtar kelimesini kaldır, fonksiyonları silme.

BACKEND (backend/app):
9. K1 kararı "kaldır" ise: app/modules/habit/ dizinini sil, app/modules/__init__.py
   MODULES listesinden çıkar, habit + habit_log tablolarını düşüren yeni bir
   Alembic revision yaz. DİKKAT: AGENTS.md kural 10 — migration'da HER SQL komutu
   ayrı op.execute() olacak. habit_log'da veri varsa önce todo+recur'a taşıyan adım
   ekle. frontend/src/modules/activity/verbs.ts'ten habit.* etiketlerini kaldır.
   AGENTS.md kural 1'deki "habit_log dokümante edilmiş istisnadır" cümlesini güncelle.
   K1 kararı "ekrana getir" ise bu maddeyi atla ve Faz 4'e devret.
10. app/sources/forkjob_core/ içinden balance.py, dedup.py, discover.py, sponsors.py
    dosyalarını sil. SİLMEDEN ÖNCE her biri için
    grep -rn "<dosya_adı>" backend/app backend/tests  ile son doğrulama yap;
    bir referans çıkarsa silme, raporla.
11. modules/todo/service.py::today_count ve core/entity.py::get_entities sil
    (hiçbir yerden çağrılmıyor).
12. K5 kararına göre silinecek uçlar varsa router+service'ten temizle.

REPO HİJYENİ:
13. frontend/dist/ ve backend/backups/*.json.gz git takibinden çıkar
    (git rm --cached -r), .gitignore'da olduklarını doğrula.

DOĞRULAMA (hepsi geçmeli):
  cd frontend && npx vitest run        → 39 dosya geçmeli, skip sayısı değişmemeli
  cd frontend && npm run build         → giriş chunk'ı < 500 KB
  make test
  cd backend && ruff check app tests scripts
Backend şeması değiştiyse: cd backend && python scripts/export_openapi.py
ve cd frontend && npm run api:generate — sonra npm run api:check.

ÇIKTI: silinen dosya/sembol listesi, net satır değişimi, test sonuçları.
Bir şeyi silememişsen (referans buldun) nedenini yaz.
```

---

### PROMPT — FAZ 2

```
forkOS deposunda çalışıyorsun. AGENTS.md, CLAUDE.md, frontend/src/index.css
(token tanımları) ve forkOS-ENTEGRASYON-PLANI.md "FAZ 2" bölümünü oku.

GÖREV: Faz 2 — tasarım dili tekleştirme. Tüm etiket, çip, rozet, buton, form
kontrolü ve tipografi tek paletten ve tek bileşen setinden gelecek.

ÖNEMLİ: Token altyapısı ZATEN SAĞLAM (index.css semantik değişkenler + koyu tema,
tailwind.config.js semantik sınıflar). Sorun tokenlarda değil, onları es geçen
çağrı yerlerinde. Yeni renk paleti icat etme; var olanı kullandır.

1. TOKEN BOŞLUKLARI (frontend/src/index.css):
   - Grafik paleti ekle: --chart-1 ... --chart-8, açık ve koyu tema için ayrı,
     surface üzerinde en az 3:1 kontrast. tailwind.config.js'e chart.1..8 olarak bağla.
   - modules/finance/FinancePage.tsx:15-24'teki 11 sabit hex'i bu tokenlarla değiştir.
     Kategori→renk eşlemesi deterministik ve sabit sıralı olsun.
   - --kind-* ve --src-* gruplarının KİMLİK rengi olduğunu, semantik
     (ok/warn/danger/accent) ile karıştırılmayacağını yorumda belgele.

2. TEK ÇİP BİLEŞENİ (core/ui.tsx):
   Chip bileşeni yaz:
     tone: "neutral"|"accent"|"ok"|"warn"|"danger"   → semantik anlam
     variant: "soft"|"outline"|"solid"
     identity?: string   → kimlik rengi ("kind-movie", "src-tmdb", "feed-hn")
     icon?, size?: "xs"|"sm"
   tone ve identity aynı anda verilemesin (TypeScript düzeyinde engelle).
   Badge'i Chip'e taşı (Badge export'unu kaldır ya da ince sarmalayıcı bırak).
   Çağrı yerlerini taşı:
     media/shared.tsx kindChip → <Chip identity={"kind-"+kind} variant="outline">
     todo/priority.ts PRIORITIES[].chip → sadece tone döndürsün, string sınıf değil
     opportunity/labels.ts STATUS_TONES → zaten doğru, dokunma

3. HAM HTML KONTROLLERİNİ KAPAT:
   21 dosyadaki ham <input>, 10 dosyadaki ham <select>, 43 dosyadaki ham <button>
   yerine core/ui.tsx bileşenlerini kullan. Bileşenin karşılamadığı gerçek bir
   ihtiyaç varsa BİLEŞENİ GENİŞLET, çağrı yerinde ham etiket bırakma:
     - Checkbox primitive'i ekle (şu an her yerde ham ve farklı boyutta)
     - Range primitive'i ekle (LearningPage kurs ilerlemesi)
     - NumberInput primitive'i ekle (LearningPage sayfa sayısı, MediaProgressActions)
   İstisna: core/ui.tsx'in kendi içi ve cmdk'nın kendi input'u.

4. TİPOGRAFİ VE YARIÇAP:
   28 dosyadaki text-[Npx] kullanımlarını tailwind.config.js ölçeğine
   (micro/meta/body/heading/title/display) eşle. Ölçekte karşılığı olmayan
   GERÇEK bir ihtiyaç varsa ölçeğe yeni adım ekle; çağrı yerinde keyfi değer bırakma.
   rounded-md/lg/xl/2xl → rounded-control | rounded-card | rounded-overlay.
   rounded-full sadece avatar ve nokta göstergelerinde kalsın.

5. YÜZEY BİLEŞENLERİ:
   7 dosyadaki `import { Section as Panel }` takma adını gerçek Section'a çevir;
   Panel export'unu kaldır. Stat ile MetricStrip/Metric arasındaki ikilemi çöz
   (JSDoc'ta netleştir ya da Stat'ı MetricStrip içinde tek Metric olarak yeniden yaz).

6. ÇEKİRDEĞE TAŞIMA:
   modules/opportunity/labels.ts::sourceLabel → core/labels.ts.
   (health modülü şu an opportunity'den import ediyor — modüller arası import bitecek.)
   SourceHealthWidget.tsx ve RssHealthWidget.tsx içindeki iki kopya MiniStat
   bileşenini core/ui.tsx'e tek MiniStat olarak taşı.

7. GUARDRAIL TESTİ (core/designSystem.test.ts):
   Repo zaten kaynak tarayan guard testi kullanıyor — lib/dateUsage.test.ts
   desenini örnek al. Şunları yasakla:
     src/modules/**/*.tsx içinde: /text-\[\d/, /#[0-9a-fA-F]{6}/,
       /<(input|select|textarea)\b/, /rounded-(md|lg|xl|2xl)\b/
     src/**/*.tsx içinde: ham tailwind palet sınıfı (bg-blue-500, text-gray-400 vb.)
   İstisna listesi dosyanın başında açık ve gerekçeli olsun.

DOĞRULAMA:
  cd frontend && npx vitest run        (designSystem.test.ts dahil yeşil)
  cd frontend && npm run build
Görsel: dev sunucusunu aç, /finance, /media, /opportunities, /todos, /learning
sayfalarını AÇIK ve KOYU temada ekran görüntüsüyle doğrula, output/ altına kaydet.
Çip, buton ve rozet dilinin beş sayfada da aynı olduğunu göster.

ÇIKTI: değişen dosya listesi, yeni primitive'ler, guardrail testinin
yasakladığı desenler ve varsa istisna listesi + gerekçesi, ekran görüntüleri.
```

---

### PROMPT — FAZ 3

```
forkOS deposunda çalışıyorsun. AGENTS.md, CLAUDE.md ve
forkOS-ENTEGRASYON-PLANI.md "FAZ 3" bölümünü oku.

GÖREV: Faz 3 — çekirdek entegrasyon altyapısı. Modüller birbirini İSİMLE
TANIMADAN bağlanabilecek. Bu faz altyapı üretir; ekranda görünen tek yeni şey
"İlgili kayıtlar" panelidir.

BAĞLAM — çözülen sorunlar:
 (a) POST/DELETE /api/links ve GET /api/entities/{id}/related uçları çalışıyor ama
     frontend'de SIFIR çağrı var. Çekirdek bağ altyapısı ekranda yok.
 (b) Tip→etiket/rota bilgisi ÜÇ yerde elle tutuluyor ve birbirinden habersiz:
     backend/app/core/search.py:60 SEARCH_LABELS,
     frontend/src/core/GlobalSearch.tsx:8 ROUTE_FOR ve :41 TYPE_LABELS.
     Eksik tipler global aramada #/ ana sayfaya düşüyor.
 (c) frontend'de today-agenda cache'ini widget'ın kendisi dışında kimse
     tazelemiyor; 40+ elle yazılmış invalidate() çağrısı var.
 (d) deadline_v elle yazılmış SQL union (alembic 0016_finance.py:35); yeni
     son-tarihli modül migration yazmayı gerektiriyor.

1. ENTITY TİPİ KAYIT DEFTERİ:
   backend/app/modules/__init__.py'de EntityTypeSpec dataclass'ı tanımla:
     type, label, label_plural, route ("/bookmarks?focus={id}"), icon (lucide adı),
     searchable=True, linkable=True
   ModuleSpec.entity_types'ı list[EntityTypeSpec] yap ve 16 modülün hepsini doldur.
   Eksik tipleri de ekle: review, media_collection, media_cycle, external_event,
   pomodoro_session, milestone.
   core/search.py'deki SEARCH_LABELS sabitini SİL; grouped_search etiketleri
   kayıt defterinden okusun.
   Yeni uç: GET /api/registry/entity-types
   Frontend: GlobalSearch.tsx'teki ROUTE_FOR ve TYPE_LABELS sabitlerini SİL;
   ikisi de bu uçtan dolsun (settings gibi açılışta bir kez).

2. LINK API'SİNİ KULLANILABİLİR YAP:
   GET /api/entities/{id}/related çıktısını zenginleştir: relation, direction
   (outgoing|incoming), entity type, title, updated_at.
   Yeni uç: GET /api/entities/{id} → tek entity özeti.
   İlişki sözlüğünü backend'de tek yerde tanımla (ileri ve geri etiketle):
     related, saved_from, belongs_to, application_step, paid_as,
     media.collection_item, prepares_for (yeni), references (yeni)
   POST /api/links sonrası log_event("link.created") ekle (AGENTS.md kural 3).

3. RelatedPanel BİLEŞENİ (frontend/src/core/RelatedPanel.tsx):
   Tek bir entity_id ile çalışan, ilişki türüne göre gruplayan liste.
   Her satır kayıt defterindeki rotaya gider. "Bağla" düğmesi global aramayı açar
   ve seçilen kaydı POST /api/links ile bağlar; "Bağı kaldır" DELETE /api/links.
   Offline'da yazma kapalı (mevcut useOnline guard'ı).
   En az bir sayfada yayına al: modules/opportunity/OpportunityDetail.tsx.

4. MERKEZİ INVALIDATION (frontend/src/core/invalidation.ts):
   AFTER haritası yaz: "todo.write", "bookmark.write", "rss.write", "media.write",
   "opportunity.write", "project.write", "plan.write", "finance.write",
   "study.write", "pomodoro.write", "source.sync" ...
   Her biri tazelenecek query key listesini tutsun. today-agenda anahtarı
   todo/plan/media/rss/calendar/opportunity yazan HER olayda listede olsun.
   invalidateAfter(...events) fonksiyonunu export et ve TÜM mutation onSuccess'lerini
   buna çevir. Ham invalidate("a","b") çağrısı kalmasın.

5. SON TARİH SAĞLAYICI SÖZLEŞMESİ:
   ModuleSpec'e opsiyonel deadline_provider ekle:
     async def deadlines(session) -> list[DeadlineRow]
   GET /api/deadlines kayıtlı sağlayıcıları toplasın ve sıralasın.
   deadline_v görünümünü düşüren migration yaz (AGENTS.md kural 10: her SQL
   komutu ayrı op.execute()).
   Sağlayıcı ekle: opportunity (mevcut + mülakat tarihleri), todo, finance
   (recurring), project (milestone), media (çıkış tarihi), calendar (3 günlük).

6. EVENT VERB KAYIT DEFTERİ:
   ModuleSpec.event_verbs zaten dolu. GET /api/registry/event-verbs ucu ekle,
   verb→Türkçe etiket eşlemesini oraya taşı.
   frontend/src/modules/activity/verbs.ts'teki 78 satırlık sözlük ya kalksın ya
   sadece yedek etiket üretici olsun. Eksik verb'leri doldur: expense.created,
   recurring_payment.created, media.* (18 tanesi eksik), link.created.

KURALLAR:
- AGENTS.md kural 4: modül eklemek main.py'ye dokunmayı gerektirmez. Bu fazda
  yazdığın her kayıt defteri bu kuralı GÜÇLENDİRMELİ, delmemeli.
- AGENTS.md kural 9-10: migration'lar elle yazılır, her SQL komutu ayrı op.execute().
- Postgres'te Türkçe stemmer yok — search'e dokunuyorsan 'simple' + immutable_unaccent kalsın.

DOĞRULAMA:
  cd backend && python scripts/export_openapi.py
  cd frontend && npm run api:generate && npm run api:check
  cd frontend && npx vitest run
  make test
  cd backend && ruff check app tests scripts
YENİ TESTLER:
  backend/tests/test_registry.py — her EntityTypeSpec.route bir frontend rotasıyla eşleşiyor
  frontend/src/core/invalidation.test.ts — hiçbir modül dosyası ham invalidate( kullanmıyor
  frontend RelatedPanel testi

ÇIKTI: yeni uçlar, silinen sabitler, invalidation haritası, deadline sağlayıcı
listesi, test sonuçları.
```

---

### PROMPT — FAZ 4

```
forkOS deposunda çalışıyorsun. AGENTS.md, CLAUDE.md,
forkOS-ENTEGRASYON-PLANI.md "FAZ 4" ve docs/faz0-kararlar.md'yi oku.
Faz 3'te kurulan EntityTypeSpec kayıt defteri, RelatedPanel ve
invalidateAfter() altyapısını KULLAN — paralel çözüm yazma.

GÖREV: Faz 4 — modüller arası akışlar. Her akış ÇİFT YÖNLÜ olmalı:
A'da yapılan işlem B'de görünmeli, B'den A'ya geri gidilebilmeli.

4.1 GÖREV BAĞLANTILARI:
  - modules/todo/TodoRow.tsx:160 proje rozeti şu an genel #/projects'e gidiyor.
    #/projects?focus={project_id} yap.
  - TodoPage'e proje filtresi ekle (?project=<id> URL parametresi).
  - ProjectTodos'tan görev eklenince invalidateAfter("todo.write","project.write")
    çağrılsın — Bugün panelinde sayfa yenilemeden görünsün.
  - TodoPage'de bir göreve "projeye bağla" aksiyonu ekle (proje seçici +
    POST /api/links, relation "belongs_to").
  - todo.milestone_id UI'da görünmüyor; TodoRow'a milestone rozeti ekle.

4.2 YER İMİ HER YERDEN (kullanıcının açık isteği):
  core/SaveToLibrary.tsx yaz: {url, title, entity_id?} alan tek aksiyon.
  POST /api/capture + (entity varsa) POST /api/links relation "saved_from".
  Bağlanacağı yerler:
    OpportunityDetail ve OpportunityList satır menüsü → ilan URL'si,
      collection "reference", fırsata saved_from ile bağlı
    MediaDetailPage → dış bağlantı
    RSS → mevcut "kaydet" akışını bu bileşene taşı, tekrarı sil
    DocumentsPage → Drive bağlantısı
    ProjectsPage → repo/doküman bağlantısı
  ÖNEMLİ: kaydettikten sonraki toast NEREYE gittiğini yazsın ve "Aç" aksiyonu
  içersin. Kullanıcı tahmin etmek zorunda kalmasın.

4.3 FIRSAT ↔ GÖREV ↔ BELGE ZİNCİRİ:
  - GET/POST /api/opportunities/{id}/todos uçları çalışıyor ama frontend'de
    hiç çağrılmıyor. OpportunityDetail'de "Başvuru adımları" bölümü olarak yayına al.
  - Bu görevler TodoPage'de fırsat rozetiyle görünsün (proje rozetinin eşi).
  - Gereksinim→belge bağının ters yönünü ekle: DocumentsPage'de "bu belge şu
    başvurularda kullanılıyor".
  - POST /opportunities/{id}/trash ve /restore uçlarını satır menüsüne bağla.

4.4 MEDYA IA'SI (K2 kararı "kur" ise):
  frontend/src/modules/media/MediaFrontend.test.tsx:171'deki describe.skip'i kaldır
  ve testi YEŞİLE GETİR. Beklenen rotalar:
    /media, /media/library, /media/collections, /media/upcoming,
    /media/stats, /media/trash, /media/:id
  Backend uçları hazır: collections CRUD, upcoming, dashboard, restore, permanent.
  Koleksiyon öğesi ekleme media.collection_item link'ini kullanıyor — RelatedPanel
  ile aynı dili konuşsun.

4.5 ÖĞRENME / ÇALIŞMA BAĞLARI:
  - study_topic → todo: "bu konu için görev oluştur" (relation "prepares_for")
  - study_topic → pomodoro: context_entity_id ile odak başlat. Altyapı
    PomodoroPage.tsx:60'ta HAZIR, sadece giriş noktası yok.
  - TodoRow'a "odaklan" düğmesi: seçili görevle pomodoro başlatır.
  - course/book → yer imi kuyruğu bağının ters yönünü BookmarksPage'de göster.

4.6 KALAN KAYIP UÇLARI BAĞLA (K5 kararına göre):
  POST /api/pomodoro/{id}/pause · /resume → PomodoroWidget ve PomodoroPage
  POST /api/recurring-payments/{id}/pay → RecurringWidget "ödendi" düğmesi
  DELETE /api/study/areas/{id} → StudyPage
  POST /api/notifications/dismiss-all → NotificationPanel
  GET /api/documents/{id}/open → DocumentsPage
  GET /api/bookmarks/collections → frontend'deki hardcoded COLLECTIONS sabitini
    besle (ya da sabit kalacaksa ucu sil — ikisinden biri)
  GET/POST/DELETE /api/views → K3 kararına göre bookmark/fırsat/medya listelerine
    "görünümü kaydet" çubuğu

KURALLAR:
- AGENTS.md kural 3: her anlamlı aksiyondan sonra log_event().
- AGENTS.md kural 7: Inbox ve Bookmark aynı tablo, collection ile ayrılır. İkinci tablo açma.
- Her yazmada invalidateAfter() kullan.
- Yeni tip eklersen EntityTypeSpec'e kaydet.

DOĞRULAMA:
  cd frontend && npx vitest run   (MediaFrontend.test.tsx'te skip kalmamalı, 9 test geçmeli)
  make test
  cd backend && ruff check app tests scripts
  cd backend && python scripts/export_openapi.py && cd ../frontend && npm run api:generate && npm run api:check
YENİ BETİK: frontend/scripts/check-endpoint-coverage.mjs — openapi.json'daki
path'lerden frontend'de hiç çağrılmayanları listeler; eşik ≤3 (auth callback gibi
tarayıcı yönlendirmeleri hariç tutulur).
ELLE AKIŞ TESTİ (dev sunucusunda, ekran görüntüsüyle):
  1. Projede görev ekle → /todos'ta ve Bugün'de sayfa YENİLEMEDEN görünüyor
  2. Fırsatta yer imi kaydet → Gelen Kutusu'nda VE fırsatın "İlgili" panelinde görünüyor

ÇIKTI: kurulan akışların listesi, her biri için hangi testin koruduğu,
endpoint kapsama betiğinin çıktısı, elle akış testlerinin ekran görüntüleri.
```

---

### PROMPT — FAZ 5

```
forkOS deposunda çalışıyorsun. AGENTS.md, CLAUDE.md ve
forkOS-ENTEGRASYON-PLANI.md "FAZ 5" bölümünü oku.

GÖREV: Faz 5 — Bugün / Dashboard tam entegrasyonu. Bugün sayfası tüm modüllerin
buluştuğu tek ekran olacak; hiçbir modül "Bugün'de görünmez" kalmayacak.

BAĞLAM: Şu an Bugün'e hiç katkı vermeyen modüller: calendar, documents, learning,
todo (kendi widget'ı yok), health, settings. backend/app/modules/today/service.py
agenda'sı todo + calendar + rss + media + plan_slot birleştiriyor.

1. EKSİK WIDGET'LARI YAZ:
   - calendar: sonraki 3 günün olayları (bugün agenda'da zaten var, bu ileriye bakış)
   - documents: son değişen belgeler
   - learning: devam eden kurs ve kitap
   - todo: GECİKEN görevler (agenda bugünü gösteriyor; gecikmişler ayrı uyarı hak ediyor)
   Hepsi { component, slot, order } sözleşmesiyle kayıt olsun.

2. HEALTH MODÜLÜNÜ BUGÜN'E BAĞLA:
   Sağ sütunda yalnızca bozuk kaynak varsa görünen bir uyarı satırı.
   StatusLed zaten üst şeritte — panelde tekrar etmesin.

3. AGENDA'YI TAMAMLA (backend/app/modules/today/service.py):
   Ekle: fırsat son tarihleri (bugün/yarın), mülakatlar (saatli satır),
   bugün vadesi gelen tekrarlayan ödemeler, planlanmış study/pomodoro blokları.
   Hepsi mevcut AgendaRow sözleşmesine yeni kind değeri ekleyerek girsin;
   KIRICI DEĞİŞİKLİK YOK (frontend TodayAgendaWidget mevcut alanları okumaya devam etsin).

4. PANEL DÜZENLENEBİLİRLİĞİ:
   today.widget_order ve today.columns ayarları backend'de var ve hydrateSettings
   okuyor, ama todayColumns() Faz 1'de silindi (ölüydü). Kararı ver ve UYGULA:
   ya sütun sayısı ayarını gerçekten çalıştır (index.css'teki .dashboard-grid'i
   CSS değişkeniyle sür), ya ayarı backend'den de kaldır. Ara durum bırakma.

5. WIDGET SÖZLEŞMESİNİ SIKILAŞTIR:
   order alanını ZORUNLU yap (şu an varsayılan 50 ve çakışma üretiyor).
   TypeScript'te required olsun, 18 modülün tanımını güncelle.

6. BOŞ DURUM TUTARLILIĞI:
   Her widget veri yokken core/ui.tsx'teki Empty bileşenini variant="inline" ile
   kullansın. Şu an bazıları hiç render etmiyor, bazıları düz metin basıyor.

DOĞRULAMA:
  cd frontend && npx vitest run
  make test
  cd backend && python scripts/export_openapi.py && cd ../frontend && npm run api:generate && npm run api:check
YENİ TESTLER:
  - allTodayWidgetsIn() çıktısında en az 14 modülün katkısı var (registry testi)
  - today/agenda en az 8 kind döndürebiliyor (backend testi, her kind için ayrı)
  - Boş DB'de Bugün sayfası çökmüyor, her widget kendi boş durumunu gösteriyor
GÖRSEL: dev sunucusunda 375 / 768 / 1280 / 1600 px genişliklerinde ekran görüntüsü
al, output/playwright/ altına kaydet, üç sütunlu düzenin taşmadığını doğrula.

ÇIKTI: eklenen widget listesi, agenda'ya eklenen kind'lar, sütun ayarı kararı,
ekran görüntüleri.
```

---

### PROMPT — FAZ 6

```
forkOS deposunda çalışıyorsun. AGENTS.md, CLAUDE.md ve
forkOS-ENTEGRASYON-PLANI.md "FAZ 6" bölümünü oku.

GÖREV: Faz 6 — modül içi toparlama ve sayfa disiplini. "Dağınık modül" hissini
üreten dosyaları okunabilir hale getir ve AGENTS.md'deki modül reçetesine döndür.
DAVRANIŞ DEĞİŞMEZ; bu bir yeniden düzenleme fazı.

1. TEK SATIRA SIKIŞTIRILMIŞ SAYFALARI AÇ (en uzun satırdan başla):
   modules/learning/LearningPage.tsx      en uzun satır 2.596 karakter
   modules/settings/SettingsPage.tsx      2.171
   modules/study/StudyPage.tsx            1.528
   modules/documents/DocumentsPage.tsx    1.038
   modules/finance/RecurringWidget.tsx      593
   modules/opportunity/OpportunityWidget.tsx 495
   ve tek satır yazılmış 7 modül index.ts dosyası.

   LearningPage'i CoursesTab / BooksTab / QueueTab olarak üç bileşene böl.
   DİKKAT: aynı etiket sözlüğü ({watch:"İzle", read:"Oku", ...}) dosya içinde
   İKİ KEZ kopyalanmış — tek sabite indir.
   SettingsPage'i bölümlere ayır: IntegrationsSection, BackupSection,
   ModulesSection, WeatherSection, MediaLinksSection.

   KURAL: hiçbir satır 120 karakteri geçmesin. Prettier ekle (printWidth 120),
   package.json'a "format" ve "format:check" script'leri koy.

2. ŞİŞMİŞ BACKEND SERVİSLERİNİ BÖL:
   modules/media/service.py       1.545 → service.py + progress.py + collections.py + search.py
   modules/opportunity/service.py   771 → service.py + application.py (CRM kısmı)
   modules/opportunity/router.py    522 → router.py + sources_router.py
                                          (kaynak/jobhunter uçları)
   modules/media/schemas.py         483 → schemas.py + validators.py
   Hedef: hiçbir backend servis dosyası 600 satırı geçmesin.
   Public import yollarını koru; kırılan import kalmasın.

3. KAYNAK SAĞLIĞINI TEK YERE İNDİR (docs/faz0-kararlar.md K4):
   Şu an üç yerde: /sources (opportunity modülü), /health (health modülü),
   SettingsPage. K4 kararına göre tek yetkili sayfayı belirle,
   diğerlerini yönlendirmeye veya tek satırlık özete indir.
   opportunity modülünün /sources rotası kalkarsa modules/opportunity/index.ts'i
   ve SourceHealthPage dosyasını buna göre taşı/sil.

4. MIGRATION ADLANDIRMASINI DÜZELT:
   Gerçek zincir: ... 0026_media_domain → 0022_finance_sub → 0023_application_crm
   Yani gerçek head 0023_application_crm, ama dosya adları 0026'yı en son gösteriyor.
   İKİ SEÇENEK, birini seç ve gerekçesini yaz:
   (a) Dosyaları 0027_finance_sub / 0028_application_crm olarak yeniden adlandır.
       revision STRING'İ DEĞİŞMEZ — sadece dosya adı ve baştaki yorum.
       alembic_version tablosundaki değer korunur, veri etkilenmez.
   (b) Dosya adlarına dokunma, backend/alembic/README.md'ye gerçek zinciri
       gösteren bir tablo koy.

5. TEST BOŞLUKLARINI DOLDUR:
   Hiç testi olmayan frontend modülleri: study, learning, inbox, health, finance,
   documents, calendar, bookmarks. Her birine en az bir akış testi yaz.
   Mevcut desen: modules/media/MediaPage.test.tsx (fetch stub + renderView).

DOĞRULAMA:
  cd frontend && npm run format:check    (yeni script)
  cd frontend && npx vitest run
  cd frontend && npm run build
  make test
  cd backend && ruff check app tests scripts
  Hiçbir backend servis dosyası 600 satırı geçmiyor:
    find backend/app -name '*.py' | grep -v __pycache__ | xargs wc -l | sort -rn | head

ÇIKTI: bölünen dosyalar ve yeni yapıları, migration kararı ve gerekçesi,
eklenen testler, format:check sonucu.
```

---

### PROMPT — FAZ 7

```
forkOS deposunda çalışıyorsun. AGENTS.md, CLAUDE.md ve
forkOS-ENTEGRASYON-PLANI.md "FAZ 7" bölümünü oku.

GÖREV: Faz 7 — guardrail, test ve dokümantasyon. Önceki 7 fazın kazanımının
bir sonraki özellikte geri kaymasını engelle.

1. AGENTS.md VE CLAUDE.md'YE YENİ DEĞİŞMEZ KURALLARI EKLE
   (ikisi senkron kalmalı; CLAUDE.md Claude, AGENTS.md Codex içindir ama
    kural listesi aynıdır):
   13. Entity tipi, etiketi ve rotası yalnız EntityTypeSpec'te tanımlanır.
       Frontend'de tip→rota veya tip→etiket sabiti yazma.
   14. Mutation sonrası tazeleme invalidateAfter() ile yapılır;
       ham invalidate("a","b") yasak.
   15. Renk, boyut ve yarıçap yalnız tasarım tokenlarından gelir.
       text-[Npx], sabit hex ve ham <input>/<select>/<button> yasak.
   16. Son tarih üreten modül deadline_provider sağlar; deadline_v benzeri
       elle SQL görünümü yazılmaz.
   17. Kayıtlı olup frontend'den çağrılmayan uç bırakma; uç ya kullanılır ya silinir.
   Her kuralın yanına onu koruyan testin adını yaz.

2. CI İŞLERİ EKLE (.github/workflows/ci.yml):
   - frontend/scripts/check-endpoint-coverage.mjs (Faz 4'te yazıldı) — eşikli
   - npm run format:check (Faz 6'da eklendi)
   - Ölü export taraması: kullanılmayan export'ları listeleyen betiği
     frontend/scripts/check-dead-exports.mjs olarak kalıcı hale getir, eşikle bağla.
   - core/designSystem.test.ts zaten vitest run içinde koşuyor, ayrı iş gerekmez.

3. README.md GÜNCELLE:
   "Ne var" tablosuna "Modüller arası bağlar" satırı ekle.
   "Önemli endpoint'ler" listesini gerçek durumla eşitle (Faz 1'de silinen,
   Faz 4'te bağlanan uçlar).
   Faz durumunu güncelle.

4. docs/mimari.md YAZ:
   Yeni modül ekleyecek kişinin okuyacağı TEK doküman:
   - entity / link / event üçlüsü nasıl kullanılır, hangi helper neyi yapar
   - ilişki (relation) sözlüğü ve ileri/geri etiketleri
   - kayıt defterlerinin listesi: MODULES, EntityTypeSpec, event_verbs,
     deadline_provider, frontend registerModule, invalidation AFTER haritası
   - Bugün widget sözleşmesi (slot, order, boş durum kuralı)
   - tasarım tokenları ve hangi durumda hangi ton kullanılır
   Her bölümde gerçek bir dosya referansı olsun.

5. MIGRATION TESTİNİ GENİŞLET:
   backend/tests/test_migrations.py şu an model↔migration karşılaştırıyor.
   deadline_v Faz 3'te düşürüldüyse onun da olmadığını doğrula.

DOĞRULAMA:
  Tüm CI işleri yeşil: make test, backend-lint, frontend-verify, extension-verify
  cd frontend && npx vitest run && npm run build && npm run format:check
  Yeni betiklerin eşikleri tutuyor.
  docs/mimari.md ile yeni bir modül ekleme turu (kağıt üstünde) tamamlanabiliyor.

ÇIKTI: eklenen kurallar ve onları koruyan testlerin eşleşme tablosu,
CI iş listesi, docs/mimari.md özeti.
```

---

## 6. Ek — Bulguları yeniden üretme komutları

Bu planın dayandığı ölçümleri kendin doğrulamak istersen:

```bash
# Frontend'den hiç çağrılmayan API uçları
cd backend && python3 -c "
import json,re,os
spec=json.load(open('openapi.json'))
fe=[]
for r,_,fs in os.walk('../frontend/src'):
    if 'generated' in r: continue
    fe += [open(os.path.join(r,f)).read() for f in fs
           if f.endswith(('.ts','.tsx')) and '.test.' not in f]
blob='\n'.join(fe)
for p in spec['paths']:
    q=p[4:] if p.startswith('/api') else p
    parts=[re.escape(s) for s in re.split(r'\{[^}]+\}',q)]
    pat=''.join(parts[:1]+['[^\"\\'\`]*'+x for x in parts[1:]])
    if not re.search(pat,blob): print(p)
"
```

```bash
# Tasarım ihlalleri
cd frontend/src
grep -rnoE 'text-\[[0-9.]+px\]' . | grep -v test | wc -l          # keyfi tipografi
grep -rnoE '#[0-9a-fA-F]{6}' --include='*.tsx' . | grep -v test    # sabit hex
grep -rn '<input\|<select' --include='*.tsx' . | grep -v test | wc -l
grep -rnoE 'rounded-(md|lg|xl|2xl)' . | grep -v test | wc -l
```

```bash
# En uzun satırlar (dağınık sayfalar)
cd frontend/src
for f in $(find . -name '*.tsx' | grep -v test); do
  awk -v f="$f" '{if(length>m)m=length}END{if(m>200)print m, f}' "$f"
done | sort -rn
```

```bash
# Modüller arası bağ sayısı
cd backend && grep -rn "await link(" app --include='*.py' | grep -v __pycache__

# today-agenda'yı kim tazeliyor
cd frontend/src && grep -rn "today-agenda" . | grep -v test
```
