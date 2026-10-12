# forkOS V1 — pre-release readiness

12 Ekim 2026 · macOS Apple Silicon / OrbStack / Chrome.
**LOCAL RELEASE READY — CI PENDING**

Bu rapor yerel kalite kapısını belgeler; production release, tag veya CI onayı değildir.
Tarihsel `v1-final-closure.md` değiştirilmedi. [Bulgular](v1-pre-release-findings.md) ·
[Taslak notlar](../releases/v1-draft.md) · [Ölçüm matrisi](evidence/v1-viewport-matrix.json).

## A. Executive summary

- Başlangıç HEAD: `ccb2ca535e1ed381cf0e7865da6ae20df055cd2f`; başlangıç main/origin aynı, working tree temizdi.
- Doğrulanan son kod HEAD: `0253d009c773a9d71f1720e2b11ba35fb9f70838`; `[skip ci]` hardening commit serisi. Kesin teslim HEAD'i `git log -1 --format=%H` ile bulunur; raporu taşıyan commit kendi SHA'sını dosyasına yazamaz. Son kod testinden sonra yalnız dokümantasyon değişti.
- Düzeltilen bulgu: **18** (5 P0, 10 P1, 3 P2); açık keşfedilmiş P0/P1/P2: **0/0/0**.
- Yeni regression sonucu: **30** (backend +16, frontend +14). Backend başlangıç 2728/43; frontend 1048; extension 27. Tarihsel 2727 sayısı ile bu turdaki baseline karıştırılmadı.
- Yeni dependency/framework/migration yok; çekirdek Entity/Event/Link sözleşmesi ve kişisel ayarlar korunur.
- Tam suite, son frontend kod düzeltmesinden sonra yeniden çalıştırıldı: backend 2744/43, frontend 1062, extension 27.
- Değişen dosya sayısı: **38** (33 kod/test/generated + README ve 4 kanıt/rapor dosyası). `git diff --name-only ccb2ca5..HEAD` ile doğrulanır.

## B. Accessibility

| Kontrol | Sonuç | Kanıt / kapsam |
| --- | --- | --- |
| Gerçek %100/%125/%150/%200 | Geçti | Chrome native View/Zoom menüsü; CSS width 1800/1440/1200/900 ve DPR 2/2.5/3/4. %200 yalnız viewport daraltması değildir. |
| %200 kritik UI | Geçti | Sidebar/header, Capture, palette, Goal Studio, goal/plan/project/learning/cards/reader, discovery, Planner; ayrıca Career detail/evaluation ve Settings backup kontrolleri erişilebilir. |
| %400 | Smoke geçti | Native menü %400; width 450, DPR 8. Settings body 440; backup file picker açılabilir. Bütün modüllerin %400 E2E doğrulaması yapılmadı. |
| Reduced motion | Geçti | Chrome DevTools Rendering gerçek reduce, `matchMedia` true; computed transition/animation 0.00001s. Tutorial Adıma git odağı, keyboard drag/cancel ve Pomodoro geri bildirimi korundu. DevTools kapanınca emulation kaldırıldı. |
| Keyboard / focus | Geçti | Tab, Shift+Tab, Enter, Space, Escape; nested modal, alertdialog, reader, palette ve capture trap/restoration. Planner Space→Arrow→Space ve Escape cancel. Select keyboard/browser seçenekleri kullanıldı. |
| Semantik | Yerel kontroller geçti | Modal dialog/alertdialog aria-modal, icon accessible names, loading/error ve sonuç metni; confirm safe initial focus. Semantik unit testleri + gerçek DOM inspection; gerçek screen-reader uygulaması çalıştırılmadı. |
| Mobil | Geçti | 360×800 / 390×844; menü açma/navigation, palette, Goal Studio ve import formu; body overflow yok. |
| Tablet / laptop / desktop | Geçti | 768×1024 / 1280×800 / 1440×900. |
| Açık / koyu | Geçti | 17 yüzey × 5 boyut × 2 tema = **170 DOM/layout ölçümü**. Bu sayı screenshot veya bağımsız E2E test sayısı değildir. |
| High contrast / Windows / Linux font | Yapılmadı | Bu tur macOS/Chrome ile sınırlı; lisans veya ekran okuyucu sertifikası iddiası yok. |

Gövde yatay taşması görülmedi; scroll gerektiren workspace/tab yüzeyleri kendi sınırlarında kalır.
Yerel screenshot kanıtları git dışında `.codex/artifacts/v1-hardening/`: `chrome-real-200.png`,
`chrome-reduced-motion.png`, `reduced-motion-tutorial.png`, `mobile-dark-goals.png`,
`goal-studio-mobile-applied.png`, `settings-backup-real-200.png`, `backup-merge-success.png`.

Reduced motion'da spinner/skeleton'ın her zamanlama evresi ayrı elle test edilmedi;
CSS global süre kuralı, gerçek busy feedback ve animation kullanan tutorial/drag/timer doğrulandı.

## C. Test results

| Gate | Passed | Failed | Skipped / sınırlama |
| --- | --- | --- | --- |
| Backend tam | **2744** | 0 | **43**; 220.01s, son kod durumu |
| Frontend tam | **1062**, 157 dosya | 0 | 0; 19.35s |
| Extension Node | **27** | 0 | 0 |
| Migration | Clean→79→80, downgrade 80→79→80, tek head | 0 | 80 downgrade belgelenmiş no-op; tablo DROP beklentisi yok |
| Backup / restore | 14 yeni preservation regression + ikinci DB fingerprint roundtrip; mevcut suite | 0 | Güç kesilmesi / dağıtık transaction simülasyonu yok |
| Browser E2E | Aşağıdaki 14 senaryo ailesinde kritik yazma/okuma/retst | 0 açık kritik bug | CUA ile manuel akış; framework pass sayısı uydurulmadı |
| API schema / typecheck / Vite / bundle | Geçti | 0 | 87 PWA entries, 73 assets; bundle guard içinde |
| Prettier / Ruff / diff | Geçti | 0 | `ruff check app tests scripts`; `git diff --check` |
| Security / dependencies | npm audit **0**; pip check geçti; secret/ignored runtime kontrolleri geçti | 0 doğrulanmış bulgu | Python CVE veri tabanı tarayıcısı yapılandırılmamış; pentest iddiası yok |
| Vault read-only permission ek kontrol | **1** | 0 | Tam suite'de root skip; ayrı UID 1000 ile 403 testi 0.65s geçti |

Son komutlar:

```bash
# İsimleri doğrulanmış disposable container; kişisel DB değil
docker exec forkos-v1-hardening-backend pytest -q -rs
docker exec forkos-v1-hardening-backend ruff check app tests scripts
docker exec forkos-v1-hardening-backend pip check
PYTHON=/tmp/forkos-hardening-python make frontend-verify
make extension-verify
```

`PYTHON` wrapper, API schema exporter'ını mevcut Python 3.12 test container'ında çalıştırdı.
Host Apple CLT Python 3.9 ile ilk girişimde `datetime.UTC` import hatası oldu; doğru runtime
seçildikten sonra kapı geçti. Test timeout yükseltilmedi, assert gevşetilmedi, yeni skip eklenmedi.

Mevcut toleranslı warning'ler: `/api/system/career-ops/doctor` için 1 referanssız uç (eşik 3),
`KIND_LABELS` için 1 dead export (eşik 10), PendingDecisions static/dynamic import build uyarısı.
Bu çalışma bu endpoint/export'u eklemedi; mevcut gate sınırları değiştirilmedi.

### Backend skip dökümü (43)

| Grup | Adet | Gerekçe / sınıf |
| --- | --- | --- |
| sources batch2 / batch3 / LinkedIn / native batch1 | 11+10+1+6 = 28 | Explicit canlı dış ağ opt-in, acquisition görev kapsamı dışında |
| A5 answer/context/memory | 3 | Gerçek isteğe bağlı yerel model / opt-in; mevcut Goal Studio canlı testi bunların yerine sayılmadı |
| career discovery/live smoke | 3 | Pinned vendor test container'ında yok; acquisition/altyapı |
| career live validation | 2 | Gerçek ağ opt-in kapalı; kapsam dışı |
| career targeting | 1 | Pinned vendor/Node test altyapısı yok |
| H4 live | 3 | H4_LIVE opt-in kapalı, gerçek model |
| source privacy | 2 | Container'a Git metadata bağlı değil; host `git ls-files`/`git check-ignore` eşdeğeri geçti |
| Vault read-only | 1 | Root yazma izinlerini aşabiliyor; ayrı non-root tekrar **geçti** |

Canlı scraping testlerini çalıştırmak için skip'ler yapay olarak sıfırlanmadı.
Kullanıcının son onayı yalnız normal runtime açılışında mevcut kaynak çekimine izin verdi;
acquisition testlerini veya scheduler/katalog değişikliğini yetkilendirmez.

## D. Agent-discovered bugs

Tam reproduction/beklenen/gerçek/root cause/fix/regression/retst kayıtları
[V1-H001–V1-H018](v1-pre-release-findings.md) içindedir.

- P0: merge parent preservation, path/overwrite, restore I/O/uncertain commit, missing document export, self-FK chunk ordering.
- P1: nested Escape, confirmation focus/promise ownership, Capture/palette/reader focus,
  goal/plan async hydration, RSS completion/invalidation, backup import race, project milestone navigation.
- P2: Deste kopyası, internal finding kodları, kaldırılmış Pomodoro bahçesinin registry açıklaması.

Önce fail olan regression'lar düzeltmeden sonra geçti. H018 yalnız düşük etkili açıklama;
sırf metni yansıtacak yeni test eklenmedi, gerçek UI ve final registry/full suite ile doğrulandı.

## E. User-reported bugs

Bu çalışmada yeni kullanıcı bug bildirimi yok. Tarihsel annotation'lar önceki işlerin
bağlamıdır; burada yeni kapatılmış kullanıcı bug sayısı olarak yeniden sayılmadı.
Son kullanıcı yanıtı: normal API açılışında otomatik kaynak çekimi yapılabilir.
Bu izin README'de başlangıç/otomasyon davranışı notuyla ve bu raporda kayıtlıdır.

## F. Data safety

- Ayrı Compose project `forkos-v1-hardening-test`; PG16 tmpfs, dış port yok.
- `forkos_test` regression, `forkos_browser_test` UI. İkinci restore DB adı her testte
  `forkos_release_<uuid>_test`; safety guard ve finally DROP yalnız bu üretilen ada uygulanır.
- Personal `forkos_pgdata` üzerinde reset/truncate/restore/seed/export yapılmadı.
- Head `0080_goal_studio_capture`; tarihsel migration değiştirilmedi. Empty→79→80,
  80→79 belgelenmiş no-op→80 ve metadata guardrail geçti.
- İkinci DB'de tabloların sıralanmış içerik SHA256 fingerprint'leri, UUID/ilişki/event,
  KR 4/10, plan start 600/duration 45, kaynak kimliği, setting revision, historical note/
  attachment/document ve Goal Studio session/revision/capture receipt korundu.
- İlk restore sonrası fingerprint eşit; tekrar restore 0 insert, fingerprint aynı.
  Yeni `backup.restored` append-only event'leri fingerprint karşılaştırmasından bilinçli ayrılır.
- Document UUID/basename/symlink/base64 ve attachment digest doğrulanır. Mevcut farklı
  bytes overwrite edilmez. Precommit/verify/disk failure yalnız yeni dosyaları journal ile kaldırır.
- COMMIT cevabı kaybında DB commit edilmiş olabilir: tam exclusive dosyalar korunur,
  açık hata ve idempotent retry vardır. Süreç/güç kesilmesi yetim dosya bırakabilir;
  DB+dosya sistemi için dağıtık atomicity garantisi verilmez.
- Vault sentetik container tmpfs `/vault` altında. Kişisel Vault mount edilmedi;
  profile/config/hooks/plugins salt okunur bağlandı. Note replay aynı frontmatter UUID'de
  çözüldü; farklı payload 409 ve bytes değişmedi. Notlar legacy Entity/Note tablosuna yazılmaz.
- Normal `.env`, kişisel source profiles/feeds ve credential dosyaları takip edilmiyor.
  Frontend lock 568 paket license/integrity metadata içerir; extension dependency yok.
  Credential benzeri tracked eşleşmeler yalnız sentetik privacy test fixture'larıydı.

Cleanup tamamlandı: kimliği doğrulanmış bu çalışmanın API/backend/PG container'ları,
Compose network'ü, tmpfs Vault/test DB, browser tab'ları ve seçili `/tmp` fixture'ları kaldırıldı.
Project label filtresinde container/volume kalmadı; 18787 ve test 5173 listener'ı kapandı.
Screenshot kanıtları git dışında korunur; layout JSON kanıtı repo içindedir.
Normal forkOS mevcut launcher ile açıldı; health read-only kontrol edildi. Mevcut otomasyon tercihleri değiştirilmedi.

## G. Product dogfooding

| Modül / senaryo ailesi | Gerçek kullanıcı akışı / başarılı sonuç | Bulgu / kalan kapsam |
| --- | --- | --- |
| 1. Onboarding | Fresh Welcome→journey→kaynakları geç→tutorial; ilk canonical hedef/görev; checklist gerçek kanıt; reset/skip/dismiss; reload ve ikinci sekmede tema/tutorial kalıcı | Sahte completion görülmedi. Tutorial focus reduced motion'da Yeni hedef'e gider. |
| 2. Goals & Strategy | UI plan/pillar/goal/KR/milestone; KR baseline 0/current 4/target 10→%40; goal/plan edit/reopen; parent child UI kaydet/reload; Review ve canonical deep link | H006/H016 kapandı. Proje/task tamamlama KR'yi değiştirmedi. Unknown ölçüm yüzde sıfır başarı gibi sunulmadı. |
| 3. Goal Studio / Hermes | Dedicated yerel tools=0 Qwen profil; gerçek sohbet→invalid proposal açık hata/draft korunması→valid revision1→edit→approve disabled→validate revision2→explicit apply; canonical Goal+KR ve KR deep link | İki model yanıtı invalid kaldı; güvenli hata. Üçüncü geçerli proposal sonra kalıcı apply. API stale revision 409 / same UUID replay / idempotent approval ayrıca geçti. Model her istekte valid draft garantilemez. |
| 4. Todo / Planner / habits | UI görev→bugün→gelecek hafta; keyboard drag taşıma/cancel; API saat 10:00/süre45→UI carry-over19 Eki korunur; task completion; günlük rutin→yarın yeni instance; overdue 10 Eki ile plan20 Eki ayrı etiketler | H004 focus kapandı. Optimistic rollback/lost-response/race mekanizmaları suite'de; gerçek browser socket kesilmesi her mutation'da ayrı enjekte edilmedi. |
| 5. Projects | Create→task→milestone→complete; 7 event timeline; Goal link; continuity milestone→doğru owner/İşler; temporary canonical Obsidian note ve continuity path görünür | H017 kapandı. GitHub live dış yazma yapılmadı; repo boş UI ve fixture/full suite. |
| 6. Learning | Native JSON picker→preview2topic/1resource→apply→visible tree; bookmark→topic iki kez aynı resource; deep link; resource sayısı mastery değil | Duplicate bookmark resource DB count=1. Invalid import/rollback suite'de; full JSON kullanıcının kişisel dosyası değil. |
| 7. Flashcards | Deste create→kart atomic Q/A→Space flip→İyi→1 gün SRS→session complete1card | H014 kapandı. Kart varlığı goal veya topic mastery olarak sayılmadı. |
| 8. RSS / feed / bookmarks | HN/GH/HF fixture selection, Reddit off; bundle create/edit→filter2provider/remove; HF off/reload; RSS add, native OPML1added1existing, item read/save, reader full-text402words, Learning link; 503 error→retry→RSS delete explicit confirm | H012/H013 kapandı. Request log: selected HN/GH/HF/RSS/article ve purposeful error fixture; Reddit isteği yok. Browser test dış GET'leri MockTransport ile yanıtlandı. |
| 9. Calendar | Month/Week→19–25Eki→canonical 6 todo; timed10:00 versus all-day; task/project ilişkileri | Google OAuth ve kişisel calendar açılmadı. |
| 10. Review / continuity | Weekly%40/unknown/career applied+interview; not kaydet→history/reopen; carry-over preview6→explicit H7 apply→6 durable completed receipts; Home daily close kayıtlı durumu | Carry-over 10:00/45 korundu. Eski historical/adjacent snapshot karşılaştırması suite ve saved summary; ikinci haftayı yaşayıp doğal clock geçişi yapılmadı. |
| 11. Career / Academic | Synthetic canonical manual Job+announcement; shortlist bağımsız Application applied→interview; follow-up todo deep link; yerel profile ve evaluation UI; profile-fit100 vs candidate65 vs recommendation100 ayrı; kısa metin uyarısı | Değerlendirme kalıcı/güncel. Discovery scraper/manual refresh başlatılmadı; CV kişisel dosyası kullanılmadı, mevcut sentetik profil fallback. |
| 12. Obsidian / Capture | Temporary Vault note same UUID twice→tek dosya; farklı payload409/bytes korunur; project ensure iki kez→tek note; continuity path; native Todo capture | Unavailable/read-only/conflict/unknown delivery/history receipt suite'de. Kişisel Obsidian GUI'de test notu açılmadı. |
| 13. Settings / Health | Tema/tutorial iki sekmede; Odak off→reload checkbox false/nav yok→on; backup generate→native file inspect→explicit merge0new196skip; source health, storage, worker kapalı, Goal Studio ready tools0 | H015/H018 kapandı. Runtime preference davranışı doğrulandı. Revision conflict/CAS suite'de; iki sekme aynı setting'in eşzamanlı write'ı ayrıca browser'da zorlanmadı. |
| 14. Extension / API | 27 mevcut Node test: bookmark/todo/note/opportunity/announcement, persistent outbox retry/unknown delivery, UUID dedup ve permissions; canonical API/Vault replay ayrıca gerçek local HTTP | Native extension installation/permission genişletmesi yapılmadı. File chooser extension izin hatası native picker ile aşıldı, security permission değiştirilmedi. |

### Cross-module audit

Goal→Todo ve Project→Goal canonical link/fingerprint; Todo→Planner gün/saat/süre;
RSS→Bookmark kaynak kimliği; Bookmark→Learning count1; Learning→Flashcard mastery ayrımı;
Opportunity→Todo canonical deep link; Review→Planning preview/onay/receipt;
Hermes→Goal revision/approval/replay; Obsidian→Entity frontmatter ve project continuity;
Extension→API UUID/outbox; Settings→Runtime gerçek navigation tercihi doğrulandı.

Browser console: app kaynaklı yeni crash görülmedi. Chrome'un yüklü Zotero extension'ında
“Receiving end does not exist” mesajları vardı; forkOS hatası olarak sayılmadı.
Test sırasında kasıtlı 503 kaynak, invalid proposal ve permission/chooser hataları ayrıca sınıflandırıldı.
Her provider'ın canlı availability veya her UI permütasyonunun tam kapsamı iddia edilmez.

## H. Deferred items

- GitHub Actions kota sonrası: çalıştırılmadı; workflow dosyaları değişmedi.
- V1 tag/GitHub Release/production ilanı yapılmadı.
- Codex OAuth / Nous Portal canlı inference ertelendi.
- Canlı acquisition, LinkedIn policy, katalog/scheduler ve otomasyon defaults değiştirilmedi.
- Windows/Linux/Podman gerçek kurulum ve font; screen reader/high contrast ayrı platform kontrolü.
- Root dağıtım LICENSE kararı repository sahibine ait; paket metadata kontrolü lisans tahsisi değildir.
- Restore process kill/power loss/distributed atomicity ve her mutasyonda browser transport loss ayrı kapsam.

## I. Git / runtime / installation

Branch `main`. Kod commit'leri: `ede2b53` backup/restore, `93f88d6` dialog accessibility,
`3affd28` RSS completion, `0253d00` async forms/import/deep links. Rapor commit'i
bu serinin ardından gelir. Commit'ler **[skip ci]** mesajıyla normal push edilir;
force push, workflow dispatch, tag veya release yok. Kesin SHA/push/working tree teslim mesajında
ve `git log ccb2ca5..HEAD` ile doğrulanır. README, bu rapor ve taslak notlar kanıtla aynı seridedir.

README installation sanity: env örneği→Compose DB/migrate/API/web, loopback portları,
optional worker, Vault overlay, Hermes, First Run, backup ve forkos stop/restart akışları
incelendi. İzole image/PG temiz migration, test API ve Vite start doğrulandı. Yeni makinede
tüm optional uygulamaları indirip kurma veya Podman kurulum testi yapılmadı.

Normal runtime test başında kapalıydı; cleanup sonrası mevcut launcher `scripts/forkos.py --no-open`
ile açıldı ve exit 0 döndü. Doctor: **11 OK, 0 WARN, 0 FAIL**. DB/API/web healthy;
`/health` status ok, web HTTP 200; DB head80; Vault readable/writable; Goal Studio
local_custom/ready/tools_verified, Qwen3.5-9B-Q4_K_M. Worker açılmadı. Kullanıcı API açılışında kaynakların çekilmesini açıkça onayladı. Bu açılışın
source warning'leri kaynak availability verisidir; healthy gibi gizlenmez. Personal DB üzerinde
son kontrol yalnız health/current head/service status okumasıdır.

## J. Final verdict

**LOCAL RELEASE READY — CI PENDING**

Keşfedilen P0/P1 kapalı, gerçek %200/reduced motion tamam, son tam suite/build/contract/migration/
restore ve kritik browser yazma akışları yeşil. Bu karar CI, public release ve yukarıdaki ertelenen
platform/canlı provider kontrollerinin yapılmış olduğu anlamına gelmez.
