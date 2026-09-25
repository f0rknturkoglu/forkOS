# forkOS × career-ops — C2: Discovery & Provider Fusion Spec

- **Tarih**: 2026-09-25
- **Faz**: C2
- **Amaç**: `career-ops` iç yetenek motorunun Ters ATS (Reverse ATS) iş keşif gücünü forkOS'a entegre etmek; kanonik hakikat sahipliğini, `Opportunity` tekil kimliğini, kaynak gözlemlerini (`OpportunitySourceObservation`) ve kapanma güvenliğini korumak.

---

## 1. Mimari Prensipler ve Hakikat Zinciri

```text
career-ops                     forkjob_core
 discovery                      discovery
    │                               │
    └───────────────┬───────────────┘
                    ▼
          forkOS Ingestion (`ingest_jobs`)
                    │
                    ▼
             Canonical Dedup
                    │
                    ▼
           Kanonik Opportunity (PostgreSQL)
                    │
       ┌────────────┴────────────┐
       ▼                         ▼
OpportunitySourceObservation  OpportunitySourceObservation
 (jobhunter:greenhouse:...)       (careerops:greenhouse)
```

1. **Tek Bir İş Evreni**: Kullanıcı arayüzünde "forkOS jobs", "career-ops jobs" ayrımı olamaz. Her iki motor da aynı kanonik `Opportunity` havuzunu besler.
2. **Kanonik Durum Sahibi**: Yalnızca `forkOS PostgreSQL`. career-ops'un `data/pipeline.md`, `applications.md`, `applications.db` veya `scan-history.tsv` dosyaları kanonik durum değildir ve normal çalışma esnasında kullanılmaz (`--dry-run` zorunludur).
3. **Orkestratör**: Hermes. career-ops'a doğrudan veya kabuk seviyesinde keyfi erişimi yoktur.
4. **Tek Yönlü Projeksiyon**: forkOS arama ve hedefleme yapılandırması (`config.yaml`), `portals.yml` formatında geçici çalışma alanına (`backend/data/runtime/career-ops/portals.yml`) tek yönlü yansıtılır. Bu dosya tek kullanımlık ve harcanabilirdir.

---

## 2. Lane Değerlendirmesi

### Lane A: Ters ATS Keşfi (`scan-ats-full.mjs`) — AKTİF
- **Sözleşme**: `--json --dry-run --ats <provider> --since <days>` ile çağrılır.
- **Çıktı**: `stdout` üzerinde tek ve eksiksiz bir JSON nesnesi üretir (`offers[]` içinde `company`, `title`, `url`, `location`, `postedAt`, `dateStatus`, `source`).
- **Sağlayıcılar**: `greenhouse`, `lever`, `ashby`, `workday`, `icims`, `bamboohr`.
- **Durum**: `discovery.reverse_ats` yeteneği **SUPPORTED** olarak etkinleştirilir.

### Lane B: Küratörlü Tarama (`scan.mjs`) — ERTELENDİ / UNAVAILABLE
- **Bulgu**: `scan.mjs --json` çıktısı yalnızca `added_urls: string[]` üretmekte; iş ilanının unvanı, şirketi, yayın tarihi ve konumu gibi alanları makine formatında sunmamaktadır.
- **Kural**: Konsol çıktısını regex ile kazımak, markdown taramak veya upstream kodunu değiştirmek kesinlikle yasaktır.
- **Durum**: `discovery.scan` yeteneği dürüstçe **UNAVAILABLE** bırakılır; ileride bir köprü sözleşmesi geliştirilene kadar ertelenir.

---

## 3. Bileşen Mimarisi

### 3.1. Hedefleme Projeksiyonu (`CareerOpsDiscoveryConfigBuilder`)
- **Modül**: `backend/app/integrations/career_ops/targeting.py`
- **Girdi**: `backend/data/config.yaml` içindeki `role_terms`, `skills`, `kill_words`, `seniority_tiers`.
- **Çıktı**: `runtime_dir / "portals.yml"`.
- **Güvenlik Koruyucusu (Section 18)**: Pozitif anahtar kelime listesi boşsa tarama başlatılamaz; on binlerce ilgisiz ilanın içeri akması engellenir.

### 3.2. Subprocess Runner Genişletmesi
- **Modül**: `backend/app/integrations/career_ops/runner.py`
- **Allowlist**: `ALLOWED_SCRIPTS = frozenset({"doctor.mjs", "scan-ats-full.mjs"})`.
- **Ortam Güvenliği**: Yalnızca minimum gerekli ortam aktarılır; `CAREER_OPS_PORTALS` geçici yansıtılmış dosyaya işaret eder. Hiçbir LLM veya bulut kimlik bilgisi aktarılmaz.
- **Akış Sınırları**: `stdout` ve `stderr` için güvenli streaming devam eder; keşif çıktılarının büyüklüğüne uygun olarak arabellek tavanı yükseltilebilir (varsayılan 2MB).

### 3.3. Adapter Keşif API'si
- **Modül**: `backend/app/integrations/career_ops/adapter.py`
- **Metot**: `async def reverse_scan(self, provider: str, *, since_days: int = 7, limit: int | None = 200, include_undated: bool = False) -> CareerOpsDiscoveryResult`
- **Doğrulama**:
  - `provider` izin verilen 6 sağlayıcıdan biri olmalıdır.
  - `since_days` 1 ile 90 arasında olmalıdır.
  - `limit` 1 ile 10.000 arasında olmalıdır.

### 3.4. forkOS Kaynak Adaptörleri (`CareerOpsReverseSource`)
- **Modül**: `backend/app/sources/career_ops_sources.py`
- **Kaynak Kimlikleri**:
  - `careerops:greenhouse`
  - `careerops:lever`
  - `careerops:ashby`
  - `careerops:workday`
  - `careerops:icims`
  - `careerops:bamboohr`
- **Sınıf**: `SourceClass.SLOW_OPTIN` (otomatik genel yenilemeye girmez; yalnızca manuel veya açıkça planlandığında çalışır).
- **Kısmi Başarı Mantığı**: `stoppedByOutage`, veri seti hatası veya yüksek erişilemeyen pano durumunda `FetchOutcome(partial=True, detail=...)` üretilir.

### 3.5. Kapanma Taraması Muafiyeti (No-False-Closure Invariant)
- **Modül**: `backend/app/modules/opportunity/worker.py`
- **Kural**: Ters ATS taramaları filtrelenmiş ve pencereye bağlıdır. Önceki koşuda görülen bir ilanın yeni ters taramada çıkmaması ilanın kapandığını kanıtlamaz.
- **Uygulama**: `_sweep_missing()` fonksiyonu `careerops:*` kaynakları için **asla çağrılmaz**.

### 3.6. Kanonik Birleşme ve Gözlem Modeli
- İlanlar `CareerOpsDiscoveredJob` -> `RawItem` -> `ingest_jobs()` hattından geçer.
- Tekil URL veya normalize edilmiş URL eşleştiğinde mevcut `Opportunity` güncellenir; yeni bir kayıt açılmaz.
- `OpportunitySourceObservation` kaydı `source="careerops:<provider>"` olarak eklenir veya güncellenir.
- Mevcut `jobhunter:*` kaynakları ile tam uyum ve çakışma (overlap) korunur.

---

## 4. Test Stratejisi

1. **Birim / Adapter Testleri (`test_career_ops_discovery_adapter.py`)**:
   - Geçerli JSON çıktılarının ayrıştırılması.
   - Bilinmeyen sağlayıcı, geçersiz argüman reddi.
   - Bozuk JSON / eksik alan fail-closed davranışı.
   - Kısmi sonuç (`stoppedByOutage`, `datasetStatus` != "ok") `FetchOutcome(partial=True)` üretimi.
2. **Kanonik Birleşme ve Güvenlik Testleri (`test_career_ops_discovery_integration.py`)**:
   - `jobhunter:greenhouse` ile eklenmiş bir ilanın `careerops:greenhouse` ile tekrar gelmesi durumunda `Opportunity` sayısının 1 kalması ve 2 ayrı `OpportunitySourceObservation` oluşması.
   - Aynı career-ops taramasının ardışık çalışmasında idempotentlik.
   - **Kapanma Güvenliği**: Önceki taramada eklenen ilanın bir sonraki taramada çıkmaması durumunda ilanın durumunun `closed` veya `missing`e düşürülmediğinin kanıtlanması.
   - **Dosya Sistemi / Durum İzolasyonu**: Runtime dizini silinse dahi kanonik PostgreSQL fırsatlarının korunduğunun doğrulanması.
3. **Canlı Duman Testi (`test_career_ops_discovery_live.py`)**:
   - Pinned `.vendor/career-ops` motoru üzerinden küçük bir gerçek sağlayıcı testi (`--limit 2 --since 3`).

---

## 5. Başarı ve Kabul Kriterleri (C2 Checklist)
- [x] C1.1 tamamlandı ve pushlandı.
- [ ] `scan-ats-full.mjs` allowlist'e eklendi; keyfi scriptler engelli.
- [ ] `discovery.reverse_ats` etkinleştirildi; `discovery.scan` dürüstçe UNAVAILABLE bırakıldı.
- [ ] 6 reverse ATS sağlayıcısı `careerops:*` olarak modellendi.
- [ ] `config.yaml` disposable `portals.yml` projeksiyonu oluşturuyor.
- [ ] JSON çıktısı sıkı Pydantic modelleriyle ayrıştırılıyor; konsol regex kazıma yok.
- [ ] Normal entegrasyon `--dry-run` kullanıyor; upstream tracker dosyaları noncanonical.
- [ ] Kanonik birleşme testi geçiyor (forkjob + career-ops = 1 Opportunity, çoklu gözlem).
- [ ] `_sweep_missing` muafiyeti (no-false-closure) kanıtlandı.
- [ ] `slow_optin` sınıflandırması genel döngüyü koruyor.
- [ ] Tüm regresyon testleri geçiyor.
- [ ] `origin/main`e push yapıldı.
