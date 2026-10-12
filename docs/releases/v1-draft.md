# forkOS V1 — taslak release notları

**Taslak; yayımlanmış release değildir. Yerel kalite kapısı geçti, CI bekleniyor.**

## Amaç ve kapsam

forkOS tek kullanıcılı, bilgisayarda çalışan bir kişisel işletim sistemidir.
Günlük yürütme ve ölçülebilir hedefler ortak Entity/Link/Event omurgasıyla bağlanır;
bilgi notlarının sahibi Obsidian Vault'udur.

- **Hedefler & Strateji:** plan, pillar, goal, KR ve milestone; ölçülmeyen sonuç başarı sayılmaz. Faaliyet ile sonuç ilerlemesi ayrıdır.
- **Planlama:** görevler, rutinler, haftalık plan, tarih/saat/süre, takvim, odak seansları ve açık onaylı carry-over.
- **Projeler:** işler, kilometre taşları, ilişkiler, activity timeline ve Obsidian bilgi/günlük köprüleri.
- **Öğrenme:** alan/konu ağacı, JSON import, kaynak bağlantıları, konu tekrarı ve flashcard SRS. Kaynak veya kart sayısı mastery değildir.
- **Kariyer & Akademik:** fırsatlar/duyurular, yerel profil ve CV değerlendirmesi, başvuru CRM'i, takip görevleri ve kayıt bağlantıları.
- **Hermes Brain Interface:** sınırlı yerel MCP araçları; Goal Studio typed proposal/revision ve açık onaydan sonra canonical kayıt. Manuel hedef akışı Hermes'ten bağımsızdır.
- **Obsidian & Capture:** canonical kimlik, UUID ile tekrar güvenliği ve explicit conflict; Vault erişilemezse açık hata, legacy DB'ye gizli fallback yok.
- **Personal Feed:** kullanıcı seçimiyle HN, GitHub, HF Papers, Reddit, RSS/OPML ve seçkiler; yer imleri ve tam metin okuyucu.
- **Başlangıç & Sistem:** welcome/journey, tekrar açılabilir tutorial, sayfa bilgi chip'i, modül tercihleri, source/model/worker/storage health ve yedekleme.

Emekli Medya, Finans, bağımsız Belgeler/Bilgi ve Google Drive arayüzleri V1 kapsamına geri eklenmedi; tarihsel metadata korunur.

## Bu kapanışta düzelenler

18 bulgu kapatıldı: yedek birleştirmede ilişki ve dosya koruması, missing-document hatası,
self-FK/chunk restore, dialog focus/Escape, gecikmiş goal/plan hydration, gerçek RSS
completion, native backup import race, project milestone deep link ve iki metin tutarsızlığı
ile teknik finding kodlarının görünümü. Yeni framework veya dependency eklenmedi.

Son yerel kapılar: backend 2744/43 skip, frontend 1062/0 skip, extension 27/0 skip;
typecheck/build/API schema, npm audit, pip check, migration/ikinci DB fingerprint restore geçti.
Gerçek Chrome %200, reduced motion, mobil/tablet/desktop ve açık/koyu tema doğrulandı.

## Kurulum ve platform

[README kurulum akışı](../../README.md): Docker Compose + PostgreSQL 16, FastAPI ve React/Vite.
macOS Apple Silicon + OrbStack üzerinde yerel doğrulama yapıldı. Podman alternatifinin
komutları korunur; Linux/Windows font rendering ve Podman bu turda canlı doğrulanmadı.
Worker isteğe bağlıdır ve varsayılan kapalıdır. Obsidian Vault ve Hermes bağlantıları
ayrıca yapılandırılır; normal ilk kullanımda Welcome kaynakları isteğe bağlı seçtirir.

## Local-first ve veri güvenliği

Servisler loopback üzerinde yayınlanır; hosted backend/auth/tenant/telemetri eklenmedi.
Kaynak çekimi dış GET yapabilir; kişisel veriyle model iletişimi yalnız yapılandırılmış
yerel provider'da bu turda doğrulandı. Dış model kullanan başka harness'lerin veri sınırı
ayrıca değerlendirilmelidir. Kaynak sonuçlarının tazeliği/eksiksizliği garanti edilmez.

Merge restore mevcut satırları değiştirmez. Dosyalar doğrulanır, farklı içerikteki
mevcut dosya korunur; precommit failure yeni dosyaları ve DB yazmasını geri alır.
Kayıp COMMIT cevabında tamamlanmış dosyalar korunur ve idempotent tekrar denenebilir.
Süreç/güç kesilmesine karşı DB+dosya sistemi dağıtık atomicity garantisi yoktur.
Obsidian Vault forkOS yedeğine dahil değildir; ayrı Vault yedeği gerekir.

## Bekleyenler

- GitHub Actions/CI kota sonrası ayrı doğrulanacak; tag/release oluşturulmadı.
- Codex OAuth ve Nous Portal canlı inference ertelendi.
- Canlı career acquisition testleri çalıştırılmadı; katalog ve scheduler değiştirilmedi.
- Yerel model zaman zaman geçersiz proposal üretebilir; UI draft'ı korur, hata gösterir, açık onaysız mutation yapmaz. Retry gerekebilir.
- Repository kökünde dağıtım LICENSE dosyası yok; yayımlama öncesi lisans kararını sahibi vermeli. Paket lock/license metadata kontrolü bu kararı çözmez.
- Ekran okuyucu uygulaması, high-contrast ve Windows/Linux gerçek font testi bu turda yapılmadı.

Ayrıntılı kanıt ve test sınırları: [readiness](../architecture/v1-pre-release-readiness.md).
