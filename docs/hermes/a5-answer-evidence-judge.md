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
mekanik uygunluk kontrolü
           ↓
sınırlandırılmış H3 kanıt getirme
           ↓
anlık görüntü bağlama (snapshot binding)
           ↓
anlamsal yargı (semantic judgment)
           ↓
kaynak yeniden doğrulama (revalidation)
           ↓
danışmanlık sonucu (advisory result)
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
2. **Çıkarım Sırasında Mutasyon Tespiti (Post-Call Revalidation):**
   Model çıkarımı tamamlandıktan sonra (özellikle 500-3000 ms sürebilen yerel NLI işlemleri sırasında) kaynakların disk veya veritabanındaki durumları tekrar kontrol edilir.
   Eğer çıkarım sürerken kaynak dosyası değiştirilmişse (`mtime_ns` veya `content_hash` uyuşmazlığı) ya da veritabanı varlığı güncellenmişse (`updated_at` / `revision` değişimi), modelin ürettiği semantik hüküm çöpe atılır; durum `stale` / `degraded` yapılır ve `effective_support: uncertain` döner (`SOURCE_MUTATED` / `SOURCE_STALE`).

### 2.2 Zaman Semantiği (Temporal Semantics)

> **Tarihsel bir olayın gerçekleşmiş olması, o olayın şu anki güncel durum olduğu anlamına gelmez.**

Geçmişe ait bir event kaydı (`event`) veya eski bir not satırı, bir durumun geçmişte var olduğunu kanıtlayabilir; ancak güncel kanonik varlık (`entity`) farklı bir duruma işaret ediyorsa, model bu çelişkiyi veya güncel durumu `contradicted` ya da `insufficient` olarak ele almalıdır.

---

## 3. Giriş ve Bütçe Sınırları

- **Açık İddia (`claim`):** İstemci tarafından sağlanır (maksimum 1000 karakter, minimum 2 karakter). Boş veya çok kısa metinler doğrudan reddedilir (`EMPTY_CLAIM`).
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
- **Genişletilmiş Çalışma Seti (`answer_runtime_v1.json`):** 24 senaryo (12 dev, 12 holdout), SHA-256 `2394d8519e4cea8ae0af35463d834baa94108d9fac34fa26826b8a9539dc9190`. Negasyon, kapsam uyumsuzluğu, zamansal kayma, kısmi örtüşme ve bağlam eksikliği gibi zorlayıcı durumları kapsar.
- **Değerlendirme Betiği:** `backend/scripts/eval_a5_answer.py` doğruluk, macro-F1, supported precision/recall, yanlış-destek oranı (`false_supported_rate`), çelişki yakalama ve gecikme metriklerini raporlar.

---

## 7. MCP Arayüzü

A5.3, ajan ekosistemine `forkos_answer_judge` salt-okunur aracıyla açılır:
- **Argümanlar:** `claim: str` (zorunlu), `scope: "all" | "vault" | "canonical"` (isteğe bağlı), `mode: "off" | "shadow" | "assist" | "on"` (isteğe bağlı).
- **Anotasyonlar:** `readOnlyHint=true`, `destructiveHint=false`, `idempotentHint=true`, `openWorldHint=false`.
- **Dönüş:** `AnswerJudgeResponse` (durum, hüküm, gerekçe, kanıt anlık görüntüleri ve izlenebilirlik metadata'sı).
