# forkOS × career-ops Entegrasyonu (C1: Temel & Doctor, C2: Keşif & Sağlayıcı Füzyonu)

Bu doküman, `career-ops` projesinin forkOS içerisine **sürüm-sabitli iç yetenek motoru** (version-pinned internal capability engine) olarak nasıl entegre edildiğini, hakikat sınırlarını, C1.1 çalışma zamanı güvenlik sertleştirmelerini ve C2 iş keşfi (Discovery & Provider Fusion) mimarisini tanımlar.

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
| **C3** | İlan Zenginleştirme ve Yaşam Döngüsü | `FUTURE` | JD extraction, repost tespiti, liveness kontrolleri |
| **C4** | Derin Değerlendirme ve Skorlama | `FUTURE` | A-H çok boyutlu uyum raporları, risk analizleri |
| **C5** | Başvuru Hazırlığı ve Hermes Orkestrasyonu | `FUTURE` | CV/ön yazı stratejisi, başvuru paketi üretimi |
