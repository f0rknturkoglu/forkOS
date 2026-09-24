# A5.1 — Yerel Context Judge (jevmlx)

## Amaç ve sınır

`forkos_context_judge` tek yeni salt-okunur MCP aracıdır. Aynı girdiyle mevcut, model içermeyen H3 `retrieve_evidence()` çağrısını içeriden yapar; istemci keyfî kanıt metni gönderemez. A5 yalnızca H3'ün uygun bulduğu ≤15 öğeyi değerlendirir. Orijinal `EvidenceBundle` değişmeden yanıtın içindedir. A5.1 v1 hiçbir kanıtı atmaz: `baseline_order`, `advisory_order` ve `effective_order` aynı kimlik kümesini taşır. Anlamsal sınıf, doğruluk veya yetki değildir; yazma/supersession olamaz.

## Çalışma topolojisi ve konfigürasyon

forkOS backend yalnız yapılandırılmış loopback HTTP üzerinden **ayrı** jevmlx daemon'ına gider. forkOS jevmlx/MLX/model paketlerini kendi bağımlılığına eklemez, daemon başlatmaz ve model indirmez. Doğrulanan upstream pin `bnsd55/jevmlx@011a23bc44fe78259c95f4949687d119e83ea262`; `fast` alias'ı `mlx-community/Qwen2.5-3B-Instruct-4bit` modelini kullanır. Sağlayıcı değiştirilirse A5 sözleşmesi ve frozen fixture'lar değişmez.

- `A5_CONTEXT_MODE=off` varsayılan. `shadow`, `assist`, `on` açıkça seçilebilir.
- `A5_JEVMLX_BASE_URL=http://127.0.0.1:8000` varsayılan; yalnız `localhost`, `127.0.0.1`, `[::1]`, kullanıcı bilgisi/yol/query olmadan kabul edilir.
- `A5_CONTEXT_TIMEOUT_SECONDS=1.5` varsayılan; uygulama en fazla 5 saniyeye sınırlar.
- Yalnız `/ready` kullanılabilirlik kanıtıdır (`/health` yalnız canlılık). Tek H3 paketi için **tek** `/decide` isteği gönderilir. HTTP yönlendirmeleri ve ortam proxy'leri kapalıdır; uzak fallback yoktur.

Örnek bağımsız kurulum: `uv tool install 'git+https://github.com/bnsd55/jevmlx@011a23bc44fe78259c95f4949687d119e83ea262'`; ardından Apple Silicon host'ta `jevmlx serve --model fast --host 127.0.0.1 --port 8000`. API container'ında `127.0.0.1` container'ın kendisidir; host daemon'ına erişim için ağ topolojisi ayrıca ve **loopback-only** sınırını koruyarak yapılandırılmalıdır. Bu faz Docker'dan host'a güvenlik kuralını gevşetmez.

## Rollout ve sıralama

| Mod | Sağlayıcı | Önerilen sıra | Etkin sıra |
|---|---|---|---|
| `off` | çağrılmaz | H3 | H3 |
| `shadow` | çağrılır | anlamsal | H3 |
| `assist` | çağrılır | anlamsal | anlamsal |
| `on` | çağrılır | anlamsal | anlamsal; ek yetki yok |

Sıra yalnız sınıflardan türetilir: `essential > useful > weak > uncertain > irrelevant`, ardından `unique > uncertain > redundant`, ardından orijinal H3 konumu. Ham olasılık sıralama anahtarı değildir. İki alanın min olasılık/marjı varsa yalnız tanı metadata'sı olarak taşınır; kalibre edilmediği ve objektif doğruluk olasılığı olmadığı açıkça belirtilir.

## Anlık görüntü ve başarısızlık

Sağlayıcıdan **önce** entity'nin kanonik `updated_at` + güncel H3 projeksiyon özeti, event'in kimlik ve satır özeti veya Vault dosyasının güvenli göreli yolundan SHA-256 alınır. Sağlayıcıdan **sonra** yeniden okunur. Kaybolan/değişen ya da doğrulanamayan bir kaynak varsa tüm anlamsal öneri bırakılır; eksik öğe gizlice çıkarılmaz. Güçlü eski verdict'ler `stale` durumda dışa verilmez.

`off`, boş paket, daemon yok/ısınma, timeout, 429, 413, hatalı JSON/enum, eksik alan veya bayat kaynak durumlarında orijinal H3 paketi ve H3 etkin sırası döner. Sınırlı makine nedenleri kullanılır; ham HTTP gövdesi, mutlak yol veya exception mesajı dışa çıkmaz. Tekrar deneme ve `Retry-After` beklemesi yoktur.

Kanıt alıntıları güvenilmeyen veridir. Model girdisi yalnız sorgu, slot, kaynak tipi, sınırlı başlık ve alıntıdır; kaynak içindeki komutlar uygulanmaz. Yerel sağlayıcıda `remote_allowed=false` çalışmayı engellemez. Uzak sağlayıcı ve bulut fallback uygulanmadı.

## Canlı doğrulama ve dürüst operasyon önerisi

Apple Silicon host'ta pinli `fast` daemon `/ready=200` ile doğrulandı. Frozen `context-v1` değerlendirmesinde 8 uygun vaka, 11 öğe: yararlılık **6/11**, yinelenme **7/11**, geçersiz yanıt **0**. Sekiz sağlayıcı isteğinin medyanı **550 ms**, en yükseği **767 ms**. Sentetik H3 → A5 uçtan uca isteği 2 kanıtla **806.5 ms** sürdü. Bunlar küçük örneklemdir; genel p95 iddiası değildir.

Yüksek-değerli gözlem: leksik benzerlik tuzağı `irrelevant` kaldı, güncel entity eski event'in önüne geçti. Ancak tekrar eden kopya `redundant` yerine `unique`, belirsiz sorgu `uncertain` yerine `weak` çıktı. Frozen beklentiler değiştirilmedi ve eşik/prompt hilesi eklenmedi. **Operasyon önerisi şimdilik `shadow`**; `assist/on` teknik modları kalite dogfooding'i olmadan açmayın. Varsayılan `off`tur.

Canlı evaluator: `cd backend && A5_CONTEXT_TIMEOUT_SECONDS=5 .venv/bin/python scripts/eval_a5_context.py`. Normal pytest model gerektirmez; sentetik uçtan uca test yalnız `A5_CONTEXT_LIVE=1` ile açılır.

## Ertelenenler

A5.2 Memory Judge, A5.3 Answer Evidence Judge, otomatik yanıt engelleme, kalıcı yargı telemetrisi, frontend UI, model süreç yönetimi ve kanıt filtreleme/sıkıştırma yoktur. GitHub Actions, kullanıcının kota tercihi nedeniyle kapalı kalır; bu faz yalnız yerel kapılardan doğrulanır.
