# Fırsatlar Kategorik Çalışma Alanı Tasarımı

## Amaç

Fırsatlar ekranını iki farklı kullanım niyetine göre düzenlemek:

1. İş ilanlarını uygunluk, iş ailesi, konum ve başvuru akışıyla yönetmek.
2. YLSY, ÖSYM ve diğer kurumsal duyuruları gerçek yayın tarihleriyle takip etmek.

Ekran, mobil ve masaüstünde liste/kart görünümünü gerçekten değiştirmeli; binlerce
kaydı tek istekte indirmemeli; kaynak hataları aktif ve eyleme dönük durumu
yansıtmalıdır.

## Mevcut Durum ve Doğrulanan Sorunlar

- Kart görünümü yalnızca kartın iç yerleşimini değiştiriyor. Taşıyıcı `RowList`
  tek sütun kaldığı için responsive grid oluşmuyor.
- İş ilanı ve duyuru ekranları aynı skor, remote, bölge ve CRM filtrelerini
  kullanıyor. Bu filtrelerin çoğu YLSY/ÖSYM için anlamsız.
- ÖSYM duyuru tarihi başlıkta bulunmasına rağmen `published_at` olarak
  ayrıştırılmıyor. Kayıtlar ilk tarama zamanına göre yanlış sıralanıyor.
- `found_at` hem yayın hem keşif zamanı gibi kullanılıyor; arayüz hepsini
  "tarandı" olarak etiketliyor.
- `/opportunities?limit=2000` çağrısı gerçekte 8.916 kayıt ve yaklaşık 6,3 MB
  veri döndürüyor. Backend `limit`, `status` ve `kind` parametrelerini
  uygulamıyor.
- Kaynak senkronunda `cluster_key` sorgusu tek satır varsayıyor. Veritabanında
  208 yinelenen küme bulunduğu için 36 aktif fırsat kaynağının çoğu
  `Multiple rows were found` hatasıyla duruyor.
- Kaynak sağlığı 148 silinmiş RSS beslemesinin yetim `source_run` geçmişini
  aktif hata olarak sayıyor.
- `yok-msc`, `jobhunter:bulldogjob`, `jobhunter:consider-sequoia` ve
  `jobhunter:consider-a16z` adapter uçları güncelliğini kaybetmiş durumda.

## Bilgi Mimarisi

Birincil çalışma alanları:

- **İş ilanları**
- **Duyurular**
- **Çöp**

Duyuruların ikincil ayrımı:

- **YLSY**: `source == "ylsy"`
- **ÖSYM**: `source == "osym"`
- **Diğer**: iş olmayan ve yukarıdaki iki kaynağa girmeyen kayıtlar

Bu iki seviyeli yapı, beş eş düzey sekmenin yarattığı kategori karmaşasını
ortadan kaldırır. Çöp bir içerik kategorisi değil, yardımcı yaşam döngüsü
alanı olarak sağ tarafta daha düşük vurgu ile sunulur.

## İş İlanı Kategorileri

İş ilanları merkezi ve deterministik bir sınıflandırıcıyla şu iş ailelerine
ayrılır:

- `software`: Yazılım ve mühendislik
- `data-ai`: Veri ve yapay zekâ
- `product-design`: Ürün ve tasarım
- `cloud-security`: Bulut, DevOps ve güvenlik
- `business-ops`: İş, finans ve operasyon
- `sales-marketing`: Satış ve pazarlama
- `other`: Diğer

Sınıflandırıcı normalize edilmiş ilan başlığı, departman ve sınırlı kaynak
metadatasını kullanır. Aynı keyword grupları hem Python çıktı üretiminde hem
SQL filtre ifadesinde tek modülden beslenir. Kategori yeni bir entity tipi
değildir ve frontend route sabiti üretmez.

Sınıflandırma kullanıcı verisini değiştirmez. Kaynağın kategori bilgisi
yetersizse kayıt `other` altında kalır; yanlış bir kategori uydurulmaz.

## Tarih Semantiği

API, `found_at` yanında nullable `published_at` döndürür:

- `published_at`: Kaynağın açıkladığı yayın/duyuru zamanı.
- `found_at`: forkOS'un kaydı ilk gördüğü zaman.
- `deadline_at`: Yalnızca gerçek başvuru/işlem son tarihi.

ÖSYM adapteri başlığın başındaki Türkçe tarihi ayrıştırıp gelecek kayıtların
`published_at` alanını doldurur. Mevcut ÖSYM kayıtları için servis aynı
ayrıştırıcıyla geriye dönük fallback uygular. YLSY API'sindeki `ISLEMSAAT`
yayın tarihi olarak korunur. Bilinmeyen son tarihler tahmin edilmez.

İş ilanında yayın tarihi varsa "yayınlandı", yoksa keşif zamanı "tarandı"
olarak gösterilir. Duyurularda varsayılan sıralama en yeni `published_at`,
fallback olarak `found_at` olur. Aynı güne ait duyurular başlıkla kararlı
biçimde sıralanır.

## Filtre ve Sıralama Davranışı

### İş ilanları

- Arama: başlık, şirket, konum ve kaynak.
- İş ailesi kategorisi.
- Kaynak.
- Türkiye, Avrupa, diğer bölge.
- Uzaktan, hibrit, ofis.
- Başvuru durumu.
- Sıralama: en uygun, en yeni yayın, yaklaşan gerçek son tarih.
- Elenen ilanları gizleme.

### Duyurular

- Arama: başlık ve kurum.
- Alt kaynak: YLSY, ÖSYM, diğer.
- Dönem: son 30 gün, son 3 ay, son 1 yıl, tümü.
- Yıl filtresi.
- Takip durumu.
- Sıralama: en yeni, en eski, yaklaşan gerçek son tarih.

İş ilanına özgü skor, bölge ve çalışma biçimi filtreleri duyurularda
render edilmez. Çalışma alanı değiştiğinde anlamsız filtreler sıfırlanır;
arama ve görünüm tercihi korunur.

## Backend Tarama Sözleşmesi

Fırsatlar sayfası için `GET /api/opportunities/browse` eklenir. Sözleşme:

- Girdi: çalışma alanı, duyuru kaynağı, iş kategorisi, arama, status, kaynak,
  region, remote, dönem/yıl, sort, offset ve limit.
- Çıktı: `items`, `total`, kategori sayaçları ve geçerli filtre facet'leri.
- Varsayılan limit 60, üst sınır 120.

Filtreleme, sıralama ve sayfalama SQL'de yapılır. Kartlar artık tüm veri
kümesini istemciye çekmez. Mevcut `/opportunities` endpoint'i diğer modüller
için korunur ancak ilan edilmiş `status`, `kind` ve `limit` davranışları
gerçekten uygulanır; erişilemeyen dönüş satırı silinir.

Mutation sonrası `invalidateAfter("opportunity.write")` kullanılmaya devam
eder. Event tablosu append-only kalır ve yeni schema/entity istisnası eklenmez.

## Responsive Sunum

Liste görünümü her genişlikte tek sütundur. Kart görünümünün taşıyıcısı gerçek
CSS grid olur:

- Mobil: 1 sütun
- Orta ekran: 2 sütun
- Geniş ekran: 3 sütun

İş ilanı kartı skor, kategori, şirket, konum, yayın/keşif tarihi ve başvuru
durumunu gösterir. Duyuru kartı skor alanı kullanmaz; tarih bloğu, kurum,
duyuru türü ve varsa deadline ön plandadır. Eylemler dar ekranda taşmaz ve
dokunma hedefleri korunur.

Liste/kart tercihi localStorage'da saklanır. Mobil ekran kart görünümünde bile
tek sütuna düşer; içerik yatay scroll üretmez.

## Kaynak Hatası İyileştirmeleri

### Yinelenen cluster kayıtları

Ingest tek satır varsaymaz. Aynı `cluster_key` için deterministik canonical
kayıt seçilir. Aynı kaynaktan gelen yeni external ID de duplicate kabul edilir;
kaynak bilgisi canonical kayda birleştirilir. Mevcut duplicate'ler görünümde
tekilleştirilir. Kullanıcı durumu, notu veya linki bulunan kayıt otomatik
silinmez.

Mevcut veride doğrulanan 416 duplicate satırın tamamı `discovered`, notsuz,
başvurusuz ve linksizdir. Güvenli temizlik ayrı, testli bir bakım adımı olarak
çalıştırılır ve sonucu raporlanır; event geçmişi değiştirilmez.

### Yetim kaynak geçmişi

`/sources/health`, `rss:<uuid>` kayıtlarını yalnızca karşılık gelen aktif feed
entity'si hâlâ mevcutsa gösterir. Source run geçmişi silinmez; yalnızca aktif
sağlık özetinden çıkarılır. Böylece tarihsel veri korunurken global uyarı bandı
148 silinmiş beslemeyi hata saymaz.

### Değişen harici kaynaklar

- YÖK duyuru adresi resmi siteden yeniden doğrulanır; çalışan resmi uç varsa
  adapter güncellenir, yoksa kaynak catalog'dan devre dışı bırakılır.
- BulldogJob canlı payload'ı ve resmi/gerçek API yanıtı karşılaştırılır; yeni
  şekil desteklenir. Yanıt sözleşmesi yoksa kaynak açık hata mesajıyla opt-in
  duruma alınır.
- Consider Sequoia/a16z uçları doğrulanır. Kalıcı 404/gone kaynaklar catalog'dan
  çıkarılır; geçici 412 için uygun istek sözleşmesi bulunursa adapter güncellenir.
- Harici bir kaynağı başarılı göstermeye yönelik hata yutma yapılmaz.

## Durumlar ve Hata Sunumu

- İlk yükleme kart/listenin biçimini takip eden skeleton gösterir.
- Filtre sonucu boşsa aktif filtreleri temizleme eylemi sunulur.
- Browse isteği hata verirse ham backend metni yerine anlaşılır mesaj ve tekrar
  deneme eylemi gösterilir.
- Offline durumda son cache okunur; durum değiştirme, kaydetme ve senkron
  eylemleri devre dışıdır.
- Kaynak sağlık ekranı aktif, kaldırılmış ve geçici hataları birbirine karıştırmaz.

## Test Stratejisi

- Backend sınıflandırıcı: çok dilli örnek başlıklar ve kategori önceliği.
- Browse endpoint: kategori, arama, source, tarih dönemi, sort, limit/offset ve
  facet sayaçları.
- Türkçe ÖSYM tarih ayrıştırma ve mevcut kayıt fallback'i.
- Ingest duplicate cluster regresyonu: birden fazla mevcut satır hata üretmez,
  canonical kayıt seçilir ve yeni duplicate oluşmaz.
- Kaynak sağlığı: silinmiş RSS entity'sine ait geçmiş koşu global hataya sızmaz.
- Frontend: iş/duyuru bağlamsal filtreleri, kategori değişiminde reset,
  duyuru tarih sıralaması ve liste/grid erişilebilir durumları.
- Responsive class sözleşmesi: grid taşıyıcısında 1/2/3 sütun breakpoint'leri;
  liste taşıyıcısında tek sütun.
- Tüm mevcut fırsat lifecycle, CRM, DocumentsPage ve source sync testleri
  regresyon paketi olarak çalıştırılır.

## Kapsam Dışı

- Tahmine dayalı YLSY/ÖSYM son tarihi üretmek.
- Harici LLM ile ilan sınıflandırmak.
- Yeni bir kullanıcı/tenant modeli.
- Event geçmişini güncellemek veya silmek.
- Çalışmayan harici kaynağı başarı gibi raporlamak.

