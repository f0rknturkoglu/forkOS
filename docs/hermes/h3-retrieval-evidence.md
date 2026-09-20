# forkOS × Hermes — H3 Kanıt Getirme (Retrieval & Evidence)

> **H3'ün amacı soru CEVAPLAMAK değildir.** Bir soru ya da iddia verildiğinde
> *incelenebilir kanıt* üretmektir: forkOS ne biliyor, bu bilgi nereden geldi,
> ilgili kaynaklara nasıl ulaşıldı ve hangi sınırlar devreye girdi.

```text
Kullanıcı sorusu
      │
      ▼
    Hermes
      │  MCP
      ▼
forkos_evidence(...)
      │
      ├── Entity / Link grafiği
      ├── append-only Event geçmişi
      ├── yönetilen Vault işaretçileri
      ├── Vault leksikal kanıtı
      └── sınırlı wikilink/backlink gezinmesi
      │
      ▼
 EvidenceBundle
      │
      ▼
 Hermes muhakemesi → cevap
```

**forkOS getirir. Hermes akıl yürütür.**

---

## 1. Değişmez ilkeler

```text
H3 hiçbir doğruluğa SAHİP DEĞİLDİR.
```

Var olan kanonik kaynaklardan **türetilmiş, sınırlı ve kökenli** bir kanıt
görünümü kurar. Yeni bir bilgi sahibi yaratmaz.

| Kural | Sonuç |
|---|---|
| **Salt-okunur** | Hiçbir tabloya yazmaz, hiçbir dosyayı değiştirmez, hiçbir olay (Event) üretmez. |
| **Yanıt üretmez** | Pakette `answer`, `conclusion`, `recommendation` gibi alan YOKTUR. |
| **Model içermez** | Gömme (embedding), vektör veritabanı, LLM, harici API çağrısı YOKTUR. |
| **Kalıcılık yok** | İz, paket, sorgu geçmişi, indeks saklanmaz; her istek kendi geçici görünümünü kurar ve atar. |
| **Tek sahiplik** | Operasyonel gerçek forkOS'ta, kalıcı bilgi f0rknbrain'de kalır. H3 ikisini de KOPYALAMAZ. |

### 1.1 Getirme felsefesi

```text
YAPI ÖNCE  →  HAM KAYNAK / KÖKEN  →  LEKSİKAL  →  (anlamsal: H3'te YOK)
```

forkOS zaten deterministik yapıya sahiptir: `Entity`, `Link`, `Event`, yönetilen
kasa işaretçileri, Markdown ve `[[wikilink]]`. Bu yüzden H3 hiçbir zaman bir
modele "ilişkileri yeniden keşfet" demez; **var olan ilişkiyi okur ve kökeniyle
gösterir**.

Anlamsal arama (embedding/vektör) H3'te yoktur ve bu bir eksiklik değil, bilinçli
bir sıralamadır: gerçek bir başarısızlık gözlemlenmeden eklenmez.

---

## 2. Kanıt kaynakları

Tam olarak ÜÇ kaynak tipi vardır:

| `source_type` | Kaynak | Örnek |
|---|---|---|
| `entity` | Operasyonel nesnenin GÜNCEL durumu | `status=active`, `stack=[Rust, PostgreSQL]` |
| `event` | Append-only geçmiş | `todo.completed` + sanitize edilmiş payload |
| `vault` | Markdown bilgi | `20 Projects/forkjob.md` → `## Teknoloji Kararı` |

### 2.1 Sıcak hafıza kanıt DEĞİLDİR

`90 Agent/Memory` ağacı kanıt taramasının **dışındadır**. Sıcak hafıza
kişiselleştirme bağlamıdır ("kullanıcı kısa cevap sever"), kanıt değildir
("Rust neden seçildi" sorusunun dayanağı değildir). Ayrı araçla sunulur:
`hot_memory_context`.

Bu ayrım kalıcıdır; `source_type` listesine `hot_memory` eklenmeyecektir.

### 2.2 Güncel gerçek ile tarih AYRI kalır

```text
entity kanıtı : "status=active"          (şimdi)
event kanıtı  : "project.paused"          (geçmiş)
vault kanıtı  : "Prototype will use Python." (yazıldığı andaki bilgi)
```

H3 bu üçünü **birlikte** döner ve hiçbirini diğerine göre sessizce silmez ya da
"güncel olan kazanır" diye düzeltmez. Çelişki varsa çelişki olarak görünür;
yorum Hermes'e aittir.

Kanonik zaman semantiği:

```text
entity güncel durum  → updated_at
olay geçmişi         → occurred_at
kasa kanıtı          → yalnızca açık frontmatter damgası (forkos_updated_at)
```

Dosya sistemi `mtime`'ı bilgi zamanı SAYILMAZ.

---

## 3. Kanallar ve öncelik

Küçük sayı önce gelir (doğrudan kanıt, zayıf yakınlığın önündedir):

| Katman | Kanal | Örnek gerekçe |
|---:|---|---|
| 10 | Çekirdek entity'nin güncel durumu | `explicit entity seed; current operational state` |
| 20 | Çekirdeğin yönetilen kasa notu | `managed knowledge note of the explicit entity seed` |
| 30 | Çekirdeğe bağlı olaylar | `event on the explicit entity seed` |
| 40 | Doğrudan operasyonel komşular | `depth-1 related entity via 'belongs_to' link` |
| 50 | Komşuların yönetilen notları | `managed knowledge note of a depth-1 related entity` |
| 60 | Komşulara bağlı olaylar | `event on a depth-1 related entity ("...")` |
| 70 | Wikilink / backlink kanıtı | `direct wikilink from '20 Projects/forkjob.md'` |
| 80 | Genel kasa leksikal yedeği | `global Vault lexical fallback; query tokens matched (body)` |
| 90 | Sorgu-only entity adayları | `lexical operational candidate; not graph-expanded` |

Bu sıra **kanıt-seçimi** sırasıdır; kaynakların doğruluk sıralaması DEĞİLDİR.
Kasa, veritabanından "daha az doğru" değildir: ikisi farklı zamanları ve farklı
anlamları anlatır (bkz. §2.2).

### 3.1 Kanallar

```text
açık çekirdek varsa        : yapısal grafik + olaylar + yönetilen not + kasa hopu + leksikal yedek
çekirdek yoksa (sorgu-only): leksikal operasyonel adaylar + leksikal kasa kanıtı
```

- **Grafik:** deterministik BFS; ziyaret kümesi + döngü koruması + derinlik ve
  düğüm tavanı. Özyinelemeli sınırsız DFS yoktur. Komşular her seviyede
  `(ilişki, yön, tip, başlık, id)` ile sıralanır.
- **Olaylar:** YALNIZCA yapısal bir çapaya (çekirdek + gezinilen düğümler)
  bağlı olarak okunur; global olay metin araması yoktur. Sorgu terimiyle
  eşleşen olaylar önce, sonra en yeni olanlar gelir.
- **Çakışan kimlik:** bir `forkos_id`'yi birden fazla dosya sahipleniyorsa hedef
  TAHMİN EDİLMEZ; `VAULT_CONFLICT` uyarısı verilir ve o kaynak kimlik iddiası
  olmadan (yol üzerinden) sunulur.
- **Wikilink:** `[[Hedef]]`, `[[Hedef|Takma ad]]`, `[[Hedef#Başlık]]`. Kod
  blokları ve satır içi kod içindeki bağlar kenar SAYILMAZ; `![[ek]]` atlanır.
  Çıplak hedef tek adaya çözülürse izlenir, birden fazla adaya çözülürse
  **belirsiz** kabul edilir ve atlanır; çözülemeyen bağ ölümcül değildir.
- **Backlink:** hedefe işaret eden notlar sınırlı taramada bulunur. Bağ tek
  başına kanıt değildir: not ancak sorgu terimleriyle de eşleşiyorsa kanıt olur.

---

## 4. Köken (provenance)

Her kanıt öğesi iki soruyu yanıtlar: **nerede** (`locator`) ve **nasıl bağlı**
(`relation_path`).

> **Değişmez kural:** `relation_path` DAİMA açık entity çekirdeğinde başlar ve
> kanıt öğesinin kaynağında biter. Yarısı gösterilen bir yol, yol değildir.

### 4.1 Link yönü korunur

`Link` modeli anlamsal yön taşır: `from_id --relation--> to_id`. Gezinme aynı
kenarı iki yönden birinde geçebilir; bu yüzden her `entity_link` hop'u hem
**kanonik ilişki adını** hem **geçiş yönünü** taşır:

```text
DB satırı     : Todo --belongs_to--> Project
çekirdek      : Project
gezinme       : Project → Todo
raporlanan    : relation=belongs_to   direction=incoming
```

İlişki adı **ters çevrilmez**: "Project belongs_to Todo" gibi uydurma bir
ontoloji üretilmez. `direction` gezinmeye göredir:

```text
A --related--> B     A → B  ⇒ direction=outgoing
                     B → A  ⇒ direction=incoming
```

`knowledge_pointer`, `wikilink` ve `backlink` hop'ları yön taşımaz
(`direction=null`): yönleri zaten `kind` ile anlatılır.

### 4.2 Yapısal köprü

```text
entity:forkjob
   │ belongs_to / incoming
   ▼
entity:todo-x
   │
   ▼
event:9341        relation_path = [entity_link(belongs_to, incoming)]
```

### 4.3 Bilgi köprüsü (komşudan geçen tam zincir)

```text
entity:forkjob
   │ belongs_to / incoming
   ▼
entity:todo-x
   │ knowledge_pointer (knowledge_note)
   ▼
vault:20 Projects/todo-x.md
   │ wikilink
   ▼
vault:30 Knowledge/Rust.md
```

```text
relation_path = [entity_link(belongs_to, incoming), knowledge_pointer, wikilink]
```

Backlink yönünde son hop `kind=backlink` olur ve **getirme yönünü** izler:

```text
Decision.md içinde [[Todo]] varsa ve getirme Todo.md'den başlıyorsa
gezinme : Todo.md → Decision.md
hop     : from_ref=vault:Todo.md   to_ref=vault:Decision.md
```

`from_ref` çapa notudur (bağlantıyı ALAN), `to_ref` bağlantıyı kuran nottur;
yön zaten `kind=backlink` ile anlatıldığı için `direction=null`. Entity öneki
yine korunur.

### 4.5 Süreklilik değişmezi

Çok hop'lu her yolda ardışık hop'lar bitişik olmak ZORUNDADIR:

```text
hop[i].to_ref == hop[i+1].from_ref
```

Ve kasa kanıtlarında son hop kaynağın kendisine işaret eder:

```text
relation_path[-1].to_ref == "vault:" + locator.relative_path
```

(Olay kanıtı bilinçli istisnadır: yolu sahibi entity'de biter, olayın kendisi
`locator.event_id` ile tanımlanır.)

### 4.4 Tek yapısal anlık görüntü

Bir istekte grafik gezinmesi **tam olarak bir kez** çalışır. Entity kanıtı,
olay kanıtı ve kasa köken yolları aynı sonuçtan türetilir; bu yüzden aynı
komşu, hangi kanaldan gelirse gelsin AYNI ilk hop'u taşır. İstek-yerlidir:
saklanmaz, önbelleğe alınmaz, süreçler arası paylaşılmaz.

### 4.3 Satır numaraları dürüsttür

`line_start` / `line_end` gerçek Markdown dosyasının **1 tabanlı fiziksel
satırlarıdır**. Kesilmemiş bir snippet için:

```text
excerpt == "\n".join(dosya_satirlari[line_start-1 : line_end])
```

Türetilemeyen bir konum için `None` döner; **yaklaşık değer uydurulmaz**.

### 4.4 Kanıt kimlikleri deterministiktir

```text
entity:<uuid>
event:<event_id>
vault:<forkos_id veya göreli yol>#<başlık | root>
```

Rastgele UUID yoktur. Aynı durum + aynı istek = aynı kimlikler.

---

## 5. Ölçek ve sınırlar

| Sınır | Değer | Nerede |
|---|---:|---|
| `query` | 2–200 karakter | şema + çalışma zamanı |
| `limit` | 1–15 (varsayılan 12) | şema + çalışma zamanı |
| `max_depth` | 0–2 (varsayılan 1) | şema + çalışma zamanı |
| Snippet / öğe | ≤ 1200 karakter | `evidence_models.py` |
| Toplam snippet bütçesi | ≤ 8000 karakter | `evidence_models.py` |
| En küçük anlamlı snippet | 120 karakter | `evidence_models.py` |
| Grafik düğümü | ≤ 25 | `evidence_models.py` |
| Olay kanıtı | ≤ 8 | `evidence_models.py` |
| Olay tarama penceresi | ≤ 120 satır (+1 nöbetçi) | `evidence_models.py` |
| Entity adayı (sorgu-only) | ≤ 5 | `evidence_models.py` |
| Uyarı | ≤ 10 (her biri ≤ 300 karakter) | `evidence_models.py` |
| Uyarıdaki belirsiz bağ örneği | ≤ 5 | `evidence_models.py` |
| Kasa tarama dosyası | ≤ 500 | `obsidian/evidence.py` |
| Tek dosya okuma | ≤ 256 KiB | `obsidian/evidence.py` |
| Çapalı kasa notu | ≤ 12 | `evidence_models.py` |
| Sorgu terimi | ≤ 12 (≥ 2 karakter) | `obsidian/evidence.py` |

Kasa tarama tavanı gerçek ölçeğe göre seçildi: mevcut kasa **28** Markdown
dosyası, en büyüğü ~29 KiB. 500 dosya / 256 KiB sınırları kaba kuvvet taramayı
sınırlar ama bugünkü kullanımın ~18× ve ~9× üstündedir.

### 5.1 Dürüstlük semantiği

```text
truncated=true   → bir kanal ya da öğe bütçeyle kesildi (öğe sınırı, karakter
                   bütçesi, düğüm tavanı, dosya tavanı, not tavanı, olay tavanı)
omitted_total    → YALNIZCA bilinen (sayılabilen) atlanan aday sayısı
warnings         → sınırlı, model-okunur; kanal kesmeleri gizlenmez
```

Evrensel toplam bilinmiyorsa (ör. tarama tavanda durdu) **uydurma sayı
verilmez**; bunun yerine `truncated` + uyarı + iz sayaçları konuşur.

Snippet sonradan global bütçe yüzünden kısaltılırsa kırpma **snippet'in
türetildiği başlık bölümünün dışına çıkamaz**: `heading` ve fiziksel satır
numaraları kırpılmış hâlde de doğru kalır. Tek bir kaynak satırı bütçeyi tek
başına aşıyorsa o satır önek olarak kırpılır (`line_start == line_end`).

İz (`retrieval_trace`) her istekte AYNI 8 aşamayı, aynı sırada taşır:

```text
entity_resolution → graph → events → managed_knowledge
                  → wikilinks → backlinks → vault_lexical → budget
```

İz, modelin düşünme zinciri DEĞİLDİR: hangi kanalın kaç aday gördüğünü ve kaçını
kabul ettiğini söyleyen olgusal bir kayıttır. Gizli akıl yürütme yazılmaz.

### 5.2 İyileştirme ipuçları

`recovery_hint` yalnızca EYLEME DÖNÜK olduğunda verilir:

```text
"Provide entity_id to traverse a specific operational entity."
"Use a more specific query, or provide an entity_id for structural traversal."
"Configure the Obsidian Vault (OBSIDIAN_VAULT_PATH) to include knowledge evidence."
```

---

## 6. Kapsam ayrımı

| `scope` | Ne okur | Ne OKUMAZ |
|---|---|---|
| `operational` | Entity, Link, Event, kanonik okuma modelleri | **Vault'a hiç dokunmaz** |
| `knowledge` | yönetilen not, Markdown, wikilink/backlink, leksikal | Entity/Event kanıtı ÜRETMEZ |
| `all` | ikisi birlikte; kasa erişilemezse operasyonel kanıt korunur | — |

`scope="operational"` için Vault'a dokunulmadığı test edilebilir: kasa okuma
fonksiyonları yamalanıp patlatıldığında bile istek başarılı olmalıdır
(`test_operational_scope_touches_no_vault`).

Bunu mümkün kılmak için H3, gömülü kasa işaretçisi taşıyan H0 bağlam
sarmalayıcılarını (`get_project_context` / `get_entity_context`) kullanmaz;
onların altındaki **kanonik alanları ve servisleri** (`project.service`,
`links`, `Entity`/`Event` modelleri) doğrudan okur. Aksi hâlde "operational" bir
çağrı sessizce Markdown okurdu.

---

## 7. Neler YOK (bilinçli)

```text
embedding            vektör veritabanı      pgvector        Neo4j / RDF
GraphRAG indeksi     topluluk tespiti       LLM varlık çıkarımı
LLM üretimi graf kenarı   otomatik iddia çıkarımı   semantik reranker
sorgu yeniden yazma modeli   yanıt üretimi   konuşma arşivi
yeni bilgi veritabanı   yeni tablo   migration   arka plan işçisi
başlangıçta tarama   kalıcı indeks   kalıcı iz   frontend   REST ucu
```

Bunlar ya ertelenmiştir ya reddedilmiştir. H3'ün borç aldığı ders tek cümledir:

> **Türetilmiş her ilişki ham kaynağa geri götürebilmelidir.**

---

## 8. Gizlilik ve ağ sınırı

- H3 **hiçbir dış model/API çağrısı yapmaz**: 0 HTTP, 0 DNS, 0 dış soket.
  Kanıt, internet araştırması değildir.
- Vault yolları H0 güvenlik politikasından geçer (`resolve_safe_vault_path`,
  `is_safe_knowledge_path`, sembolik bağ sınırı). Mutlak dosya yolu ajan
  yanıtına ve tanılamaya SIZMAZ.
- Olay payload'ları kanonik `sanitize_payload` ile maskelenir.
- Sıcak hafıza ağacı H3 taramasının dışındadır (§2.1).
- Normal Vault bilgisi H3'te H0 politikasıyla aynı muameleyi görür; H2'nin
  kimlik bilgisi politikası tüm kasaya YAYILMAZ (H3 kasayı yeniden
  sınıflandırmaz).

> **Dürüst ifade:** forkOS H3 hiçbir dış çağrı yapmaz. Ancak dönen
> `EvidenceBundle` içeriğini MCP istemcisi (Hermes) tüketir ve uzak bir model
> sağlayıcısı kullanılıyorsa bu içerik oraya gidebilir. "Uçtan uca yerel"
> iddiası ancak model çalıştırma yolu gerçekten yerelleştikten sonra
> yapılabilir.

---

## 9. Erteleme (H3.x)

Gözlemlenebilir bir ihtiyaç doğmadan eklenmeyecek olanlar:

- Çok adımlı kasa gezinmesi (H3 tek kasa hopu kullanır).
- Global olay metin araması (olaylar çapaya bağlıdır).
- Semantik/vektör arama.
- Kanıt çekmecesi (Evidence Drawer) ve görsel inceleme arayüzü.
- Zamansal geçersiz kılma (`valid_from` / `superseded_by`).

---

## 10. İlgili belgeler

- [H3 Araç Sözleşmesi](h3-tool-contract.md): `forkos_evidence` imzası, sınırlar,
  hata kodları ve örnek çıktı.
- [H3 Kurulum ve Doğrulama](h3-setup.md): testler, ölçümler, sorun giderme.
- [H0 Beyin Arayüzü](h0-brain-interface.md) · [H1 Güvenli Eylemler](h1-safe-actions.md)
  · [H2 Sıcak Hafıza](h2-hot-memory.md)
- [H-Serisi Yol Haritası](roadmap.md)
