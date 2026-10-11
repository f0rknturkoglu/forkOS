# V1 başlangıç ve rehberler

## Kullanıcı akışı

Backend gerçekten boşsa ilk açılışta karşılama görünür. Kullanıcı hedef, günlük plan, öğrenme veya kariyer yolunu seçer; etkin olmayan modüller sunulmaz. Mevcut kuruluma, yeni tarayıcıya, offline duruma ve başarısız tercih isteğine otomatik karşılama uygulanmaz.

Kaynak seçimi isteğe bağlıdır. Kullanıcı geri dönebilir, geçebilir, kapatabilir ve devam edebilir. Karşılama ve tur; sahte görev, başvuru, konu veya hedef oluşturmaz. İlk adımlar kontrolü backend'deki gerçek kayıtları, ziyaret edilen adımı ve kaynakların seçilmesini/özellikle geçilmesini kullanır. Teknik kurulum checklist'i ayrı kalır.

Her ortak sayfa header'ında `(i)` düğmesi vardır: sayfa bilgisi, aranabilir rehberler, tekrar başlatma ve kaynak galerisi burada toplanır. Ayarlar ve komut paleti de rehberi açar. Yeni sidebar alanı yoktur. Proje/konu/kariyer/plan bağlamındaki yerel kayıt özeti doğrudan görünür; Hermes mesajı yazıp Enter'a basmak mevcut Goal Studio oturum/turn protokolünü başlatır. Pasif özet yerel deterministik uçtan alınır; modele istek göndermez.

## Kalıcılık ve mimari

`system` modülünde `/api/system/experience` GET/PUT; mevcut `setting` tablosundaki `product.experience.v1` anahtarını kullanır. Kapalı Pydantic sözleşmesi, sürüm 1 ve SHA256 revision ile korunur. PUT yerel StudioRoute güvenlik sınırından geçer. PostgreSQL advisory lock + revision karşılaştırması ikinci sekmenin eski seçimleri ezmesini 409 ile önler. Generic settings PUT ile bu sözleşme atlanamaz. Başarılı yazma `settings.updated` event'i üretir.

Onboarding durumları: new / in_progress / completed / dismissed; aşamalar: welcome / journey / sources / tour / checklist. Tur ve adım kimlikleri, ziyaret/geçme kayıtları, kaynak kararı ve kapatılan ipuçları kalıcıdır. Bozuk/gelecek sürümlü kayıt güvenli uyarıya dönüşür; kişisel kayıtlar değiştirilmez. Tarayıcıdaki revision sinyali yalnız sekmelerin query'sini tazeler; ayrı veri deposu değildir.

`catalog.ts` tur tanımları modül registry'sindeki etkin route'lardan türetilir. Hedef adımları/KR, gerçek görev, haftalık plan, proje, konu/kaynak, konu SRS, kart SRS, kariyer profili/başvurular, akış/RSS/yer imi ve değerlendirme açıklanır. Gerçek kayıt gerektiren koşullu kontroller bulunamazsa İleri devre dışıdır; kullanıcı kaydı açabilir veya adımı geçebilir. Eksik kontroller varmış gibi işaretlenmez.

Nonmodal tur paneli işlem yapmayı engellemez. Lazy hedefler MutationObserver ile izlenir; sabit timeout yoktur. Route değiştirmek mevcut navigation guard'dan geçer. Refresh sonrası adım korunur; zorla farklı sayfaya gidilmez. Adıma git gerçek hedefi odaklar. Escape/küçültme odağı header yardım düğmesine döndürür. İpuçları bir tane gösterilir; yazma, modal, hata, odak seansı veya Hermes görüşmesi sırasında bastırılır. Kaydırma animasyonsuzdur.

## Referanslardan alınan kararlar

- [Twenty onboarding geçişleri](https://raw.githubusercontent.com/twentyhq/twenty/main/packages/twenty-front/src/modules/onboarding/utils/getNextOnboardingStatus.ts): koşullu aşamalar ve geri dönüş fikri; forkOS'ta gerçek backend kanıtı kullanıldı.
- [n8n optional onboarding](https://raw.githubusercontent.com/n8n-io/n8n/master/packages/frontend/editor-ui/src/features/ai/instanceAi/onboarding/useInstanceAiOnboarding.ts): isteğe bağlı ve kalıcı ilerleme.
- [Appsmith checklist bileşeni](https://raw.githubusercontent.com/appsmithorg/appsmith/release/app/client/src/pages/Editor/FirstTimeUserOnboarding/Checklist.tsx): ilk kullanım checklist yüzeyi referansı.
- [Driver.js yapılandırması](https://driverjs.com/docs/configuration): tur etkileşimi incelendi; mevcut React/Modal/guard altyapısı ile küçük bir controller yazıldı, paket eklenmedi.

## Doğrulama ve sınırlar

Ayrıntılı sonuçlar [teslim raporunda](v1-welcome-delivery.md). Tarayıcıda karşılama, gerçek görev, tur refresh/devam, yardım/Escape, kaynak galerisi ve gerçek okuma/kayıt yolları ayrı geçici DB ile doğrulandı. Her koşullu hedef/kariyer dalının her veri kombinasyonu tarayıcıda yürütülmedi; registry, guard ve geç yüklenen hedef davranışları otomatik testlerde kapsandı. OS ekran okuyucusu ve gerçek %200 browser zoom denemesi yapılmadı. Bu özellik yeni model, entegrasyon veya veri migration'ı kurmaz.
