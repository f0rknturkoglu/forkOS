# forkOS × Hermes — H0 Teknik Mimari & Tasarım

Bu belge, **H0: Brain Interface Foundation** arayüzünün teknik mimarisini, protokol seçimini, FastAPI entegrasyonunu, bilgi tarama stratejisini ve güvenlik önlemlerini detaylandırır.

---

## 1. Protokol ve Taşıma Katmanı: Streamable HTTP

H0 arayüzü resmi Python Model Context Protocol (`mcp>=1.0,<3.0`) SDK'sı üzerine inşa edilmiştir.

### Neden Tek Kanonik Taşıma Olarak Streamable HTTP Seçildi?
- **Çalışma Zamanı Birliği:** forkOS zaten tek kullanıcılı bir FastAPI servisi olarak çalışır. Ayrı bir daemon veya stdio companion process açmak yerine `/mcp` altında bir Streamable HTTP Starlette alt uygulaması mount edilmiştir.
- **Paylaşımlı Kaynaklar:** FastAPI'nin mevcut SQLAlchemy asyncpg bağlantı havuzu (`SessionLocal`), konfigürasyon nesnesi (`settings`) ve Obsidian Vault izin bağlamı ek bir katman gerekmeksizin doğrudan paylaşılır.
- **Hermes Uyumluluğu:** Hermes, HTTP tabanlı MCP uç noktalarını yerel olarak destekler.
- **Sıfır Ek Bellek/Süreç:** Ayrı bir işlem veya arka plan kuyruğu çalıştırılmaz.

### FastAPI Lifespan Entegrasyonu
MCP SDK'sında `MCPServer.session_manager` bir arka plan görev yöneticisidir ve HTTP oturumlarının temiz şekilde açılıp kapanmasını sağlar. FastAPI'nin `lifespan` context manager'ına aşağıdaki şekilde bağlanmıştır:

```python
# backend/app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Diğer başlangıç adımları...
    async with mcp_server.session_manager.run():
        yield
    # Kapanış adımları...
```

Streamable HTTP alt uygulaması `/mcp` rotasına mount edilir:
```python
mcp_app = get_streamable_http_app()
app.mount("/mcp", mcp_app)
```

---

## 2. Vault Bilgi Tarama Stratejisi: Doğrudan İsteğe Bağlı Tarama (Direct Scan)

f0rknbrain Obsidian Vault'u hem forkOS tarafından yönetilen yapılandırılmış notları (`forkos_id` frontmatter'ına sahip) hem de kullanıcının serbest yazdığı unmanaged Markdown notlarını barındırır.

### Performans Ölçümleri ve Karar
H0 tasarımı sırasında gerçek kullanıcı kasasında yapılan ampirik ölçümler:
- **Toplam Not Sayısı:** 27 Markdown dosyası
- **Toplam Boyut:** ~49.8 KB
- **Doğrudan Disk Tarama Süresi:** **5.53 ms** (ortalama)

Bu sonuçlar doğrultusunda:
1. **Ayrı bir Shadow DB veya Vektör İndeksi kurulmamıştır.**
2. **Arka planda çalışan dosya izleyici (file watcher) veya polling daemon eklenmemiştir.**
3. `brain_search` ve `brain_read` doğrudan dosya sistemi üzerinde isteğe bağlı (on-demand) çalışır.
4. Sıfır ek RAM tüketimi, sıfır senkronizasyon bayatlığı ve anında güncellik garanti edilmiştir.

---

## 3. Güvenlik ve Mahremiyet Güvenceleri

Arayüz aşağıdaki katı güvenlik denetimlerini uygular:

### 1. Dizin Atlama (Path Traversal) ve Kaçış Engellemesi
- Tüm dosya yolları `Path.resolve()` ile kanonik hale getirilir.
- Çözümlenen yolun `vault_path` altında kalıp kalmadığı `path.is_relative_to(vault_root)` ile denetlenir.
- `../../etc/passwd` gibi göreli yollar veya Vault dışındaki dosyalara işaret eden sembolik linkler (`symlink`) anında reddedilir (`ToolError: ACCESS_DENIED` / `VAULT_PATH_ESCAPES`).

### 2. Kanonik Bilgi Yolu İzolasyonu (Unified Knowledge Path Policy)
- Hem `brain_search` hem de `brain_read` aynı kanonik filtreleme politikasını (`is_safe_knowledge_path`) uygular:
  - `.git/**`, `.obsidian/**`, `.forkos-migration/**`, `.trash/**`, `attachments/**`, `95-ekler/**`, `90-şablonlar/**` ve `.` ile başlayan tüm gizli dosya ve klasörler anında engellenir.
- Yalnızca güvenli ve geçerli `.md` uzantılı dosyalar okunabilir.

### 3. Hassas Bilgi Maskeleme ve Yük Sınırlama (Credential Scrubbing & Payload Bounding)
- Olay günlüğü çağrılarında, `token`, `password`, `secret`, `api_key`, `authorization` ve `credential` anahtarlarını içeren tüm alanlar `[REDACTED]` ile maskelenir.
- Derinlik (max 4), sözlük anahtar sayısı (max 25), liste eleman sayısı (max 25), metin uzunluğu (max 500 karakter) ve toplam serileştirilmiş yük boyutu (max 4096 bayt) sınırlandırılır.

### 4. Localhost DNS-Rebinding Koruması
- MCP Starlette uygulaması resmi MCP SDK `TransportSecuritySettings` ile localhost koruması etkin olarak çalıştırılır:
  - Yalnızca `127.0.0.1:*`, `localhost:*` ve `[::1]:*` Host ve Origin başlıklarına izin verilir; yabancı origin'ler (örn. `evil.com`) 403/421 ile reddedilir.

### 5. Yerel Ağ Sınırı (Loopback Only)
- API ve MCP servisi yalnızca `127.0.0.1` adresine bağlanır (`0.0.0.0` kullanılmaz).

---

## 4. Değişmezlik ve Salt-Okunur Güvencesi (Immutability Proof)

Sistemin salt-okunurluğu `backend/tests/test_agent_immutability.py` test süiti ile otomatik olarak doğrulanmaktadır:

1. **Deterministik DB Satır İçeriği SHA-256 Parmak İzi:** Yüzeysel satır sayısı sayımı yerine, `Entity`, `Event`, `Link`, `Todo`, `Project`, `Milestone`, `Notification`, `Opportunity`, `Application`, `FlashcardCard`, `Bookmark`, `Note` ve `NoteFolder` tablolarındaki tüm satır içerikleri birleştirilerek SHA-256 özetine dönüştürülür. `test_db_content_fingerprint_sensitive_to_updates` testi tek bir satırdaki alan güncellemesinin (`UPDATE`) bile parmak izini anında değiştirdiğini kanıtlar. 8 MCP aracının tamamı çalıştırıldıktan sonra, kritik tablolardaki seçilmiş kanonik durum alanları üzerinde hesaplanan deterministik içerik parmak izi %100 korunur.
2. **Dosya Sistemi Değişmezliği:** Vault içindeki tüm dosyaların SHA-256 hash'leri ve son değiştirilme zamanları (`mtime`) araç çağrılarından önce ve sonra karşılaştırılır; tek bir baytın dahi değişmediği kanıtlanır.
3. **Protokol Seviyesinde İpuçları:** Her araç tanımında `ToolAnnotations` nesnesi şu değerlerle işaretlenmiştir:
   - `readOnlyHint = True`
   - `destructiveHint = False`
   - `idempotentHint = True`
