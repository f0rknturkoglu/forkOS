# forkOS × Hermes — H4 Kurulum ve Doğrulama

H4 **yeni bir zorunlu bağımlılık getirmez**. Yerel bir Ollama sunucusu
olmadan da kod ve testler çalışır: `H4_ENABLED=false` iken araç `H4_DISABLED`
döner ve hiçbir soket açılmaz. Model çağrısı yalnızca açıkça etkinleştirilmiş
bir yerel uç üzerinden yapılır.

---

## 1. Ön koşullar

```text
Ollama sunucusu (isteğe bağlı)   yalnız canlı H4 çağrıları için
H4_ENABLED=true                  yerel model yolu etkinleştirir
H4_SMALL_MODEL / H4_MEDIUM_MODEL  çekilen model kimliklerine ayarlı olmalı
branch: main
```

- **Yeni Python bağımlılığı YOK.** HTTP istemcisi `httpx`, şemalar `pydantic` ile
  yazılmıştır; ikisi de depoda zaten vardır. `requirements`/`pyproject`
  değişmez.
- Ollama yoksa:

```text
H4_ENABLED=false              → araç H4_DISABLED döner; kod ve testler çalışır
H4_ENABLED=true, sunucu yok   → MODEL_PROVIDER_UNAVAILABLE
H4_ENABLED=true, model yok    → MODEL_UNAVAILABLE
```

Hiçbir bozulmuş mod sessiz değildir; her biri kendi kodunu döner.

---

## 2. Yapılandırma

Tüm alanlar `Settings` üzerinden okunur. Varsayılanlar kapalı ve güvenlidir:
etkinleştirmek ve model atamak açık bir adımdır.

| Ortam değişkeni | Ayar alanı | Varsayılan | Anlam |
|---|---|---|---|
| `H4_ENABLED` | `h4_enabled` | `false` | Yerel model yolu ana anahtarı. |
| `H4_OLLAMA_BASE_URL` | `h4_ollama_base_url` | `http://127.0.0.1:11434` | Yerel Ollama kök adresi. |
| `H4_SMALL_MODEL` | `h4_small_model` | `""` | `local-small` slotuna atanacak model kimliği. |
| `H4_MEDIUM_MODEL` | `h4_medium_model` | `""` | `local-medium` slotuna atanacak model kimliği. |
| `H4_SMALL_INPUT_CHARS` | `h4_small_input_chars` | `12000` | `local-small` için muhafazakâr girdi bütçesi. |
| `H4_MEDIUM_INPUT_CHARS` | `h4_medium_input_chars` | `24000` | `local-medium` için muhafazakâr girdi bütçesi. |
| `H4_TIMEOUT_SECONDS` | `h4_timeout_seconds` | `45` | Tek yerel model çağrısı için üst sınır (saniye). |

### 2.1 Yalnızca loopback

```text
localhost      → kabul
127.0.0.1      → kabul
::1            → kabul
diğer host     → INVALID_LOCAL_MODEL_ENDPOINT
```

`H4_OLLAMA_BASE_URL` loopback dışına işaret ederse yapılandırma **reddedilir**.
Yürütme sınırı `local_loopback`'tir: uzak bir uç noktaya sessizce düşülmez.

---

## 3. Model kurulumu (sunucu tarafı)

H4 çalışma zamanında **model İNDİRMEZ**. Model çekme açık, elle bir adımdır ve
yalnızca sunucu tarafında yapılır. Eksik model çağrı anında `MODEL_UNAVAILABLE`
döner; arka planda indirme denenmez.

```bash
ollama --version          # sunucu kurulu mu
ollama serve              # sunucuyu başlat (genelde arka planda çalışır)
ollama list               # yerelde çekili modeller
ollama pull <model>       # kullanılacak modeli BİR KEZ çek
```

Sonra kimlikleri yapılandırmaya yazın:

```bash
H4_ENABLED=true
H4_SMALL_MODEL=<küçük model kimliği>
H4_MEDIUM_MODEL=<orta model kimliği>
```

- Model kimlikleri **yapılandırmadan** gelir; kodda sabit model adı YOKTUR.
- `ollama list` çıktısındaki tam kimlik kullanılmalıdır; aksi halde
  `MODEL_UNAVAILABLE`.
- Slot ataması boşsa (`""`) o slot uygun değildir; gerekiyorsa zincir
  `NO_ELIGIBLE_MODEL` ile durur.

---

## 4. Girdi bütçeleri model bağlamı DEĞİLDİR

`H4_SMALL_INPUT_CHARS` / `H4_MEDIUM_INPUT_CHARS` **muhafazakâr yönlendirme
güvenlik bütçeleridir**, modelin gerçek bağlam penceresi değildir. Gerçek model
bağlam penceresi bu değerlerden büyük olabilir; bütçe bilerek dar tutulur ki
yerel küçük modelin gecikmesi ve bellek kullanımı öngörülebilir kalsın.

```text
girdi ≤ small bütçesi        → local-small denenir
girdi > small, ≤ medium      → local-medium seçilir (LOCAL_SMALL_CONTEXT_EXCEEDED)
girdi > TÜM bütçeler         → CONTEXT_TOO_LARGE (sessiz kırpma YOK)
```

Bütçe aşıldığında metin **kırpılmaz, reddedilir**: sessiz kısaltma kaynağı
kaybetmiş bir çıkarıma yol açardı. `local-small` yönlendirmesi bütçe yüzünden
mümkün değilse gerekçe `LOCAL_SMALL_CONTEXT_EXCEEDED` olarak izlenir. Girdinin
üst sınırı ayrıca sert bir sözleşme sınırıdır (bkz. §8, text 2..24000).

---

## 5. Doğrulama komutları

Odaklanmış testler:

```bash
backend/.venv/bin/python -m pytest backend/tests/test_h4_models.py backend/tests/test_h4_policy.py backend/tests/test_h4_service.py backend/tests/test_h4_ollama.py backend/tests/test_agent_h4_contract.py backend/tests/test_agent_h4_transport.py -q
```

Yönlendirme eval'i (model gerekmez; sentetik girdiler):

```bash
backend/.venv/bin/python backend/scripts/h4_eval.py --routing
```

Canlı eval (yerel Ollama + çekili model + açık bayraklar gerekir):

```bash
H4_LIVE=1 H4_ENABLED=true H4_SMALL_MODEL=<model> \
  backend/.venv/bin/python backend/scripts/h4_eval.py --live

# lane/limit ile daraltma (uzun benchmark yerine hızlı doğrulama):
H4_LIVE=1 H4_ENABLED=true H4_SMALL_MODEL=<model> \
  backend/.venv/bin/python backend/scripts/h4_eval.py --live --lane classify --limit 2
```

Canlı pytest testleri (varsayılan olarak atlanır):

```bash
H4_LIVE=1 H4_ENABLED=true H4_SMALL_MODEL=<model> \
  backend/.venv/bin/python -m pytest backend/tests/test_h4_live.py -q
```

Kanonik tam koşu:

```bash
make test CO="docker compose"
```

Kapsam:

| Dosya | Ne kanıtlar |
|---|---|
| `test_h4_models.py` | İstek/yanıt modelleri, sürümlü çıkarım sözleşmeleri, doğrulama alt kodları |
| `test_h4_policy.py` | Lane politikası, reddedilen lane'ler, yönlendirme gerekçe kodları, deneme tavanı |
| `test_h4_service.py` | Uçtan uca servis akışı, sınırlar, `needs_escalation`, doğrulama zinciri |
| `test_h4_ollama.py` | Yerel HTTP istemcisi, loopback dayatması, zaman aşımı, sağlayıcı hataları |
| `test_agent_h4_contract.py` | Yüzey (26 araç), `forkos_local_cognition` anotasyonları, hata kodları |
| `test_agent_h4_transport.py` | Gerçek `/mcp`: şema, değişmezlik, gizli bağlam yok, kaynak metin loglanmaz |
| `test_h4_live.py` | Gerçek yerel modelle üç lane (yalnız `H4_LIVE=1` ile koşar) |

Yüzey toplamı: **H0=8, H1=11, H2=5, H3=1, H4=1 → 26 araç**.

---

## 6. Gizlilik sınırı — dürüst ifade

```text
H4 model çağrısı yalnız loopback üzerindedir: 0 dış ağ, 0 uzak API.
```

Ancak **"Hermes uçtan uca yereldir" DENMEZ**. Hermes'in kendi modeli uzak
olabilir ve H4'e gönderdiği metni zaten görmüş olabilir; H4 yalnızca yerel
çıkarım katmanının sınırını daraltır, tüm hattı yerelleştirmez.

Ek olarak:

- H4 sunucu tarafı hiçbir uzak model/API çağırmaz.
- Başarısız yerel zincir `needs_escalation` döner; **arka planda buluta
  düşmez**. Yükseltme kararı çağırana bırakılır.
- "Uçtan uca yerel" iddiası ancak Hermes'in model çalıştırma yolu da
  yerelleştikten sonra yapılabilir.

---

## 7. Sorun giderme

| Belirti | Neden | Yapılacak |
|---|---|---|
| `H4_DISABLED` | `H4_ENABLED=false` (varsayılan) | Yerel model yolunu istiyorsan `H4_ENABLED=true` yap |
| `INVALID_LANE` | Lane `classify`/`structured_extract`/`query_rewrite` dışında (`rerank`, `compress`, `reason`, `chat`, `answer`, `plan`) | Aktif üç lane'den birini seç; reddedilenler H4.x/H5 araştırmasıdır |
| `INVALID_ARGUMENT` | Alan sınırı ihlali (boş text, >24000 karakter, tekil olmayan label, boş protected_term…) | Girdiyi §8'deki aralıklara çek; kırpma YOK |
| `INVALID_LOCAL_MODEL_ENDPOINT` | `H4_OLLAMA_BASE_URL` loopback dışı | `localhost`/`127.0.0.1`/`::1` kullan |
| `MODEL_PROVIDER_UNAVAILABLE` | Yerel Ollama sunucusuna bağlanılamadı | `ollama serve` çalışıyor mu; `H4_OLLAMA_BASE_URL` doğru mu |
| `MODEL_UNAVAILABLE` | Çekili model yok / kimlik yanlış | `ollama pull <model>`; kimliği `ollama list` ile doğrula |
| `NO_ELIGIBLE_MODEL` | Hiçbir slot uygun değil (atama boş veya sınırlar dışı) | `H4_SMALL_MODEL`/`H4_MEDIUM_MODEL` ata |
| `CONTEXT_TOO_LARGE` | Girdi TÜM yapılandırılmış bütçeleri aştı | Girdiyi küçült; bütçeyi büyütmek yerine çağrıyı böl |
| `VALIDATION_FAILED` | Model çıktısı doğrulanamadı; alt kod nedeni söyler | Alt koda bak: `INVALID_MODEL_JSON`, `OUTPUT_SCHEMA_MISMATCH`, `INVALID_CLASS_LABEL`, `SOURCE_EXCERPT_NOT_FOUND`, `INVALID_DATE`, `INVALID_TIME`, `PROTECTED_TERM_LOST`, `OUTPUT_TOO_LARGE` |
| `LOCAL_CAPABILITY_UNAVAILABLE` | Yerel çıkarım yolu kullanılamıyor | Yapılandırmayı ve sunucuyu doğrula; gerekirse çağıran taraf yükseltme kararı versin |
| `needs_escalation` durumu | Yerel zincir tükendi (small→medium denemeleri başarısız) | Çağıran yükseltmeye karar verir; H4 kendiliğinden buluta düşmez |

Deneme tavanı yukarı yapışkandır: `local-small` tükendikten sonra
`local-medium` denenir, geri dönülmez (`small→medium→small` YASAK).

---

## 8. Sınırların tek listesi

```text
text                  2-24000 karakter          (şema + çalışma zamanı)
labels                2-20 adet, tekil          (her biri 1-80)
classification_goal   ≤ 300 karakter
protected_terms       ≤ 20 adet                 (her biri 1-100)
yeniden yazılan sorgu 2-200 karakter
çıkarım öğesi tavanı  ≤ 80
source_excerpt        ≤ 500 karakter
title                 ≤ 200 karakter
date_text             ≤ 120 karakter
deneme tavanı         local-small=2, local-medium=1, toplam ≤ 3 model çağrısı
```

Çıkarım sözleşmeleri sürümlüdür: `academic_calendar_v1`, `weekly_schedule_v1`,
`deadline_candidates_v1`. Model slotları: `local-small`, `local-medium`.
Yürütme sınırı: `local_loopback`.

---

## 9. İlgili belgeler

- [H4 Yerel Biliş](h4-local-cognition.md) — mimari, lane'ler, yönlendirme.
- [H4 Araç Sözleşmesi](h4-tool-contract.md) — imza, modeller, hata kodları.
- [H4 Yönlendirme Eval'i](evals/h4-routing.yaml) — beklenen yönlendirme kararları.
- [H3 Kanıt Getirme](h3-retrieval-evidence.md) — H4'ün üzerine oturduğu kanıt katmanı.
- [Yol Haritası](roadmap.md) — H4.1/H4.x araştırma sıralaması.
