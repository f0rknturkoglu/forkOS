# A5.1 — Yerel Context Judge (jevmlx)

## Amaç ve sınır

`forkos_context_judge` tek yeni salt-okunur MCP aracıdır. Aynı girdiyle mevcut, model içermeyen H3 `retrieve_evidence()` çağrısını içeriden yapar; istemci keyfî kanıt metni gönderemez. A5 yalnızca H3'ün uygun bulduğu ≤15 öğeyi değerlendirir. Orijinal `EvidenceBundle` değişmeden yanıtın içindedir. A5.1 v1 hiçbir kanıtı atmaz: `baseline_order`, `advisory_order` ve `effective_order` aynı kimlik kümesini taşır. Anlamsal sınıf, doğruluk veya yetki değildir; yazma/supersession olamaz.

## Çalışma topolojisi ve konfigürasyon

forkOS backend yalnız yapılandırılmış loopback HTTP üzerinden **ayrı** jevmlx daemon'ına gider. forkOS jevmlx/MLX/model paketlerini kendi bağımlılığına eklemez, daemon başlatmaz ve model indirmez. Doğrulanan upstream pin `bnsd55/jevmlx@011a23bc44fe78259c95f4949687d119e83ea262`; `fast` alias'ı `mlx-community/Qwen2.5-3B-Instruct-4bit` modelini kullanır. Sağlayıcı değiştirilirse A5 sözleşmesi ve frozen fixture'lar değişmez.

- `A5_CONTEXT_MODE=off` varsayılan. `shadow`, `assist`, `on` açıkça seçilebilir.
- Yerel host API varsayılanı `A5_JEVMLX_BASE_URL=http://127.0.0.1:8000`dır. Canonical Compose API container'ı `http://host.docker.internal:8000` varsayımını ve yalnız Compose tarafından açılan `A5_HOST_BRIDGE_ENABLED=1` kapısını taşır. Bu özel host köprüsü dışında LAN IP'si/genel hostname kabul edilmez; kullanıcı bilgisi/yol/query reddedilir.
- `A5_CONTEXT_TIMEOUT_SECONDS=1.5` varsayılan; uygulama en fazla 5 saniyeye sınırlar.
- Yalnız `/ready` kullanılabilirlik kanıtıdır (`/health` yalnız canlılık). Tek H3 paketi için **tek** `/decide` isteği gönderilir. HTTP yönlendirmeleri ve ortam proxy'leri kapalıdır; uzak fallback yoktur.

Örnek bağımsız kurulum: `uv tool install 'git+https://github.com/bnsd55/jevmlx@011a23bc44fe78259c95f4949687d119e83ea262'`; ardından Apple Silicon host'ta `jevmlx serve --model fast --host 127.0.0.1 --port 8000`. Host'ta çalışan API loopback'e, Compose API ise Docker'ın yerel makine için ayırdığı `host.docker.internal` özel adına gider. Bu Mac'teki OrbStack Compose topolojisinde loopback'e bağlı daemon'a erişim canlı doğrulandı; Docker Desktop kurulu olmadığından onun host ağı canlı doğrulanamadı. Docker Desktop'ta bu adın host iç IP'sine çözülmesi, yalnız `127.0.0.1` adresine bağlı bir servise erişimi garanti etmez; bu kombinasyon Docker Desktop üzerinde ayrıca kanıtlanmadan A5.1 kapanmış sayılmaz. Daemon'ı LAN'a açmak veya `0.0.0.0` adresine bağlamak bu kılavuzun parçası değildir.

## Rollout ve sıralama

| Mod | Sağlayıcı | Önerilen sıra | Etkin sıra |
|---|---|---|---|
| `off` | çağrılmaz | H3 | H3 |
| `shadow` | çağrılır | anlamsal | H3 |
| `assist` | çağrılır | anlamsal | anlamsal |
| `on` | çağrılır | anlamsal | anlamsal; ek yetki yok |

Sıra yalnız sınıflardan türetilir: `essential > useful > weak > uncertain > irrelevant`, ardından `unique > uncertain > redundant`, ardından orijinal H3 konumu. Ham olasılık sıralama anahtarı değildir. İki alanın min olasılık/marjı varsa yalnız tanı metadata'sı olarak taşınır; kalibre edilmediği ve objektif doğruluk olasılığı olmadığı açıkça belirtilir.

## Anlık görüntü ve başarısızlık

H3, kanıtı ürettiği anda kaynak projeksiyonunun içerik özetini yalnız istek ömründe taşır; bu özel alan H3 MCP/OpenAPI çıktısına girmez ve bütçe kırpması boyunca korunur. İlk snapshot aynı projeksiyonu yeniden okuyup **H3 kanıtı ↔ kaynak sürümü** bağını doğrular; başarısızsa modele hiç gidilmez. İkinci snapshot **ilk sürüm ↔ değerlendirme sonrası sürüm** kararlılığını doğrular; fark varsa yargı `stale` olur. Entity için proje alt alanları dâhil tüm H3 projeksiyon satırları, event için append-only satır ve H3'te görünen değişebilir entity başlığı, Vault için H3'ün okuduğu normalize edilmiş kaynak satırları ve başlık içerik-türetilmiş SHA-256 ile bağlanır. Kaybolan/değişen ya da doğrulanamayan bir kaynak varsa H3 sırası korunur; eksik öğe gizlice çıkarılmaz.

Başarılı verdict'teki `metadata.model_id`, varsa jevmlx `/ready` yanıtının gerçek `model` alanından gelir. Sağlayıcı örneği istek başına kurulur; readiness yenilemesinde eski kimlik temizlenir. Alan yoksa `None` kalır, model adı uydurulmaz.

`off`, boş paket, daemon yok/ısınma, timeout, 429, 413, hatalı JSON/enum, eksik alan veya bayat kaynak durumlarında orijinal H3 paketi ve H3 etkin sırası döner. Sınırlı makine nedenleri kullanılır; ham HTTP gövdesi, mutlak yol veya exception mesajı dışa çıkmaz. Tekrar deneme ve `Retry-After` beklemesi yoktur.

Kanıt alıntıları güvenilmeyen veridir. Model girdisi yalnız sorgu, slot, kaynak tipi, sınırlı başlık ve alıntıdır; kaynak içindeki komutlar uygulanmaz. Yerel sağlayıcıda `remote_allowed=false` çalışmayı engellemez. Uzak sağlayıcı ve bulut fallback uygulanmadı.

## Canlı doğrulama ve dürüst operasyon önerisi

Apple Silicon host'ta pinli `fast` daemon `/ready=200` ile doğrulandı. A5.1.1 frozen `context-v1` yeniden koşusunda 8 uygun vaka, 11 öğe: yararlılık **6/11**, yinelenme **7/11**, geçersiz yanıt **0**. Sekiz sağlayıcı isteğinin medyanı **468 ms**, en yükseği **721 ms**. Son kodla izole Compose API → H3 → host-local jevmlx SHADOW isteği 1 kanıtla **687 ms** sürdü ve verdict `model_id=fast` taşıdı. Ölçümler küçük örneklemdir; genel p95 iddiası değildir.

Yüksek-değerli gözlem: leksik benzerlik tuzağı `irrelevant` kaldı, güncel entity eski event'in önüne geçti. Ancak tekrar eden kopya `redundant` yerine `unique`, belirsiz sorgu `uncertain` yerine `weak` çıktı. Frozen beklentiler değiştirilmedi ve eşik/prompt hilesi eklenmedi. **Operasyon önerisi şimdilik `shadow`**; `assist/on` teknik modları kalite dogfooding'i olmadan açmayın. Varsayılan `off`tur.

Canlı evaluator: `cd backend && A5_CONTEXT_TIMEOUT_SECONDS=5 .venv/bin/python scripts/eval_a5_context.py`. Normal pytest model gerektirmez; sentetik uçtan uca test yalnız `A5_CONTEXT_LIVE=1` ile açılır.

## Ertelenenler

A5.2 Memory Judge, A5.3 Answer Evidence Judge, otomatik yanıt engelleme, kalıcı yargı telemetrisi, frontend UI, model süreç yönetimi ve kanıt filtreleme/sıkıştırma yoktur. GitHub Actions, kullanıcının kota tercihi nedeniyle kapalı kalır; bu faz yalnız yerel kapılardan doğrulanır.
