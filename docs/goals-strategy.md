# Hedefler ve Strateji V1

## Sahiplik ve uyumluluk

`goal` modülü kanonik strateji sahibidir; `/goals` birincil Hedefler alanıdır.
Kariyer artık özet ve bu alana bağlantı sunar. Eski Goal kimlikleri, kaynak hafıza
referansları, ilişkileri ve milestone kayıtları değişmez. `progress_percent` eski
milestone yüzdesidir; `milestone_progress_percent` açık isimli eşdeğeridir.
`strategic_progress_percent` ayrı read model alanıdır. Eski hedefler atanmadıkça
plana/stratejik alana taşınmaz. Plansız hedef geçerlidir.

## Kanonik graph

`strategic_plan`, `strategic_pillar`, `key_result`, `strategic_plan_revision` PK'leri
`entity.id` FK'sidir. Goal isteğe bağlı plan, pillar ve üst hedef taşır; döngü ve
plan/pillar uyumsuzluğu reddedilir. Plan düzenlemesi ve pillar değişimi immutable
revizyon entity'si ve append-only event üretir. Plan anlatısı yalnız güvenli göreli
Vault Markdown yoludur; gizli/dış/traversal/symlink yollar reddedilir, dosya yazılmaz.

## Ölçüm

Decimal ilerleme `clamp((current-baseline)/(target-baseline),0,1)`; azalan hedefte
yön tersine işler. Başlangıç ve hedef eşit olamaz. Ağırlık pozitif olmalıdır.
Objective yüzdesi ölçülebilen etkin/tamamlanmış KR'ların ağırlıklı ortalamasıdır;
eksik KR kapsamı görünür ve güven düşüktür. Duraklatılmış/emekli KR paydada yoktur.
Milestone yalnız `goal_milestones` sağlayıcısı açıkça seçilince KR sonucuna katılır.
Plan/pillar yüzdesi etkin hedefleri ağırlıklandırır; hedeflerin en az %80'i tüm KR'larıyla
ölçülebilirse gösterilir. Pillar ağırlığı plan içindeki ilgili hedef ağırlığına çarpılır.
Bu yöntem gösterilir; toplu yüzde tek başına başarı kararı değildir.

Kapalı sağlayıcılar: manual; applications_applied/interview/offer;
goal_milestones; linked_completion (kanonik hedef adımı veya öğrenme konusu).
Başvuru sayımı tam durum/geçiş kanıtını arar: teklif, atlanmış görüşmeyi kanıtlamaz.
Kohort başlangıcı opsiyoneldir. Nitelik/uygunluk/tahmini teklif çıkarımı yapılmaz.
SQL, ifade, ağ URL'si veya serbest sağlayıcı kabul edilmez. Bilinmeyen/eksik ölçüm
sıfır değil `null` olur. Güncel manual ölçüm orta, 30 gün eski ölçüm düşük güvenlidir.
Her KR kaydetme mevcut manual değerin kullanıcı tarafından yeniden teyididir.

## Rota, uyum, güven

Doğrusal rota tarihler arasındaki geçen süreyle beklenen yüzde üretir; ±10 puan
rotada, fazlası önde/geride. Deadline modeli yalnız son tarihte eşik uygular.
`none` için rota uygulanmaz; eksik kanıt için bilinmiyor.

Uyum 7/30/90 günde H5 COUNTED_VERBS anlamlı event'leri ve mevcut explicit
`advances_goal`, `advances_goal_milestone`, en fazla beş hop `belongs_to` bağlarıyla
hesaplanır. Pozitif olmayan medya tüketimi sayılmaz. Her event genel paydada ve
bağlı payında bir kez sayılır. Birden çok hedefe dağılım eşit kesirlidir.
Bağlar güncel graph'a göre geçmiş pencereyi sınıflandırır; tarihsel graph çıkarımı yoktur.
Uyum hiçbir KR sonucunu yükseltmez. Boş pencere yüzde üretmez.
Güven kanıt kalitesidir; ruh hali, öz güven veya hedefe ulaşma olasılığı değildir.

Taramalar sınırlıdır: 500 hedef,100 plan,500 pillar,2000 KR,5000 başvuru,
20000 başvuru geçmişi,5000 milestone,5000 event,10000 ilişki.
Limit ölçüm/uyum için görünür reason üretir; eksik kanonik sayım sonuç olmaz.
Kanıt referans listeleri 100, hedef hareketleri 50 ile sınırlıdır.

## Salt okunan inceleme

Desteklenen bulgular: MISSING_MEASUREMENT, OBJECTIVE_WITHOUT_SUPPORT,
OBJECTIVE_INACTIVE, STALE_OBJECTIVE, DEADLINE_WITHOUT_PROGRESS, KR_BEHIND,
BUSY_NOT_PROGRESSING, EXECUTION_DRIFT. Her bulgu tarih penceresi, gözlenen olgu
ve entity/event kanıtı taşır. Busy kuralı en az 5 bağlı hareket ve <%20 sonuç arar;
sonucun değişmediğini veya nedensellik iddia etmez. İnceleme hiçbir nesne yazmaz.

## Review, Hermes ve proaktivite

Kabul edilen Review.stats içinde schema_version=1 strateji snapshot'ı saklanır.
Snapshot kabul anındaki sonuç/uyum/tanımlar/revizyonlarıdır; geçmiş outcome'u geriye
hesaplama iddiası yoktur. Eski Review kayıtları aynen okunur. Geçmiş sayfası
son 50 Review ve 50 revizyonu gösterir. İki snapshot aynı sürüm, tanım, ağırlık,
revizyon, ölçüm penceresi ve yeterli kanıt kapsamı taşıyorsa delta üretir.

`forkos_strategy(mode=overview|objective|audit|history,days=7|30|90)` tek typed
salt okunan MCP aracıdır. Hermes kanonik gerçekleri yorumlar; stratejik yazma yoktur.
H3 supporting evidence ve brain_read Vault anlatısı mevcut yüzeylerdir. H5 anlamlı
hareket sözleşmesi yeniden kullanılır. H7'ye stratejik mutasyon kısayolu eklenmez.
H6 `strategy_attention` varsayılan kapalıdır, mevcut policy/digest/snooze/cooldown
motorunu kullanır; yüksek öncelikli hareketsiz veya yakın tarih/düşük sonuç bulgusu
aday olabilir. Kural açılmadıkça yeni bildirim göndermez.

## Fixture örnekleri

- Bir milestone tamamlandı: adımlar %100, KR yoksa sonuç null.
- Manual KR 10/100 ve beş bağlı todo: uyum %100, sonuç %10; busy bulgusu.
- Aynı KR 100/100 ama 31 gün eski: sonuç %100, güven düşük; kötü outcome değildir.
- Bir event iki ayrı ilişkiyle aynı hedefe bağlı: bağlı sayım bir, iki değil.
- Eski accepted Review %10 içerir; güncel KR %100 olunca snapshot %10 kalır.

## V1 sınırları

V1 geçmiş outcome serisi türetmez; kabul edilmiş Review kanıtını saklar. Kanonik
proje bitişinin güvenilir sözleşmesi olmadığı için proje completion sağlayıcısı yoktur.
Görüşme/teklif kalitesi, psikoloji ve serbest metin metrikleri çıkarılmaz. Bağlanmamış
hareket drift üretir; proje başlığına göre otomatik hedef eşlemesi yapılmaz.

## V1 kapanış doğrulaması — 2026-10-01

- Backend seçili Goal/Review/H6/MCP/registry/migration regresyonları: **307 geçti** (17.44 s). Yeni strateji dosyası 24 test içerir.
- Frontend bütün suite: **166 dosya, 1202 test geçti** (20.33 s). GoalsPage boş/hata/geçmiş akışları dahil.
- TypeScript, Vite build ve bundle sınırları geçti; git diff --check temiz.
- OpenAPI export --check ve TypeScript generation --check kendi container runtime'larında geçti. Web container Python içermediğinden birleşik npm api:check yerine aynı alt kontroller ayrı çalıştırıldı.
- Endpoint coverage: iki önceden mevcut referanssız uç, eşik üç; yeni strateji uçları frontend tarafından tüketiliyor.
- İzole 0076→0077 upgrade ve 0077→0076 downgrade; eski Goal kimliği, source_memory_id, milestone başlığı ve tamamlanmış durumu korundu.
- Canlı DB yedeği: backend/backups/pre-goals-strategy-20261001.dump (Git dışı). Canlı tek head 0077_goals_strategy; overview HTTP 200.
- Canlı MCP initialize→tools/list→tools/call: 37 public araç, forkos_strategy overview başarılı. Salt okuma testinde DB fingerprint değişmedi.
- Tarayıcı: geniş ve 390 px, açık/koyu, boş/hata/yeniden deneme, dolu hedef, plan ve geçmiş. Yatay scroll viewport'u aşmadı.
- Geçici preview servisleri, tmpfs DB/network, container içindeki geçici schema kaynakları ve ek Vite süreci temizlendi. Kişisel pgdata volume korunur.
