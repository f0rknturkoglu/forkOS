# forkOS × career-ops C6–C7 Interview and Outcome Intelligence Report

## Kapsam

Başlangıç temizdi. Yerel main ve fetch edilmiş origin/main:
`ff055a8d1302296b2ed58725a93f60be619fdd9b`.
Pinned career-ops değişmedi:
`v1.34.0 / 6326eb5d3804e8cb20d28acd5701a4e603a301f9`.
C4–C5 kapanışı, C6 hazırlık/prova/debrief ve C7 betimsel analitik uygulanmıştır.
C4–C5 ve C6–C7 uygulama/test kapanışı SEALED. C8 uygulanmamıştır.
Bu statü gerçek LLM kalitesi veya gerçek işveren outcome doğrulaması değildir.

## C4–C5 kapanışı

Gerçek Türkçe DOCX ve İngilizce revize PDF yerel CV klasöründen okundu.
Talimatın DOCX önceliği uygulanır. PDF'deki ek web/mobil prototip maddesi
DOCX'e sessizce aktarılmaz. Master kaynaklar değiştirilmez.

DOCX paragraf ve PDF sayfa/satırları CandidateFact'e dönüşür: belge ID,
bölüm, source locator, confidence, verified. Verified, kullanıcı belgesinden
sadık çıkarımdır; bağımsız işveren doğrulaması değildir. Açık rol/kurum/tarih
ayrımları korunur; eksik deneyim yılı/başarı/metrik çıkarılmaz. İçerik ve
locator değişimi context revision'ını değiştirir. Metadata-only READY olamaz;
CV'de olmayan scoring/targeting becerileri aday geçmişine kanıt sayılmaz.

Fake/unverified refs yazımda temizlenir; strong/partial unknown'a düşer.
Eski değerlendirme kanıtları okumada yeniden denetlenir. Top-level
evidence/strengths kanonik kaynaklardan kurulur. Work authorization,
sponsorship ve compensation model tarafından sertifikalandırılmaz.

C5 gerçek CV section/fact içeriğini alır. Null/fake ref, gerçek skill ref'ine
bağlanmış alakasız iddia ve unsupported/ambiguous maddeler READY'yi engeller.
Material gate muhafazakâr source-copy doğrulamasıdır; serbest yeniden yazım
otomatik doğrulanmış sayılmaz. Başvuru yanıtında ref varlığı tek başına yetmez:
yanıt source fact ile uyuşmalıdır. Hassas sorular kullanıcı kararı ister.
Manual cevapların ayrı provenance/event'i vardır; bir cevabı çözmek diğer
kapıları atlamaz. Ön yazı material-claim incelemesi otomatik onaylanmaz.

HTML CV, TXT ön yazı ve kullanılabiliyorsa PDF gerçek Documents/dosyalardır.
Ref'ler temel CV, opportunity ve file API bağı taşır. API transaction'ında
flush yapılır, Documents helper gizli commit yapmaz. Paket tam değerlendirme
hash'ine bağlıdır. Eski READY paketlerde dosya/belge varlığı, kaynak bağları,
claim'ler ve renderer yeniden denetlenir; placeholder gerçek belge sayılmaz.

Pinned renderHtmlToPdf izole geçici workspace kullanır. JS/uzak ağ upstream
renderer tarafından kapatılır; yeni model/font/browser indirilmez. Kimlik,
exit kodu, PDF magic, 1–3 sayfa, çıkarılabilir metin, temel bölümler ve bölüm
sırası kontrol edilir. Render/sıra hatası readiness'i engeller. Gerçek smoke
PDF'si rasterize edilip manuel incelendi: tek sayfa, belirgin clipping/overflow
yok. Bu bütün gelecek PDF'ler için otomatik görsel kanıt değildir:
cv.render_pdf degraded, cv.visual_validate ve cv.render_latex unavailable.

## C6 mimarisi

Yeni lifecycle tablosu yok. Mevcut Interview satırında intelligence JSONB,
typed InterviewPrep, bounded practice listesi ve InterviewDebrief saklar.
0072 migration eklemeli/geri alınabilir; tek SQL per op.execute.
Mutation'lar satır kilidi ve append-only event kullanır.

Prep güncel VALID JD, C4 evaluation ve gerçek CV ister. Input revision;
ilan, tam değerlendirme, aday context, package, company research, aşama,
notlar, hikâyeler ve önceki görüşme not/debrief'lerini bağlar. Read sırasında
stale hesaplanır; yazım öncesi tekrar karşılaştırılır. En fazla altı requirement
ve üç gerçek, arşivlenmemiş supported/existing CareerStory önerilir.
Hikâye yoksa missing_story_gap, bilinmeyen aşama null kalır; format uydurulmaz.
Şirket bilgisi yalnızca saklı araştırmadan alınır ve source ref taşır.

Provider deterministic / evidence-rules-v1 olarak etiketlidir. Bir işlem
bir soru/cevaptır; soru 2.000, yanıt 8.000 karakter, görüşme başına 50 deneme.
Clarity/detail/STAR ipuçları heuristiktir; technical correctness needs_review.
Kaynaksız aday beyanları inceleme ister, kesin yanlış diye damgalanmaz.
Practice prep ve aday revizyonunu saklar.

Debrief geçmiş/saat dilimli gerçekleşme zamanı ve user_report taşır. Notlar,
algılanan açık/başarı, biliniyorsa bildirilen outcome ve işveren alıntısı
ayrıdır. Outcome/ret nedeni çıkarılmaz; alıntı bağımsız doğrulanmış değildir.
Mevcut story update ID'leri doğrulanır; yeni STAR önerileri yalnızca artifact.
Canonical story bank mutasyonu, Todo ve follow-up send yok; onay gerektirir.

JobDetail Görüşmeler ve CareerWorkspace Mülakat hazırlığı yüzeylerinde
Hazırlık/Prova/Görüşme sonrası vardır. Offline yazma kapalıdır; invalidateAfter
merkezi tazeleme sözleşmesi korunur.

## C7 ölçüm sözleşmesi

Snapshot yalnızca kanonik Opportunity, Application, ApplicationHistory,
Interview/debrief, evaluation/package ve source observations kullanır.
Tracker veya LLM yoktur. Dönem keşif tarihi cohort'udur; outcome generation
anına kadar gözlemdir. Dönem/eşik/içerik fingerprint'i ve evidence refs taşır.
Toplu DB okuma kullanılır; ilan başına DB sorgusu yoktur.

Funnel yalnızca gözlenen aşamaları sayar. Ret, önceki applied aşamasını
kanıtlamaz. Conversion payı hedef ve önceki aşama kesişimidir, payda açıkça
önceki aşamadır. Interview kaydı veya stage geçişi görüşme aşamasını gösterir;
görüşmenin gerçekten yapıldığını tek başına sertifikalandırmaz. Süreler açık
tarihli history geçişlerinden çıkar; eksik/negatif süre atlanır. İlk aşama
tarihi korunur. Minimum sample 3–100; küçük örnekte oran/mean/median yoktur.

Canonical reply receipt yoktur: reply=0 gözlem yoktur, yanıtsızlık değildir.
Yanıt oranı/süresi uydurulmaz. Rol/category, ülke, work mode, kaynak, şirket,
değerlendirilmiş teknoloji, CV/paket sürümü ve ay cohort'ları betimseldir.
Kanonik seniority yoksa unknown. CV/paket sürümleri mevcut kayıt sürümleridir;
başvuru anı snapshot'ı yokken nedensel başarı/başarısızlık iddiası yapılmaz.

Rejection taxonomy: explicit_reason (bildirilen employer quote),
user_entered_reason, unknown. Employer cause otomatik confirmed değildir.
Tekrarlayan açık sadece ilişkidir. Postgres/PostgreSQL, k8s/Kubernetes gibi
kesin alias'lar normalize edilir; çelişen sınıflar unknown, aynı ilan iki kez
sayılmaz. Frequency ve weakness sınıfları ayrıdır. Frequency paydası yalnızca
güncel değerlendirilmiş ilanlar; tüm keşif havuzuna genellenmez. Stale
evaluation skill sinyallerine girmez. Interview/employer quote mentions
ayrıdır ve kanıt refs taşır.

Calibration mevcut rule score, deep assessment ve observed outcome'u gösterir;
historical score snapshot yokluğu belirtilir. Production weights değişmez.
Beş bölümlü briefing deterministiktir; LLM metrikleri değiştiremez. Geçmiş
snapshot olmadan trend/what changed uydurulmaz. UI kompakt İçgörüler sekmesidir.

## Semantic yüzey ve capability durumu

forkos_career_interview: prepare/practice/debrief, local write annotation,
MCP host untrusted approval sözleşmesi; send/submit veya gizli story write yok.
forkos_career_insights: bounded, salt-okunur, deterministik. Detay listeleri
100 ile sınırlı, truncation açık; tam funnel/metrikler korunur.
Toplam MCP yüzeyi 36 araç; H0–H7/A5 değişmez, Career iki araçtır.
Provider/SQL alt araçları açılmaz.

interview.practice/debrief ve analytics.funnel/rejection_patterns/skill_gap/
calibration yerel uygulanır, LLM/Node gerektirmez. interview.prepare gerçek
CV/VALID JD/güncel C4 kapıları nedeniyle degraded. Engine inventory disabled
configuration durumu korunur; kanonik UI hizmetleri bağımsızdır.
Doctor ve adapter available sayıları aynı kuralları kullanır.
application.cover_letter/application.package ID drift'i onarıldı.
Cloud LLM factory None reasoner'a düşer; kişisel CV dışarı gönderilmez.

## Gerçek kaynak smoke

Kişisel DB yalnızca okundu; test/fixture yazılmadı, migration uygulanmadı.
Boş forkos_test, geçici Documents ve rollback kullanıldı. Türkçe DOCX gerçek
source; Figma 6178851004 JD'si public Greenhouse GET'ten alındı.
Bu rol kullanıcıya önerilmiş gibi raporlanmaz.

| Kanıt                     | Sonuç                                                            |
| ------------------------- | ---------------------------------------------------------------- |
| CV source-bound records   | 52                                                               |
| Gerçek JD                 | 5.929 karakter                                                   |
| DOCX SHA-256              | edc3ff8369d71e647b68e54af3286c7c6d9546b4b97ecd5b6d0c2981a26a8d15 |
| Master değişimi           | Yok                                                              |
| Gerçek Documents/dosyalar | HTML, TXT, PDF                                                   |
| PDF                       | 1 sayfa, metin/bölüm sırası passed, manuel layout QA             |
| Reasoner                  | Mock; gerçek LLM mevcut/yapılandırılmış değil                    |
| Paket                     | NEEDS_INPUT                                                      |
| Interview/debrief         | Açıkça synthetic fixture; gerçek dünya olayı değil               |
| Prep                      | Deterministic, revision-bound                                    |
| Debrief                   | user_report; inferred outcome yok                                |
| Analytics                 | population=1, küçük örnekte oran yok                             |
| Auto-send/submit          | Yok                                                              |

## Doğrulama

Odaklı backend: 88 passed; semantic transport ve salt-okunur DB fingerprint
kontrolleri dahil. Son sabit-ağaç tam backend: **2.440 passed, 6 skipped**
(238,67 saniye). Frontend: **164 test dosyası, 1.184 passed**.
Eski count-34 guardrail başarısızlıkları düzeltildikten sonra tam koşu tekrarlandı.

Build/API check geçti; endpoint coverage 2/eşik 3; dead exports 10/eşik 10;
Prettier ve git diff --check geçti. 1.280px açık ve 390px koyu fixture UI
kontrolü: anlamlı içerik, error state, klavye sekme erişimi, sıfır page error,
yatay taşma yok. Kişisel DB kullanılmadı. Geçici fixture HTML/TSX kaldırıldı.
React ve frontend-design becerileri primitive/token/erişilebilirlik ve
loading/empty/error kontrollerini yönlendirdi; agent-browser yokken mevcut
yerel Playwright kullanıldı, paket indirilmedi.

Upgrade → downgrade 0071 → upgrade head izole DB'de geçti.
Tek head 0072_interview_intelligence. Kişisel forkos_pgdata korunur.
Kişisel DB'ye migration uygulanmadı; özellikleri çalıştırmadan önce normal
kurulum akışında `make migrate` ile güncel head uygulanmalıdır.
CI/Actions çalıştırılmadı; kullanıcı isteğiyle kapalı tutuluyor. Başlangıç
temizdi; değişiklikler bu göreve ait ve commit/push kullanıcı talebiyle yapıldı.
Geçici PDF/görsel QA dosyaları silindi;
orijinal CV'ler değişmedi. Görev için açılan DB container'ları ve geçici network
kaldırıldı; kişisel forkos_pgdata volume'ü korunur.

## Gerçek sınırlamalar

Gerçek LLM kalite smoke'u yok; mock/deterministic açık etiketlidir.
Otomatik tüm-belge visual QA ve LaTeX yok. Ön yazı/material review kullanıcıya
bırakılır; otomatik READY garantisi yok. Reply receipts, bağımsız employer
feedback doğrulaması, historical score snapshots ve C8 strateji otomasyonu
yoktur. Bu eksikler metrik/kesinlik uydurarak örtülmez.
