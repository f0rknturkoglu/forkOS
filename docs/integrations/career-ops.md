# forkOS × career-ops Entegrasyonu (C1/C1.1: Entegrasyon Temeli, Sürüm Sabitleme ve Doctor)

Bu doküman, `career-ops` projesinin forkOS içerisine **sürüm-sabitli iç yetenek motoru** (version-pinned internal capability engine) olarak nasıl entegre edildiğini, hakikat sınırlarını ve C1.1 çalışma zamanı güvenlik sertleştirmelerini tanımlar.

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
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "name": "career-ops",
  "repository": "https://github.com/career-ops-hq/career-ops",
  "pinned_version": "1.34.0",
  "pinned_commit": "6326eb5d3804e8cb20d28acd5701a4e603a301f9",
  "required_node_min": "18.0.0",
  "recommended_node_min": "22.5.0"
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

C1/C1.1 aşamasında yalnızca `foundation.doctor` aktiftir; diğer yetenekler bildirilmiş ancak henüz implemente edilmediği için `unavailable` raporlanır.

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
2. **Kilit Dosyasını Güncelle**: `backend/app/integrations/career_ops/upstream.lock.json` içindeki `pinned_version` ve `pinned_commit` değerlerini güncelle.
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
