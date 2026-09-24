# A5 — Judgment Layer: dondurulmuş v1 sözleşmesi (A5.0)

## Amaç ve sahiplik

A5, H3'ün mekanik olarak uygun bulduğu kanıtın sorguya yararlılığını, A4 adayının mevcut dayanıklı kartla anlamsal ilişkisini ve açıkça verilen bir yanıt iddiasının sağlanan kanıtça desteklenmesini **ölçer**. Ölçüm mimarisi sağlayıcı mimarisinden önce gelir. Judge çıktısı doğru, yetki veya kanonik durum değildir; güven sinyali gerçekliğin olasılığı değildir. Belirsizlik belirsiz kalır.

Hermes orkestrasyona, PostgreSQL operasyonel duruma, H2 güncel kürasyonlu bağlama, f0rknbrain dayanıklı bilgiye, A3 tarihsel epizoda, A4 aday ve insan denetimli terfiye, H3 sınırlı uygun kanıt getirmeye sahiptir. A5 yalnızca geçici anlamsal ölçüme sahiptir. Yeni bellek/veritabanı veya kalıcı yargı defteri yoktur. A5.0 üretim hattına bağlı değildir.

## Üç ayrı iş

| İş | Girdi | Çıktı | Sınır |
|---|---|---|---|
| Context | Sorgu + H3'ten zaten uygun, sıralı, ≤15 öğe | `essential/useful/weak/irrelevant/uncertain` ve ayrı `unique/redundant/uncertain` | H3'ün reddettiği kaynağı geri getiremez, kanıt yaratamaz |
| Memory relation/support | A4 adayı + okunabilir, kapsam-uyumlu, efektif ve sır engeli olmayan tek kart | `same_claim/narrows/elaborates/changed_decision/incompatible/unrelated/uncertain`; ayrı destek: `supported/contradicted/insufficient/uncertain` | İlişki supersession/terfi/yazma izni değildir |
| Answer evidence | ≤1000 karakterlik **açık** iddia + sınırlı alıntı ve çevre bağlamı | `supported/contradicted/insufficient/uncertain` | Yanıtı yeniden yazmaz, otomatik iddia çıkarmaz veya engellemez |

H3 excerpt sınırı 1200, toplam metin sınırı 8000 karakterdir. Alıntı tek başına destek değildir; çevre bağlamı yoksa `context_complete=false` ve belirsizlik tercih edilir. Kaynak/tarih karışmaz: geçmiş olay güncel gerçek diye sunulamaz. `provider_confidence` yalnızca sağlayıcı tarafından bildirilen belirsizlik sinyalidir, nesnel doğruluk olasılığı değildir. Çıktılarda serbest komut/aksiyon alanı bulunmaz.

Her uygun `ContextCandidate` için tam bir `ContextVerdict` zorunludur: eksik, yinelenen veya uydurulmuş kanıt kimliği geçersizdir. `status != success` olan her verdict yalnızca `uncertain` anlamsal alanlar taşıyabilir; başarılı çalışma da meşru biçimde `uncertain` dönebilir. Deterministik bellek kontrolü A4'ün `normalize_statement()` eşliğini yeniden kullanır; parafraz tahmini yapmaz.

## Rollout ve sağlayıcı sınırı

Her amaç bağımsız mod taşır; A5.0'da hepsi `off`:

- `off`: sağlayıcı çağrısı yok; deterministik kontrol.
- `shadow`: yalnız geçici ölçüm; davranışa etkisi yok.
- `assist`: sınırlı düşük-riskli seçime etki edebilir; kanonik mutasyon/izin yok.
- `on`: yalnız açıkça izin verilen amaç için deterministik politikanın yargıyı kullanması; güvenlik, gizlilik, yazma ve supersession izni yine yok.

Durumlar `success`, `abstained`, `unavailable`, `stale`, `invalid`. Abstention nedenleri `insufficient_evidence`, `ambiguous_relation`, `context_incomplete`, `low_provider_margin`, `unsupported_capability`, `provider_unavailable`, `source_stale`, `mechanical_policy_block`. Bir sağlayıcının yetenekleri `context_relevance`, `semantic_relation`, `entailment`, `contradiction`, `answer_support` kümesidir. Desteklenmeyen yetenek çağrılmaz. Sağlayıcı yoksa deterministik kontrol/çekimserlik kullanılır; gizli uzak fallback yoktur.

`JudgmentProvider` sağlayıcı-nötr protokoldür. A5.1 bağlamda ayrı localhost jevmlx sürecini uygular; varsayılan mod yine `off`tur. A5.2 ilişki için jevmlx, A5.2 destek/çelişki ve A5.3 yanıt için poorjev/NLI yalnız plandır. Bunlar değiştirilebilir uygulama seçenekleridir; v1 domain sözleşmelerine sağlayıcı kimliği sızmaz. Ayrıntı: [A5.1 yerel bağlam yargısı](a5-context-judge.md).

## Kaynak anlık görüntüsü, gizlilik ve yeniden doğrulama

Her değişebilir kaynak `source_id`, tip, mevcut sürüm/revizyon ve yakalama zamanı ile bağlanır. Mekanik uygunluk ve gizlilik sağlayıcıdan **önce** uygulanır; H3 kapsam, Vault güvenli yolu, kaynak sınırı ve tazelik atlanamaz. Sağlayıcı çağrısı sonrasında kaynak revizyonu yeniden okunur; değişmiş/kaybolmuşsa `stale` ve sonuç kullanılamaz. Append-only olay gibi gerçekten değişmez kimlik/sürümün yeterli olduğu istisna gelecekte kaynak bazında açıkça belgelenmelidir.

Yerellik `local|remote`; uzak sağlayıcı **varsayılan ret**. İlgili her öğede `remote_allowed=true` açıkça gerekli; duyarlılık ve kaynak politikası önceden denetlenir. Judge kendi gizlilik uygunluğunu belirleyemez. Bu sözleşme uzak içerik paylaşımını bugün açmaz. A5.0 gerçek özel verileri değerlendirme setlerine koymaz.

`remote_allowed` yalnızca **uzak aktarımı** denetler; yerel sağlayıcının mekanik uygunluğunu etkilemez. Mekanik uygunluk ayrı ve her iki yerellik için zorunlu kapıdır.

## Dondurulmuş v1 değerlendirme ve kontrol

`backend/tests/fixtures/a5/` altındaki üç JSON dosyasının `schema_version`, `dataset_version` ve exact-byte SHA-256 kimliği `evals.py` içinde sabittir. Hatalı beklenti sessizce değiştirilmez; gerekirse belgelenmiş v2 oluşturulur.

| Set | Sürüm | Vaka | SHA-256 |
|---|---|---:|---|
| ContextEval | context-v1 | 13 (8 uygun, 5 mekanik dışlama) | `e6c7537e47e1ef0a1f65e6d262456508049a4a56b52fab70c35750c51eb216e4` |
| MemoryEval | memory-v1 | 14 | `c3eac5d7b65ec6b1f0319b7f4e9250f73f4fe49997a6c082a2e98907ae56b770` |
| AnswerEvidenceEval | answer-evidence-v1 | 12 | `6de1b082e91c34d7f607999077caef2084d9dd514ac9093d056ca9825b718397` |

Kontrol: Context H3 sırasını ve 11 uygun öğeyi korur; 0 anlamsal yeniden sıralama/dışlama. Memory yalnız **tam** ifade eşliğini tanır, diğer 13 vakada `uncertain` (parafraz dahil). Answer 12/12 semantik `uncertain`, 0 yanlış `supported`. Bunlar sağlayıcı başarısı değil, muhafazakâr kontrol ölçümüdür. Uygunluk dışlamaları değerlendirmede judge'a `irrelevant` diye gönderilmez; **hiç gönderilmez**.

İleride bağlam için top-k yararlılık kesinliği, useful recall, redundancy removal, false exclusion, NDCG/MRR, çekimserlik ve gecikme; memory için relation accuracy/macro-F1, false incompatible, false changed decision, çekimserlik ve gecikme; answer için support macro-F1, **false supported**, contradiction/insufficient recall, çekimserlik ve gecikme ölçülür. Güvenlik yanlış-pozitifleri toplam doğruluktan önemlidir. Henüz sağlayıcı kazananı ilan edilmez.

## Ertelemeler ve Hermes kancası

Hermes `post_llm_call` teslim öncesi yanıtı bloke/değiştirilemez; bu yüzden A5.3 bir yanıt güvenlik duvarı değildir. Gelecekte explicit verify aracı veya yanıt-sonrası shadow ölçümü olabilir. Gerçek pre-send `on` için uygulanabilir ayrı kanca gerekir. A5.1 yalnız bağlam sıralamasını uygular; A5.2, A5.3, otomatik iddia çıkarımı, kalıcı telemetri, UI ve A6 Brain Doctor başlamadı.
