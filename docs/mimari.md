# forkOS yaşayan mimarisi

Bu belge forkOS'un güncel teknik sözleşmesini anlatır. Tamamlanmış fazların değişiklik günlüğü değildir; yeni bir modül veya entegrasyon geliştirirken başvurulacak yaşayan kaynaktır. Bağlayıcı agent kuralları `AGENTS.md` dosyasındadır.

## 1. Çalışma modeli

forkOS tek makinede ve tek kullanıcı için çalışır:

```text
Chrome extension ─┐
React/Vite PWA ───┼──> FastAPI ───> PostgreSQL 16
                  │        │
                  │        └──> kalıcı kaynak kuyruğu ──> SourceAdapter'lar
                  │
                  └──> isteğe bağlı APScheduler worker aynı kuyruğu tüketir
```

| Servis | Görev | Varsayılan adres |
| --- | --- | --- |
| `web` | React/Vite arayüz ve PWA | `127.0.0.1:5173` |
| `api` | FastAPI, iş kuralları ve manuel yenileme | `127.0.0.1:8787` |
| `db` | PostgreSQL 16 | `127.0.0.1:5433` |
| `worker` | Zamanlanmış kaynak ve bakım işleri | profil kapalı |

Manuel genel yenileme worker'a bağımlı değildir. API bir batch oluşturur ve aynı kalıcı kaynak kuyruğunu arka planda tüketir. Worker açılırsa yarım kalan/due işleri aynı sözleşmeyle devralır.

## 2. Entity, link ve event omurgası

### Entity

`backend/app/core/models.py::Entity`, bütün aranabilir ve linklenebilir kayıtların kimliğidir:

- `id`: sistem genelinde UUID
- `type`: registry'deki entity tipi
- `title`: ortak görünen başlık
- `search_text`: FTS/trigram arama içeriği
- `archived_at`: ortak yaşam döngüsü

Bir modülün ana kaydı `EntityBacked` olur ve PK'si aynı zamanda `entity.id` alanına FK'dır. Yazmalar `backend/app/core/entity.py` içindeki `create_entity`, `touch_entity`, `archive_entity` ve `delete_entity` helper'larından geçer.

### Link

`link`, iki entity arasında yönlü ilişki kurar: `from_id → to_id`. İlişki sözlüğünün tek kaynağı `backend/app/core/links.py::RELATIONS` değeridir. Frontend ilişkileri `RelatedPanel` ve `BacklinksPanel` üzerinden gösterir.

Yeni bir ilişki eklerken:

1. İleri/geri Türkçe etiket çiftini `RELATIONS` içine ekle.
2. Bağı aynı transaction içinde yaz.
3. Anlamlı event üret.
4. Frontend'de `invalidateAfter("link.write")` kullan.

### Event

`event` append-only aksiyon günlüğüdür. Domain tabloları güncel durumu, event ise nasıl o duruma gelindiğini taşır. Event satırları güncellenmez veya silinmez.

```python
await log_event(
    session,
    verb="note.updated",
    entity_id=note.id,
    entity_type="note",
    payload={"fields": ["body"]},
)
```

Activity, ritim/ısı haritası, review özetleri ve bazı proje zaman akışları bu günlükten türetilir.

## 3. Registry'ler

### Backend

`backend/app/modules/__init__.py` iki merkezi sözleşmeyi taşır:

- `MODULES`: router, event verb'leri ve deadline provider'lar
- `EntityTypeSpec`: entity tipi → etiket, çoğul etiket, ikon ve frontend rotası

`main.py`, arama, deadline toplama ve registry uçları bu listeden beslenir. Yeni modül için özel `main.py` bağlantısı yazılmaz.

### Frontend

`frontend/src/modules/index.ts`, her frontend modülünü bir kez import eder. Modülün `index.ts` dosyası `registerModule(...)` ile şunları kaydeder:

- route'lar
- sidebar hiyerarşisi
- komut paleti eylemleri
- Today widget'ları

Entity linkleri ve global arama hedefleri backend registry'sinden gelen veriyi `frontend/src/core/entityRegistry.ts` içindeki `entityRoute()` ve `typeLabel()` üzerinden çözer.

## 4. Modül anatomisi

### Backend

```text
backend/app/modules/<name>/
├── __init__.py     MODULE = ModuleSpec(...)
├── models.py       EntityBacked domain modelleri
├── schemas.py      Pydantic sözleşmeleri
├── service.py      Transaction ve iş kuralları
└── router.py       İnce HTTP katmanı
```

Router transaction/iş mantığını tekrar etmez. Entity helper'ları, link ve event yazımları service katmanında aynı transaction sınırında yürür.

### Frontend

```text
frontend/src/modules/<name>/
├── index.ts        registerModule(...)
├── <Name>Page.tsx  çalışma alanı kompozisyonu
├── bileşenler
└── *.test.ts(x)
```

Sayfa, uygulama kabuğunu veya ikinci bir navigasyonu yeniden üretmez. Ortak yüzeyler `frontend/src/core/shell`, form ve durum bileşenleri `frontend/src/core/ui.tsx` üzerinden gelir.

## 5. Modüller arası sözleşmeler

### Mutation invalidation

`frontend/src/core/invalidation.ts::AFTER`, bir domain yazımının hangi query key'lerini tazeleyeceğinin tek kaynağıdır:

```ts
invalidateAfter("todo.write", "plan.write");
```

Yeni mutation için önce anlamlı event adını/invalidasyon girdisini ekle; bileşenlere dağılmış ham query-key listeleri yazma.

### Görev oluşturma

Backend'de görev oluşturmanın tek sınırı todo service'tir. Opportunity, learning ve project gibi bağlamlar bu service'e delege eder, sonra kendi linkini aynı transaction içinde kurar.

Frontend'de `frontend/src/core/tasks.ts`, bütün manuel görev girişlerinin ortak intent katmanıdır. `plan_day` “o gün yap” anlamına gelir; `due_at` teslim tarihidir ve birbirine dönüştürülmez.

### Evrensel yakalama

`frontend/src/core/capture.ts`, görev/not/bağlantı yakalama intent'lerini tek noktada toplar. Extension yazımları `client_uuid` ile idempotenttir. Inbox ve Bookmark aynı domain tablosunu kullanır; `collection` kayıt durumunu belirler.

### Son tarihler

Son tarih üreten modüller `ModuleSpec.deadline_provider` sağlar. `backend/app/core/deadlines.py` sağlayıcıları toplar. SQL union view veya modüller arası elle join zinciri kullanılmaz.

### Today

Today bir veri sahibi değil, orkestrasyon yüzeyidir. Modüller `todayWidgets` ile benzersiz ve kalıcı widget ID'leri kaydeder. Kullanıcının sıra/görünürlük tercihleri bu ID'lere bağlıdır.

Agenda; görev, plan, takvim, fırsat, öğrenme ve medya kayıtlarını tek günlük read-model içinde birleştirir. Bir widget hatası diğer widget'ları engellememelidir.

### Pomodoro

Pomodoro sunucu otoritelidir; sayfadan bağımsız global yüzey yalnızca aktif session'ı yansıtır. Context bir entity'ye bağlanabilir. Tamamlanan session domain'e özgü tüketim/çalışma event'lerine köprü olabilir.

### Notlar ve bilgi grafı

Notlar entity-backed'tir. Markdown body, klasör, ekler, varsayılan görünüm ve Excalidraw canvas state aynı domain içinde yaşar. Wiki linkleri ve açık entity linkleri bilgi grafına katılır. Büyük attachment içeriği liste uçlarında yüklenmez; detay/attachment uçlarından alınır.

## 6. Kaynak ve scraper mimarisi

Her yeni ağ kaynağı `backend/app/sources/base.py` içindeki `SourceAdapter` sözleşmesini uygular. Öncelik sırası:

1. Resmî API veya JSON-LD/schema.org
2. Kararlı HTML seçiciler
3. Kontrollü fallback ayrıştırma

Her çalıştırma `source_run` üretir. Sonuç sınıfları en az `ok`, `empty` ve `error` ayrımını korur; hata türü teşhis edilebilir olmalıdır. Üç beklenmedik boş sonuç veya tekrarlayan hata kaynak sağlığına ve bildirimlere yansır.

`backend/app/core/source_sync.py` kalıcı batch/kuyruk sahipliğini yönetir. Uzun senkron:

- API request ömrüne güvenmez,
- yeniden başlatmadan sonra devam edebilir,
- aynı kaynağın eşzamanlı sahiplenilmesini engeller,
- ilerlemeyi tamamlanan/toplam kaynak olarak raporlar,
- LinkedIn gibi opt-in kaynakları açık seçim olmadan çalıştırmaz.

Başarılı HTTP yanıtlarını sınırsız biçimde diske yığma. Cache'in okuma yolu, boyut/yaş sınırı ve pruning davranışı tanımlı olmalıdır.

## 7. Arama

PostgreSQL'te Türkçe stemmer varsayılmaz. Arama:

- `simple` text search config,
- `immutable_unaccent()`,
- `pg_trgm`,
- entity `title + search_text`

bileşimiyle çalışır. Yeni aranabilir domain kaydı entity başlığı ve arama metnini create/update sırasında güncel tutar.

## 8. Tasarım sistemi

Tasarım tokenları `frontend/src/index.css` ve `frontend/tailwind.config.js` dosyalarındadır. Ortak primitive'ler `frontend/src/core/ui.tsx` içindedir.

- Semantik renkler: `accent`, `ok`, `warn`, `danger`
- Kimlik renkleri: `kind-*`, `src-*`, `feed-*`
- Grafik renkleri: `chart-1..8`
- Z-index: adlandırılmış katman tokenları
- Formlar: `Input`, `Select`, `Checkbox`, `Range`, `NumberInput`, `FileInput`, `Chip`

Loading için skeleton, veri yokluğu için açıklayıcı empty state, hata için erişilebilir geri bildirim kullan. Modal/popover focus yönetimi, Escape ve focus restore sözleşmesini korur.

## 9. Veri, gizlilik ve yedek

- PostgreSQL kalıcı verisi `forkos_pgdata` named volume'ündedir.
- Belge, attachment, medya cache'i, OAuth token'ları ve kişisel config Git'e girmez.
- Secret setting anahtarlarının tek kaynağı `backend/app/modules/system/secrets.py::SECRET_SETTING_KEYS` listesidir.
- Export ve taşınabilir yedek secret satırlarını içermez.
- Normal restore merge/idempotent'tir; mevcut veriyi silmez.
- Gerçek disaster restore uygulama dışı CLI sınırıdır, önce doğrulanmış safety dump alır ve transaction tamamlanmadan commit etmez.

Local-only, “hiç ağ isteği yok” anlamına gelmez. RSS, ilan, katalog ve açıkça bağlanan Google/GitHub entegrasyonları dış kaynaklardan veri çeker; kişisel veritabanını buluta yüklemez. Yeni paket veya ağ davranışında `.agents/skills/local-privacy-audit/SKILL.md` uygulanır.

## 10. Migration ve API sözleşmesi

Migration'lar elle yazılır; her SQL komutu ayrı `op.execute()` çağrısıdır. Yeni revision önce `alembic heads` çıktısındaki gerçek head'e bağlanır. Ayrıntı: `backend/alembic/README.md`.

FastAPI/Pydantic sözleşmesi değişirse:

```bash
cd backend
python scripts/export_openapi.py
cd ../frontend
npm run api:generate
npm run api:check
```

Generated TypeScript dosyası elle düzenlenmez.

## 11. Doğrulama

```bash
# İzole backend + migration testleri
make test CO="docker compose"

# Backend lint + frontend test/build + extension
make verify CO="docker compose"
```

Özellikle şu guardrail'ler mimari drift'i durdurur:

- entity-backed tablo ve tek migration head
- append-only event davranışı
- entity registry route/label sahipliği
- merkezi mutation invalidation
- design token ve UI primitive kullanımı
- frontend tarafından tüketilmeyen endpoint sınırı
- test DB'nin kişisel DB'den izolasyonu
