# forkOS × career-ops Entegrasyonu (C1: Temel & Doctor, C2: Keşif & Sağlayıcı Füzyonu, C3: İlan Metni, Canlılık ve İstihbarat, C3.1: Kanıt Doğruluğu & Yaşam Döngüsü Kapanışı)

Bu doküman, `career-ops` projesinin forkOS içerisine **sürüm-sabitli iç yetenek motoru** (version-pinned internal capability engine) olarak nasıl entegre edildiğini, hakikat sınırlarını, C1.1 çalışma zamanı güvenlik sertleştirmelerini, C2 iş keşfi (Discovery & Provider Fusion), C3 ilan çıkarma / canlılık / ilan istihbaratı ve C3.1 kanıt doğruluğu ve yaşam döngüsü kapanışı mimarisini tanımlar.

---

## 1. Mimari Sorumluluk ve Hakikat Zinciri

Entegrasyonun temel kuralı: **Tek bir kalıcı hakikat kaynağı vardır ve o da forkOS PostgreSQL'dir.**

```text
Hermes (Orkestratör)
    ↓
forkOS (Kanonik İşletim Sistemi)
    ├── kanonik kariyer durumu  → PostgreSQL
    ├── kalıcı insan bilgisi    → Obsidian
    └── CareerOps entegrasyonu
             ↓
        career-ops motoru (Arama / Analiz / Üretim Motoru)
```

### Kesin Roller
* **`career-ops`**: Salt bir arama, analiz ve üretim motorudur.
* **`forkOS PostgreSQL`**: Tüm kariyer durumlarının (`Opportunity`, `Application`, `Interview`, `CareerStory`, `CareerConnection`) tek kanonik sahibidir.
* **`Hermes`**: Karar ve orkestrasyon katmanıdır. career-ops'a doğrudan veya keyfi erişimi **yoktur**.
* **`Obsidian`**: İnsan tarafından okunabilir kalıcı not ve bilgi deposudur.

### Kesinlikle Devre Dışı Bırakılan / Reddedilen career-ops Davranışları
Aşağıdaki upstream özellikleri forkOS tarafından **asla** hakikat veya durum olarak kabul edilmez:
1. `data/applications.md` veya `data/pipeline.md` takip dosyaları.
2. SQLite türevli takip veritabanları (`data/applications.db`).
3. Upstream `set-status.mjs` veya durum değiştirme betiklerinin kanonik durum yazması.
4. Upstream `update-system.mjs` self-updater'ı (otomatik güncelleme kesinlikle yasaktır).
5. career-ops Web veya Go TUI gösterge panelleri.
6. Otomatik başvuru gönderme veya otomatik e-posta/mesajlaşma mekanizmaları.
7. Harici bulut/telemetri entegrasyonları.

---

## 2. Sabitlenmiş Sürüm Kimliği ve Kilit Dosyası (Single Source of Truth)

Entegrasyon, upstream reponun belirli ve test edilmiş bir commit'ine kilitlenmiştir. Tek yetkili kaynak **`backend/app/integrations/career_ops/upstream.lock.json`** dosyasıdır:

```json
{
  "repository": "career-ops-hq/career-ops",
  "version": "1.34.0",
  "commit": "6326eb5d3804e8cb20d28acd5701a4e603a301f9"
}
```

* Hem Python konfigürasyonu (`config.py`) hem de kurulum betiği (`scripts/setup_career_ops.sh`) bu dosyayı tüketir; hiçbir yerde sabit değer kopyası (duplicate literal) bulunmaz.
* Commit SHA doğrulaması zorunludur: checkout commit'i tespit edilemez veya bilinmeyen bir commit ise motor **asla `READY` durumuna geçemez** (`MISCONFIGURED` olarak işaretlenir).

---

## 3. Kurulum ve Çalışma Zamanı Topolojisi

* **Konum**: `.vendor/career-ops` dizini (forkOS `.gitignore` içinde yer alır; ana git ağacına kod kopyalanmaz).
* **Hazırlık (Provisioning)**:
  ```bash
  make career-ops-setup
  # veya doğrudan:
  ./scripts/setup_career_ops.sh
  ```
  Bu betik `upstream.lock.json` dosyasını okuyarak upstream repoyu belirtilen commite çeker, `npm install --ignore-scripts --no-audit` ile minimal JS bağımlılıklarını kurar ve sürüm/commit doğrulaması yapar.

* **Çalıştırma Modeli (Subprocess Runner & Streaming Bounds)**:
  `backend/app/integrations/career_ops/runner.py` içindeki `SubprocessCareerOpsRunner`, allowlist'e tabi betikleri (`doctor.mjs`, vb.) izole argümanlarla çalıştırır.
  - **Akış Sınırları**: `stdout` ve `stderr` çıktıları `max_buffer_bytes` (varsayılan 512 KB) ile **anlık akış (streaming chunk) esnasında** sınırlandırılır.
  - **Zombi Süreç Koruması**: Arabellek aşımı veya zaman aşımı durumunda alt süreç `SIGTERM` ve gerektiğinde `SIGKILL` ile derhal sonlandırılır ve işletim sistemi kaynakları `wait()` ile geri toplanır (reap edilir).

---

## 4. Çalışma Alanı İzolasyonu ve Kanonik Güvenlik

Upstream betiklerin forkOS dosyalarını veya kendi kaynak dizinlerini kirletmesini önlemek için izole bir çalışma alanı kullanılır:

```text
backend/data/runtime/career-ops/
    ├── generated-input/      # Geçici girdi yükleri
    ├── temporary-output/     # Ham betik çıktıları / raporlar
    └── cache/                # Geçici önbellek
```

Tüm betik çağrılarına `CAREER_OPS_ROOT`, `CAREER_OPS_DATA_DIR` ve `CAREER_OPS_TRACKER` ortam değişkenleri enjekte edilerek dosya yazımları bu dizine hapsedilir.

### Kanonik Veritabanı Değişmezliği (Zero Canonical Mutation)
`backend/tests/test_career_ops_safety.py` içinde `capture_db_content_fingerprint` ile doğrulanır:
- CareerOps teşhis (`doctor`) veya yetenek sorguları esnasında forkOS PostgreSQL kanonik tablolarında (Entity, Event, Opportunity, vb.) **sıfır mutasyon** gerçekleştiği SHA-256 parmak izi ile matematiksel olarak kanıtlanmıştır.
- Dosya sistemi testinde upstream `applications.md` ve `pipeline.md` takip dosyalarının hiçbir dizine yazılmadığı test edilir.

---

## 5. Yapılandırma (`Settings`)

`backend/app/config.py` ve `.env.example` üzerinden yönetilen ayarlar:

| Ayar | Varsayılan | Açıklama |
| --- | --- | --- |
| `CAREER_OPS_ENABLED` | `False` | Entegrasyon anahtarı. Kapalıyken forkOS sıfır bağımlılıkla açılır. |
| `CAREER_OPS_ROOT` | `""` | career-ops dizini (boşsa `.vendor/career-ops` çözülür). |
| `CAREER_OPS_NODE_BIN` | `"node"` | Node.js çalıştırılabilir dosya yolu. |
| `CAREER_OPS_TIMEOUT_SECONDS` | `30.0` | Azami betik zaman aşımı süresi. |
| `CAREER_OPS_MAX_BUFFER_BYTES` | `524288` (512 KB) | Azami stdout/stderr bellek akış sınırı. |
| `CAREER_OPS_RUNTIME_DIR` | `""` | İzole çalışma alanı yolu. |

### Hata Semantiği (Fail Closed)
- `career_ops_enabled=False` ise motor `DISABLED` durumundadır.
- Node veya checkout eksikse motor `UNAVAILABLE` döner; forkOS asla çökmez.
- Commit veya sürüm uyuşmazlığında motor `VERSION_MISMATCH` döner ve işlem yapmayı reddeder.
- Bilinmeyen commit SHA tespitinde motor `MISCONFIGURED` döner.

---

## 6. Yetenek Kayıt Defteri (Capability Registry)

`backend/app/integrations/career_ops/capabilities.py` içinde tanımlanan semantik yetenekler:

* **Temel**: `foundation.doctor` (C1'de aktif)
* **Keşif**: `discovery.scan`, `discovery.reverse_ats`, `discovery.liveness` (C2)
* **İlan & İstihbarat**: `job.extract`, `job.repost_analysis`, `job.legitimacy` (C2/C3)
* **Değerlendirme**: `evaluation.deep`, `evaluation.requirements`, `evaluation.compensation`, `evaluation.work_authorization` (C3)
* **CV & Belge**: `cv.tailor`, `cv.verify_facts`, `cv.render_pdf`, `cv.render_latex`, `cv.visual_validate` (C5)
* **Başvuru & Mülakat**: `application.cover_letter`, `application.answers`, `application.prefill`, `interview.prepare`, `interview.practice`, `interview.debrief` (C4)
* **Analitik**: `analytics.funnel`, `analytics.rejection_patterns`, `analytics.skill_gap`, `analytics.calibration` (C4)

C1-C2.1 aşamasında `foundation.doctor` ve `discovery.reverse_ats` aktiftir; diğer yetenekler bildirilmiş ancak henüz implemente edilmediği için `unavailable` raporlanır.

---

## 7. Teşhis ve Doctor (CLI & API)

### Doğruluk İlkeleri (Truthfulness & Separation)
- **`--target` Bayrağının Kaldırılması**: Upstream `doctor.mjs` betiğine `--target` verilmez. `--target` upstream tarafından hem proje hem kod kökü olarak yorumlandığından runtime scratch dizininde kod dosyalarını aramakta ve hatalı sonuç vermekteydi. İzolasyon salt ortam değişkenleriyle sağlanır.
- **Entegrasyon Sağlığı ve Upstream Hazırlık Ayrımı**: Upstream `doctor.mjs --json` çıktısındaki eksik profil/cv/playwright uyarıları `upstream_onboarding` başlığı altında bilgilendirme amaçlı raporlanır; C1 entegrasyonunun `READY` durumunu bozmaz.

### CLI Kullanımı
```bash
# Sadece durum özeti:
make cli ARGS="status"

# Detaylı career-ops tanı raporu:
make cli ARGS="career-doctor"
```

### API Endpoint'i
```http
GET /api/system/career-ops/doctor
```
Salt okunurdur; sistem durumunu, kilit dosyasını ve upstream onboarding durumunu derleyerek döner.

---

## 8. Sürüm Yükseltme Prosedürü (Upgrade Runbook)

Gelecekte career-ops sürümü güncellenmek istendiğinde izlenecek adımlar:

1. **Upstream Commit Seçimi**: Upstream sürüm ve commit SHA'sını belirle (asla `latest` çekme).
2. **Kilit Dosyasını Güncelle**: `backend/app/integrations/career_ops/upstream.lock.json` içindeki `version` ve `commit` değerlerini güncelle.
3. **Provisioning Çalıştır**:
   ```bash
   ./scripts/setup_career_ops.sh
   ```
4. **Sözleşme ve Güvenlik Testlerini Doğrula**:
   ```bash
   pytest backend/tests/test_career_ops*.py -v
   ```
5. **Yetenek ve Çıktı Farklarını İncele**: Upstream script argümanlarında veya JSON çıktılarında kırıcı değişiklik olup olmadığını denetle.
6. **Git Commit**: Sürüm yükseltmesini forkOS üzerinde commit'le.

---

## 9. C2: Keşif ve Sağlayıcı Füzyonu (Discovery & Provider Fusion)

C2 aşamasında, `career-ops` motorunun reverse-ATS tarama kabiliyeti forkOS'un `SourceAdapter` sözleşmesine bağlanmıştır.

### 9.1 Desteklenen Sağlayıcılar ve Kaynak Kimlikleri
Aşağıdaki 6 ATS sağlayıcısı `careerops:<provider>` ad alanında forkOS kaynaklarına eklenmiştir:
- `careerops:greenhouse`
- `careerops:lever`
- `careerops:ashby`
- `careerops:workday`
- `careerops:icims`
- `careerops:bamboohr`

Tüm `careerops:*` kaynakları **`SourceClass.SLOW_OPTIN`** olarak sınıflandırılmıştır. Arka plan otomatik periyodik taramalarına dahil edilmez; yalnızca açık kullanıcı isteği veya manuel tetikleme ile çalıştırılır.

### 9.2 Çalışma Zamanı Dinamik Portals Projeksiyonu
forkOS kendi kullanıcı tercihlerini (`config.yaml` içindeki rol terimleri, beceriler, yasaklı kelimeler, şehirler) upstream motorun anlayacağı biçime dönüştürür:
- `CareerOpsDiscoveryConfigBuilder`: forkOS tercihlerini anlık olarak okur ve `portals.yml` formatına çevirir.
- Betik çağrısı öncesinde `backend/data/runtime/career-ops/portals.yml` konumuna yazılır ve `CAREER_OPS_PORTALS` ortam değişkeni ile aktarılır.
- Betik çalışması tamamlandığında `finally:` bloğunda derhal silinir (`unlink`).
- `.vendor/career-ops` içerisine hiçbir filtre ya da ayar dosyası yazılmaz.

### 9.3 Makine Sözleşmesi ve Güvenli Çalıştırma
- **Yalnızca JSON Çıktı**: Betik `scan-ats-full.mjs --json --dry-run` bayraklarıyla çağrılır. Disk veya veritabanına doğrudan yazma kesinlikle engellenir.
- **Tek Belge Ayrıştırma**: `stdout` içindeki JSON belgesi güvenle ayıklanır; eksik/bozuk çıktılarda `CareerOpsInvalidOutputError` fırlatılır.
- **Runner İzin Listesi**: Yalnızca onaylı `scan-ats-full.mjs` ve `doctor.mjs` betiklerinin çalıştırılmasına izin verilir; keyfi dosya/argüman yürütme güvenlik hatası üretir.

### 9.4 Çok Kaynaklı Kanonik Birleştirme ve Dedup
- Bir ilan hem mevcut bir forkOS kaynağından (örn. `forkjob:greenhouse`) hem de `careerops:greenhouse` tarafından keşfedildiğinde, URL ve kanonik anahtar üzerinden **aynı `Opportunity` kaydına bağlanır**.
- Her iki kaynaktan gelen tarama için ayrı `OpportunitySourceObservation` üretilir.
- `careerops` gözlemleri asla forkjob tarafından çıkarılan zengin metadata'yı (açıklama, şirket meta verisi) veya kullanıcı düzenlemelerini ezmez (`coalesce` semantiği).

### 9.5 Yanlış Kapanma Koruması (No False Closure Invariant)
Geleneksel forkjob kaynaklarında, hedef panoda artık listelenmeyen ilanlar `_sweep_missing()` tarafından `status="closed" / source_status="missing"` durumuna çekilir.
Reverse-ATS discovery taramaları ise şirket şirket gezen ve filtreye göre kısmi sonuç getiren örnekleme taramalarıdır.
Bu nedenle:
- `backend/app/modules/opportunity/worker.py` içerisinde `careerops:` öneki `MISSING_SWEEP_EXEMPT_PREFIXES` arasına alınmıştır.
- `careerops:*` taramalarında görünmeyen mevcut ilanlar **asla** süpürülmez ve kapanmış olarak işaretlenmez.

### 9.6 Lane B (`scan.mjs`) Analizi ve Ertelenme Gerekçesi
`scan.mjs` betiği `--json` parametresiyle çağrıldığında yalnızca `{"added_urls": ["https://..."]}` listesi üretmektedir; başlık, şirket adı, konum veya tarih gibi ilan meta verilerini sağlamamaktadır. Bu durum forkOS `RawItem` sözleşmesini karşılamadığı ve C2'de LLM kullanımına izin verilmediği için, `discovery.scan` yeteneği **`UNAVAILABLE`** olarak bırakılmış ve registry envanterinde gerekçesiyle belgelenmiştir.

---

## 10. Yetenek Envanteri ve Durum Tablosu

`get_provider_capability_inventory()` çağrısıyla elde edilen sağlayıcı bazlı entegrasyon matrisi:

| Sağlayıcı | Tarama Kabiliyeti | Durum | Gerekçe |
| --- | --- | --- | --- |
| `greenhouse` | Reverse ATS | `SUPPORTED` | `scan-ats-full.mjs` üzerinden tam entegre |
| `lever` | Reverse ATS | `SUPPORTED` | `scan-ats-full.mjs` üzerinden tam entegre |
| `ashby` | Reverse ATS | `SUPPORTED` | `scan-ats-full.mjs` üzerinden tam entegre |
| `workday` | Reverse ATS | `SUPPORTED` | `scan-ats-full.mjs` üzerinden tam entegre |
| `icims` | Reverse ATS | `SUPPORTED` | `scan-ats-full.mjs` üzerinden tam entegre |
| `bamboohr` | Reverse ATS | `SUPPORTED` | `scan-ats-full.mjs` üzerinden tam entegre |
| `portal_scan` | Broad Scan | `UNAVAILABLE` | `scan.mjs` yalnızca URL döner, ilan meta verisi sağlamaz |

---

## 11. C2.1 Doğruluk ve Kanonik Birleştirme Kapanışı (Correctness & Canonical Merge Closure)

C2.1 fazı, C2 keşif yeteneğini sağlamlaştıran ve veri kaybını/bozulmasını önleyen 12 maddelik doğruluk ve güvenlik denetimini tamamlamıştır:

1. **Upstream `location_filter` Şema Uyumu**: `CareerOpsDiscoveryConfigBuilder` upstream `buildLocationFilter()` şemasıyla (`always_allow`, `allow`, `block`, `block_hard`, `strict: False`) birebir uyumlu hale getirilmiştir.
2. **Çalışma Zamanı Hazırlık Kapısı (`CareerOpsRuntimeGuard`)**: Subprocess çağrılmadan önce kilitli sürüm, commit hash, Node >= 18 sürümü ve gerekli betik varlığı fail-closed olarak doğrulanır.
3. **URL Sınır Doğrulaması & Katı JSON Sözleşmesi**: Yalnızca `http://` ve `https://` şemaları kabul edilir (`javascript:`, `file:` vb. karantinaya alınır); `stdout` tek ve tam JSON belgesi olarak ayrıştırılır.
4. **Alt Süreç İptali ve Öksüz Süreç Temizliği**: `asyncio.CancelledError` durumunda alt süreç ağacı (`terminate` -> `wait` -> `kill` -> `wait`) güvenle toplanır.
5. **Tarama Eksiksizliği ve Bozulma Hakikati**: Kota aşımı (`capHit`), kısıtlanan pano (`cappedBoards`) veya kesinti durumlarında `FetchOutcome.partial = True` ve açıklayıcı `detail` atanır.
6. **Deterministik Küme Eşleme & Farklı URL Dedup**: `forkjob_core.models.cluster_key` kullanılarak farklı URL'lerden gelen aynı pozisyon tek bir `Opportunity` altında birleştirilir.
7. **Veri Kaybı Olmayan İlan Tazeleme (`_refresh_opportunity`)**: Zengin forkjob verileri (açıklama, çalışma modu, maaş, ülke, bölge, skor, profil uyum oranı) seyrek career-ops taramaları tarafından ezilmez; `raw["career_ops"]` ve `raw["sources"]` zenginleştirilir.
8. **Worker Kiralama Kataloğu**: `careerops:*` kaynakları worker `_source_catalog()` içine dahil edilmiş ve 300 saniyelik sert zaman aşımı kiralama korumasına alınmıştır.
9. **Dinamik Teşhis Yetenek Sayımı**: `CareerOpsDoctor` çalışma zamanı durumuna göre `capabilities_available` değerini dinamik hesaplar.
10. **Sıfır PostgreSQL Mutasyon Güvencesi**: `READY` teşhis probu esnasında dahi kanonik veritabanında sıfır mutasyon gerçekleştiği kanıtlanmıştır.

---

## 12. Kanonik Yol Haritası (Canonical Roadmap)

| Aşama | Başlık | Durum | Odak |
| --- | --- | --- | --- |
| **C1** | Temel & Teşhis (Foundation & Doctor) | `CLOSED` | Sürüm sabitleme, izolasyon, doctor teşhisleri |
| **C1.1** | Hakikat ve Çalışma Zamanı Sertleştirmesi | `CLOSED` | Streaming bounds, tek kilit dosyası, zombi koruması |
| **C2** | Ters ATS Keşfi ve Sağlayıcı Füzyonu | `CLOSED` | 6 ATS sağlayıcısı, SourceRun, non-destructive merge |
| **C2.1** | Doğruluk ve Kanonik Birleştirme Kapanışı | `CLOSED` | cluster_key dedup, location_filter uyumu, runtime guard |
| **C3** | İlan Zenginleştirme ve Yaşam Döngüsü | `CLOSED` | JD extraction, liveness köprüsü, 2-step kapanma, listing health |
| **C3.1** | Kanıt Doğruluğu ve Yaşam Döngüsü Kapanışı | `CLOSED` | Playwright çözümleme, taze 2. onay, timestamp ayrımı, JD provenance & promotion, yetenek mutabakatı |
| **C4** | Derin Değerlendirme ve Skorlama | `FUTURE` | A-H çok boyutlu uyum raporları, risk analizleri |
| **C5** | Başvuru Hazırlığı ve Hermes Orkestrasyonu | `FUTURE` | CV/ön yazı stratejisi, başvuru paketi üretimi |

---

## 13. C3 İlan Zenginleştirme, Canlılık ve İlan İstihbaratı (JD Extraction, Liveness & Listing Intelligence)

C3 entegrasyonu, career-ops motorunun içerik çıkarma, sıfır-token link canlılık doğrulaması ve ilan kalitesi değerlendirme yeteneklerini forkOS'a bağlar.

### 13.1 Değişmez Temel İlkeler (Core Invariants)
1. **Sıfır LLM Çağrısı (Zero LLM Tokens)**: İlan metni çıkarma, canlılık doğrulaması ve ilan kalite değerlendirmeleri %100 deterministiktir (DOM seçicileri, düzenli ifadeler, upstream JSON API'leri ve kural tabanlı puanlama).
2. **Kanonik Hakikat Tekliği**: Tüm kalıcı durumlar (`OpportunitySourceObservation.enrichment` JSONB alanı, `Opportunity.source_status`, `Opportunity.closed_at`) PostgreSQL'de saklanır. Upstream `scan-history.tsv` projeksiyonları kesinlikle geçicidir (ephemeral scratch) ve işlem sonunda silinir.
3. **Aday Uygunluk Skoru İzolasyonu**: `Opportunity.score` (adayın profile/beceriye uygunluğu) ilan kalitesi sinyallerinden **asla** etkilenmez. İlan kalitesi ayrı bir teşhis nesnesi (`listing_health`) olarak sunulur.
4. **Canlılık Tutarlılığı (`uncertain != expired`)**: Ağ zaman aşımı, WAF engeli veya geçici hatalar `uncertain` üretir ve ilanı asla kapatmaz. Kapanma, tüm bağlı kaynaklarda en az 12 saat arayla 2 ardışık onay gerektirir (2-step confirmation).

### 13.2 Statik JSON Köprüsü (`bridges/liveness.mjs`)
Upstream CLI çıktısı insan için biçimlendirilmiş metin (`✅ active`) bastığından, regex kazıma yerine forkOS'a ait bağımsız bir Node köprüsü yazılmıştır:
- ATS API'leri (Greenhouse, Lever, Ashby, Workday) doğrudan HTTP üzerinden sıfır tarayıcı maliyetiyle kontrol edilir.
- Fallback olarak izole Playwright Chromium sayfası çalıştırılır.
- SSRF koruması (`rejectPrivateOrInvalid`) ile yerel ağ ve özel IP istekleri engellenir.
- Çıktı tek ve katı bir JSON nesnesidir (`CareerOpsLivenessReceipt`).

### 13.3 İlan Metni Çıkarma (`browser-extract.mjs`) ve Kanonik Yükseltme
- `CareerOpsAdapter.extract_job(url)`: ATS API ve Playwright fallback ile ilan başlığı ve tam metnini çıkarır.
- Eğer mevcut `Opportunity` açıklaması taslak/boş ise (`len(desc) < 200`) ve çıkarılan metin yeterince zenginse (`len(text) >= 200`), metin `Opportunity.raw["description"]` alanına yazılır.
- `Entity.search_text` güncellenerek PostgreSQL unaccent/trgm arama indekslerine anında yansıtılır.
- Çıkarma meta verileri `OpportunitySourceObservation.enrichment["jd_extraction"]` içine kaydedilir ve `opportunity.updated` eventi loglanır.

### 13.4 Çok Kaynaklı Canlılık Birleştirme (`OpportunityListingService`)
- 24 saatlik önbellek (`enrichment["liveness"]`) ile gereksiz dış istekler engellenir (`force=True` ile atlanabilir).
- **Çoklu Kaynak Kuralı**: Bir ilan birden fazla kaynaktan (örn. hem `forkjob:rss` hem `careerops:greenhouse`) gözleniyorsa, en az BİR kaynak aktif kaldığı sürece kanonik ilan `active` kalır.
- **2 Aşamalı Güvenli Kapanma**: Tüm kaynaklar `expired` olduğunda ilk kontrolde `likely_closed` atanır. En az 12 saat sonra yapılan ikinci kontrolde de hepsi `expired` kalırsa `closed` ve `closed_at = now()` atanır.

### 13.5 İlan Kalitesi Teşhisi (`ListingHealthOut`)
`quick_signals()` fonksiyonu aday uyum puanına dokunmadan aşağıdaki 5 alt sinyali ve 0–100 arası kalite puanını hesaplar:
- `jd_completeness`: `complete` (>1000 kr), `concise` (300–1000 kr), `stub` (<300 kr).
- `salary_transparency`: `transparent` (belirgin aralık), `unclear` (tek sınır veya geniş aralık >%50), `missing`.
- `liveness_status`: `live`, `at_risk`, `expired`, `unchecked`.
- `repost_frequency`: `none`, `moderate` (2x), `frequent` (3+).
- `health_score`: Temel 100 üzerinden eksiklik cezaları düşülerek üretilen kalite puanı.

### 13.6 REST Uçları ve Kullanıcı Arayüzü
- `POST /api/opportunities/{id}/liveness?force=false`
- `POST /api/opportunities/{id}/extract-jd?force=false`
- `JobDetail.tsx`: İlan künyesi altında kalite rozeti, canlılık/maaş/açıklama etiketleri ve canlılık tazeleme / ilan metni çıkarma aksiyon butonları.

---

## 14. C3.1 Kanıt Doğruluğu ve Yaşam Döngüsü Kapanışı (Evidence Correctness & Lifecycle Closure)

C3.1 fazı, C3 ile gelen yeteneklerin kanıt zincirini, çalışma zamanı hazırlık kapılarını ve yaşam döngüsü uç durumlarını C4 LLM muhakemesi öncesinde kesinleştiren 10 ana denetim ve düzeltmeyi içermektedir:

### 14.1 Pinned Runtime Guard Kapsamı
- C3 yürütme yollarının tümü (`check_liveness`, `extract_job`, `detect_reposts`) alt süreç veya köprü çalıştırmadan önce `CareerOpsRuntimeGuard.ensure_ready()` üzerinden fail-closed kontrolden geçer.
- `detect_reposts()` geçici dosya projeksiyonu yapmadan önce gerekli betik (`detect-reposts.mjs`) varlığını ve sürüm kimliğini doğrular; kilit uyuşmazlığında sıfır alt süreç ve sıfır dosya yazımı güvence altındadır.

### 14.2 Playwright Modül Çözümlemesi ve Öksüz Süreç Koruması
- `bridges/liveness.mjs` içerisinde Playwright, forkOS veya keyfi çalışma dizinlerinden değil; `createRequire(pathToFileURL(resolve(checkoutDir, 'package.json')))` ile kesin olarak sabitlenmiş upstream checkout (`.vendor/career-ops`) içerisinden yüklenir.
- Playwright eksik olduğunda köprü çökmez; yapılandırılmış `no_playwright` / `uncertain` makbuzunu döner.
- Tarayıcı başlatıldığında `SIGINT` ve `SIGTERM` sinyal yakalayıcıları bağlanır; süreç kesilmelerinde veya zaman aşımlarında öksüz Chromium kalması engellenir.

### 14.3 Taze İkinci Onay ile Kapanma Semantiği
- `LIVENESS_CACHE_TTL = 24 saat` ve `LIVENESS_CLOSE_CONFIRMATION_INTERVAL = 12 saat` sabitleri tanımlanmıştır.
- Bir kaynak `likely_closed` durumundayken ve üzerinden en az 12 saat geçmişken, önbellekteki süresi dolmuş makbuz **asla ikinci onay yerine geçemez**. Bu durumda önbellek zorunlu olarak atlanır ve adapter'dan taze bir kontrol zorlanır.
- Aynı `checked_at` zaman damgasına sahip önbellek kaydının yeniden okunması veya `uncertain` sonucu ilanı kapatamaz (`likely_closed` kalır).
- Kaynak ancak taze ve farklı bir zamanda üretilmiş `expired` gözlemiyle `closed` durumuna geçebilir.

### 14.4 Zaman Damgası Ayrımı (Discovery vs Liveness)
- `OpportunitySourceObservation.last_seen_at` ve `Opportunity.last_seen_at` yalnızca yeni tarama/keşif sighting'leri tarafından güncellenir.
- Canlılık kontrolleri (`check_liveness`) bir keşif sighting'i **değildir**; bu nedenle asla `last_seen_at` veya `last_successful_seen_at` değerlerini değiştirmez.
- Kontrol zamanı yalnızca `enrichment["liveness"]["checked_at"]` içinde izole saklanır.

### 14.5 İlan Metni Kanıt Kaynağı (JD Provenance)
- Birden fazla kaynağa sahip ilanlarda metin çıkarma tetiklendiğinde `select_extraction_source` ile URL önceliklendirilir: (Kanonik URL -> Yetkili ATS -> Şirket Kariyer Sayfası -> İlk Gözlem).
- Çıkarma kanıtları (`source_url`, `requested_url`, `returned_url`, `method`, `jd_hash`, `jd_text_length`, `jd_title`, `promoted`, `promotion_reason`, `source_selection_reason`) **yalnızca çıkarmanın yapıldığı kaynağın** `enrichment["jd_extraction"]` alanına yazılır; diğer kaynakların meta verisi kirletilmez.

### 14.6 Veri Kaybı Olmayan İlan Metni Yükseltmesi (Non-Destructive JD Promotion)
- `normalize_jd_text()`, `compute_jd_hash()` ve `should_promote_jd()` ile güvenli yükseltme:
  - Mevcut açıklama boş veya taslak ise (<200 karakter) ve çıkarılan metin >=200 karakter ise yükseltilir.
  - Mevcut açıklama zenginse (örn. 10.000 karakter), yeni çıkarılan metin daha fakir ise (örn. 400 karakter), `force=True` olsa dahi mevcut açıklama ezilmez (`REJECT_POORER_THAN_EXISTING`).
  - Çıkarılan metin mevcut açıklamayla aynı normalize hash'e sahipse veritabanı yazımı ve event tetiklemesi atlanır (`IDENTICAL_HASH`).
  - Çıkarılan metin mevcut açıklamadan belirgin derecede daha zenginse (en az 1.5 kat ve en az 300 karakter daha uzun) yükseltilir.
- **Değerlendirme Eskime Koruması**: İlan metninin maddi değişimi `listing_fingerprint` değerini değiştirir ve C4 değerlendirmesini eskitir (`stale`). Fakir olduğu için reddedilen çıkarmalar ise fingerprint'i korur ve sahte eskimeyi önler.

### 14.7 Yetenek Bağlamı, Repost Bağımsızlığı ve Doctor Mutabakatı
- `CareerOpsCapabilityContext` ve `CapabilityStatus.DEGRADED` durumu eklendi.
- `job.repost_analysis` betiği (`detect-reposts.mjs`) tarayıcı gerektirmediğinden, çekirdek çalışma zamanı hazır olduğunda `browser_ready` değerinden bağımsız olarak `SUPPORTED` döner.
- `job.legitimacy`, forkOS içindeki deterministik `ListingHealthOut` sinyalleri ve risk kuralları ile karşılandığından resmi olarak `SUPPORTED` ilan edilmiştir.
- `discovery.liveness` ve `job.extract`, Playwright eksik olduğunda `DEGRADED` (API katmanı aktif, tarayıcı fallback'i devre dışı), Playwright hazır olduğunda `SUPPORTED` döner.
- `CareerOpsDoctor.capabilities_available`, adapter'ın `status == CapabilityStatus.SUPPORTED` dönen yetenek sayısıyla tüm ortam koşullarında (tarayıcılı, tarayıcısız, entegrasyon kapalı) %100 mutabıktır.

### 14.8 SSRF Derinlemesine Savunma ve Repost İzolasyonu
- `_is_safe_http_url()` ile `ipaddress` kütüphanesi üzerinden loopback (`127.0.0.1`), özel ağ (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), bulut metadata IP'leri (`169.254.169.254`) ve geçersiz hostlar alt süreç çağrılmadan önce engellenir.
- `detect_reposts()` her çağrı için benzersiz `repost_scratch/<scratch_id>/data/scan-history.tsv` dizini oluşturur, `CAREER_OPS_ROOT` olarak bu geçici dizini verir ve eşzamanlı çalıştırmalarda birbirinin verisini kirletmez. İşlem sonunda `finally:` bloğunda tüm geçici dosyalar ve dizinler temizlenir.

### 14.9 Olay Semantiği ve Yeniden Açılma
- Önceden `closed` veya `likely_closed` olan bir kaynağın canlılık kontrolünde `active` dönmesi durumunda `opportunity.source_reopened` eventi fırlatılır ve `closed_at` temizlenir.
- Kaynak durumu değiştiğinde `opportunity.source_status_changed` eventi yalnızca gerçek durum geçişlerinde tetiklenir.
