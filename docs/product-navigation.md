# forkOS ürün navigasyonu — V1

Kanonik ürün sınırları: [V1 ürün kapsamı](architecture/v1-product-scope.md).
Gerçek navigasyon `frontend/src/core/navigation.ts` ve modül registry'sinden türetilir.

| Alan | Yüzeyler |
| --- | --- |
| Home | Bugünün planı, dikkat, bekleyen kararlar, emek haritası |
| Plan | Görevler, haftalık plan, rutinler, Takvim, Pomodoro |
| Projeler | Proje ilerlemesi, görevleri, GitHub, Obsidian proje günlüğü |
| Hedefler / Strateji | Hedef ilerlemesi ve kariyer stratejisi |
| Kariyer | İlanlar, akademik fırsatlar, başvurular, mülakat, yerel kariyer belgeleri |
| Öğrenme | Öğrenme ağacı, SRS, bağımsız flashcard'lar |
| Kütüphane | Yer İmleri / Inbox ve RSS / Feed |
| Etkinlik / Değerlendirme | Hareket geçmişi, emek haritası, retrospektifler |
| Ayarlar | Tercihler, Agent & Bilgi, entegrasyonlar, durum/tanılama, yerel yedek |

Tanılama `health` modülü üzerinden kullanıcı tarafından erişilebilir kalır.
RSS kaynak yönetimi `/rss`, karma akış `/feed`, yer imleri `/bookmarks` ayrı yeteneklerdir.
Takvim doğrudan seçilen güne görev oluşturur; Pomodoro sayaç, geçmiş ve analitik içerir.

## Tarihsel URL uyumluluğu

| Eski rota | Davranış |
| --- | --- |
| `/notes?focus=<uuid>` veya `/knowledge?focus=<uuid>` | Vault öğesini çöz, sunucunun Obsidian URI'sini aç; eksik/bozuk/erişilemez durumunu göster |
| `/notes`, `/knowledge` | Ayarlar → Agent & Bilgi |
| `/documents` ve alt rotaları | Kariyer → Başvurular |
| `/media`, `/finance` ve alt rotaları | Home |

Not çözümleyici bir uyumluluk yüzeyidir; modül, editör, katalog veya sidebar öğesi değildir.
Tarihsel `note` entity rotası backend `EntityTypeSpec` içinde `/notes?focus={id}` olarak tanımlıdır.
Medya/Finans entity'leri Aktivite arşivine gider; yeni ilişki/arama seçicilerinde bulunmazlar.
Eski `media.links`, `section=media-links` ayarları ve `sources?scope=media` ürün davranışı sağlamaz.

## Sahiplik

Entity tipi etiketi/ikonu/rotası yalnız backend registry'sinden gelir.
Frontend `entityRoute()` ve `typeLabel()` kullanır. Komutlar, Today widget'ları,
sidebar ve rotalar frontend modül kaydından türer; emekli ürün kaydı yoktur.
Bilgi Obsidian'dadır; Ayarlar yalnız bağlantı, sağlık ve ajan yapılandırmasını yönetir.
Google entegrasyonu Calendar'dır; Drive sync veya bulut yedek davranışı sunulmaz.

## Başlangıç ve sayfa yardımı

Header'daki `(i)` sayfa bilgisini ve aranabilir rehberleri açar; Ayarlar ve komut paletinden de erişilir. Karşılama/tur ayrı bir navigasyon ürünü veya sidebar alanı değildir. `/feed` Kaynaklar galerisi kişisel sağlayıcıları ve seçkileri yönetir; `/rss` mevcut abonelik/OPML/okuyucu yüzeyidir. Proje ve konu bağlamında yerel özet doğrudan görünür, Hermes mesajı Enter ile mevcut Goal Studio akışına girer. [Detay](product/v1-welcome-onboarding.md).
