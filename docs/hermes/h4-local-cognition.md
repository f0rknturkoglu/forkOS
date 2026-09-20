# forkOS × Hermes — H4 Yerel Biliş Yönlendiricisi (Local Cognition Router)

H4, Hermes'in **açıkça istediği** dar bir bilişsel primitifi yerel bir modelle
yürütür: sınıflandırma, adlandırılmış sözleşmeye göre yapılandırılmış çıkarım ve
sınırlı sorgu yeniden yazımı.

H4 bir sohbet botu, genel bir muhakeme ajanı, bulut LLM geçidi, otonom
planlayıcı veya doğruluk sahibi **değildir**.

---

## 1. Sorumluluk paylaşımı

```text
Hermes        → hangi bilişsel primitifin gerektiğine karar verir
H4            → hangi UYGUN yerel yürütme yolunun o işi yapabileceğine karar verir
Yerel model   → bir ADAY sonuç önerir
Doğrulayıcı   → adayın sözleşmeyi karşılayıp karşılamadığına karar verir
H1            → onay kurallarından sonra kanonik yazmayı yapar
```

> **H4 hiçbir doğruluğa sahip değildir.** Entity, Link, Event, Todo, Project,
> Sıcak Hafıza, Vault bilgisi, Application, Opportunity veya Bookmark
> oluşturmaz/güncellemez. Kanonik yazma yolu H1'dir.

---

## 2. Akış

```text
SİNYALLER            lane, input_chars, yetenekler, slot yapılandırması, sağlık
      ↓
SERT UYGUNLUK        policy.route_task — SAF, deterministik, metni GÖRMEZ
      ↓
MODEL SEÇİMİ         en küçük sağlıklı ve uygun slot
      ↓
YEREL YÜRÜTME        loopback sağlayıcı (Ollama /api/chat, stream=false)
      ↓
DETERMİNİSTİK        şema + kaynak kanıtı + tarih/saat + korunan terim
DOĞRULAMA
      ↓
SINIRLI TEKRAR /     small ≤2 deneme, medium ≤1 deneme, toplam ≤3 çağrı
YEREL ÇIKIŞ          yukarı yapışkan (small → medium → dur)
      ↓
SONUÇ ya da needs_escalation
```

### 2.1 Sinyal ≠ politika ≠ karar

```text
SİNYAL   : ölçülen olgular (girdi boyu, sağlık, yapılandırma)
POLİTİKA : uygunluk kuralları (tek modül: policy.py)
KARAR    : seçilen slot + gerekçe kodları
```

Model tabanlı yönlendirici YOKTUR: "prompt zor görünüyor" bir politika değildir.
`route_task` metni hiç görmez — imzasında `text` parametresi yoktur, bu yüzden
karmaşıklık kelimelerine göre karar vermesi yapısal olarak imkânsızdır.

### 2.2 Seçim kuralı

```text
local-small → local-medium
```

Küçük model uygun olduğunda tercih edilir. Medium yalnızca şu durumlarda seçilir:

```text
small yapılandırılmamış veya sağlıksız   (LOCAL_SMALL_UNAVAILABLE)
small girdi bütçesi yetmiyor             (LOCAL_SMALL_CONTEXT_EXCEEDED)
small doğrulama denemelerini tüketti      (LOCAL_SMALL_VALIDATION_FAILED)
```

Yerel model kaydı TUTULMAZ: profiller yapılandırmadan türetilir, sağlık istek
anında ölçülür. Kalıcı tablo, Redis veya disk önbelleği yoktur.

### 2.3 Sağlık, uygunluktan ayrıdır

```text
healthy=true, eligible=false   → model ayakta ama bütçesi yetmiyor
healthy=false                  → model kurulu değil / sağlayıcı erişilemez
```

---

## 3. Lane'ler

| Lane | Girdi | Çıktı |
|---|---|---|
| `classify` | `text`, `labels`, `classification_goal` | `{"label": "<sağlanan etiketlerden biri>"}` |
| `structured_extract` | `text`, `contract` | Sözleşmeye uygun doğrulanmış öğeler |
| `query_rewrite` | `text`, `protected_terms?` | `{"rewritten_query": "..."}` (2–200) |

```text
rerank      → H4.1 araştırması (CrossEncoder değerlendirmesi bekliyor)
compress    → H4.x/H5 araştırması
reason, chat, answer, plan → REDDEDİLİR (muhakeme Hermes'e aittir)
```

Lane açıkça verilir: H4 hedef ayrıştıran bir ajan değildir.

---

## 4. Çıkarım sözleşmeleri

Sözleşmeler **adlandırılmış ve sürümlüdür**; serbest JSON şeması kabul edilmez.
Uyumsuz bir değişiklik `_v2` olur, sessiz şema kayması olmaz.

| Sözleşme | Koleksiyon | Öğe alanları |
|---|---|---|
| `academic_calendar_v1` | `events` | `title`, `category`, `date_text`, `start_date?`, `end_date?`, `source_excerpt` |
| `weekly_schedule_v1` | `blocks` | `title`, `day_of_week`, `start_time`, `end_time`, `source_excerpt` |
| `deadline_candidates_v1` | `deadlines` | `title`, `kind`, `date_text`, `due_date?`, `due_time?`, `source_excerpt` |

Kategoriler: `registration · classes · exam · holiday · deadline · orientation · payment · other`
Günler: `monday … sunday` · Türler: `submission · application · exam · payment · registration · appointment · other`

### 4.1 Tarih dürüstlüğü

Kaynak metin normalize bir tarihi **güvenle desteklemiyorsa**:

```text
start_date = null / end_date = null / due_date = null
date_text  = kaynaktaki ifadenin AYNEN korunmuş hâli
```

Model, şemayı doldurmak için yıl veya gün UYDURMAZ.

---

## 5. Doğrulama — model önerir, doğrulayıcı karar verir

| Doğrulayıcı | Ne yapar | Kod |
|---|---|---|
| Şema | Pydantic modeli, ek alan YASAK | `OUTPUT_SCHEMA_MISMATCH` |
| Boyut | Koleksiyon/öğe tavanları | `OUTPUT_TOO_LARGE` |
| Kaynak kanıtı | `source_excerpt` sağlanan metnin içinde **birebir** bulunmalı (NFKC + satır sonu + boşluk normalizasyonu; bulanık eşleştirme yok) | `SOURCE_EXCERPT_NOT_FOUND` |
| Alan temellendirmesi | `date_text` gibi ham alanlar `source_excerpt`'in parçası olmalı | `SOURCE_FIELD_NOT_SUPPORTED` |
| Etiket | `label` sağlanan kümeden olmalı | `INVALID_CLASS_LABEL` |
| Tarih | Deterministik çözümle uyuşmalı; geçerli takvim tarihi; `end_date ≥ start_date` | `INVALID_DATE` |
| Saat/gün | `HH:MM`; `end_time > start_time`; gün ve saatler kaynaktan çıkarılanla eşleşmeli (gece yarısı v1 kapsamı dışında) | `INVALID_TIME` |
| Korunan terim | Yeniden yazımda AYNEN kalmalı | `PROTECTED_TERM_LOST` |
| JSON | Ham çıktı JSON olmalı | `INVALID_MODEL_JSON` |

İkinci bir model doğrulayıcı olarak ÇAĞRILMAZ: doğrulama tamamen
deterministiktir.

---

## 6. Tekrar ve yukarı çıkış

```text
local-small : en fazla 2 deneme   (2. deneme sınırlı onarım promptu kullanır)
local-medium: en fazla 1 deneme
toplam      : ≤ 3 model çağrısı
```

Onarım promptu yalnızca doğrulama kodunu ve şema hatırlatmasını taşır: önceki ham
yanıt, yığın izi veya uzun içerik geri konmaz.

Çıkış **yukarı yapışkandır**: `small → medium → dur`. Aynı işlem için medium'dan
small'a dönülmez.

Zincir tükendiğinde:

```text
status=needs_escalation
failure_code=LOCAL_CAPABILITY_UNAVAILABLE   (iki slot denendi)
             | VALIDATION_FAILED            (tek slot vardı, doğrulama tutmadı)
             | MODEL_PROVIDER_UNAVAILABLE   (sağlayıcı erişilemez/zaman aşımı)
             | MODEL_UNAVAILABLE            (model kurulu değil)
result=null + recovery_hint + route_decision
```

### 6.1 Sağlayıcı düşmesi tipik bir durumdur (H4.1)

Yerel sunucu çalışmıyorsa (sağlık probu başarısız):

```text
status=needs_escalation
failure_code=MODEL_PROVIDER_UNAVAILABLE
attempts=[]                       sağlık probu bir ÇIKARIM DENEMESİ DEĞİLDİR
selected_slot=null · validation_status=not_attempted
```

Bu **beklenen bir operasyonel durumdur**, uygulama hatası değil: ham
`ProviderError` servis sınırından çıkmaz ve `LOCAL_COGNITION_FAILED` üretilmez.
Aynı durum gerçek `/mcp` üzerinden de `is_error=false` + tipik gövde olarak döner.

### 6.2 Yükseltme ≠ seçim (H4.1)

```text
LOCAL_MEDIUM_SELECTED
= İLK yönlendirme kararı medium'u seçti (small yapılandırılmamış/sağlıksız/
  bütçesi yetmiyor). small HİÇ denenmedi → escalated=false

ESCALATED_TO_LOCAL_MEDIUM
= çalışma ZAMANINDA small denendi ve medium'a çıkıldı
  (small iki kez doğrulamada düştü ya da üretim anında MODEL_UNAVAILABLE)
  → escalated=true
```

`RouteDecision.escalated` yalnızca gerçek yukarı geçişte `true` olur.

Bütçe aşımı da "kullanılamaz" değildir:

```text
girdi > small bütçesi  → LOCAL_SMALL_CONTEXT_EXCEEDED
girdi > medium bütçesi → LOCAL_MEDIUM_CONTEXT_EXCEEDED
sağlıksız/yok          → LOCAL_SMALL_UNAVAILABLE / LOCAL_MEDIUM_UNAVAILABLE
```

**Arka planda buluta düşülmez**: yükseltme kararı çağırana aittir.

---

## 7. Sağlayıcı ve ağ sınırı

```text
sağlayıcı   : Ollama (/api/chat, stream=false, format=<JSON şeması>, temperature=0)
istemci     : mevcut httpx  (yeni SDK bağımlılığı YOK)
adres       : yalnız loopback — localhost · 127.0.0.1 · ::1
yönlendirme : izlenmez (follow_redirects=False)
proxy       : ortam değişkenlerinden devralınmaz (trust_env=False)
araç        : modele hiçbir araç/fonksiyon verilmez
indirme     : çalışma zamanında model İNDİRİLMEZ
```

Loopback dışı bir adres `INVALID_LOCAL_MODEL_ENDPOINT` ile reddedilir ve **hiçbir
bağlantı denenmez**: H4 yapılandırma yoluyla bir bulut geçidine dönüşemez.

---

## 8. Gizlilik sınırı — dürüst ifade

```text
H4 model çağrısı yalnız loopback üzerindedir: 0 dış ağ, 0 uzak API, 0 DNS.
```

Ancak **"Hermes uçtan uca yereldir" DENMEZ**: Hermes'in kendi modeli uzak olabilir
ve H4'e gönderdiği metni zaten görmüş olabilir. H4 yalnızca yerel çıkarım
katmanının sınırını daraltır.

Ek olarak:

- H4 **bağlam toplamaz**: `forkos_evidence`, `brain_search`, `hot_memory_context`
  veya `forkos_project_context` çağırmaz. Hangi sınırlı metnin gönderileceğine
  Hermes karar verir.
- Veritabanı oturumu AÇMAZ, Vault'u OKUMAZ: kasa yokken de çalışır.
- Kaynak metin, prompt ve model yanıtı **loglanmaz**; kalıcı istek geçmişi
  tutulmaz.
- Gözlemlenebilirlik `RouteDecision`'dır: slot, model kimliği, deneme sayısı,
  gecikme, doğrulama durumu ve sınırlı kodlar. İçerik taşımaz.

---

## 9. Ürün akışındaki yeri

```text
akademik takvim
  ↓  Hermes: "çıkarım gerekiyor"
  ↓  H4 structured_extract  → doğrulanmış adaylar
  ↓  Hermes: "hangileri eyleme dönük?"
  ↓  kullanıcı onayı
  ↓  H1 Todo/planner yazmaları
```

H4 planlama YAPMAZ, görev OLUŞTURMAZ. Haftalık program çıkarımı da aynı
şekildedir: H4 blokları çıkarır, planı Hermes önerir, yazmayı H1 yapar.

`query_rewrite` primitifi H3'e **otomatik bağlanmaz**: H3 deterministik leksikal
getirme olarak kalır. Yeniden yazımı getirmeye katmak, dogfooding ve ayrı bir
H4.1 tasarımı gerektirir.

---

## 10. Neler YOK (bilinçli)

```text
gömme/vektör yönlendirici    öğrenilmiş yönlendirici    karmaşıklık-temelli seçim
LLM doğrulayıcı              uzak model yedeği           otomatik model indirme
kalıcı model kaydı           model çağrı geçmişi tablosu Redis/Prometheus
genel sohbet/muhakeme lane'i çok kiracılı altyapı       frontend
H3 içine gizli entegrasyon   LLMLingua sıkıştırma        CrossEncoder rerank (H4.1)
```

---

## 11. İlgili belgeler

- [H4 Araç Sözleşmesi](h4-tool-contract.md) — imza, sınırlar, hata kodları, örnek.
- [H4 Kurulum ve Doğrulama](h4-setup.md) — yapılandırma, model kurulumu, sorun giderme.
- [H4 Yönlendirme Eval'i](evals/h4-routing.yaml) — sentetik, tekrar oynatılabilir vakalar.
- [H3 Kanıt Getirme](h3-retrieval-evidence.md) — H4'ün üzerine oturduğu kanıt katmanı.
- [Yol Haritası](roadmap.md) — H4.1/H5/H6 sıralaması.
