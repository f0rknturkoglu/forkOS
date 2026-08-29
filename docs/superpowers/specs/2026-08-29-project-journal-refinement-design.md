# Proje Günlüğü Görsel Birleştirme Tasarımı

Tarih: 2026-08-29

## Sorun

Proje günlüğü günlük notunu hem üst editörde hem de seçili gün kartında tekrar gösteriyor. Notun teknik yaşam döngüsü olayları (`note.created`, `note.updated`, `note.deleted`) aynı yüzeye ikinci bir kayıt olarak ekleniyor. Etiket sözlüğünde bulunmayan event verb'leri ham teknik adlarıyla kullanıcıya sızıyor. Tarih seçicinin ayrı kolonda durması ve yüksek editör de not ile timeline'ı iki bağımsız bölüm gibi gösteriyor.

## Karar

- `note.*` event'leri append-only `event` tablosunda ve genel Aktivite yüzeyinde korunur; proje günlüğü cevabının hareket listesine eklenmez.
- Seçili gün tek bir çalışma yüzeyi olur: kompakt tarih seçici, düzenlenebilir günlük notu ve aynı günün hareketleri aynı kart içinde görünür.
- Seçili gün alt geçmiş listesinde tekrar render edilmez.
- Geçmiş günler not önizlemesi ve hareketleri aynı kartta gösterir; güne basınca o gün seçili çalışma yüzeyine taşınır.
- `entity_type` chip'leri proje günlüğünden kaldırılır. Olay noktası, insan dili etiketi, kayıt başlığı ve zaman bilgisi yeterlidir.
- Bilinmeyen event verb'leri ham olarak gösterilmez; görünür fallback `Proje hareketi` olur. Teknik verb yalnız geliştirme verisinde kalır.
- Editör mevcut tasarım tokenlarıyla daha kompakt olur; yeni renk, radius, kütüphane veya ham form kontrolü eklenmez.

## Veri Akışı

- Backend `journal()` proje ve bağlı görev olaylarını mevcut `timeline()` servisinden alır.
- Günlük notları `note` tablosundan gün bazında cevapta taşınır.
- Note event sorgusu proje günlüğü birleştirmesinden kaldırılır; event yazımı değişmez.
- Frontend seçili günün grubunu `activeGroup` olarak ayırır. Seçili gün mevcut değilse boş not ve boş hareketlerle sanal bir çalışma yüzeyi gösterir.
- Geçmiş liste `group.day !== selectedDay` filtresiyle seçili günü dışarıda bırakır.

## Durumlar

- Yükleniyor ve hata durumları mevcut `Section`/`Empty` sözleşmesini kullanır.
- Seçili günde hareket yoksa editörün altında kompakt `Bugün henüz hareket yok.` metni görünür.
- Not kaydı başarısızsa taslak korunur ve mevcut toast gösterilir.
- Offline durumda not editörü kapalı, geçmiş okunabilir kalır.

## Testler

- Backend journal cevabı notu taşır fakat hiçbir `note.*` event'i taşımaz; aynı event genel aktivitede bulunmaya devam eder.
- Frontend ham `note.created` veya bilinmeyen verb göstermez.
- Seçili not yalnız editörde bir kez görünür; alt geçmiş kartında tekrarlanmaz.
- Seçili gün hareketleri editörle aynı aktif yüzeyde görünür.
- Geçmiş güne basmak editörü ve aktif hareketleri o güne taşır.
- Mevcut kaydetme, boş not silme, gelecek gün kısıtı ve invalidation testleri korunur.
