# Media Task 7 — Cinematic Page Report

## Sonuç

`/media` sayfası Tasks 2–6 bileşenlerinden oluşan cinematic kütüphane sayfasına çevrildi. Sayfa sırası `PageHeader`, `MediaMetrics`, `MediaSearchComposer`, `MediaLibraryControls`, `MediaPosterGrid`, `MediaSyncSummary` oldu. Tür/durum filtreleri yalnızca local React state'te tutuluyor ve `/media?kind=...&status=...` isteğine yansıyor.

## RED / GREEN

- RED: cinematic/focus/composer koşusunda 22 testten 8'i beklenen nedenlerle kırıldı: 5 cinematic sözleşme, 1 eski inline focus davranışı, 1 güvensiz title-focus fallback ve 1 stale non-409 hata.
- GREEN (odaklı): 23/23 test geçti.
- Medya bileşen paketi: 50 geçti, 9 Task 5 legacy testi bilinçli olarak skipped kaldı.
- Tam frontend: 139 geçti, 9 skipped.
- `npm run build`: başarılı; TypeScript, Vite ve bundle bütçe kontrolü geçti.

## Kaldırılan legacy davranışlar

- Sayfa içi `MediaEditor` ve inline PATCH düzenleme.
- Küçük `RowList` kütüphane görünümü.
- Provider türü seçilerek yapılan eski arama ve settings sorgusu.
- Sayfaya gömülü `Cover`, tür/durum sabitleri, external-link üretimi ve quick-site satırı.
- Kartların yanında sürekli görünen harici linkler; bunlar tür-aware poster action menüsünde kaldı.
- `?focus=` değerini inline detay isteğiyle açma. Entity focus artık güvenli biçimde `#/media/:encoded-id` rotasına gider.
- ID içermeyen duplicate cevabında title'ı ID gibi kullanan `?focus=<title>` fallback; artık güvenli `#/media` fallback kullanılıyor.

## Entegrasyon gövdeleri ve invalidation

- Ana sayfa hızlı aksiyonu append-only `POST /media/{encoded-id}/consumptions` çağırır.
- Gövde `consumptionBody("quick", item)` ile üretilir: `{ action: "quick", amount: 1, client_uuid: <fresh UUID>, measure: <progress_measure> }`.
- Her başarılı hızlı tüketim, ekleme ve recoverable trash aksiyonu aynı altı aileyi invalid eder: `media`, `media-detail`, `media-stats`, `media-dashboard`, `today-agenda`, `activity`.
- Trash kalıcı silme kullanmaz; onaydan sonra mevcut `DELETE /media/{id}` recoverable akışını çağırır.
- Offline durumda composer eklemeleri, poster quick/trash aksiyonları ve sync yazmaları disabled kalır; mevcut query verileri okunur.
- Kütüphane ve stats yükleme/hata durumları görünür; iki hata da bağımsız retry sunar.

## Dosyalar

- `frontend/src/modules/media/MediaPage.tsx`
- `frontend/src/modules/media/MediaCinematicPage.test.tsx`
- `frontend/src/modules/media/MediaPageFocus.test.tsx`
- `frontend/src/modules/media/MediaPosterGrid.tsx` — quick callback'e `progress_measure` taşıyan küçük tip entegrasyonu
- `frontend/src/modules/media/MediaSearchComposer.tsx`
- `frontend/src/modules/media/MediaSearchComposer.test.tsx`
- `frontend/src/modules/media/integrationKeys.test.ts`

## Ek temizlik ve açık konular

- Composer non-409 add hataları başlatıldıkları term'e scope edildi; eski istek yeni aramanın altında hata göstermez.
- Composer testindeki `console.error` spy açık bırakılmıyor.
- `receiveMediaFocus` export'u compatibility için korunuyor ve mounted/missing row davranışı testli.
- Bilinen açık ürün sorunu yok. Task 5'in geniş responsive kontratı önceki karara uygun biçimde skipped bırakıldı.
- `.superpowers/sdd/task-3-report.md` ve `task-4-report.md` kullanıcı değişiklikleri korunup bu görevin staging/commit kapsamına alınmadı.
