# forkOS — Future Agent Boundary & Context Architecture

Bu doküman, gelecekte forkOS üzerine inşa edilecek otonom ajan/yapay zeka katmanının veri sınırlarını, bağlam (context) hiyerarşisini ve bilgiye erişim stratejisini tanımlar.

> [!IMPORTANT]
> Bu aşamada hiçbir Ajan, LLM, RAG, Embeddings veya Vector DB **implement edilmez**. Bu doküman yalnızca hibrit mimarinin veri sınırlarını netleştirmek içindir.

---

## 1. Üç Katmanlı Bağlam Modeli (Three Context Tiers)

Gelecekteki bir kişisel asistan ajanın doğru kararlar verebilmesi için veriyi tek bir dev havuza dökmek yerine üç farklı hız ve kalıcılık katmanında ele alması gerekir:

```text
┌──────────────────────────────────────────────────────────┐
│ 1. CANLI DURUM (Live State) — forkOS                     │
│    Anlık operasyonel gerçeklik (REST API / JSON / DB)    │
├──────────────────────────────────────────────────────────┤
│ 2. UZUN VADELİ BİLGİ (Long-Term Knowledge) — Vault       │
│    İnsan düşüncesi, kararlar, araştırmalar (Markdown)    │
├──────────────────────────────────────────────────────────┤
│ 3. SICAK BELLEK (Hot Curated Memory) — 90 Agent/         │
│    Ajanın damıttığı profil, hedefler, kısıtlar           │
└──────────────────────────────────────────────────────────┘
```

### 1.1 Canlı Durum (Live State — forkOS)
Ajanın "Şu an ne oluyor?" sorusuna yanıt aradığı yerdir:
- **Görevler & Rutinler:** Açık işler, ertelenenler, öncelikler, alt görevler.
- **Zaman & Planlama:** Günlük ajanda, takvim etkinlikleri, Pomodoro / odak seansları.
- **Öğrenme İlerlemesi:** SRS tekrar sırası, aktif kurslar, çalışma süreleri.
- **Dış Kaynaklar:** Yeni RSS girdileri, gelen kutusu (inbox), iş fırsatları.
- **Sistem Durumu:** Bildirimler, arka plan otomasyon durumu, sağlık logları.

*Erişim Biçimi:* forkOS yerel REST API (`127.0.0.1:8787`). Hızlı, yapılandırılmış, filtrelenebilir.

### 1.2 Uzun Vadeli Bilgi (Long-Term Knowledge — Obsidian Vault)
Ajanın "Geçmişte ne karar verdik? Bu konu hakkında ne biliyoruz?" sorusuna yanıt aradığı yerdir:
- **Proje Bilgisi:** Mimari tercihler, teknik gerekçeler, hedefler (`20 Projects/`).
- **Araştırmalar & Notlar:** Derinlemesine okumalar, teknik sentezler (`30 Knowledge/`).
- **Kariyer:** CV detayları, başvuru stratejileri, mülakat notları (`50 Career/`).
- **Öğrenme:** Kavramsal ders notları, problem çözümleri (`40 Learning/`).
- **Yazılı Günlükler:** İnsanın kendi duygusal ve mesleki yansımaları (`10 Daily/`).

*Erişim Biçimi:* Yerel dosya sistemi (Markdown).

### 1.3 Sıcak Bellek (Hot Curated Memory — `90 Agent/`)
Ajanın her işlemde tüm Vault'u okumadan hızlıca erişebileceği kompakt, filtrelenmiş bilgi katmanı:
- **Kullanıcı Profili:** Değerler, iletişim tercihleri, dil alışkanlıkları (`90 Agent/Profile.md`).
- **Aktif Hedefler:** Bu çeyrekte odaklanılan 3 ana hedef (`90 Agent/Goals.md`).
- **Aktif Kısıtlar:** "Şu kütüphaneyi kullanma", "Hafta sonu iş görevi planlama" (`90 Agent/Constraints.md`).
- **Son Kritik Kararlar:** En son alınan stratejik mimari kararlar.

---

## 2. Sıfır Veritabanı Yansıtması (No Database Mirroring)

Ajanın Obsidian Vault'taki dosyaları okumak için bu dosyaları PostgreSQL'e kopyalaması (mirror) **GEREKMEZ**.
- Vault doğrudan disk üzerinde düz Markdown dosyalarından oluşur.
- Dosyaları PostgreSQL'e kopyalamak:
  1. İki yönlü senkronizasyon (two-way sync) çatışmaları yaratır.
  2. Veri boyutunu ikiye katlar.
  3. Kullanıcının Obsidian'da yaptığı bir değişikliğin forkOS'a gecikmeli yansımasına sebep olur.
- forkOS yalnızca hafif bir dosya indeksi (`forkos_id` -> dosya yolu) tutar; metnin kendisi diskte kalır.

---

## 3. Aşamalı Bilgi Getirme Mimarisi (Retrieval Stages)

Gelecekteki bilgi getirme stratejisi gereksiz karmaşıklık eklemeden, kademeli olarak inşa edilmelidir:

### Aşama 1: Metadata + Dosya Yolu + Metin Arama (Temel & Yeterli)
- Dosya adı ve `forkos_id` üzerinden doğrudan dosya okuma.
- Belirli klasörlerde (`20 Projects/`, `30 Knowledge/`) hızlı yerel metin araması (Python dosya taraması veya yerel `ripgrep`).
- *Maliyet:* Sıfır ekstra bağımlılık, sıfır indeks gecikmesi. Birçok senaryo için tamamen yeterlidir.

### Aşama 2: Hafif Yerel FTS (İhtiyaç Doğarsa)
- Vault binlerce dosyaya ulaştığında SQLite FTS5 veya hafif bir yerel ters indeks (inverted index).
- *Maliyet:* Düşük bellek tüketimi, yerel süreç.

### Aşama 3: Semantik Arama / Vektör Gömüleri (Yalnızca Kanıtlanmış İhtiyaç Halinde)
- Yalnızca kelime bazlı aramanın yetersiz kaldığı kavramsal benzerlik sorguları için.
- Küçük yerel embedding modelleri (ör. `all-MiniLM-L6-v2` veya `bge-small-tr`).
- **Vektör Veritabanı Başlangıç Gereksinimi Değildir:** Yerel bir kişisel asistan için ilk günden Pinecone, Chroma veya Qdrant gibi harici vektör sistemleri kurmak aşırı mühendisliktir (over-engineering). İhtiyaç doğmadıkça eklenmeyecektir.
