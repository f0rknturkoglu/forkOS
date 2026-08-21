# Fırsat Çöp Kutusu, Kaynak Senkronizasyonu ve Timeline Tasarımı

## Amaç

Fırsatlar modülünü yüksek hacimli kaynakları yönetmeye uygun hale getirmek:

- ilgisiz fırsatları geri alınabilir biçimde çöpe atmak ve gerektiğinde kalıcı silmek,
- manuel kaynak çekimlerinin gerçek durumunu iki katmanlı arayüzde izlemek,
- YLSY ve ÖSYM duyurularını üst seviye sekmelerde görünür kılmak,
- fırsat detayını gereksinimlere odaklamak,
- Etkinlik sayfasındaki olay listesini görsel olarak gerçek bir timeline'a dönüştürmek.

Her şey local-only kalır. Yeni harici servis veya veri aktarımı eklenmez.

## Kapsam

### Dahil

- Fırsatlarda soft-delete, geri yükleme ve onaylı kalıcı silme
- Aktif kaynak çekimi için kalıcı batch takibi
- Fırsatlar ekranında kompakt ilerleme şeridi
- Kaynaklar ekranında ayrıntılı aktif durum ve batch geçmişi
- İş İlanları, YLSY, ÖSYM, Diğer Duyurular ve Çöp üst sekmeleri
- İş ilanı detayından Başvuru adımları bölümünün kaldırılması
- Gereksinimler bölümünün korunması
- Etkinlik timeline omurgası ve düğümlerinin düzeltilmesi
- Backend, frontend ve migration testleri

### Hariç

- Tek bir HTTP isteğinin byte veya HTML ayrıştırma yüzdesi
- Çok kullanıcılı senkronizasyon
- Harici queue veya websocket altyapısı
- Event kayıtlarının silinmesi
- Başvuru adımı backend API'lerinin bu aşamada kaldırılması

## Fırsat Çöp Kutusu

### Veri modeli

`opportunity` tablosuna şu alanlar eklenir:

- `trashed_at timestamptz null`
- `trashed_from_status text null`

Çöpe atma sırasında mevcut durum `trashed_from_status` alanına yazılır,
`trashed_at` doldurulur ve durum `trashed` olur. Geri yükleme, kayıtlı önceki
duruma döner; önceki durum yoksa `discovered` kullanılır. Ardından iki çöp alanı
temizlenir.

Liste endpoint'i varsayılan olarak çöpteki kayıtları döndürmez. Çöp sekmesi açık
bir sorgu parametresiyle yalnızca çöpteki kayıtları ister.

Durum alanını genel PATCH ile doğrudan `trashed` yapmak yerine yaşam döngüsü
alanlarını birlikte yöneten ayrı endpoint'ler kullanılır:

- `POST /opportunities/{id}/trash`
- `POST /opportunities/{id}/restore`
- `DELETE /opportunities/{id}`

Bu ayrım `trashed_at` ile `trashed_from_status` alanlarının yarım veya çelişkili
kalmasını önler.

### Davranış

- Normal fırsat kartında hızlı çöp eylemi bulunur ve kısa onay ister.
- Çöp sekmesinde `Geri yükle` ve `Kalıcı sil` eylemleri bulunur.
- Kalıcı silme ikinci bir onayda fırsat başlığını gösterir.
- Kalıcı silme öncesinde `opportunity.deleted` olayı append-only `event`
  tablosuna yazılır; ardından fırsatın bağlı `entity` kaydı entity helper'ı
  üzerinden silinir ve cascade ile fırsat/requirement/link kayıtları kaldırılır.
- `event` satırı silinmez; entity FK davranışı nedeniyle geçmiş olayı korunur.
- Kaynak taraması aynı `source + external_id` kaydını yeniden gördüğünde çöpteki
  kaydı güncelleyebilir fakat geri yüklemez. Böylece reddedilmiş fırsat yeniden
  normal listeye çıkmaz.

## Kaynak Senkronizasyon Batch'i

### Yaklaşım

Manuel toplu çekimler kalıcı bir batch ile temsil edilir. Bu, mevcut
`source_run` satırlarından tahmin edilen ve otomatik turlarla karışan bir yüzde
yerine kesin bir payda sağlar.

`source_sync_batch` aranabilir veya linklenebilir kullanıcı nesnesi değildir;
`source_run` gibi operasyonel bir destek tablosudur. Bu nedenle `entity.id`
kuralının belgelenmiş istisnasıdır. Kullanıcıya ait fırsat ve duyuru kayıtları
entity-backed kalır.

Önerilen alanlar:

- `id uuid primary key`
- `status text`: `queued`, `running`, `completed`, `completed_with_errors`
- `source_ids jsonb`: tekilleştirilmiş kaynak kimlikleri
- `total_sources integer`
- `completed_sources integer`
- `ok_sources integer`
- `empty_sources integer`
- `error_sources integer`
- `items_found integer`
- `created_at`, `started_at`, `finished_at`

`source_run` tablosuna nullable `batch_id` FK eklenir. Otomatik periyodik
koşuların `batch_id` alanı boş kalır.

### İlerleme semantiği

Yüzde kaynak bazlıdır:

`floor(completed_sources / total_sources * 100)`

Aktif kaynaklar tamamlanan sayısına dahil değildir. Her kaynak bittiğinde batch
sayaçları aynı transaction içinde güncellenir. Arayüz şunları gösterebilir:

- `%25`
- `20 / 80 kaynak`
- çalışan kaynaklar
- başarılı, boş ve hatalı sayıları
- bulunan yeni fırsat toplamı

### Eşzamanlı istekler

Yeni manuel çekim geldiğinde aktif batch varsa seçilen yeni kaynaklar aynı
batch'e eklenir. Batch'te zaten bulunan veya halen çalışan kaynaklar ikinci kez
kuyruklanmaz. Yeni kaynak eklenirse `source_ids` ve `total_sources` atomik olarak
genişletilir.

API yeniden başlarsa dashboard kalıcı batch ve run kayıtlarından mevcut durumu
göstermeye devam eder. Süreç yeniden başlatıldığı için yarım kalan `running`
satırlar başlangıçta hata/yarım kaldı olarak sonlandırılır; kullanıcı bunları
yeniden çekebilir.

### API

- `POST /sources/refresh`: batch kimliği, kuyruğa yeni eklenen kaynak sayısı ve
  toplam batch kaynak sayısını döndürür.
- `GET /sources/sync`: aktif batch özeti, kaynak bazlı durum ve hesaplanmış yüzde
  döndürür.
- `GET /sources/sync/history`: son batch özetlerini döndürür.

Mevcut `GET /sources/runs` kaynak bazlı teşhis için korunur.

## Arayüz

### Fırsatlar

Üst sekmeler:

1. İş İlanları: `kind=job`
2. YLSY: `source=ylsy`
3. ÖSYM: `source=osym`
4. Diğer Duyurular: iş dışı ve YLSY/ÖSYM dışındaki kayıtlar
5. Çöp: `status=trashed`

Sekmeler sayaç gösterir. Tür ve durum filtreleri seçili üst sekmenin altında
çalışır. Çöp dışındaki tüm sekmeler çöpteki kayıtları hariç tutar.

Aktif bir manuel batch varken sayfanın üstünde kompakt ilerleme şeridi görünür.
Şerit yüzdeyi, tamamlanan/toplam kaynak sayısını, çalışan kaynak sayısını,
bulunan kayıtları ve hataları gösterir. Hata sayısı Kaynaklar dashboard'una
bağlanır. Batch bittiğinde kısa sonuç özeti gösterilir ve sonra pasifleşir.

### Kaynaklar dashboard'u

Mevcut Kaynaklar sayfası ayrıntılı dashboard olarak genişletilir:

- aktif batch için büyük ilerleme kartı,
- çalışan/tamamlanan/hatalı kaynak listesi,
- başarılı, boş, hatalı ve bulunan kayıt sayaçları,
- son batch'lerin zaman, süre ve sonuç geçmişi,
- mevcut kaynak sağlık tablosu ve tekli/çoklu çekim kontrolleri.

YLSY veya ÖSYM boş ya da hatalı dönse bile ilgili üst sekme kaybolmaz. Boş
durum, son çalışma zamanı ve son hata ilgili sekmede kullanıcıya gösterilir.

### Fırsat detayı

İş ilanı detayındaki Başvuru adımları sorgusu, formu ve listesi arayüzden
kaldırılır. Gereksinimler, belge eşleme, skor, künye, durum ve ilan bağlantısı
korunur. Backend todo endpoint'leri geriye dönük uyumluluk için şimdilik kalır.

### Etkinlik timeline

Her gün grubu gerçek bir dikey timeline olarak çizilir:

- omurga etkinlik düğümlerinin merkezinden geçer,
- düğümler omurgayı örtecek yüzey halkasına ve durum rengine sahip olur,
- ilk olayın üstünde ve son olayın altında taşan çizgi olmaz,
- olaylar arası çizgi kesintisizdir,
- gün başlığı omurgayı yanlış hizalamaz,
- uyarı düğümleri renk ile ayrışırken metin okunabilir kalır.

## Hata Davranışı

- Kaynak hatası batch'i tamamen durdurmaz; diğer kaynaklar devam eder.
- En az bir hata varsa sonuç `completed_with_errors` olur.
- API çevrimdışıysa yeni çekim ve çöp yazmaları kapalıdır; mevcut veriler salt
  okunur kalır.
- Çöpe atma, geri yükleme ve silme mutasyonları başarısız olursa liste optimistik
  olarak kalıcı değişmez; hata toast'ı gösterilir.
- Kalıcı silmede bulunamayan kayıt 404 döndürür.
- Batch'e sonradan eklenen kaynaklar ilerleme paydasını artırır; yüzde geçici
  olarak düşebilir ve bu doğru davranıştır.

## Event'ler

Anlamlı eylemler şu event'leri yazar:

- `opportunity.trashed`
- `opportunity.restored`
- `opportunity.deleted`
- `source_sync.started`
- `source_sync.sources_added`
- `source_sync.completed`

Senkron batch'i entity-backed olmadığı için batch event'lerinde `entity_id`
boş, `entity_type` değeri `source_sync` ve batch kimliği payload içinde olur.

## Test Stratejisi

Backend testleri:

- çöpe atma normal listeden çıkarır,
- çöp sorgusu yalnızca çöpteki kayıtları döndürür,
- geri yükleme önceki durumu korur,
- yeniden ingest çöpteki kaydı görünür yapmaz,
- kalıcı silme entity cascade ve event geçmişini doğru bırakır,
- batch yüzdesi ve sayaçları kaynak sonuçlarıyla ilerler,
- aktif batch'e yeni kaynak ekleme tekilleştirilir,
- hata diğer kaynakları durdurmaz ve batch sonucuna yansır,
- YLSY/ÖSYM kaynakları doğru sınıfa girer,
- migration'larda her SQL komutu ayrı `op.execute()` çağrısıdır.

Frontend doğrulaması:

- üst sekme filtreleri ve sayaçları,
- çöp/geri yükle/kalıcı sil onay akışı,
- kompakt ilerleme şeridi ve dashboard durumları,
- detayda Başvuru adımları bölümünün bulunmaması,
- timeline ilk/orta/son öğe çizgi hizası,
- TypeScript ve production build.

## Başarı Ölçütleri

- Kullanıcı ilgisiz fırsatı normal akıştan çıkarabilir, geri alabilir veya açık
  onayla kalıcı silebilir.
- Manuel çekimin tamamlanma yüzdesi seçilen kesin kaynak toplamına dayanır.
- Aynı senkron durumu hem Fırsatlar ekranında özet hem Kaynaklar ekranında
  ayrıntı olarak görünür.
- YLSY ve ÖSYM tek tıklamayla ayrı listelenir ve kaynak sorunları görünürdür.
- İş ilanı detayı Başvuru adımları olmadan gereksinimlere odaklanır.
- Etkinlik listesi kesintisiz ve doğru uçlara sahip bir timeline olarak görünür.
