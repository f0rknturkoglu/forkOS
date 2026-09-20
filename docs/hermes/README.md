# forkOS × Hermes — Brain Interface

Hermes ve forkOS arasındaki resmi entegrasyon katmanı. Kişisel işletim sistemi
(forkOS) ve uzun vadeli bilgi deposunu (f0rknbrain Obsidian Vault) yapay zeka
ajanlarına **bounded** bir MCP yüzeyiyle açar.

Yüzey **H0 → H5** boyunca büyüdü ve bugün toplam **27** araçtır:

```text
H0   8 araç   operasyonel durum + bilgi kasası OKUMA
H1  11 araç   açıkça onaylanan güvenli YAZMALAR
H2   5 araç   f0rknbrain `90 Agent/Memory` içinde küratörlü sıcak hafıza
H3   1 araç   kökenli, sınırlı KANIT getirme (forkos_evidence)
H4   1 araç   YEREL biliş router'ı: sınıflandırma/çıkarım/yeniden yazım
H5   1 araç   GÖZDEN GEÇİRME zekâsı: süreklilik, gün kapanışı, haftalık,
              dönem deltası ve konsolidasyon adayları (forkos_review_intelligence)
```

> Bu dokümanın eski başlığı "Brain Interface Foundation (H0)" idi; H0 artık
> yüzeyin yalnızca ilk katmanıdır.

Bu arayüz, resmi Model Context Protocol (MCP) Python SDK'sı kullanılarak inşa edilmiştir ve FastAPI çalışma zamanı içine `/mcp` Streamable HTTP endpoint'i olarak entegre edilmiştir.

---

## 1. Zihinsel Model (Mental Model)

forkOS ekosistemi net sorumluluk sınırlarına sahip üç ana bileşenden oluşur:

```text
                           ┌────────────────────────┐
                           │         Hermes         │
                           │ (Agent Harness / LLM)  │
                           └───────────┬────────────┘
                                       │
                                       │ MCP (Streamable HTTP)
                                       ▼
                       ┌────────────────────────────────┐
                       │  forkOS Brain Interface (/mcp) │
                       │      27 Bounded MCP Tools      │
                       └───────────────┬────────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
     ┌───────────────────────┐                    ┌─────────────────────────┐
     │        forkOS         │                    │        f0rknbrain       │
     │   (Canlı Operasyon)   │                    │     (Kalıcı Bilgi)      │
     ├───────────────────────┤                    ├─────────────────────────┤
     │ • Ajanda / Today      │                    │ • Kavramsal Notlar      │
     │ • Görevler / Rutinler │                    │ • Günlük Yazılar        │
     │ • Proje Aşamaları     │                    │ • Proje Bilgi Notları   │
     │ • Fırsatlar & CRM     │                    │ • Araştırmalar          │
     │ • Olay Günlüğü        │                    │ • Kararlar & Wiki       │
     │ (PostgreSQL 16)       │                    │ (Obsidian Markdown)     │
     └───────────────────────┘                    └─────────────────────────┘
```

1. **forkOS (Operasyonel Yürütme):** Görevler, takvim, planlayıcı, rutinler, Pomodoro, öğrenme/SRS takibi, kariyer fırsatları ve bildirimlerin canlı durumunu tutar.
2. **f0rknbrain (İnsan Bilgisi & Kalıcı Hafıza):** Kullanıcının Obsidian Vault'unda Markdown formatında yaşayan notları, günlükleri, proje dökümantasyonunu ve fikirlerini barındırır.
3. **Hermes (Otonom Ajan):** Kullanıcı adına kararlar üreten, durum değerlendirmesi yapan harici ajan harness'ı. forkOS ile yalnızca standart MCP protokolü üzerinden konuşur.

---

## 2. H0 Kesin Sınırları ve Kapsam Dışı Alanlar

H0 aşamasında güvenlik, mahremiyet ve veri bütünlüğü en yüksek önceliktir. Aşağıdaki kurallar mutlaktır:

- **%100 Salt-Okunur (Zero Mutation):** H0 içinde hiçbir yazma, güncelleme veya silme aracı **bulunmaz**. Ne PostgreSQL veritabanında ne de Vault dosya sisteminde tek bir bayt dahi değiştirilemez.
- **Harici Ağ Çağrısı Yok (Local-Only):** Arayüz yalnızca yerel döngü (`127.0.0.1`) üzerinde çalışır. Dışarıya telemetri veya veri çıkışı yoktur. H4'ün yerel model çağrısı da yalnızca **loopback** üzerindedir (localhost/127.0.0.1/::1); başka bir adres yapılandırılamaz.
- **forkOS İçinde Embedding/Vektör DB Yok:** Semantik arama, embedding üretimi ve vektör veritabanı forkOS backend'inin işi DEĞİLDİR. forkOS deterministik leksikal tarama ve yapısal veri sunar; H3 kanıt getirmesi gömme/vektör kullanmaz.
- **H4 yerel modeli ÇALIŞTIRMAZ, yönlendirir:** çıkarımı yapılandırılmış yerel sağlayıcı (Ollama) yapar; forkOS yalnızca sınırlı istek gönderir, çıktıyı deterministik doğrular ve hiçbir uzak modele düşmez. Model önerir; doğrulayıcı karar verir.
- **Hafıza Konsolidasyonu Yok:** Ajanın uzun vadeli hafıza üretmesi veya hafızayı Vault'a geri yazması bu katmanların işi değildir (konsolidasyon H5'in gözden geçirme katmanının işidir ve H5 yalnızca **aday** üretir, hiçbir şey yazmaz; H2 yalnızca insan onaylı küratörlü hafıza tutar).
- **Dondurulmuş Not Tabloları:** Eski forkOS `note` ve `note_folder` tabloları salt arşivdir; diriltilmez ve arama sonuçlarına dahil edilmez.

---

## 3. Sağlanan MCP Araçları (27)

Arayüz toplam **27** bounded araç sunar: **8 salt-okunur** (H0) + **11 yazma**
(H1) + **5 sıcak hafıza** (H2) + **1 kanıt getirme** (H3) + **1 yerel biliş**
(H4) + **1 gözden geçirme** (H5). Yazma araçları `readOnlyHint=false` taşır ve
`trust: untrusted` bir istemcide kullanıcı onayı gerektirir.

### Okuma araçları (H0)

| Kategori | Araç Adı | Açıklama |
| --- | --- | --- |
| **Operasyonel** | `forkos_briefing` | Günlük ajanda, açık görevler, son tarihler, aktif projeler ve bildirimler paketi |
| **Operasyonel** | `forkos_search` | Aktif modüller (todo, project, opportunity, bookmark vb.) üzerinde yapısal arama |
| **Operasyonel** | `forkos_entity_context` | Belirli bir varlığın kimliği, derin linkleri, ilişkili nesneleri ve geçmişi |
| **Operasyonel** | `forkos_project_context` | Bir projenin durumu, kilometre taşları, görevleri ve Vault not işaretçisi |
| **Operasyonel** | `forkos_recent_activity` | Maskelenmiş ve temizlenmiş append-only olay geçmişi |
| **Bilgi** | `brain_status` | Obsidian Vault bağlantı durumu, erişim izinleri ve dosya istatistikleri |
| **Bilgi** | `brain_search` | Vault içindeki tüm güvenli Markdown dosyalarında deterministik leksikal arama |
| **Bilgi** | `brain_read` | `forkos_id` veya `relative_path` ile sınırlandırılmış güvenli Markdown okuyucu |

### Yazma araçları (H1)

| Kategori | Araç Adı | Açıklama |
| --- | --- | --- |
| **Görev** | `forkos_todo_create` | Tek görev oluşturur; `plan_day` plan kaydını da yazar |
| **Görev** | `forkos_todo_update` | Görev metadata'sını günceller (durum/silme hariç) |
| **Görev** | `forkos_todo_complete` | Canonical tekrar kurallarıyla tamamlar |
| **Görev** | `forkos_todo_plan` | Plan slotunu oluşturur/yeniden zamanlar |
| **Proje** | `forkos_project_update` | Yalnızca operasyonel `next_action` alanı |
| **Fırsat** | `forkos_opportunity_transition` | Keşif/duyuru yaşam döngüsü geçişi |
| **Fırsat** | `forkos_application_transition` | Başvuru CRM hattı geçişi |
| **Yer imi** | `forkos_bookmark_capture` | Yerel yer imi kaydı (ağ erişimi yok) |
| **Yer imi** | `forkos_bookmark_update` | Koleksiyon, favori, okuma durumu, etiketler |
| **Bilgi** | `brain_capture` | Vault `00 Inbox/` içine yeni bilgi notu |
| **Bilgi** | `brain_save_to_entity` | Yönetilen bilgi notuna metin EKLER |

### Sıcak hafıza araçları (H2)

| Kategori | Araç Adı | Açıklama |
| --- | --- | --- |
| **Hafıza** | `hot_memory_context` | Aktif sıcak hafıza paketi (sınırlı bütçe, deterministik sıralama) |
| **Hafıza** | `hot_memory_list` | Yönetim/keşif listesi (leksikal arama, emekli/süresi geçmiş dâhil) |
| **Hafıza** | `hot_memory_store` | Onaylanmış tek öğe oluşturur (`90 Agent/Memory/`) |
| **Hafıza** | `hot_memory_update` | `expected_revision` ile düzeltir |
| **Hafıza** | `hot_memory_retire` | Kullanmayı bırakır (silmez) |

### Kanıt getirme aracı (H3)

| Kategori | Araç Adı | Açıklama |
| --- | --- | --- |
| **Kanıt** | `forkos_evidence` | Bir soru/iddia için kökenli, sınırlı kanıt paketi: yapısal grafik + olay geçmişi + yönetilen kasa notları + tek kasa hopu + deterministik leksikal eşleşme. Yanıt ÜRETMEZ; `EvidenceBundle` döner. Salt-okunur. |

### Yerel biliş aracı (H4)

| Kategori | Araç Adı | Açıklama |
| --- | --- | --- |
| **Biliş** | `forkos_local_cognition` | Açıkça seçilen TEK yerel primitifi yürütür: `classify`, `structured_extract` (sürümlü sözleşmeler), `query_rewrite`. Model önerir, deterministik doğrulayıcı karar verir; zincir tükenirse `needs_escalation`. Yalnız loopback model trafiği; yazma yok, bağlam toplamaz. |

### Gözden geçirme aracı (H5)

| Kategori | Araç Adı | Açıklama |
| --- | --- | --- |
| **Gözden geçirme** | `forkos_review_intelligence` | Kanonik duruma bağlı, sınırlı ve deterministik gözden geçirme: `continuity` ("nerede kalmıştım?"), `daily_close`, `weekly_review`, `period_delta`, `consolidation_review`. Her olgu `support_refs` ve `source_manifest` taşır; terfi/bilgi sağlığı/yeniden yüzey çıktıları **adaydır**, doğruluk değildir. Hiçbir şey yazmaz (Review/Todo/Entity/Event/Vault/Sıcak Hafıza mutasyonu ve otomatik özet saklama yok). Yerel model yardımı (H4) isteğe bağlıdır ve yokluğunda çıktı deterministik kalır. Salt-okunur. |

Ayrıntılı sözleşmeler: [H1 Araç Sözleşmesi](h1-tool-contract.md) ·
[Onay modeli](h1-safe-actions.md) ·
[H2 Sıcak Hafıza](h2-hot-memory.md) ·
[H2 Araç Sözleşmesi](h2-tool-contract.md) ·
[H2 Hafıza Politikası](h2-memory-policy.md) ·
[H2 Kurulum](h2-setup.md) ·
[H3 Kanıt Getirme](h3-retrieval-evidence.md) ·
[H3 Araç Sözleşmesi](h3-tool-contract.md) ·
[H3 Kurulum](h3-setup.md) ·
[H4 Yerel Biliş](h4-local-cognition.md) ·
[H4 Araç Sözleşmesi](h4-tool-contract.md) ·
[H4 Kurulum](h4-setup.md) ·
[H5 Gözden Geçirme Zekâsı](h5-review-intelligence.md) ·
[H5 Araç Sözleşmesi](h5-tool-contract.md) ·
[H5 Kaynak ve Konsolidasyon Politikası](h5-source-and-consolidation-policy.md)

---

## 4. Dökümantasyon Dizini

- [Teknik Mimari ve Lifespan Entegrasyonu](h0-brain-interface.md): Streamable HTTP mimarisi, FastAPI yaşam döngüsü ve doğrudan Vault tarama tasarımı.
- [Araç Sözleşmeleri ve Şemalar](h0-tool-contract.md): 8 aracın tüm parametre şemaları, yanıt zarfları ve örnek JSON çıktıları.
- [Hermes Kurulum Rehberi](h0-setup.md): Hermes yapılandırması, yerel bağlantı adımları ve test yöntemleri.
- [H3 Kanıt Getirme](h3-retrieval-evidence.md): kanıt modeli, kanallar, öncelik katmanları, köken zincirleri ve dürüstlük semantiği.
- [H3 Araç Sözleşmesi](h3-tool-contract.md): `forkos_evidence` imzası, sınırlar, hata kodları ve örnek çıktı.
- [H3 Kurulum ve Doğrulama](h3-setup.md): testler, ölçümler ve sorun giderme.
- [H4 Yerel Biliş](h4-local-cognition.md): sorumluluk paylaşımı, lane'ler, yönlendirme politikası, sınırlı tekrar ve gizlilik sınırı.
- [H4 Araç Sözleşmesi](h4-tool-contract.md): imza, sınırlar, kodlar ve örnek çıktı.
- [H4 Kurulum ve Doğrulama](h4-setup.md): yapılandırma, model kurulumu, sorun giderme.
- [H5 Gözden Geçirme Zekâsı](h5-review-intelligence.md): sorumluluk paylaşımı, olgu/aday/öneri ayrımı, beş mod, süreklilik felsefesi ve bozulmuş mod davranışı.
- [H5 Araç Sözleşmesi](h5-tool-contract.md): imza, mod/argüman kuralları, zaman semantiği, sınırlar, kodlar ve örnek çıktı.
- [H5 Kaynak ve Konsolidasyon Politikası](h5-source-and-consolidation-policy.md): episodic ≠ semantic, aday ≠ hafıza, kaynak kilidi, varış yeri politikası ve kapsam dürüstlüğü.
- [H-Serisi Yol Haritası (H0 → H6)](roadmap.md): Beyin arayüzünün H0 temelinden H6 tam otonom eşlikçiye evrilme planı.
