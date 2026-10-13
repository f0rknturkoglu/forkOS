# Goals 2.0 — Semantic Reliability Closure

## Durum ve kapsam

**GOALS 2.0 SEMANTIC RELIABILITY — PARTIAL**

Bu rapor 39e8910f5118221799f20e5aaf0c896438233bb0 üzerine yapılan yerel
çalışmanın ölçüm sonuçlarını kaydeder. Önceki 50 denemenin raporu tarihsel baseline
olarak korunmuştur. Yeni akışın gerçek model kalitesi iyileşmedi; VERIFIED değildir.
Ölçüm aşamasında CI, commit/push, release/tag veya deploy çalıştırılmadı.
Sonraki teslimde kullanıcı tüm değişikliklerin commit/push edilmesini istedi;
teslim Git geçmişinden izlenir. Bu teslim PARTIAL kalite sonucunu değiştirmez.

## Varsayılan kullanım politikası

Çok aşamalı deneysel akışın yedi ana authoring serisi kullanılabilir içerikte 0/70 oldu.
Kalite artmadan çağrı/gecikme artışını varsayılan yapmamak için
`GOAL_STUDIO_SEMANTIC_ENABLED=false` korunur. CLI `--semantic` ile açıkça bu akışı
seçer; bu seçenek provider/consent/tool sınırlarını değiştirmez. Başlamış turn'ün
pipeline işareti kalıcıdır: dağıtım/bayrak değişmesi sözleşmeyi ortasında değiştirmez.
Koçluk durum kartı her iki yolda kanonik snapshot'tan üretilir. Yeni `current_facts`
DTO'su model yanıtı beklenirken veya yanıt bozulduğunda da o sorunun verisini
gösterir. Geçmiş mesajların snapshot'ları değiştirilmez. Varsayılan yolun
Learning ve authoring P1'lerinin kapandığı iddia edilmez. Başarısız deneysel tur
sessizce eski üreticiye veya başka sağlayıcıya aktarılmaz.

Primary fixed cohort pipeline kodunu belleğe yükledikten sonra durum kartının
ölçülmüş yüzde tip dönüşümü ve pending/error DTO'su, yeni tur için opt-in kapısı,
revizyon aday/alan/kapsam kontrolleri, kısmi revizyonda hedef adını koruma ve açık
takvim olumsuzluğunda scheduler'ı atlama düzeltildi. Bunlar yedi primary isteğin
authoring prompt'larını değiştirmedi. Sonraki CLI ve browser süreçleri güncel kodu
yeni süreçte yükler. Raw log'lar sonuçları değiştirilmeden korunur; geliştirme
probe'ları fixed/holdout serilerine eklenmez.

## Kök nedenler

- Flat WorkPlan bağımsız konu/kaynak ve çok aşamalı görev ilişkisini kaybediyordu.
- Öğrenme gereksinimi açık sözcüklere bağlanıyordu; modelin yorumladığı amaç ayrı
  denetlenmiyordu.
- Revizyon modeli gerçek phase/Topic/slot referanslarını kavrayamıyordu. UUID/index
  üretmesini istemek yerine küçük kapsam referansları sunucu tarafından çözülür.
- Önceki pseudo-JSON örnekleri geçerli JSON yerine JS benzeri cevaplara yol açtı.
  Yeni örnekler geçerli JSON'dur; bozuk JSON tamamlanmaz, en fazla bir yeniden
  üretim istenir.
- Yeni çok aşamalı denemelerde denetçi de kullanıcı eşiğini uydurma dış kurallarla
  reddedebildi. Desteksiz iddia/ilgisiz süreç reddi artık verilen içerikten birebir
  alıntı gerektirir. Bu tek başına denetçinin anlamsal doğruluğunu kanıtlamaz.
- Hermes repetition guard bazı gerçek yanıtları tümüyle attı; bu uygulama tarafında
  başarılı üretim sayılmaz.

## Mimari

`semantic_planning.py`: Needs/Requirements, SemanticDraft, SemanticRevision,
QualityReview ve CoachingReply. Açık kullanıcı şartları çıkarımdan ayrılır.
Learning ve resources required/optional/not_applicable/unknown olabilir. Sayısal
outcome ve uzun dönem tercihi sunucunun açık isteğinden gelir. Bilinmeyen seviye,
puan, tarih ve dış koşullar doldurulmaz. Plan modeli bağımsız konuları, kaynak
arama ihtiyaçlarını ve görevlerin konu ilişkilerini kurar; uygulama bir alan
şablonu veya hazır YDS/pasaport planı üretmez.

`semantic_pipeline.py`: bounded, Studio turn içinde kalıcı stages. Her adımın
request/run kimliği saklanır; reviewer generator'ın private history'sini paylaşmaz.
İhtiyaç veya taslak için açıklanabilir ret doğru katmana tek düzeltme verir.
Normal yeni hedef üç, kısa somut iş iki, revizyon/koçluk iki Hermes run isteğidir; belirsiz
mesaj için bir route çağrısı eklenebilir. Global üst sınır altı çağrı ve bir repair.

`package_authoring.py`: model-facing anlamsal çıktı mevcut PackageDraft'a çevrilir.
İki geçişli Topic derleme konu farklı aşamalarda kullanılsa da tek kanonik Topic
oluşturur. Mevcut konu kaynakları ve doğrulanmış kayıt bağlama mevcut V2
`learning.resource`, `record.link`, `roadmap.create` işlemlerini kullanır.

Onay, fingerprint, stale/provenance/policy, transaction rollback, event/Link,
V1 ve gerçek Todo/Topic/Project sahipliği korunur. Inference domain kaydı yazmaz.
Model üretimi başarısızsa güvenilir paket hazırmış gibi gösterilmez.

## Türkçe istek ve revizyon

Emir köklerine ek olarak ekleyelim/ekleyebilir miyiz, taşıyalım, hafiflet, azaltalım,
güncellememiz lazım ve plana alsak ifadeleri ele alınır. Sence/gerekir mi/nasıl olur,
açık olumsuzluk ve İngilizce should I/we/what if yorum yolundadır. Diğer belirsiz
ifadeler küçük sınıflandırıcıyla coach/author/clarify olarak çözülür. Hiçbir rota
insan onayı yerine geçmez.

Tipli eylemler: görev/konu/kaynak ekleme, mevcut kayıt bağlama, görev düzenleme ve
öncelik, phase rename, node detach/reattach, mevcut slot move/reduce/replan.
Başlık eşleşmesi tekil olmalı; aynı isimde farklı kayıtlar tahmin edilmez. Boş
süreli slot hafifletilmez; mevcut konu yeniden eklenmez. Paylaşılan kaydı bağlamak
kaydı kopyalamaz. Slot snapshot değişmişse öneri yeniden bağlam ister.

## Native structured output araştırması

Gerçek kurulu Hermes **0.21.6**, custom OpenAI-compatible provider ve
**Qwen3.5-9B-Q4_K_M**, mevcut llama.cpp Metal binary, context **65536**, parallel **1**,
reasoning **off**, araçlar **0** kullanıldı. Kişisel Hermes ayarları değiştirilmedi.

Doğrudan llama.cpp `response_format` JSON schema/enum sentinel'e uydu. Aynı alan
Hermes `/v1/runs` tepesinde ve `model_options` içinde gönderildiğinde normal serbest
yanıt verdi. Kurulu kaynakta `_request_agent_overrides`/`_create_agent` zinciri
schema'yı completion'a taşımıyor. Alt sunucunun desteği uygulama zincirinin desteği
sayılmadı; forkOS sahte bir strict schema özelliği ilan etmez.

Doğrudan llama.cpp `--n-predict 16` probu 16 token/length ile durdu; Hermes üzerinden
isteğin slot ayarı **8192** idi ve sunucu default'unu geçersiz kıldı. Bu probun
ardından owned runtime önceki flags'e döndü. Per-request output budget kullanılıyor
iddiası yoktur. Uygulama acceptance bütçesi 180 saniyedir; native decoding maliyetini
kesin sınırlamaz. Bütçe aşımında stop denenir; geç cevap kabul edilmez.

## Deney protokolü

DB `forkos_hermes_eval`, PG16 tmpfs ve ayrı Compose network. Test DB
`forkos_test` ayrıdır. Başlangıç/koçluk/revizyon fixture'ları sentetiktir; gerçek
Vault mount edilmez. Profile/key/history geçicidir. Her deneme yeni StudioSession
ve client_uuid alır; eski cevabı yeniden kullanmaz. Yedi ana authoring senaryosu
A–G ve ayrı holdout paraphrase kümesi bulunur. Fixed/holdout birbirine eklenmez.

`backend/scripts/eval_goal_hermes.py` sadece adı doğrulanmış disposable DB ve
verified tool-free local profile ile çalışır. Her satır ham çıktı, girdi byte
boyutu, tokenlar, çağrı sayısı, zaman, model aşaması, JSON/schema/semantic/compile,
repair, kanonik snapshot ve kabul durumunu saklar. `quality_proxy` yalnız otomatik
kontroldür; operator_review ayrı yapılır. Kabul edilen paketler insan incelemesinin
anlamsal kalitesinin yerine geçmez. Öneriler ölçüm sırasında uygulanmaz; Goal/Todo
sayısı önce/sonra kontrol edilir.

Örnek owned ortam komutu:

```bash
python scripts/eval_goal_hermes.py --cases yds software passport document python mixed long_term --attempts 10 --semantic --timeout 180 --output /evidence/fixed-final.log
python scripts/eval_goal_hermes.py --cases yds software passport document python mixed long_term --attempts 2 --semantic --holdout --timeout 180 --output /evidence/holdout-final.log
```

## Sonuçlar

### Primary fixed A–G: 70 bağımsız deneme

| Senaryo | İlk geçiş derleme | En fazla bir repair sonrası | Kullanılabilir paket | Çağrı | Median / p95 sn |
| --- | ---: | ---: | ---: | ---: | ---: |
| YDS 55+ | 0/10 | 0/10 | 0/10 | 27 | 43.22 / 170.06 |
| forkOS V2 | 0/10 | 0/10 | 0/10 | 29 | 34.61 / 41.75 |
| Pasaport | 0/10 | 1/10 | 0/10 | 33 | 30.31 / 48.32 |
| Belge teslimi | 0/10 | 0/10 | 0/10 | 31 | 20.65 / 27.63 |
| Python öğrenme | 0/10 | 0/10 | 0/10 | 29 | 29.72 / 46.10 |
| Mülakat + portföy | 0/10 | 0/10 | 0/10 | 32 | 38.24 / 62.42 |
| Beş yıllık akademik hedef | 0/10 | 0/10 | 0/10 | 25 | 16.69 / 155.06 |

Toplam **206 gerçek Hermes run isteği**, 66 repair girişimi, bir derleme/repair başarısı.
202 parse edilen stage cevabının 133'ü JSON, 85'i schema, 71'i stage gate geçti.
Bunlar ayrı stages'in sayılarıdır; 71 başarılı plan anlamına gelmez. Dört native
run tamamlanmadı ve parse aşamasına gelemedi. Tüm denemelerde median 29.75,
p95 147.32 saniye. Raporlanan input/output token **284375 / 45394**; dört başarısız
native run'ın kullanım bilgisi yok, gerçek compute maliyeti bu toplama sığmaz.
Toplam instruction+input boyutu 502886 byte. Başarısız uzun repetition cevapları
gecikmeyi artırdı. Bu ortamda ayrıca regression testleri çalıştı; süreler kontrollü
donanım benchmark'ı değildir.

Tek derlenen pasaport taslağı (attempt 5) kullanıcı söylemediği TR/UK ayrımı,
yeni/çalışma başvurusu, diplomatik temsilcilik, e-posta/e-imza, belirli belgeler
ve ödeme kanalı varsayımları içeriyordu. Bağımsız reviewer kabul etti; operator
incelemesi reddetti. Yeni gate'in anlamsal doğruluğu bu karşı örnekle sınırlıdır.
Kabul edilmemiş diğer 69 cevap end-to-end kullanılabilir paket değildir;
başarısız bir taslağın tüm kelimelerinin yanlış olduğu iddia edilmez.

Eski 50 denemede yazılım 9/10, pasaport 8/10 derleme; yeni akışta aynı primary
isteklerde 0/10 ve 1/10. Eski coverage proxy ile yeni operator kalite ölçüsü aynı
ölçek değildir; buna rağmen derleme ve çağrı maliyeti belirgin kötüleşmiştir.
Bayrak bu yüzden varsayılan olarak kapalıdır. Daha hızlı ve daha kaliteli yeni
ürün yolu gösterilemedi.

### Yerel regresyon

- Backend, gerçek ayrı PostgreSQL ile: **2955 passed, 43 skipped**.
- Odaklı semantic/package/adaptive/inference/provider: **221 passed**.
- Frontend: **162 dosya, 1087 test passed**; `tsc -b` ve üretim build geçti.
- Ruff, değişen TSX/generated dosyaların Prettier kontrolü geçti.
- Runtime OpenAPI ve üretilmiş TypeScript kontratı güncel.
- Endpoint coverage: mevcut tek referanssız uç `/api/system/career-ops/doctor`, eşik 3.
- Ağsız, salt okunur repo privacy guard'ları: **10 passed** (pytest cache yazma uyarısı).
- Yeni migration, tablo, entity/event registry tipi, paket, endpoint veya dış ağ bağımlılığı yok.

DB testleri insan onayından önce Goal/Todo/Topic yazılmadığını, ortak Topic'nin
iki aşamada tek kimlikle kullanımını, kaynak/kayıt eklemede mevcut nesnelerin
korunmasını, slot/aşama/Topic stale durumlarını ve partial revizyonda hedef adı
korumayı doğrular. Aynı görüşmede gerçek DB completion/reopen/new work/outcome
değişimleri **0→50→100→67→100→67**, ölçülen outcome %100 olarak doğrulandı;
bu testin model cevapları fixture'dır, native model başarı oranına katılmaz.



### Ayrı ölçüm serileri

Holdout A–G iki bağımsız paraphrase ile denendi; fixed seriye eklenmedi.

#### Holdout

| Senaryo | n | İlk kabul/derleme | Repair sonrası | Operator uygun | Çağrı | Median / p95 sn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| document | 2 | 0 | 0 | 0 | 8 | 27.56 / 27.63 |
| long_term | 2 | 0 | 0 | 0 | 4 | 11.26 / 12.45 |
| mixed | 2 | 0 | 0 | 0 | 6 | 24.35 / 35.45 |
| passport | 2 | 0 | 0 | 0 | 5 | 20.36 / 26.36 |
| python | 2 | 0 | 0 | 0 | 5 | 36.63 / 61.10 |
| software | 2 | 0 | 1 | 0 | 7 | 36.91 / 38.48 |
| yds | 2 | 0 | 0 | 0 | 5 | 24.64 / 37.11 |

#### Revizyonlar — ilk 30 deneme

| Senaryo | n | İlk kabul/derleme | Repair sonrası | Operator uygun | Çağrı | Median / p95 sn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| revision_attach | 3 | 0 | 0 | 0 | 6 | 4.65 / 27.02 |
| revision_detach | 3 | 0 | 0 | 0 | 7 | 13.54 / 20.35 |
| revision_move | 3 | 0 | 0 | 0 | 8 | 10.10 / 20.26 |
| revision_one | 3 | 1 | 1 | 1 | 8 | 15.76 / 24.45 |
| revision_reduce | 3 | 0 | 0 | 0 | 8 | 21.39 / 56.76 |
| revision_rename | 3 | 0 | 0 | 0 | 15 | 26.08 / 30.06 |
| revision_replan | 3 | 0 | 0 | 0 | 7 | 16.83 / 18.96 |
| revision_resource | 3 | 0 | 0 | 0 | 9 | 16.88 / 24.89 |
| revision_topic | 3 | 1 | 1 | 0 | 6 | 7.99 / 10.15 |
| revision_two | 3 | 2 | 2 | 2 | 6 | 9.12 / 9.18 |

#### Revizyonlar — düzeltme sonrası ayrı 12 deneme

| Senaryo | n | İlk kabul/derleme | Repair sonrası | Operator uygun | Çağrı | Median / p95 sn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| revision_attach | 3 | 0 | 1 | 1 | 9 | 16.90 / 21.21 |
| revision_rename | 3 | 0 | 0 | 0 | 11 | 20.23 / 22.53 |
| revision_resource | 3 | 0 | 0 | 0 | 9 | 17.87 / 23.38 |
| revision_topic | 3 | 1 | 1 | 0 | 7 | 9.12 / 20.26 |

#### Varsayılan koçluk — 20 deneme

| Senaryo | n | İlk kabul/derleme | Repair sonrası | Operator uygun | Çağrı | Median / p95 sn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| focus | 10 | 10 | 10 | 6 | 10 | 2.55 / 3.61 |
| progress | 10 | 9 | 10 | 10 | 11 | 2.55 / 8.03 |

#### Deneysel koçluk — ayrı 6 holdout denemesi

| Senaryo | n | İlk kabul/derleme | Repair sonrası | Operator uygun | Çağrı | Median / p95 sn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| focus | 3 | 3 | 3 | 0 | 7 | 10.49 / 11.69 |
| progress | 3 | 0 | 1 | 0 | 11 | 19.08 / 22.62 |

#### Güncel kod authoring kontrolü — ayrı 7 deneme

| Senaryo | n | İlk kabul/derleme | Repair sonrası | Operator uygun | Çağrı | Median / p95 sn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| document | 1 | 0 | 0 | 0 | 4 | 30.45 / 30.45 |
| long_term | 1 | 0 | 0 | 0 | 3 | 31.28 / 31.28 |
| mixed | 1 | 0 | 0 | 0 | 3 | 70.94 / 70.94 |
| passport | 1 | 0 | 0 | 0 | 3 | 24.49 / 24.49 |
| python | 1 | 0 | 0 | 0 | 2 | 13.63 / 13.63 |
| software | 1 | 0 | 0 | 0 | 4 | 45.64 / 45.64 |
| yds | 1 | 0 | 0 | 0 | 3 | 180.29 / 180.29 |

### Stage ve maliyet ayrımı

| Seri | JSON / schema / gate | Stage | Repair | Raporlanan input / output token | Girdi+instruction byte | Kullanım eksik native run |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed | 133 / 85 / 71 | 202 | 66 | 284375 / 45394 | 502886 | 4 |
| holdout | 22 / 16 / 13 | 40 | 14 | 57384 / 8063 | 100435 | 0 |
| revisions | 71 / 55 / 36 | 80 | 24 | 138467 / 5336 | 261953 | 0 |
| revision-followup | 31 / 28 / 18 | 36 | 11 | 67533 / 1549 | 129942 | 0 |
| coaching-default | 0 / 0 / 0 | 0 | 1 | 26721 / 1052 | 39288 | 0 |
| coaching-semantic | 17 / 17 / 13 | 18 | 3 | 24306 / 1085 | 36827 | 0 |
| final-authoring-smoke | 12 / 10 / 8 | 21 | 7 | 30799 / 4729 | 61489 | 1 |

Varsayılan koçluk düz metindir; onun JSON/schema stage ölçüsü **uygulanmaz**, tabloda
0/0/0 olması başarısız JSON sayısı değildir. Bu seride 20 cevabın tamamı kabul edildi;
19 ilk geçiş, biri bounded repair ile. 21 gerçek çağrı yapıldı. Operator incelemesinde
16/20 yorum uygun bulundu. Tamamlanmış kelime tekrarını açık iş gibi önermek,
%67 oranını korumayı söylemek, gerçek ölçüm bilinmiyor diye doğrulanmış çalışma
ilerlemesini belirsiz saymak ve kaydedilmemiş tarama hataları uydurmak açık kaldı.
Kanonik kart model yorumundan bağımsızdır; prose doğruluğu tamamen çözülmedi.

Deneysel koçlukta 4/6 cevap/clarification kabul edildi; tam güvenilir sonuç 0/6.
Bir yanıt %67 çalışma ilerlemesini ölçülmüş YDS puanı gibi anlattı; reviewer
yanlış kabul etti. İki yorum açık işi önerdi fakat sınıflandırıcı yolundan geçince
o ölçüm epochunda facts mesajına eklenmemişti. Başka biri verilmiş hedefi yeniden
sordu. Route/clarification için de pending ve accepted facts artık korunur;
unit test ve son browser soru akışı bunu ayrıca doğrular. Eski ham sonuçlar
yeni kod çalışmış gibi yeniden etiketlenmedi.

Holdout yazılım attempt 2 test yazma/çalıştırma, hata düzeltme ve paketleme
boyutlarını kapsadı, fakat kullanıcı belirtmediği imzalama ve sunucuya yükleme
koşullarını ekledi; tamamen uygun sayılmadı. İlk revision_topic attempt 1 bir
konu yerine iki konu ekledi. Açık ekleme miktarı ortak literal parser ile
görev/konu/kaynak için ayrıldı; server yanlış sayıyı reddeder. Aynı kaydedilmiş
cevabın güncel gate ile replay
[kanıtı](../../.codex/artifacts/semantic-reliability/quantity-replay.log)
`incomplete_revision` oldu. İmplicit bağlama ve “adını … yap” isteklerinin
route/coach yerine author intent olarak ele alınması, tavsiye/olumsuzluğun
önceliği ve boş/same-day move/replan reddi eklendi. Bunlar domain planı üretmez.

Sonraki ayrı 12 revizyonda bir mevcut kayıt bağlama doğru çözüldü. Tek konu
sayısı korunmuş başka bir taslak, gramer için anlamsız “Yükleyici ve Yüklemeler”
başlığını üretti; reviewer yine kabul etti. Kaynak, taşıma, hafifletme, ayırma,
rename ve replan için güvenilir native oran gösterilemedi. Küçük n=3 serileri
ürün güvenilirliği kanıtı değildir. Son yedi authoring kontrolü güncel kodla
0/7 kaldı; YDS turu acceptance bütçesinden yaklaşık 180.29 saniyede durdu.
`timeout` flag yalnız CLI deadline'ını ölçer; uygulamanın bütçe duruşu ayrı
`failed/budget_expired` olarak görünür.

CLI `applicable` alanı teknik olarak author/revision için preview varlığını,
koçluk için hatasız discussion varlığını ölçer. İnsan incelemesi ve gerçek
onay/materialization bunun ayrı kanıtıdır. `format_valid` en son public parse
sonucudur; daha sonraki stage/compile başarısını ispatlamaz. Tablolar bu alanları
“kabul/derleme” olarak adlandırır. Otomatik `quality_proxy` operator kararının
yerine kullanılmadı. Her başarısız örneğin stage hata kategorisi ve detayı
JSONL içinde saklıdır.

### Epoch ve tekrar üretim

Primary/holdout authoring, ilk revision serisi, facts/routing/quantity
düzeltmelerinden önce import edilmiş süreçlerde çalıştı. Sonraki düzeltmeler
eski raw log'lara uygulanmadı. Ayrı followup ve son authoring kontrolü yeni
süreçlerle çalıştı; son browser API son facts/routing kodunu yükledi. Hash
snapshot'ları `source-hashes-primary.json` ve `source-hashes-final.json` içindedir.
Final authoring n=1 serisi primary n=10 serisine birleştirilmez. Default/semantic
koçluk ve aynı isimli önce/sonra revizyonlar ayrı dosyalarda özetlenir.

## Gerçek browser akışları

Yalnız disposable API `127.0.0.1:18888` ve Vite `127.0.0.1:5174` kullanıldı.
Kişisel 5173 yüzeyi/DB/Vault test için kullanılmadı.

- Yeni hedef “Örnek belgeyi incele.” gerçek Hermes'ten kullanılabilir preview
  alamadı; hata gösterdi, Goal/Todo yaratmadı.
  [Ekran](../../.codex/artifacts/semantic-reliability/authoring-browser-failure.png).
- Gerçek `revision_one` attempt 3, browser'da önizlendi ve onaylandı. “Sonuç
  belgesini incele” kanonik Todo ve plan bloğu oluştu. Todo sayısı 124→125,
  Goal sayısı 61→61, mevcut hedef adı değişmedi; session `applied` oldu.
  [Önizleme](../../.codex/artifacts/semantic-reliability/native-revision-preview.png),
  [uygulanan görev](../../.codex/artifacts/semantic-reliability/native-revision-applied.png).
- Gerçek followup `revision_attach` attempt 3 onaylandı. Mevcut “Kanonik ek
  kontrol” Todo aynı UUID ile gerçek Gramer aşamasına bağlandı. Todo 125→125,
  Goal 61→61; yeni kopya yok. DB `roadmap.target_id == canonical_todo_id`
  doğruladı.
  [Önizleme](../../.codex/artifacts/semantic-reliability/native-attachment-preview.png),
  [bağlanan kayıt](../../.codex/artifacts/semantic-reliability/native-attachment-applied.png).
- Aynı sentetik YDS görüşmesi `9678c6cf-7325-44ec-9de9-8a322a90bfce` içinde
  açık Todo UI'dan tamamlandı: %67→%100, 2/3→3/3. Gerçek sonuç ölçülmedi.
  Yeni “Şu an neredeyiz?” sorusunda model iki çağrı sonunda bozuk cevap verdi;
  o sorunun %100 kartı ve unknown outcome yine görünürdü.
  [Hata halinde doğru kart](../../.codex/artifacts/semantic-reliability/coaching-after-completion-error.png).
- Aynı Todo UI'dan yeniden açıldı, aynı UUID ve `completed_at=None` korundu.
  Hedef %67 ve 2/3'e döndü. Aynı görüşmede dolaylı öncelik sorusu route üzerinden
  beş native çağrıyla geçerli yanıt verdi; gerçek açık Todo'yu önerdi ve %67
  kartı eklendi. Bu tek başarı geniş güvenilirlik iddiası değildir.
  [Yeniden açma sonrası](../../.codex/artifacts/semantic-reliability/coaching-after-reopen.png).
  Eski %67 yanıt snapshot'ı değiştirilmedi; başarısız %100 turunun kanonik facts'ı
  durable stage request'lerinde saklıdır.
- 1280×900 geniş ve 390×844 dar viewport kontrol edildi; dark-mode kartı okunur,
  yatay taşma yok, dar ekranda butonlar sarılır. Textarea→Tab ile Gönder odağı
  doğrulandı. Loading, bağlantı retry ve model error yüzeyleri gerçek browser'da
  görüldü. Geçici viewport override kaldırıldı.
  [Geniş](../../.codex/artifacts/semantic-reliability/coaching-facts-final-wide.png),
  [dar](../../.codex/artifacts/semantic-reliability/coaching-facts-final-narrow.png).

Learning/Project/outcome yeni durumları ve 0/50 gibi diğer oranlar gerçek DB
regression fixture'larıyla doğrulandı; bunların tümü için native browser başarısı
iddia edilmiyor. Browser kanıtında yeni hedef yaratma başarısı yok; küçük görev
revizyonu ve mevcut kayıt bağlama onayı gerçekten çalıştı.

## Test çalıştırma notları

Son backend koşusu **2955 passed, 43 skipped**, odaklı son koşu **221 passed**.
Bir ara aynı disposable test DB'sini iki pytest süreci kullandı; TRUNCATE
fixture'ları çakıştı. İkisi durduruldu ve tek süreçle tam test yeniden çalıştı.
Bu ara log'lar başarı toplamına katılmaz. Yeni tavsiye-routing testinin `mıyım`
Türkçe soru ünlüsünü yakalamaması düzeltildi ve son testlerde geçti. Test helper
import hatası lint sırasında kapatıldı; yarım koşular final sayı değildir.

Son frontend koşusu **162 dosya / 1087 passed**, worker sayısı iki. Önceki yüksek
CPU yükü altındaki koşuda üç zamanlama/asenkron test başarısız olmuştu
(FlashcardPage, LearningPage, PomodoroCrossSurface); uygulama dosyaları değiştirilmeden
bütün suite yeniden geçti. Build, Prettier, Ruff ve API sync ayrıca geçti.

## Kalan kusurlar

**P0:** Bu kapsamda onaysız domain yazma, kanonik kimlik kopyalama, stale revision
bypass veya rollback regresyonu bulunmadı. Bu ifade repository-wide security scan
sonucu değildir.

**P1 açık:**

- Yeni hedef üretiminde güvenilir Learning/resource/outcome/delivery kapsamı,
  closed schema ve başarılı paket derleme oranı gösterilemedi.
- Bağımsız reviewer yanlış idari prosedür, anlamsız konu ve yanlış puan yorumunu
  kabul edebiliyor. JSON ve compiler başarısı içerik doğruluğu değildir.
- Normal scoped revision'ların çoğu geçerli preview üretemiyor. Bağlama routing'i
  ve literal miktar hataları düzeltildi; native başarı oranı yeterli değil.
- Varsayılan coaching prose bazen tamamlanmış işi yeniden açık sayıyor veya
  kanıtsız ifade üretiyor. Kanonik facts doğru olsa da yorum tamamen güvenilir değil.
- Route classifier açık bağlamı yeniden sorabiliyor. Teknik accept/clarify oranı
  kullanıcının sorusunu yanıtlamakla eşdeğer değildir.

**P2 / sınırlar:**

- Hermes runs API schema/output-token limitini forward etmiyor. Uygulama bütçesi
  native decoding maliyetini kesin sınırlamıyor; eksik usage compute'ü gizleyebilir.
- Context bounded; truncation kullanıcıya gösterilir. Her Türkçe kip/horizon veya
  karmaşık çok eylemli revizyon için güvenilir kapsama iddia edilmez.
- Hedefin tamamını yeniden üretmek yerine tek tipli küçük revizyon kullanılır;
  büyük/çok eylemli istekler açıklığa kavuşturma gerektirebilir.
- Target seçilmeyen küçük görev eklemesi mevcut hedef adında ek phase üretebilir;
  bu örnek browser'da görüldü. Eşleşme/plan preview ve bazı error metinleri hâlâ
  kullanıcı için gereğinden ayrıntılı veya authoring odaklıdır.

Model adı veya doğrudan llama.cpp desteği gerekçe gösterilerek strict generation
varmış gibi davranılmadı. Mevcut kurulu zincirle bu yaklaşım güvenilir ürün sonucu
vermedi; yeni model/provider/API ile ölçüm yapılmadan VERIFIED denemez.

## Kanıt dizini ve teslim

Yerel kanıtlar `.codex/artifacts/semantic-reliability/` içindedir. Ham JSONL'ler,
per-stage hata detayları, operator kararları, per-cohort özetler, native schema ve
token-cap probe'ları, hash'ler, test log'ları ve screenshot'lar saklandı. Bu
raporda adı geçen seri ve operator JSON dosyaları ayrıdır; development probe'ları
primary/holdout toplamlarına eklenmedi. Yedi nihai ölçüm serisinde **159 deneme /
423 gerçek Hermes run isteği** var; browser/prototype çağrıları bu toplam dışında tutulur.

Migration yok. Ölçüm aşamasının başlangıç commit'i
`39e8910f5118221799f20e5aaf0c896438233bb0` olarak kaydedildi.

Son kaynak guard kontrolü URL ile HTTP kavram adını ayırır; büyük harfli
`HTTPS://` de reddedilir. HTTP içeren bağlantısız kaynak ihtiyacının kanonik
onay akışı mevcut integration testinde doğrulandı. Bu guard düzeltmesi
ölçülen native prompt veya stage içeriğini değiştirmedi.

## Değişen dosyalar

- `.env.example`
- `backend/app/config.py`
- `backend/app/modules/goal/package_authoring.py`
- `backend/app/modules/goal/package_constraints.py`
- `backend/app/modules/goal/semantic_pipeline.py`
- `backend/app/modules/goal/semantic_planning.py`
- `backend/app/modules/goal/studio.py`
- `backend/app/modules/goal/studio_inference.py`
- `backend/app/modules/goal/studio_schemas.py`
- `backend/app/modules/goal/studio_transport.py`
- `backend/openapi.json`
- `backend/scripts/eval_goal_hermes.py`
- `backend/scripts/summarize_goal_hermes.py`
- `backend/tests/test_goal_adaptive.py`
- `backend/tests/test_goal_inference.py`
- `backend/tests/test_goal_semantic.py`
- `backend/tests/test_goal_studio_providers.py`
- `compose.hermes-goal.yaml`
- `docs/architecture/goals-2.0-hermes-reliability.md`
- `docs/architecture/goals-2.0-semantic-reliability-closure.md`
- `docs/architecture/goals-2.0.md`
- `frontend/src/generated/api-schema.ts`
- `frontend/src/modules/goal/GoalCoachingFacts.test.tsx`
- `frontend/src/modules/goal/GoalCoachingFacts.tsx`
- `frontend/src/modules/goal/GoalStudio.tsx`

## Temizlik doğrulaması

Göreve ait Hermes gateway, llama.cpp ve Vite süreçleri durdu. Üç owned container
ve boş `forkos-semantic_default` network kaldırıldı. Geçici profile/history,
credentials ve runtime metadata silindi. 18435, 8643, 18888, 5174 portlarında
listener kalmadı. Kişisel `forkos_pgdata` volume hiçbir test container'ına
mount edilmedi; temizlik öncesi/sonrası kimliği/oluşturulma bilgisi değişmedi.
İlişkisiz anonymous volume silinmedi. Kişisel DB/Vault/attachments/session/model
weights ve kurulu Hermes kodu korunur. Kanıt dosyaları rapor için bırakıldı.

`git diff --check` temiz. Teslim kapsamı kod/config/test/API çıktıları, bu rapor,
yeni evaluator/semantic/facts dosyaları ve değerlendirme JSON'larıdır.
Default semantic flag kapalıdır.

Çağrı sayısı benzersiz `/v1/runs` POST kimliklerinden ölçülür. Uygulamanın altı
çağrı sınırı bu run istekleridir; native agent/provider içindeki retry veya
completion denemelerinin bağımsız toplamı ayrıca instrument edilmedi. Tokenlar
Hermes’in raporladığı usage değerleridir; gerçek decode maliyeti için kesin
sayaç iddiası yoktur.

Bu görevde başlatılan OrbStack motoru `orb stop` ile durduruldu; Docker daemon
bağlantısının kapalı olduğu doğrulandı. Anahtar/profile dosyaları veya çalışan
test servisleri bırakılmadı.
