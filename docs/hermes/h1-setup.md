# forkOS × Hermes — H1 Kurulum & Onay Rehberi

Bu belge, H1'in **yazma yetenekli** Brain Interface'ini Hermes'e nasıl
bağlayacağınızı ve onay davranışını nasıl doğru kuracağınızı anlatır.

> [!IMPORTANT]
> forkOS, gizlilik ve local-only sözleşmesi gereği kullanıcının ev dizinindeki
> kişisel yapılandırmasına (`~/.hermes/config.yaml` vb.) **ASLA otomatik olarak
> dokunmaz**. Aşağıdaki ayarları kendiniz eklemelisiniz. H1 hiçbir zaman
> `approvals.mode: off`, `--yolo` veya `trust: full` önermez.

---

## 1. Ön koşullar

1. **forkOS çalışıyor olmalı** (`/mcp` ucu dinliyor olmalı):
   ```bash
   make up-obsidian CO="docker compose"   # Vault bağlı hibrit runtime
   ```
2. **Vault bağlı olmalı** (bilgi yazmaları için):
   ```env
   OBSIDIAN_VAULT_HOST_PATH=/Users/kullanici/Documents/f0rknbrain
   OBSIDIAN_VAULT_NAME=f0rknbrain
   ```

---

## 2. Hermes yapılandırması (önerilen)

```yaml
mcp_servers:
  forkos-brain:
    type: http
    url: "http://127.0.0.1:8787/mcp"
    trust: untrusted          # ← H1'in onay kapısı BURADAN gelir
    headers: {}
    timeout: 30
```

**Neden `trust: untrusted`?**

H1'in tüm yazma araçları `readOnlyHint = false` taşır. `untrusted` modda
Hermes, bu bayrağı taşıyan her çağrı için **kullanıcıdan onay ister**. Onay
yüzeyi istemcide yaşar; forkOS kendi onay tablosunu/kuyruğunu KURMAZ.

Kurmayın / önermeyin:

```yaml
approvals:
  mode: off        # ✗ onay kapısını kaldırır
trust: full        # ✗ untrusted yerine tam güven
```

---

## 3. Bağlantıyı doğrulama

### Adım 1: Araç yüzeyini görün (19 araç beklenir)

```bash
python3 -c "
import asyncio
from mcp.client.streamable_http import streamable_http_client
from mcp.client.session import ClientSession

async def main():
    async with streamable_http_client('http://127.0.0.1:8787/mcp') as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            print('tool count:', len(tools))
            for t in tools:
                print(f'{t.name:32s} readOnly={t.annotations.read_only_hint!s:5s} '
                      f'destructive={t.annotations.destructive_hint!s:5s} '
                      f'idempotent={t.annotations.idempotent_hint}')

asyncio.run(main())
"
```

**Beklenen:** 19 araç; 8 okuma `readOnly=True`, 11 yazma `readOnly=False` ve
hepsi `destructive=False`.

### Adım 2: Okuma turu (onay gerektirmez)

```bash
python3 -c "
import asyncio
from mcp.client.streamable_http import streamable_http_client
from mcp.client.session import ClientSession

async def main():
    async with streamable_http_client('http://127.0.0.1:8787/mcp') as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool('brain_status', {})
            print(result.content[0].text)

asyncio.run(main())
"
```

### Adım 3: Yazma turu (onay gerektirir)

Aynı istemciyle bir görev oluşturmayı deneyin:

```python
result = await session.call_tool('forkos_todo_create', {'title': 'H1 kurulum denemesi'})
print(result.is_error, result.content[0].text)
```

`trust: untrusted` altında Hermes bunu **onay istemiyle** göstermelidir.
forkOS tarafında dönen makbuz şu biçimdedir:

```json
{
  "source": "forkos",
  "data": {
    "tool": "forkos_todo_create",
    "status": "executed",
    "target_type": "todo",
    "target_id": "…",
    "summary": "Created todo \"H1 kurulum denemesi\"",
    "changed_fields": ["title", "priority", "status", "tags", "..."],
    "before": {},
    "after": { "title": "H1 kurulum denemesi", "status": "open", "priority": 2 }
  }
}
```

> Bu adım gerçek bir görev oluşturur. Denemek istemezseniz Adım 1 ve 2 yeterlidir.

---

## 4. Araç allowlist profilleri

Araç filtreleme **istemci yapılandırmasıdır**, sunucu yetkilendirmesi DEĞİLDİR:
sunucu 19 aracı da sunar, hangilerinin Hermes'e görüneceğine siz karar verirsiniz.

### Tam profil (önerilen)

19 aracın tamamı açık. H1, kapsamı ve onay akışını kanıtlamak için tasarlandı;
araçları kısıtlamak zorunda değilsiniz.

### Muhafazakâr profil

Yalnızca en sık kullanılan yazmalar açık:

```text
8 H0 okuma aracı
+ forkos_todo_create
+ forkos_todo_update
+ forkos_todo_complete
+ forkos_todo_plan
+ brain_capture
+ brain_save_to_entity
```

Kapalı kalanlar: `forkos_project_update`, `forkos_opportunity_transition`,
`forkos_application_transition`, `forkos_bookmark_capture`,
`forkos_bookmark_update`.

---

## 5. Hermes sistem prompt'una eklenecek davranış kuralları

```text
- Yazma işlemleri onay gerektirir; onay kullanıcıya aittir.
- Bir mutasyondan önce hedefi araçlarla ÇÖZ; UUID tahmin etme.
- Kullanıcı açıkça istemediyse yazmaları ZİNCİRLEME.
- Her yazmadan sonra gerçek makbuzu raporla (status = executed | noop).
- Sonucu belirsiz bir yazmadan sonra önce OKU (brain_read), sonra gerekirse
  tekrar dene; kör otomatik tekrar YAPMA.
- Kullanıcının istemediği hiçbir şeyi hafızaya yazma.
```

---

## 6. Sık karşılaşılan durumlar

| Belirti | Neden | Çözüm |
|---|---|---|
| Yazma çağrısı `TARGET_NOT_FOUND` | UUID yanlış/eski | Önce `forkos_search` + `forkos_entity_context` ile hedefi çöz |
| `STALE_ACTION` | Kullanıcı onaylarken durum değişti | Güncel durumu yeniden oku, kullanıcıya tekrar sor |
| `AMBIGUOUS_PLAN` | Görev için birden fazla gelecek plan kaydı var | Plan kayıtlarını tek kayda indir |
| `VAULT_UNAVAILABLE` | Vault tanımlı değil/erişilemez | `make up-obsidian` + `OBSIDIAN_VAULT_*` kontrol et |
| `VAULT_STALE` | Not, okunduktan sonra Obsidian'da değişti | `brain_read` ile güncel gövdeyi al, sonra tekrar dene |
| `VAULT_CONFLICT` | Aynı `forkos_id` iki dosyada | Çakışmayı Vault'ta çöz, indeksi yenile |
| `HEADING_NOT_FOUND` / `AMBIGUOUS_HEADING` | Başlık yok/çok | Başlıksız ekleme yap veya başlığı netleştir |
| `INVALID_INPUT` | Şema sınırı ihlali | Araç sözleşmesindeki sınırlara bak (`h1-tool-contract.md`) |

> **Vault yoksa ne olur?** Bilgi yazmaları **açıkça hata verir**; forkOS legacy
> Notlar tablosuna DÜŞMEZ. Operasyonel özellikler (görev, odak, fırsat, RSS)
> çalışmaya devam eder.

---

## 7. İlgili belgeler

- `h1-safe-actions.md` — onay modeli, tazelik kuralları, makbuz yapısı.
- `h1-tool-contract.md` — 19 aracın tam sözleşmesi.
- `h0-setup.md` — okuma yüzeyinin kurulumu (H1 bunun üzerine eklenir).
