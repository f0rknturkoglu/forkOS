# Goal Studio — sağlayıcı, izin ve yerel çalışma sözleşmesi

Güncelleme: 12 Ekim 2026. Bu profil **Brain Interface MCP istemcisinden ayrıdır**.
Goal Studio yalnız konuşma/tipli taslak üretir; kayıt yazma mevcut açık revizyon onayından geçer.

## Doğrulanmış sürüm ve topoloji

Hermes `0.21.6` API sözleşmesi; kurulu kaynak `1fd182772671`.
Tek named-profile listener: `forkos-goal-studio`, `gateway.standalone: true`,
`gateway.multiplex_profiles: false`, **127.0.0.1:8643**, normal `/v1/...` uçları.
`/p/<profile>` multiplex prefix'i bu modda reddedilir. Başka sürüm/şema sessizce kabul edilmez.

Native forkOS API aynı host'ta `HERMES_GOAL_TOPOLOGY=native` ve
`HERMES_GOAL_BASE_URL=http://127.0.0.1:8643` kullanır. macOS OrbStack API için
`compose.hermes-goal.yaml`, sabit `host.docker.internal:8643` hedefi ve Bearer auth
kullanır. Bu köprü host loopback'e ulaşabilmelidir; daemon/model LAN'a açılmaz.
Başka Docker/Podman motorunda köprü çalışmazsa **unavailable** kalır; `0.0.0.0` çözüm değildir.
Mevcut web/API/DB portları değişmez.

## Ayrı profil kurulumu

Yeni kurulum, mevcut kişisel profili klonlamadan:

```bash
python3 scripts/hermes_goal_runtime.py init
python3 scripts/hermes_goal_runtime.py start
python3 scripts/hermes_goal_runtime.py status
```

`init` var olan profile yazmayı reddeder. Resmî `hermes profile create --no-skills
--no-alias` ve repo YAML'i kullanılır; yeni ayrı API/model anahtarları 0600 dosyalara
yazılır. Model otomatik indirilmez. Doğrulanan yerel kurulum mevcut
`~/.hermes/models/Qwen3.5-9B-Q4_K_M.gguf` ve
`~/.hermes/tools/llamacpp-metal-11370-darwin-arm64/llama-server` gerektirir.
Hermes en az 64K context istediğinden sunucu **65536**, tek slot, reasoning off,
127.0.0.1:18435 ve ayrı `--api-key-file` kullanır. Kişisel 18434 sunucusuna/anahtarına dokunmaz.

Hermes bu sürümde `--no-skills` ile bile kendi essential reference skill'ini
seed eder. `agent/system_prompt.py` skill araçları yoksa skill index'i yüklemez.
`platform_toolsets.api_server: []` ve canlı `/v1/toolsets` doğrulaması tüm etkin
araçları kapatır; dosya/shell/browser/skill/delegation/cron/MCP/Nous tool erişimi yoktur.
Hooks/plugin dosyaları, dolu cron listesi, MCP/fallback/model routing, otomatik memory,
curator/background review ve dış login devralma reddedilir.

Compose (yerel anahtar dosyası sadece backend ortamına okunur):

```bash
export HERMES_GOAL_PROFILE_DIR="$HOME/.hermes/profiles/forkos-goal-studio"
docker compose -f compose.yaml -f compose.dev.yaml -f compose.hermes-goal.yaml up -d api web
```

Config/hooks/plugins/cron salt okunur bağlanır; profil `.env`, OAuth `auth.json`,
kişisel hafıza ve Vault bağlanmaz. `forkos` launcher bu kendisine ait profili
bulursa overlay'i ve başlangıç checklist'ini ekler. `forkos stop` önce yalnız
PID + process birth eşleşmesiyle bu daemon/modeli SIGTERM ile kapatır;
zorla öldürmez, profil/verileri korur. Bağımsız kapatma:
`python3 scripts/hermes_goal_runtime.py stop`.

## Kapalı sağlayıcı politikası

| forkOS modu | Hermes canonical provider | Yerleşim | Gereken |
|---|---|---|---|
| local_custom | custom | yerel | loopback `/v1` model, ayrı model key |
| codex_oauth | openai-codex | bulut | bu ayrı Hermes profilinde kullanıcı OAuth login'i |
| nous_portal | nous | bulut | bu ayrı Hermes profilinde kullanıcı Nous login'i |

Browser provider/model/URL/key belirleyemez. Operatör YAML'de `model.provider`
ve `model.default` değerini düzenler; OAuth modunda `model.base_url` kaldırılır.
Resmî Hermes `hermes -p forkos-goal-studio model` / `auth add` akışı kullanıcı
kontrolündedir. `auth.adopt_external_logins: false` korunmalı; kişisel root/Codex
credential kopyalanmaz. `hermes login --provider` bu sürümde deprecated'dır ve
provider parametresini yok sayar; kurulum için önerilmez.
Değişiklikten sonra ayrı daemon yeniden başlatılmalıdır.

**Bulut varsayılan kapalıdır.** UI, dış sağlayıcıya yalnız seçili bounded bağlam
özeti ve mesaj gönderileceğini bildirir. Açık checkbox + İzni kaydet, backend'de
CAS ile `hermes.goal_studio.consent.v1` kaydını yazar. İzin amaç (`goal_studio`),
canonical provider, model, config, profil, endpoint ve API key digest'ine bağlıdır.
Değişiklik eski izni geçersiz kılar. Revocation kilidi yeni HTTP run gönderimiyle
seri olur. Eski frozen UUID yeni sağlayıcıya gönderilemez; replay izin gerektirir.
Mevcut run GET/stop/reconcile izni tekrar inference değildir ve grant gerektirmez.
Yedek/export bu yetkiyi taşımaz; restore ile bulut izni verilemez. Genel Settings
PUT bu anahtarı yazamaz. Revoke bozuk profille bile backend'de mümkündür.

Bağlantı readiness **OAuth auth/inference başarısı değildir**. Auth expired/
provider unavailable koşuda güvenli hata verir. UI, yapılandırılmış modeli ayrı,
son cevabın doğrulanmış `runtime.provider/model` kökenini ayrı gösterir.
Hermes `/v1/models` alias'ı gerçek model diye gösterilmez. Veri saklama için
sağlayıcının kendi kuralları geçerlidir; local-only güvencesi buluta verilmez.

## Run, SSE ve onay

Health + authenticated detailed readiness + capabilities + durable idempotency
(en az 86400 saniye) + effective tools=0 doğrulanır. Toolsets sürüm kontrollü
array veya `object:list/platform:api_server/data` wrapper'ı olabilir; bilinmeyen
şema fail-closed'dur. Local model `/v1/models` kontrolü ayrı kimlikle yapılır.

Aynı UUID aynı frozen input/provider/model/instructions ile replay edilir;
farklı mesaj/policy 409'dur. 23 saatten eski belirsiz tur otomatik gönderilmez.
Gönderim öncesi engel `delivery_blocked`; HTTP sonucu belirsizse `unknown_delivery`.
SSE yalnız sabit lifecycle progress taşır: ham delta, interim commentary,
reasoning veya tool payload gösterilmez. Final poll sonucu gerçek runtime
kökeniyle doğrulanır. Normal düz final yanıt yalnız bounded sohbet sayılır; taslak veya onay oluşturmaz.
Yapılandırılmış çıktı kapalı discussion/proposal JSON ile doğrulanır. Hatalı model JSON'u
kayda uygulanmaz ve raw çıktı UI'ye dökülmez. Kullanıcı düzeltme turu gönderebilir.

Taslak → dry-run → revizyon/fingerprint → **Bu revizyonu onayla ve uygula**
→ atomik canonical Goal/Plan/Pillar/KR/Milestone. Sohbette “onaylıyorum” yazmak
yetki değildir. Manuel Goals, Hermes olmadan kullanılabilir.

## Kanıt ve sınırlar

[Final kapanış raporu](../architecture/v1-final-closure.md) fixture ile canlı
sonuçları ayrı tutar. `scripts/test_goal_studio_live.py` yalnız `_test` DB ve
local provider ile açıkça çalıştırılır; gerçek kayıtlar kişisel DB'ye eklenmez.
Codex/Nous için otomatik login, token taşıma veya ücretli smoke yapılmaz.

Resmî referanslar: [Providers](https://hermes-agent.nousresearch.com/docs/integrations/providers),
[Nous Portal](https://hermes-agent.nousresearch.com/docs/integrations/nous-portal),
[API server](https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server),
[Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration),
[CLI](https://hermes-agent.nousresearch.com/docs/reference/cli-commands).
