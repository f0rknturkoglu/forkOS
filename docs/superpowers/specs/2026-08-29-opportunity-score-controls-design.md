# Fırsat Skor Kontrolleri Tasarımı

## Amaç

İş ilanlarını hesaplanmış uyum skoruna göre açıkça sıralanabilir ve belirli bir skor aralığına göre süzülebilir hale getirmek. Duyuruların skor semantiği olmadığı için bu kontroller yalnızca İş İlanları çalışma alanında görünür.

## Kullanıcı deneyimi

Filtre paneline `Uyum skoru` bölümü eklenir. Bölüm dört hazır bant sunar:

- `70–100` — güçlü eşleşme
- `40–69` — değerlendirilebilir eşleşme
- `0–39` — düşük eşleşme
- `Elendi` — negatif skor

Hazır bantların yanında minimum ve maksimum skor için tasarım sistemi `NumberInput` kontrolleri bulunur. Kullanıcı hazır bir banda bastığında alanlar doldurulur; aynı banda tekrar basmak skor filtresini temizler. Alanlar elle değiştirildiğinde hazır bant seçimi kendiliğinden güncellenir.

Skor aralığı etkin olduğunda skoru olmayan ilanlar sonuçlara dahil edilmez. Aralık kaldırıldığında skorsuz ilanlar tekrar görünür. Bölümdeki temizleme eylemi yalnız skor aralığını sıfırlar.

Sıralama seçenekleri iş ilanlarında açık adlarla sunulur:

- `Skor: yüksekten düşüğe`
- `Skor: düşükten yükseğe`
- mevcut tarih ve son tarih sıralamaları

Her iki skor sıralamasında da skorsuz ilanlar listenin sonunda tutulur. Eşit skorlarda mevcut tarih, başlık ve kimlik bağlayıcıları kararlı sayfalamayı korur.

## API ve veri akışı

`GET /api/opportunities/browse` iki isteğe bağlı parametre alır: `min_score` ve `max_score`. Değerler skorun mevcut alanı olan `raw.forkjob.score` üzerinden sayıya çevrilerek filtrelenir; yeni tablo veya migration gerekmez.

API kabul edilen skor sınırını `-1..100` olarak doğrular. Yalnız bir uç gönderilebilir. İki uç gönderilip minimum maksimumdan büyükse API `422` döndürür. Skor sıralaması için mevcut `score` geriye dönük uyumlulukla yüksekten düşüğe davranmaya devam eder; yeni `score_asc` düşükten yükseğe sıralar.

Frontend filtre durumu ve sorgu anahtarı `min_score` ile `max_score` değerlerini taşır. İş İlanları dışındaki bölümlere geçildiğinde bu alanlar sorguya gönderilmez ve bölüm değişiminde temizlenir.

## Hata ve sınır durumları

- Boş sayı alanı ilgili sınırı kaldırır.
- Frontend değerleri `-1..100` aralığında tutar ve minimumun maksimumu aşmasını engeller.
- Doğrudan yapılmış geçersiz API çağrıları `422` ile reddedilir.
- Skor alanı eksik veya sayıya çevrilemiyorsa kayıt aralık filtresinde eşleşmez ve skor sıralamasında sona gider.
- Duyurular ve çöp görünümü mevcut davranışını korur.

## Test stratejisi

Backend entegrasyon testi minimum/maksimum filtrelerini, iki skor sıralama yönünü, skorsuz kayıt davranışını ve geçersiz aralığın `422` sonucunu kapsar. Frontend testleri sorgu parametrelerini, bölüm geçişinde skor filtresinin temizlenmesini, hazır bantları ve sıralama seçeneklerini doğrular. Ardından tüm backend/frontend testleri, build, lint ve endpoint kapsam kontrolü çalıştırılır.

