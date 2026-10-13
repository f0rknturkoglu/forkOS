# Goals 2.0 — Yaşayan hedefler

## Ürün akışı

`/goals` tek Hedefler alanıdır. Kullanıcı amacını ve ayırabileceği zamanı yazar;
`Uzun vadeli` aynı ürünün dönemli hedef tercihidir. Hermes içerik önerir, sunucu
tipli bir pakete dönüştürür, kullanıcı önizlemeyi düzenleyip onaylar. Başarılı
onay hedefin yol haritasını açar. Manuel hedef oluşturma bağımsız çalışır.

Ana görünüm çalışma ilerlemesini, sıradaki işleri, öğrenmeyi ve takvim planını
gösterir. Ölçümler, model bağlantı ayrıntıları, tarihsel planlar ve V1 düzenleyicileri
isteğe bağlı açılır. Bir sınav puanının ölçülmemesi, hazırlık işlerinin tamamlanmasıyla
giderilmez: gerçek sonuç ve çalışma ilerlemesi ayrı kalır.

## Kanonik sahiplik

| Kayıt | Sahibi | Yol haritasında saklanan |
| --- | --- | --- |
| Hedef ve alt hedef | Goal | hedef referansı, dönem/aşama bağlantısı |
| Görev ve tamamlanması | Todo | kanonik görev referansı |
| Öğrenme alanı/konu/kaynak | Learning | kanonik konu/kaynak referansı |
| Proje ve milestone | Project | kanonik proje referansı |
| Çalışma günü/süresi | Todo PlanSlot | önizlemede öneri; uygulamada gerçek PlanSlot |
| Sonuç ölçümü | V1 KeyResult sağlayıcısı | ayrı sonuç read model'i |
| Düğüm | GoalRoadmapNode + Entity | ad, açıklama, sıra, ağırlık, üst düğüm, tür, kapı, çıkarılma |
| Bağlantı | Link | `targets`, `advances_goal`, `prepares_for`, `roadmap_requires` |

`GoalRoadmapNode.id` entity FK'sidir. Durum ve yüzde sütunları içermez. Tüm durumlar
okuma sırasında asıl modüllerden alınır. Entity helper'ları ve append-only event
defteri kullanılır. `roadmap_requires` normal Link yazma uçlarında değiştirilemez;
tipli paket revizyonu döngü kontrolünü uygular.

## Paket ve onay sözleşmesi

Hermes `PackageDraft` semantik içerik üretir: başlık, isteğe bağlı ölçülebilir hedef tanımı,
aşamalar, milestone'lar, konular, görevler, dönemli alt hedefler, aday token'ları,
plan niyeti ve açıklamalar. UUID, SQL, araç çağrısı, tamamlanma veya ölçülmüş güncel
puan kabul edilmez. Mevcut kayıtlar en fazla 30 doğrulanmış yerel aday ile önerilir.

Normal yeni hedefte küçük model sınırı kapalı, düz `WorkPlan`'dır: modelin yazdığı
somut işler, isteğe bağlı aşama/öğrenme konusu ve sonuç alanları mevcut
`PackageDraft` biçimine deterministik çevrilir. Eksik iş/konu uydurulmaz. Uzun
vadeli ve mevcut hedef revizyonları doğrudan tam semantik package kullanır.

`compile_draft()` token'ları yeniden doğrular; çalışma tarihlerini, sahipliği,
bağımlılıkları, mevcut adım indekslerini ve tam eşleşmeleri çözerek kararlı anahtarlarla
`StudioProposal(schema_version=2)` üretir. Tam eşleşme dahi önizleme/onay gerektirir.
Mevcut alan/konu/görev kullanımı kopya oluşturmaz. Benzer başlık tek başına birleşme
kanıtı değildir. Yeni kaynak URL'si üretmek yerine kaynak ihtiyacı kaydı açılır.
Bookmark kullanımı Learning'in kanonik `attach_bookmark` köprüsünden geçer; kurs ve
kart destesi bağları konu Kaynaklar bölümünde görünür. Otomatik Anki ithali yoktur.

Kapalı operasyonlar: Goal create/update, KR save, milestone create/update,
roadmap create/update, Learning area/topic/resource, Todo create/update,
PlanSlot schedule/explicit replacement, doğrulanmış Record Link. Görev düzenleme
tamamlanma alanı içermez. Aşama değişimi ve çıkarılması asıl kayıtları silmez.

Paket en fazla 160 operasyon / 120 KB, ilk taslak en fazla 20 görev ve 28 çalışma
bloğu içerir. V1'in 20 operasyon sınırı ve tarihsel proposal okumaları korunur.
Önizleme değişince eski fingerprint onaylanamaz; sunucuda yeni revizyon gerekir.

```mermaid
flowchart LR
  A[İstek] --> B[Hermes semantik taslak]
  B --> C[Kapalı doğrulama ve kanonik çözümleme]
  C --> D[Önizleme / yeni revizyon]
  D --> E[Açık fingerprint onayı]
  E --> F[Tek transaction]
  F --> G[Goal + Todo + Learning + PlanSlot + Link]
  E --> H[Stale / failed / rejected receipt]
```

V1 Studio session/revision tabloları, TTL, sağlayıcı kökeni, consent kilitleri,
idempotent tur teslimi, SSE ve kayıp cevap uzlaştırması yeniden kullanılır.
Yeni altyapı veya ikinci bir agent motoru yoktur. Önizleme dry-run'ı nested transaction
içinde geri alınır. Onay en güncel revizyonu, süresini, fingerprint'i, referans
kayıtların önceki durumlarını ve plan uygunluğunu kontrol eder. Domain helper'ları
`commit=False` ile aynı transaction'a katılır. Hata sonrası tüm domain yazmaları
geri alınır; hata receipt'i kalır. İkinci onay aynı gerçek ID'leri ve PlanSlot ID'sini
döndürür. Başarılı yeni paket görüşmesi yaratılan ana hedefe bağlanır.

## Hiyerarşi ve görünüm

Normal hedef ihtiyaca göre aşama → Todo/konu veya aşama → milestone → Todo/konu
şeklindedir. Tek aşama ve tek görev geçerlidir; Learning, milestone ve sonuç ölçümü
zorunlu değildir. Ayrı kabul kriteri gerçek milestone/sonuç kapısı olabilir.
Uzun vadeli hedef anlamlı dönem → alt Goal → yakın dönem aşaması şeklindedir.
Sabit aşama, görev, konu veya dönem kotası yoktur. Kanonik `parent_goal_id` ve graph
referansları birlikte döngü kontrolüne girer. Gelecek dönemler görevle doldurulmaz;
içeriği henüz açılmamış alt hedefin ilerlemesi bilinmez. Açık kabul kriteri olan boş
milestone tamamlanmamış birimdir. İlk dönemin bitmesi tüm stratejiyi bitirmez.

React/SVG, mevcut bundle'a yeni graph paketi eklemeden deterministik yerleşim,
pan, yakınlaştırma, ekrana sığdırma, dal daraltma ve yön tuşları sağlar. Küçük ekranda
ağaç/liste vardır. Düğüm ayrıntısı asıl modüle gider; düzenleme de inceleme/onay
üzerinden çalışır. Hareket azaltma tercihi gözetilir. Görsel düzen operasyonel veri
değildir; yeni tarayıcı veri deposu eklenmez.

## İlerleme formülü

1. Todo `done` ve Topic `done` gerçek tamamlanma kanıtıdır. Tekrarlı şablon bilinmez;
   belirli occurrence ID'si kanıttır. Eksik/arşivli hedef kayıt `null` olur.
2. Kanonik ID aynı kabul edilmiş kapsamda yalnız bir kez sayılır. Parent Todo,
   aynı kapsamdaki alt görevlerinin yanında ikinci bir iş birimi değildir.
3. Bir konuya hazırlayan görevler ve konunun kendisi tek öğrenme gereksiniminde
   birleşir; kanıtlarının ortalaması görev bittiğinde de ilerleme sağlar. Sonra
   konunun bitmesi aynı gereksinimi tamamlar. Bilinmeyen kanıt bilinmez kalır.
4. Milestone alt işlerinin ortalamasıdır. Kullanıcının açık milestone tamamlaması
   kendi kabul kriterini karşılar. `completion_gate` milestone ise alt işler ve
   ayrıca sonuç onayı gerekir.
5. Aşama/dönem ağırlıklı birimdir. Hedef yüzdesi `sum(fraction * weight)/sum(weight)`;
   aynı iş ikinci aşama/proje/alt hedef yolundan tekrar payda oluşturmaz. Tekrar
   görünen iş ilk deterministik aşamaya aittir; yalnız tekrardan oluşan grup hariçtir.
6. Bilinmeyen gerekli birim veya kapsam kesilmesi toplamı `null` yapar. Bilinen ve
   toplam gereksinim sayıları ayrıca taşınır. Ara düğümler seçili hedef kapsamını,
   alt hedefin kendi sayfası kendi kapsamını gösterir.

Project aynı kanonik evidence helper'ını kullanır. Her proje milestone'u birimdir;
Goal içinde de bu milestone ağırlıkları korunur; yalnız görevlerin düz ortalaması
alınarak farklı bir proje yüzdesi üretilmez. Arşivli kriter belirsiz kalır.
atamasız görevler birer birimdir. Proje yüzdesi bu proje kapsamının ortalaması,
Goal yüzdesi aşama/dönem kapsamının ortalamasıdır. Çalışma veya link değişince merkezi
`invalidateAfter()` Goal/graph/workspace/Project/Planning/Learning okumalarını yeniler.
Gerçek dünya sonucu V1 KR sağlayıcılarında kalır; çalışma yüzdesi ölçüm yazmaz.

## Planlama ve takvim

İlk pencere İstanbul gününe göre 14 gündür. Kullanıcının açık kapasitesi korunur;
bilinmeyen kapasite günlük 30 dakika etiketli başlangıç varsayımıdır. Uzun iş
kapasiteye sığacak birden fazla gün bloğuna bölünür; kalan iş uyarısı gizlenmez.
Mevcut bloklar kapasiteden düşülür; süresi bilinmeyen blok olan gün atlanır.
Yeni paket mevcut slotu sessizce değiştiremez. Taşıma açık eski slot ID'siyle
onaylanır; gerçek teslim tarihi ayrı kalır.

Yeni kesin saat yalnız kullanıcıca onaylanmış çalışma aralığı varsa kabul edilir.
Mevcut manuel blok açıkça başka güne taşınırken kullanıcının saati, süresi ve notu
korunur; değiştirilecek eski blok da önizlemenin takvim snapshot'ına dahildir.
PlanSlot ve local ExternalEvent çakışması, günlük kapasite, uygun günler ve pencere
sunucuda kontrol edilir. Saat bilinmiyorsa gün düzeyinde plandır; kesin saat
rezervasyonu değildir. Plan/Calendar
değişikliği önizlemeden sonra olursa revizyon stale olur. Aynı transaction kilidi
kanonik PlanSlot yazıcılarında da kullanılır. Google'a otomatik gönderim yapılmaz;
Google bağlantılı slot normal Planner üzerinden düzenlenir.

Öneri, dry-run ve onay aynı `calendar_snapshot()` / `availability_policy()`
kurallarını kullanır. Calendar şemasında free/busy veya transparency alanı olmadığı
için tüm gün etkinlikleri otomatik planlamada engeldir. Aralıklar İstanbul yerel
gününde ve bitiş hariç yorumlanır; geceyi aşan etkinlikler ilgili günlere yayılır.
Bitişi eksik veya başlangıcından önce olan etkinlik yalnız başlangıç gününü belirsiz
yapar; o gün otomatik planlanmaz. Gerçek devam süresi bilinmediği için sonraki günün
müsaitliği bu kayıttan doğrulanmış sayılmaz. Arşivli etkinlikler engel sayılmaz.
Bilinen saatli etkinlikte gün düzeyindeki öneri yalnız işin o güne dağıtımıdır.

Kullanıcı önizlemede başka güne taşıyabilir veya ilgili blok için açık
`calendar_override` seçebilir. Gün değişince bu seçim sıfırlanır. Model bu alanı
üretemez; flag yalnız onaylanan revizyonda ve uyarıda kalır, PlanSlot'a eklenmez.
Kesin saatli çakışmalar, kapasite ve pencere kuralları yine uygulanır.

## Bağlantıdan çıkarma ve güncel katkı

`contributions.current_scope()` graph, GoalWork, Strategy alignment ve dolayısıyla
Hermes snapshot için aynı etkin katkı kapsamını hesaplar. Ayrılmış/arşivli düğümün
alt ağacı güncel kapsamdan çıkar; aynı hedefte başka etkin düğüm veya başka hedefte
bağlantı varsa o katkı devam eder. Kanonik Todo/Learning/Project ve Link satırları
silinmez; tamamlanma ve geçmiş Review snapshot değişmez.

Roadmap öncesi Link zamanı veya mevcut Link ömrüne ait bağımsız `link.created`
eventi manuel ilişkiyi korur. Düğüm eventi hedef/kaynak/ayrılma kökenini taşır.
Eski eşzamanlı ve eventsiz köken belirsizliğinde Link geçmişi korunur, yalnız
ayrılmış roadmap katkısı okuma sırasında bastırılır. Bu, eski veriyi kesin olarak
sınıflandırmış bir migration değildir. Ayrılma revizyonu etkilenen graph yapısını
ve kanonik hedef kayıtlarını da snapshot alır; sonradan değişmiş onay stale olur.

## Hermes bağlamı ve sınırı

Her yeni soruda `GoalContextSnapshot` yeniden hazırlanır: Goal/hiyerarşi, graph,
güncel Todo/konu/kaynaklar, gerçek slotlar, Project ilerlemesi, mevcut sonuç ölçümleri,
7/30/90 günlük anlamlı event pencereleri, ilgili kabul edilmiş Review snapshot'ları,
son paket kararları ve kayıtlı kapasite. İç içe alt hedeflerin kanonik işleri bu
kapsama dahildir; ayrılmış işler legacy bağlantılardan geri getirilmez. Kaynak
ihtiyacı ve kırılmış kaynak bağlantısı gerçek URL'den ayrı gösterilir.
Global notlar/Vault veya başka hedeflerin
anlatısı bağlama gönderilmez. Sağlayıcıya giden görünüm 20 KB ile sınırlı ve kesilme
işaretlidir. Yeni turn'de author/coach görevi kalıcı olarak ayrılır. Koçluk yalnız
güncel çalışma yüzdesi, tamamlanan/bekleyen işler, Topic/Project durumu ve gerçek
sonuç ölçümlerinin kısa görünümünü alır; paket şeması veya düzenleme token'ları
gerektirmez. Açık değişiklik isteği aynı görüşmede authoring'e geçer.

Hermes yalnız yorum veya tipli revizyon önerebilir. Yüzde, tarih, mevcut puan veya
etkinlik nedenini tahmin etmesi istenmez. Bozuk yapısal cevap bir kez aynı doğrulanmış
sağlayıcıyla düzeltilebilir; yine geçersizse hiçbir domain kaydı yazılmaz. Yerel profil
araçsızdır. Mevcut açık cloud consent, iptal ve sağlayıcı/model doğrulaması korunur.

Canlı modelin biçim kabulü tam içerik doğruluğu değildir; serbest metin guard'ları
tüm doğal dil iddialarını ispatlamaz. Sabit yerel modelde oranlar ve açık P1'ler
[Live Hermes Reliability Closure](goals-2.0-hermes-reliability.md) içinde kayıtlıdır.

## Migration ve V1

`0081_goal_roadmap` tek head'dir, `0080_goal_studio_capture` sonrasına eklenir.
Yalnız yeni tablo/index ekler; Goal/Entity/Event/Link çekirdeğini yeniden yazmaz.
V1 Goal, milestone, Plan, Pillar, KR, Studio ve Review geçmişi aynen kalır. Eski
Goal'ların graph'ı okuma adaptörüyle gösterilir; toplu dönüştürme yapılmaz.

0081→0080 boş graph'ta tabloyu düşürebilir. Kabul edilmiş graph satırları varsa
tablo/history korunur; tekrar upgrade idempotent'tir. Verili graph ile daha eski
Goal tablosunu düşüren derin downgrade FK tarafından engellenir; sessiz veri silme
yapılmaz. Üretim upgrade öncesi doğrulanmış safety dump saklanır.

## Sınırlar

500 Goal, toplam 10.000 graph satırı / Goal başına 1.000 düğüm, hiyerarşi 12 ve
düğüm derinliği 32 ile sınırlıdır. Graph okumaları batch hazırlanır; recursive
çocuk başına yeniden DB taraması yoktur. Agent snapshot'ında en fazla 60 düğüm,
100 görev/konu, 50 kaynak, 100 slot, 5 revision/Review bulunur; inference görünümü
daha küçüktür. Büyük kapsamda belirsizlik ve kesilme gösterilir.

Canlı modelin her istekte geçerli ve içerik olarak doğru taslak üretmesi garanti
edilmez. Bu durum onay/dry-run sınırında reddedilir. Kaynak araştırması yerel aday
keşfidir; internet taraması veya otomatik deste indirme yoktur. Doğal dilde tüm
müsaitlik ifadelerini çözme kapsamı sınırlıdır; typed preview bilinen kısıtları taşır.
İlk teslimin tarihsel kanıtı [kapanış kaydındadır](goals-2.0-closure.md).
Uyarlanabilir paket, Calendar ve katkı düzeltmelerinin güncel kanıtı
[adaptive closure kaydındadır](goals-2.0-adaptive-closure.md).

## Semantik planlama ve durum kartı

Deneysel `GOAL_STUDIO_SEMANTIC_ENABLED=true` ile yeni living turu küçük model sözleşmeleriyle ilerler: ihtiyaçlar → bağımsız görev ve
öğrenme konuları → kapsam denetimi → mevcut V2 derleyici → insan onayı. Somut tek
bir işi açıkça isteyen kısa mesaj ihtiyaç çağrısını atlayabilir. Mevcut hedef
revizyonu veya koçluk iki aşamalıdır; belirsiz yönlendirmeye küçük bir sınıflandırıcı
eklenir. Eski pipeline işareti olmayan turlar eski parser üzerinden okunur.

`Requirements` kullanıcı bilgisi değildir. Learning/kaynak/doğrulama gereksinimleri
model çıkarımıdır; açık sayı, tarih, kapasite ve olumsuz tercihler ayrı sunucu
verisidir ve önceliklidir. `SemanticDraft` konuları görevlerden bağımsız tanımlar;
bir konu birden çok aşamadaki görevle ilişkilendirilebilir. Kaynak ihtiyacı henüz
seçilmemiş yerel LearningResource olarak görünür; kaynak URL'si uydurulmaz.

Revizyonlar yalnız seçili hedefin gerçek aşama/iş/konu/slot referanslarıyla çözülür.
Kaynak ekleme mevcut konuyu tekrar oluşturmaz; kayıt bağlama adayın tipini ve
güncel entity bilgisini doğrular. Ayrılan adım yalnız revizyon kapsamında tekrar
bağlanabilir, etkin ilerleme hesabına kendiliğinden dönmez. Takvim taşıma/hafifletme
mevcut slot kimliğini ve okunan gün/süreyi koruyan doğrulamadan geçer.

Koçluk mesajındaki **Bu yanıtın kayıtlı durumu** bloğu model metninden ayrı,
GoalContextSnapshot'tan üretilir. Önceki mesaj tarihsel durumunu korur; yeni soru
veriyi yeniden okur. %100 hazırlık ile ölçülmüş gerçek sonuç ayrıdır. Model yorumu
ve en fazla iki gerçek açık iş önerisi ayrı bir incelemeden geçer. Serbest metnin
tüm anlamı deterministik olarak ispatlanmış değildir.

Bir deneysel turda en fazla altı Hermes generation isteği, toplam bir düzeltme ve 180 saniyelik kabul
bütçesi vardır. Bütçe sonrası geç yanıt öneri olamaz; iptal teslimi bilinmiyorsa bu
bir native iptal garantisi değildir. Yeni endpoint, migration veya veri sahipliği
katmanı yoktur. Deneysel seçenek varsayılan olarak kapalıdır; ölçülen native
başarı oranı daha çok çağrıyı varsayılan yapmak için yeterli değildir. Kanonik
durum kartı mevcut tek çağrılı koçlukta da kullanılır. Bayrağı kapatmak devam eden
kalıcı turun sözleşmesini değiştirmez. Güncel ölçüm ve kalan sınırlar:
[Semantic Reliability Closure](goals-2.0-semantic-reliability-closure.md).

Koçlukta `current_facts` pending/error ve sınıflandırıcı yolunda da bulunur;
model yanıtı bozulsa bile o sorunun çalışma durumu gösterilir. Açık görev/konu/
kaynak miktarları, phase-only rename, gerçek değişiklik içeren move/replan ve
actual slot günü/süresi sunucu tarafından doğrulanır. Kısmi tipli revizyon hedef
metadatasını değiştirmez.
