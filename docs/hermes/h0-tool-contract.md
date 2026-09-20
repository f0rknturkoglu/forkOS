# forkOS × Hermes — H0 Araç Sözleşmeleri (Tool Contracts)

Bu belge, H0 aşamasında sunulan 8 salt-okunur MCP aracının şemalarını, parametrelerini, yanıt zarflarını ve hata formatlarını tanımlar.

---

## 1. Genel Yanıt Zarfı (`AgentResponseEnvelope`)

Tüm araçlar yanıtlarını standart bir meta zarf içinde döndürür:

```json
{
  "system": "forkos-brain",
  "version": "1.0",
  "timestamp": "2026-09-20T10:00:00.000000Z",
  "read_only": true,
  "data": { ... }
}
```

- `system`: Sabit `"forkos-brain"` değeri.
- `version`: Arayüz versiyonu (`"1.0"`).
- `timestamp`: UTC ISO 8601 zaman damgası.
- `read_only`: Her zaman `true`.
- `data`: Araca özgü tip güvenli veri yükü.

Hata durumlarında araç doğrudan MCP standardına uygun `ToolError` yükseltir; istemciye `isError: true` ve açıklayıcı hata mesajı döner (iç yığın izi verilmez).

---

## 2. Araç Detayları

### 1. `forkos_briefing`
Kullanıcının güncel durumunu özetleyen olgusal, hafif ve sınırlı günlük brifing paketini döndürür.

- **Açıklama:** `"Get a factual, bounded operational day briefing packet (agenda, open todos, active projects, learning due, attention opportunities, unread notifications, vault status). Read-only. Does not modify forkOS or the Vault."`
- **Parametreler:** Yok (`{}`)
- **Veri Alanları (`data`):**
  - `today`: Günün tarihi (`YYYY-MM-DD`).
  - `agenda`: Bugünkü zaman blokları / plan slotları listesi.
  - `open_todos`: Açık görevler (başlık, öncelik, son tarih vb. max 20).
  - `deadlines`: Yaklaşan son tarihler listesi.
  - `active_projects`: Aktif projeler (id, başlık, durum, ilerleme yüzdesi).
  - `learning_due`: Bugün tekrar edilmesi gereken kart/öğrenme sayısı.
  - `opportunity_attention`: İnceleme bekleyen veya yaklaşan fırsat sayısı.
  - `unread_notifications`: Okunmamış veya ilgilenilmemiş bildirim sayısı.
  - `recent_activity_summary`: Son 24 saatteki olay sayıları özeti.
  - `vault_status`: Kasa bağlantı durumu özeti.

---

### 2. `forkos_search`
forkOS'taki aktif operasyonel modüller (todo, project, opportunity, bookmark vb.) üzerinde yapısal arama yapar. Dondurulmuş legacy notları aramaz.

- **Açıklama:** `"Search active operational entities across forkOS modules (todos, projects, bookmarks, opportunities, etc.). Excludes legacy notes. Read-only. Does not modify forkOS or the Vault."`
- **Parametreler:**
  - `query` (*string, zorunlu*): Arama terimi.
  - `entity_type` (*string, opsiyonel*): Belirli bir tip filtresi (örn: `"todo"`, `"project"`).
  - `limit` (*integer, opsiyonel, varsayılan: 10, max: 50*): Maksimum sonuç sayısı.
- **Yanıt:** `items: list[SearchEntityItem]`, `total_matched: int`.

---

### 3. `forkos_entity_context`
Belirli bir varlığın kimliğini, derin linklerini, bağlı diğer nesnelerini ve son aktivite geçmişini getirir.

- **Açıklama:** `"Get detailed operational identity, deep links, related entities, and recent activity for a specific entity UUID. Read-only. Does not modify forkOS or the Vault."`
- **Parametreler:**
  - `entity_id` (*string, zorunlu*): Varlığın UUID değeri.
- **Yanıt:**
  - `entity`: Kimlik, tip, başlık, oluşturulma/güncellenme zamanı.
  - `direct_links`: Bu varlığa bağlı veya bu varlıktan giden ilişkili varlıklar.
  - `recent_events`: Varlıkla ilgili son olaylar (maskelenmiş).
  - `vault_pointer`: Eğer varlığa bağlı bir Vault bilgi notu varsa dosya yolu ve linki.

---

### 4. `forkos_project_context`
Bir projenin durumunu, kilometre taşlarını, açık görevlerini ve Obsidian bilgi notu bağlantısını içeren kompakt operasyonel paketi döndürür.

- **Açıklama:** `"Get a compact operational context packet for a project (status, milestones, open todos, recent activity, and Obsidian vault note pointer). Read-only. Does not modify forkOS or the Vault."`
- **Parametreler:**
  - `project_id` (*string, zorunlu*): Projenin UUID değeri.
- **Yanıt:**
  - `project`: Proje adı, durumu, önceliği, rengi.
  - `milestones`: Kilometre taşları listesi.
  - `open_todos`: Projeye bağlı tamamlanmamış görevler.
  - `vault_note_path`: Varsa `20 Projects/<Proje>.md` yolu.
  - `vault_note_exists`: Kasa dosyasının fiziksel mevcudiyet durumu.

---

### 5. `forkos_recent_activity`
forkOS'un append-only olay günlüğündeki son aktiviteleri getirir. Hassas bilgiler (token, şifre vb.) filtrelenir.

- **Açıklama:** `"Get a sanitized list of recent operational events from the append-only event log. Sensitive keys are masked. Read-only. Does not modify forkOS or the Vault."`
- **Parametreler:**
  - `limit` (*integer, opsiyonel, varsayılan: 20, max: 100*): Döndürülecek maksimum olay sayısı.
  - `entity_type` (*string, opsiyonel*): Filtrelenecek varlık tipi.
- **Yanıt:** `events: list[SanitizedEventItem]`.

---

### 6. `brain_status`
f0rknbrain Obsidian Vault'unun yapılandırma, bağlantı ve dosya istatistiklerini raporlar.

- **Açıklama:** `"Get the health, connectivity, and statistics of f0rknbrain Obsidian Vault knowledge retrieval. Read-only. Does not modify forkOS or the Vault."`
- **Parametreler:** Yok (`{}`)
- **Yanıt:**
  - `configured`: Vault yolunun tanımlı olup olmadığı (`bool`).
  - `available`: Vault dizininin diskte mevcut ve okunabilir olup olmadığı (`bool`).
  - `vault_name`: Kasa adı (örn: `"f0rknbrain"`).
  - `vault_path`: Kasa dizin yolu.
  - `total_markdown_files`: Bulunan geçerli Markdown dosyası sayısı.
  - `managed_files`: forkOS tarafından yönetilen (`forkos_id` içeren) dosya sayısı.
  - `unmanaged_files`: Kullanıcının serbest Markdown dosya sayısı.

---

### 7. `brain_search`
f0rknbrain Vault'undaki tüm güvenli Markdown notlarında deterministik leksikal (metin tabanlı) arama yapar.

- **Açıklama:** `"Deterministic lexical search across all safe Markdown knowledge files in f0rknbrain Vault (managed and unmanaged). Read-only. Does not modify forkOS or the Vault."`
- **Parametreler:**
  - `query` (*string, zorunlu*): Arama terimi (büyük/küçük harf duyarsız alt dizi araması).
  - `scope` (*string, opsiyonel*): Dizin filtresi (örn: `"20 Projects"`, `"10 Daily"`).
  - `limit` (*integer, opsiyonel, varsayılan: 10, max: 50*): Maksimum sonuç sayısı.
- **Yanıt:**
  - `matches: list[BrainSearchMatchItem]`:
    - `relative_path`: Kasa içi göreli yol.
    - `title`: Not başlığı (H1 veya dosya adı).
    - `forkos_id`: Varsa bağlı forkOS UUID'si.
    - `is_managed`: forkOS tarafından yönetilip yönetilmediği.
    - `snippet`: Eşleşen satır ve bağlamı.
  - `total_matched`: Eşleşen toplam not sayısı.

---

### 8. `brain_read`
Vault içindeki belirli bir Markdown notunun içeriğini güvenli ve sınırlı bir biçimde okur.

- **Açıklama:** `"Read a bounded markdown note from the f0rknbrain Vault by forkos_id or relative_path, with optional heading extraction. Read-only. Does not modify forkOS or the Vault."`
- **Parametreler:**
  - `forkos_id` (*string, opsiyonel*): Notun frontmatter'ındaki `forkos_id` UUID'si.
  - `relative_path` (*string, opsiyonel*): Notun kasa içi göreli dosya yolu (örn: `"20 Projects/X.md"`).
  - `heading` (*string, opsiyonel*): Yalnızca belirli bir başlık altındaki bölümü okumak için başlık metni.
  - `max_chars` (*integer, opsiyonel, varsayılan: 20000, max: 50000*): Maksimum karakter limiti.
  *(Not: `forkos_id` veya `relative_path` parametrelerinden en az biri sağlanmalıdır.)*
- **Yanıt:**
  - `relative_path`: Okunan dosyanın yolu.
  - `title`: Not başlığı.
  - `forkos_id`: Varsa bağlı UUID.
  - `headings`: Dosyadaki tüm başlıkların listesi (`list[str]`).
  - `content`: İstenen metin içeriği (karakter sınırı uygulanmış).
  - `truncated`: İçeriğin `max_chars` sebebiyle kesilip kesilmediği (`bool`).

---

## 3. Örnek JSON Çağrı ve Yanıtı

### İstek: `brain_read`
```json
{
  "name": "brain_read",
  "arguments": {
    "relative_path": "20 Projects/Hermes Integration.md",
    "heading": "Architecture"
  }
}
```

### Yanıt:
```json
{
  "system": "forkos-brain",
  "version": "1.0",
  "timestamp": "2026-09-20T10:14:00.123456Z",
  "read_only": true,
  "data": {
    "relative_path": "20 Projects/Hermes Integration.md",
    "title": "Hermes Integration",
    "forkos_id": "8a32d184-b039-4d6f-9988-51821bc64808",
    "headings": ["Overview", "Architecture", "Roadmap"],
    "content": "### Architecture\nThe interface uses Streamable HTTP mounted in FastAPI at /mcp.",
    "truncated": false
  }
}
```
