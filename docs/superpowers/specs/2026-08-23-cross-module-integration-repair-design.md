# Modüller Arası Entegrasyon Onarım Tasarımı

**Tarih:** 2026-08-23
**Durum:** Onaylandı

## Amaç

Today, Görevler, Plan, Takvim ve Projeler aynı çekirdek verileri kullanıyor ancak
bazı yazma akışları ilişkileri eksik taşıyor veya bağlı ekranların sorgularını
zamanında yenilemiyor. Bu çalışma, medya modülüne dokunmadan bu gerçek kopuşları
onarır.

Başarı ölçütleri:

- Proje görevi tek atomik işlemle oluşturulur ve projeye bağlanır.
- Alt görevler ve tekrar eden görevler proje ile kilometre taşı bağlamını korur.
- Proje aktivitesi görev, kilometre taşı, GitHub ve bağlamlı odak hareketlerini
  doğru gösterir.
- Today widget'ları ile ayrıntı sayfaları aynı sorgu anahtarları üzerinden
  yenilenir.
- Kilometre taşları kullanıcı tarafından manuel tamamlanmaya devam eder.

## Kapsam

Kapsama dahil:

- Todo–proje–kilometre taşı ilişki mirası
- Atomik proje görevi oluşturma
- Proje aktivitesi ve timeline bütünlüğü
- Todo bağlamlı Pomodoro hareketlerinin proje timeline'ına katılması
- Today/takvim/finans/RSS sorgu invalidation uyumu
- Backend ve frontend regresyon testleri

Kapsam dışında:

- Medya modülünün Today, Review veya emek haritasına bağlanması
- Kilometre taşının görevlerden otomatik tamamlanması
- Yeni tablo veya Alembic migration
- Proje silindiğinde bağlı görevlerin silinmesi

## Mimari Karar

Backend merkezli entegrasyon uygulanır. Frontend ilişkileri ayrı isteklerle
orkestre etmez; ilişki doğrulama, miras ve transaction sınırı servis katmanında
kalır.

### Todo oluşturma

`TodoIn` şemasına isteğe bağlı `project_id` eklenir. `/api/todos` çağrısı:

1. Açıkça verilen proje ve kilometre taşını doğrular.
2. `parent_id` varsa ebeveynin proje ve kilometre taşı bağlamını okur.
3. Açık değerlerle miras alınan değerler çelişiyorsa isteği reddeder.
4. Entity, todo, etiket, `belongs_to` link'i ve `todo.created` event'ini aynı
   transaction içinde yazar.

Bir kilometre taşı yalnızca ait olduğu projeyle birlikte kullanılabilir.
Kilometre taşı verilip proje verilmezse proje, kilometre taşından türetilir.

Proje sayfasındaki görev formu iki istek yerine tek `/api/todos` isteği gönderir.
Mevcut `/api/projects/{project_id}/todos` link endpoint'i, önceden oluşturulmuş
bir görevi projeye bağlama yeteneğini korur.

### Alt görev bağlamı

Yeni todo bir `parent_id` taşıyorsa:

- Ebeveynin `belongs_to` proje link'i devralınır.
- Ebeveynin `milestone_id` değeri devralınır.
- İstemci aynı değerleri açıkça gönderebilir; farklı proje veya kilometre taşı
  gönderirse `400` döner.

Bu davranış TodoRow, Today, Görevler ve Projeler sayfasından oluşturulan bütün alt
görevlerde aynıdır.

### Tekrar eden görev bağlamı

Tamamlanan tekrar eden görevden yeni kayıt üretilirken başlık, açıklama, öncelik,
planlanan tarih, tekrar bilgisi ve etiketlere ek olarak şunlar kopyalanır:

- `milestone_id`
- `belongs_to` proje link'i

Yeni todo ve link aynı transaction içinde oluşturulur. Aynı serinin açık kaydı
zaten varsa mevcut idempotent davranış korunur.

### Proje aktivitesi

API'nin döndürdüğü proje `last_activity_at` değeri şu zamanların en yenisi olur:

- Projenin mevcut GitHub `last_activity_at` kolonu
- Projeye bağlı todo entity'lerinin `updated_at` değeri
- Projenin kendi entity `updated_at` değeri

Bu değer listeleme sırasında toplu sorguyla hesaplanır; proje başına ayrı sorgu
üretilmez. Veritabanındaki kolon GitHub senkron zamanını saklamaya devam eder.

Kilometre taşı ekleme, güncelleme, tamamlama ve silme işlemleri proje entity'sine
append-only event yazar. Event payload'u kilometre taşı kimliği, başlığı ve değişen
alanları taşır. Kilometre taşı otomatik tamamlanmaz.

### Pomodoro ve proje timeline'ı

`pomodoro.completed` ve `pomodoro.interrupted` event payload'larına
`context_entity_id` ile `context_type` eklenir. Proje timeline sorgusu:

- Proje event'lerini,
- Bağlı todo event'lerini,
- Projenin GitHub commit event'lerini,
- Bağlı todoları bağlam alan tamamlanmış/kesilmiş Pomodoro event'lerini

tek kronolojik listede birleştirir. Pomodoro event'inin kendi `entity_id` değeri
değişmez; event Pomodoro entity'sine bağlı kalır.

## Frontend Veri Akışı

TanStack Query anahtarları modül bazında ortak prefix kullanır:

- Today takvim widget'ı: `["calendar-events", "today"]`
- Today ödeme widget'ı: `["recurring", "widget"]`
- Proje görevi ve kilometre taşı mutation'ları:
  `projects`, `project-todos`, `project-timeline`, `todos`, `activity`
- RSS item'ını bookmark'a kaydetme:
  mevcut anahtarlara ek olarak `bookmark-stats`

Prefix invalidation sayesinde Today ile ayrıntı sayfaları aynı mutation sonrası
yenilenir. Global `staleTime` davranışı değiştirilmez.

Proje kartına tıklama mevcut `/projects` rotasını kullanmaya devam eder; seçili
proje için yeni URL veya router değişikliği bu çalışmanın kapsamı değildir.

## Hata Yönetimi ve Transaction Sınırları

- Geçersiz proje, ebeveyn veya kilometre taşı için `400`/`404` döner.
- Proje–kilometre taşı uyuşmazlığı herhangi bir kayıt yazılmadan reddedilir.
- Entity, todo, etiket, link ve event aynı transaction sınırındadır.
- Link oluşturma başarısız olursa todo/entity kaydı commit edilmez.
- Frontend mevcut hata toast'ını gösterir; ikinci bir telafi isteği çalıştırmaz.
- Proje silinince link cascade ile kalkar, todo kayıtları korunur.
- Event tablosu append-only kalır; onarım UPDATE/DELETE event işlemi eklemez.

## Test Tasarımı

### Backend entegrasyon testleri

1. `project_id` ile todo oluşturmak todo ve `belongs_to` link'ini tek istekte
   üretir.
2. Geçersiz proje veya başka projeye ait kilometre taşı kayıt bırakmaz.
3. Alt görev ebeveynin proje ve kilometre taşı bağını devralır.
4. Çelişen açık alt görev bağlamı reddedilir.
5. Tekrar eden görev tamamlanınca oluşan kayıt aynı proje ve kilometre taşına
   bağlıdır.
6. Bağlı görev güncellemesi proje çıktısındaki `last_activity_at` değerine
   yansır.
7. Kilometre taşı event'leri proje timeline'ında görünür.
8. Todo bağlamlı tamamlanmış Pomodoro proje timeline'ında görünür.

### Frontend testleri

1. Proje görev formu tek `/todos` çağrısı yapar ve `project_id` ile
   `milestone_id` gönderir.
2. Today takvim widget'ı `calendar-events` prefix'ini kullanır.
3. Today ödeme widget'ı `recurring` prefix'ini kullanır.
4. RSS bookmark mutation'ı `bookmark-stats` sorgusunu invalidate eder.

### Tam doğrulama

- `docker compose exec -T api pytest -q`
- `docker compose exec -T api ruff check app tests`
- `cd frontend && npm test`
- `cd frontend && npm run build`
- `git -c core.whitespace=cr-at-eol diff --check`

## Kabul Kriterleri

- Proje sayfasından görev eklerken yarım veya sahipsiz todo oluşamaz.
- Alt ve tekrar eden görevler projeden veya kilometre taşından kopmaz.
- Todo, milestone ve bağlamlı Pomodoro hareketleri proje timeline'ında görünür.
- Today görev/proje/takvim/ödeme/bookmark göstergeleri ilgili sayfadaki mutation
  sonrasında yeniden sorgulanır.
- Mevcut Todo → Plan → Pomodoro → Habit → Review dikey testi geçmeye devam eder.
- Medya modülünde davranış değişikliği olmaz.
