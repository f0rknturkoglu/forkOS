# forkOS × Hermes — H3 Kurulum ve Doğrulama

H3 **yeni yapılandırma gerektirmez**: yeni ortam değişkeni, yeni tablo, yeni
migration, yeni servis yoktur. Var olan `/mcp` ucu ve var olan `OBSIDIAN_VAULT_PATH`
ayarı yeterlidir.

---

## 1. Ön koşullar

```text
PostgreSQL erişilebilir        (Entity / Link / Event okuması)
OBSIDIAN_VAULT_PATH ayarlı     (scope=knowledge veya scope=all için)
branch: main · H3 öncesi baseline: 9417321
```

Kasa yoksa:

```text
scope=operational → çalışır (Vault'a hiç dokunmaz)
scope=all         → operasyonel kanıt + VAULT_UNAVAILABLE uyarısı
scope=knowledge   → VAULT_UNAVAILABLE hatası
```

Hiçbir bozulmuş mod sessiz değildir.

---

## 2. MCP yapılandırması (değişmedi)

`forkos_evidence` var olan sunucuya kayıtlıdır; istemci tarafında ek ayar
gerekmez. Araç salt-okunurdur (`readOnlyHint=true`), bu yüzden onay akışına
girmez. Yazma araçları (`readOnlyHint=false`) için onay modeli değişmedi.

---

## 3. Doğrulama

### 3.1 Araç yüzeyi (25 araç beklenir)

```bash
cd backend
DATABASE_URL="postgresql+asyncpg://lifeos:lifeos@127.0.0.1:15433/forkos_test" \
  .venv/bin/python -m pytest tests/test_agent_h3_contract.py -q
```

Beklenen: yüzey tam olarak **25** araçtır ve `forkos_evidence` anotasyonları

```text
readOnlyHint=true · destructiveHint=false · idempotentHint=true
```

Şema sınırları:

```text
query      minLength=2   maxLength=200   (zorunlu)
scope      enum: all | operational | knowledge
max_depth  minimum=0     maximum=2
limit      minimum=1     maximum=15
```

Aralık dışı `max_depth`/`limit` **kırpılmaz, reddedilir** (`INVALID_MAX_DEPTH`,
`INVALID_LIMIT`). Gerçek MCP'de bu değerler zaten şema katmanında reddedilir;
doğrudan Python çağrısında çalışma zamanı aynı sınırı bağımsız dayatır.

### 3.2 Davranış ve taşıma

```bash
cd backend
DATABASE_URL="postgresql+asyncpg://lifeos:lifeos@127.0.0.1:15433/forkos_test" \
  .venv/bin/python -m pytest \
    tests/test_agent_h3_contract.py \
    tests/test_agent_h3_evidence.py \
    tests/test_agent_h3_transport.py \
    tests/test_obsidian_evidence.py -q
```

Kapsam:

| Dosya | Ne kanıtlar |
|---|---|
| `test_agent_h3_contract.py` | Yüzey (25), anotasyon, şema sınırları, hata kodları, yasak alan yokluğu, sınır kırpma |
| `test_agent_h3_evidence.py` | Kanallar, öncelik sırası, köken zincirleri, kapsam ayrımı, döngü/patlama/bütçe, değişmezlik, determinizm |
| `test_agent_h3_transport.py` | Gerçek `/mcp`: şema + anotasyon + değişmezlik + sır sızıntısı yok + determinizm |
| `test_obsidian_evidence.py` | Kasa primitifleri: yol politikası, tokenizasyon, başlık dilimleri, TAM satır numaraları, wikilink/backlink, salt-okunurluk |

### 3.3 Regresyon

```bash
cd backend
DATABASE_URL="postgresql+asyncpg://lifeos:lifeos@127.0.0.1:15433/forkos_test" \
  .venv/bin/python -m pytest tests/test_agent_*.py -q
```

H0 (8 araç), H1 (11 araç + `MCP_ARGUMENT_BINDING_UNAVAILABLE` fail-closed
davranışı), H2 (5 araç + CAS + tüm-artifact politikası) değişmeden yeşil
kalmalıdır.

Kanonik tam koşu:

```bash
make test CO="docker compose"
```

### 3.4 Statik kontroller

```bash
cd backend && .venv/bin/python -m ruff check app tests scripts
git diff --check
```

---

## 4. Ölçümler (gerçek donanım, sentetik veri)

Ölçüm ortamı: 500 notluk kasa (500 dosya / 1692 KiB), 1 proje, 24 görev,
8 alt kilometre taşı, 12 olay. Beş koşunun medyanı.

| Yol | Gecikme | Kanıt | Karakter | Grafik düğümü | Olay |
|---|---:|---:|---:|---:|---:|
| Sorgu-only operational | 3.2 ms | 1 | 422 | 0 | 0 |
| Sorgu-only knowledge (500 dosya taraması) | 110.1 ms | 8 | 7616 | 0 | 0 |
| Çekirdek, derinlik 0 | 119.3 ms | 12 | 1092 | 0 | 8 |
| Çekirdek, derinlik 1 | 124.0 ms | 12 | 1272 | 24 | 8 |
| Çekirdek, derinlik 2 | 124.7 ms | 12 | 1272 | 24 | 8 |
| Yalnız kasa taraması | 110.2 ms | — | — | — | 500 dosya okundu |

Yorumlar:

- Baskın maliyet **kasa taramasıdır** (~0.22 ms/dosya). Gerçek kasa 28 dosya
  olduğu için beklenen gecikme ~6 ms'dir; 500 dosya tavanı en kötü durumu
  ~110 ms'de sınırlar.
- Grafik genişlemesi (24 düğüm) + olay okuması derinlik 0 → 1 arasında
  ~5 ms ekler. H3.1'den beri BFS istek başına **bir kez** çalışır (önce iki
  kez çalışıyordu); `scope=all` bu yüzden bir tur daha az sorgu atar.
- Derinlik 2, düğüm tavanı (25) derinlik 1'de dolduğu için ek maliyet getirmez.
- Ölçümler bilgi amaçlıdır; **kırılgan CI zamanlama eşiği yoktur**.

---

## 5. Sorun giderme

| Belirti | Neden | Yapılacak |
|---|---|---|
| `VAULT_UNAVAILABLE` | `OBSIDIAN_VAULT_PATH` boş ya da dizin yok | Yolu ayarla; `scope=operational` kasa olmadan da çalışır |
| `VAULT_CONFLICT` uyarısı | İki dosya aynı `forkos_id`'yi taşıyor | Dosyalardan birinin `forkos_id`'sini düzelt; H3 hedef tahmin ETMEZ |
| `ambiguity` uyarısı | Çıplak `[[Rust]]` birden fazla nota çözülüyor | Notu `[[30 Knowledge/Rust]]` gibi yol nitelikli yaz |
| `truncated=true` | Bir kanal bütçeye takıldı | İzi oku: hangi aşama kesildi (`retrieval_trace`) |
| Olay kanalı `truncated=true` | 9+ uygun olay veya 121+ olay satırı | İz'deki `events.considered/accepted` sayılarına bak |
| `INVALID_MAX_DEPTH` / `INVALID_LIMIT` | Sınır aralık dışı (kırpma YOK) | 0–2 ve 1–15 aralığına çek |
| `omitted_total` beklenenden küçük | Yalnızca **sayılabilen** atlanan adaylar sayılır | Tarama tavanı gibi bilinmeyen toplamlarda uyarıya ve iz sayaçlarına bak |
| `TIME_FILTER_REQUIRES_ENTITY_SEED` | Zaman filtresi olay kanalına aittir | `entity_id` ver; global olay araması H3'te YOKTUR |
| `INVALID_TIME_RANGE` | Saat dilimsiz damga | `2026-09-01T00:00:00+03:00` ya da `...Z` yaz |
| Sonuç boş + `recovery_hint` | Sorgu çok genel ya da kasa boş | Daha özgül sorgu ya da `entity_id` ver |

---

## 6. Sınırların tek listesi

```text
query                2-200 karakter            (şema + çalışma zamanı)
limit                1-15, varsayılan 12       (şema + çalışma zamanı)
max_depth            0-2, varsayılan 1         (şema + çalışma zamanı)
snippet/öğe          ≤ 1200 karakter
toplam snippet       ≤ 8000 karakter
en küçük snippet     120 karakter
grafik düğümü        ≤ 25
olay kanıtı          ≤ 8
olay tarama penceresi ≤ 120 (+1 nöbetçi)
entity adayı         ≤ 5 (sorgu-only)
uyarı                 ≤ 10 (her biri ≤ 300 karakter)
kasa dosya taraması  ≤ 500
tek dosya            ≤ 256 KiB
çapalı kasa notu     ≤ 12
sorgu terimi         ≤ 12
```

---

## 7. Gizlilik sınırı — dürüst ifade

```text
forkOS H3 hiçbir dış model/API çağrısı yapmaz: 0 HTTP, 0 DNS, 0 dış soket.
```

Ancak `EvidenceBundle` içeriğini MCP istemcisi (Hermes) tüketir; uzak bir model
sağlayıcısı kullanılıyorsa bu içerik oraya gidebilir. "Uçtan uca yerel" iddiası
ancak model çalıştırma yolu gerçekten yerelleştikten sonra yapılabilir.

Ek olarak:

- Mutlak kasa yolu hiçbir yanıt veya tanılamada görünmez.
- Olay payload'ları kanonik `sanitize_payload` ile maskelenir.
- `90 Agent/Memory` kanıt taramasının dışındadır; sıcak hafıza
  `hot_memory_context` ile ayrıca sunulur.

---

## 8. İlgili belgeler

- [H3 Kanıt Getirme](h3-retrieval-evidence.md) — mimari, kanallar, öncelik, köken.
- [H3 Araç Sözleşmesi](h3-tool-contract.md) — imza, modeller, hata kodları.
- [H2 Kurulum](h2-setup.md) · [H1 Güvenli Eylemler](h1-safe-actions.md)
  · [H0 Beyin Arayüzü](h0-brain-interface.md)
