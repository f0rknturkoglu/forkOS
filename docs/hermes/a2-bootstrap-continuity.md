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

#### Katı Karakter Bütçesi ve Kırpma Sırası
- Toplam bağlam metni **4000 karakteri aşamaz**.
- Bütçe aşıldığında deterministik öncelik sırasına göre kırpılır:
  1. H2 sıcak hafıza öğeleri
  2. Aktif projelerin ikincil olanları
  3. Tamamlanan yakın işler
  4. Açık iş parçaları
- **Kullanıcı kimliği ve güvenlik ilkeleri asla kırpılmaz.**
- **Doğrulanabilir Kırpma Tanılaması (Truthful Hard-Cap Diagnostics):** Trimming döngüsü öğe çıkaramadığında dahi retained alanlar nedeniyle 4000 karakter hard-ceiling devreye girerse `diagnostics.truncated = True` ve geçerli kapanış etiketi (`</forkos-context>`) garanti edilir.

---

## 3. Sonraki Turlar ve Kaynak Devamlılığı (Later-Turn Continuity)

Sonraki turlarda tam bootstrap **asla tekrarlanmaz**; token israfı önlenir ve güvenlik yüzeyi daraltılır:

1. **Belirsiz Devam Sorusu (Ambiguous Continuation):**
   - Kullanıcı *"bunu biraz aç"*, *"onu da karşılaştır"*, *"önceki kaynağa göre?"* gibi kısa (<60-80 karakter) veya önceki kaynaklara atıfta bulunan ifadeler kullandığında:
   - TTL (60 dakika) dolmamışsa önceki teslim edilen taze kaynaklar tekrar kullanılır.
   - **Proje Kapsam İzolasyonu (Project Scope Filter):** Mevcut oturum `scope_project = A` kapsamındaysa, yalnızca `scope_project is None` veya `scope_project == A` olan kaynaklar reuse edilir; başka projelere (ör. Project B) ait kaynaklar bağlama kesinlikle dahil edilmez.
   - Modele kompakt `<forkos-continuity>` bloğu enjekte edilir.
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
2. **Savunma Derinliği ve Güvenilmeyen Veri (Defense-in-Depth / Untrusted Data):**
   - Yerel depolama veya veritabanından çekilen tüm bağlam "güvenilmeyen veri" olarak etiketlenir.
   - `html.escape(text, quote=True)` ve `redact_absolute_paths` fonksiyonları ile hem XML etiketleri (`<`, `>`, `&`, `"`, `'`) hem de wrapper sınırları (`</forkos-context>`, `<forkos-continuity>`) korunur. Sistemin tüm injection risklerini tek başına sıfırladığı iddia edilmez; savunma derinliği ve sınırlandırma uygulanır.
3. **Mutlak Sistem Yollarının Gizlenmesi:**
   - Hiçbir mutlak dosya yolu (`/Users/...`, `C:\...`) prompt context'ine veya tanılamalara sızamaz. `redact_absolute_paths` regex filtresi ile `<vault>` olarak maskelenir.
4. **H2 Revizyon Farkındalıklı Tazelik Denetimi (Revision-Aware Stale Detection):**
   - Sıcak hafıza öğelerinde `HotMemoryItem.revision` kaynak sürümü olarak taşınır.
   - Kaynağın revizyonu değiştiğinde veya bellek aktif bağlamdan çıktığında/emekli edildiğinde kaynak derhal bayat (`SOURCE_STALE`) kabul edilir, eski referans tablodan silinir ve eski devamlılık enjekte edilmez.
5. **Sağlayıcı Farkındalıklı Son Tarih Sürümleme (Provider-Aware Deadline Fingerprinting):**
   - Son tarih sürümleri `deadline == Todo` varsayımı yapmaz; tüm kayıtlı sağlayıcıları (`MODULES[].deadline_provider` — Todo, Media, Calendar, Finance, Opportunity vb.) kapsar.
   - Hem ilk turda hem sonraki tazelik kontrollerinde aynı kanonik parmak izi kullanılır: `sha256(title | due_at | entity_type | module | priority)`.
6. **Anlamsal ve Güvenli f0rknbrain Not Seçimi:**
   - `90 Agent` altındaki rastgele dosyalar dayanıklı tercih (`durable_preferences`) kabul edilmez; semantik kaynağı olmayan notlar tercih ilan edilmek yerine boş dönülür.
   - Not seçimi hot-path üzerinde `os.walk` yapmaz; `vault_index` üzerinden managed kayıtları sorgular.
   - Tüm kasa erişimleri `resolve_safe_vault_path` + `is_safe_knowledge_path` + `is_policy_excluded` kontrollerinden geçer. Traversal (`..`), symlink, gizli dizinler veya politika dışı notlar asla okunmaz.
7. **Kapsam Geçiş Matrisi ve Filtreleme (Scope Transitions & Filtering):**
   - $A \rightarrow A$: Aynı proje kapsamı; geçerli kaynaklar korunur ve filtrelenerek kullanılır.
   - $A \rightarrow B$: Proje değişimi; $A$'ya ait önceki tüm kaynaklar geçersiz kılınır.
   - $A \rightarrow \text{None}$: Kapsam temizlendi; proje kaynakları silinir, genel kaynaklar korunur.
   - $\text{None} \rightarrow B$: Proje kapsamına giriş; farklı proje kaynakları temizlenir.
   - Aktif turda `scope_project` varsa harici proje kaynakları filtrede elenir.
8. **Deterministik Konu Uyumluluğu:**
   - Harici model veya embedding kullanılmadan; doğrudan soru kelimeleri ile aktif kaynak başlıkları ve kapsam arasındaki deterministik anahtar kelime örtüşmesi hesaplanır. Aynı konudaki doğrudan sorular bağlam sürekliliğini kaybetmez.
9. **Local-Only Çalışma ve Sıfır Mutasyon:**
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
