# Hermes Anlamsal Terfi ve Kalıcı Hafıza (A4)

A4; epizodik ve kanonik sinyallerden türetilen kalıcı bilgi adaylarını epistemik kalitesini kaybetmeden doğru kanonik sahibe yönlendiren ve yalnızca doğrulanmış / kullanıcı tarafından onaylanmış durumda kalıcı anlamsal bilgiye dönüştüren terfi hattıdır.

```text
episodic / canonical signals
        ↓
evidence classification (explicit_user, canonical_source, episode_derived, model_derived)
        ↓
ownership routing (forkOS, H2, f0rknbrain 30 Knowledge/Memory, procedural)
        ↓
human review & mechanical gates
        ↓
controlled promotion & A2/H3 integration
```

A4; yeni bir hafıza veritabanı, ikinci beyin çalışma zamanı, otomatik bellek yargıcı veya kanonik gerçeklik sahibi DEĞİLDİR. Bir aday oluşturma, kanıt sınıflandırma, sahiplik yönlendirme, inceleme ve denetimli terfi boru hattıdır.

---

## 1. Amaç (Purpose)

Hermes oturumlarında (A3) ve günlük operasyonlarda üretilen geçici gözlemlerin, kullanıcı tercih ve düzeltmelerinin ("Windows değil macOS varsay", "Türkçe casual cevap ver", vb.), mimari ve proje kararlarının unutulmaması gerekir. Ancak bu bilgilerin ham transkriptler halinde yığılması veya model çıkarımlarının körlemesine "gerçek" kabul edilerek veritabanına yazılması epistemik bozulmaya (hallucination drift, context pollution, privacy leak) yol açar.

A4'ün amacı:
1. Bilgi adaylarını yapılandırılmış biçimde yakalamak (`agent_semantic_candidate`).
2. Bilginin kanıt kökenini dürüstçe sınıflandırmak (`evidence_class`).
3. Bilginin ait olduğu doğru kanonik sistemi seçmek (`destination_routing`).
4. Güvenli, revizyon korumalı ve insan tarafından düzenlenebilir kalıcı kartlar üretmek (`30 Knowledge/Memory/<uuid>.md`).
5. Aktif kalıcı bilgileri A2 önyükleme bağlamına (`BootstrapIdentity`) ve H3 kanıt aramasına güvenle entegre etmek.

---

## 2. Sorumluluk ve Mülkiyet Sınırları (Ownership)

forkOS mimarisinde kanonik mülkiyet değişmezdir:

| Katman | Sahiplik Alanı | Kanonik Depolama |
|---|---|---|
| **Çalışma / Muhakeme** | Hermes aktif oturumu ve anlık akıl yürütmesi | Geçici istemci belleği |
| **Epizodik** | A3 oturum devri ve kapanış özetleri | `agent_session_episode*` tabloları |
| **Operasyonel** | Görevler, projeler, son tarihler, kariyer, aktiviteler, yürütme planları | forkOS PostgreSQL domain tabloları |
| **Sıcak / Güncel Bağlam** | H2 küratörlü, anlık önemli kişisel bağlam | `90 Agent/Memory/*.md` |
| **Kalıcı Anlamsal Bilgi** | f0rknbrain dayanıklı insan bilgisi, tercihler, kararlar, düzeltmeler | `30 Knowledge/Memory/*.md` |
| **Prosedürel** | Ajan işletim sözleşmesi ve Hermes becerileri | `AGENTS.md`, Hermes Skills |
| **A4** | Aday akışı, sınıflandırma, inceleme ve terfi orkestrasyonu | `agent_semantic_candidate` (yalnızca iş akışı metadata'sı) |

### Temel Değişmez: İkinci Bir Hafıza Veritabanı Eklenemez
A4 projesine vektör veritabanı (Chroma, Qdrant vb.), grafik veritabanı (Neo4j, Graphiti vb.), SQLite hafıza kataloğu, Mem0/LangMem bağımlılığı veya PostgreSQL içinde kanonik "hafıza gerçekliği" tablosu EKLENMEZ. Kanonik dayanıklı anlamsal bilginin tek evi `f0rknbrain` kasasıdır.

---

## 3. Aday Doğruluk Değildir (Candidate != Truth)

`agent_semantic_candidate` tablosunda saklanan kayıtlar **kanonik gerçeklik değildir**. Bunlar:
- Henüz kullanıcı tarafından onaylanmamış veya doğrudan kanonik kaynakla kanıtlanmamış iddialardır.
- Modelin H4 (`consolidation_candidates_v1`) üzerinden metin parçalarından çıkardığı çıkarımlardır.
- Tekrarlanma sayısı (`recurrence_count`) ve destek referansları (`support_refs`) aday bazında birleşebilir; ancak bir adayın çok sık tekrarlanması onu kendiliğinden doğrulanmış gerçek yapmaz.
- Terfi etmemiş bir aday A2 önyüklemesine doğrudan enjekte edilmez ve H3 tarafından kanıt olarak gösterilmez.

---

## 4. Kanıt Sınıfları (Evidence Classes)

A4'te kanıt sınıfları birer **güven olasılık puanı** (örn. %87 doğru) DEĞİLDİR; bilginin epistemik kökenini (provenance) tanımlar:

| Kanıt Sınıfı | Tanım | Yetki Düzeyi | Terfi Politikası |
|---|---|---|---|
| `explicit_user` | Kullanıcının oturumda doğrudan ve açıkça söylediği beyan (transkript saklanmaz; kaynak rolü ve SHA-256 hash'i doğrulanır). | Kişisel beyanlar için en yüksek. | Mekanik kontrolleri geçerse `ready` olabilir. |
| `canonical_source` | forkOS operasyonel kaydı (Event, tamamlanmış Todo, yönetilen Vault notu). | Olgusal/durumsal gerçekler için yüksek. | Kaynak hâlâ güncelse `ready` olabilir. |
| `episode_derived` | A3 oturum devir öğelerinden veya mühürlü epizotlardan damıtılmış bilgi. | Orta/tarihsel. | Varsayılan `needs_review`; doğrudan otomatik terfi YOK. |
| `model_derived` | Modelin doğrudan desteklenmeyen genel çıkarımı veya genellemesi. | En düşük. | Varsayılan `needs_review`; doğrudan MCP terfisi kilitlidir (`SEMANTIC_REVIEW_REQUIRED`). |

### A3 `canonical_supported` Ayrımı
A3'teki `canonical_supported` sınıfı, ifadenin oturumda teslim edilmiş bir kaynakla eşleştiğini gösterir; ifadenin o kaynak tarafından tam olarak kanıtlandığını garanti etmez. Bu nedenle A3'ten gelen `canonical_supported` ifadeler A4'te körlemesine `canonical_source` yapılmaz; `episode_derived` olarak işlenir.

---

## 5. Gizlilik ve Transkript Saklamama Güvencesi (Privacy / No Transcript)

A4, forkOS'un temel gizlilik değişmezini korur:
1. **Ham Metin Depolanmaz:** `user_message`, `assistant_response`, `conversation_history`, `raw_prompt` veya `source_excerpt` alanları veritabanında ASLA kalıcılaştırılmaz.
2. **Geçici Doğrulama (Transient Validation):** A3'te tur işlenirken `source_excerpt`'in kullanıcı mesajında mı yoksa asistan yanıtında mı geçtiği mekanik olarak belirlenir. Yalnızca:
   - `source_role`: `"user"` | `"assistant"` | `"mixed"`
   - `evidence_digest`: `sha256("forkos-explicit-evidence-v1" + normalized_excerpt)`
   değerleri saklanır.
3. **Açık Gizlilik Vetosu (Semantic Memory Opt-Out):**
   Kullanıcı oturum içinde açıkça bellek kaydını reddettiğinde:
   - Türkçe: `"bunu hafızaya alma"`, `"bunu hatırlama"`, `"hafızaya kaydetme"`
   - İngilizce: `"don't remember this"`, `"do not store this as memory"`
   gibi yüksek güvenilirlikli kalıplar tespit edilirse o turun `semantic_memory_eligible` değeri `false` olur ve o turdan aday üretilmez. Bu durum "aday reddedildi" anlamına gelmez; aday hiç oluşturulmaz.
   - Genel ve muğlak ifadeler (`"boşver"`, `"forget it"`, `"kaydetme"`) yanlış pozitif üretmemesi için veto sayılmaz.
4. **Sır ve Kimlik Bilgisi Reddi:** Aday ifadesi, koşulları veya gerekçesi içinde API anahtarı, parola, token deseni tespit edilirse (`secret_safety.py`) işlem derhal reddedilir.

---

## 6. Aday İş Akışı (Candidate Workflow)

Adaylar `agent_semantic_candidate` tablosunda şu yaşam döngüsünü takip eder:

```text
[Signal: H5 consolidation; yalnız uygun A3 item'ları ve isteğe bağlı kanonik event'ler]
        ↓
  (ready veya needs_review)
        ↓
  Mekanik Kontroller
    ├── Kopya / Duplicate? ──────────→ (already_present / noop)
    ├── Gizlilik Vetosu? ────────────→ (aday oluşturulmaz)
    ├── Zayıf Kanıt / Çelişki? ──────→ (needs_review)
    └── Güçlü Kanıt (explicit_user)? ──→ (ready)
        ↓
  İnceleme (UI veya kısıtlı MCP)
    ├── Kullanıcı Onayı ─────────────→ (ready) → terfi → (promoted)
    ├── Kullanıcı Reddi ─────────────→ (rejected)
    └── Kaynak Bayatlaması ──────────→ (stale)
```

### Aday Kimliği (Deterministic Candidate Key)
Aday kimliği destek referanslarına bağımlı olmamalıdır; çünkü aynı iddia zamanla yeni kanıtlar toplayabilir.
```text
candidate_key = sha256(
    "v2:"
    + kind
    + ":" + (scope or "global")
    + ":" + (scope_project or "")
    + ":" + (subject_key or "")
    + ":" + normalize_for_matching(statement)
)
```
Aynı anahtara sahip yeni kaynak referansları geldiğinde yalnız açık adayların `recurrence_count` değeri artar ve yeni kanıt referansları birleştirilir. Eski v1 adayları, opt-out metadata'sı olmadığı için migration sırasında `stale` yapılır; yeniden canlandırılmaz.

---

## 7. Sahiplik Yönlendirmesi (Destination Routing)

A4'ün ilk sorusu "Bu bilgi hafıza mı?" değil, **"Bu bilginin kanonik sahibi kimdir?"** sorusudur.

```text
Aday Sinyali
    ├── commitment / action ──→ OPERATIONAL (forkOS: Todo, Project)
    ├── oturumluk açık hedef ──→ HOT_MEMORY (H2: 90 Agent/Memory)
    ├── identity / preference ─→ DURABLE_VAULT (f0rknbrain: 30 Knowledge/Memory)
    ├── explicit correction ───→ DURABLE_VAULT (+ gerekirse H2 sıcak bellek)
    ├── decision / lesson ─────→ DURABLE_VAULT (f0rknbrain: 30 Knowledge/Memory)
    ├── project knowledge ─────→ DURABLE_VAULT (f0rknbrain: 30 Knowledge/Memory)
    ├── system / prompt rule ──→ PROCEDURAL_CANDIDATE (Gelecek Sözleşme İncelemesi)
    └── trivial / noisy chat ──→ aday çıkarılmaz; kullanıcı ayrıca discard seçebilir
```

- **Operasyonel Yönlendirme:** A4 kendiliğinden doğrudan `Todo` veya `Project` tablosuna INSERT yapmaz. `suggested_destination = "operational"` işaretler; mevcut H1/H7 güvenli yürütme hattına havale eder.
- **Prosedürel Yönlendirme:** A4 `AGENTS.md` veya sistem promptlarını otomatik olarak DEĞİŞTİRMEZ. Yalnızca `procedural_candidate` etiketiyle kullanıcı incelemesine bırakır.

---

## 8. Kalıcı Kart Şeması (Durable Vault Card Schema)

Kalıcı anlamsal kartlar f0rknbrain içinde `30 Knowledge/Memory/` klasöründe tekil Markdown dosyaları olarak saklanır:
`30 Knowledge/Memory/<uuid>.md`

### Managed Frontmatter
```yaml
---
forkos_id: "550e8400-e29b-41d4-a716-446655440000"
forkos_type: note
forkos_note_kind: semantic_memory
forkos_created_at: "2026-09-23T15:00:00Z"
forkos_updated_at: "2026-09-23T15:00:00Z"
forkos_memory_kind: "correction"
forkos_memory_scope: "global"
forkos_memory_scope_id: null
forkos_memory_subject_key: "shell_platform"
forkos_memory_domains:
  - "development"
  - "cli"
forkos_memory_status: "active"
forkos_memory_observed_at: "2026-09-23T14:45:00Z"
forkos_memory_valid_from: "2026-09-23T14:45:00Z"
forkos_memory_valid_to: null
forkos_memory_evidence_class: "explicit_user"
forkos_memory_evidence_refs:
  - "episode:12"
forkos_memory_supersedes: []
forkos_memory_sensitivity: "normal"
forkos_memory_remote_allowed: false
---
```

### Gövde Biçimi (Human-Readable Body)
Gövde Obsidian içinde kolayca okunabilir ve düzenlenebilir olmalıdır:
```markdown
# macOS Terminal Ortamı Varsayımı

## İfade
Terminal ve betik komutlarında Windows/PowerShell değil macOS/zsh varsayarak komut ver.

## Koşullar
- Kullanıcı açıkça Windows ortamı belirtmediği sürece geçerlidir.

## Gerekçe
Kullanıcı geliştirme ortamını macOS olarak düzeltmiştir.
```
Yalnızca `## İfade` başlığı zorunludur; diğer bölümler opsiyoneldir.

---

## 9. H2 Sıcak Bellek ve Anlamsal Bellek Ayrımı (H2 vs Semantic Memory)

| Nitelik | H2 Sıcak Bellek (`90 Agent/Memory`) | A4 Anlamsal Bellek (`30 Knowledge/Memory`) |
|---|---|---|
| **Amaç** | Anlık, kısa vadeli, küratörlü çalışma bağlamı. | Dayanıklı, zamansal, kanıt temelli insan bilgisi. |
| **Kapsam** | H2 context paketi (`profile`, `preference`, `goal`, `constraint`, `decision`, `correction`). | Tüm anlamsal alanlar (`identity`, `preference`, `correction`, `decision`, `lesson`, `project_knowledge` vb.). |
| **H3 Kanıt Uygunluğu** | **HARİÇTİR** (kişiselleştirme kanıt sayılamaz). | **UYGUNDUR** (dayanıklı bilgi H3 aramasında kanıt olabilir). |
| **Ömür / Geçerlilik** | Aktif veya emekli (emeklilik silme değildir). | `valid_from`, `valid_to`, `supersedes` ile tam zamansallık. |

### H2'ye `correction` Eklenmesi
Düzeltmeler ("Windows değil macOS kullan") birinci sınıf vatandaş olduğundan, H2 `MemoryKindValue` türüne `correction` 6. tür olarak eklenir. Böylece anlık sıcak bağlamda da düzeltmeler öncelikli taşınır.

---

## 10. Zamansal Anlamsallık (Temporal Semantics)

Bir iddianın ne zaman gözlemlendiği ile ne zaman geçerli olduğu birbirinden farklıdır:
- `observed_at`: İddiayı destekleyen kanıtın tespit edildiği an.
- `valid_from`: İddianın geçerli olmaya başladığı bilinen an (bilinmiyorsa `observed_at` veya `null`).
- `valid_to`: İddianın geçerliliğini yitirdiği bilinen an (açık bir bitiş yoksa `null`). Uydurma bitiş tarihi yazılmaz.

Bir kart yerine yenisi geçtiğinde (`supersedes`):
Eski kartın `valid_to` değeri otomatik yazılmaz veya uydurulmaz. Yeni aktif kart eski kartı açıkça `supersedes` ile işaretlediğinde okuma modeli eski kartı `superseded` olarak gösterir.

---

## 11. Geçersiz Kılma ve Çakışma Yönetimi (Supersession)

A4 anlamsal belleği **eklemeli (additive)** yönetir. Eski gerçekler veritabanından silinmez veya sessizce üzerine yazılmaz.

1. **Birebir Çift (Exact Duplicate):** Kapsam, tür, subject ve normalize ifade mevcut aktif bir kartla birebir aynıysa YENİ KART YAZILMAZ (`already_present`). Aday mevcut karta bağlanmış `promoted` durumuna geçer.
2. **Subject Key Yalnızca İpucudur:** Aynı `subject_key` değerine sahip olmak eski kartı geçersiz kılmak için yeterli DEĞİLDİR.
3. **Geniş Varlık Geçersiz Kılma Yasaktır:** "Kullanıcı Proje X hakkında konuştu" diye önceki tüm Proje X kartları emekli edilemez.
4. **Kullanıcı Onaylı Geçersiz Kılma:** Eski bir kartın yerine yenisinin geçmesi, ancak kullanıcının açıkça seçtiği `supersedes_card_id` ile mümkündür. Yeni kartın `forkos_memory_supersedes` listesine eski kartın ID'si yazılır.
5. **Türetilmiş Efektif Durum:** Bir kartın intrinsic durumu `active` olsa dahi, daha yeni aktif bir kart onu `supersedes` ile referans veriyorsa kartın efektif durumu `superseded` olarak türetilir.

---

## 12. İnceleme ve Terfi Politikası (Review & Promotion)

A4 v1'de **tam otomatik kalıcı hafıza kartı yazımı YOKTUR**.

### Mekanik Kapılar (Mechanical Gates)
Terfi öncesinde şu kontroller zorunludur:
- Aday mevcut ve durumu tam olarak `ready` (onay ayrı bir durum değil, `ready` geçişidir).
- `expected_revision` adayın güncel revizyonu ile eşleşiyor (optimistic concurrency).
- Kanonik kaynak referansları geçerli, A3 turu semantic-memory-eligible ve varsa hedef proje/kaynak silinmemiş.
- Gizlilik vetosu yok.
- Secret safety kontrolü temiz (ifade içinde anahtar/şifre yok).
- Hedef Vault yazılabilir.
- Birebir aktif kopya varsa yeni dosya yazılmadan `already_present` döner.

### Zayıf Kanıt Koruması
`episode_derived` veya `model_derived` kanıt sınıfına sahip adaylar kullanıcı arayüzünden doğrudan onaylanmadıkça (`reviewed_by = "user"`) MCP write araçları üzerinden tek tıkla terfi ettirilemez (`SEMANTIC_REVIEW_REQUIRED`). Ajan kendi çıkarımını kendi kendine onaylayamaz.

---

## 13. A2 Bootstrap Entegrasyonu (A2 Integration)

Kalıcı hafıza kartları dosyada unutulmak için değil, Hermes'in sonraki oturumlarına yön vermek için vardır.

### Türetilmiş İnsan Profili (`SemanticProfile`)
Aktif ve geçerli kartlardan salt-okunur, sınırlı bir profil türetilir:
```text
Semantic Cards
      ↓ (filter: effective_status == 'active' & not expired)
SemanticProfile
      ├── corrections (en yüksek öncelik)
      ├── constraints
      ├── identity
      ├── goals
      └── preferences
```
Bu profil bağımsız bir `profile.json` dosyası değildir; kartların anlık indeks görünümüdür.

### A2 `_collect_identity()` İyileştirmesi
Mevcut durumda H2'den beslenen ve `explicit_corrections` alanı boş kalan `_collect_identity()` fonksiyonu, artık bu `SemanticProfile` görünümünden beslenir:
- `explicit_corrections`: aktif düzeltme kartları (en fazla 3).
- `durable_preferences`: aktif tercih kartları (en fazla 4).
- `long_running_goals`: aktif hedef kartları (en fazla 3).

### Kaynak Sürümleme ve Tazelik (Source Continuity)
A2 teslimatına eklenen her anlamsal kart `semantic_memory:<uuid>` biçiminde ve kart dosyasının SHA-256 revizyonuyla etiketlenir. Dosya elle veya terfiyle değiştiğinde, emekli edildiğinde veya yerine yenisi geçtiğinde A2 kaynak devamlılığı bunu algılayarak bayat bağlamı geçersiz kılar (`SOURCE_STALE`). A2'nin 4000 karakterlik genel tavanı korunur.

---

## 14. H0 / H3 Arama ve Kanıt Entegrasyonu (H0/H3 Integration)

- **H0 Arama:** `30 Knowledge/Memory` f0rknbrain'in normal bilgi ağacında yer aldığından, mevcut `brain_search` ve `brain_read` araçlarıyla güvenli ve engelsiz taranabilir.
- **H3 Kanıt Uygunluğu:** `is_evidence_path` kuralı `90 Agent/Memory` klasörünü dışlarken, `30 Knowledge/Memory` klasörüne tam erişim sağlar. Dolayısıyla dayanıklı anlamsal kartlar H3 kanıt sorgularında geçerli kanıt olarak döndürülebilir.
- **Kanıt Sınırı:** Bir kartın H3 kanıtı olarak sunulması, H3'ün o kartın arkasındaki tüm tarihsel kaynakları bağımsız olarak teyit ettiği anlamına gelmez; kartın kendisinin dayanıklı insan bilgisi olduğunu gösterir.

---

## 15. Hata ve Dayanıklılık Semantiği (Failure Semantics)

- **Fail-Open / Güvenli Başarısızlık:** Kasa erişilemez durumdaysa, aday üretimi başarısız olduysa veya yerel model (H4) kapalıysa, Hermes oturumu veya A1 yaşam döngüsü ASLA düşürülmez.
- **Dürüst Teşhis:** H4 kapalıysa uydurma aday üretilmez; refresh `0 aday` döner. A4 refresh yanıtı şu anda ayrıca `LOCAL_COGNITION_UNAVAILABLE` kodu taşımaz.
- **Yazma Atomikliği:** Dosya yazımları `O_EXCL` ve geçici dosya üzerinden atomik gerçekleştirilir; bozuk/yarım dosya oluşmaz.

---

## 16. Doğrulama ve Değerlendirme Seti (Evaluation)

A4'ün doğruluğu deterministik değerlendirme seti ile kilitlenir:
`backend/tests/fixtures/a4_semantic_eval_v1.json`

Set şu test durumlarını zorunlu olarak içerir:
1. **PromotionEval:** Açık tercih, düzeltme, karar, taahhüt ve oturumluk hedef için sahiplik/yönlendirme beklentileri.
2. **EvidenceEval:** `explicit_user`, `canonical_source`, `episode_derived`, `model_derived` doğru sınıflandırması.
3. **PrivacyEval:** `"bunu hafızaya alma"` ve varyantlarında A3 turunun uygunsuz işaretlenmesi ve A4 adayının hiç oluşmaması; olumsuz örneklerde yanlış veto verilmemesi.
4. **TemporalEval:** Eski tercihin yeni tercih ile ilişkisi ve zamansal geçerlilik türetimi.
5. **SupersessionEval:** Birebir kopyada noop; seçilen hedefte yerine geçme; alakasız varlık veya aynı proje bahsinde geçersiz kılmama.
6. **AbstentionEval:** Yetersiz veya şüpheli veride `needs_review` veya `stale` dönülmesi; kesinlik uydurulmaması.

---

## 17. Ertelenen Kapsamlar: A5 (Explicit A5 Deferrals)

Şunlar **A5 Yargı Katmanı** kapsamındadır ve A4'te KESİNLİKLE YAPILMAZ:
- Jev veya harici yargıç modelleri.
- Cross-encoder veya BGE reranker tabanlı anlamsal çelişki dedektörleri.
- Anlamsal çelişkiyi serbest LLM ile otomatik çözme.
- Cevap kanıtı yargıcı (Answer Evidence Judge) ve bağlam yargıcı (Context Judge).
- `OFF / SHADOW / ASSIST / ON` kademeli yargı çalışma zamanı.

---

## 18. Ertelenen Kapsamlar: A6 (Explicit A6 Deferrals)

Şunlar **A6 Brain Doctor** kapsamındadır ve A4'te KESİNLİKLE YAPILMAZ:
- Kapsamlı Brain Doctor tanılama motoru.
- Otomatik uzun vadeli bellek çöp toplama (retention garbage collector).
- Otomatik gizlilik kanaryası (canary suite).
- Otomatik bilgi sağlığı onarımı.
