# A5.3 — Answer Evidence Judge (deneysel, yerel poorjev/NLI)

Answer Evidence Judge, forkOS ekosisteminde verilen açık bir iddia (*claim*) ile sistemden getirilmiş kanıtlar (*evidence*) arasındaki anlamsal ilişkiyi değerlendiren **salt-okunur danışmanlık** servisidir.

A5.3 tek bir dar soruyu yanıtlar:

> Açıkça verilmiş bir iddia ve forkOS üzerinden getirilmiş kanıtlar ışığında, bu kanıtlar iddiayı ne kadar güçlü destekliyor?

İzin verilen anlamsal çıktılar:
- `supported`: Kanıt iddiayı doğrudan ve yeterli düzeyde doğrular.
- `contradicted`: Kanıt iddiayla açıkça çelişir veya yanlışlar.
- `insufficient`: Kanıt iddia edilen konuyla ilgilidir ancak iddiayı doğrulamak veya yanlışlamak için yetersizdir.
- `uncertain`: Kanıt eksik, belirsiz, parçalıdır ya da model güvenilir bir çıkarım yapamaz (fail-closed varsayılan).

---

## 1. Kapsam Dışı ve Kesin Olmayan Roller (Non-Goals)

Answer Evidence Judge:
- **Bir gerçeklik oraklı (fact oracle) DEĞİLDİR.** Dünyadaki mutlak doğruları bilmez; yalnızca sunulan kanıt metnini iddia ile karşılaştırır.
- **Bir doğruluk veritabanı (truth database) DEĞİLDİR.** İddiaları veya hükümleri kalıcı bir tabloda indekslemez veya saklamaz.
- **Bir halüsinasyon güvenlik duvarı (hallucination firewall) DEĞİLDİR.** İstemcinin veya dil modelinin cevabını engellemez, susturmaz veya filtrelemez.
- **Bir cevap yeniden yazıcısı (response rewriter) DEĞİLDİR.** İddiayı düzeltmez, yeniden formüle etmez veya zenginleştirmez.
- **Otomatik bir iddia çıkarıcısı (automatic claim extractor) DEĞİLDİR.** Serbest metinden veya konuşmadan kendi kendine iddia türetmez; iddia çağırıcı tarafından açıkça verilmelidir.
- **Bir cevap engelleyicisi (answer blocker) DEĞİLDİR.** Yanıt üretimi akışını durdurmaz; yalnızca danışmanlık (`advisory`) metadata'sı üretir.
- **Bir kanonik durum yazıcısı (canonical state writer) DEĞİLDİR.** PostgreSQL'e veya Vault'a tek bir bayt dahi yazmaz.

---

## 2. Mimari ve Boru Hattı

A5 mimarisinin temel ilkesi korunur:

```text
mekanik uygunluk kontrolü (claim length >= 2)
           ↓
sınırlandırılmış H3 kanıt getirme
           ↓
anlık görüntü bağlama (pre-call snapshot binding)
           ↓
sağlayıcı anlamsal çıkarımı (poorjev/NLI)
           ↓
kriptografik provenance doğrulaması (claim + evidence + question digest)
           ↓
kaynak yeniden doğrulama (post-call source revalidation)
           ↓
danışmanlık sonucu (advisory result, default OFF / SHADOW)
```

Asla:
```text
model → mutlak doğru
```
veya
```text
iddia → kanonik kayıt
```
ilişkisi kurulamaz.

### 2.1 İki Katmanlı Koruma ve Yarış Koşulu Güvenliği

1. **Ön-Çıkarım Anlık Görüntüleme (Snapshot Capture & Binding):**
   H3 üzerinden getirilen her kanıt parçası (`AnswerEvidenceItem`) için bir `SourceSnapshot` yakalanır:
   - Kaynak türü (`vault`, `entity`, `event`),
   - İlgili kaynak ID'si,
   - `content_hash` (SHA-256),
   - `mtime_ns` / `source_revision`.
2. **Kriptografik Provenance Bağlama ve Doğrulama (A5.3.1):**
   Sağlayıcıdan dönen `AnswerJudgeProvenance` bağımsız olarak orkestrasyon tarafından denetlenir:
   - `expected_claim_digest == answer_claim_digest(request.claim)`
   - `expected_evidence_digest == answer_evidence_digest(request.evidence)`
   - `provenance.question_version == "a5-answer-questions-v1"`
   - `provenance.question_hash == QUESTION_HASH`
   - Pinned Model Kimliği ve Revizyonu: `MoritzLaurer/deberta-v3-base-zeroshot-v2.0` (`8e7e5af5983a0ddb1a5b45a38b129ab69e2258e8`).
   Herhangi bir digest veya üstveri uyuşmazlığında, ya da provenance eksikliğinde yanıt doğrudan `status: invalid`, `effective_support: uncertain` olarak reddedilir (`ANSWER_JUDGE_INVALID_RESPONSE`).
3. **Çıkarım Sırasında Mutasyon Tespiti (Post-Call Revalidation):**
   Model çıkarımı tamamlandıktan sonra kaynakların disk veya veritabanındaki durumları tekrar kontrol edilir.
   Eğer çıkarım sürerken kaynak dosyası değiştirilmişse (`mtime_ns` veya `content_hash` uyuşmazlığı) ya da veritabanı varlığı güncellenmişse (`updated_at` / `revision` değişimi), modelin ürettiği semantik hüküm çöpe atılır; durum `stale` / `degraded` yapılır ve `effective_support: uncertain` döner (`SOURCE_MUTATED` / `SOURCE_STALE`).

### 2.2 Zaman Semantiği (Temporal Semantics)

> **Tarihsel bir olayın gerçekleşmiş olması, o olayın şu anki güncel durum olduğu anlamına gelmez.**

Geçmişe ait bir event kaydı (`event`) veya eski bir not satırı, bir durumun geçmişte var olduğunu kanıtlayabilir; ancak güncel kanonik varlık (`entity`) farklı bir duruma işaret ediyorsa, model bu çelişkiyi veya güncel durumu `contradicted` ya da `insufficient` olarak ele almalıdır.

---

## 3. Giriş ve Bütçe Sınırları

- **Açık İddia (`claim`):** İstemci tarafından sağlanır ($2 \le \text{karakter} \le 1000$). Boş, tek karakterlik veya 1000 karakterden uzun metinler doğrudan reddedilir (`ANSWER_JUDGE_INVALID_CLAIM`).
- **Çağırıcı Kanıt Sağlayamaz:** İstemci dışarıdan kanıt metni enjekte edemez. Kanıtlar yalnızca forkOS içindeki H3 motoru (`retrieve_evidence`) üzerinden sistem tarafından toplanır.
- **H3 Sorgu Türetimi (`derive_h3_query`):** Orijinal iddiayı mutasyona uğratmadan, ilk 2..200 karakter arasındaki sözcük sınırından güvenli bir arama sorgusu türetilir.
- **Kanıt Öğeleri Sayısı:** En fazla 8 kanıt öğesi (`max_evidence_items <= 8`).
- **Öğe Başına Metin Sınırı:** En fazla 1000 karakter (`max_chars_per_item <= 1000`).
- **Toplam Alıntı Bütçesi:** Tüm kanıt parçalarının toplam uzunluğu 8000 karakteri aşamaz (`total_excerpt_budget <= 8000`).

---

## 4. Sağlayıcı ve Yerel Çevrimdışı Çalışma

- **Sağlayıcı:** `poorjev-local-nli` (Upstream poorjev 0.1.0 sözleşmesi).
- **Model:** `MoritzLaurer/deberta-v3-base-zeroshot-v2.0` (HF revision `8e7e5af5983a0ddb1a5b45a38b129ab69e2258e8`).
- **Soru / Hipotez Şablonu:** `a5-answer-questions-v1`, SHA-256 hash: `fe04928f17c91038629a8186ecc2fb7753838b3b442da3141b91f3148ccda2cf`.
- **Eksik Bağlam Koruması (`context_complete=False`):** Eğer kanıt toplama aşamasında eksiklik tespit edilmişse (`context_complete=False`), model asla kesin `supported` veya `contradicted` dönemez; güvenli biçimde `uncertain` (`context_incomplete`) döner.
- **Çevrimdışı Zorunluluğu:** `TRANSFORMERS_OFFLINE=1` ve `HF_HUB_OFFLINE=1`. İstek sırasında model indirme veya dış ağa çıkma kesinlikle yasaktır (0 HTTP, 0 DNS).

---

## 5. Çalışma Modları (Operating Modes)

1. **`off` (Varsayılan):** Answer Judge çağrılmaz veya mekanik temel seviyede `disabled` döner.
2. **`shadow` (Önerilen Operasyonel Mod):** Model çıkarımı çalıştırılır, gecikme ve metrikler gözlemlenir; ancak `effective_support` her zaman `uncertain` olarak maskelenir (sıfır operasyonel yetki).
3. **`assist`:** Danışmanlık çıktısı istemciye verilir; inceleme bayrakları eklenir ancak hiçbir otomatik karar alınmaz.
4. **`on`:** Model çıktısı doğrulanmış olarak döner; yine de DB/Vault'a yazma yetkisi veya cevabı sansürleme yetkisi yoktur.

---

## 6. Değerlendirme ve Sentetik Kıyaslama (AnswerEvidenceEval)

- **Donmuş Kıyaslama (`answer_evidence_eval_v1.json`):** 12 dondurulmuş senaryo (SHA-256 `6de1b082e91c34d7f607999077caef2084d9dd514ac9093d056ca9825b718397`).
- **Genişletilmiş Çalışma Seti (`answer_runtime_v1.json`):** 24 senaryo (12 dev, 12 holdout), SHA-256 `2394d8519e4cea8ae0af35463d834baa94108d9fac34fa26826b8a9539dc9190`.

### 6.1 Deterministik Taban Metrikleri (BASELINE ONLY)

Herhangi bir ML modeli olmadan veya mekanik abstention durumunda fail-closed çalışan taban:

| Metrik | Frozen v1 (12) | Runtime Dev (12) | Runtime Holdout (12) | Combined (24) |
| :--- | :--- | :--- | :--- | :--- |
| **Accuracy** | 0.1667 | 0.0833 | 0.1667 | 0.1250 |
| **Macro-F1** | 0.0714 | 0.0385 | 0.0714 | 0.0556 |
| **Supported Precision** | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **Supported Recall** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **False Supported Sayısı** | 0 | 0 | 0 | 0 |
| **False Supported Oranı** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **Uncertain Oranı** | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **Medyan Gecikme** | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms |

### 6.2 Gerçek Yerel Model Metrikleri (`poorjev-local-nli` / DeBERTa-v3)

Apple Silicon / OrbStack üzerinde `forkos-api-memory:local` konteynerinde offline çalışan pinli modelin gerçek ölçümü:

| Metrik | Frozen v1 (12) | Runtime Dev (12) | Runtime Holdout (12) | Combined (24) |
| :--- | :--- | :--- | :--- | :--- |
| **Accuracy** | **0.5000** | 0.4167 | 0.1667 | 0.2917 |
| **Macro-F1** | **0.4810** | 0.2582 | 0.1833 | 0.2930 |
| **Supported Precision** | **1.0000** | 0.5000 | 0.0000 | 0.3333 |
| **Supported Recall** | **0.7500** | 0.6667 | 0.0000 | 0.4000 |
| **Contradiction Recall** | 0.5000 | 0.0000 | 0.2500 | 0.1429 |
| **Insufficient Recall** | 0.5000 | 0.6000 | 0.0000 | 0.3333 |
| **False Supported Sayısı** | **0** | **2** | **2** | **4** |
| **False Supported Oranı** | **0.0000** | 0.2222 | 0.2000 | 0.2105 |
| **Uncertain Oranı** | 0.1667 | 0.0000 | 0.3333 | 0.1667 |
| **Brier Skoru** | 0.3097 | 0.2872 | 0.2945 | 0.2909 |
| **Medyan Gecikme** | 326.5 ms | 331.5 ms | 329.5 ms | 330.5 ms |
| **p95 Gecikme** | 1910 ms (soğuk) | 362 ms | 344 ms | 357.5 ms |
| **Sağlayıcı Hataları** | 0 | 0 | 0 | 0 |

### 6.3 False-Supported Analizi ve Model Kalitesi

Model donmuş temel sette (`frozen_v1`) sıfır yanlış-destek üretmiş (`false_supported = 0`) ve %100 supported precision göstermiştir. Ancak zorlu çalışma setinde (`answer_runtime_v1`) toplam 4 adet yanlış-destekleme tespit edilmiştir:

1. `partial_compound_dev` (Dev):
   - **İddia:** "Atlas uses Rust and PostgreSQL."
   - **Kanıt:** "Atlas uses Rust."
   - **Beklenen:** `insufficient` | **Model:** `supported` (güven: 0.3525)
   - **Hata Türü:** **Partial Evidence / Lexical Overlap** (Rust kısmını kanıtlayan metin yüzünden eksik kalan PostgreSQL bileşeni gözden kaçmıştır).
2. `narrow_condition_dev` (Dev):
   - **İddia:** "All Atlas microservices use Rust."
   - **Kanıt:** "Rust is used for Atlas CLI tooling."
   - **Beklenen:** `insufficient` | **Model:** `supported` (güven: 0.6345)
   - **Hata Türü:** **Scope Mismatch / Quantifier Overgeneralization** (Dar CLI kullanımından evrensel mikroservis kapsamı türetilmiştir).
3. `partial_compound_holdout` (Holdout):
   - **İddia:** "Atlas has 10 users and 5 admins."
   - **Kanıt:** "Atlas has 10 users."
   - **Beklenen:** `insufficient` | **Model:** `supported` (güven: 0.3341)
   - **Hata Türü:** **Partial Evidence / Lexical Overlap** (Kullanıcı sayısının doğrulanması yönetici sayısının yokluğunu gizlemiştir).
4. `scope_mismatch_holdout` (Holdout):
   - **İddia:** "Production database uses SQLite."
   - **Kanıt:** "Development sandbox uses SQLite."
   - **Beklenen:** `insufficient` | **Model:** `supported` (güven: 0.3106)
   - **Hata Türü:** **Scope Mismatch / Environment Confusion** (Geliştirme sandbox'ı ile canlı veritabanı kelime örtüşmesi sebebiyle karıştırılmıştır).

**Nihai Kalite Değerlendirmesi:**
Model basit atıf ve doğrudan kanıt içeren temel iddialarda başarılıdır (%75 recall). Ancak bileşik iddialarda eksik kalan parçaları ayıklamakta ve dar kapsamı geniş iddiaya genelleme eğilimindedir. Bu nedenle sağlayıcı kalitesi **DENEYSEL / ZAYIF** (`EXPERIMENTAL / WEAK`) olarak sınıflandırılır. Operasyonel kullanım için varsayılan **`off`** ve deneyler için **`shadow`** modu zorunludur.

---

## 7. MCP Arayüzü

A5.3, ajan ekosistemine `forkos_answer_judge` salt-okunur aracıyla açılır:
- **Argümanlar:**
  - `claim: str` ($2 \le \text{karakter} \le 1000$, zorunlu)
  - `retrieval_query: str | None` ($2 \le \text{karakter} \le 200$, isteğe bağlı)
  - `entity_id: str | None` (isteğe bağlı)
  - `scope: "all" | "operational" | "knowledge"` (isteğe bağlı)
  - `since: str | None`, `until: str | None` (isteğe bağlı)
  - `max_depth: int` ($0 \le d \le 2$, varsayılan 1)
  - `limit: int` ($1 \le l \le 15$, varsayılan 12)
- **Anotasyonlar:** `readOnlyHint=true`, `destructiveHint=false`, `idempotentHint=true`, `openWorldHint=false`.
- **Dönüş:** `AnswerJudgeResponse` (durum, hüküm, gerekçe, kanıt anlık görüntüleri ve izlenebilirlik metadata'sı).
