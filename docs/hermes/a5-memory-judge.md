# A5.2 — Memory Judge (deneysel, yerel poorjev/NLI)

Memory Judge, A4'ün ürettiği `AgentSemanticCandidate` için **salt-okunur danışmanlık** verir. `forkos_memory_judge(candidate_id)` istemciden yalnız UUID alır. A4 adayını, kaynaklarını ve aynı tür/kapsam/özneye ait etkin Vault kartlarını içeriden okur; model yeni kaynak arayamaz. Sıra `MEKANİK → ANLAMSAL → POLİTİKA`dır. Yargı asla yazma izni değildir: terfi, ret, Vault yazımı, silme, düzeltme veya supersession A4'ün ayrı yetkili yolunda kalır.

## Mevcut akış ve ekleme noktası

A3 mühürlü bölüm öğeleri ve H5 anlamlı event'leri → H5 aday çıkarımı → A4 `refresh_candidates` → A4 DB destek satırı / inceleme / yetkili `promote_candidate` → Vault/Hot Memory. A5.2 yalnız A4 adayını okuyan ayrı MCP danışmanlık yüzeyidir; A4 terfi kodunu çağırmaz veya davranışını değiştirmez. `source_revision` yeni adayların her `episode_item`/`event` kanıtına eklenir; eski, revizyonu olmayan adaylar güvenli biçimde `SOURCE_UNBOUND` ile degrade olur. A3 öğesi orijinal konuşmanın tam dökümü değil, türetilmiş mühürlü metindir; explicitness yargısının bu sınırlaması korunur.

### Kanıt sınırlandırması ve tam kanıt doğrulaması (A5.2.1)

A4 adayları zamanla birden fazla oturum veya konsolidasyon döngüsünde 3'ten fazla kanıt (`evidence_refs > 3`) biriktirebilir. A4'ün kanonik kanıt listesi asla budanmaz; tam tarihçe korunur. A5.2 ise model paketini korumak için deterministik sınırlandırma uygular:

1. **Tam kanıt denetimi**: Adayın `evidence_refs` listesindeki *tüm* kaynaklar okunur ve revizyonları doğrulanır. Listede tek bir bozuk, bayat veya gizlilik engeli taşıyan kaynak varsa seçim bunu gizleyemez; işlem doğrudan `degraded` (`SOURCE_STALE` / `SOURCE_INVALID`) döner.
2. **Deterministik seçim (`select_memory_sources`)**: Geçerli kaynaklar arasından en fazla `MAX_SOURCES = 3` kaynak deterministik kuralla seçilir:
   - Rol önceliği: `user` (3) > `canonical` (2) > `assistant` (1) > diğer (0).
   - Yenilik önceliği: Daha yüksek/yeni kaynak ID'si önce gelir (`source_id`).
   - Eşitlik bozucu: Alfabetik `ref` anahtarı.
3. **Ayrık anlık görüntü bağlama (Snapshot)**:
   - `candidate_digest`: Adayın tüm sütunlarını ve tam `evidence_refs` listesini hash'ler. Çıkarım sırasında adaya yeni bir kanıt eklenirse anında `stale` olur.
   - `full_source_digest`: Adaya bağlı *tüm* kaynakların revizyonlarını hash'ler. Seçilmemiş bir kaynak çıkarım sırasında değişirse `stale` olur.
   - `source_digest`: Modele gönderilen seçilmiş kaynak paketinin hash'idir.
   - `policy_digest`: `MEMORY_POLICY_VERSION` ve `MEMORY_SOURCE_SELECTION_VERSION` (`a5-memory-source-selection-v1`) sürümlerini bağlar.

### Mahremiyet ve `remote_allowed` ayrımı

A5.0 mimari sözleşmesi gereği `remote_allowed` bayrağı yalnızca **uzak** model sağlayıcıları için geçerli bir kapıdır. A5.2'nin kullandığı `poorjev` tamamen yerel bir model sağlayıcısı olduğundan `remote_allowed=False` tek başına yerel çıkarımı engellemez. Buna karşılık hassasiyet ve sır kapıları (`is_privacy_blocked`, `contains_high_confidence_secret`, `sensitivity != 'normal'`) hem yerel hem de uzak tüm sağlayıcılar için koşulsuz engelleyicidir (`SENSITIVITY_BLOCKED`).

## Sinyaller ve yetki sınırı

`evidence_support`: `supported`, `partially_supported`, `unsupported`, `uncertain`. `intent`: `explicit`, `implicit`, `tentative`, `uncertain`. `durability`: `durable`, `temporary`, `uncertain`. Kapsam: `same_scope`, `narrower_scope`, `broader_scope`, `different_scope`, `uncertain`; koşul/istisna: `yes`, `no`, `not_applicable`, `uncertain`. Her ilgili kart için ilişki:

| İlişki | Anlam | Mekanik sınır |
| --- | --- | --- |
| `duplicate` | Yeni anlam katmıyor | Tam metin eşitliği önce A4-benzeri normalizasyonla kesilir |
| `same_claim` | Aynı çekirdek önerme, farklı kanıt/ifade | Yazma izni vermez |
| `narrows` | Daha özel/koşullu | Kapsamı kendiliğinden değiştirmez |
| `elaborates` | Uyumlu ayrıntı | Eski kartı silmez |
| `incompatible` | Aynı kapsam/zamanda bir arada olamaz | İnsan/ajan incelemesi gerekir |
| `changed_decision` | Yeni açık karar eskisini değiştirmiş görünüyor | A4 tarih, açık niyet, kapsam ve onayı ayrıca doğrular |
| `unrelated` | İlişki yok | Yanlış genişleme yapmaz |
| `uncertain` | Bağlam yetersiz | Abstention tercih edilir |

Yanıt durumları `disabled`, `success`, `abstained`, `unavailable`, `invalid`, `stale`, `degraded`. Her durumda A4 `baseline_status` ve `baseline_destination` değişmez. `shadow` yalnız ölçer; `assist` ve `on` yalnız yanıttaki inceleme bayraklarını ekler, DB/Vault'a kaydetmez. Varsayılan `off`; deney için `shadow` önerilir. `on` bile otomatik terfi/supersession değildir.

## poorjev ve çevrimdışı kurulum

Entegrasyon upstream [poorjev](https://github.com/rupeshpoojary9/poorjev) 0.1.0, incelenen commit `7e684e95db13b90238c63e6ab39e1a016263a168` üzerindeki `Choice` ve `LocalNLIBackend.entail_probs` API'sini kullanır; sahte HTTP servisi yoktur. Model `MoritzLaurer/deberta-v3-base-zeroshot-v2.0`, sabit HF revizyonu `8e7e5af5983a0ddb1a5b45a38b129ab69e2258e8`. Hipotez sürümü `a5-memory-questions-v1`, donmuş soru hash'i `51cc78bf261d1f1148c85fed8c72b46505a067d873fcb79fe198bd5da8b2d329`; ikisi de provenance'dadır. Yerel `poorjev` olasılıkları **kalibre edilmemiş telemetri**dir: forkOS dev/holdout seti küçük, ON eşikleri veya doğruluk iddiası için kullanılamaz. `calibration_id=null`. Upstream abstention varsa aynen `abstained` döner; varsayılan `Choice` eşik tanımlamadığı için otomatik seçici abstention sağladığı iddia edilmez.

Standart API imajına ML paketi girmez. Ayrı `Dockerfile.memory` ve `compose.memory.yaml` açıkça seçilir; opsiyonel imajın etiketi `forkos-api-memory:local` olduğu için normal `forkos-api` imajını ezmez. Model ilk kez **kurulum sırasında** indirilir; istek sırasında indirme yasaktır. Örnek:

```bash
cd backend
uv sync --extra dev --extra memory
.venv/bin/python scripts/prepare_a5_memory_model.py --destination data/cache/a5-memory-model
cd ..
docker compose -f compose.yaml -f compose.memory.yaml up --build -d api
```

Kurulum betiği var olan dolu dizine dokunmaz. Model manifesti kimlik/revizyonu kaydeder. Compose modeli salt-okunur bağlar, `HF_HUB_OFFLINE=1` ve `TRANSFORMERS_OFFLINE=1` uygular. Sağlayıcı da inference öncesi bu bayrakları zorlar ve yerel `config.json`/manifest doğrular. Ağ/LLM fallback yoktur. Model eksik veya yanlışsa A4 baseline korunur. Bu opt-in imaj normal forkOS kurulumunun yerini almak zorunda değildir.

## MemoryEval

`backend/tests/fixtures/a5/memory_judge_v1.json` 23 tamamen sentetik senaryodur (11 dev, 12 donmuş holdout), SHA-256 `753fffa6a3615fd8e9d8a4d039db86807f3df2717801ee784f7e3da137522cfc`. Etiketleri/model sorularını sonuçlara bakarak değiştirmeyin; yeni sürüm açın. `backend/scripts/eval_a5_memory.py` beklenen/doğrulanan destek, ilişki, niyet, niteleyiciler, macro-F1, coverage/abstention, ECE, üst-etiket Brier, risk–coverage, gecikme ve hatalı-terfi baskısını ayrı dev/holdout raporlar. Son metrik bir **tanı**dır: desteklenmeyen/belirsiz veya mekanik kapıdan geçmeyen örnekte modelin `supported + explicit + durable` demesi; hiçbir yazma yetkisi anlamına gelmez.

`jevmlx` A5.1 için ayrı H3 sıralama şemasındadır; aynı 7 alanlı MemoryEval'e uyarlamak yeni prompt/çıktı sözleşmesi gerektirir. Bu fazda zorlama bir provider karşılaştırması/ensemble yapılmaz. Deterministik kontrol yalnız mekanik vakaları keser ve semantik vakalarda karar vermez.

OrbStack Linux/aarch64 opsiyonel imajında pinli modelle 23 sentetik vaka gerçekten koşuldu. Son rapor (mekanik dışlama ve post-call `stale` vakaları semantik skora katılmaz): dev destek doğruluğu **1/10**, ilişki **3/7** (macro-F1 **0.357**, kapsam **10/11**); holdout destek **2/7**, ilişki **0/3** (macro-F1 **0**, kapsam **7/12**). Holdout kapsam/qualifier performansı da zayıftır. Ham güven skoru özellikle holdout'ta güvenilir değildir (üst-etiket ECE **0.446**, Brier **0.202**, yalnız 3 ilişkili örnek); forkOS kalibrasyonu yoktur. Bunlar model kalitesi kanıtı değildir; `assist`/`on` önerilmez. Varsayılan `off`, kontrollü deney `shadow`.

İlk kaynak ölçümünde model dizini **374 MiB**, normal test imajı **183 MB**, opsiyonel imaj **356 MB** (Docker image `Size`, +**173 MB**); çalışan değerlendirme konteyneri yaklaşık **1.7 GiB RSS** ve kısa tepe ölçümünde **%650 CPU** kullandı. İlk uygun vaka model yüklemesiyle yaklaşık **3.0 sn**, sonraki uygun vakaların medyanı yaklaşık **0.9 sn** sürdü. Sayılar tek Apple Silicon/OrbStack koşusudur; genellenmiş p95 değildir. `off` normal imajda torch/transformers/model kurmaz veya başlatmaz.

Kanonik OrbStack Compose opt-in API servisinde, yalıtılmış `forkos_test` DB ve sentetik A4 adayıyla `shadow` canlı testi `success` döndü. Provenance model kimliği/yukarıdaki revizyonu taşıdı; sağlayıcı gecikmesi **2792 ms** idi. Aday `proposed` kaldı, Vault dosyası yazılmadı. Aynı model değerlendirmesi `docker run --network none` altında da tamamlandı; çıkarım sırasında ağ gerekmedi.
