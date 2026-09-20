# forkOS × Hermes — H0 Araç Sözleşmeleri (Tool Contracts)

Bu belge, H0 aşamasında sunulan 8 salt-okunur MCP aracının şemalarını, parametrelerini, yanıt zarflarını, doğrulama kurallarını ve hata formatlarını tanımlar.

> H1 ile arayüze 11 yazma aracı eklendi ve toplam yüzey 19'a çıktı. Yazma araçlarının tam sözleşmesi [`h1-tool-contract.md`](h1-tool-contract.md), onay modeli [`h1-safe-actions.md`](h1-safe-actions.md) içindedir. Bu belge yalnızca okuma yüzeyini tanımlar.

---

## 1. Genel Yanıt Zarfı (`AgentEnvelope[T]`)

Tüm araçlar yanıtlarını standart bir meta zarf içinde döndürür:

```json
{
  "as_of": "2026-09-20T10:00:00.000000Z",
  "source": "forkos",
  "data": { ... },
  "truncated": false
}
```

- `as_of`: UTC ISO 8601 zaman damgası.
- `source`: Verinin etki alanı kaynağı (`"forkos"` veya `"f0rknbrain"`).
- `data`: Araca özgü tip güvenli veri yükü.
- `truncated`: Bütçe veya kota sınırı sebebiyle sonucun/içeriğin kesilip kesilmediği (`bool`).

Hata durumlarında araç doğrudan MCP standardına uygun `ToolError` yükseltir; istemciye `isError: true` ve açıklayıcı hata kodu döner (iç yığın izi verilmez):
- `QUERY_TOO_SHORT` / `QUERY_TOO_LONG`
- `INVALID_UUID`
- `INVALID_SINCE`
- `INVALID_SCOPE`
- `INVALID_DATE`
- `INVALID_LOCATOR`
- `ACCESS_DENIED` / `VAULT_PATH_ESCAPES`

---

## 2. Araç Detayları

### 1. `forkos_briefing`
Kullanıcının güncel durumunu özetleyen olgusal, hafif ve sınırlı günlük brifing paketini döndürür.

- **Açıklama:** `"Factual, bounded operational day briefing (agenda, open todos, deadlines, active projects, learning due, notifications, vault status). Read-only. Does not modify forkOS or the Vault."`
- **Parametreler:**
  - `day` (*string, opsiyonel*): Hedef tarih (`YYYY-MM-DD`). Geçersiz biçimde `INVALID_DATE` fırlatır.
- **Veri Alanları (`data`):**
  - `day`: Günün tarihi (`YYYY-MM-DD`).
  - `agenda`: Bugünkü zaman blokları / plan slotları listesi (max 30).
  - `open_todos`: Açık görevler (başlık, öncelik, son tarih vb. max 20).
  - `deadlines`: Yaklaşan son tarihler listesi (`collect_deadlines` sözleşmesiyle max 15).
  - `active_projects`: Aktif projeler (id, başlık, durum, next_action, github_repo max 10).
  - `learning_due`: Vadesi gelmiş SRS bilgi kartları (max 10).
  - `opportunity_attention`: Aktif takip edilen iş başvuruları ve duyurular (max 10).
  - `notifications`: Okunmamış bildirimler (max 10).
  - `recent_activity_summary`: Son olaylar özeti (max 10).
  - `vault_status`: Kasa bağlantı ve indeks durumu özeti.
- **Kesilme (`truncated`):** Alt listelerden herhangi biri üst sınırına ulaştığında `true`.

---

### 2. `forkos_search`
forkOS'taki aktif operasyonel modüller (todo, project, opportunity, bookmark vb.) üzerinde yapısal arama yapar. Dondurulmuş legacy notları aramaz.

- **Açıklama:** `"Search active operational entities across forkOS (excluding legacy note entities). Read-only. Does not modify forkOS or the Vault."`
- **Parametreler:**
  - `query` (*string, zorunlu*): Arama terimi (2 ile 200 karakter arasında olmalıdır; aksi halde `QUERY_TOO_SHORT` veya `QUERY_TOO_LONG` yükseltilir).
  - `entity_types` (*list[str], opsiyonel*): Tip filtreleri listesi (örn: `["todo", "project"]`).
  - `limit` (*integer, opsiyonel, varsayılan: 10, max: 30*): Maksimum sonuç sayısı.
- **Yanıt:** `list[EntitySearchResult]` (`id`, `type`, `title`, `route`, `summary`).
- **Kesilme (`truncated`):** `len(results) >= limit` ise `true`.

---

### 3. `forkos_entity_context`
Belirli bir operasyonel varlığın kimliğini, derin linklerini, bağlı operasyonel nesnelerini ve son aktivite geçmişini getirir. Dondurulmuş legacy notlar ilişkilerden filtrelenir.

- **Açıklama:** `"Inspect identity, deep links, related entities, and recent activity for an operational entity UUID. Read-only. Does not modify forkOS or the Vault."`
- **Parametreler:**
  - `entity_id` (*string, zorunlu*): Varlığın UUID değeri. Geçersiz UUID biçiminde `INVALID_UUID` fırlatır.
- **Yanıt:** `EntityContextData` (`id`, `type`, `title`, `route`, `details`, `related_entities`, `recent_events`, `knowledge_ref`).
- **Kesilme (`truncated`):** `false`.

---

### 4. `forkos_project_context`
Bir projenin durumunu, kilometre taşlarını, kanonik `belongs_to` ve kilometre taşı ilişkili açık görevlerini, kapsamlı proje zaman tüneli olaylarını (`project_svc.timeline`) ve Obsidian bilgi notu bağlantısını içeren kompakt operasyonel paketi döndürür.

- **Açıklama:** `"Inspect compact project operational packet (status, milestones, open todos, recent activity, Vault note pointer). Read-only. Does not modify forkOS or the Vault."`
- **Parametreler:**
  - `project_id` (*string, zorunlu*): Projenin UUID değeri. Geçersiz UUID biçiminde `INVALID_UUID` fırlatır.
- **Yanıt:** `ProjectContextData` (`project`, `milestones`, `todos`, `recent_activity`, `deadlines`, `knowledge`).
- **Kesilme (`truncated`):** `false`.

---

### 5. `forkos_recent_activity`
forkOS'un append-only olay günlüğündeki son aktiviteleri getirir. Hassas bilgiler (`token`, `secret`, `password` vb.) maskelenir ve olay yükleri derinlik/anahtar/karakter/bayt sınırlarına tabi tutulur.

- **Açıklama:** `"Inspect sanitized append-only operational events. Read-only. Does not modify forkOS or the Vault."`
- **Parametreler:**
  - `since` (*string, opsiyonel*): Zaman filtresi. Ön tanımlı değerler (`"today"`, `"yesterday"`, `"7d"`, `"30d"`) veya ISO 8601 tarih formatı olmalıdır. Geçersiz biçimde `INVALID_SINCE` fırlatır.
  - `entity_type` (*string, opsiyonel*): Filtrelenecek varlık tipi.
  - `verb` (*string, opsiyonel*): Filtrelenecek olay fiili.
  - `limit` (*integer, opsiyonel, varsayılan: 30, max: 100*): Döndürülecek maksimum olay sayısı.
- **Yanıt:** `list[ActivityEventData]` (`id`, `timestamp`, `verb`, `entity_id`, `entity_type`, `title`, `payload`).
- **Kesilme (`truncated`):** `len(data) >= limit` ise `true`.

---

### 6. `brain_status`
f0rknbrain Obsidian Vault'unun yapılandırma, bağlantı ve dosya istatistiklerini raporlar.

- **Açıklama:** `"Health, connectivity, and statistics of f0rknbrain Vault knowledge interface. Read-only. Does not modify forkOS or the Vault."`
- **Parametreler:** Yok (`{}`)
- **Yanıt:** `BrainStatusData`:
  - `brain_interface_version`: `1`.
  - `configured`: Vault yolunun tanımlı olup olmadığı (`bool`).
  - `available`: Vault dizininin diskte mevcut ve okunabilir olup olmadığı (`bool`).
  - `readable`: Okuma izni durumu (`bool`).
  - `writable`: Yazma izni durumu (`bool` - H0 kapsamında mutasyon yapılmaz).
  - `vault_name`: Kasa adı.
  - `total_markdown_files`: Güvenli Markdown dosya sayısı.
  - `managed_files_count`: `forkos_id` içeren dosya sayısı.
  - `conflicts_count`: Çakışan mükerrer `forkos_id` sayısı.
  - `invalid_metadata_count`: Geçersiz frontmatter içeren dosya sayısı.
- **Kesilme (`truncated`):** `false`.

---

### 7. `brain_search`
f0rknbrain Vault'undaki tüm güvenli Markdown notlarında (yönetilen + serbest) deterministik leksikal (metin tabanlı) arama yapar.

- **Açıklama:** `"Deterministic lexical search across all safe Markdown knowledge in the Vault (managed + unmanaged). Read-only. Does not modify forkOS or the Vault."`
- **Parametreler:**
  - `query` (*string, zorunlu*): Arama terimi (2 ile 200 karakter arasında).
  - `scope` (*BrainScope Literal, opsiyonel, varsayılan: "all"*): `'all' | 'inbox' | 'daily' | 'projects' | 'knowledge' | 'learning' | 'career' | 'sources' | 'agent'`. Geçersiz kapsamda `INVALID_SCOPE` fırlatır.
  - `limit` (*integer, opsiyonel, varsayılan: 8, max: 20*): Maksimum sonuç sayısı.
- **Yanıt:** `list[BrainSearchResult]` (`locator`, `title`, `relative_path`, `forkos_id`, `forkos_type`, `matched_heading`, `snippet`, `score`).
- **Kesilme (`truncated`):** `len(data) >= limit` ise `true`.

---

### 8. `brain_read`
Vault içindeki belirli bir Markdown notunun içeriğini güvenli, dizin atlama korumalı ve bütçeli bir biçimde okur.

- **Açıklama:** `"Safe, bounded Markdown reader for a specific knowledge file by forkos_id or relative_path. Read-only. Does not modify forkOS or the Vault."`
- **Parametreler:**
  - `forkos_id` (*string, opsiyonel*): Notun frontmatter'ındaki `forkos_id` UUID'si (biçim doğrulanır, `INVALID_UUID`).
  - `relative_path` (*string, opsiyonel*): Notun kasa içi göreli dosya yolu (örn: `"20 Projects/X.md"`). Kanonik güvenli yol politikasınca `.git`, `.obsidian`, `.forkos-migration`, `.trash`, `attachments`, `95-ekler`, `90-şablonlar` ve gizli dosyalar `ACCESS_DENIED` ile reddedilir.
  - `heading` (*string, opsiyonel*): Yalnızca belirli bir başlık altındaki bölümü okumak için başlık metni.
  *(Not: `forkos_id` veya `relative_path` parametrelerinden tam olarak biri sağlanmalıdır; aksi halde `INVALID_LOCATOR` fırlatılır).*
- **Yanıt:** `BrainReadData` (`title`, `relative_path`, `forkos_id`, `forkos_type`, `frontmatter`, `headings`, `content`, `truncated`).
- **Kesilme (`truncated`):** İçerik karakter bütçesini aştığında `true` (zarfın `truncated` alanına aynen aktarılır).

---

## 3. Örnek JSON Çağrı ve Yanıtı

### İstek: `brain_read`
```json
{
  "name": "brain_read",
  "arguments": {
    "relative_path": "20 Projects/forkOS.md",
    "heading": "Kararlar"
  }
}
```

### Yanıt:
```json
{
  "as_of": "2026-09-20T10:14:00.123456Z",
  "source": "f0rknbrain",
  "data": {
    "title": "forkOS Projesi",
    "relative_path": "20 Projects/forkOS.md",
    "forkos_id": "3f6f99e0-1234-5678-9abc-def012345678",
    "forkos_type": "project",
    "frontmatter": {
      "forkos_id": "3f6f99e0-1234-5678-9abc-def012345678",
      "forkos_type": "project",
      "title": "forkOS Projesi"
    },
    "headings": ["Mimari", "Kararlar", "Yol Haritası"],
    "content": "### Kararlar\nStreamable HTTP MCP seçildi.",
    "truncated": false
  },
  "truncated": false
}
```
