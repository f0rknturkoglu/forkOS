# forkOS — A1.1b + A2.1 Correctness & Completeness Pass Tasarım Belgesi

**Tarih:** 2026-09-22  
**Branch:** `main`  
**Hedef:** A1.1b invariant güçlendirmesi ve A2.1 doğruluk ve bütünlük tamamlama geçişi.  
**Kapsam Sınırı:** Yeni özellik genişletmesi değildir. A3/A4/A5 başlatılmayacaktır.

---

## 1. Mimari ve Korunan İlkeler

Mevcut tek yerel HTTP round-trip mimarisi korunur:

```text
Hermes pre_llm_call
         │
         ▼  (Tek Yerel HTTP Round-Trip)
POST /api/agent/lifecycle/turn
   ├── 1. A1 observe(session_start | turn_seen) -> Bağımsız commit
   └── 2. A2 compose(first_turn | later_turn)   -> Salt-okunur üretim (A1'den izole)
         │
         ├── İlk tur:  BootstrapPacketV1 (<forkos-context>)
         └── Sonraki:  Kaynak devamlılığı (<forkos-continuity>)

Hermes on_session_finalize
         │
         ▼
POST /api/agent/lifecycle/event (A1 finalize)
```

---

## 2. A1.1b — Tam Durum Parmak İzi (State Fingerprint) İnvariantı

### Problem
Mevcut `test_agent_lifecycle_invariants.py` yalnızca `func.count()` ile satır sayılarını karşılaştırıyor. Mevcut bir satır `UPDATE` edildiğinde satır sayısı değişmediği için sessizce test geçebilirdi.

### Çözüm
1. **18 Kanonik Model İçin Deterministik Parmak İzi:**
   - `entity`, `event`, `link`, `notification`, `todo`, `project`, `milestone`, `opportunity`, `application`, `bookmark`, `flashcard_card`, `pomodoro_session`, `review`, `proactivity_rule`, `proactivity_run`, `execution_plan`, `execution_receipt`, `execution_decision`.
   - Her tablo için satırlar Primary Key sırasına göre çekilir.
   - Sütunlar kararlı bir tuple/dict serileştirmesine dönüştürülür (tarihler, UUID'ler, JSON alanları normalize edilir).
   - Her tablo için bir SHA-256 özeti (`digest`) ve `row_count` hesaplanır.
2. **Kasa / Sıcak Bellek Dosya Parmak İzi:**
   - Kasa içindeki tüm Markdown dosyaları için `relative_path -> sha256(content)` haritası doğrulanır.
3. **Değişmezlik Doğrulaması:**
   - `session_start`, `turn_seen`, `session_finalize` ve mükerrer çağrılar sonrasında tüm özetler birebir eşit olmalıdır.
   - Yalnızca `agent_session` ve `agent_session_turn` tablolarının değiştiği doğrulanır.
4. **Negatif Doğrulama Testleri:**
   - Simüle edilen bir `UPDATE`, `INSERT` veya `DELETE` işleminin invariant kontrolünü anında kırdığı (fail ettiği) testle kanıtlanır.
   - Kasa dosyasında yapılan 1 baytlık değişikliğin invariant kontrolünü kırdığı testle kanıtlanır.

---

## 3. A2.1 — Gerçek Kaynak Versiyonlama Sözleşmesi

### Problem
`BootstrapSourceRef.source_version` ve `AgentSessionSource.source_version` alanları pratikte `None` saklanıyordu; bu nedenle dokümante edilen "kaynak değiştiğinde stale kaynak reuse edilmez" kuralı çalışmıyordu. Ayrıca `Entity.updated_at` domain tablolarındaki (örneğin `project.next_action`, `project.status`) değişiklikleri otomatik yansıtmaz.

### Çözüm
1. **Deterministik Canonical Payload Fingerprint'i (Operational):**
   - Kaynağın A2 tarafından modele teslim edilen anlamlı bounded canonical payload'ının SHA-256 parmak izi alınır (`compute_source_version`):
     - **Project:** `sha256(f"{title}|{status}|{next_action or ''}|{last_activity_at or ''}")`
     - **Todo / Deadline:** `sha256(f"{title}|{due_at or ''}|{status}")`
     - **Decision:** `sha256(f"{summary}|{status}|{revision}")`
   - Kural: A2'nin modele verdiği anlamlı canonical source payload değiştiyse $\rightarrow$ `source_version` zorunlu olarak değişir.
2. **Kasa (Vault Note) Exact Content Revision:**
   - Seçilen/bounded f0rknbrain notunun tam baytlarının SHA-256 özeti: `sha256(note_bytes)`.
   - Saniyeye yuvarlanmış `int(mtime)` revision authority değildir; ucuz pre-check olarak `st_mtime_ns + size` kullanılabilir ancak nihai revision otoritesi tam içerik hash'idir.
   - Full Vault scan yapılmaz; yalnızca A2'nin seçtiği küçük sayıdaki not (en fazla 2-3) için hesaplanır.
3. **H2 Sıcak Bellek:**
   - Mevcut `HotMemoryItem.revision` (sha256 içerik karması) doğrudan yeniden kullanılır.
4. **Ambiguous Continuation Sırasında Doğrulama:**
   - Önceki aktif kaynaklar `agent_session_source` tablosundan okunurken canlı kaynakların güncel payload fingerprint'i kontrol edilir.
   - Versiyon uyuşmazlığında kaynak **stale** kabul edilir (`SOURCE_STALE` tanılama kodu), modele teslim edilmez; stale kaynaklar temizlenerek gerekirse yeni arama yapılır.
5. **Test:**
   - Kaynak v1 teslim edilir $\rightarrow$ varlığın canonical payload'ı (ör. `next_action`) mutate edilerek v2 yapılır $\rightarrow$ ambiguous continuation isteği gelir $\rightarrow$ v1 reuse edilmez, stale olarak işaretlenir.

---

## 4. A2.1 — `scope_project` Gerçek Geçersiz Kılma (Invalidation) Sınırı

### Davranış Matrisi
- **`previous == current (A == A)`:** Süreklilik reuse'u geçerli; A kapsamındaki kaynaklar taşınır.
- **`previous == A, current == B`:** Kapsam açıkça değişti; eski A kaynakları invalidate edilir (silinir), B kapsamı için yeni arama yapılır.
- **`previous == A, current == None`:** Kullanıcı proje kapsamından genel kapsama geçti. Projeye özel kaynaklar temizlenir, genel/kimlik kaynakları korunur.
- **`previous == None, current == B`:** B dışındaki kaynaklar körlemesine taşınmaz; B kapsamına odaklanılır.

---

## 5. A2.1 — Deterministik Konu Uyumluluğu (Topic Compatibility)

### Problem
`topic_signature` alanı `initial_bootstrap` gibi anlamsız sabit etiketler taşıyordu ve her non-ambiguous prompt gereksiz yere topic shift sayılarak eski kaynakları siliyordu.

### Çözüm (Seçenek A: Bounded Deterministik Uyumluluk)
- **Harici model / embedding / LLM classifier YOKTUR.**
- `topic_signature`, aktif kaynakların başlıklarından, kapsam projesinden ve normalize edilmiş anahtar kelimelerden kararlı bir hash/imza olarak türetilir (`p:<scope>|k:<sorted_tokens>`).
- Gelen prompt incelendiğinde:
  1. **Ambiguous follow-up** (*"bunu aç", "önceki kaynak?"*): Doğrudan aktif kaynaklar reuse edilir.
  2. **Doğrudan/Açık aynı konu sorusu** (*"forkOS A2 source continuity nasıl çalışıyor?"* ardından *"source version ne zaman değişiyor?"*):
     - Prompt terimleri aktif kaynakların başlıkları veya anahtar kelimeleriyle örtüşüyorsa ($\ge 1$ örtüşme veya aynı proje kapsamı): **Topic değişmemiştir.**
     - Mevcut kaynaklar korunur; gerekiyorsa yeni arama sonuçları mevcut listeyi zenginleştirir.
  3. **Doğrulanmış Konu Değişimi:** Örtüşme sıfır ve açıkça başka bir varlık/proje sorgulanıyorsa eski kaynaklar invalidate edilir.
  4. **Belirsiz:** Güvenli olarak yeni arama yapılır, temelsiz iddia üretilmez.

---

## 6. A2.1 — f0rknbrain'i Gerçek Bounded A2 Kaynağı Yapma

### Çözüm
- Mevcut H0 altyapısı doğrudan yeniden kullanılır: `app.integrations.agent.knowledge` (`search_vault`, `read_vault_note`, `vault_index`).
- **First-turn Bootstrap:**
  - Kalıcı kullanıcı tercihleri ve etkileşim ilkeleri için `90 Agent/` klasöründeki veya aktif projeyle ilişkili notlar bütçeli olarak okunur.
  - Asla tüm not veya tüm kasa dökümü yapılmaz; en fazla 2-3 küçük özet öğe seçilir.
- **Later-turn Bounded Retrieval:**
  - Operasyonel aramanın yanında gerekirse sınırlı kasa araması (`search_vault(query, limit=2)`) yapılır.
- **Kaynak Provenance:**
  - `source_type="vault_note"`
  - `source_id="vault:<relative_path>"` (Mutlak host yolu ASLA yer alamaz).
  - `source_version`: Dosya `mtime:hash` değeri.
- **Hata Yönetimi:** Kasa yoksa veya arama boş dönerse sistem çökmez; `VAULT_UNAVAILABLE` koduyla fail-open devam eder.

---

## 7. A2.1 — Hot Path'ten Full Vault Walk'un Kaldırılması

### Çözüm
- `compose_first_turn_bootstrap` içindeki `get_brain_status()` çağrısı kaldırılır (bu çağrı `os.walk` ile tüm diski tarıyordu).
- Yerine hafifletilmiş kontrol eklenir:
  - `vault_path.is_dir()` ve `os.access(vault_path, os.R_OK)`.
  - Varsa `vault_index` bellek içi durumu.
- **Performans Garantisi:** First-turn hot path diskteki tüm dosyaları gezmez.
- Regresyon testi ile `os.walk` çağrılmadığı doğrulanır.

---

## 8. A2.1 — 4000 Karakterlik Katı Bütçe Garantisi (Hard Limit)

### Çözüm
1. **Alan Seviyesi Sınırlandırma (Field-level Sanitization):**
   - Başlıklar: $\le 120$ karakter.
   - Karar özetleri: $\le 150$ karakter.
   - İlke ve hedefler: $\le 200$ karakter.
   - Not/içerik alıntıları: $\le 250$ karakter.
2. **Hiyerarşik Kırpma Sırası:**
   - H2 sıcak hafıza $\rightarrow$ İkincil projeler $\rightarrow$ Tamamlanan işler $\rightarrow$ Açık iş parçaları.
3. **Hard Cap ve Güvenli Kapanış:**
   - Render sonrası metin 4000 karakteri aşıyorsa, açılış etiketi ve kapanış etiketi `</forkos-context>` bozulmadan son satırlar güvenli şekilde kırpılır.
   - `len(rendered) <= 4000` matematiksel olarak garanti edilir.
   - Tanılamada `truncated=True` ve `omitted_count` set edilir.
4. **Adversarial Test:** Devasa deadline başlıkları, devasa H2 girdileri, devasa proje başlıkları içeren vakalarda bütçenin aşılmadığı kanıtlanır.

---

## 9. A2.1 — Geçici Prompt Asla Loglanamaz (Privacy Hardening)

### Çözüm
- `service.py` ve ilgili dosyalardaki tüm `LOGGER.debug`, `LOGGER.warning`, `LOGGER.exception` çağrılarından `user_message`, `candidate`, `query`, not gövdeleri ve mutlak yollar temizlenir.
- Yalnızca hata sınıfları (`type(exc).__name__`) ve tanı kodları loglanır.
- **Gizlilik Testi:** Test içinde gizli bir token (`SECRET_PROMPT_TOKEN_XYZ`) içeren prompt gönderilir; test log capture ile log kayıtlarında bu token'ın kesinlikle bulunmadığı kanıtlanır.

---

## 10. A2.1 — Renderer Güvenliği ve Evrensel Kaçış

### Çözüm
- `renderer.py` içinde `escape_context_data`:
  - `redact_absolute_paths` uygulanır.
  - `html.escape(text, quote=True)` kullanılarak `&`, `<`, `>`, `"`, `'` karakterleri XML entity'lerine dönüştürülür.
- Kötü niyetli `</forkos-context>`, `<system>`, `<tool>`, `</forkos-context >` gibi enjeksiyon denemeleri etkisiz hale getirilir.
- Güvenlik bildirimi aynen korunur (içerik untrusted data'dır).

---

## 11. A2.1 — Bounded Ephemeral Storage ve Pruning

### Çözüm
- `agent_session_context` ve `agent_session_source` tablolarının sınırsız büyümesi engellenir.
- Her yazma sırasında oportünistik temizlik:
  - Süresi dolan kaynaklar temizlenir (`expires_at < now()`).
  - İlgili oturum için `agent_session_context` tablosunda yalnızca son 50 kayıt tutulur; eski kayıtlar silinir.

---

## 12. A2.1 — Tanılama ve UI Düzeltmeleri

### Çözüm
- `ContinuityStatusOut` şemasına `last_context_at: datetime | None` eklenir (son bağlam enjeksiyonu zamanı).
- `last_bootstrap_at` yalnızca ilk tur bootstrap zamanını gösterir.
- `active_source_count` son aktif oturuma göre filtrelenir.
- Frontend'de `BrainAgentSection.tsx` ve `agentContinuity.ts` bu alanları doğru Türkçe başlıklarla sunar.
- `check-endpoint-coverage.mjs` ve API sözleşmeleri senkronize tutulur.

---

## 13. A2.1 — Hermes Plugin Temizliği ve İşlem İzolasyonu

### Çözüm
- `tools/hermes/forkos-lifecycle/__init__.py` başlığındaki eski A1-only docstring güncellenir (A1 lifecycle + A2 bounded context adapter).
- `MAX_PLUGIN_USER_MESSAGE_CHARS = 500` sabiti tanımlanır ve dokümante edilir.
- `router.py` içinde A2 compose hatası durumunda:
  - Destek transaction'ı (`support_session`) explicit `rollback()` edilir.
  - A1 commit'i kesinlikle etkilenmez; HTTP 200 ve `degraded_reasons` ile fail-open dönülür.
