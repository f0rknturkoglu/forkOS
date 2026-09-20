# forkOS × Hermes — H3 Araç Sözleşmesi (`forkos_evidence`)

H3 genel yüzeye **tam olarak bir** araç ekler. H0'ın `forkos_search`,
`forkos_entity_context`, `forkos_project_context`, `forkos_recent_activity`,
`brain_search` ve `brain_read` araçları YERİNDE kalır; `forkos_evidence` bu
alanları birleştiren **sınırlı orkestrasyon** katmanıdır.

---

## 1. İmza

```text
forkos_evidence(
    query:        str,                                   # ZORUNLU, 2-200
    entity_id:    str | None = None,                     # açık çekirdek (UUID)
    scope:        "all" | "operational" | "knowledge" = "all",
    since:        str | None = None,                     # ISO-8601, saat dilimli
    until:        str | None = None,                     # ISO-8601, saat dilimli
    max_depth:    int = 1,                               # 0-2
    limit:        int = 12                               # 1-15
) -> AgentEnvelope[EvidenceBundle]
```

Anotasyonlar:

```text
readOnlyHint    = true
destructiveHint = false
idempotentHint  = true
```

Onay gerekmez (yazma yoktur).

### 1.1 Girdi sözleşmesi

| Alan | Kural | İhlalde |
|---|---|---|
| `query` | Zorunlu; boş/whitespace kabul edilmez | `INVALID_QUERY` |
| `query` uzunluğu | 2–200 | `QUERY_TOO_SHORT` / `QUERY_TOO_LONG` |
| `entity_id` | UUID; var olmalı; dondurulmuş legacy olmamalı | `INVALID_UUID` / `ENTITY_NOT_FOUND` / `FROZEN_ENTITY_UNAVAILABLE` |
| `scope` | `all` \| `operational` \| `knowledge` | `INVALID_SCOPE` |
| `since` / `until` | ISO-8601 **ve saat dilimli** (`+03:00`, `Z`) | `INVALID_TIME_RANGE` |
| `since > until` | Reddedilir | `INVALID_TIME_RANGE` |
| `since`/`until` + çekirdek yok | Reddedilir (olaylar çapa ister) | `TIME_FILTER_REQUIRES_ENTITY_SEED` |
| `max_depth` | 0–2; aralık dışı **REDDEDİLİR** | `INVALID_MAX_DEPTH` |
| `limit` | 1–15; aralık dışı **REDDEDİLİR** | `INVALID_LIMIT` |

`query` zorunludur: bu araç genel bağlam dökümü DEĞİLDİR. Genel bağlam için
`forkos_entity_context` / `forkos_project_context` vardır.

Zaman damgası saat dilimsiz verilirse **reddedilir** (ör.
`2026-09-01T00:00:00`); yerel saat varsayımı sessiz bir yanlış cevaba dönüşürdü.

**İki savunma katmanı:** MCP şeması ilk savunmadır (aralık/enum ihlalleri
handler'a ulaşmadan reddedilir); çalışma zamanı otoritedir (şemadan geçen ama
anlamsız girdiler — geçersiz UUID, çapasız zaman filtresi — servis katmanında
reddedilir). Doğrudan Python çağıranları şemayı atlayabildiği için ikinci katman
gereklidir.

Aralık dışı `max_depth`/`limit` **sessizce kırpılmaz**: `max_depth=3` hata
verir, 2'ye düşürülmez; `limit=16` hata verir, 15'e düşürülmez. H2.2 ilkesi:
şema bağı = çalışma zamanı bağı.

Tek istisna **sorgu-only** durumdur: `entity_id` yokken `max_depth=2` geçerli
bir girdidir, ama çekirdek olmadığı için etkin derinlik **0**'dır ve grafik
gezinmesi yapılmaz. Bu bir hata değil, kapsam semantiğidir.

---

## 2. Çekirdek davranışı

| Durum | Davranış |
|---|---|
| `entity_id` VAR | Çekirdek olarak çözülür; grafik, olaylar ve yönetilen not bu noktadan genişler. |
| `entity_id` YOK + `scope=operational` | Yalnızca leksikal entity adayları döner; **hiçbir aday kök yapılıp genişletilmez**. |
| `entity_id` YOK + `scope=knowledge` | Yalnızca leksikal kasa kanıtı; leksikal sonuçtan bağ gezinmesi YAPILMAZ. |
| `entity_id` YOK + `max_depth` verilmiş | Etkin derinlik **0**'dır; iz bunu açıkça söyler. |
| Dondurulmuş legacy entity (PK) | `FROZEN_ENTITY_UNAVAILABLE` + kasaya yönlendiren ipucu. Legacy not DB'den okunmaz. |
| Arşivlenmiş entity (açık çekirdek) | Kanıt olarak döner ama `archived_at` **dürüstçe** gösterilir; komşuları varsayılan olarak genişletilmez. |
| Arşivlenmiş komşu | Genişletilmez (güncel durumu olmayan kayıt komşu gibi sunulmaz). |

Kimlik çözümünde `ResolvedEntityRef.resolution` ayrımı kritiktir:

```text
explicit_seed      → kullanıcı/çağıran tarafından açıkça verildi
lexical_candidate  → sorguyla eşleşti; "çözülmüş gerçek" DEĞİLDİR (expanded=false)
```

---

## 3. Çıktı modeli

### 3.1 `EvidenceBundle`

| Alan | Anlam |
|---|---|
| `query` | Getirmenin yapıldığı soru/iddia. |
| `entity_seed` | Kullanılan açık çekirdek UUID'si (yoksa `null`). |
| `resolved_entities` | Pakete giren entity'ler ve nasıl girdikleri. |
| `evidence` | Öncelik sırasına dizilmiş kanıt öğeleri. |
| `retrieval_trace` | Hangi kanalın kaç aday gördüğü/kabul ettiği (olgu, akıl yürütme değil). |
| `sources_used` | Gerçekten danışılan sahiplik alanları: `forkos`, `f0rknbrain`. |
| `truncated` | Herhangi bir kanal ya da öğe bütçeyle kesildi mi. |
| `omitted_total` | **Bilinen** atlanan aday sayısı (tahmin değil). |
| `warnings` | Sınırlı, model-okunur uyarılar. |
| `recovery_hint` | Eyleme dönük sonraki adım (varsa). |

### 3.2 `EvidenceItem`

| Alan | Anlam |
|---|---|
| `evidence_id` | `entity:<uuid>` · `event:<id>` · `vault:<locator>#<başlık\|root>` |
| `source_type` | `entity` \| `event` \| `vault` |
| `source_id` | Yönetilen notta `forkos_id`; yönetilmeyende göreli yol; entity UUID; olay id |
| `title` | Kaynağın okunabilir başlığı |
| `locator` | `entity_id`, `event_id`, `forkos_id`, `relative_path`, `heading`, `line_start`, `line_end` |
| `excerpt` | Sınırlı, deterministik snippet |
| `occurred_at` / `updated_at` | Kanonik zaman damgaları (varsa) |
| `relation_path` | Çekirdeğe nasıl bağlandığı (hop listesi) |
| `retrieval_reason` | Neden seçildi (≤ 240 karakter) |
| `truncated` | Snippet kısaltıldı mı |

**Yasak alanlar** (sözleşmeye giremez): `confidence`, `probability`,
`truth_score`, `certainty`, `answer`, `summary_answer`, `conclusion`,
`recommendation`. forkOS'un kalibre edilmiş bir epistemik modeli yoktur; sahte
kesinlik üretilmez. Leksikal puan yalnızca **sıralama** içindir ve çıktıya
yazılmaz; gerekçe gözlemlenebilir bir olgu söyler:

```text
"query tokens matched (exact title, body)"     ✅
"confidence=0.92"                              ❌
```

### 3.3 `EvidencePathHop`

```text
kind      : entity_link | knowledge_pointer | wikilink | backlink
from_ref  : "entity:<uuid>" | "vault:<göreli yol>"
relation  : KANONİK makine ilişkisi (ör. belongs_to, knowledge_note, wikilink)
direction : incoming | outgoing | null
to_ref    : "entity:<uuid>" | "vault:<göreli yol>"
```

`relation` daima makine ilişkisidir; yerelleşmiş etiket tek başına kimlik
olarak kullanılmaz.

`direction` **gezinmeye** göredir ve yalnızca `entity_link` hop'larında bulunur:

```text
DB satırı : Todo --belongs_to--> Project
çekirdek  : Project
gezinme   : Project → Todo
hop       : relation=belongs_to, direction=incoming
```

```text
A --related--> B     A → B ⇒ outgoing        B → A ⇒ incoming
```

Kural modelde dayatılır: `entity_link` yönsüz üretilemez, diğer türler yön
taşıyamaz. İlişki adı ASLA ters çevrilmez; `belongs_to_inverse`, `contains`,
`owned_by` gibi uydurma ilişkiler üretilmez.

`relation_path` **tam**tır: açık çekirdekte başlar, kaynakta biter. Komşu
üzerinden gelen bir kasa kanıtı entity önekini kaybetmez:

```text
[entity_link(belongs_to, incoming), knowledge_pointer, wikilink]
```

### 3.4 `RetrievalTraceStep`

```text
stage       : entity_resolution | graph | events | managed_knowledge
              | wikilinks | backlinks | vault_lexical | budget
description : olgusal tek cümle
considered  : bu aşamada görülen aday
accepted    : kanıta dönüşen aday
truncated   : bu aşama sert bir tavana takıldı mı
```

Her istek **aynı 8 aşamayı, aynı sırada** döndürür; kapsam yalnızca içerikleri
değiştirir (`scope=knowledge` operasyonel aşamalar için "skipped" adımı taşır).
Böylece iki farklı çağrının izleri karşılaştırılabilir kalır.

Sayaç semantiği aşamaya göre kesindir:

```text
graph     considered = ziyaret edilen çekirdek dışı düğüm
          accepted   = kanıta dönüşen komşu
events    considered = DB tarama penceresinden SONRA dikkate alınan uygun satır
          accepted   = genel kanıt bütçesinden ÖNCE kanıta dönüşen olay
budget    considered = oluşturulan aday
          accepted   = pakete giren öğe
```

Olay kanalında `truncated`, iki tavandan **herhangi biri** dolduğunda `true`
olur (tarama penceresi veya kanıt tavanı) ve pakete yayılır.

---

## 4. Örnek çıktı (gerçek bir çağrıdan kısaltılmıştır)

İstek: `forkos_evidence(query="Rust mimari kararı", entity_id=<forkjob>, scope="all")`

```json
{
  "query": "Rust mimari kararı",
  "entity_seed": "3ce971dd-...",
  "sources_used": ["forkos", "f0rknbrain"],
  "truncated": false,
  "resolved_entities": [
    {"type": "project", "resolution": "explicit_seed", "expanded": true}
  ],
  "evidence": [
    {
      "evidence_id": "entity:3ce971dd-...",
      "source_type": "entity",
      "excerpt": "type: project\ntitle: forkjob\nstatus: active\nnext_action: \"Mimariyi yaz\"\nstack: [Rust, PostgreSQL]",
      "retrieval_reason": "explicit entity seed; current operational state",
      "relation_path": []
    },
    {
      "evidence_id": "vault:3ce971dd-...#Teknoloji Kararı",
      "source_type": "vault",
      "locator": {
        "forkos_id": "3ce971dd-...",
        "relative_path": "20 Projects/forkjob.md",
        "heading": "Teknoloji Kararı",
        "line_start": 10, "line_end": 14
      },
      "relation_path": [
        {"kind": "knowledge_pointer", "from_ref": "entity:3ce971dd-...",
         "relation": "knowledge_note", "direction": null,
         "to_ref": "vault:20 Projects/forkjob.md"}
      ],
      "retrieval_reason": "managed knowledge note of the explicit entity seed; query tokens matched (heading, body)"
    },
    {
      "evidence_id": "event:2",
      "source_type": "event",
      "locator": {"event_id": 2, "entity_id": "3ce971dd-..."},
      "occurred_at": "2026-09-10T12:00:00+00:00",
      "excerpt": "project.updated · entity=\"forkjob\"\npayload={\"stack\": [\"Rust\"]}",
      "retrieval_reason": "event on the explicit entity seed; query terms matched the event"
    },
    {
      "evidence_id": "vault:30 Knowledge/Rust.md#Rust",
      "source_type": "vault",
      "locator": {"relative_path": "30 Knowledge/Rust.md", "heading": "Rust", "line_start": 1, "line_end": 3},
      "relation_path": [
        {"kind": "knowledge_pointer", "relation": "knowledge_note", "direction": null},
        {"kind": "wikilink", "relation": "wikilink", "direction": null}
      ],
      "retrieval_reason": "direct wikilink from '20 Projects/forkjob.md'; query tokens matched (title token, body)"
    }
  ],
  "retrieval_trace": [
    {"stage": "entity_resolution", "considered": 1, "accepted": 1, "truncated": false},
    {"stage": "graph", "considered": 1, "accepted": 1, "truncated": false},
    {"stage": "events", "considered": 1, "accepted": 1, "truncated": false},
    {"stage": "managed_knowledge", "considered": 1, "accepted": 1, "truncated": false},
    {"stage": "wikilinks", "considered": 1, "accepted": 1, "truncated": false},
    {"stage": "backlinks", "considered": 0, "accepted": 0, "truncated": false},
    {"stage": "vault_lexical", "considered": 2, "accepted": 2, "truncated": false},
    {"stage": "budget", "considered": 7, "accepted": 5, "truncated": false}
  ],
  "omitted_total": 2,
  "warnings": [],
  "recovery_hint": null
}
```

`omitted_total=2`: aynı iki nota (proje notu ve wikilink hedefi) leksikal kanaldan
da ulaşıldı; tekilleştirme en yüksek öncelikli kopyayı tuttu.

---

## 5. Uyarılar

| Uyarı | Anlam |
|---|---|
| `VAULT_UNAVAILABLE` | Kasa yapılandırılmamış/okunamıyor. `scope=all`'da operasyonel kanıt korunur; `scope=knowledge`'da hata döner. |
| `VAULT_CONFLICT` | Bir `forkos_id`'yi birden fazla dosya sahipleniyor; hedef tahmin edilmedi, not kimlik iddiası olmadan yol üzerinden sunuldu. |
| `Vault wikilink ambiguity: ...` | Çıplak bağ birden fazla güvenli nota çözüldü; hiçbiri izlenmedi (sınırlı örnek yolla birlikte). |
| `Vault scan stopped at the 500-file cap ...` | Tarama tavanına takıldı; sonuç eksik olabilir. |
| `N note(s) exceeded 256 KiB and were only partially scanned.` | Büyük dosya kısmen tarandı. |
| `N note(s) could not be read and were skipped.` | Okunamayan dosya atlandı (çökme yok, sessiz tam-kapsam iddiası yok). |

Uyarılar en fazla 10 tanedir ve her biri 300 karakterle sınırlıdır; tek tek
belirsiz bağlar için uyarı üretilmez (toplanır).

---

## 6. Hata kodları

```text
INVALID_QUERY                     boş/whitespace sorgu
QUERY_TOO_SHORT                   < 2 karakter
QUERY_TOO_LONG                    > 200 karakter
INVALID_UUID                      entity_id UUID değil
ENTITY_NOT_FOUND                  entity_id yok
FROZEN_ENTITY_UNAVAILABLE         legacy note/note_folder/note_attachment
INVALID_SCOPE                     bilinmeyen scope
INVALID_MAX_DEPTH                 max_depth 0-2 aralığının dışında
INVALID_LIMIT                     limit 1-15 aralığının dışında
INVALID_TIME_RANGE                bozuk / saat dilimsiz / since > until
TIME_FILTER_REQUIRES_ENTITY_SEED  zaman filtresi çekirdeksiz kullanıldı
VAULT_UNAVAILABLE                 scope=knowledge ve kasa yok
EVIDENCE_UNAVAILABLE              beklenmeyen iç hata (yığın izi sızdırılmaz)
```

Hata mesajları ham yığın izi, mutlak yol veya orm nesnesi taşımaz.

**Belirsizlik genellikle hata DEĞİLDİR:** sorgu-only modda birden fazla entity
adayı normaldir; paket adayları ve ipucunu döner. Ölümcül belirsizlik yalnızca
tek bir kaynağın kesin çözülmesi gereken yerlerde (ör. çıplak wikilink hedefi)
geçerlidir — o yol atlanır ve uyarı verilir.

---

## 7. Yüzey doğrulaması

```text
H0 = 8    H1 = 11    H2 = 5    H3 = 1    TOPLAM = 25
```

Kanıt dosyaları: `test_agent_h3_contract.py` (yüzey + anotasyon + şema + hata
kodları), `test_agent_h3_evidence.py` (davranış), `test_agent_h3_transport.py`
(gerçek `/mcp` + değişmezlik).
