# forkOS — A1.1 Hardening + A2 Bootstrap & Continuity Design

**Tarih:** 2026-09-22  
**Durum:** Taslak (İncelemeye Hazır)  
**Branch:** `main`  
**Hedef:** A1.1 Lifecycle Bridge Mini-Hardening ve A2 Bounded Bootstrap & Continuity Alt Sistemi

---

## 1. Mimari Bağlam ve Sorumluluk Sınırları

Canonical ownership ve bellek sınırları korunur:

- **Hermes:** Akıl yürütme, orkestrasyon, model kararları.
- **forkOS (PostgreSQL 16):** Canlı operasyonel kanonik durum (todo, project, deadline, career, planning, approvals, receipts).
- **f0rknbrain (Obsidian Vault):** Kalıcı insan bilgisi (tercihler, kararlar, araştırmalar, notlar).
- **H2 Hot Memory (`90 Agent/Memory`):** Geçici ancak şu anda önemli, küratörlü bağlam.
- **A-Serisi (A1/A1.1/A2):** Yaşam döngüsü gözlemi, bounded başlangıç bağlamı ve oturum içi kaynak devamlılığı. **Yeni kanonik durum sahibi DEĞİLDİR.**

Bellek ayrımı:
- `WORKING`: Mevcut Hermes / oturum çalışma durumu
- `EPISODIC`: A3 (bu fazda YOK)
- `OPERATIONAL`: forkOS PostgreSQL
- `HOT MEMORY`: H2
- `SEMANTIC`: f0rknbrain
- `PROCEDURAL`: Hermes Skills + Agent Operating Contract

---

## 2. A1.1 Mini-Hardening

### 2.1 A1.1.1 — No-source-mutation Invariant
- **Amaç:** Yaşam döngüsü gözleminin (`observe`) yalnızca kendi destek tablolarını (`agent_session`, `agent_session_turn`) değiştirebildiğini; hiçbir operasyonel veya bilgi kaynağını mutate edemeyeceğini garanti etmek.
- **Davranış:**
  - `Entity`, `Event` (`log_event`), `Link`, `Todo`, `Project`, `Opportunity`, `Notification`, `ProactivityRule`, `ProactivityRun`, `ExecutionPlan` tabloları değişmez.
  - H2 Hot Memory dosyaları değişmez.
  - Vault dosyaları değişmez.
- **Test:** `backend/tests/test_agent_lifecycle_invariants.py` tüm tablo satır sayıları ve dosya hash'lerini yaşam döngüsü çağrıları öncesi/sonrası denetler. İleride yanlışlıkla `log_event()` veya domain mutasyonu bağlanırsa test kırılır.

### 2.2 A1.1.2 — HTTP Success Semantics
- **Sıkılaştırma:** Hermes eklentisi (`tools/hermes/forkos-lifecycle/__init__.py`) teslim başarısını yalnızca `200 <= status < 300` olarak kabul eder.
- **Fail-open:** `3xx`, `4xx`, `5xx` durumları hata kabul edilir ancak exception yakalanarak loglanır; Hermes konuşması hiçbir durumda çökmez (`fail-open`).
- **Ağ sınırları:** Yönlendirme (redirect) takip edilmez. Yalnızca loopback (`127.0.0.1`, `localhost`, `::1`) kabul edilir. Hot path üzerinde retry yapılmaz.
- **Testler:** 2xx success, 3xx fail-open, 4xx fail-open, 5xx fail-open doğrulanır.

---

## 3. A2 — Yaşam Döngüsü ve Orkestrasyon Mimarisi

### 3.1 Uç Nokta Ayrımı ve Tek Round-Trip Sözleşmesi

- **`pre_llm_call`** için: Yeni orchestration endpoint:  
  `POST /api/agent/lifecycle/turn`
- **`on_session_finalize`** için: Mevcut A1 endpoint:  
  `POST /api/agent/lifecycle/event`

```text
Hermes pre_llm_call
       │
       ▼ (tek HTTP POST)
POST /api/agent/lifecycle/turn
       │
       ├─► 1. A1 observe(session_start | turn_seen) ──► DB COMMIT (Bağımsız Transaction)
       │
       └─► 2. A2 Context Composition ────────────────► Read-Only Bounded Context
                 ├─► f0rknbrain / H2 / H5 / forkOS DB
                 ├─► Ephemeral session source tracking
                 └─► Format rendered context
       │
       ▼
TurnContextOut (HTTP 200)
{
  "lifecycle": { "accepted": true, "event": "...", "duplicate": false },
  "packet": BootstrapPacketV1 | null,
  "rendered_context": string | null,
  "degraded_reasons": []
}
```

### 3.2 Bağımsız Transaction ve Hata İzolasyonu
1. **A1 İzolasyonu:** `AgentLifecycleService.observe()` önce çalışır ve transaction commit edilir. A2 bağlam üretimindeki herhangi bir arıza (Vault erişilemezliği, H2 çatışması, DB gecikmesi) A1 oturum gözlemini ASLA geri almaz (`rollback` etmez).
2. **Hermes Güvenliği (Fail-Open):** A2 bağlamı oluşturulamazsa `rendered_context=None`, `degraded_reasons=["..."]` ile HTTP 200 döner. Hermes tura normal şekilde devam eder.

---

## 4. Veri Modelleri ve Ephemeral Destek Depolama

A2 kalıcı kanonik bilgi tutmaz; yalnızca oturum devamlılığı metadata'sını tutar.

### 4.1 Veritabanı Şeması (`0064_agent_continuity.py`)

#### `agent_session_context` Tablosu
Enjekte edilen bağlamların özet metrikleri ve tanılamaları:
- `id`: BigInteger PK
- `session_id`: BigInteger FK → `agent_session.id` (ON DELETE CASCADE)
- `turn_id`: BigInteger FK → `agent_session_turn.id` (ON DELETE CASCADE, nullable)
- `schema_version`: Integer NOT NULL (1)
- `is_first_turn`: Boolean NOT NULL
- `item_count`: Integer NOT NULL
- `char_count`: Integer NOT NULL
- `truncated`: Boolean NOT NULL DEFAULT False
- `omitted_count`: Integer NOT NULL DEFAULT 0
- `degraded_reasons`: JSONB NOT NULL (örn. `[]` veya `["VAULT_UNAVAILABLE"]`)
- `created_at`: DateTime(timezone=True) NOT NULL

#### `agent_session_source` Tablosu
Oturum içinde modele teslim edilen bounded kaynak referansları:
- `id`: BigInteger PK
- `session_id`: BigInteger FK → `agent_session.id` (ON DELETE CASCADE)
- `turn_id`: BigInteger FK → `agent_session_turn.id` (ON DELETE CASCADE, nullable)
- `source_id`: String(128) NOT NULL (örn. `entity:<uuid>`, `vault:<path>`, `hot_memory:<id>`, `deadline:<id>`)
- `source_type`: String(32) NOT NULL (`entity`, `vault_note`, `hot_memory`, `deadline`, `review`, `project`)
- `source_version`: String(64) NULLABLE (hash veya revizyon damgası)
- `scope_project`: String(64) NULLABLE (proje UUID)
- `topic_signature`: String(64) NULLABLE
- `delivered_at`: DateTime(timezone=True) NOT NULL
- `expires_at`: DateTime(timezone=True) NOT NULL
- **Kısıt:** Oturum başına en fazla 5 aktif kaynak grubu saklanır.
- **İndeks:** `(session_id, expires_at desc)`

---

## 5. BootstrapPacketV1 Şeması ve Katı Bütçe

### 5.1 Şema Tanımı
```python
class BootstrapSourceRef(BaseModel):
    source_id: str
    source_type: str
    source_version: str | None = None
    scope_project: str | None = None
    title: str | None = None

class BootstrapIdentity(BaseModel):
    interaction_conventions: list[str]  # max 3
    durable_preferences: list[str]      # max 4
    explicit_corrections: list[str]     # max 3
    long_running_goals: list[str]       # max 3

class OperationalDeadline(BaseModel):
    id: str
    title: str
    due_at: str | None
    remaining_days: int | None
    entity_type: str

class OperationalProject(BaseModel):
    id: str
    title: str
    status: str
    next_action: str | None = None

class OperationalState(BaseModel):
    active_projects: list[OperationalProject]    # max 5
    upcoming_deadlines: list[OperationalDeadline] # max 5
    open_todos_count: int
    pending_decisions_count: int
    pending_decisions_summary: list[str]        # max 3

class BootstrapContinuity(BaseModel):
    anchor_timestamp: str | None
    anchor_kind: str | None
    activity_gap_hours: float | None
    last_meaningful_activity: str | None
    recent_completed: list[str]                 # max 3
    active_threads: list[str]                   # max 3
    stalled_projects: list[str]                 # max 2

class BootstrapHotMemory(BaseModel):
    items: list[dict[str, Any]]                 # max 6

class BootstrapDiagnostics(BaseModel):
    available: bool
    truncated: bool
    omitted_count: int
    degraded_reasons: list[str]
    generation_ms: float

class BootstrapPacketV1(BaseModel):
    schema_version: Literal[1] = 1
    session_key: str
    generated_at: str
    is_first_turn: bool
    identity: BootstrapIdentity
    operational_state: OperationalState
    continuity: BootstrapContinuity
    hot_memory: BootstrapHotMemory
    sources: list[BootstrapSourceRef]
    diagnostics: BootstrapDiagnostics
```

### 5.2 Katı Bütçe (Hard Limits)
- Toplam render metin bütçesi: **4,000 karakter**.
- Kırpma (truncation) öncelik sırası:
  1. Kimlik ve açık düzeltmeler (korunur)
  2. Kritik operasyonel durum (yaklaşan son tarihler, bekleyen kararlar)
  3. Yakın süreklilik (çapa, son anlamlı hareket)
  4. Sıcak hafıza (H2 kısıt/profil)
  5. Aktif projeler
  6. Diğer detaylar (önce bunlar kırpılır)
- Bütçe aşıldığında `truncated=True`, `omitted_count=N` açıkça belirtilir.

---

## 6. First Turn vs. Later Turns & Kaynak Devamlılığı

### 6.1 First Turn (İlk Tur)
- `session_start` ile tam bounded `BootstrapPacketV1` üretilir.
- Render edilen format:
  ```markdown
  <forkos-context version="1">
  ### Kimlik & Tercihler
  ...
  ### Güncel Operasyonel Durum
  ...
  ### Yakın Süreklilik
  ...
  ### Sıcak Hafıza
  ...
  ### Kaynaklar
  ...
  </forkos-context>
  ```
- Teslim edilen kaynaklar (en fazla 5) `agent_session_source` içine yazılır.

### 6.2 Later Turns (Sonraki Turlar)
- Tam bootstrap **kesinlikle tekrarlanmaz**.
- İstekle gelen transient prompt incelenir:
  - Eğer soru belirsiz bir devam sorusu ise (*"bunu biraz aç"*, *"onu da karşılaştır"*, *"peki bunun diğerinden farkı?"*, *"önceki kaynağa göre?"*, vb.):
    - Oturum aynıysa, TTL dolmamışsa (60 dk) ve kaynak revizyonu güncelse:
      Önceki kaynak kümesini özetleyen kısa devam bağlamı üretilir:
      ```markdown
      <forkos-continuity version="1">
      Önceki aktif kaynaklar: [kaynak listesi]
      </forkos-continuity>
      ```
  - Eğer açıkça yeni bir konuya/projeye geçildiyse veya devamlılık kriteri sağlanmıyorsa:
    - Önceki kaynak devamlılığı sıfırlanır (`reset/invalidate`).
    - `rendered_context=None` döner (model MCP araçlarıyla çalışır).

### 6.3 Geçersiz Kılma (Invalidation) Kuralları
- **Oturum değişti:** Yeni oturumda eski kaynaklar kullanılmaz.
- **Proje/kapsam değişti:** Kaynak referansları temizlenir.
- **Kaynak revizyonu değişti:** Bayat kaynak yeniden kullanılmaz.
- **TTL (60 dk) aşıldı:** Sıfırlanır.
- **Açık konu değişimi:** Sıfırlanır.

---

## 7. Gizlilik ve Güvenlik Güvenceleri

1. **Transient Prompt:** Gelen kullanıcı mesajı (`user_message`) yalnızca bellek içinde devamlılık/konu analizi için kullanılır; PostgreSQL'e, loglara, tanılamalara veya Vault'a **asla yazılmaz**.
2. **Local-Only:** Tüm işlemler `127.0.0.1` üzerinde kalır, hiçbir harici API/telemetri çağrısı yapılmaz.
3. **Yol Gizleme:** Dosya yolları `redact_absolute_paths` ile temizlenir; mutlak sistem yolları arayüze veya modele sızmaz.
4. **Prompt Injection İzolasyonu:** Context blokları açık XML/Markdown sınırlarıyla (`<forkos-context>`) veri olarak işaretlenir; sistem talimatı gibi yorumlanamaz.

---

## 8. Arayüz ve Tanılamalar (Ayarlar → Agent & Bilgi)

- Sayfa yapısı korunur (`BrainAgentSection.tsx`).
- İç faz kodları (`A1`, `A2`, `H2`, `H5`) kullanıcı etiketlerinde kullanılmaz.
- Eklenen/genişletilen durum satırları:
  - **Oturum devamlılığı:** Hazır / Kısmi / Kullanılamıyor
  - **Başlangıç bağlamı:** Hazır (4.0 KB) / Kısmi / Kullanılamıyor
  - **Son bağlam oluşturma:** 2 dk önce / Henüz oluşturulmadı
  - **Kaynak devamlılığı:** 3 kaynak etkin / Etkin kaynak yok
- "Hermes bağlı" gibi sahte iddialarda bulunulmaz; epistemik dürüstlük korunur.

---

## 9. Doğrulama ve Test Planı

1. **A1.1 Hardening Testleri:**
   - Invariant testi: Lifecycle gözlemlerinin `Entity`, `Event`, `Todo`, `Vault` vb. tabloları/dosyaları değiştirmediğini kanıtlayan test.
   - HTTP semantikleri: 2xx success, 3xx/4xx/5xx fail-open testleri.
2. **A2 Bootstrap & Context Testleri:**
   - İlk turda bounded bootstrap üretimi, bütçe aşımında kırpma.
   - Vault/H2/H5 arızalarında degrade olma ve fail-open davranışı.
   - Idempotans: Çift çağrıda duplicate context enjekte edilmemesi.
3. **Kaynak Devamlılığı Testleri:**
   - Aynı oturumda "bunu biraz aç" isteminde kaynak devamlılığı reuse.
   - Oturum/konu/TTL değişiminde invalidation / reset.
   - Raw prompt'un veritabanına kaydedilmediğinin kanıtı.
4. **Canlı Hermes Yürüyüşü (Walkthrough):**
   - Yerel Hermes CLI ile oturum açma, ilk tur bootstrap doğrulaması, devam sorusu testi, finalize ve latency ölçümü.
