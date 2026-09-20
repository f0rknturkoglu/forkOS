# forkOS × Hermes — H1: Güvenli Eylemler ve Onay Modeli

> **Tek cümle:** H0 Hermes'e *gözlerini* verdi; H1 ona **kontrollü eller** verir —
> yalnızca kullanıcının onayladığı, sınırlı, silme içermeyen semantik eylemleri.

H1 otonom çalışma DEĞİLDİR. H1:

> **Mevcut forkOS ve f0rknbrain yetenekleri üzerinde, insan onaylı semantik yazma yüzeyidir.**

Arka plan yürütme yok. Proaktif ajan yok. Hermes'in kontrol ettiği zamanlayıcı yok.
Yerel LLM yok. Ajan hafızası yok. Faz 4 temizliği yok.

---

## 1. Onay modeli — iki ayrı kapı

H1'in merkezî ayrımı şudur:

```text
Hermes onayı  = İNSAN kapısı     → "bu eylem kullanıcı tarafından istendi mi?"
forkOS doğrulaması = YÜRÜTME güvenliği → "bu eylem domain kurallarına uygun mu?"
```

Bu iki kapı birbirinin yerine GEÇMEZ:

- **Onay, domain kurallarını atlatmaz.** Onaylanmış ama geçersiz bir eylem
  yine başarısız olur (ör. `discovered → interview` keşif akışında geçersizdir).
- **Domain geçerliliği onayı atlatmaz.** Kurallara uygun bir eylem bile
  kullanıcı onayı olmadan çalışmaz.

### Onay nerede yaşar?

forkOS **kendi onay sistemini KURMAZ**. H1'de şunların hiçbiri yoktur:

```text
pending_action tablosu        onay kuyruğu
approval_token                onay kodu
ajan onay modalı              onay polling worker'ı
```

Kanunî onay katmanı **MCP istemcisidir** (Hermes). Bunun çalışması için sunucu
tarafının tek sorumluluğu, yazma araçlarını **doğru işaretlemektir**:

```text
readOnlyHint = false   →  istemci bunu "onay gerektiren yazma" olarak görür
```

`trust: untrusted` yapılandırılmış bir Hermes MCP sunucusu, bu bayrağı taşıyan
her çağrı için kullanıcıdan onay ister. Kurulum: `h1-setup.md`.

> **Dürüst sınır:** forkOS, kullanıcının gerçekten onay düğmesine bastığını
> KANITLAYAMAZ. Sunucu sözleşmesi "yazma araçları doğru işaretli"; istemci
> sözleşmesi "untrusted sunucu onay ister". Kanıtlanan ve test edilen kısım
> birincisidir.

### Neden MCP elicitation kullanılmıyor?

H1, her mutasyon için ikinci bir kullanıcı istemi (`ctx.elicit`) AÇMAZ. Bu,
Hermes'in zaten var olan onay yüzeyini ikizler ve iki farklı onay deneyimi
yaratırdı. H1 sıradan MCP yazma araçları + doğru anotasyonlar kullanır.

---

## 2. Yasak tasarımlar

H1 bilinçli olarak dar tutuldu. Aşağıdakiler **yüzeyde yoktur** ve testle de
yokluğu doğrulanır:

| Yasak | Neden |
|---|---|
| `call_api(method, path, body)` | REST yüzeyinin tamamını ajan yüzeyine açar |
| `execute_sql(...)` | Domain kurallarını tamamen atlar |
| `update_entity(type, fields)` | Genel mutasyon; insan anlamlı eylem değil |
| `write_file(path, content)` | Kullanıcının kendi bilgi dosyalarını yazılabilir kılar |
| silme araçları (todo/proje/yer imi/not) | Yıkıcı; geri dönüşü yok |
| toplu işlem | Onayın anlamını bozar; "yüzlerce satır" onaylanamaz |
| credential/token/OAuth yazmaları | Sır yönetimi ajan yüzeyine ait değil |
| kaynak yenileme / scrape / enrich | H1 yereldir; ağ eylemi yapmaz |
| zamanlanmış/otomatik yürütme | H1 otonom değildir |

---

## 3. Yürütme mimarisi

```text
        Hermes
          │  MCP (Streamable HTTP, /mcp, 127.0.0.1)
          ▼
   forkOS Brain Interface
          │
          ├── 8 okuma aracı  → context.py / knowledge.py
          │
          └── 11 yazma aracı → actions.py
                                 │
                    ┌────────────┼────────────┬──────────────┐
                    ▼            ▼            ▼              ▼
              todo.service  project.service  opportunity   bookmark.service
                                            lifecycle/     obsidian.service
                                            application
                    │            │            │              │
                    ▼            ▼            ▼              ▼
                PostgreSQL   PostgreSQL    PostgreSQL    Vault (dosya sistemi)
```

Yazma adaptörleri **ikinci bir domain katmanı DEĞİLDİR**. Sıra her zaman:

```text
MCP girdisini doğrula (write_models)
→ hedefi/mevcut durumu çöz
→ H1'e özgü güvenlik önkoşulunu uygula (tazelik / belirsizlik)
→ canonical domain servisini çağır
→ sınırlı ActionReceipt döndür
```

Yaşam döngüsü kuralları, ilişki yönü, tekrar (recurrence) davranışı, olay
semantiği ve doğrulama **canonical servislerde kalır**; adaptör bunları
kopyalamaz.

---

## 4. Tazelik ve yarış koşulları

Onay bir zaman aralığı yaratır:

```text
Hermes durumu okur → kullanıcıya anlatır → kullanıcı onaylar → yazma çalışır
                          ↑ bu arada durum değişebilir
```

H1 bu aralıkta **fail-closed** davranır:

| Koruma | Kullanıldığı yer | Hata kodu |
|---|---|---|
| `expected_updated_at` | görev, proje, yer imi güncellemesi | `STALE_ACTION` |
| `expected_status` | fırsat ve başvuru geçişleri | `STALE_ACTION` |
| Vault `mtime` | yönetilen bilgi notu ekleme | `VAULT_STALE` |

Bayat bir karar **sessizce yeni duruma uygulanmaz**; eylem durur ve makbuz
güncel durumu bildirir.

Ayrıca:

- **Belirsiz plan:** bir görev için birden fazla gelecek plan kaydı varsa
  hangisinin taşınacağı belirsizdir → `AMBIGUOUS_PLAN` (tahmin edilmez).
- **Belirsiz başlık:** `brain_save_to_entity` tam eşleşen tek başlık arar;
  0 eşleşme `HEADING_NOT_FOUND`, >1 eşleşme `AMBIGUOUS_HEADING`.
- **Vault çakışması:** aynı `forkos_id` iki dosyada varsa yazma reddedilir
  (`VAULT_CONFLICT`); çakışma çözülene kadar hiçbir şey yazılmaz.

---

## 4b. Verilmeyen alan ≠ null verilen alan

MCP çağrısında bir alanı **hiç göndermemek** ile **açıkça `null` göndermek**
farklı anlamlara gelir ve H1 bu ayrımı korur:

| İstek | Anlamı |
|---|---|
| `{"todo_id": "...", "priority": 1}` | yalnızca `priority` değişir; diğer alanlar KORUNUR |
| `{"todo_id": "...", "description": null}` | `description` TEMİZLENİR |
| `{"project_id": "..."}` | istenen bir mutasyon yok → `status = noop` |
| `{"project_id": "...", "next_action": null}` | `next_action` TEMİZLENİR |

Bu ayrım sunucuda **ham istek argümanlarından** okunur; şemada sahte bir
"gönderilmedi" işareti (`"__UNSET__"` vb.) YOKTUR ve alan düzeyi kısıtlar
(`maxLength`, `enum`, sayı aralıkları) korunur.

> `recur` alanında canonical domain sözleşmesi geçerlidir: boş metin (`""`)
> rutini KALDIRIR, alanı hiç göndermemek rutini korur.

## 5. Tekrar deneme politikası

Yazma çağrıları **kör otomatik tekrar denemeye DAYANMAZ**. Sonucu belirsiz
bir yazmadan sonra:

```text
1. H0 ile güncel durumu OKU
2. mutasyonun gerçekleşip gerçekleşmediğini belirle
3. yalnızca gerekiyorsa tekrar dene
```

Özellikle `brain_save_to_entity` **idempotent değildir** (ekleme yapar): sonuç
belirsizse önce `brain_read` ile gövdeyi oku, sonra karar ver. H1 bunu gizli
metin tekilleştirme sezgileriyle "çözmez".

Okuma araçları normal güvenli tekrar davranışını korur.

---

## 6. Makbuz (ActionReceipt)

Her başarılı yazma sınırlı bir makbuz döner:

```json
{
  "request_id": "…",
  "tool": "forkos_todo_complete",
  "status": "executed",
  "target_type": "todo",
  "target_id": "…",
  "summary": "Completed: H1 sözleşme incelemesi",
  "changed_fields": ["status", "completed_at"],
  "before": { "status": "doing", "recur": "weekly" },
  "after": { "status": "done", "completed_at": "…", "next_occurrence_id": "…" },
  "warnings": ["Rutin görev: forkOS tekrar kurallarına göre bir sonraki oluşum oluşturuldu."]
}
```

Kurallar:

- `status` yalnızca `executed` veya `noop` olabilir.
- Makbuz **kanıttır, düzyazı değildir**: gerçek sonuç durumu taşır, LLM
  açıklaması içermez.
- Gövde/metin İÇERİĞİ kopyalanmaz: bilgi yakalamada yalnız `relative_path`,
  `forkos_id`, `title` döner; büyük metinler karakter sayısıyla özetlenir.
- Ham ORM nesnesi, tam veritabanı satırı, credential, mutlak dosya yolu
  DÖNMEZ.
- `request_id` yalnızca **tanılama korelasyonudur**; yetkilendirme değildir ve
  yeni bir onay/oturum alt sistemi kurmak için kullanılmaz.

---

## 7. İdempotans

`idempotentHint` araç başına doğrudur ve **abartılmaz**:

| Araç | idempotent | Gerekçe |
|---|---|---|
| `forkos_todo_create` | `false` | her çağrı yeni görev üretir |
| `forkos_todo_update` | `true` | aynı değer yeniden istenirse servis çağrılmaz |
| `forkos_todo_complete` | `true` | zaten `done` ise `noop`, ek oluşum yok |
| `forkos_todo_plan` | `true` | tek uygun slot güncellenir |
| `forkos_project_update` | `true` | aynı `next_action` ise servis çağrılmaz |
| `forkos_opportunity_transition` | `false` | geçiş kaydı/olayı üretir |
| `forkos_application_transition` | `false` | geçiş geçmişi (append-only) üretir |
| `forkos_bookmark_capture` | `false` | yeni kayıt üretebilir |
| `forkos_bookmark_update` | `true` | aynı değer ise servis çağrılmaz |
| `brain_capture` | `false` | her çağrı yeni dosya üretir |
| `brain_save_to_entity` | `false` | metin EKLER; ikinci çağrı ikinci ek olur |

İdempotent araçlarda istenen değer zaten geçerliyse canonical servis hiç
çağrılmaz: tekrar denemeler gereksiz olay/`touch` gürültüsü üretmez ve
`status = noop` döner.

---

## 8. Yerellik (local-only)

Her H1 aracı **dış ağ çağrısı YAPMAZ**. Açıklamalar bunu açıkça yazar ve
testler bunu zorlar (httpx ve readability çağrıları test hatasına dönüşür).

Tetiklenmeyenler:

```text
GitHub HTTP      iş kaynağı ingestion   LinkedIn
RSS fetch        Google API'leri        sayfa zenginleştirme (enrich)
OpenAI / Nous / OpenRouter              embedding API'leri
```

H1 yalnızca **hâlihazırda yerel olan** durumu değiştirir. Yer imi kaydetmek
sayfayı İNDİRMEZ; kaynak notu oluşturmak makale gövdesini KOPYALAMAZ.

---

## 9. Bilgi sahipliği (Faz 3 sınırı korunur)

`brain_capture` ve `brain_save_to_entity` **doğrudan Obsidian Vault'a** yazar:

```text
forkOS veritabanı: entity / note / note_folder / note_attachment / link satırı OLUŞMAZ
Vault:             yönetilen Markdown dosyası oluşturulur veya eklenir
legacy Notlar:     SIFIR yazma (dondurulmuş arşiv)
```

Kurallar:

- `brain_save_to_entity` hedefi yalnızca **`forkos_id`**'dir. `relative_path`
  şemada YOKTUR: kullanıcının kendi Obsidian notları okunabilir ama
  YAZILAMAZ.
- Yazma **ekleme**dir; tam gövde değiştirme H1'de açılmaz.
- Bilinmeyen kullanıcı frontmatter'ı ve gövdesi korunur; Markdown yeniden
  biçimlendirilmez.
- Vault yazmaları `integrations/obsidian/service.py` üzerinden geçer; agent
  paketinde doğrudan dosya yazımı YOKTUR.
- Bilgi notunun gövdesi veritabanı olay yüklerine KOPYALANMAZ.

---

## 9b. Bilgi yazmalarında başarısızlık atomikliği

Yönetilen nota ekleme (`brain_save_to_entity`) **yaratıcı adımdan ÖNCE**
doğrular. Hedef not yoksa ve çağıran bir başlık verdiyse istek
`HEADING_NOT_FOUND` ile reddedilir; **yetim bir yönetilen dosya bırakılmaz**.

```text
not yok + başlık verildi        → HEADING_NOT_FOUND, Vault DEĞİŞMEZ
not yok + başlık verilmedi      → canonical `ensure` ile oluştur + ekle (tek eylem)
not var + geçersiz başlık       → HEADING_NOT_FOUND, gövde DEĞİŞMEZ
```

Herhangi bir başarısızlıkta hem veritabanı içerik parmak izi hem Vault dosya
ağacı özeti **aynı** kalır. Geri alma için "dosyayı sil" gibi bir yan etki
kullanılmaz; doğrulama yan etkiden önce yapılır.

## 9c. Yol gizliliği

Ajan çıktısı ve MCP yanıtları **mutlak dosya yolu taşımaz**:

```text
✓ "Obsidian Vault directory does not exist."
✓ "Obsidian Vault is not configured."
✓ "Multiple managed notes share this identity."
✗ "/Users/<kullanıcı>/.../f0rkn-vault"
✗ HOME, kullanıcı adı, sürücü harfi içeren tam yollar
```

Bilgi yazma makbuzları yalnızca **göreli** yol (`relative_path`) döndürür.
Tanılama metinleri ayrıca bir redaksiyon ağından geçer: yol gövdesi boşluk
içerebilir, bu yüzden kesme noktaları tırnak/parantez/virgül/satır sonudur;
göreli yollar (`20 Projects/x.md`) yanlışlıkla redakte EDİLMEZ.

## 10. Kapsam dışı (H1'de yok)

```text
silme (todo/proje/milestone/yer imi/not/Vault dosyası)
credential, GitHub token, OAuth yazmaları
ayar sıfırlama (settings reset), yedek geri yükleme
kaynak yenileme, iş ilanı ingestion, RSS refresh, enrich, uzak GitHub
genel içe aktarma, toplu yıkıcı mutasyon, keyfî Vault yeniden yazımı
Pomodoro başlat/durdur        (fiziksel çalışma durumu; ayrı UX gerekir)
Takvim yazmaları              (dış senkron riski; planlama ihtiyacı todo_plan ile karşılanır)
Öğrenme durumu / SRS / kart notlama (özel domain semantiği; sonraki fazlar)
H2 sıcak hafıza, yerel LLM, RAG/vektör, Faz 4 şema temizliği
```

---

## 11. Hermes davranış rehberi

Bir mutasyondan ÖNCE Hermes şunu yapmalıdır:

```text
1. hedefi H0 ile ÇÖZ            (forkos_search → forkos_entity_context)
2. güncel ilgili durumu İNCELE
3. planlanan mutasyonu kullanıcıya AÇIKLA
4. TEK bir semantik yazma aracı çağır
5. gerçek makbuzu RAPORLA
```

- UUID **tahmin edilmez**; önce arama ile bulunur.
- Kullanıcı açıkça çok eylemli bir iş istemediyse yazmalar sessizce
  ZİNCİRLENMEZ. `untrusted` modda her yazma ayrı onay ister.
- Bir yazmadan sonra Hermes kendiliğinden ek mutasyon YAPMAZ (proje
  `next_action` güncellemez, günlük not yazmaz, başka görevi ertelemez).
- **Otomatik hafıza yazımı yoktur**: `brain_capture` yalnızca kullanıcının
  niyeti bilgi kaydetmeyi içerdiğinde çağrılır.

### Örnek akış — görev tamamlama

```text
Kullanıcı: "Şu H0 audit işini tamamla."

Hermes: forkos_search("H0 audit")
        → forkos_entity_context(todo_id)
        → forkos_todo_complete(todo_id)

Makbuz: status = executed | noop
        after.next_occurrence_id varsa rutin yeni oluşum üretmiştir
```

### Örnek akış — bilgi yakalama

```text
Kullanıcı: "Bunu not olarak kaydet: Hermes yazma araçları semantik kalmalı."

Hermes: brain_capture(...)
Sonuç:  00 Inbox/… (forkOS'ta not satırı YOK)
```

### Yasak akış örneği

```text
Kullanıcı: "Tüm eski fırsatları sil."

Sonuç: H1'de bunu yapacak araç YOKTUR; Hermes başka bir genel uçtan
       türetme yapmaz. Yetenek yokluğu tasarımın parçasıdır.
```

---

## 12. İlgili belgeler

- `h1-tool-contract.md` — 19 aracın tam sözleşmesi (girdi, önkoşul, yan etki,
  idempotans, hatalar, makbuz).
- `h1-setup.md` — Hermes yapılandırması ve araç allowlist profilleri.
- `h0-brain-interface.md` — okuma yüzeyinin temeli ve değişmezlik kanıtı.
- `roadmap.md` — H-serisi ve sonraki fazlar.
