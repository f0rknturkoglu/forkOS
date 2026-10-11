# Kişisel akış ve kaynak keşfi

## Seçim

Yeni kurulumda HN, GitHub, Hugging Face Papers, Reddit ve RSS kapalıdır. Starter RSS kaynağı kurulmaz. Akış → Kaynaklar galerisi seçimleri anında taslakta gösterir; Kaydet önceki tercihleri sürümlü backend sözleşmesine yazar. Modal açılması, preset seçilmesi veya kaynak seçeneği değiştirilmesi dış GET başlatmaz. Galeriden RSS eklemek açık bir abonelik yazmasıdır fakat `probe:false` ile DNS/probe/poll yapmaz; kaynak kararı ayrıca kaydedilir. RSS okuyucusunda normal ekleme/OPML yeni abonelik eklenmesi açık RSS yenileme tercihi sayılır.

Eski gerçek RSS abonelikleri ve persist edilmiş subreddit seçimleri korunur. Varsayılan subreddit listesi izin sayılmaz. Kaynakların kapanması içerikleri, abonelikleri ve SourceRun geçmişini silmez. Boş subreddit ile Reddit yeni tercihi kaydedilemez; eski bu tür tercihte diğer sağlayıcılar korunur, Reddit GET kapalı kalır.

Yapay Zekâ & Araştırma (Papers+HN), Yazılım & Açık Kaynak (GitHub+HN), Kendi Kaynaklarım (RSS) presetleri düzenlenebilir başlangıç seçimleridir. Kullanıcı kendi seçkisini oluşturabilir, adını/üyelerini düzenleyebilir, sıralayabilir ve silebilir. Seçki üyeliği gerçek RSS Feed UUID'leri ve sağlayıcı kimlikleridir; abonelik silmez. Sınırlar: 12 seçki, seçki başına 50 Feed, 20 subreddit.

## Kaynak doğruluğu

| Sağlayıcı | Gerçek kaynak | TTL / sınır |
| --- | --- | --- |
| Hacker News | Mevcut Algolia front_page | 15 dk, en fazla 30 öğe |
| GitHub · Yeni ve Popüler | Search repositories: son 7 günde oluşturulan depolar, yıldız sırası | 6 saat, 30 depo |
| Hugging Face Papers | Resmî `/api/daily_papers`, isteğe bağlı `date=YYYY-MM-DD` | 24 saat, 30 makale, 2 MB |
| Reddit | Kullanıcının seçtiği toplulukların mevcut RSS proxy'si | 10 dk |
| RSS | Gerçek abonelikler ve mevcut kaynak kuyruğu | Mevcut interval, 4 MB yanıt |

GitHub resmî Trending değildir; ürün etiketi özellikle **Yeni ve Popüler** olarak düzeltilmiştir. [Resmî Search API](https://docs.github.com/en/rest/search/search#search-repositories).

HF latest isteğinde tarih gönderilmez, son gerçek seçki alınır. Yayın `paper.publishedAt`, seçki `paper.submittedOnDailyAt` alanından gelir; top-level `publishedAt` yayın yerine kullanılmaz. Yazar/özet/oylar gerçek alanlardır; eksik yorum veya görsel uydurulmaz. [Hub API](https://huggingface.co/docs/huggingface_hub/en/package_reference/hf_api), [resmî list_daily_papers uygulaması](https://raw.githubusercontent.com/huggingface/huggingface_hub/main/src/huggingface_hub/hf_api.py). Canlı doğrulama makalesi: [2610.11216](https://huggingface.co/papers/2610.11216), yayın 2026-10-08, seçki 2026-10-09.

## İstek ve sağlık davranışı

Frontend tüm haber query'lerini yalnız doğrulanmış ve seçilmiş tercihlerle açar. Backend provider uçları, RSS due/poll/refresh/startup ve worker yolu aynı tercihi denetler. Kapalı sağlayıcı adaptör oluşturmaz, ağ çağrısı veya sahte SourceRun üretmez. Worker varsayılan olarak kapalı kalır.

Haberlerin gerçek çekimi SourceAdapter + mevcut SourceRun start/finish protokolünü kullanır. Üç empty görünür stalled event'ine döner; bozuk sözleşme empty kabul edilmez. Aynı kaynağın eşzamanlı GET'leri kilitle tek çekime iner; cache istekleri yeni run üretmez. 429/503 Retry-After uygulanır, bekleme sırasında yeni dış istek/run yapılmaz. Cache process içindedir ve yeniden başlatmada silinir. Kaynak seçimi otomatik yenileme timer'ı kurmaz. Home ve Feed aynı query/cache yolunu paylaşır.

Sağlık özeti kapalı sağlayıcının tarihsel hatasını aktif sorun gibi saymaz. Tanılama geçmişi korunur. RSS kapalı banner'ı açık tercihi ifade eder; sağlıklı çekim iddiası değildir.

## Editorial akış ve okuma

`/feed` kartları seçilmiş kaynakları dönüşümlü birleştirir. Mixed akış bir RSS beslemesini 5, RSS toplamını 15 öğeyle sınırlar. URL tracking parametreleri çıkarılarak yinelenenler ayıklanır; HF/arXiv kimliği de aynı makaleyi tanır. Birleşim en fazla 200 aday, ilk 24 kart ve +24 devam adımları kullanır. Home ilk 15 öğeyi gösterir. İstenen sağlayıcı başarısızsa diğerleri kalır ve gerçek hata/yeniden dene yüzeyi görünür.

Otomatik uzak thumbnail/favicon/avatar çağrısı yoktur. Kartlar kaynak kimliği, başlık, mevcut özet, gerçek tarih/yazar/puanı taşır. RSS Oku mevcut entityRoute okuyucusuna gider; Kaydet mevcut `/rss/items/{id}/save` ile Bookmark + saved_from link'ini kullanır. Diğer kaynaklar stable client_uuid ile mevcut capture'a yazılır, URL dedup uygulanır. Papers kaydı mevcut BookmarkLearningAttach üzerinden gerçek konuya `learns_from` bağı kurar. Tam metin yoksa saklanan kaynak özeti açıkça özet olarak gösterilir; makale uydurulmaz.

## Güvenlik ve gizlilik

RSS yalnız HTTP(S), credentials olmadan standart portlarda kabul edilir. DNS yanıtlarının tamamı global olmalıdır; bağlantı doğrulanan IP'ye pinlenir, orijinal Host/SNI korunur. Her redirect yeniden doğrulanır; redirect sayısı ve indirilen byte sınırlandırılır. OPML 2 MB ile sınırlıdır; DOCTYPE/ENTITY engellenir, duplicate URL yeni abonelik üretmez. Okuyucu HTML'i aktif içerik, uzak gömülü asset ve tehlikeli link protokollerini temizler.

Tarayıcı yalnız ortak local API'yi kullanır. Kişisel görev/not/tercihler dış servise gönderilmez; sağlayıcı GET'leri içerik alma amaçlıdır. Yeni paket, CDN, telemetri veya harici LLM eklenmedi. Yaşayan doğrulamalar [teslim raporunda](v1-welcome-delivery.md).
