# forkOS × Hermes — H2 Kurulum ve Gizlilik Sınırı

H2 ek bir sunucu, servis ya da anahtar GEREKTİRMEZ. Yalnızca:

```text
1. forkOS çalışıyor olmalı (MCP /mcp ucu)
2. Obsidian Vault bağlı olmalı (sıcak hafıza orada yaşar)
3. Hermes'te kalıcı hafıza KAPALI olmalı (tek sahiplik)
```

> [!IMPORTANT]
> forkOS, kullanıcının kişisel yapılandırmasına (`~/.hermes/config.yaml` vb.)
> **ASLA otomatik olarak dokunmaz**. Aşağıdakiler elle eklenir.

---

## 1. Ön koşullar

```bash
make up-obsidian CO="docker compose"
```

```env
OBSIDIAN_VAULT_HOST_PATH=/Users/kullanici/Documents/f0rknbrain
OBSIDIAN_VAULT_NAME=f0rknbrain
```

`90 Agent/Memory/` dizini **açılışta oluşturulmaz**. Yalnızca onaylanmış ilk
yazma geldiğinde tembel olarak oluşturulur; açılış salt okunurdur.

---

## 2. MCP yapılandırması (değişmedi)

```yaml
mcp_servers:
  forkos-brain:
    type: http
    url: "http://127.0.0.1:8787/mcp"
    trust: untrusted          # yazma araçları onay ister
    headers: {}
    timeout: 30
```

H2 yazma araçları `readOnlyHint=false` taşır; `untrusted` modda Hermes her
çağrı için kullanıcıdan onay ister. forkOS kendi onay sistemini KURMAZ.

---

## 3. Hermes'in kendi kalıcı hafızası KAPATILMALI

Sıcak hafızanın kanonik sahibi f0rknbrain'dir. Hermes'in yerleşik hafızası
açık kalırsa **ikinci bir hafıza kaynağı** doğar ve "ne hatırlıyorsun?"
sorusunun cevabı bölünür.

Önerilen (Hermes sürümünüzdeki anahtar adlarını kendi dokümanından doğrulayın):

```yaml
memory:
  memory_enabled: false
  user_profile_enabled: false
```

Doğrulanmamış anahtar adlarını körü körüne uygulamayın; Hermes'in sürüm
dokümanına bakın. **Bu dosya hiçbir şeyi otomatik değiştirmez.**

Harici hafıza sağlayıcısı (Mem0, Hindsight, Honcho, Supermemory vb.) kuruluysa
**sessizce kaldırılmaz**; yalnızca bunun ikinci bir kaynak yarattığı ve H2'nin
desteklenen mimarisine dâhil olmadığı bilinmelidir.

Neden harness bağımsızlığı: hafıza `Markdown + Obsidian + Git + kullanıcıya
ait` kalır. Ajanı değiştirmek (yarın başka bir istemci, sonra yerel model)
kişisel hafızayı SİLMEZ.

---

## 4. Gizlilik sınırı — dürüst ifade

```text
forkOS/f0rknbrain H2 için hiçbir dış ağ çağrısı yapmaz.
```

ancak:

```text
MCP araç sonuçlarını Hermes tüketir.
Hermes UZAK bir model sağlayıcısı kullanıyorsa,
sıcak hafıza bağlamı o sağlayıcıya model girdisi olarak gidebilir.
```

Bu yüzden sıcak hafıza küçük, hassas olmayan ve amaçlı kalmalıdır
(`h2-memory-policy.md`). H4 (yerel model yönlendirme) gelene kadar
"uçtan uca yerel çıkarım" GARANTİ EDİLMEZ; öyle bir vaat verilmez.

Ajan çıktısı mutlak dosya yolu taşımaz; yalnızca göreli yollar döner.

---

## 5. Doğrulama

### 5.1 Araç yüzeyi (24 araç beklenir)

```bash
python3 -c "
import asyncio
from mcp.client.streamable_http import streamable_http_client
from mcp.client.session import ClientSession

async def main():
    async with streamable_http_client('http://127.0.0.1:8787/mcp') as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = (await s.list_tools()).tools
            print('tool count:', len(tools))
            for t in tools:
                if t.name.startswith('hot_memory'):
                    print(f'{t.name:24s} readOnly={t.annotations.read_only_hint} '
                          f'destructive={t.annotations.destructive_hint} '
                          f'idempotent={t.annotations.idempotent_hint}')

asyncio.run(main())
"
```

Beklenen:

```text
tool count: 24
hot_memory_context   readOnly=True  destructive=False idempotent=True
hot_memory_list      readOnly=True  destructive=False idempotent=True
hot_memory_store     readOnly=False destructive=False idempotent=False
hot_memory_update    readOnly=False destructive=False idempotent=True
hot_memory_retire    readOnly=False destructive=False idempotent=True
```

### 5.2 Boş hafıza normaldir

H2 **boş başlar**. Uygulama, mevcut kasayı, veritabanını, eski konuşmaları ya
da Hermes hafıza dosyalarını tarayıp otomatik hafıza ÜRETMEZ. Doldurma,
kullanıcının konuşma sırasında bilinçli tercihidir.

---

## 6. Sık karşılaşılan durumlar

| Belirti | Neden | Çözüm |
|---|---|---|
| `HOT_MEMORY_UNAVAILABLE` | Vault tanımlı değil/erişilemez | `make up-obsidian` + `OBSIDIAN_VAULT_*` |
| `HOT_MEMORY_STALE` | Dosya okunduktan sonra Obsidian'da değişti | `hot_memory_list` ile güncel `revision` al, sonra tekrar dene |
| `HOT_MEMORY_CONFLICT` | Aynı `memory_id` iki dosyada | Kopyayı Vault'ta uzlaştır; aktif bağlam fail-closed kalır |
| `HOT_MEMORY_POLICY_REJECTED` | Metin apaçık sır biçimi içeriyor | Sıcak hafızaya yazmayın; normal Vault notu kullanın |
| `INVALID_RELATED_ENTITY` | Kimlik yok/arşiv/dondurulmuş tip | Geçerli aktif operasyonel kayıt kullan |
| `status=noop` (store) | Aynı tür + metin zaten var | Mevcut kaydı `hot_memory_update` ile güncelle |
| `INVALID_EXPIRY` / şema hatası | `expires_at` ISO değil | ISO-8601 tarih ver |

---

## 7. İlgili belgeler

- `h2-hot-memory.md` — mimari, depolama, revizyon, bütçe.
- `h2-memory-policy.md` — ne hatırlanır/hatırlanmaz, aday akışı.
- `h2-tool-contract.md` — 5 aracın tam sözleşmesi.
- `h1-setup.md` — yazma onay modeli.
