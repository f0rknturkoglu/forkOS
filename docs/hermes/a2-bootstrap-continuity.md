# Hermes Başlangıç Bağlamı ve Kaynak Devamlılığı (A2)

Bu katman, Hermes ajan oturumları için yerel operasyonel durumu, kalıcı kullanıcı tercihlerini ve oturum içi kaynak sürekliliğini **sınırlı, kaynak kökenli ve prompt injection korumalı** bir şekilde LLM öncesi bağlama enjekte eder.

---

## 1. Mimari ve Orkestrasyon

A1 içeriksiz, ucuz ve bağımsız bir yaşam döngüsü ilkelidir (`POST /api/agent/lifecycle/event`). A2 ise Hermes `pre_llm_call` kancası sırasında tek bir yerel HTTP çağrısıyla tetiklenen birleşik orkestrasyon ucunu sunar:

```text
Hermes pre_llm_call
         │
         ▼  (Tek HTTP POST)
POST /api/agent/lifecycle/turn
   ├── 1. A1 observe(session_start | turn_seen) -> Bağımsız commit
   └── 2. A2 compose(first_turn | later_turn)   -> Salt-okunur üretim
         │
         ├── İlk tur:  BootstrapPacketV1 (<forkos-context>)
         └── Sonraki:  Kaynak devamlılığı (<forkos-continuity>)
```

### Önemli Hata ve İzolasyon Sınırı
- A1 gözlemi ve A2 bağlam üretimi aynı başarı/başarısızlık alanını **paylaşmaz**.
- A1 gözlemi bağımsız işleminde commit edilir; A2 bağlam üretimi beklenmedik bir hata alsa veya kısıtlansa dahi A1 oturum kaydı geri alınmaz (`rollback` yapılmaz).
- Uç HTTP 200 döner ve `degraded_reasons` ile arıza kodunu bildirir (`CONTEXT_COMPOSITION_FAILED`); Hermes oturumu veya turu hiçbir zaman çökmez (fail-open).
- `on_session_finalize` kancası doğrudan `POST /api/agent/lifecycle/event` üzerinden A1 finalize olarak işlemeye devam eder.

---

## 2. İlk Tur Başlangıç Bağlamı (First-Turn Bootstrap)

İlk turda (`is_first_turn: true`) üretilen bağlam (`BootstrapPacketV1`), modelin kullanıcıyı, güncel projeleri, yaklaşan son tarihleri ve son oturum izini tanımasını sağlar:

1. **Kimlik ve İlkeler:**
   - Etkileşim kuralları: Kullanıcı Türkçe konuşur; kod ve değişkenler İngilizce, açıklamalar Türkçe olmalı.
   - Yerel sınır: Harici telemetri veya bulut modeli çağrısı yok.
   - Mutasyon yasağı: Kullanıcı onayı olmadan kanonik operasyonel veriler doğrudan değiştirilmez.
   - f0rknbrain / H2 üzerinden kalıcı tercihler, düzeltmeler ve uzun vadeli hedefler.
2. **Kanonik Operasyonel Durum (forkOS DB):**
   - Aktif projeler (en fazla 5) ve bir sonraki eylemler (`next_action`).
   - Yaklaşan son tarihler (en fazla 5) ve kalan gün sayıları.
   - Bekleyen H7 kararları özeti.
   - Açık görev sayısı.
3. **Yakın Süreklilik (H5):**
   - Son anlamlı hareket (`last_meaningful_activity`), aktivite aralığı (`activity_gap_hours`), tamamlananlar ve açık iş parçaları.
4. **Sıcak Hafıza (H2):**
   - Profil, kısıt, hedef ve kararlar (en fazla 6 öğe).
5. **Kaynak Referansları:**
   - Teslim edilen tüm varlıklar `source_id` (`entity:<uuid>`, `hot_memory:<id>`) ile listelenir. Mutlak dosya yolları kesinlikle yer almaz.

### Katı Karakter Bütçesi ve Kırpma Sırası
- Toplam bağlam metni **4000 karakteri aşamaz**.
- Bütçe aşıldığında deterministik öncelik sırasına göre kırpılır:
  1. H2 sıcak hafıza öğeleri
  2. Aktif projelerin ikincil olanları
  3. Tamamlanan yakın işler
  4. Açık iş parçaları
- **Kullanıcı kimliği ve güvenlik ilkeleri asla kırpılmaz.** Kırpma yapıldığında tanılamada `truncated: true` ve `omitted_count > 0` bayrakları set edilir.

---

## 3. Sonraki Turlar ve Kaynak Devamlılığı (Later-Turn Continuity)

Sonraki turlarda tam bootstrap **asla tekrarlanmaz**; prompt injection ve token israfı önlenir:

1. **Belirsiz Devam Sorusu (Ambiguous Continuation):**
   - Kullanıcı *"bunu biraz aç"*, *"onu da karşılaştır"*, *"önceki kaynağa göre?"* gibi kısa (<60-80 karakter) veya önceki kaynaklara atıfta bulunan ifadeler kullandığında:
   - TTL (60 dakika) dolmamışsa önceki teslim edilen kaynaklar `agent_session_source` tablosundan tekrar kullanılır.
   - Modele kompakt `<forkos-continuity>` bloğu enjekte edilir:
     ```markdown
     <forkos-continuity version="1">
     <!-- Önceki oturum içi kaynak devamlılığı (untrusted data) -->
     Önceki aktif kaynaklar:
     - `entity:b6ec9f54-...` (project) "forkOS"
     </forkos-continuity>
     ```
2. **Konu Değişimi (Topic Shift):**
   - Kullanıcı açıkça yeni bir konuya/projeye geçtiğinde önceki kaynak kümesi geçersiz kılınır (`AgentSessionSource` silinir).
   - Yeni sorgu için sınırlandırılmış yerel arama (`search_operational_context`) yapılarak yalnızca eşleşen varlıklar yeni kaynak olarak kaydedilir.
3. **Bağlam Gerektirmeyen Turlar:**
   - Ek bağlam gerekmediğinde `rendered_context=None` döner ve Hermes doğrudan MCP araçlarıyla çalışır.

---

## 4. Güvenlik, Gizlilik ve İzolasyon Sözleşmesi

1. **Transient Prompt Asla Saklanmaz ve Loglanmaz:**
   - Gelen `user_message` yalnızca tur içinde devamlılık/konu sınıflandırması ve yerel arama için RAM'de kullanılır.
   - Veritabanına (`AgentSessionContext`, `AgentSessionSource`), loglara (`LOGGER.debug/info/exception`) veya Vault'a **kesinlikle yazılmaz**. Loglar arıza durumunda yalnızca istisna sınıf adını (`type(exc).__name__`) kaydeder.
2. **Evrensel XML/HTML Kaçışı:**
   - Getirilen tüm kaynak verisi (untrusted data) olarak kabul edilir.
   - `html.escape(text, quote=True)` ve `redact_absolute_paths` fonksiyonları ile hem XML etiketleri (`<`, `>`, `&`, `"`, `'`) hem de wrapper sınırları (`</forkos-context>`, `<forkos-continuity>`) tam güvenlik altına alınır.
3. **Mutlak Sistem Yollarının Gizlenmesi:**
   - Hiçbir mutlak dosya yolu (`/Users/...`, `C:\...`) prompt context'ine veya tanılamalara sızamaz. `redact_absolute_paths` regex filtresi ile `<vault>` olarak maskelenir.
4. **Deterministik Kaynak Parmak İzi ve Bayatlama Denetimi (Stale Detection):**
   - Kaynak sürümleri `Entity.updated_at` yerine doğrudan A2 tarafından tüketilen bounded kanonik payload'ın deterministik SHA-256 hash'idir:
     - Proje: `sha256(title | status | next_action | last_activity_at)`
     - Görev/Son tarih: `sha256(title | due_at | status)`
     - Karar: `sha256(summary | status | revision)`
     - Vault notu: `sha256(note_bytes)`
   - Sonraki turlarda depolanan parmak izi canlı DB/dosya ile uyuşmazsa kaynak bayat kabul edilir (`SOURCE_STALE`), eski referans silinir ve temiz yeniden getirme tetiklenir.
5. **Kapsam Geçiş Matrisi (Scope Project Boundary):**
   - $A \rightarrow A$: Aynı proje kapsamı; geçerli kaynaklar korunur ve yeniden kullanılır.
   - $A \rightarrow B$: Proje değişimi; $A$'ya ait önceki tüm kaynaklar geçersiz kılınır.
   - $A \rightarrow \text{None}$: Kapsam temizlendi; proje kaynakları silinir, genel kaynaklar korunur.
   - $\text{None} \rightarrow B$: Proje kapsamına giriş; farklı proje kaynakları temizlenir.
6. **Deterministik Konu Uyumluluğu (Option A):**
   - Harici model veya embedding kullanılmadan; doğrudan soru kelimeleri ile aktif kaynak başlıkları/kapsamı arasındaki anahtar kelime örtüşmesi hesaplanır. Aynı konudaki doğrudan sorular bağlam sürekliliğini kaybetmez.
7. **Local-Only Çalışma ve Sıfır Mutasyon:**
   - Tüm HTTP trafiği `127.0.0.1:8787` üzerindedir. Dışarıya hiçbir veri veya telemetri çıkışı yoktur.
   - A2 bağlam üretimi `entity`, `event`, `link`, `todo`, `project`, `opportunity`, `notification`, `proactivity_run`, `execution_plan` veya Vault dosyalarında **sıfır mutasyon** gerçekleştirir.

---

## 5. Ephemeral Destek Modelleri ve Budama

`0064_agent_continuity` ve `0065_continuity_scope` migration'ları ile iki destek tablosu eklenmiştir:

- `agent_session_context`: Oturum başına tur sayısı, bağlam karakter sayısı, kırpılma durumu, arıza kodları (`degraded_reasons`) ve proje kapsamını (`scope_project`) tutar. Oturum başına en fazla 50 kayıt saklanacak şekilde oportunistik olarak budanır.
- `agent_session_source`: Teslim edilen kaynakların kimliğini (`source_id`), türünü, parmak izini (`source_version`), kapsamını (`scope_project`) ve 60 dakikalık geçerlilik süresini (`expires_at`) saklar. Süresi dolan kayıtlar her turda otomatik olarak temizlenir.

---

## 6. Canlı Doğrulama ve Performans Ölçümleri

Gerçek yerel Hermes CLI ve forkOS API çalışma zamanı üzerinde yapılan ölçümler:

| İşlem | Enjekte Edilen Bağlam | Ölçülen Gecikme |
| --- | --- | --- |
| **Tur 1 (İlk Tur / Bootstrap)** | `<forkos-context>` (732 karakter) | **184.4 ms** |
| **Tur 2 (Belirsiz Devam Sorusu)** | `<forkos-continuity>` (kaynak reuse) | **18.7 ms** |
| **Tur 3 (Aynı Konu Devamı)** | `<forkos-continuity>` (topic compatibility) | **13.5 ms** |
| **Tur 4 (Konu Değişimi)** | Invalidation + Bounded query retrieval | **16.3 ms** |
| **Oturum Kapanışı (Finalize)** | İçeriksiz yaşam döngüsü kaydı | **11.8 ms** |
