# Goals 2.0 — Adaptive Planning & Integrity Closure

Tarih: 2026-10-13. Başlangıç/final HEAD: `61bd6187f5410edee605a8e222dda92a5148073f`.
Bu çalışma commit/push yapılmadan çalışma ağacında bırakıldı. İlk teslimin
`goals-2.0-closure.md` kaydı değiştirilmedi.

## Kök nedenler ve düzeltmeler

1. Authoring prompt/örnekleri ve derleyici normal hedefte üç aşama, sabit başlangıç
   işleri ve zorunlu milestone varsayıyordu. Onarım promptunda da bu kota vardı.
   Ortak kapalı `PackageDraft` artık hedefe göre anlamlı küçük/büyük şekilleri kabul
   eder; Learning, milestone, nitel kabul kriteri ve sayısal sonuç bağımsız opsiyoneldir.
   Tek aşama/tek görev geçerlidir. Boş yeni paket, aynı aşama adının tekrarı,
   döngü, sahte başlangıç puanı, kaynak URL'si ve yanlış açık sayısal hedef reddedilir.
   Uzun dönem sayısı sabit değildir; gelecekteki alt hedef görevle doldurulmaz.
   Kullanıcının açık Learning isteği konusuz yeni paketle karşılanmış sayılmaz;
   bu koşul eğitim dışı hedeflere zorunlu Learning eklemez.
2. Planner saatli etkinlikleri işlerken all-day ve eksik bitişi tutarlı ele almıyordu.
   Ortak Calendar snapshot/policy artık öneri, dry-run ve onayda aynıdır. İstanbul
   yerel günü, bitiş hariç sınırlar, çok günlük/geceyi aşan aralıklar ve arşiv dikkate
   alınır. All-day otomatik engeldir. Eksik/geçersiz bitiş başlangıç gününü belirsiz
   yapar; gerçek sonraki gün müsaitliği bu kayıttan doğrulanmış sayılmaz.
3. Detached düğümler graph'tan çıkarken otomatik `advances_goal` ilişkileri
   GoalWork/Strategy alignment üzerinden güncel katkıyı sürdürüyordu. Paylaşılan
   `ContributionScope` bu okumaları ve dolayısıyla Hermes context'i birleştirir.
   Otomatik katkı ayrılır; manuel V1 ilişki, başka etkin düğüm/hedef katkısı ve
   kanonik Todo/Learning/Project verisi korunur. Link satırları silinmez.
4. Browser'da Project'e bağlı `/workspace` yanıtı iç `groups` hesaplama alanını
   kapalı API sözleşmesine geçirerek 500 üretiyordu. SnapshotProject alanları artık
   açık whitelist ile alınır; gerçek Project + HTTP yanıtı regresyonla doğrulanır.
5. Göreli tarihler derleyici ve inference promptunda farklı hesaplayıcılardan
   geliyordu. Yeni hedeflerde aynı kullanıcı mesaj zamanına bağlı hesaplayıcı ve
   açık tarih allowlist'i kullanılır. Yeniden gönderim aynı kalıcı payload'ı kullanır.

## Sözleşme, veri ve onay

Yeni migration yok; Alembic head `0081_goal_roadmap`. Entity/Event/Link çekirdeği ve
kanonik modül sahipliği değişmedi. `ScheduleData.calendar_override` proposal alanıdır;
PlanSlot sütunu değildir. Model semantik taslağında bu alan bulunmaz. Kullanıcı
önizlemede ilgili blok için açıkça seçer, gün değişince sıfırlanır. Kapasite,
pencere ve kesin saat çakışmaları yine reddedilir; açık tercih revizyon uyarısına
kaydedilir. Preview fingerprint + TTL + idempotent karar + nested dry-run ve
tek transaction rollback korunur. Calendar/PlanSlot değişimi stale olur.
Detach preview graph yapısını ve ilgili kanonik hedef kayıtlarını da snapshot alır.
Yapı veya kanonik durum değişince eski onay reddedilir.

Manuel bağımsız ilişki: roadmap öncesi Link zamanı veya mevcut Link ömrüne ait
`link.created` eventi. Eski eşzamanlı/eventsiz köken kesin sınıflandırılamaz: fiziksel
Link ve event geçmişi korunur, ayrılmış roadmap-only güncel katkı okuma sırasında
bastırılır. Bu bilinçli muhafazakâr politika eski veriye provenance uydurmaz.
Tarihsel Review snapshot'ları değiştirilmez. Project kendi kanonik kapsamında
aynı yüzdeyi tutar; Goal kapsamından ayrılmak Project işini geri açmaz.

Reddedilen yollar: boş aşamalarla kota doldurma; öğrenme dışı hedefte sahte konu;
eksik Calendar bitişini sıfır süre sayma; all-day'i sessizce boş sayma; Link'i
körlemesine silme; eski Review yüzdelerini yeniden yazma; model hatasında genel
fallback planı veya ölçüm uydurma; kişisel veritabanıyla test.

## A–H değerlendirmesi — sentetik fikstürler

Fikstürler gerçek Hermes çıktısı değildir. Aynı derleyici, preview/dry-run,
approval/apply, idempotent ikinci approval ve kanonik ilerleme okumaları çalışır.
`backend/tests/fixtures/goals_adaptive.json` A–G; H mevcut kayıtlarla testte üretilir.

| Senaryo | Operasyon | Yeni Todo / Topic | Slot | İşler tamamlandıktan sonra | Sonuç |
| --- | ---: | ---: | ---: | --- | --- |
| A YDS 55+, günde 2 saat | 24 | 3 / 3 | 3 | %38; Topic/sonuç kanıtı ayrı | applied |
| B forkOS V2 teslimi | 14 | 3 / 0 | 3 | %75; sürüm kabulü bekliyor | applied |
| C pasaport | 10 | 2 / 0 | 2 | %50; teslim doğrulaması bekliyor | applied |
| D üç ayda taşınma | 15 | 3 / 0 | 3 | %75; gerçek taşınma kabulü bekliyor | applied |
| E haftada üç koşu | 11 | 3 / 0 | 3 | ilk haftanın kabul edilmiş çalışma kapsamı %100 | applied |
| F beş yıllık kariyer | 11 | 1 / 0 | 1 | gelecek alt hedef bilinmez; toplam null | applied |
| G yarın belge teslimi | 5 | 1 / 0 | 1 | %100; tarih kullanıcı mesajından | applied |
| H Project/Learning/Todo/resource tekrar kullanımı | 7 | 0 / 0 | — | kanonik Project %100; tamamlanmış Todo korunur | applied |

Yüzdeler kabul edilmiş çalışma kapsamıdır; sınav puanı, alışkanlık kazanımı veya
gerçek dünya sonucu otomatik yazılmaz. Eksik kapasite 30 dakika açık varsayımdır;
A'nın iki saat kapasitesi fixture compilation ve parser/regresyonla doğrulanır. Takvime sığmayan süre
başka tarihe uydurulmaz; kalan dakika üst uyarıda görünür.

## Calendar ve katkı regresyonları

Tüm gün, birden çok gün, geceyi aşan saatli aralık, komşu bitiş/başlangıç,
eksik bitiş, arşiv, gün düzeyinde plan, bilinçli override, 14 gün tamamen dolu
takvim, preview sonrası Calendar değişimi ve rollback kontrol edildi.
Mevcut concurrency/idempotency/TTL/partial rollback testleri korunur.

Todo detach, subtree detach, başka etkin düğüm, başka hedef, roadmap öncesi/sonrası
manuel Link, yeniden bağlama, kanonik durum/yapı stale onayı; Project yüzde ve
public snapshot; Review geçmişinin değişmemesi kontrol edilir. GoalWork,
Strategy linked scope, roadmap ve Hermes Todo context aynı etkin kapsamı kullanır.

## Tarayıcı kanıtı

Kişisel uygulama yerine `5174 → 18888`, ayrı `forkos_adaptive_browser_test` kullanıldı.
Gerçek uygulama ve API ile açıkça sentetik etiketli Learning/Project/Calendar
preview'ları UI'da düzenlendi ve onaylandı. Project tekrar kullanımı, Todo detach,
all-day günü izinsiz seçmenin reddi, açık override ile gerçek PlanSlot yazımı
gözlendi. Kısa hedeften boş Learning bölümü kalktı. Project workspace 500 bulundu,
düzeltildi ve yeniden başarılı okundu.

390×844 ve 1366×900: yatay taşma yok; mobil liste, Enter ile adım seçimi ve Escape
ile inspector kapatma çalışır. Loading/empty/error durumları gözlendi; mevcut UI
regresyonları da çalıştırıldı. Kanonik Todo UI'da tamamlanınca hedef %100 oldu;
gerçek sonuç ölçümü bilinmez kaldı. Ekranlar yerel `.codex/artifacts/goals-adaptive/`
altında: `learning-applied.png`, `project-after-detach.png`,
`calendar-explicit-override.png`, `simple-mobile.png`, `simple-wide.png`,
`simple-completed.png`.

## Canlı yerel Hermes

Hermes 0.21.6, araçsız fresh geçici profil, yerel Qwen3.5-9B-Q4_K_M/llama.cpp
ile gerçek `/v1/runs` ve sunucu köken kontrolü kullanıldı. Kişisel config, credentials,
Vault veya geçmiş devralınmadı. Mevcut readonly bağımlılık venv'i kullanıldı;
kurulum onarımı yapılmadı. Başlangıçtaki 32K context Hermes'in 64K minimumuna
uymadığı için geçici model 65536 context ile yeniden açıldı.

Kısa belge hedefinde gerçek model tek Todo, sıfır Learning/milestone/KR ile
approval_pending üretti. Farklı YDS ve yazılım istemlerinde model fazla alan,
yanlış resource biçimi, key tekrarı veya uydurma tarih üretti; tek onarım sonrasında
geçersiz taslaklar güvenle reddedildi. Bir YDS istemi yalnız açıklama verdi.
Ortak tarih guidance düzeltmesi sonrasında başka bir YDS çıktısı geçerli yapıda
olmasına rağmen istenen Learning konularını içermiyordu. Bu semantik eksikliği
reddeden açık kullanıcı isteği guard'ı eklendi ve regresyonla doğrulandı.
Gerçek UI koçluk isteğinin son denemesi de geçersiz yanıtla başarısız oldu;
mevcut kanonik ilerleme ve kayıtlar korundu.
Bu sonuçlar fikstür başarısı veya canlı uçtan uca başarı olarak gösterilmez.
Canlı modelin bu kurulumda her doğal dil isteğinde güvenilir paket üretmesi
doğrulanmış değildir. Kapalı schema ve gerçek kayıt/ölçüm sınırı gevşetilmedi.

## Doğrulama ve sonuç

Yerel doğrulama: backend 2.846 passed / 43 skipped; frontend 161 dosya / 1.084
test; extension 27 test. Adaptive matrix/kritik regresyon dosyası 31 test.
Ruff, Prettier, TypeScript/build/bundle sınırı, OpenAPI/generated schema senkronu,
endpoint coverage, dead-export sınırı ve `git diff --check` geçti. npm audit:
0 vulnerability. Mevcut migration ve registry guardrail testleri tam suite içinde
çalıştı; yeni migration yok. 43 skip mevcut opsiyonel canlı/ortama bağlı testlerdir,
test başarısı sayılmadı. Son kaynak haliyle backend turu 188.00 saniyede tamamlandı:
2.846 passed / 43 skipped.
Bu aşamada P0 yok. Üç özgün deterministik P1 ve Project public workspace hatası
regresyonlarla kapandı. Açık P1: bu yerel modelle doğal dil YDS/yazılım üretimi ve
koçluk akışının tutarlı canlı kabulü sağlanamadı. P2: belirsiz tarihsel Link kökeni,
eksik Calendar bitişi ve sınırlı doğal dil müsaitlik kapsamı belgelenmiş politikalardır.
Tam canlı kabul sağlanmadan VERIFIED iddiası yapılmaz.

## Temizlik ve teslim durumu

Kişisel `forkos-api-1`, `forkos-web-1`, `forkos-db-1` bu görevde başlatılmadı.
Testler tmpfs `forkos_test`, tarayıcı/canlı eval ayrı `forkos_adaptive_browser_test`
veritabanında yürütüldü. Kişisel `forkos_pgdata` korundu; Vault mount edilmedi.
Geçici API/backend/DB container'ları ve `forkos-adaptive_default` network kaldırıldı.
Geçici Hermes, llama.cpp, Vite ve browser kapatıldı; test anahtarları ve geçici
profil/harness silindi. 5173/5174/8787/18888/5433/18434/18435/8643 portlarında
dinleyici kalmadığı kontrol edildi. Yerel kanıt logları ve ekranlar korundu.
Yeni paket/dependency, CI, tag veya deploy yok. Değişiklikler commit/push yapılmadı.

**GOALS 2.0 ADAPTIVE CLOSURE — PARTIAL**

Sonraki canlı model güvenilirliği çalışması, ayrı oranlar ve açık P1'ler:
[Live Hermes Reliability Closure](goals-2.0-hermes-reliability.md).
Bu ek, yukarıdaki tarihsel test ve canlı değerlendirme kaydını değiştirmez.
