# career-ops → forkOS Opportunities Entegrasyon Planı

Kaynak: `pasted-text-1.txt` içindeki 4 Eylül 2026 tarihli karşılaştırma raporu.

Amaç, forkOS'un güçlü ilan toplama ve CRM altyapısını korurken career-ops'un
karar desteği, gerçeklik denetimi ve başvuru sonrası takip özelliklerini tamamen
yerel çalışan bir katman olarak eklemektir. Hiçbir özellik kullanıcı onayı olmadan
dışarıya başvuru veya mesaj göndermez.

## Faz 1 — Hızlı sinyaller ve başvuru sonrası radar

- [x] Aynı kurum + aynı başlık kimliği + 90 gün + farklı URL/gün kuralıyla repost/zombi ilan sinyali
- [x] Ücret bandını ayrıştırma ve `%50` üzerindeki genişlik için şeffaflık uyarısı
- [x] İlan metninden yerel risk sinyalleri: gizli taşeronluk, AI eleme bildirimi, geo-mismatch, sponsorluk engeli
- [x] Yapıştırılan e-posta yanıtını yerelde sınıflandırma ve kullanıcı onaylı aksiyon
- [x] Son görüşmeden 21+ gün sonra firma sessizliği radarı
- [x] Liste, kanban, ilan detayı ve CRM yüzeylerine entegrasyon

## Faz 2 — İki aşamalı değerlendirme ve güvenlik zekâsı

- [x] Pass 1: yalnız ilan metninden gereksinim, önem ve kanıt türü çıkarımı
- [x] `inferred` gereksinimin `critical/high` olmasını engelleyen doğrulama
- [x] Pass 2: aday belgeleriyle `strong/partial/missing` eşleştirmesi ve gap telafisi
- [x] FDE, SA, PM, LLMOps, Agentic Systems ve Transformation arketipleri
- [x] Çalışma izni profili, sponsorluk ve coğrafi hard-blocker kontrolü
- [x] Değerlendirme sürümü ve kullanıcı tarafından düzenlenebilir sonuç kaydı

## Faz 3 — Mülakat hafızası ve gerçeklik denetimi

- [x] Entity-backed STAR+R hikâye bankası
- [x] `existing / supported / derived-unverified / user-cannot-confirm` iddia kaynağı
- [x] Gereksinim ↔ hikâye eşleştirmesi
- [x] Mülakat turu bazlı sözlü ücret beyanı ve tutarlılık uyarısı
- [x] Cover letter için yerel Voice DNA / anti-AI-slop denetimi

## Faz 4 — Yerel warm-intro ağı

- [x] LinkedIn `Connections.csv` içe aktarımı
- [x] Kurum adlarını token bazlı normalize ederek fırsatlarla eşleştirme
- [x] İlan detayında bağlantı listesi ve ilişki bağlamı
- [x] Dış ağ çağrısı yapılmadığını doğrulayan gizlilik denetimi

## Tamamlanma kapıları

- [x] Backend modül, migration, registry ve event testleri
- [x] OpenAPI ve üretilen TypeScript şeması senkron
- [x] Endpoint kapsam kontrolü
- [x] Frontend tasarım sistemi ve TypeScript kontrolleri
- [x] Açık/koyu tema ve dar/geniş ekranda gerçek tarayıcı doğrulaması
- [x] Tüm backend ve frontend testleri

## 4 Eylül 2026 tamamlanma özeti

### Tamamlananlar

- Faz 1 tamamlandı: repost/zombi sinyali, ücret bandı ve şeffaflık riski,
  ilan riskleri, yapıştırılan yanıt sınıflandırması, kullanıcı onaylı durum
  aksiyonu ve 21+ günlük sessizlik radarı liste/kanban/detay/CRM'e bağlandı.
- Faz 2 tamamlandı: iki aşamalı değerlendirme, kanıt/önem güvenlik kuralı,
  altı rol arketipi, çalışma izni/coğrafya hard-blocker'ları ve düzenlenebilir
  sürümlü değerlendirme eklendi.
- Aday eşleştirmesi artık yalnız profil ayarına bakmıyor. Başvuruya bağlı CV'yi,
  yoksa son yerel CV belgesini seçiyor; TXT/MD/CSV/JSON/YAML, DOCX, HTML ve PDF
  içeriğini cihazda okuyup Pass 2'de kullanıyor. PDF için `pypdf` kilit dosyalarına
  eklendi; kullanıcı verisini dışarı gönderen yeni bir yol eklenmedi.
- Faz 3 tamamlandı: entity-backed STAR+R bankası, iddia kaynağı, gereksinime
  hikâye bağlama, tur bazlı ücret beyanı/tutarlılık uyarısı ve yerel cover-letter
  üslup/anti-slop denetimi eklendi.
- Faz 4 tamamlandı: entity-backed yerel bağlantı ağı, LinkedIn
  `Connections.csv` içe aktarımı, idempotent kişi güncellemesi, kurum token
  normalizasyonu, fırsat eşleştirmesi, arama paneli ve ilan detayındaki warm-intro
  kartı eklendi. CSV yalnız yerel API/PostgreSQL hattında işleniyor; yeni bir dış
  ağ isteği yok.
- `0045_career_connections` migration'ı canlı yerel veritabanına uygulandı ve
  veritabanı Alembic head durumunda.
- Canlı tarayıcıda bağlantı paneli ile ilan içindeki warm-intro kartı 824 px ve
  1280 px genişlikte, açık ve koyu temalarda doğrulandı. Kullanıcı verisini
  değiştirmemek için canlı veritabanına sahte bağlantı eklenmedi; CSV içe aktarım,
  tekrar içe aktarım ve fırsat eşleştirmesi entegrasyon testinde doğrulandı.
- Son temiz doğrulama: backend `393 passed`; frontend `491 passed`; TypeScript
  geçti; OpenAPI ve üretilen TypeScript şeması güncel; referanssız endpoint sayısı
  `0`; gizlilik taraması yeni dış ağ çağrısı bulmadı.
