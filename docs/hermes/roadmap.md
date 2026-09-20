# forkOS × Hermes — Evrimsel Yol Haritası (H-Serisi)

forkOS ile otonom ajan ekosistemini (Hermes) birleştiren vizyon; kademeli,
güvenli ve insan denetimini elden bırakmayan aşamalar halinde tasarlanmıştır.

```text
  H0 ✓            H1 ✓            H2 ✓            H3 ✓            H4              H5              H6
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  Gözler  │──>│  Eller   │──>│  Sıcak   │──>│  Kanıt   │──>│  Yerel   │──>│  Sentez  │──>│ Proaktif │
│ Salt-    │   │ Onaylı   │   │  Hafıza  │   │  & Geri  │   │  Model   │   │  & Brif. │   │  Ajan    │
│ Okunur   │   │ Eylemler │   │ (Vault)  │   │  Getirme │   │  Router  │   │          │   │          │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
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

## H4 — Local Model Router (Sıradaki)

**Soru:** *Hangi iş hangi yerel modelle yapılmalı?*

- Yerel modellerin (Ollama/MLX/llama.cpp sınıfı) görev tipine göre
  yönlendirilmesi; **local-only** kalır.
- **Şimdilik yok:** hiçbir model kurulumu, indirme veya dış sağlayıcı bağlama.

---

## H5 — Consolidation & Briefings

**Soru:** *Biriken bilgi nasıl özetlenir?*

- Haftalık/aylık konsolidasyon: olay geçmişinden kalıcı bilgiye dönüşüm.
- Kişiselleştirilmiş brifingler (sabah/akşam), kullanıcıya sunum kanalları
  (Today widget, terminal, bildirim).

---

## H6 — Proactive / Scheduled Agent

**Soru:** *Kullanıcı sormadan ne zaman devreye girmeli?*

- Yaklaşan kritik son tarihler, tıkanmış görevler, kaçırılan rutinler.
- Düşük gürültülü, yüksek sinyalli proaktif uyarılar.
- **H1'de yok:** arka plan yürütme, ajanın kontrol ettiği zamanlayıcı,
  otonom mutasyon. H6'da bile her yazma onay kapısından geçer.

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
