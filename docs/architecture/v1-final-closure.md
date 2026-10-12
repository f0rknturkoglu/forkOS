# forkOS V1 — final kapanış kanıtı

Tarih: **12 Ekim 2026**. Audit başlangıcı `3985c175e6fd50eacbde45607a678a2833c7b708`,
branch `main`, başlangıç çalışma ağacı temiz. Önceki kapsam/preflight/Goal Studio
QA sayıları tarihsel kalır. Bu belge bu çalışmanın yerel doğrulama kaydıdır.
Test edilen uygulama commit'i `cb021ae`; bunu izleyen dokümantasyon/metadata/hijyen
ve kanıt commit'leri aynı çalışma zincirindedir. Nihai HEAD kendini referanslayamaz;
commit zinciri ve push edilen tam HEAD teslim cevabında/Git geçmişinde verilir.
Son kullanıcı kararı: **Codex OAuth / Nous canlı doğrulaması sonraya ertelendi**.
Yerel ürün düzeltmeleri tamamlanır; bu iki hesap akışı teslimi bekletmez.

## A. Seçilen audit maddeleri

| Audit | Durum | Uygulanan değişiklik | Kanıt |
|---|---|---|---|
| #2 | Kapandı | Tek güncel head 0080; 0079 predecessor; no-op downgrade pointer/şema ayrımı | `test_v1_migration_roundtrip.py`, `test_migrations.py`, gerçek PG16 clean install |
| #3 | Kapandı | Feed silme ve yalnız ilgili bundle UUID'lerini temizleme tek transaction; boş seçki korunur; CAS kontrollü repair | `test_rss_transaction_integrity.py`, gerçek API delete → UI seçki düzenleme/kaydetme |
| #4 | Kod ve yerel runtime kapandı; iki bulut canlı gate'i kullanıcı kararıyla ertelendi | custom/openai-codex/nous allowlist; standalone named-profile /v1; authenticated host bridge; effective tools=0; backend cloud consent; gerçek runtime kökeni | `test_goal_studio_providers.py`, canlı yerel draft/approval/Goal/KR ve gerçek browser sohbeti; aşağıdaki bulut sınırları |
| #6 | Kapandı | OPML önce tam validate; 200 feed/30s bütçe; ağ probe'u yok; tek commit/rollback; refresh commit sonrası | RSS transaction testleri; gerçek file chooser → iki sentetik abonelik |
| #7 | Kapandı | Visit/skip ve canonical action evidence ayrı; orphan Entity kanıt değildir; mevcut kayıt doğru etiketlenir | Product experience/onboarding testleri; browser “Mevcut kayıt doğrulandı” |
| #8 | Kapandı | RSS anında kaydolur; Vazgeç yalnız kaydedilmemiş Feed tercihlerini iptal eder; pending/repair/CAS durumları korunur | Onboarding frontend testleri; browser add RSS → Cancel → RSS durur, GitHub tercihi kaydolmaz |
| #9 | Kapandı | Starter sabitleri, helper ve startup no-op kaldırıldı | Gerçek lifespan testleri; eski `rss.starter_feeds.v1` kayıt anahtarı uyumluluk için durur |
| #10 | Kapandı | H6 7 rule, H7 10 operation, MCP 37 tool; API title forkOS; özel frontend paket adı; bileşen version politikası | Gerçek MCP list_tools=37, typed operation/rule registry, OpenAPI/check/build |
| #11 | Kapandı | Tarihsel QA arşivi, kullanılmayan Notes screenshot'ı, portable doc linkleri, 12 kullanılmayan public export temizliği | Referans taraması, dead-export gate=1/10, Markdown link kontrolü |

## B. Gerçek yerel doğrulama

| Gate | Passed | Failed | Skipped / kapsam |
|---|---:|---:|---|
| Backend tam pytest, PostgreSQL 16 | **2727** | **0** | **43** |
| Frontend tam Vitest, 156 dosya | **1048** | **0** | **0** |
| Extension Node | **27** | **0** | **0**; extension davranışı/sürümü değiştirilmedi |
| Git metadata bağlı kaynak gizliliği ek koşusu | **10** | **0** | **0**; tam suite'in iki Git skip'i ayrıca doğrulandı |
| Migration + export/restore roundtrip | **1** | **0** | **0**; tam backend suite içinde |
| Canlı yerel structured Goal Studio smoke | **1** | **0** | İki bulut provider canlı inference koşusu yapılmadı |
| Gerçek browser sohbeti | **1** | **0** | Araçsız yerel model; test DB; final cevap + köken + resume |

Bu sayıların üst üste binen alt-suite'leri toplama. Son backend full run:
`2727 passed, 43 skipped in 180.48s`; frontend full run:
`1048 passed`, extension `27 pass`.

Full suite sonrasındaki dar son düzeltmeler ayrıca doğrulandı: hatalı porttaki
secret'ın hata mesajına taşınmaması regresyonu dahil hedef/Hermes **65 passed**;
Goal ekranındaki iki sibling bileşenin aynı React key'ini kullanması düzeltildi,
Goals/Goal Studio/onboarding **23 passed**. Typecheck, Prettier, Ruff lint ve
iki değişen Python dosyasının format kontrolü tekrar geçti. Bunlar full suite
sayısına eklenerek yeni bir full run sonucu gibi gösterilmez.

43 backend skip'in dağılımı: 34 kaynak/kariyer live opt-in veya vendor/Node ortam
kapısı, 3 A5 live, 3 H4 live, 2 Git metadata, 1 Vault permission düşürme testi.
Kariyer acquisition testleri açılmadı; Git metadata testleri tam repo salt okunur
mount ile ayrıca geçti. Root test container'ında dosya izinlerini düşürme vakası
skip kaldı. Fixture/auth testleri gerçek OAuth hesabı testi değildir.

Ek yerel gate'ler: tüm backend Ruff lint geçti; kapsam içindeki **22** Python
dosyası Ruff format check geçti; TypeScript typecheck, API runtime export +
generated TS check, production build/bundle guard, design-system/invalidation
ve registry testleri geçti. Endpoint coverage **1** referanssız uç (eşik 3),
mevcut kapsam dışı career-ops doctor; yeni repair/consent uçları UI'de tüketilir.
Dead export **1** (eşik 10), kapsam dışı mevcut `KIND_LABELS`; 12 gereksiz export
private yapıldı. `npm audit`: **0 vulnerability**; `pip check`: broken requirement yok.
`git diff --check` ve göreve ait Markdown relative linkleri kontrol edildi.

İlk full backend koşusundaki bir process-tree failure, `sleep` PID1'inin orphan
child'ı reap etmemesinden kaynaklandı. `compose.test.yaml` **init:true** ile
izole ortam düzeltildi; runner kodu/testi değiştirilmedi. Son full run'da geçti.

### Browser / erişilebilirlik kanıtı

İzole `forkos_browser_test` + PostgreSQL16, gerçek API ve frontend; localhost
IPv6 dev listener 5173, yalnız 127.0.0.1:18787 test API. Test API'nin kariyer
catch-up/maintenance başlangıcı harness içinde durduruldu; iş endpoint'leri ve
Hermes taşıması gerçektir. Kişisel DB hiçbir UI fixture'ına dönüşmedi.

Doğrulanan **9 akış**: Welcome dismiss; Yeni hedef Enter/Space aç-kapa; manuel
Goal kaydı; gerçek Hermes kapalıyken manuel Goal; RSS add/Cancel; bundle save,
API üzerinden son RSS delete, boş bundle rename/save; OPML file chooser/import;
tutorial reset/domain kayıtlarını koruma ve mevcut canonical evidence etiketi;
gerçek sohbet, final model kökeni ve Son görüşme resume.

Responsive: **390×844, 768×1024, 1440×900**; üç viewport'ta yatay document taşması
yok. Açık/koyu tema ve loading/empty/offline/error/ready durumları görüldü;
session gönderme ikonu erişilebilir ad aldı. Geçici viewport/tema geri alındı.
**Gerçek 200% browser zoom ve reduced-motion media emülasyonu doğrulanmadı**:
IAB yalnız visibility/viewport yetenekleri sunuyor. Bunları viewport testine
veya fixture'a eşdeğer sayma; manuel erişilebilirlik gate'i açık kalır.
Görseller yerel/ignore edilen `.codex/artifacts/forkos-ui-polish/v1-local-ready-*.png`
kanıtlarıdır; repo'ya kişisel screenshot eklenmedi.

## C. Temizlik ve koruma

- Ölü RSS starter runtime kodu kaldırıldı; tarihsel Setting marker silinmedi.
- Root `design-qa.md`, `docs/archive/qa/focus-garden-design-qa.md` içine tarihsel
  Bahçe QA olarak taşındı. Emekli tasarım güncel release kanıtı gibi gösterilmez.
- `docs/assets/screenshots/notes-workspace.jpg` kaldırıldı: takip edilen kaynak
  ve belgelerde referansı yok; Notes bağımsız UI'si emeklidir.
- Public teknoloji ikonları ve LICENSE, extension ikonları, migration'lar,
  Notes/Media/Finance restore metadata'sı, ADR/superpowers geçmişi korunur.
- Makineye özel altı `file:///Users/...` belge bağı göreli spec bağlantısı oldu.
- Geçici test container/PG16 tmpfs/network/image, browser test listener/tab ve
  bu çalışmanın 11 `/tmp/forkos-v1-closure-*` dosyası temizlendi.
- İstenen normal forkOS/OrbStack/Obsidian/Hermes Desktop açık kalır. Yeni ayrı
  araçsız Goal Studio daemon/model profili çalışan ürün konfigürasyonu olarak
  kalır; credential ve durable history dosyaları silinmez.

## D. Hermes gerçek durumu

| Mod | Konfigürasyon | Fixture / backend gate | Gerçek inference | Kalan adım |
|---|---|---|---|---|
| local_custom | Ayrı fresh profile; custom / Qwen3.5-9B-Q4_K_M; 65536 context; 127.0.0.1:18435 model ve :8643 standalone API | ready/offline/missing model, auth/topology/tools/schema/runtime mismatch, idempotency/stale/approval | **Evet**: API → gerçek draft → revision → explicit approval → canonical Goal/KR; aynı UUID replay ve onay retry; browser düz sohbet/resume | Yok; normal API host_bridge ready ve tools_verified=true |
| codex_oauth | Backend allowlist canonical **openai-codex**; hazır profile seçim kuralları | default-off consent/CAS/binding/revoke/race, successful mocked turn, auth/provider failure | **Hayır** | Kullanıcı ayrı Hermes profilinde resmi auth/model akışını tamamlamalı, config'i seçmeli ve forkOS'ta cloud opt-in vermeli |
| nous_portal | Backend allowlist canonical **nous**; hazır profile seçim kuralları | Aynı consent/provider/transport/actual-runtime gates | **Hayır** | Kullanıcı ayrı profilde Nous auth/model akışını tamamlamalı, config'i seçmeli ve cloud opt-in vermeli |

Kurulu Hermes `0.21.6+763.g1fd1827`; API base version `0.21.6`, kaynak
`1fd182772671`. `/v1/models` Hermes alias'ı değil, run'ın gerçek runtime pair'i
cevap kökeni sayılır. Effective toolsets canlı API'de **0**. Bu sürümde no-skills
essential reference dosyasını yine seed eder; skill araçları olmayınca index
model prompt'una girmez. Named daemon için standalone shim gerekir; değişen
API sürümü/config güvenli varsayılmaz.

Cloud izni backend'de purpose/profile/provider/model/config/endpoint/key digest
bağıyla default-off'tur. Revoke ve HTTP submission aynı consent lock sırasına
uyar; grant bekleyen frozen tur yeni provider'a taşınmaz. Genel Settings PUT ve
backup restore ile grant açılamaz. Health/readiness OAuth auth başarısı değildir.
Fresh profilde OAuth auth.json yok; kişisel root/Codex credential'ı taşınmadı,
login veya ücretli/cloud inference tetiklenmedi. İki gerçek bulut hesabı ve
Nous gateway effective tools doğrulaması **kullanıcı kararıyla sonraki çalışmaya
ertelendi**; bu teslim için hesap girişi veya onay beklenmez.

İlk canlı denemede 16K context Hermes tarafından reddedildi; 65536 ile düzeltildi.
Modelin `source_config:null` / `baseline_value:null` taslakları fail-closed kaldı;
prompt'ta doğru canonical default örneği eklendi. Düz final cevap yalnız sohbet
olabilir; bozuk yapılandırılmış JSON, reasoning/tool payload ve yanlış köken
canonical kayıt yazamaz. Geçerli proposal ayrıca dry-run/revision/approval ister.

Kurulum/teknik sınırlar: [Goal Studio runtime](../hermes/goal-studio-runtime.md),
[Goal Studio mimarisi](hermes-goal-studio-extension-v1.md),
[migration runbook](../../backend/alembic/README.md).

## E. Release gate

**V1 CLOSURE PARTIAL — BLOCKERS REMAIN**

İstenen yerel kod düzeltmeleri, regresyonlar, runtime ve temizlik tamamlandı.
Gerçek Codex/Nous account runtime doğrulaması kullanıcı kararıyla ertelendi;
yerel teslim için blokaj değildir. Kapsayıcı V1 release sertifikasyonu için
200% zoom/reduced-motion manuel kontrolü doğrulanmadığından gate partial kalır.
Bu kontroller fixture/viewport sonuçlarıyla kapanmış sayılmaz. CI ayrıca pending
ve açıkça kapsam dışıdır; tek başına bu kararı oluşturmaz.

## F. Git ve sınırlar

Anlamlı zincir: RSS atomicity → tutorial/feed semantiği → Hermes provider/consent
→ documentation/metadata/hygiene → final evidence. Normal push; force/reset yok.
`.github/workflows/*`, kariyer acquisition/catalog/scheduler/catch-up/
`automation.opportunity.*`, tarihsel migration ve extension kodları değiştirilmedi.
Normal API overlay'e alınırken **yalnız HERMES_GOAL_* env değerleri değişti**;
kişisel DB, kaynak tercihleri, Vault ve default Hermes model ayarı korunur.

GitHub Actions ayarı etkin bırakıldı, workflow dispatch/enable yapılmadı. Push'un
CI tetiklememesi için son commit mesajlarında `[skip ci]` kullanılır; repository
workflow'u yalnız push/pull_request olaylarını dinler.
[GitHub'un skip davranışı](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs).
