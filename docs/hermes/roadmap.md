# forkOS × Hermes — Evrimsel Yol Haritası (H-Serisi)

forkOS ile otonom ajan ekosistemini (Hermes) birleştiren vizyon; kademeli,
güvenli ve insan denetimini elden bırakmayan aşamalar halinde tasarlanmıştır.

```text
  H0 ✓            H1 ✓            H2 ✓            H3 ✓            H4 ✓            H5 ✓            H6 ✓            H7 ✓
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  Gözler  │──>│  Eller   │──>│  Sıcak   │──>│  Kanıt   │──>│  Yerel   │──>│  Sentez  │──>│ Proaktif │──>│  Karar & │
│ Salt-    │   │ Onaylı   │   │  Hafıza  │   │  & Geri  │   │  Model   │   │  & Brif. │   │  Ajan    │   │  Yürütme │
│ Okunur   │   │ Eylemler │   │ (Vault)  │   │  Getirme │   │  Router  │   │          │   │          │   │          │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
```

---

## H0 — Brain Interface Foundation ✅ Tamamlandı

**Soru:** *Ne oluyor ve ne biliyorum?*

- FastAPI `/mcp` üzerinde Streamable HTTP MCP ucu (loopback-only, DNS rebinding koruması).
- **8 salt-okunur araç:** `forkos_briefing`, `forkos_search`,
  `forkos_entity_context`, `forkos_project_context`, `forkos_recent_activity`,
  `brain_status`, `brain_search`, `brain_read`.
- %100 değişmezlik: DB ve Vault'a **sıfır yazma** (deterministik içerik parmak
  izi ile kanıtlanır).
- Deterministik leksikal Vault taraması; bounded payload'lar; sır maskeleme.
- Ayrıntı: `h0-brain-interface.md`, `h0-tool-contract.md`, `h0-setup.md`.

---

## H1 — Safe Actions & Approval ✅ Tamamlandı

**Soru:** *Kullanıcı açıkça onayladıktan sonra neyi değiştirebilirim?*

- **11 yazma aracı** (toplam yüzey 19): görev oluştur/güncelle/tamamla/planla,
  proje `next_action`, fırsat ve başvuru geçişleri, yer imi kaydet/güncelle,
  bilgi yakala, yönetilen nota ekle.
- **Onay modeli:** onay kapısı MCP istemcisindedir (`trust: untrusted`); forkOS
  kendi onay tablosunu/kuyruğunu KURMAZ. Sunucu tarafı yalnızca yazma
  araçlarını `readOnlyHint=false` ile doğru işaretler.
- **Domain otoritesi korunur:** tüm yazmalar canonical servislere delege eder
  (`todo.service`, `project.service`, `opportunity.lifecycle/application`,
  `bookmark.service`, `obsidian.service`). Genel mutasyon, raw SQL, keyfî
  dosya yazımı ve silme YOKTUR.
- **Fail-closed tazelik:** `expected_updated_at`, `expected_status`, Vault
  `mtime`; bayat karar uygulanmaz (`STALE_ACTION`, `VAULT_STALE`).
- **Yerellik:** hiçbir yazma aracı dış ağ çağrısı yapmaz.
- **Bilgi sahipliği:** `brain_capture` / `brain_save_to_entity` doğrudan Vault'a
  yazar; forkOS veritabanına not satırı eklemez; legacy Notlar arşivine sıfır
  yazma.
- Kanıt: `test_agent_h1_contract.py` (yüzey + anotasyon + sınırlar),
  `test_agent_h1_mutation_scope.py` (yalnızca beklenen domain değişir),
  `test_agent_h1_failure_immutability.py` (başarısızlık hiçbir şey değiştirmez),
  `test_agent_mcp.py` (gerçek `/mcp` taşıması).
- Ayrıntı: `h1-safe-actions.md`, `h1-tool-contract.md`, `h1-setup.md`.

---

## H1.1 — Write Correctness ✅ Tamamlandı

- Kısmi güncellemede **verilmeyen alan ≠ açık null** (MCP argüman bağlaması).
- Yer imi etiket güncellemesi gerçekten çalışır; plan tekrarı `noop`.
- `brain_save_to_entity` başarısızlıkta **atomik** (yetim Vault notu bırakmaz).
- Mevcut başvuruda `expected_status` ZORUNLU.
- Mutlak kasa yolu ajan tanılamasından temizlendi.

## H1.2 — Binding Upgrade Guard ✅ Tamamlandı

- İstek bağlamı VAR ama argümanlar çözülemiyorsa **fail-closed**
  (`MCP_ARGUMENT_BINDING_UNAVAILABLE`); SDK yükseltmesi omitted-vs-null
  hatasını sessizce geri getiremez.
- Taşıma testleri hermetik oturuma geçti (başlangıç yan etkileri kapalı).

---

## H2 — Hot Curated Memory ✅ Tamamlandı

**Soru:** *Ajansal bağlam olarak hangi küçük, kalıcı gerçekleri yanımda taşımalıyım?*

- Sahiplik: `f0rknbrain / 90 Agent/Memory/<memory_id>.md` — öğe başına tek
  dosya, UUID kimliği, sürümlü frontmatter (v1).
- 5 tür: `profile`, `preference`, `goal`, `constraint`, `decision`.
- `effective_status`: `active | expired | retired` (zaman aşımı okuma anında;
  emeklilik silme değildir).
- Revizyon = `sha256(dosya baytları)`; güncelleme/emeklilik `expected_revision`
  ister, bayat yazma fail-closed.
- Sınırlı bağlam: ≤24 öğe, ~6000 karakter, deterministik sıralama, dürüst
  `truncated`/`omitted_total`.
- **5 MCP aracı** (toplam yüzey 24). Silme, aday tablosu, otomatik yazma,
  konuşma arşivi ve DB aynası YOKTUR.
- Ayrıntı: `h2-hot-memory.md`, `h2-memory-policy.md`, `h2-tool-contract.md`,
  `h2-setup.md`.

---

## H2.1 — Correctness, Concurrency & Privacy Hardening ✅ Tamamlandı

**Soru:** *Kullanıcı dosyayı elle düzenlediğinde ve iki yazma yarıştığında
sistem hâlâ güvenilir mi?*

Mimari DEĞİŞMEDİ; yalnızca somut doğruluk/yarış/gizlilik açıkları kapatıldı:

- **Dosya sistemi CAS:** revizyon kararı artık tarama anındaki kopyadan değil,
  `os.replace`'ten hemen önce okunan **güncel baytlardan** gelir. Kullanıcının
  Obsidian düzenlemesi bayat bir ajan yazmasıyla ezilmez.
- **Bayat revizyon > `noop`:** istenen değerler mevcut duruma eşit olsa bile
  bayat `expected_revision` `HOT_MEMORY_STALE` verir (update ve retire).
- **Yaşam döngüsü dürüstlüğü:** kesin tekrar denetimi yalnızca AKTİF kayıtlar
  için; emekli/süresi geçmiş kayıt yeni bir "hatırla" isteğini bloklamaz, aynı
  olgu YENİ kimlikle aktifleşir.
- **Okuma anında politikası:** elle düzenlenmiş dosya apaçık sır taşıyorsa
  sıcak hafızaya yüklenmez, DEĞİŞTİRİLMEZ ve H0 yüzeyinden de dışlanır.
- **Atomik oluşturma:** hedef yalnızca içeriği tam olan dosyaya bağlanır; kısmi
  dosya görünmez, başarısızlık artık geçici dosya bırakmaz.
- **Dürüst tanılama:** `invalid_count` gerçek sayıyı, `invalid_paths` sınırlı
  listeyi verir; okunamayan Vault temiz `HOT_MEMORY_UNAVAILABLE` döner.

**Eklenmedi:** yeni araç, yeni tablo, embedding, kilit alt sistemi, semantik
benzerlik. Yüzey yine **24** araç.

---

## H2.2 — Metadata Privacy & Bounded Contracts ✅ Tamamlandı

**Soru:** *Politika yalnızca başlık/gövdeyi mi koruyor, ve belgelenen her sınır
gerçekten uygulanıyor mu?*

- **Tam artifact politikası:** denetim girdisi artık `göreli yol + ham Markdown`.
  `tags`, `retired_reason`, bilinmeyen frontmatter ve taşınmış dosya adı da
  kapsanır; ajan yüzeyine çıkabilecek hiçbir metadata kaçış yolu kalmaz.
- **Depolama yetkili:** politika, render edilen aday YAYINLANMADAN önce depolama
  katmanında dayatılır; adaptördeki denetim yalnızca kolaylıktır.
- **Tanılama redaksiyonu:** `invalid_paths` ve çakışma mesajlarındaki sır benzeri
  bileşenler `[redacted]` olur; mutlak yol hiçbir koşulda dönmez.
- **Gerçek sınırlar:** elle düzenlenen dosyada etiket başına 50 karakter ve
  boş-olmayan etiket kuralı ayrıştırıcıda da uygulanır; `query` sınırı (200)
  hem MCP şemasında hem çalışma zamanında dayatılır.
- **Belge dürüstlüğü:** kök README ve bu doküman 24 araçlı gerçek yüzeyi
  anlatır; gizlilik ifadesi "uçtan uca yerel" iddiasından arındırılıp
  ajan/model sağlayıcı sınırına bağlandı; oluşturma garantisi sert bağ ve
  yedek yol ayrımıyla yazıldı.

**Eklenmedi:** yeni araç, yeni tablo, PII sınıflandırıcı, semantik arama, H3.
Yüzey yine **24** araç.

---

## H3 — Retrieval & Evidence ✅ Tamamlandı

**Soru:** *Bir iddiayı hangi kanıt destekliyor?*

- **Tek genel araç:** `forkos_evidence` (yüzey 25). Yanıt ÜRETMEZ; kökenli bir
  `EvidenceBundle` döner. Hermes paketin üzerinde akıl yürütür.
- **Üç kanıt kaynağı:** `entity` (güncel durum), `event` (append-only geçmiş),
  `vault` (Markdown). Sıcak hafıza kanıt DEĞİLDİR ve taranmaz.
- **Yapı önce:** sorguya çekirdek verilirse kanonik Link grafiği (deterministik
  BFS, düğüm tavanı 25) ve olay geçmişi taranır; verilmezse yalnızca leksikal
  adaylar döner ve hiçbir aday kök yapılıp genişletilmez.
- **Köken zinciri:** her öğe `locator` (dosya/başlık/satır veya olay id) ve
  `relation_path` (`entity_link` / `knowledge_pointer` / `wikilink` /
  `backlink`) taşır.
- **Tek kasa hopu:** yönetilen not → doğrudan wikilink + doğrudan backlink.
  Belirsiz bağ TAHMİN EDİLMEZ (`VAULT_CONFLICT`, ambiguity uyarısı); çözülemeyen
  bağ ölümcül değildir. Kod blokları ve `![[ek]]` bağ sayılmaz.
- **Leksikal kasa araması** token tabanlıdır (stopword küçük ve açık; `İ→i`,
  `ş→s` aksan duyarsız). Bağlı not ancak sorguyla eşleşiyorsa kanıt olur.
- **Dürüst sınırlar:** öğe (≤15), snippet (≤1200), toplam (≤8000), grafik (≤25),
  olay (≤8), kasa notu (≤12), tarama dosyası (≤500), tek dosya (≤256 KiB).
  `truncated` / `omitted_total` / `warnings` sınırları saklamaz.
- **Kapsam ayrımı:** `scope=operational` Vault'a HİÇ dokunmaz;
  `scope=knowledge` entity/olay kanıtı üretmez.
- **Determinizm:** aynı durum + aynı istek = aynı kanıt kimlikleri, sıra, köken
  yolları ve iz. İz her istekte aynı 8 aşamayı taşır.
- **Eklenmedi:** embedding, vektör DB, model çağrısı, GraphRAG indeksi, kalıcı
  iz/index, arka plan işçisi, migration, frontend, REST ucu, yanıt üretimi.
  Yüzey 25 araçtır (H0 8 + H1 11 + H2 5 + H3 1).
- Kanıt: `test_agent_h3_contract.py`, `test_agent_h3_evidence.py`,
  `test_agent_h3_transport.py`, `test_obsidian_evidence.py` (75 test).
- Ayrıntı: `h3-retrieval-evidence.md`, `h3-tool-contract.md`, `h3-setup.md`.

---

## H3.2 — Son Köken Düzeltmesi ✅ Tamamlandı

**Soru:** *Gösterdiğimiz yol, gerçekten gittiğimiz yol mu?*

- **Backlink hop'u getirme yönünü izler:** `from_ref` çapa notu, `to_ref`
  bağlantıyı kuran nottur. Ardışık hop'lar artık bitişik
  (`hop[i].to_ref == hop[i+1].from_ref`) ve kasa kanıtının son hop'u kaynağın
  kendisine işaret eder.
- **Tek satıra düşen kırpma locator'ı günceller:** global bütçe snippet'i odak
  satırının önekine indirdiğinde `line_start == line_end == odak satırı` yazılır.
- **Odak satırı eşleşen satırdır:** `Excerpt.focus_line` dışa verilir; kırpma
  kanıtın dayanağını korur (aksi hâlde öğe düşüyordu).
- Kanıt: `assert_continuous_path` yardımcısı + 5 regresyon testi.

---

## H4 — Local Model Router ✅ Tamamlandı

**Soru:** *Hangi iş hangi yerel modelle yapılmalı?*

- **Tek araç:** `forkos_local_cognition` (H4 sonrası yüzey 26; H5 ile 27). Hermes hangi primitifi
  istediğini **açıkça** söyler; H4 hedef ayrıştırmaz.
- **Üç aktif lane:** `classify`, `structured_extract`, `query_rewrite`.
  `rerank` H4.1'e, `compress` H4.x/H5'e ertelendi; `reason`/`chat`/`answer`/
  `plan` reddedilir (muhakeme Hermes'e aittir).
- **Sinyal ≠ politika ≠ karar:** yönlendirme saf ve deterministiktir; `route_task`
  metni hiç görmez, bu yüzden "prompt zor görünüyor" diye karar veremez.
- **Slot seçimi:** `local-small` → `local-medium`. Medium yalnızca small
  yapılandırılmamış/sağlıksız/bütçesi yetmiyor/doğrulamada tükendiyse seçilir.
- **Model önerir, doğrulayıcı karar verir:** şema, kaynak kanıtı (birebir
  `source_excerpt`), tarih/saat, etiket ve korunan terim denetimleri deterministik.
- **Sınırlı tekrar:** small ≤2, medium ≤1, toplam ≤3 çağrı; yukarı yapışkan
  (small → medium → dur). Zincir tükenirse `needs_escalation`; **arka planda
  buluta düşülmez**.
- **Yalnız loopback:** `localhost`/`127.0.0.1`/`::1`; yönlendirme izlenmez,
  proxy devralınmaz, araç verilmez, çalışma zamanında model indirilmez.
- **Yazma yok:** Entity/Link/Event/Todo/Vault/Sıcak Hafıza'ya dokunmaz; DB
  oturumu açmaz, kasa okumaz, bağlam toplamaz.
- **Eval + canlı ölçüm:** 43 sentetik vaka (`docs/hermes/evals/h4-routing.yaml`),
  betikli sağlayıcıyla tam tekrar; gerçek modelle üç lane doğrulandı.
- Kanıt: `test_h4_models.py`, `test_h4_policy.py`, `test_h4_service.py`,
  `test_h4_ollama.py`, `test_agent_h4_contract.py`, `test_agent_h4_transport.py`,
  `test_h4_live.py`.
- Ayrıntı: `h4-local-cognition.md`, `h4-tool-contract.md`, `h4-setup.md`.
- Ayrıntı: `h4-local-cognition.md`, `h4-tool-contract.md`, `h4-setup.md`.

---

## H4.1 — Source Grounding & Routing Semantics ✅ Tamamlandı

**Soru:** *Kabul edilen her değer kaynaktan savunulabilir mi, ve her gerekçe
olguya uygun mu?*

- **Kaynak temellendirme zinciri:** `source_excerpt` → `date_text`/ham alan →
  normalize değer. Gerçek bir alıntı eklemek uydurma normalize alanı
  meşrulaştırmaz; `date_text` alıntının parçası olmalı
  (`SOURCE_FIELD_NOT_SUPPORTED`), normalize tarih deterministik çözümle
  uyuşmalı (`INVALID_DATE`), saat/gün kaynaktan çıkarılanla eşleşmeli
  (`INVALID_TIME`).
- **Deterministik zamansal ayrıştırıcı:** TR+EN, sürüm-tanımlı küçük biçim
  kümesi (ISO, DD.MM.YYYY, DD/MM/YYYY, `D Ay YYYY`, `Month D, YYYY`, gün/ay
  aralıkları, `X ile Y` / `X to Y`, `HH:MM`, hafta günleri). Takvim doğrulaması
  gerçek; doğal dil anlama YOK; yeni bağımlılık YOK.
- **Muhafazakâr null:** desteklenmeyen/biçim belirsizse normalize alan `null`
  kalır ve bu GEÇERLİDİR — eksik normalizasyon, uydurma normalizasyondan iyidir.
- **Sağlayıcı düşmesi tipik durum:** sağlık probu başarısızsa
  `needs_escalation` + `MODEL_PROVIDER_UNAVAILABLE` + `attempts=[]`; ham
  `ProviderError` sızmaz, `LOCAL_COGNITION_FAILED` üretilmez (MCP'de
  `is_error=false`).
- **Yükseltme ≠ seçim:** `LOCAL_MEDIUM_SELECTED` ilk yönlendirme kararıdır
  (`escalated=false`); `ESCALATED_TO_LOCAL_MEDIUM` yalnızca small denendikten
  sonra yukarı çıkıldığında görünür (`escalated=true`). Bütçe aşımı artık
  `LOCAL_MEDIUM_CONTEXT_EXCEEDED` ile "kullanılamaz"dan ayrılır.
- Kanıt: `test_h4_temporal.py`, `test_h4_grounding.py` + servis/politika/taşıma
  regresyonları; eval 50 vaka (7 yeni düşmanca vaka, deneme-kodu doğrulamasıyla).
- **Sıradaki (H4.2 araştırma):** CrossEncoder rerank değerlendirmesi, sorgu
  yeniden yazımı ayarı, bağlam sıkıştırma araştırması.

---

## H5 — Consolidation & Review Intelligence ✅ Tamamlandı

**Soru:** *Biriken bilgi nasıl özetlenir?*

- **Tek araç:** `forkos_review_intelligence` (yüzey 27) — beş mod:
  `continuity`, `daily_close`, `weekly_review`, `period_delta`,
  `consolidation_review`. Hermes hangi soruyu sorduğunu söyler; H5 mod seçmez.
- **%100 salt-okunur:** hiçbir mod Event/Todo/Review/Vault/hot memory yazmaz;
  parmak iziyle kanıtlanır. Kalıcı aday tablosu, arka plan işçisi ve zamanlayıcı
  YOKTUR; özetleme yazma değildir.
- **Fact / candidate / suggestion:** her çıktı `support_refs` taşır ve
  "önerilen aksiyon" diye bir alan yoktur. Opak puan, güven yüzdesi, üretkenlik
  veya ruh hali metriği üretilmez.
- **Süreklilik çapası gerçek damgadır:** `explicit` → `last_meaningful_activity`
  → `previous_review` → `fallback`; hiçbiri yoksa tarih uydurulmaz.
- **Kaynaklı terfi adayları:** günlük notlar + olaylar sınırlı bir pakete girer,
  H4 `consolidation_candidates_v1` sözleşmesiyle aday çıkarır, her aday alıntısı
  kaynağa geri eşlenir; belirsiz alıntı aday ÜRETMEZ
  (`AMBIGUOUS_CANDIDATE_SOURCE`).
- **Bilgi sağlığı adayları:** eskime (`operational_state_newer_than_managed_note`),
  olası yerine geçme (yalnızca H4 sınıflandırması + H3 kanıtı varsa) ve
  yapısal yeniden yüzey. Not asla yeniden yazılmaz, silinmez, geçersiz kılınmaz.
- **Bozulmada dürüstlük:** H4 kapalı → deterministik çıktı korunur
  (`H4_UNAVAILABLE`); kasa erişilemez → bilgi okuması yapılmaz
  (`VAULT_UNAVAILABLE`); çelişkili kimlik → `CONFLICTING_KNOWLEDGE`; eksik günlük
  not → `MISSING_DAILY_NOTES`; kısmi dönem → sayısal karşılaştırma yapılmaz.
- Kanıt: `test_h5_*.py`, `test_agent_h5_*.py`, `test_review_priority_receipts.py`
  ve gerçek `/mcp` taşıma testleri; ayrıntı `h5-review-intelligence.md`,
  `h5-tool-contract.md`, `h5-source-and-consolidation-policy.md`.
- **H6'ya kalan:** proaktif/zamanlanmış devreye girme, bildirim kanalları,
  brifing sunumu (Today widget/terminal). H5 yalnızca sorulduğunda cevap verir.

### H6.1 — Correctness Hardening ✅ Tamamlandı

Bağımsız denetimde bulunan dört doğruluk açığı kapatıldı; **yeni özellik
eklenmedi**, mimari korundu.

- **Aday sözleşmesi:** aralık dışı son tarih (T-31 normal, T-15 takip) aday
  DEĞİLDİR; `None` aday listesine giremez, ihlal `INVALID_CANDIDATE` ile
  raporlanır.
- **Koşul kimliği:** `entity` kimliği ≠ temporal koşul kimliği. Aynı fırsatın
  ilan son tarihi, takip tarihi ve her görüşmesi ayrı koşullardır; stale iptal
  ve snooze devralma kapsamı koşul kimliğidir. Anahtar `deadline:v2:...`;
  revizyon datetime için saat duyarlıdır.
- **Digest muhasebesi:** `delivered` yalnızca bildirime GERÇEKTEN giren üye
  için yazılır; parti kimliği üye kümesinden türer, taşan üyeler kuyrukta kalır.
- **Açılış sırası:** dakikalık H6 turu, kaynak tazeleme + H6 telafisi
  tamamlandıktan sonra kaydedilir (bayat durumdan bildirim üretilmez).
- Kanıt: `test_h6_deadline_identity.py` (B1–B5b, S1–S2), `test_h6_service.py`
  (C1–C4), `test_h6_worker.py` (D1), `test_h6_rules.py` (A1–A2) +
  `docs/hermes/evals/h6-proactivity.yaml` (50 vaka, 21 negatif).

**H7 bu sertleştirme sürümünde ele alınmadı.**

---

## H6 — Proactive / Scheduled Agent ✅ Tamamlandı

**Soru:** *Kullanıcı sormadan ne zaman devreye girmeli?*

- **Tek araç:** `forkos_proactivity` (H6 sonrası yüzey 28; H7 ile 29) — yedi işlem: `status`,
  `configure`, `rule_set`, `snooze`, `unsnooze`, `history`, `evaluate_now`.
  Hermes hangi kararı istediğini söyler; H6 kural seçmez.
- **Opt-in:** ana anahtar `proactivity.enabled` varsayılan **false**. Kapalıyken
  hiçbir H6 bildirimi çıkmaz; bekleyen koşular tarihsel kalır ve tekrar
  açıldığında **güncel** durumla yeniden değerlendirilir.
- **Kapalı kural kümesi (6):** `morning_continuity`, `daily_close`,
  `weekly_review`, `deadline_staircase`, `continuity_gap`, `project_stalled`.
  Genel bir kural DSL'i, cron dizesi veya serbest istem YOKTUR; yeni davranış
  kod yazmak demektir. Kural ayarları da kapalı şemadır (bilinmeyen alan
  reddedilir).
- **Sonuçlar ve sessizlik:** `silent | defer | digest | surface | prepare`.
  Sessizlik **birincil sınıftır**: "yapacak bir şey yok" başarıdır. Tetik
  yalnızca "şimdi değerlendir" demektir; anlamlı içerik yoksa boş bildirim
  yerine sessizlik seçilir.
- **Karar saf ve deterministik:** `policy.decide()` veritabanı ve model
  çağrısı yapmaz; karar sırası kararlıdır (ana anahtar → kural → snooze →
  tekrar → cooldown → kuiet → odak → günlük bütçe → kategori). Opak puan,
  güven yüzdesi veya "AI skoru" YOKTUR; karar sınırlı gerekçe kodlarıyla
  açıklanır. **H6 v1'de "dokunayım mı?" sorusunu model cevaplamaz.**
- **Kalıcı koşu kimliği:** iki tablo (`proactivity_rule`, `proactivity_run`;
  migration `0060_proactivity`). `logical_trigger_key` UNIQUE'tir: idempotans
  veritabanında zorlanır, yalnızca zamanlayıcıya güvenilmez. Tablolar
  `source_run` ile aynı sınıftır (operasyonel kayıt) ve `subject_id` bilinçli
  olarak FK'sizdir; entity silinse bile "neden o gün dürtüldü" okunabilir kalır.
- **Yeniden doğrulama teslimden önce:** tetikleyici payload'una asla
  güvenilmez; koşul teslim anında güncel durumdan yeniden doğrulanır, ortadan
  kalktıysa iptal edilir.
- **Tek worker işi:** `proactivity_tick` (1 dakika, `max_instances=1`,
  `coalesce=True`) + açılışta bir kez `proactivity_catch_up` (kaynaklar
  tazelendikten **sonra**). Eski `morning_digest` ve `deadline_ladder` işleri
  emekliye ayrıldı; zamanlama semantiği yalnızca H6'nın durumundadır.
- **Otomatik mutasyon yok:** H6 hiçbir Todo/Project/Opportunity/Review/Vault/
  Hot Memory kaydını değiştirmez; Entity/Event üretmez. Yazma yolu H1'dir ve
  onay kapısından geçer. Dış push (e-posta/SMS/webhook) yoktur; teslim yalnızca
  `notification` tablosuna yazılır.
- Kanıt: `test_h6_policy.py` (karar tablosu, gerekçe kodlarının üretim yolu,
  opak alan yokluğu), `test_h6_models.py`, `test_h6_rules.py`,
  `test_h6_delivery.py`, `test_h6_service.py`, `test_h6_api.py`,
  `test_h6_worker.py` ve gerçek `/mcp` taşıması dâhil
  `test_agent_h6_contract.py` / `test_agent_h6_transport.py`; değerlendirme
  seti `docs/hermes/evals/h6-proactivity.yaml` (42 sentetik vaka, 20'si
  sessizlik/erteleme; saf politika vakaları `policy.decide()` ile birebir
  oynatılır).
- Ayrıntı: `h6-proactivity.md`, `h6-policy.md`, `h6-tool-contract.md`.

**H7 bu sürümde ele alınmadı**; H6 bilinçli olarak "ne zaman dokunmalıyız?"
sorusunda durur.

---

## H7 — Durable Decision & Bounded Execution ✅ Tamamlandı

**Soru:** *Onaylanan bir planı, yarıda kesilse bile doğru şekilde nasıl
yürütürüm?*

- **Tek araç:** `forkos_execution` (yüzey 29) — dokuz işlem: `prepare`, `get`,
  `list`, `approve`, `reject`, `respond`, `cancel`, `execute`, `status`.
  Hermes hangi adımı istediğini söyler; H7 plan seçmez, adım uydurmaz.
- **Zincir:** kanıt (H3/H5/H6) → öneri (Hermes) → plan → doğrulama → **insan
  kararı** → yürütme → makbuz. Halkalardan hiçbiri atlanamaz; modelin
  "approved" demesi bir halka değildir.
- **Sahiplik:** Hermes önerir, H7 doğrular/karar verir/yürütür, H1 mutasyon
  yapar. Adımlar H1'in **KAPALI** 11 eylem sözlüğünden seçilir ve argümanlar
  H1'in kendi Pydantic modelleriyle doğrulanır: serbest araç adı, shell, SQL,
  keyfî HTTP ve silme reddedilir (`app/integrations/agent/write_registry.py`).
- **Onay sunucu tarafıdır ve IMMUTABLE revizyona bağlanır:** revizyon
  `plan-v1:<sha256>` kanonik JSON'un özetidir (adımlar ordinal sıralı, argüman
  anahtarları sıralı, kanıt referansları sıralı + tekil; `created_at`, `state`
  ve onay alanları özete GİRMEZ). Model `approved=true` iddia etse bile kayıt
  yoksa yürütme `APPROVAL_REQUIRED` döner; plan değişirse eski onay
  `APPROVAL_STALE` olur.
- **Dört karar:** APPROVE, EDIT (aynı soy ağacında yeni revizyon; eski satır ve
  onayı tarihsel kayıt olarak kalır), REJECT, RESPOND (`input_required` →
  `draft`; cevap mutasyon ÜRETMEZ) + CANCEL. TTL 72 saattir: süresi geçen plan
  onaylanamaz (`PLAN_EXPIRED`).
- **Sınırlı yürütme:** `approved → executing` geçişi DB-destekli CAS ile
  sahiplenilir (ikinci eşzamanlı çağrı kaybeder); adımlar ordinal sırayla
  yürür; her adım öncesi hedef `updated_at` damgası yeniden doğrulanır; ilk
  hatada **DURULUR**; otomatik rollback/compensation YOKTUR; sonuç dürüstçe
  `partial` olabilir.
- **Idempotans ve crash:** `execution_receipt` içinde `(plan_row_id, step_id)`
  UNIQUE'tir; tamamlanmış adım restart sonrası tekrar yürütülmez. Makbuz
  yazıldıktan sonra sonuç bilinmiyorsa adım körlemesine tekrarlanmaz:
  `RECONCILIATION_REQUIRED`.
- **Kalıcılık:** üç tablo (`execution_plan`, `execution_receipt`,
  `execution_decision`; migration `0061_execution`). Bunlar
  `source_run`/`proactivity_run` ile aynı sınıftır (operasyonel ajan/iş akışı
  kaydı) ve bilinçli olarak entity FK'si taşımaz.
- **Yürütme modele bağlı değildir:** plan hazır ve onaylıysa yürütme
  deterministiktir; hiçbir yerel veya uzak model çağrılmaz.
- **Sınırlar:** 10 adım, 10 mutasyon, 8192 bayt argüman, 20 kaynak/kanıt
  referansı, 10 doğrulama hatası, 50 liste limiti, 3 soru.
- Kanıt: `test_h7_models.py` (revizyon determinizmi, durum makinesi, adım
  doğrulama), `test_h7_approval.py` (onay, TTL, hedef tazeleme, red, mükerrer
  prepare), `test_h7_execution.py` (yürütme, durma, kısmi sonuç, eşzamanlılık,
  mutabakat, modelsiz yürütme); değerlendirme seti
  `docs/hermes/evals/h7-execution.yaml` (36 sentetik vaka).
- Ayrıntı: `h7-execution.md`, `h7-state-machine.md`, `h7-approval-policy.md`,
  `h7-tool-contract.md`.

**H8 başlatılmadı.** Dış bildirim/haberleşme kanalları (e-posta, SMS, webhook),
bugün/terminal brifing sunumu ve yürütmenin kendiliğinden başlatılması bu
sürümde ele alınmaz: **external channels sonraki fazın konusudur.** H7 yürütmeyi
yalnızca açık bir çağrıyla başlatır; yürütmenin *ne zaman* başlayacağı sorusu
H6'nın karar alanıdır ve H6 canonical mutasyon yapmaz.

---

## A-Serisi — Yaşam Döngüsü, Süreklilik ve Anlamsal Terfi (A1 → A4)

Ajan oturumlarının yaşam döngüsünü gözleyen, Hermes harness'ı ile forkOS arasında hafif ve bütçeli bir süreklilik köprüsü kuran katman. A-serisi yeni bir kanonik durum sahibi DEĞİLDİR; forkOS operasyonel durumunu ve f0rknbrain bilgisini MCP dışındaki oturum sınırlarında köprüler.

**Sözleşilmiş taksonomi:**

```text
A1 — Lifecycle Bridge
A2 — Bootstrap & Source Continuity
A3 — Session Handoff & Episodic Memory
A4 — Semantic Promotion / Durable Memory      (CLOSED, A4.1 hardening)
A5 — Context Judge / Feedback layer           (BAŞLATILMADI)
```

### A1 — Lifecycle Bridge ✅ Tamamlandı
- Hermes oturum yaşam döngüsü kancaları: `session_start`, `turn_seen`, `session_finalize`.
- İçeriksiz, ucuz ve bağımsız metadata kaydı (`POST /api/agent/lifecycle/event`).
- `AgentSession` ve `AgentSessionTurn` modelleri (migration `0063_agent_lifecycle`).
- Ayrıntı: `a1-lifecycle-bridge.md`.

### A1.1 — Lifecycle Bridge Hardening ✅ Tamamlandı
- **Kaynak Değişmezliği İnvariantı (`A1.1.1`):** 18 operasyonel model (H7 yürütme tabloları dahil) ve Vault/H2 üzerinde sıfır mutasyon garantisi (`test_agent_lifecycle_invariants.py`).
- **Katı 2xx Başarı Semantiği (`A1.1.2`):** Yalnızca `200 <= status < 300` durum kodları başarı kabul edilir; 3xx/4xx/5xx durumlarında fail-open çalışarak Hermes turunu asla çökertmez (`test_hermes_lifecycle_plugin.py`).

### A2 — Bounded Bootstrap & Continuity ✅ Tamamlandı
- **Tek HTTP Round-Trip:** `pre_llm_call` kancasında `POST /api/agent/lifecycle/turn` üzerinden bağımsız A1 commit'i ve salt-okunur A2 bağlam üretimi.
- **Fail-Open Hata İzolasyonu:** A2 arızası A1 commit'ini geri almaz; `degraded_reasons` ile 200 döner.
- **Bütçeli İlk Tur Bağlamı:** Kimlik/güvenlik ilkeleri, aktif projeler (≤5), son tarihler (≤5), yakın H5 sürekliliği ve H2 sıcak hafıza (≤6) ile 4000 karakter bütçeli `<forkos-context>`.
- **Sonraki Turlar İçin Kaynak Devamlılığı:** Ambiguous continuation durumunda 60 dk TTL'li kaynak reuse (`<forkos-continuity>`); topic shift durumunda eski kaynak invalidation ve sınırlandırılmış arama. Tam bootstrap asla tekrarlanmaz.
- **Güvenlik ve Gizlilik:** Geçici kullanıcı promptları asla saklanmaz, prompt injection XML escaping savunması, mutlak sistem yollarının maskelenmesi (`<vault>`), sıfır dış ağ çağrısı.
- **Destek Modelleri:** `agent_session_context` ve `agent_session_source` (migration `0064_agent_continuity`).
- Ayrıntı: `a2-bootstrap-continuity.md`.

### A3 — Session Handoff & Episodic Memory ✅ Tamamlandı
- **Kaynağa bağlı epizodik devir:** `post_llm_call` turu gözler, `on_session_finalize` oturumu mühürler, yeni oturumun İLK turunda en fazla bir önceki ilgili devir enjekte edilir (`<forkos-handoff version="1">`).
- **Ham transkript kalıcılaşmaz:** A3'ün üç tablosunda ham mesaj/yanıt/transkript kolonu YOKTUR; yerine alan-ayrılmış tur digest'i saklanır. `conversation_history` forkOS'a hiç gönderilmez.
- **Epistemik dürüstlük:** her ifade `turn_derived` / `canonical_supported` / `observed_during_session` sınıflarından birini taşır. Session decision ≠ authorization; tarihsel ≠ güncel doğru.
- **H4 ve H5 yeniden kullanılır:** `episodic_turn_v1` dar çıkarım sözleşmesi + deterministik grounding; mühürlemede H5 oturum-penceresi zemini. Yeni özetleyici veya ikinci biliş yolu yoktur.
- **Destek Modelleri:** `agent_session_episode`, `agent_session_episode_turn`, `agent_session_episode_item` (migration `0066_agent_episode`).
- Ayrıntı: `a3-episodic-handoff.md` · Uçtan uca koşu: `walkthrough.md`.

### A4 — Semantic Promotion / Durable Memory (CLOSED, A4.1)

A4 adayları A3'ün uygun mühürlü öğeleri ve isteğe bağlı kanonik event'lerden H5 consolidation ile çıkarılır. Aday kanonik doğru değildir. Kullanıcı incelemesi, `ready` kapısı, kaynak tazeliği, açık tek-kart supersession seçimi ve kopya koruması sonrasında H2 veya f0rknbrain'e terfi edebilir. Operasyonel/prosedürel yönlendirme kanonik yazma yapmaz; sahip eylemi gerektirir. Opt-out ham metin kalıcılaşmadan A3 turunda belirlenir. Ayrıntı: `a4-semantic-promotion.md`.

### A5 — Context Judge / Feedback layer (BAŞLATILMADI)

Enjekte edilen bağlamın ve ajan yanıtlarının kalitesini/kanıt doğruluğunu değerlendiren geri bildirim katmanı henüz uygulanmadı. A4 kendi çıkarımını otomatik doğrulamaz.

---

## Değişmez ilkeler (tüm fazlar)

1. **İnsan onayı her mutasyonun önündedir.** Otonomi, onayın yerini almaz.
2. **Tek sahiplik:** operasyonel durum forkOS'ta, bilgi f0rknbrain Vault'unda.
3. **Domain otoritesi:** iş kuralları canonical servislerde yaşar; ajan katmanı
   kopyalamaz.
4. **Backend-yerel sınır:** ajan araçları kendileri dış model/servis
   ÇAĞIRMAZ ve H0/H1/H2/H3 işlemleri dış ağ çağrısı yapmaz (H3 kanıt getirmesi
   dahil: 0 HTTP, 0 DNS, 0 dış soket). Verinin makineden
   çıkıp çıkmaması, yapılandırılmış ajan/model sağlayıcısına bağlıdır: MCP
   sonuçlarını harness tüketir ve uzak bir model kullanılıyorsa bağlam oraya
   gidebilir. "Uçtan uca yerel" ancak model çalıştırma yolu yerelleştikten
   sonra iddia edilebilir.
5. **Silme yok:** ajan yüzeyinde yıkıcı yetenek bulunmaz.
6. **Sessiz yedek yok:** bir yazma başarısızsa hata olarak kalır; başka bir
   depoya düşülmez.
