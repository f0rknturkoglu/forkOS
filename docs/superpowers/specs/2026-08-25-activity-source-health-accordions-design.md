# Etkinlik ve Kaynak Sağlığı Akordeonları

## Amaç

Sistem ve Ayarlar sayfalarındaki uzun kayıt listelerini, önemli özetleri görünür
tutup ayrıntıları istek üzerine açılan minimalist bölümlere dönüştürmek. Etkinlik
sayfasındaki emek haritası kaldırılacak; backend uçları ve veri modelleri
değişmeyecek.

## Kapsam

- `Etkinlik` sayfasından `Heatmap` kaldırılır.
- Sorunlu kaynak özeti, varsayılan kapalı bir kaynak sağlığı akordeonuna dönüşür.
- Etkinlik timeline'ı gün bazında açılıp kapanabilir olur.
- En yeni timeline günü başlangıçta açık, eski günler kapalıdır.
- Timeline için tek bir bağlamsal `Tümünü genişlet` / `Tümünü daralt` kontrolü
  bulunur.
- Ayarlar sayfasındaki kaynak sağlığı tablosu aynı ortak akordeon sunumunu
  kullanır ve başlangıçta kapalıdır.
- Kaynak sağlığı başlığı toplam, sağlıklı ve sorunlu kayıt sayılarını görünür
  tutar.

Kapsam dışında:

- Activity/health API değişiklikleri.
- Emek haritası backend endpoint'inin veya günlük detay sayfasının kaldırılması.
- Kalıcı açık/kapalı tercihleri; durum yalnızca mevcut sayfa oturumunda tutulur.
- Akordeon animasyonları ve iç içe kaynak bazlı akordeonlar.

## Bileşen Tasarımı

### Ortak kaynak sağlığı akordeonu

`SourceHealthAccordion`, hem Etkinlik hem Ayarlar tarafından kullanılır. Başlık
satırı bölüm adı, kayıt sayısı ve sorun rozeti taşır. İçerik kapalıyken yalnızca
bu özet görünür. Açıldığında kaynak koşumları kompakt satırlar halinde listelenir:
kaynak adı, durum, bulunan kayıt sayısı, göreli zaman ve varsa hata özeti.

Bileşen kontrollü bir `open` değeri ve `onOpenChange` callback'i alır. Böylece iki
sayfa aynı görsel/erişilebilir davranışı paylaşırken başlangıç durumunu kendisi
belirler. Uygulama doğal `<details>/<summary>` semantiğini kullanır; klavye ve
ekran okuyucu davranışı ek JavaScript erişilebilirlik katmanı gerektirmez.

Etkinlik sayfası yalnızca sorunlu kaynakları geçirir. Ayarlar sayfası mevcut
sağlık sorgusunun tüm sonuçlarını geçirir.

### Timeline gün akordeonu

Her gün, başlığında gün adı, hareket sayısı ve uyarı sayısı bulunan kontrollü bir
`<details>` bölümüdür. İçerik mevcut timeline çizgisini ve olay satırlarını aynen
korur. İlk render'da ilk gün açık, diğer günler kapalıdır.

Üst araç çubuğundaki toplu kontrol:

- Her görünür gün açıksa `Tümünü daralt` gösterir.
- Aksi halde `Tümünü genişlet` gösterir.
- `Sadece uyarılar` filtresi değiştiğinde artık görünmeyen gün anahtarları açık
  durumdan temizlenir; yeni ilk görünür gün, açık gün kalmadıysa açılır.

## Veri Akışı ve Durum

Mevcut React Query sorguları korunur. Açık bölüm anahtarları yalnızca yerel React
state'inde tutulur. Akordeon açmak/kapatmak ağ isteği üretmez; sorgu sonuçları
sayfa açıldığında mevcut davranışla yüklenir.

Kaynak listesi boşsa akordeon yerine mevcut boş durum gösterilir. Yükleme ve API
hata davranışları bu çalışmada genişletilmez.

## Görsel Davranış

- Başlıklar mevcut `Section`, `Badge`, renk tokenları ve tipografi ölçeğiyle
  uyumlu kalır.
- Chevron açık/kapalı durumu belirtir; renk tek başına durum taşımaz.
- İçerik kapalıyken dikey boşluk minimumdur.
- Ayrı `Tümünü genişlet` ve `Tümünü daralt` düğmeleri yerine tek bağlamsal düğme
  kullanılır.

## Test Stratejisi

Test-first akışta önce aşağıdaki davranışlar başarısız testlerle sabitlenir:

1. Etkinlik sayfası emek haritasını render etmez.
2. Kaynak sağlığı başlangıçta kapalıdır ve açıldığında kayıtları gösterir.
3. Timeline yalnızca en yeni günü açık başlatır.
4. Toplu kontrol tüm günleri açar ve tekrar basıldığında kapatır.
5. Ayarlar sayfası aynı kaynak sağlığı akordeonunu kapalı başlatır.

Odak testlerden sonra tüm frontend Vitest paketi ve production build çalıştırılır.
