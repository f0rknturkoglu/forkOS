# forkOS × Hermes — Brain Interface Foundation (H0)

Hermes ve forkOS arasındaki ilk resmi entegrasyon katmanı olan **H0: Brain Interface Foundation**, kişisel işletim sistemi (forkOS) ve uzun vadeli bilgi deposunu (f0rknbrain Obsidian Vault) yapay zeka ajanlarına açan **salt-okunur, bounded ve yerel** bir arayüzdür.

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
                       │    8 Bounded Read-Only Tools   │
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
- **Harici Ağ Çağrısı Yok (Local-Only):** Arayüz yalnızca yerel döngü (`127.0.0.1`) üzerinde çalışır. Dışarıya telemetri, LLM çağrısı veya veri çıkışı yoktur.
- **forkOS İçinde LLM/Embedding/Vektör DB Yok:** Semantik arama, embedding üretimi veya dil modeli çalıştırma forkOS backend'inin işi değildir; bu sorumluluk Hermes'e aittir. forkOS yalnızca deterministik leksikal tarama ve yapısal veri sunar.
- **Hafıza Konsolidasyonu Yok:** Ajanın uzun vadeli hafıza üretmesi veya hafızayı Vault'a geri yazması H0 kapsamında değildir (H3'e ertelenmiştir).
- **Dondurulmuş Not Tabloları:** Eski forkOS `note` ve `note_folder` tabloları salt arşivdir; diriltilmez ve arama sonuçlarına dahil edilmez.

---

## 3. Sağlanan 8 Temel MCP Aracı

Arayüz tam olarak 8 adet bounded, deterministik ve salt-okunur araç sunar:

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

---

## 4. Dökümantasyon Dizini

- [Teknik Mimari ve Lifespan Entegrasyonu](h0-brain-interface.md): Streamable HTTP mimarisi, FastAPI yaşam döngüsü ve doğrudan Vault tarama tasarımı.
- [Araç Sözleşmeleri ve Şemalar](h0-tool-contract.md): 8 aracın tüm parametre şemaları, yanıt zarfları ve örnek JSON çıktıları.
- [Hermes Kurulum Rehberi](h0-setup.md): Hermes yapılandırması, yerel bağlantı adımları ve test yöntemleri.
- [H-Serisi Yol Haritası (H0 → H6)](roadmap.md): Beyin arayüzünün H0 temelinden H6 tam otonom eşlikçiye evrilme planı.
