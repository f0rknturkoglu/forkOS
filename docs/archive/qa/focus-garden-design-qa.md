# Odak Modülü Tasarım QA

> Tarihsel QA: 11 Ekim 2026 öncesi Bahçe tasarımı. Bahçe V1 arayüzünden kaldırılmıştır; bu kayıt güncel ürün veya release doğrulaması değildir.

## Referans ve ortam

- Seçilen görsel yön: `Sessiz Bahçe`, seçenek 3.
- Görsel referans: `yerel ImageGen artefaktı `exec-589130da-9319-4e73-9912-7f2a36ed56cc.png` (repo dışı)`
- Referans boyutu: 1487 x 1058 px.
- Uygulama önizlemesi: Codex yerel tarayıcı sekmesi 5, `http://127.0.0.1:5173/#/pomodoro`.
- QA viewport'u: 1487 x 1058 CSS px, device pixel ratio 1.
- Mobil kontrol: 390 x 844 CSS px.
- Durum: `Odaklan` sekmesi, AMOLED açık, etkin sayaç yok. Kişisel veritabanına test verisi yazılmadı.

## Karşılaştırma

### Yerleşim

Referanstaki sol navigasyon, üst başlık, üç sekmeli sayfa yapısı, büyük haftalık bahçe, sağdaki haftalık trend ve son seanslar ile alttaki seans oluşturucu korundu. Genel hızlı işlem düğmesi sağ alta taşındı. Geniş görünümde yatay taşma yok; mobil görünümde sidebar gizleniyor ve içerik tek kolona düşüyor.

Sidebar rail ayrıca daraltılarak kontrol edildi: 56 px başlık alanında yalnız ortalanmış `f` logosu kaldı; genişletme eylemi çalışma alanı başlığına geçti ve logo ile çakışmadı.

### Tipografi ve renk

Uygulama Manrope Variable kullanıyor. Hiyerarşi; küçük büyük-harf bölüm etiketleri, güçlü süre göstergesi ve sade gövde metniyle referansa yakınlaştırıldı. AMOLED durumda canvas hesaplanan renk olarak `#000000`; vurgu ve tamamlanan seans sinyalleri semantik yeşil tokenlardan geliyor.

### Veri görselleştirme ve boş durum

Bahçe ile trend grafiği gerçek analitik endpoint'inden besleniyor. Referans dolu örnek veri gösterirken test anındaki canlı hafta boştu; bu nedenle uygulama bilinçli olarak nokta ve boş çubuklarla sıfır durumunu gösteriyor. Tamamlanan seanslar oluştuğunda Lucide bitki işaretleri veri yoğunluğuna göre büyüyor.

### Metin ve etkileşim

Başlıklar ve eylemler Türkçe. `Odaklan`, `İstatistikler`, `Ayarlar`, AMOLED anahtarı, hızlı işlem menüsü, iç içe odak başlatma paneli ve hızlı yakalama diyaloğu tarayıcıda doğrulandı. Konsolda hata veya uyarı yok.

## İterasyon geçmişi

1. İlk uygulama karşılaştırmasında ana başlatma eylemi ile sağ-alt hızlı işlem düğmesi referansa göre fazla açık kaldı.
2. Ana eylem `success` varyantıyla dolu yeşile, hızlı işlem düğmesi koyu yüzey tokenına geçirildi.
3. Son geniş ve mobil kontrollerde P0, P1 veya P2 görsel sorun kalmadı.

## Sonuç

Passed. Seçenek 3'ün yerleşim, AMOLED atmosferi, bilgi hiyerarşisi ve ana etkileşim modeli uygulanmış durumda.
