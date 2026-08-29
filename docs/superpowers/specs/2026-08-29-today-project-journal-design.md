# Today ve Proje Günlüğü Tasarımı

Tarih: 2026-08-29

## Amaç

Today ekranındaki dikey alan kullanımını azaltmak, okuma akışını tekrar görünür ve hata toleranslı yapmak, Projeler sayfasındaki serbest not ile append-only olay akışını gün bazlı tek bir çalışma günlüğünde birleştirmek.

## Kapsam

### Today agenda

- Tamamlananlar bölümü erişilebilir bir disclosure/akordeon olur.
- Bölüm varsayılan olarak kapalı açılır, başlıkta kayıt sayısı görünür.
- Açık/kapalı durum yalnız bileşen ömrü boyunca korunur; kalıcı kullanıcı ayarı oluşturulmaz.
- Öneriler bölümü birleşik todo ve RSS adaylarından en fazla iki satır gösterir.
- Önerilerin sırası backend cevabındaki mevcut sırayı korur.
- Açık todo ve okunmamış RSS satırlarında görünür, erişilebilir `Tamamla`
  aksiyonu bulunur. Aksiyon mevcut complete mutation'ını kullanır; context-only
  ve tamamlanmış satırlarda gösterilmez.

### Okuma akışı

- `today.feed-stream` varsayılan görünür widget olur.
- Daha önce varsayılan gizleme nedeniyle saklanmış tercih, tek seferlik registry ayarı göçüyle görünür hale getirilir.
- RSS, Reddit, Hacker News ve GitHub sorguları birbirinden bağımsız kalır.
- Bir kaynak hata verdiğinde diğer kaynakların verisi gösterilmeye devam eder.
- Tümü filtresinde hata veren kaynaklar kompakt bir durum satırında belirtilir; kaynak filtresinde boş/hata durumu açıkça gösterilir.
- Yeniden deneme aksiyonu yalnız hata veren sorguları tekrar çalıştırır.
- Canlı incelemede `/news/hacker-news`, `/news/github-trending` ve `/rss/items` uçlarının veri döndürdüğü doğrulandı. Ana kök neden widget'ın `defaultVisible: false` olması ve kalıcı gizleme tercihidir.

## Proje günlüğü

### Veri modeli

- Mevcut `Note` entity tipi yeniden kullanılır; ikinci bir not veya journal entity tipi oluşturulmaz.
- `note` tablosuna opsiyonel `project_id` ve `journal_day` alanları eklenir.
- `project_id` doluysa `journal_day` zorunludur. Normal notlarda iki alan da boştur.
- `(project_id, journal_day)` üzerinde benzersizlik vardır; her proje ve uygulama günü için en fazla bir günlük notu bulunur.
- `project_id`, proje silinirse `SET NULL` olur. Günlük notu ve tarih bilgisi normal yerel not olarak korunur.
- Günlük notu oluşturulurken nota `notes_about` ilişkisi de eklenir. Böylece RelatedPanel ve global ilişki yüzeyleri mevcut sözleşmeyle çalışır.
- Eski `project.notes` alanı kullanılmadığı için migration ile kaldırılır. Kullanıcı mevcut verinin önemsiz olduğunu onayladı.

### API

- `GET /projects/{project_id}/journal?limit=60` günlüğü döndürür.
- Cevap günlere göre gruplanmış olaylar ve varsa o günün notunu içerir.
- `PUT /projects/{project_id}/journal/{day}` seçili günün notunu create-or-update yapar.
- Gelecek günler 400 ile reddedilir; bugün ve geçmiş günler kabul edilir.
- Boş veya yalnız whitespace gövde mevcut günlük notunu siler, yoksa no-op döner.
- Upsert, entity helper'ları ve Note service sınırını kullanır; anlamlı create/update/delete event'leri korunur.
- Timeline verisi mevcut append-only `event` tablosundan gelir ve değiştirilmez.

### Arayüz

- Proje detayındaki ayrı `Notlar` ve `Günlük` bölümleri kaldırılır; yerlerine tek `Proje günlüğü` yüzeyi gelir.
- Üst satırda bugün varsayılan tarih seçici ve seçili günün kısa özeti bulunur. Tarih seçicinin `max` değeri uygulama günüdür.
- Seçili günün notu olay listesinin üstünde düzenlenir; blur ile kaydedilir ve kayıt durumu görünür.
- Alt bölüm gün gruplarını yeni tarihten eskiye gösterir. Her grupta not önizlemesi ve o günün immutable olayları aynı dikey zaman çizgisinde yer alır.
- Bir gün grubuna basmak o günü editöre taşır.
- Boş, yükleniyor ve hata durumları mevcut `Section`, `Empty`, `Textarea`, `Button` ve token sistemiyle gösterilir.
- Yeni görsel kütüphane, renk, radius veya ham form kontrolü eklenmez.

## Veri akışı ve invalidation

- Journal GET query key'i `project-journal, projectId` olur.
- Günlük notu mutation'ı `invalidateAfter("note.write", "project.write", "link.write")` çağırır.
- Timeline olayları ve not aynı endpoint cevabından geldiği için yarım görsel durum oluşmaz.
- Proje değiştiğinde tarih bugüne ve editör yeni projenin bugünkü notuna sıfırlanır.

## Hata yönetimi

- Journal yüklenemezse mevcut proje panelleri çalışmaya devam eder ve journal içinde yeniden deneme görünür.
- Not kaydı başarısızsa taslak korunur, kullanıcıya toast gösterilir ve kaydedilmemiş durumu sürer.
- Feed kaynak hataları diğer kaynakları gizlemez.
- Offline durumda journal okunabilir; tarih ve not mutation'ları kapalıdır.

## Test stratejisi

- Frontend: tamamlanan akordeonunun kapalı/açık durumu ve `aria-expanded`.
- Frontend: önerilerin iki satırla sınırlandırılması.
- Frontend: açık todo satırındaki Tamamla aksiyonunun doğru endpoint'i çağırması.
- Frontend: feed widget varsayılan görünürlüğü, eski gizleme tercihinin göçü ve kaynak bazlı hata/retry.
- Backend: journal günü için create, update, boş gövdeyle delete, gelecek gün reddi ve proje/gün benzersizliği.
- Backend: journal cevabında not ve event'lerin aynı gün grubunda birleşmesi.
- Frontend: ProjectJournal tarih seçimi, save gövdesi, gün grupları ve hata durumu.
- Regresyon: backend, frontend, extension, OpenAPI ve production build doğrulamaları.

## Kapsam dışı

- Bir günde birden fazla proje notu.
- Gelecek günlere günlük notu yazma.
- Rich text, dosya eki, yorum sistemi veya ayrı journal modülü.
- Event kayıtlarını düzenleme veya silme.
