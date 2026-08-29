# Proje GitHub merkezini iyileştirme tasarımı

**Tarih:** 29 Ağustos 2026  
**Durum:** Onaylandı

## Amaç

Projeye bağlı GitHub deposunu ayrı ve zayıf bir sekmeli kutu olmaktan çıkarıp,
projenin güncel geliştirme durumunu tek bakışta anlatan ve doğrudan eyleme
dönüştüren dengeli bir çalışma merkezine çevirmek.

Başarı ölçütleri:

- Issue olmayan ama commit bulunan bir depo açıldığında panel boş görünmez.
- Issue, pull request ve commit hareketleri tek kronolojik akışta okunabilir.
- Kullanıcı verinin GitHub'dan ne zaman alındığını ve manuel yenilemenin gerçekten
  çalışıp çalışmadığını anlayabilir.
- Bir issue'nun forkOS görevine dönüşmüş olup olmadığı yeniden yüklemeden sonra da
  anlaşılır.
- Private depo izin, token ve rate-limit hataları eyleme dönük biçimde ayrışır.
- Tasarım forkOS'un mevcut token, tipografi, yoğunluk ve bileşen dilini korur.

## Tasarım yönü

Bu alan mini bir GitHub istemcisi olmayacak. Repo metadatası yalnızca proje
bağlamını güçlendirecek kadar gösterilecek; ana vurgu son hareketler ve
"issue'dan görev üret" akışı olacak.

Görsel dil sakin, yoğun ve araç odaklıdır:

- Mevcut `Section`, semantik renk tokenları, tipografi ölçeği ve kontrol
  yarıçapları kullanılır.
- Yeni renk paleti, gradient, ağır gölge veya yeni tasarım sistemi eklenmez.
- GitHub kimliği ikon ve semantik `feed-gh` tonu ile desteklenir; sayfanın genel
  vurgu rengiyle yarışmaz.
- Masaüstü ve mobilde aynı bilgi sırası korunur; eylemler hover arkasına saklanmaz.

## Bilgi mimarisi

### 1. Repo başlığı

Panel başlığında şu bilgiler tek satırlık, responsive bir kimlik alanı oluşturur:

- `owner/repo` bağlantısı,
- private/public durumu,
- varsayılan dal,
- GitHub'da aç bağlantısı,
- son başarılı GitHub veri alma zamanı,
- manuel yenileme eylemi.

Yenileme sırasında düğme metni ve ikonu bekleme durumunu açıkça gösterir. Yalnızca
ikonla ifade edilen belirsiz bir kontrol kullanılmaz.

### 2. Özet şeridi

Başlığın altında tek çerçeveli kompakt özet şeridi bulunur:

- açık issue sayısı,
- açık pull request sayısı,
- son push zamanı,
- ana dil.

Private kişisel projede düşük bilgi değeri taşıyan yıldız, fork ve watcher
sayıları ana metriklerden çıkarılır. Gerekirse repo bağlantısında GitHub üzerinden
görülebilirler; forkOS panelinde çalışma bağlamına öncelik verilir.

### 3. Birleşik aktivite akışı

Issue, pull request ve commitler ortak bir sunum modeline dönüştürülür ve hareket
tarihine göre azalan sırada listelenir:

- commit için `committed_at`,
- issue ve pull request için `updated_at`, yoksa `created_at`.

Filtreler `Tümü`, `Issue`, `PR` ve `Commit` olarak sunulur. Her filtre yanında
sayısını gösterir. Varsayılan `Tümü` filtresidir; böylece tek bir veri türünün boş
olması paneli boş bırakmaz. Filtre seçimi yalnızca bileşen ömrü boyunca tutulur;
kalıcı ayar veya `localStorage` eklenmez.

Satırlar ortak ritmi paylaşır fakat türleri ikon, erişilebilir metin ve semantik
renkle ayırt edilir. Başlık dış bağlantıdır; ikincil satırda numara/SHA, yazar,
etiket veya yorum sayısı ile göreli zaman bulunur.

## Issue'dan göreve dönüşüm

Issue satırındaki eylem masaüstünde ve mobilde her zaman erişilebilir olacaktır.

- Dönüşmemiş issue: `Göreve dönüştür`.
- İstek sürerken: yalnızca ilgili satır bekler; diğer satırlar kullanılabilir kalır.
- Dönüşmüş issue: `Görevlerde` durumu ve varsa görev bağlantısı.
- Yinelenen istek: yeni görev açmaz; mevcut görev durumu gösterilir.

Kalıcı durum frontend tahminine bırakılmaz. Backend, projenin mevcut
`owner/repo#number` eşleşme kuralını kullanarak her issue için nullable `todo_id`
döndürür. Yeni eşleştirme tablosu veya migration eklenmez.

Başarılı dönüşümden sonra `invalidateAfter("project.write")` kullanılır. Böylece
GitHub paneli, proje görevleri, journal, Today ve global görev yüzeyleri merkezi
invalidation sözleşmesiyle birlikte tazelenir.

## Veri akışı ve önbellek

İlk panel isteği mevcut beş dakikalık backend önbelleğini kullanır. Backend yanıtı
GitHub verisinin gerçekten alındığı UTC zamanı `fetched_at` alanıyla döndürür.
Önbellekten dönen yanıtta bu zaman değişmez.

Manuel yenileme `/projects/{project_id}/github?refresh=true` çağrısını kullanır ve
backend önbelleğini aşar. Başarılı yanıt yeni `fetched_at` değeriyle birlikte query
cache'e yerleşir.

Bu panelin canlı repo özeti ile üç saatte bir çalışan katkı/commit event senkronu
aynı şey değildir:

- panel isteği repo özeti, issue, PR ve son commitleri okur;
- worker senkronu `github.commit` eventlerini proje günlüğü ve değerlendirme
  yüzeyleri için kalıcılaştırır.

Bu çalışma worker mimarisini veya event şemasını değiştirmez. Arayüzdeki `Yenile`
ifadesi yalnız panel verisini güncellediğini açıkça belirtir; kalıcı event senkronu
izlenimi vermez.

## Backend değişiklikleri

Mevcut repo overview akışı korunur ve sınırlı biçimde genişletilir:

- Başarılı GitHub fetch sonucuna `fetched_at` eklenir ve cache girdisiyle birlikte
  saklanır.
- Proje router/service katmanı, dönen issue numaralarını mevcut entity başlıklarıyla
  toplu eşleştirir ve her issue'ya `todo_id` ekler.
- Eşleştirme tek sorguyla yapılır; issue başına sorgu üretilmez.
- `event`, `entity` ve `link` şemaları değişmez.
- GitHub tokenı yanıta, loglara veya frontend state dışındaki yeni bir alana
  taşınmaz.

## Durumlar ve hata deneyimi

### Yükleniyor

Panelin gerçek yapısını temsil eden kısa skeleton/yer tutucu satırlar gösterilir;
tek başına `Yükleniyor…` metni kullanılmaz.

### Boş

- Tüm akış boşsa deponun henüz GitHub hareketi olmadığı açıklanır.
- Belirli filtre boşsa diğer filtrelerdeki içerik kaybolmaz ve kullanıcı `Tümü`ne
  dönebilir.
- Repo bağlı değilse mevcut `owner/repo` yönlendirmesi korunur.

### Offline

React Query cache'indeki veri okunmaya devam eder. Manuel yenileme ve issue'dan
görev üretme kapatılır; panel bunun çevrimdışı durumdan kaynaklandığını açıklar.

### GitHub hataları

Backend'in GitHub hata ayrıntısı, frontend'de şu eylem odaklı sınıflara ayrılır:

- `401` veya bad credentials: tokenın yenilenmesi için Ayarlar'a yönlendirir.
- `403` rate-limit: limitin ne zaman/niçin oluştuğunu ve sonra yeniden denemeyi
  açıklar.
- `403` izin: token repo izinlerini kontrol etmeyi söyler.
- `404`: repo adını ve private repo erişimini kontrol etmeyi söyler.
- ağ/timeout: mevcut veriyi koruyup tekrar deneme sunar.

Hata oluştuğunda daha önce başarıyla alınmış veri varsa tüm panel kaldırılmaz;
bayat veri görünür kalır ve üstte non-blocking hata bandı gösterilir.

## Erişilebilirlik ve responsive davranış

- Filtreler `aria-pressed` ile seçili durumu bildirir.
- Yenileme düğmesinin erişilebilir adı ve metinsel durumu vardır.
- Satır eylemleri klavye odağında ve dokunmatik ekranda görünürdür.
- Yalnız renkle aktarılan tür veya durum bulunmaz.
- Dar ekranda özet şeridi iki sütuna kırılır; aktivite satırı başlık, metadata ve
  eylem sırasını korur.
- Dış bağlantılar `target="_blank"` ve `rel="noreferrer"` kullanır.

## Bileşen sınırları

`GithubPanel` veri sorgusu ve üst düzey durum koordinasyonunu taşır. Sunum ve saf
dönüşümler ayrı küçük birimlere ayrılır:

- repo kimliği ve senkron durumu,
- özet metrikleri,
- filtre çubuğu,
- ortak aktivite modeli ve sıralama yardımcıları,
- aktivite listesi/satırı,
- hata/boş/loading durumları.

Dosya bölme yalnız okunabilirlik gerçekten gerektiriyorsa yapılır; tek kullanımlık
soyutlamalar veya genel amaçlı yeni bir UI sistemi eklenmez.

## Test stratejisi

Frontend bileşen testleri şu davranışları kanıtlar:

- birleşik akışın tarih sıralaması,
- `Tümü` varsayılanı ve filtre sayıları,
- issue olmayan repoda commitlerin görünmesi,
- manuel yenilemenin `refresh=true` çağırması,
- yalnız seçilen issue satırının bekleme durumu,
- issue dönüşümünden sonra `Görevlerde` durumu,
- offline, loading, boş ve hata sınıfları,
- raw GitHub hata veya teknik alanların kullanıcıya sızmaması.

Backend testleri şunları kanıtlar:

- `fetched_at` cache hit sırasında sabit kalır ve forced refresh sırasında yenilenir,
- issue numaralarının mevcut todo kayıtlarıyla toplu ve doğru eşleşmesi,
- private repo isteklerinde tokenın kullanılması,
- tokenın hiçbir response alanında bulunmaması,
- mevcut issue-to-todo idempotency davranışının korunması.

Tam frontend test/build, endpoint coverage, backend pytest ve lint kontrolleri
bitmeden çalışma tamamlanmış sayılmaz.

## Kapsam dışı

- GitHub üzerinde issue/PR düzenlemek veya kapatmak,
- yorum yazmak, merge etmek veya branch yönetmek,
- webhook eklemek,
- bütün GitHub repolarını otomatik proje olarak içe aktarmak,
- worker senkron sıklığını değiştirmek,
- yeni credential depolama yöntemi veya OAuth akışı kurmak,
- yeni kalıcı tablo ya da migration eklemek.
