# forkOS × Hermes — Evrimsel Yol Haritası (H-Serisi)

forkOS ile otonom ajan ekosistemini (Hermes) birleştiren vizyon; kademeli,
güvenli ve insan denetimini elden bırakmayan aşamalar halinde tasarlanmıştır.

```text
  H0 ✓            H1 ✓             H2              H3              H4              H5              H6
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

## H2 — Hot Memory (Sıradaki)

**Soru:** *Ajan neyi kalıcı olarak hatırlamalı?*

**Kapsam (planlanan):**

- Kullanıcı profili ve çalışma tercihleri için **Vault'ta** sıcak hafıza
  (`90 Agent/` altında yönetilen notlar).
- Hafıza adayları: oturum içinde öne çıkan kararların öneri olarak sunulması.
- Kullanıcı onayıyla kalıcılaştırma; onaysız yazma yok.

**Sınır (H1'den devredilen kural):**

- **Otomatik hafıza yazımı H1'de YOKTUR.** `brain_capture` ve
  `brain_save_to_entity` yalnızca kullanıcının niyeti bilgi kaydetmeyi
  içerdiğinde çağrılır. "Ajan bunu hatırlamalı" kararı H2'nin konusudur ve
  orada bile kullanıcı onayı gerektirir.
- Hafıza **Vault'ta** yaşar (bilgi sahipliği Faz 3 sınırı); forkOS
  veritabanına ajan hafızası tablosu eklenmez.
- Konuşma geçmişinin tamamı saklanmaz; yalnızca onaylanmış, sınırlı çıkarımlar.

**Açılmayacaklar:** sınırsız konuşma arşivi, kullanıcı davranışının sessizce
profillenmesi, hafıza yazımını tetikleyen arka plan işi.

---

## H3 — Retrieval & Evidence

**Soru:** *Bir iddiayı hangi kanıt destekliyor?*

- Yapısal ilişkiler (Entity–Link) ile Vault serbest metin/`[[wikilink]]` ağının
  birlikte kullanımı.
- Çok adımlı gezinme: proje → görevler → toplantı notları → geçmiş kararlar.
- Yanıtların kaynak göstermesi (hangi dosya, hangi alan, hangi olay).
- **Şimdilik yok:** embedding, vektör veritabanı, semantik reranker. H0'ın
  leksikal araması korunur.

---

## H4 — Local Model Router

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
4. **Local-only:** kişisel veri dış servise gitmez; yazmalar dış ağ çağrısı
   yapmaz.
5. **Silme yok:** ajan yüzeyinde yıkıcı yetenek bulunmaz.
6. **Sessiz yedek yok:** bir yazma başarısızsa hata olarak kalır; başka bir
   depoya düşülmez.
