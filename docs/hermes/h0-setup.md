# forkOS × Hermes — H0 Kurulum & Entegrasyon Rehberi

Bu belge, Hermes (veya standart Model Context Protocol destekleyen herhangi bir ajan istemcisi) ile forkOS Brain Interface arasındaki yerel bağlantının nasıl kurulacağını ve test edileceğini açıklar.

> [!IMPORTANT]
> forkOS gizlilik ve local-only sözleşmesi gereği, kullanıcının ev dizinindeki kişisel konfigürasyon dosyalarına (örn: `~/.hermes/config.yaml` veya `~/.config/hermes/`) **asla otomatik olarak dokunmaz veya değiştirmez**. Aşağıdaki ayarlar kullanıcı tarafından kendi ortamına eklenmelidir.

---

## 1. Ön Koşullar

1. **forkOS Çalışıyor Olmalıdır:**
   ```bash
   # Stable container runtime ile:
   make up CO="docker compose"
   # veya geliştirme ortamında:
   uvicorn app.main:app --port 8787
   ```
2. **Obsidian Vault Bağlantısı:**
   `.env` dosyanızda kasanızın tanımlı olduğundan emin olun:
   ```env
   OBSIDIAN_VAULT_HOST_PATH=/Users/kullanici/Documents/f0rknbrain
   OBSIDIAN_VAULT_NAME=f0rknbrain
   ```

---

## 2. Hermes Konfigürasyonu

Hermes'in araç tanımları bölümüne `forkos-brain` MCP sunucusunu ekleyin:

### Örnek Hermes MCP Ayarı:
```yaml
mcp_servers:
  forkos-brain:
    url: "http://127.0.0.1:8787/mcp"
    enabled: true
    trust: untrusted
    timeout: 120
    connect_timeout: 30
    supports_parallel_tool_calls: false
    sampling:
      enabled: false
```

*Not: Gerçek bağlanma adresi her zaman `http://127.0.0.1:8787/mcp` yoludur
(resmi Streamable HTTP endpoint'i); aynı tarif Ayarlar → **Agent & Bilgi**
sekmesinde kopyalanabilir olarak da durur. `trust: untrusted` istemci tarafında
yazma onayı ister ve forkOS bu ayarı doğrulayamaz.*

---

## 3. Bağlantıyı Doğrulama (Adım Adım)

### Adım 1: HTTP Uç Noktasını Kontrol Etme
Sunucunun ayakta olduğunu ve `/mcp` yolunun dinlendiğini curl ile test edin:

```bash
curl -i http://127.0.0.1:8787/mcp
```
*(MCP protokolü POST veya SSE/Streamable bağlantısı beklediği için HTTP 200, 400 veya 405 yanıtı dönebilir; ancak 404 dönmemelidir).*

### Adım 2: Python MCP İstemcisi ile Smoke Test
Terminalinizde hızlı bir test çalıştırmak için:

```bash
python3 -c "
import asyncio
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession

async def main():
    async with streamable_http_client('http://127.0.0.1:8787/mcp') as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            init_res = await session.initialize()
            print('Connected to server:', init_res.server_info.name, init_res.server_info.version)
            tools = await session.list_tools()
            print('Available tools:', [t.name for t in tools.tools])
            status = await session.call_tool('brain_status', {})
            print('Brain Status:', status.content[0].text)

asyncio.run(main())
"
```

**Beklenen Çıktı:**
```text
Connected to server: forkos-brain 1.0.0
Available tools: ['forkos_briefing', 'forkos_search', 'forkos_entity_context', 'forkos_project_context', 'forkos_recent_activity', 'brain_status', 'brain_search', 'brain_read']
Brain Status: {"as_of": "2026-09-20T10:00:00Z", "source": "f0rknbrain", "data": {...}, "truncated": false}
```

---

## 4. Sık Karşılaşılan Sorunlar ve Çözümleri

### 1. `VAULT_UNAVAILABLE` Hatası
- **Neden:** `OBSIDIAN_VAULT_PATH` ortam değişkeni tanımlanmamış veya dizin diskte mevcut değil.
- **Çözüm:** `.env` dosyanızda geçerli bir host yolu belirtin ve Docker kullanıyorsanız `make up-obsidian CO="docker compose"` ile kasayı mount edin.

### 2. Araç Yanıtında `is_error=True` Görünmesi
- H0 arayüzü tüm parametreleri Pydantic modelleriyle sıkı denetler. Örneğin `brain_read` için hem `forkos_id` hem `relative_path` boş gönderilirse veya geçersiz bir UUID girilirse `ToolError` yükseltilir. Parametreleri [Araç Sözleşmeleri](h0-tool-contract.md) dokümanına göre kontrol edin.

### 3. Hermes Veritabanına Yazmaya Çalışırsa
- H0 okuma yüzeyinde hiçbir mutasyon aracı tanımlı değildir (H1 ile 11 yazma aracı eklendi; bkz. [H1 Kurulum](h1-setup.md)). Hermes'e verilen sistem prompt'unda:
  *"forkOS arayüzü salt-okunurdur. Görev ekleme veya not düzenleme araçları bulunmaz; yalnızca durum incelemesi yapılabilir."*
  bilgisinin bulunması önerilir.
