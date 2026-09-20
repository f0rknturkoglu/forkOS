# forkOS × Hermes — Evrimsel Yol Haritası (H-Serisi)

forkOS ile otonom ajan ekosistemini (Hermes) birleştiren vizyon, kademeli, güvenli ve insan denetimini asla elden bırakmayan aşamalar halinde tasarlanmıştır.

```text
  H0 (Mevcut)         H1                 H2                 H3                 H4                 H5                 H6
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Temel    │    │   Günlük    │    │   Rehberli  │    │    Hafıza   │    │  Çok Adımlı │    │  Proaktif   │    │    Tam      │
│ Salt-Okunur │───>│   Brifing   │───>│   Öneriler  │───>│ Konsolidasy.│───>│   Akıl Yür. │───>│ Tetikleyic. │───>│   Otonom    │
│   Arayüz    │    │  Sentezi    │    │ (İnsan Onay)│    │   (Kasa)    │    │ & Semantik  │    │ & Rutinler  │    │   Eşlikçi   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

---

## Aşama Detayları

### H0 — Brain Interface Foundation (Tamamlandı)
- **Durum:** Tamamlandı ve Doğrulandı.
- **Kapsam:**
  - Streamable HTTP üzerinden FastAPI `/mcp` uç noktası.
  - 8 adet salt-okunur araç (`forkos_briefing`, `forkos_search`, `brain_read`, vb.).
  - %100 değişmezlik (DB ve Vault dosya sistemine sıfır yazma).
  - Deterministik leksikal Vault taraması (< 10 ms).
  - Loopback-only ve hassas veri filtreleme.

---

### H1 — Curated Daily Digest & Briefing Persona
- **Amaç:** Ajanın salt-okunur araçları kullanarak kullanıcıya özel, yüksek kaliteli sabah ve akşam brifingleri üretmesi.
- **Kapsam:**
  - Hermes için optimize edilmiş prompt ve persona tanımları.
  - Açık görevler, takvim blokları, tekrarlayan rutinler ve son tarihlerin sentezlenmesi.
  - İlgili Vault notlarından "günün odak konusu" önerileri çıkarma.
  - Kullanıcıya Telegram, Terminal veya forkOS Today widget'ı üzerinden sunum.

---

### H2 — Guided Action Proposals (Staged Mutations)
- **Amaç:** Ajanın doğrudan veritabanına yazmadan, kullanıcı onayına sunulacak "eylem teklifleri" üretebilmesi.
- **Güvenlik Sınırı (Human-in-the-Loop):**
  - Ajan doğrudan DB'ye satır ekleyemez / silemez.
  - Ajan bir teklif üretir (`proposal`): örneğin yeni bir görev, bir takvim bloğu veya durum güncellemesi.
  - Teklif, forkOS Inbox veya Today arayüzünde "Ajan Önerisi" kartı olarak belirir.
  - Kullanıcı tek tıkla kabul eder (`Approve`) veya reddeder (`Reject`). Yalnızca kabul edilen teklifler veritabanına işlenir.

---

### H3 — Memory & Long-Term Context Consolidation
- **Amaç:** Ajanın kullanıcı tercihlerini, kalıcı alışkanlıklarını ve proje kararlarını Vault içinde kurallara bağlı bir "sıcak hafıza" (hot memory) dosyasında konsolide etmesi.
- **Kapsam:**
  - Vault altında `00 Meta/Agent Memory.md` veya günlük özet notları oluşturma kuralları.
  - Olay günlüğündeki (event log) önemli kırılma anlarının haftalık olarak özetlenip kalıcı bilgiye dönüştürülmesi.
  - Operasyonel tarihçe ile f0rknbrain bilgi grafı arasındaki bağların güçlendirilmesi.

---

### H4 — Multi-hop Reasoning & Hybrid Retrieval
- **Amaç:** Yapısal ilişkisel varlıklar (Entity-Link) ile Vault'un serbest metin/wiki-link ağını birlikte kullanarak derin akıl yürütme.
- **Kapsam:**
  - Bir proje ele alındığında: projeye bağlı görevler, toplantı notları, geçmiş kararlar ve dış kaynaklar arasında otomatik çok adımlı gezinti.
  - Leksikal arama ile hafif yerel embedding tabanlı semantik aramanın hibrit (RRF) harmanlanması.

---

### H5 — Proactive Event Triggers & Routine Assistance
- **Amaç:** Kullanıcı sormadan, belirli durumlar gerçekleştiğinde ajanın devreye girmesi.
- **Kapsam:**
  - Yaklaşan kritik son tarihler (deadlines).
  - 3 günden uzun süredir tıkanmış (blocked) görevler veya duraklamış projeler.
  - Arka arkaya kaçırılan rutinler veya biriken RSS kaynakları.
  - Düşük gürültülü, yüksek sinyalli proaktif uyarılar.

---

### H6 — Full Autonomous Co-Pilot & Self-Optimizing Brain
- **Amaç:** forkOS + f0rknbrain üzerinde uçtan uca araştırma, planlama ve yürütme desteği sağlayan tam entegre yerel yapay zeka işletim sistemi.
- **Kapsam:**
  - Karmaşık projelerin otomatik kilometre taşlarına ve görev listelerine dönüştürülmesi.
  - Sürekli gelişen, kullanıcının çalışma tarzını öğrenen ve sistemi optimize eden kişisel yapay zeka ortağı.
