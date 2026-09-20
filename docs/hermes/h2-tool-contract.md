# forkOS × Hermes — H2 Araç Sözleşmesi (Sıcak Hafıza)

H2, Brain Interface'e **tam olarak 5 araç** ekler. Genel yüzey:

```text
8 H0 okuma  +  11 H1 yazma  +  5 H2 hafıza  =  24 MCP aracı
```

H2 araçlarının tamamı için:

```text
external network : NO          (dış ağ çağrısı yapmaz)
destructiveHint  : false       (silme yeteneği YOKTUR)
DB               : okumalar hiç dokunmaz; yazmalar yalnızca related_forkos_ids doğrular
Vault            : yalnızca 90 Agent/Memory/<memory_id>.md
```

H2 hata kodları:

```text
HOT_MEMORY_NOT_FOUND     HOT_MEMORY_STALE      HOT_MEMORY_CONFLICT
HOT_MEMORY_INVALID       HOT_MEMORY_UNAVAILABLE
HOT_MEMORY_POLICY_REJECTED
INVALID_EXPIRY           INVALID_RELATED_ENTITY
```

---

## 1. `hot_memory_context`

**Amaç:** kişiselleştirilmiş akıl yürütme için AKTİF sıcak hafızanın küçük,
sınırlı paketini döner.

| | |
|---|---|
| Anotasyonlar | `readOnly=true`, `destructive=false`, `idempotent=true` |
| Girdi | `kinds` (opsiyonel; verilmezse tüm kategoriler) |
| Çıktı | `HotMemoryContextData` |
| Yan etki | YOK — ne DB ne Vault |
| Ağ | NO |

Davranış:

- Süresi geçmiş (`expired`) ve emekli (`retired`) öğeler **hariçtir**.
- Bütçe: en fazla **24 öğe** ve **~6000 karakter** metin; tür başına
  `profile 5 | preference 6 | goal 5 | constraint 6 | decision 6`.
- Sıralama deterministiktir: `importance ↓`, `updated_at ↓`, `memory_id ↑`.
- Kategori sırası sabittir: `profile, preferences, goals, constraints, decisions`.
- Bütçe dışı kalan varsa dürüstçe bildirilir: `truncated`, `active_total`,
  `returned_total`, `omitted_total`.
- **Kimlik çakışması varsa fail-closed:** `HOT_MEMORY_CONFLICT` (rastgele
  seçim yapılmaz).
- Şema dışı dosyalar okumayı düşürmez: `invalid_count` ve `warnings` bildirilir.

Çıktı örneği:

```json
{
  "as_of": "2026-09-20T18:00:00Z",
  "source": "f0rknbrain",
  "data": {
    "profile": [],
    "preferences": [
      {
        "memory_id": "…",
        "kind": "preference",
        "title": "Planning style",
        "text": "Prefers project-level plans over hourly schedules.",
        "importance": 2,
        "updated_at": "…",
        "expires_at": null,
        "related_forkos_ids": [],
        "revision": "…"
      }
    ],
    "goals": [], "constraints": [], "decisions": [],
    "active_total": 1, "returned_total": 1, "omitted_total": 0,
    "invalid_count": 0, "truncated": false, "warnings": []
  },
  "truncated": false
}
```

---

## 2. `hot_memory_list`

**Amaç:** yönetim ve keşif listesi; emekli/süresi geçmiş kayıtlar da görülebilir.

| | |
|---|---|
| Anotasyonlar | `readOnly=true`, `destructive=false`, `idempotent=true` |
| Girdi | `kind`, `effective_status` (`active\|expired\|retired\|all`), `query`, `limit` (varsayılan 20, en fazla 50) |
| Çıktı | `HotMemoryListData` |
| Yan etki | YOK |
| Ağ | NO |

`query` yalnızca **leksikaldir** (başlık, metin, etiket): tam başlık > etiket >
başlık kelimesi > metin; eşitlikte `updated_at ↓`. Embedding/semantik benzerlik
YOKTUR.

Her öğe: `memory_id, kind, title, text, status, effective_status, importance,
source_mode, created_at, updated_at, expires_at, related_forkos_ids, tags,
revision, relative_path` — `relative_path` **görelidir**, mutlak yol dönmez.

Şema dışı dosyalar: `invalid_count` + sınırlı `invalid_paths` (göreli).

```text
invalid_count  = şema dışı + politika dışı dosyaların GERÇEK sayısı
invalid_paths  = yalnızca ilk 20 göreli yol (MAX_INVALID_REPORTED)
```

Politika nedeniyle dışlanan dosyalar (bkz. §3) ayrıca sayılır ve
`hot_memory_context` uyarısında raporlanır; sır, gövde ya da mutlak yol
raporlanmaz. Çakışmalar fatal değildir, `conflict_ids` olarak raporlanır.

---

## 3. `hot_memory_store`

**Amaç:** ONAYLANMIŞ tek bir sıcak hafıza öğesi oluşturur.

| | |
|---|---|
| Anotasyonlar | `readOnly=false`, `destructive=false`, `idempotent=false` |
| Girdi | `kind*`, `title*` (1-120), `text*` (1-1200), `source_mode*` (`explicit_user\|approved_candidate`), `importance` (1-3, varsayılan 2), `expires_at`, `related_forkos_ids` (en fazla 5), `tags` (en fazla 8) |
| Çıktı | `ActionReceipt` (`target_type=hot_memory`) |
| Yan etki | **tek** Markdown dosyası: `90 Agent/Memory/<yeni UUID>.md` |
| DB | ZERO (yalnızca `related_forkos_ids` doğrulanırsa salt-okunur sorgu) |
| Ağ | NO |

Kurallar:

- `memory_id`'yi **sunucu üretir**; çağıran kimlik veremez.
- **Yol girdisi YOKTUR** (`path`, `relative_path` şemada bulunmaz).
- **Kesin tekrar YALNIZCA aktif kayıt için:** aynı `kind` + normalize edilmiş
  `text` zaten **aktifse** yeni dosya açılmaz → `status=noop`, mevcut
  `memory_id` döner. Emekli ya da süresi geçmiş kayıt engellemez: aynı olgu
  sonradan yeniden hatırlatılırsa **yeni aktif kayıt** doğar (yeni
  `memory_id`); eski kayıt değişmeden kalır.
- Apaçık kimlik bilgisi biçimi → `HOT_MEMORY_POLICY_REJECTED`. Aynı denetim
  OKUMA anında da uygulanır: elle düzenlenmiş bir dosya sır taşıyorsa
  yüklenmez, DEĞİŞTİRİLMEZ ve H0 yüzeyinden de (`brain_search`/`brain_read`)
  dışlanır.
- `related_forkos_ids` aktif operasyonel kayıtlar olmalı; dondurulmuş arşiv
  (`note`, `note_folder`, `note_attachment`) ya da arşivlenmiş kayıt reddedilir
  (`INVALID_RELATED_ENTITY`). **Link/Entity satırı oluşturulmaz.**
- Oluşturma **atomiktir ve üzerine yazmaz**: hedef yalnızca içeriği tam olan
  dosyaya bağlanır; başarısız oluşturma ne yarım hedef ne artık geçici dosya
  bırakır.
- Vault yoksa `HOT_MEMORY_UNAVAILABLE`; başka depoya düşülmez.

---

## 4. `hot_memory_update`

**Amaç:** var olan öğeyi düzeltir/inceltir.

| | |
|---|---|
| Anotasyonlar | `readOnly=false`, `destructive=false`, `idempotent=true` |
| Zorunlu | `memory_id`, `expected_revision` (sha256, 64 karakter) |
| Değiştirilebilir | `kind`, `title`, `text`, `importance`, `expires_at`, `related_forkos_ids`, `tags` |
| Değiştirilemez | `status`, `created_at`, `source_mode`, `memory_id`, `relative_path` |
| Çıktı | `ActionReceipt` |
| Ağ | NO |

Kurallar:

- **Verilmeyen alan korunur, açık `null` temizler** (`expires_at: null` süreyi
  siler; `tags: []` etiketleri temizler). Bu ayrım ham MCP argümanlarından
  okunur (H1.1/H1.2 sözleşmesi).
- `expected_revision` uyuşmazsa `HOT_MEMORY_STALE`; **hiçbir yazma yapılmaz**
  ve kullanıcı düzenlemesi korunur.
- Doğrulama **dosyanın şu anki baytları** üzerinden yapılır ve `noop`
  kararından ÖNCE gelir. İstenen değerler mevcut duruma eşit olsa bile bayat
  revizyon `HOT_MEMORY_STALE` verir — sessiz bir `noop` makbuzu verilmez.
- Sonuç aynıysa (ve revizyon güncelse) `status=noop`; **dosya yeniden
  yazılmaz**, `updated_at` tazelenmez.
- Bilinmeyen kullanıcı frontmatter anahtarları KORUNUR.
- Kimlik çakışması varsa `HOT_MEMORY_CONFLICT`.

---

## 5. `hot_memory_retire`

**Amaç:** güncelliğini yitirmiş bir hafızayı **kullanmayı bırakır**, tarihsel
kanıtı korur.

| | |
|---|---|
| Anotasyonlar | `readOnly=false`, `destructive=false`, `idempotent=true` |
| Zorunlu | `memory_id`, `expected_revision` |
| Opsiyonel | `reason` (en fazla 240) |
| Mutasyon | `status=retired`, `retired_at=now`, `retired_reason`, `updated_at=now` |
| Ağ | NO |

Kurallar:

- **Silme DEĞİLDİR:** dosya Vault'ta ve Git geçmişinde kalır; makbuz bunu
  açıkça uyarı olarak söyler.
- Aktif bağlamdan çıkar; `hot_memory_list(effective_status="retired")` ile
  görünür kalır.
- Zaten emekliyse `status=noop`; **yeniden yazma yok** — ama yalnızca
  `expected_revision` GÜNCEL ise. Bayat revizyon, "zaten emekli" kararından
  ÖNCE kazanır: `HOT_MEMORY_STALE`.
- Güncelleme ile aynı CAS kuralı: karar, dosyanın şu anki baytlarının
  hash'inden gelir; kullanıcı düzenlemesi ezilmez.

---

## 6. Özet

| Araç | readOnly | destructive | idempotent | DB | Vault | Ağ |
|---|---|---|---|---|---|---|
| `hot_memory_context` | `true` | `false` | `true` | yok | okuma | yok |
| `hot_memory_list` | `true` | `false` | `true` | yok | okuma | yok |
| `hot_memory_store` | `false` | `false` | `false` | salt-okunur doğrulama | 1 dosya oluşturma | yok |
| `hot_memory_update` | `false` | `false` | `true` | salt-okunur doğrulama | 1 dosya güncelleme | yok |
| `hot_memory_retire` | `false` | `false` | `true` | yok | 1 dosya güncelleme | yok |

Silme aracı, aday aracı, "konuşmayı kaydet" aracı ve toplu işlem aracı
**yoktur** — ve olmamalıdır.

---

## 7. Yüzey doğrulaması

```bash
make up-obsidian CO="docker compose"
curl -s http://127.0.0.1:8787/mcp   # resmi MCP istemcisiyle list_tools
```

Beklenen: **24 araç**; H2 okuma araçları `readOnly=true`, yazmalar
`readOnly=false` ve hepsi `destructive=false`.
