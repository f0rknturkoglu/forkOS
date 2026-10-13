# Goals 2.0 — Live Hermes Reliability Closure

Tarih: 2026-10-13. Başlangıç/final HEAD: `61bd6187f5410edee605a8e222dda92a5148073f`.
Önceki Adaptive Closure çalışma ağacı korundu; commit/push yapılmadı.

**GOALS 2.0 HERMES RELIABILITY — PARTIAL**

Kanonik ilerleme koçluğu ve normal hedeflerde biçim kabulü iyileşti. Ancak sabit
yerel modelle her ana senaryoda 9/10 kullanışlı, uygulanabilir sonuç eşiği
karşılanmadı. Özellikle YDS'nin Learning kapsamı, idari hedeflerin içerik doğruluğu
ve mevcut hedefe revizyon üretimi açık P1'dir. Testlerin geçmesi canlı model
güvenilirliği yerine kullanılmaz.

## Kök nedenler ve uygulanan değişiklikler

Başlangıçta gerçek `/v1/runs` ile her istem iki kez çalıştırıldı. Model bazen
geçerli paketi `discussion` alanı olmadan verdi; ortak envelope bunu onarım
uygunluğu kontrolünden önce reddetti. Pasaportta `proposal:null` sıradan açıklama
olarak kabul edildi ve hedef oluşmadı. Basit koçluk sorusu ise paket üretmeye
çalıştı; düzeltme de paket sözleşmesine bağlı kaldı. Diğer doğrulanmış hatalar:
eksik JSON kapanışları, yinelenen alanlar, hatalı liste/skaler biçimleri, uydurma
tarih ve yanlış aday token/tipi. Bunların tamamını timeout diye sınıflandırmak
yanlış olur.

- Mevcut Studio turn kaydına `inference_task` eklenir: `author`, `coach`, `legacy`.
  Yeni living hedefi authoring; mevcut hedefte sıradan soru coaching; açık ekle,
  değiştir, taşı vb. istek authoring olur. Eski marker'sız kalıcı turn'ler eski
  parser ve yaşam döngüsüyle devam eder. Yeni agent engine yoktur.
- Living ve feedback isteği başına yeni `GoalContextSnapshot` alınır. Koçlukta
  tam düzenleme şeması yerine çalışma yüzdesi, tamamlanan/bekleyen gerçek işler,
  Topic ve Project durumları, gerçek sonuç ölçümü ve eksik kapsam bilgisi gönderilir.
  UUID, düzenleme indeksleri ve ilgisiz event geçmişi bu promptta bulunmaz.
- Koçluk 2–4 kısa Türkçe düz metin cümlesi üretir; tam paket derlemesi gerektirmez.
  Uyumluluk için tek metin alanı ve `proposal:null` JSON'u da kabul edilir.
  Gerçek proposal, yanlış açık yüzde, kanıtsız tempo/neden ve ölçülmemiş sonuç
  başarısının belirli biçimleri reddedilir. Bunlar tüm Türkçe iddiaları ispatlayan
  bir semantik denetçi değildir; aşağıdaki canlı eksikler devam eder.
- Normal yeni hedefe kapalı ve düz `WorkPlan` verilir: modelin yazdığı somut
  `work`, isteğe bağlı `phase`/`learning_topic`, sayısal sonuç üçlüsü, nitel kabul,
  eksik bilgi ve gerçek Project adayları. Kullanıcının numeric target'ı aynen
  korunur. Anlamlı aşama yoksa hedef başlığı altında gruplama yapılır. Aynı Topic
  tek kez oluşturulur ve görev indeksleri deterministik bağlanır. Gelecek iş,
  eksik Learning veya örnek plan sunucu tarafından uydurulmaz.
- WorkPlan yalnız model sınırındaki semantik biçimdir. Mevcut `PackageDraft`,
  V2 derleyici, preview, fingerprint ve insan onayı kullanılır. Mevcut hedef
  revizyonları/uzun dönemler tam semantik package sözleşmesini kullanır. V1,
  provider consent/provenance, session/idempotency ve rollback yolları korunur.
- Eksiksiz bare JSON, tek fence/zararsız önsöz, geçerli fakat açıklaması eksik
  envelope ve tek elemanlı `learning_topic` listesi kabul edilir. Eksik JSON,
  yinelenen alan, çok kavramlı belirsiz liste, olmayan aday ve güvenli olmayan
  çıktı reddedilir. Authoring'de null/açıklama gerçek taslak sayılmaz.
- En fazla bir kalıcı düzeltme korunur; task'a uygun alan/hata geri bildirimi
  verilir. Token/retry sınırı artırılmadı. Başarısızlık genel fallback planıyla
  kapatılmaz. Normal session'da ham özel çıktı yerine en fazla iki kategori,
  byte sayısı/hash, token ve partial/interrupted metadata'sı saklanır.

## Tekrarlanabilir canlı değerlendirme

`backend/scripts/eval_goal_hermes.py` yalnız `forkos_hermes_eval` isimli disposable
DB ve doğrulanmış yerel, araçsız Hermes profilinde çalışır. Kişisel DB'de çalışmayı
reddeder. Başlangıçta iki tamamlanmış, bir açık Todo, üç kanonik roadmap adımı,
%67 çalışma ilerlemesi ve hiç ölçülmemiş 55 puanlık KR yaratır. Ayrı sentetik
release Project'i gerçek reuse adayıdır. Her attempt yeni persistent session'dır;
onaysız inference öncesi/sonrası Goal/Todo sayısının değişmediği kontrol edilir.
Driver yeni bağımlılık kurmaz ve provider/kişisel profil değiştirmez.

İzole API ortamındaki komut:

```bash
python scripts/eval_goal_hermes.py --attempts 10 --timeout 120 --output /tmp/final-hermes.log
```

Beş istem değişmeden kullanıldı:

1. `YDS'den en az 55 puan almak istiyorum. Günde iki saat çalışabilirim.`
2. `forkOS V2'yi yayımlamak istiyorum. Eksik testleri ve release hazırlıklarını tamamlamalıyım.`
3. `Pasaport başvurumu tamamlamak istiyorum.`
4. `Neredeyiz, nasıl gidiyoruz?`
5. `Bu hafta neye odaklanmalıyım?`

Sabit runtime: Hermes **0.21.6**, mevcut yerel **Qwen3.5-9B-Q4_K_M** GGUF,
mevcut llama.cpp Metal binary, alias aynı, custom localhost OpenAI-compatible
endpoint. Context **65536**, parallel **1**, reasoning **off**, araç **0**.
Gateway ve model yalnız loopback'te; API disposable host bridge ile erişir.
Mevcut bağımlılık venv'i readonly kullanıldı. Yeni cloud/paket/proxy, grammar
ayar değişikliği veya provider seçimi yoktur. Sampling/retry/token varsayılanları
değişmedi. Fresh geçici profil repo config şablonundan kuruldu; kişisel geçmiş,
Vault ve credentials kullanılmadı.

Başlangıç 10, nested-prompt keşfi 10, flat-contract keşfi 10 ve gruplu aday keşfi
6 attempt'ten sonra final cohort **50 bağımsız attempt** olarak donduruldu.
Keşifler final oranlarına katılmadı. Finalde **63 gerçek model çağrısı** oldu:
50 ilk çağrı ve 13 tek düzeltme. Yeni promptlar alan bağımsızdır; YDS/forkOS için
hard-coded plan veya özel fallback yoktur.

## Final oranlar — her satırın paydası 10

JSON: sözdizimi/unique-field kabulü. Semantik: kapalı WorkPlan→PackageDraft
doğrulaması; identity/tarih/kısıt/preview derlemesi bundan ayrı ölçülür.
İlk ve final sütunları aynı attempt'in ayrı aşamalarıdır, iki başarı sayılmaz.

| Üretim | JSON ilk / final | Semantik ilk / final | Derleme ilk / final | İçerik kapsam proxy'si final | Düzeltme başarılı / denenmiş |
| --- | --- | --- | --- | --- | --- |
| YDS | 9 / 9 | 7 / 7 | 2 / 3 | 0 | 1 / 8 |
| Yazılım | 9 / 9 | 8 / 9 | 8 / 9 | 7 | 1 / 2 |
| Pasaport | 10 / 10 | 8 / 9 | 7 / 8 | 6 | 1 / 3 |

İçerik proxy'si sınırlı otomatik denetimdir: YDS'de görev+Learning+55 KR;
yazılımda görevlerin test ve yayın kapsamını anması ve Learning üretmemesi;
pasaportta 1–5 görev, Learning/KR olmaması. Bu proxy alan bilgisini veya bütün
doğal dil kapsamını ispatlamaz. Örneğin yazılım #6/#8 bu proxy'yi geçse de yalnız
test hazırlığı veya rapor/not derleme işleriyle eksik kalabilir. Pasaport #1/#5
vizeyi soruya katmış; #6/#7 kullanıcıdan gelmeyen belge/akış varsayımları yazmış.
Dolayısıyla 7/10 ve 6/10 insan incelemesinden geçmiş kesin içerik başarıları
değildir; tam semantik başarı için üst sınır olarak okunmalıdır.

| Koçluk | Biçim ilk / final | Sistemce kabul ilk / final | Otomatik proxy | Manuel inceleme |
| --- | --- | --- | --- | --- |
| Neredeyiz? | 10 / 10 | 10 / 10 | 10 / 10 | 10/10 doğru %67 ve açık işi anlattı; gerçek sonuç başarısı/tempo uydurmadı. #8 sonucu açıkça tekrar anmadı. |
| Bu hafta? | 10 / 10 | 10 / 10 | 6 / 10 | 9/10 kayıtlarla çelişen iddia olmadan gerçek açık işe yöneldi; yalnız 4/10 (#4,5,9,10) mevcut yüzdeyi de söyledi. #7 açık/%0 işi “kısmi tamamlanan” dedi. |

Focus proxy'si birebir görev başlığı arar; #6/#8'in doğru paraphrase'lerini
kaçırır. Öte yandan yüzde söylemeyen yanıtları kabul eder ve #7'nin “kısmi”
iddiasını yakalayamaz. Bu yüzden biçim ve otomatik proxy puanı factual grounding
ve eksiksiz koçluk sözleşmesiyle eşit değildir. Kabul edilen serbest metnin
tüm iddialarını doğrulamayan mevcut guard açık sınırlamadır.

Final timeout **0/50**; API partial/interrupted **0/63**; tüm native run status'ları
`completed`. Input+instructions 1847–4012 byte, runtime input 1232–2345 token,
output 23–445 token. Native API `finish_reason` sağlamadı. Eksik kapanışı kesin
token truncation diye nitelemek mümkün değildir; eksik JSON çıktısı gözlendi,
API üretimi tamamlandı olarak bildirdi. Timeout, token yetersizliği ve modelin
biçim hatası tek kategori yapılmadı.

## Bireysel hatalar ve onarım

Yerel `.codex/artifacts/hermes-reliability/final.log` her attempt'in public ham
çıktısını, tam scoped request/contract'ı, parse/semantik aşamalarını, tokenlarını,
snapshot'ını ve kullanıcıya gösterilen hata/durumunu içerir. `analysis.log` ham
çıktıları tekrar kapalı parser/schema'dan geçirerek ilk/final JSON ve semantik
durumlarını hesaplar. İlk driver sürümünde parse exception için semantic dizisine
false eklenmediğinden bazı türetilmiş `first_semantic_valid` alanları yanlış
olabiliyordu; ham log değiştirilmedi, rapor tekrar ayrıştırılan değerleri kullanır.
Driver'da diziler hizalandı ve ilk-parse koşulu eklendi. Bu metadata düzeltmesi
model çıktısını veya final cohort inference davranışını değiştirmez.

| Attempt | YDS | Yazılım | Pasaport |
| --- | --- | --- | --- |
| 1 | düzeltme sonrası schema reddi | düzeltmeyle derlendi | derlendi; proxy geçti |
| 2 | derlendi; Learning yok | derlendi; ilgisiz Learning | derlendi; 6 görev, proxy dışı |
| 3 | düzeltmeyle derlendi; Learning yok | derlendi | düzeltme sonrası aday/compile reddi |
| 4 | derlendi; Learning yok | iki kez JSON syntax reddi | derlendi; proxy geçti |
| 5 | yanlış Project token'ı, onarım da reddedildi | derlendi | düzeltmeyle derlendi |
| 6 | iki kez schema reddi | derlendi | derlendi; proxy geçti |
| 7 | yanlış aday, onarımda JSON syntax reddi | derlendi | derlendi; proxy geçti |
| 8 | hedef sayı eksiği; onarımda yanlış Project token'ı | derlendi | derlendi; idari hedefe Learning |
| 9 | yanlış Project token'ı, onarım da reddedildi | derlendi | iki aşamada schema reddi |
| 10 | yinelenen görev; onarımda 55 sonucu yok | derlendi; kapsam proxy'si geçmedi | derlendi; proxy geçti |

YDS #2 gerçek çıktısı 55'i koruyor fakat iki çalışma işi ve hiç Learning
üretmiyor. #5/#8/#9 `projects:["candidate_1"]` yazıyor; bu token gerçek Todo,
Project listesi boş. #7 onarımında `projects` içine İngilizce açıklama yazıp
JSON'u bozuyor. #10 son çıktısı Learning içeriyor fakat kullanıcı hedefi 55
puanı kaybediyor. Bunlar sessizce yeni ölçüm/adayla tamamlanmadı. Compiler reddi
“Taslak hazırlanamadı… Görüşme ve mevcut taslak korundu.” olarak gösterildi.

## Gerçek tarayıcı ve kanonik kayıtlar

Kişisel uygulamadan ayrı `5174 → 18888`, disposable `forkos_hermes_eval` kullanıldı.
Bu adımlar final cohort bittikten sonra yapıldı, 50 oranına katılmadı.

1. Aynı persistent görüşmede gerçek model %67'yi ve ölçülmemiş YDS puanını okudu.
   Açık Todo UI'da tamamlandı; kanonik hedef **%100 / 3/3**, sonuç hâlâ bilinmez.
   Görüşme “Son görüşme” ile açılıp aynı soru soruldu. Yeni native yanıt **%100**,
   üç tamamlanan işi ve ölçülmemiş puanı söyledi. Eski %67 snapshot'ı kullanılmadı.
2. Aynı görüşmede `Bir yeni görev ekle: sonuç belgesini incele.` authoring'e geçti.
   İlk ve tek onarım çıktısında topics yokken `topic_index:0` vardı; güvenle
   reddedildi, önceki kanonik işler ve konuşma korundu. Bu akış canlı başarılı
   revizyon olarak sayılmaz; deterministik regresyon onay yolunu ayrıca sınar.
3. Exact pasaport istemi geçerli preview üretti fakat “Vize başvuru formunu doldur”
   ekledi. UI'da reddedildi; Goal/Todo uygulanmadı. Bu örnek schema/compile
   kabulünün içerik doğruluğunu garanti etmediğini gösterir.
4. Exact yazılım istemi gerçek preview üretti; insan onayı düğmesiyle izole testte
   uygulandı: **1 Goal, 4 Todo, 6 PlanSlot**, mevcut Project reuse, sıfır Learning.
   Hedef ekranında kanonik işler, takvim blokları, Project ve %0 görüldü. Model
   metni elle değiştirilmedi. Fakat eksik testleri tamamlamak yerine güvenlik
   test sonucunu doğrulama/sertifika hazırlığına yöneldi; teknik apply başarısı
   tam kapsamlı içerik başarısı olarak sayılmadı. Gerçek bir release çalıştırılmadı.

Kanıtlar: `browser-coaching-fresh.png`, `browser-revision-failure.png`,
`browser-passport-preview.png`, `browser-software-applied.png`, DOM logları,
`browser-session-diagnostics.log` ve `browser-raw-outputs.log`.

## Regresyon ve korunmuş sınırlar

Yeni `test_goal_inference.py` **29 test**: task ayrımı, kısa/bare/fenced ve eksik
envelope kabulü, null authoring reddi, duplicate/incomplete/unsafe çıktı, yanlış
yüzde/gerçek sonuç/tempo, WorkPlan gruplama/Topic dedup ve JSON-safe numeric/date,
tek kalıcı düzeltme, fresh snapshot %0→%100, aynı görüşmede explicit revizyon ve
onaysız domain yazımı olmaması. Mevcut canlı provider test assertion'ları compact
contract'a uyarlandı; consent/provenance korumaları kaldırılmadı.

Tam yerel sonuç: backend **2875 passed / 43 skipped** (215.30s), frontend
**161 dosya / 1084 test**, extension **27 test**. Skip başarı sayılmaz. Önceki
adaptive package, calendar, relation, long-term, V1, approval fingerprint/TTL,
idempotency, rollback, registry ve migration guardrail testleri aynı suite'tedir.
Ruff, Prettier, TS/build/bundle, API-schema senkronu, endpoint coverage/dead-export
sınırları ve whitespace kontrolü geçti; npm audit 0 vulnerability. Yeni public
API schema veya migration yok; mevcut Adaptive alanları senkron kalır.
Yeni üç Python dosyasının Ruff format kontrolü geçti. Ek, repo çapındaki format
kontrolü 344 mevcut dosyanın yeniden biçimlendirilmesini istedi; geniş biçim
değişikliği uygulanmadı. Repo çapında format temizliği iddia edilmez.

## Açık P1 ve teslim

Üretim içerik güvenilirliği ve mevcut hedef revizyonu bu 9B quantized kurulumda
sağlanamadı. Focus yanıtlarında yüzde atlama ve bir yanlış completion iddiası da
var. Regex/promptlar tam factual grounding garantisi vermez. Harmless parsing
ve compiler sınırları iyileştirildi; semantik sınırlar gevşetilmedi, generic plan
ve manuel düzenleme canlı ilk-attempt başarısı sayılmadı. Model değiştirilmedi
ve daha büyük token/retry veya sonsuz onarım denenmedi.

Kişisel PostgreSQL/Vault/credentials/config/consent değiştirilmedi; worker kapalı.
Test DB'leri tmpfs, ayrı network/container ve fresh geçici yerel Hermes profiliyle
çalıştı. Owned API/backend/DB/network, Vite, Hermes, llama.cpp ve geçici anahtar,
profil/harness kaldırıldı. Kişisel `forkos_pgdata` korundu. Çalışan container
kalmayınca bu görevde başlatılan OrbStack durduruldu. 5173/5174/8787/18888/5433/
18434/18435/8643 portlarında dinleyici kalmadı; `cleanup.log` kayıtlıdır.
Yerel kanıt logları/ekranları tutuldu. Commit/push/CI/tag/release/deploy yoktur.

## 2026-10-13/14 — Semantik güvenilirlik çalışması

Bu belgenin yukarıdaki 50 denemesi ve 63 model çağrısı tarihsel baseline'dır;
sonraki sonuçlar bu tabloya karıştırılmamıştır. Yeni çalışma küçük ihtiyaç
sözleşmesi, bağımsız Topic/task ilişkisi, tipli revizyon, ayrı durum kartı ve
bağımsız kalite aşaması ekler. Yeni akışın derlenmesi veya deterministik testleri
9/10 gerçek model kullanılabilirliği anlamına gelmez.

Native structured-output araştırmasında doğrudan llama.cpp desteği doğrulandı;
kurulu Hermes 0.21.6 `/v1/runs` zincirinde schema alanının completion'a taşınmadığı
görüldü. Per-request output limit de bu zincirde doğrulanmadı. İnceleme, yeni
fixed/holdout ölçümleri, maliyet ve açık sorunlar ayrı rapordadır:
[Semantic Reliability Closure](goals-2.0-semantic-reliability-closure.md).
