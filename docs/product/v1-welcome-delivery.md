# V1 Welcome & Personal Feed — teslim raporu

Doğrulama: 12 Ekim 2026, yerel macOS/OrbStack ortamı.

1. **Başlangıç HEAD:** `97ed63ecb8606356f88426a4219ad9b95d8fc657` (`main`).
2. **Çalışma ağacı güvenliği:** başlangıç temizdi. Yeni worktree açılmadı; aynı checkout kullanıldı. Testler tmpfs PostgreSQL container'ında, `forkos_test` ve ayrı `forkos_ui_test` DB'lerinde yürütüldü. Kişisel `forkos_pgdata`, Vault, attachment ve kullanıcı kayıtları test/seed olarak kullanılmadı. Browser test kayıtları normal DB'ye aktarılmadı.
3. **Yeniden kullanılan altyapı:** System Setting, ModuleSpec/EntityTypeSpec registry, ortak API ve invalidateAfter, Modal/Input/Button/IconButton, navigation guard, SourceAdapter/SourceRun, RSS kuyruğu, canonical capture/Bookmark, BookmarkLearningAttach, ContextSummary ve Goal Studio. Yeni paket eklenmedi.
4. **Welcome/tur:** kanıtlanmış boş backend karşılama; isteğe bağlı amaç seçimi, geri/geç/kapat/yeniden aç/devam. Koşullu gerçek hedeflere dayanan turlar, refresh sonrası adım devamı; sahte görev veya başvuru yok. Checklist gerçek kayıt + ziyaret + kaynak kararını denetler.
5. **Kaynak keşfi:** Kaynaklar galerisi immediate pending seçim, save öncesi dış GET yok, presetler ve açık RSS/OPML kontrolü. Normal kurulumda geçmiş abonelikler korunur.
6. **Sağlayıcılar:** Hacker News, GitHub · Yeni ve Popüler, Hugging Face Papers, kendi RSS abonelikleri, açık seçilmiş Reddit toplulukları.
7. **GitHub doğruluğu:** mevcut Search repositories sorgusu resmî Trending diye etiketlenmiyor; son 7 günde açılan depolar yıldız sırasıyla gösteriliyor.
8. **HF sözleşmesi:** resmî latest/date API canlı kontrol edildi. `2610.11216` gerçek yayını 2026-10-08, seçkisi 2026-10-09; yazar/özet/oylar gerçek alanlardan. Latest tarihsiz, history açık tarihli. Bozuk kimlik/başlık error; fabricated makale/görsel yok.
9. **Seçkiler:** backend sürümlü Setting içinde UUID, ad, kanal ve gerçek Feed üyelikleri. Oluşturma/ad/üyelik/sıra/silme desteği. Revision+advisory lock eski sekmenin yazmasını 409 ile durdurur. Abonelikler seçki silinince silinmez.
10. **Varsayılan kapalı kanıtı:** otomatik test fresh welcome ve all-off durumunda yalnız experience GET'i; provider uçları boş dönüyor, kaynak adaptörü/ağ/run oluşturulmuyor. RSS due/poll/refresh ve startup catch-up kapalı tercihi uyguluyor. Galeri pending RSS ekleme probe yapmıyor.
11. **Legacy RSS:** gerçek abonelikler implicit legacy opt-in olarak okunuyor; starter kurulumu yok. Normal RSS ekleme açık tercih; OPML duplicate idempotent. Eski subreddit ayarları korunuyor, defaults izin sayılmıyor. RSS kapatılınca geçmiş içerik ve run'lar kalıyor.
12. **Sağlık/zamanlama:** bütün haber çekimleri SourceRun start/finish; 3 empty → stalled event. TTL ve singleflight, bounded cache, Retry-After cooldown. Kapalı kaynakların eski hatası aktif sorun gibi sayılmıyor. Yeni polling timer'ı yok; worker varsayılan kapalı.
13. **Gerçek okuma yolları:** tarayıcıda HF → canonical Bookmark → okuyucu, gerçek alan/konu oluşturma → öğrenme kaynağı bağlama (`learns_from`) doğrulandı. RSS → canonical save (`saved_from`) → RSS okuyucu gerçek içerik/read-state doğrulandı. Uzak tam metin olmayan Bookmark için mevcut özet, özet etiketiyle gösteriliyor. Hermese Enter ile tek submit akışı ve aynı UUID ile güvenli retry otomatik testte doğrulandı.
14. **Erişilebilirlik:** 1254×887 ve 390×844 reflow; dar galeride yatay taşma yok (scrollWidth=clientWidth=380). `(i)` 32px, SVG 14px. Escape sonrası odak yardım düğmesine dönüyor. Klavye, gerçek hedef odaklama, lazy target ve guard otomatik testte. Dark tema tarayıcıda görüldü. OS ekran okuyucusu, light tema görsel incelemesi ve gerçek %200 browser zoom yapılmadı.
15. **Browser E2E:** boş backend welcome → planning → AI preset/save → gerçek Todo → planner turu → refresh/resume → Home/checklist. Akış gerçek HF/HN/GH; save/reader/learning attach. RSS pending add → OPML dosya seçici → duplicate import (tek Feed) → explicit refresh (20 gerçek FeedItem) → save/read (1 saved_from). Normal runtime geri açıldı; Okuma akışı/header yardım görünür, otomatik welcome yok, Vite error overlay yok. Koşullu hedef/KR/kariyer turlarının bütün dalları manuel yürütülmedi.
16. **Testler:** backend **2679 passed, 36 skipped**, 152.88 sn; frontend tam suite **153 dosya / 1039 passed**, 11.85 sn. Son RSS/stream değişikliklerinden sonra ilgili 4 dosya/31 test tekrar geçti. TypeScript+Vite+PWA build ve bundle gate geçti (67 precache girdisi, 71 asset). OpenAPI/api-schema check geçti. Endpoint coverage mevcut 1 referanssız career-ops doctor ile 3 eşik altında; yeni uçlar tüketiliyor. Yeni backend dosyalarında Ruff, design-system testleri ve git diff --check geçti. Midnight/week ve host/DB clock test fixture'ları deterministikleştirildi; üretim tarih mantığı değiştirilmedi.
17. **Ağ ölçümleri:** deterministic singleflight testinde 5 paralel okuma + 1 tekrar → **1 upstream GET / 1 SourceRun**. Disabled testinde → **0 external call / 0 SourceRun**. Pending RSS add sonrası canlı UI test DB'de RSS run sayısı **0**, explicit refresh sonrası **1 ok**. Kaynak sayısı/seçimi değişmeden tur yazmaları cache süresi içinde yeni upstream çekim gerektirmiyor. Browser provider sayfaları ayrı local API GET'leri yapabilir; bunlar backend TTL ile ağdan ayrılır. Genel first-paint/CPU performans benchmark'ı yapılmadı.
18. **Migration:** yeni migration/DDL yok. Mevcut zincir geçici DB'de upgrade edildi; tek gerçek head `0080_goal_studio_capture`. Migration guardrail testleri tam suite içinde geçti. Eski migration veya entity/event/link çekirdeği değiştirilmedi.
19. **Sınırlar:** upstream tazelik/rate-limit/erişilebilirlik garanti değildir. Process cache restart'ta silinir. Reddit için topluluk gereklidir. Tam makale metni bulunmayan öğe özet/orijinal link sunar. Mevcut yerel ortamda Goal Studio yardım profili **not_configured**; actual yerel sohbet turu canlı modele karşı test edilmedi. H4 kapalıdır. Normal başlangıç checklist'inin yerel Qwen model health adımı 120 saniyede hazır olmadı; core container'lar açık ve sağlıklı kaldı. Hermes CLI'nin geçici Python yoluna bağlı başlatıcısı mevcut kalıcı runtime yoluna onarıldı; MCP **37 araç** keşfiyle bağlantı geçti. Normal web container'ındaki eski node_modules kilit dosyasına göre npm ci ile eşitlendi.
20. **Git teslimi:** `main`; `1bd519c` backend tercihler/sağlayıcılar, `54a4187` welcome/turlar/editorial akış, `f8f6ffa` testler. Dokümantasyon ayrı son commit'tedir. Force push kullanılmaz; son uzak SHA ve temiz ağaç teslim mesajında doğrulanır.
21. **V1 kararı:** Welcome, rehberler ve isteğe bağlı kişisel Feed günlük kullanıma hazır; gerçek provider/kayıt yolları ve local-only sınırları doğrulandı. Bütün entegrasyonların uçtan uca hazır olduğu iddiası yoktur: canlı Hermes sohbeti için ayrı doğrulanmış yerel yardım profili gereklidir. forkOS normal çalışma ortamı **açık bırakılır**; yalnız bu görev için açılan test kaynakları temizlenir.

## Kanıt ve tekrar doğrulama

Test DB: loopback `55432`, tmpfs. Normal DB: mevcut Compose volume/port. Browser testlerinde kullanıcı verisi yerine ayrı geçici DB kullanıldı.

```bash
# Yalnız izole TEST DB ile backend suite
PATH=/tmp/forkos-welcome-venv/bin:$PATH DATABASE_URL=<isolated-test-db> pytest -q
# frontend/
npm test
npm run build
PATH=<python312-venv>/bin:$PATH npm run api:check
node scripts/check-endpoint-coverage.mjs
# root
git diff --check
```

Görev sonunda geçici venv/container kaldırılır; yukarıdaki örnek PATH otomatik yeniden kullanılacak kalıcı runtime değildir. Normal forkOS container'ları, Obsidian ve Hermes Desktop kapatılmaz.
