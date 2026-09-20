# forkOS × Hermes — H5 Kaynak ve Konsolidasyon Politikası

Bu belge, H5'in **neyi bilgi saydığını**, neyi **aday** saydığını ve bir adayın
kalıcı hâle gelmesinin **hangi kapıdan** geçtiğini tanımlar. Politika
koddadır (`policy.py`, `consolidation.py`) ve bu belge onu açıklar.

---

## 1. Ayrımlar (politikanın tamamı bu tabloda)

```text
episodic          ≠ semantic            olay akışı bilgi DEĞİLDİR
aday              ≠ hafıza              aday kalıcı kayıt DEĞİLDİR
özet              ≠ kanıt               özet kanıt yerine geçmez
Hot Memory        ≠ tarihsel kanıt      kişiselleştirme bağlamı kanıt değildir
H4 çıktısı        ≠ doğruluk            model önerir, gerçeği söylemez
terfi             ≠ yazma               terfi yalnızca sonradan H1 onayıyla olur
yerine geçme      ≠ gerçekleşmiş        yalnızca ADAYDIR; hiçbir kayıt silinmez
özyinelemeli özet ≠ doğru               haftalık→aylık→yıllık zinciri KURULMAZ
```

Bu ayrımlar üslup değil, **mimari sınır**dır: ihlal eden bir tasarım H5'e
eklenmez.

---

## 2. Episodic ≠ semantic

```text
EPISODIC   Event akışı, günlük notlar, tamamlanan işler, bildirimler
           → "ne oldu" sorusunun cevabı
SEMANTIC   kalıcı bilgi: kararlar, dersler, kısıtlar, proje bilgisi, referanslar
           → "ne biliyorum" sorusunun cevabı
```

H5 episodic malzemeyi **okur** ve semantic adaylar **önerir**; aradaki geçiş
otomatik değildir. Günlük notta yazan bir cümle, kendiliğinden bilgi tabanına
girmez.

---

## 3. Aday ≠ hafıza, terfi ≠ yazma

```text
PromotionCandidate   kind · text · suggested_destination · support_refs
                     source_count · recurrence_count · status · warnings
```

- Aday **saklanmaz**: kimlik içerikten türetilir
  (`cand_<sha256 öneki>` = kind + normalize metin + sıralı destek ref'leri).
  Kalıcı aday tablosu YOKTUR.
- `status` iki değer alır: `candidate` ya da `already_present`. "Zaten var"
  yalnızca **tam (normalize) eşleşme** ile söylenir; bugün bu yalnızca
  `hot_memory` varış yerinde uygulanır ve `HOT_MEMORY_EXACT_DUPLICATE` uyarısı
  eklenir. `already_present` bir yazma değildir.
- Terfi **yalnızca** şu zincirle gerçekleşir:

```text
H5 aday üretir
      ↓  Hermes değerlendirir, kullanıcıya sunar
      ↓  kullanıcı ONAYLAR
H1 kanonik yazmayı yapar (todo / hot_memory / vault)
```

H5 bu zincirin hiçbir adımını kendi başına atmaz: ne Todo oluşturur, ne Sıcak
Hafıza yazar, ne Vault'a not ekler.

---

## 4. Özet ≠ kanıt, Hot Memory ≠ tarihsel kanıt, H4 ≠ doğruluk

| Kaynak | Ne için kullanılabilir | Ne için kullanılamaz |
|---|---|---|
| Kanonik durum (Entity/Event/Todo/Review) | Olgu ve sayım | — |
| Günlük not (`vault:` ref, satır aralığı) | Alıntı, kaynak kilidi | Doğrulanmış semantic bilgi sayılmaz |
| Sıcak Hafıza (`hot_memory:`) | Kişiselleştirme bağlamı | Tarihsel kanıt yerine geçmez |
| H3 kanıtı (`h3:`) | Bilgi sağlığı karşılaştırmasının dayanağı | Yorum üretmez |
| H4 çıktısı | **Aday** ifade | Doğruluk, gerçek, karar |
| Özet (haftalık/günlük özet) | Yön göstergesi | Kanıt yerine geçmez |

H4 çıktısı için tek güvence **kaynak kilidi**dir: `source_excerpt` sağlanan
pakette birebir bulunmalıdır. Bu, ifadenin *kaynakta geçtiğini* kanıtlar;
*doğru olduğunu* değil.

---

## 5. Yerine geçme yalnızca adaydır

Yeni bir aday ile mevcut bilgi karşılaştırıldığında H4 `classify` şu kapalı
etiket kümesini kullanır:

```text
consistent            ikisi birlikte geçerli olabilir
possibly_superseded   yeni ifade eskisinin yerine geçiyor OLABİLİR
possibly_conflicting  çelişiyor OLABİLİR
unrelated             farklı şeylerden söz ediyor
```

Sonuç `KnowledgeHealthCandidate` olur:

```text
issue          possibly_stale | possibly_superseded | possibly_conflicting
               | managed_source_conflict
reason         sınırlı, olgusal gerekçe (ör. "h4_classify:possibly_superseded")
support_refs   aday ref'leri + H3 kanıt ref'leri
warnings[]
```

**Otomatik geçersiz kılma, otomatik düzeltme, otomatik silme YOKTUR.** Eski
kayıt yerinde kalır; karar kullanıcınındır. Karşılaştırma yalnızca
`decision` / `project_knowledge` adayları için, en fazla **5 aday** ile ve
yalnızca H3'ten kanıt bulunabildiğinde yapılır.

---

## 6. Özyinelemeli özet doğruluğu YOK

H5 haftalık özeti aylık özete, aylığı yıllığa **çevirmez**:

```text
haftalık → aylık → yıllık  zinciri KURULMAZ
```

Sebep: özet üzerine kurulan özet, kanıtsız bir anlatı üretir. H5 her modda
kanonik kaynağa döner; "önceki özetin özeti" diye bir girdi yoktur. Tarihsel
karşılaştırma için kullanılan tek şey **kabul edilmiş Review kaydı** ve onun
makbuzlarıdır.

---

## 7. Kaynak kilidi ve kapsam dürüstlüğü

### 7.1 Kaynak kilidi

```text
1) adayın source_excerpt'i sağlanan pakette BİREBİR bulunmalı
   (yalnızca satır sonu/boşluk normalizasyonu + NFKC; bulanık eşleştirme YOK)
2) alıntı TEK bir parçaya çözülmeli
3) her olgu support_refs taşımalı (ref'ler deterministik ve incelenebilir)
```

Kilit tutmazsa aday üretilmez: model "makul" bir cümle yazmış olsa bile kaynak
gösterilemediği için listeye girmez.

Kural **model düzeyinde fail-closed**'dır: `ReviewInsight` en az bir KANONİK
referans taşımadan oluşturulamaz (boş ya da yalnızca boşluk içeren liste
doğrulama hatasıdır). Bu yalnızca `status=fact` için değil adaylar için de
geçerlidir; kaynaksız çıktı üretmeye çalışan bir yol varsa o yol düzeltilir,
kural gevşetilmez.

### 7.1.1 Tarihsel olgu, güncel kayıttan bağımsızdır

```text
"Todo X, Y anında tamamlandı"  →  kanıt: event:<event_id>   (append-only)
                                  entity:<todo_id>  YALNIZCA hâlâ varsa ek bağlam
```

`todo.completed` Event'ı append-only'dir; Todo/Entity sonradan silinse bile
Event kalır (`event.entity_id` → NULL). Bu yüzden tamamlanma olgusu Entity
silinince KAYBOLMAZ ve referansı da boşalmaz. Aynı kural son tarih satırları
için de geçerlidir: kanonik referansı olmayan satır için olgu/aday
ÜRETİLMEZ; uydurma ya da pseudo kaynak yazılmaz.

### 7.2 Kapsam dürüstlüğü — `source_manifest`

H5 "ne kadar baktım" sorusunu saklamaz:

```text
events_considered        kaç Event görüldü
reviews_considered       kaç Review okundu
entities_considered      kaç varlık
projects_considered      kaç proje
deadlines_considered     kaç son tarih
daily_notes_expected     dönemde BEKLENEN günlük not sayısı
daily_notes_found        bulunan
daily_notes_missing      eksik  → MISSING_DAILY_NOTES
vault_sources[]          okunan kasa dosyalarının ref'leri
h3_evidence_ids[]        kullanılan kanıt kimlikleri
hot_memory_checked       kaç sıcak hafıza öğesi (bağlam)
h4_used                  yerel model gerçekten kullanıldı mı
truncated                herhangi bir tavan devreye girdi mi
```

Ek olarak `trace` adım adım "kaç kayıt görüldü / kaç kabul edildi" der ve
`truncated=true` sessiz kırpmayı imkânsız kılar. Tavanlar `+1 nöbetçi` ile
ölçülür.

---

## 8. Kaynak doğrulama (her çağrıda)

H5 **önbellek tutmaz ve hiçbir şey yazmaz**; bu yüzden kaynak doğrulaması her
çağrıda yeniden yapılır:

```text
önceki yanıtın geçerliliği iddia EDİLMEZ
kaynak bu çağrıda bulunamazsa aday bu çağrıda ÜRETİLMEZ
aynı girdi + aynı durum → aynı çıktı (deterministik)
```

Ayrı bir "kaynak değişti" uyarı kodu YOKTUR: H5 önbellek tutmadığı için
karşılaştırılacak eski bir okuma da yoktur; doğrulama zaten okuma anındadır.
Kaynağa bağlanamayan aday sessizce düşürülmez: alıntı pakette yoksa aday
listeye hiç girmez ve manifest/iz sayıları bunu gösterir.

---

## 9. Mükerrer kaynak belirsizliği (`AMBIGUOUS_CANDIDATE_SOURCE`)

Bir adayın alıntısı pakette **birden fazla** parçada geçiyorsa hangi kaynağa
bağlandığı belirsizdir. H5 tahmin YÜRÜTMEZ:

```text
alıntı tek parçaya çözülüyor   → aday üretilir, ref o parçayı gösterir
alıntı birden fazla parçada    → AMBIGUOUS_CANDIDATE_SOURCE + aday ATLANIR
alıntı hiçbir parçada yok      → aday üretilmez (kaynak kilidi tutmadı)
```

Aynı kural yönetilen not kimliği çakışmasında da geçerlidir: iki dosya aynı
`forkos_id`'yi sahipleniyorsa hedef **tahmin edilmez**, çakışma
`managed_source_conflict` adayı olarak bildirilir.

---

## 10. Varış yeri politikası

`suggested_destination` bir **öneridir**; politika tablosu model hayal gücüne
bırakılmaz:

| Aday türü | Varsayılan varış yeri | Entity kapsamı kanıtlanmışsa |
|---|---|---|
| `commitment` | `todo` | `todo` |
| `goal` | `hot_memory` | `hot_memory` |
| `constraint` | `hot_memory` | `hot_memory` |
| `decision` | `general_vault` | `project_vault` |
| `project_knowledge` | `general_vault` | `project_vault` |
| `lesson` | `general_vault` | `project_vault` |
| `reference` | `general_vault` | `project_vault` |

```text
entity kapsamı KANITLANMIŞ = aday tam olarak bir varlığa bağlı
                             (support_refs ile gösterilebilir)
```

H5 bu adreslere **yazmaz**; öneriyi Hermes'e ve kullanıcıya bırakır.

---

## 11. Yinelenme sayımı — skor değil

Terfi adayları şu sırayla listelenir:

```text
1) recurrence_count   aynı normalize ifadenin kaç kaynak parçasında geçtiği (sayı)
2) source_count       kaç kaynak referansıyla desteklendiği (sayı)
3) candidate_id       deterministik kimlik (eşitlikte bağ bozucu)
```

Bunlar **sayımdır**, puan değildir: `recurrence_count=3` "3 kez söylendi"
demektir, "önem derecesi 3" değil. H5 hiçbir yerde güven, olasılık, ağırlık
veya öncelik puanı üretmez.

---

## 12. Makbuz tabanlı öncelik sonucu

Haftalık mod, önceki Review'ın **bildirdiği öncelikleri** onun makbuzlarıyla
eşleştirir:

```text
Review.decisions["_receipts"]["priorities"] = [
    {title, todo_id, scheduled_day}, ...
]
```

Sonuç satırları:

```text
{title, todo_id, scheduled_day, outcome: completed|open|unknown, status: <todo durumu>|missing}
{title, outcome: "unknown", reason: "PRIORITY_RECEIPTS_UNAVAILABLE"}
```

`outcome` üç değerlidir ve **yokluk kanıt değildir**:

```text
Todo var ve status=done   → outcome="completed"
Todo var ve status≠done   → outcome="open"
Todo YOK (silinmiş)       → outcome="unknown", status="missing"
```

Makbuz KİMLİKTİR, güncel varlık değildir: silinen hedef "açık" sayılmaz ve
`todo_id` tarihsel kimlik olarak yanıtta kalır.

Makbuz yoksa H5 **tahmin etmez**:

```text
önceki Review öncelik bildirmiş ama makbuz taşımıyorsa
→ PRIORITY_RECEIPTS_UNAVAILABLE
→ outcome="unknown", reason="PRIORITY_RECEIPTS_UNAVAILABLE"
→ "tamamlandı/tamamlanmadı" İDDİA EDİLMEZ
```

Başlık eşleştirmesi **kanonik kimlik sayılmaz**: makbuzda `todo_id` yoksa
yalnızca başlığa bakarak "tamamlandı" denmez.

Şema değişikliği GEREKMEZ: makbuzlar mevcut `Review.decisions` JSON'unda
yaşar; yeni migration yoktur.

---

## 13. Kısmi dönem dürüstlüğü

```text
dönem tamamlandı  → partial=false, comparable=true
dönem yarım       → partial=true,  comparable=false
                    (haftalık modda ek olarak PARTIAL_PERIOD uyarısı)
```

`until` verilmediğinde dönem şimdiye kadar açıktır; bugünün haftası da yarımdır.
Yarım dönem, tam dönemle **sayısal olarak karşılaştırılmaz**: `comparison`
bloğu `comparable=false` ve `reason="PARTIAL_PERIOD"` taşır. Bu, "bu hafta daha
az çalıştın" gibi yanıltıcı bir cümleyi yapısal olarak engeller.

---

## 14. H4 sözleşmesi — `consolidation_candidates_v1`

Konsolidasyonda kullanılan yeni sözleşme (H4 lane SAYISI değişmez):

```text
contract: consolidation_candidates_v1
{
  "candidates": [
    {"kind": "...", "text": "...", "source_excerpt": "..."}
  ]
}
kind            decision | lesson | commitment | goal | constraint
                | project_knowledge | reference
tavan           30 aday
text            ≤ 500 karakter (ADAY ifade; kanıt değil)
source_excerpt  ≤ 500 karakter ve sağlanan pakette BİREBİR bulunmalı
```

H4 kapalıysa (`H4_ENABLED=false`) veya sağlayıcı düşükse yalnızca
`H4_UNAVAILABLE` uyarısı eklenir; kanonik olgular, açık döngüler, son tarihler
ve günlük notlar **deterministik olarak** akmaya devam eder.

---

## 15. İlgili belgeler

- [H5 Gözden Geçirme Zekâsı](h5-review-intelligence.md) — akış, modlar, bozulmuş mod davranışı.
- [H5 Araç Sözleşmesi](h5-tool-contract.md) — imza, sınırlar, kodlar, örnek çıktı.
- [H2 Hafıza Politikası](h2-memory-policy.md) — sıcak hafızanın kendi sahiplik kuralları.
- [H4 Yerel Biliş](h4-local-cognition.md) — sözleşmeler, doğrulayıcı ve kaynak kanıtı.
- [H3 Kanıt Getirme](h3-retrieval-evidence.md) — kanıt katmanı ve dürüstlük semantiği.
