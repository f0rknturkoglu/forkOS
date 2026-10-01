# Ürün Navigasyonu (Productization)

Bu doküman, forkOS'un **kullanıcıya görünen** bilgi mimarisini tanımlar.
Teknik modül envanteri ile ürün navigasyonu aynı şey değildir:

```text
backend module  !=  sidebar destination
frontend module !=  primary navigation item
capability      !=  permanently visible UI
```

Tek kaynak: `frontend/src/core/navigation.ts` (`PRODUCT_AREAS`). Rota → ürün
alanı eşleşmesi BAŞKA hiçbir yerde yazılmaz.

---

## 1. Ürün alanları

```text
Home            /                     (günün planı, okuma akışı, ritim, son tarihler)
Plan            /todos                Görevler · Haftalık plan · Rutinler · Takvim · Odak
Projeler        /projects
Kariyer         /opportunities        Keşfet · Başvurular · Duyurular · Profil · Kaynaklar
Öğrenme         /learning             Öğrenme · Kartlar · Tekrar
Kütüphane       /bookmarks            Yer İmleri · RSS · Medya · Bilgi
Finans          /finance
Etkinlik        /activity             (ritim · trend · hareket akışı)
Değerlendirme   /review/weekly
────────────────────────────────────────────────────────────────────────────
Ayarlar         /settings             (tek sistem girişi)
```

Kurallar:

- **Uzun kuyruk yoktur.** "Daha fazla" ürün kavramı kaldırıldı: Finans,
  Etkinlik ve Değerlendirme sıradan kök hedeflerdir.
- **Katlanır satırın TAMAMI açar/kapar ve gezinmez** (Plan, Öğrenme,
  Kütüphane). Ok yalnız durumu söyler; "etikete basınca mı, oka basınca mı"
  belirsizliği yoktur. Tek hedefli alanlar (Home, Projeler, Kariyer, Finans,
  Etkinlik, Değerlendirme) normal bağlantıdır. Satır geometrisi tek parçadır:
  `h-9`, içinde ayrı bir tıklama dikdörtgeni yoktur.
- Aktif satır **arka plan + yazı ağırlığı + `aria-current`** ile işaretlenir;
  ayrıca bir renk noktası çizilmez.
- Temiz kurulumda yalnız kök alanlar açıktır; alt satırlar kapalı başlar ve
  aktif rota kendi alanını otomatik açar (katlanma tercihi
  `forkos.sidebar.areas`). Tek kompakt kontrol ("Tümünü genişlet/daralt")
  hepsini birlikte açar/kapatır. Ağaç görsel olarak konuşur: alan başlığı
  `h-9`/16px ikon, alan hedefi `h-8`/14px, hedefin alt rotası `h-7`/13px +
  daha derin girinti.
- **Komut aramasının tek girişi üst şerittedir.** Sidebar'ın kendi
  "Ara veya komut" kopyası kaldırıldı; Cmd/Ctrl+K her yerde çalışır.
- **Üst şeridin sağ kümesi tek taban çizgisindedir:** ikon kontrolleri
  `h-8 w-8`, komut besteleyicisi `h-8` ama kasıtlı olarak kare değil. Çalışan
  ya da duraklatılmış odak seansı burada kompakt bir gösterge olarak durur
  (kalan süre + konu); tıklamak global odak panelini açar. Oturum yokken
  gösterge çizilmez — boşta şerit kalabalıklaşmaz.
- Bir modül **çalışıyor olabilir** ama sidebar'da satır tutmaz: `inbox`
  (triyaj akışı), `health` + `sources` (Ayarlar → Durum & Kaynaklar),
  `documents` (kariyer bağlamı), `feed`/`activity.heatmap` (bulundukları
  yüzeyin parçası). Bu, modülü devre dışı bırakmak DEĞİLDİR: rota, widget'lar
  ve komutlar aynen çalışır.
- Domain/backend modülleri birleştirilmez. Plan altındaki `todo`, `calendar` ve
  `pomodoro` ayrı servislerdir; yalnız aynı zihinsel çalışma alanında sunulur.
- Alan satırları registry'den türetilir: modülün birincil rotası + `navigation:
  "child"` işaretli rotalar + alan `links`'leri. Yeni bir alt rota eklemek için
  modül kaydına yazmak yeterlidir; `navigation: "hidden"` rotayı yaşatır ama
  satır bırakmaz.

## 2. Home adlandırma sözleşmesi

Kullanıcıya görünen yüzeyin adı **Home**'dur. Teknik ad alanı `today` olarak
KALIR (isim değişikliği sözleşmeyi kırmaz):

| Katman | Ad | Not |
|---|---|---|
| Modül kimliği | `today` | Değişmez |
| Ayar anahtarları | `today.widget_order`, `today.widget_hidden`, `today.auto_suggestions` | Değişmez |
| Backend uçları | `/api/today/agenda` | Değişmez |
| Widget kimlikleri | `today.agenda`, `today.deadlines`, ... | Değişmez (kullanıcı tercihlerinin anahtarı) |
| localStorage | `lifeos.todayWidgetOrder`, `lifeos.todayWidgetHidden` | Değişmez |
| Görünen ad | **Home** | Sidebar, sekme, başlık |

Zamansal Türkçe ifadeler normal kalır: "Bugünün planı", "Bugün 3 görev",
"Bugüne ekle", "Bugün tekrar".

## 3. Home bileşenleri (temiz kurulum)

İskelet SABİTTİR ve iki katmandır: **çekirdek** yüzeyler Home düzenini kurar
(`TodayWidget.core` alanı), **isteğe bağlı** yüzeyler iskeletin altında akar.

```text
Hero
Bekleyen kararlar   (H7; boşken hiç çizilmez)   → üst şerit (tam genişlik)
Bugünün planı                                   → sol kolon
Öğrenme                                         → sol kolon
Okuma akışı                                     → orta kolon (görsel çapa)
Isı haritası                                    → orta kolon
Son tarihler                                    → sağ kolon
Kariyer                                         → sağ kolon
```

Dar ekranda TEK kolon; DOM sırası okuma sırasıdır: bekleyen kararlar →
bugünün planı → son tarihler → kariyer → okuma akışı → öğrenme → ısı haritası.
Masaüstünde üç kolon `grid-auto-flow: row dense` ile kurulur; ikinci bir
"mobil düzen" yoktur (masaüstü kolonları yeniden sıralanmaz).

Çekirdek yüzeyler **gizlenemez ve sıralanamaz**: eski gizleme kayıtları onları
etkilemez. Ayarlar > Home iki grubu ayırır ("çekirdek yüzeyler" salt okunur,
"isteğe bağlı yüzeyler" gizlenir/sıralanır).

Kurallar:

- Kendini çizmeyen yüzey (veri yokken `null` dönen kart) ızgarada yer TUTMAZ.
- Son tarihler ve Kariyer AYNI kaydı iki kez göstermez: fırsat/mülakat son
  tarihleri yalnız Kariyer kartında durur; genel bildirimler üst şeritteki
  bildirim panelinde kalır. Satırın hedefi yoksa satır bağlantı gibi görünmez.
- Son tarihlerin "tümü" hedefi YOKTUR: tarihler altı modülden toplanır ve
  hepsini tutan tek yüzey yoktur; her satır kaydın kendi rotasına gider.
- Otomatik öneri modu kaldırıldı: Home yalnız ne planlandı / ne açık /
  kullanıcının eklediğini gösterir. Backend `today.auto_suggestions` anahtarı
  ve `/api/today/agenda` öneri alanları uyumluluk için durur, UI tüketmez.
- Bir uç hata verirse yalnız o kaynak düşer; kalan veri dürüstçe gösterilir.
  Hiçbir kaynak veri vermezse yüzey hiç çizilmez (sessizlik başarısıdır).
- `Home render` canonical mutation TETİKLEMEZ: sayfa açılışı hiçbir ajan
  eylemi başlatmaz.
- Widget tercihleri reaktiftir (`core/registry.ts` store): Ayarlar'dan açılan
  yüzey aynı oturumda Home'da görünür. Sunucu anlık görüntüsü yerel tercihin
  üzerine YAZMAZ; yalnız bu cihazda hiç dokunulmamışken tohumlar.
- Home'un temiz kurulum fan-out'u `modules/today/homeFanout.test.tsx` ile
  sabitlenmiştir (≤ 20 uç, tekrar yok).
- Briefing yüzeyi **ertelendi**: H5 review intelligence bugün yalnız ajan/MCP
  yüzeyinde (`forkos_review_intelligence`, `forkos_briefing`) var; HTTP sunumu
  yok. H5 çıktısının bir kısmı H6 proaktif bildirimlerine katlanır. Yeni bir
  uç yazmak yerine bu bağlantı noktası korundu.

## 4. Sabitlenmiş görünümler

- Kaydetme/sabitleme/silme: `frontend/src/core/SavedViewPicker.tsx`
  (`GET|POST /views`, `PATCH|DELETE /views/{id}`).
- Sidebar "Sabitlenenler" bölümü sunucu sırasını korur
  (`pinned` → `position` → `id`).
- Derin bağlantı sözleşmesi: `#/<rota>?saved=<gorunum-id>`. Kenar çubuğu
  satırı bu bağlantıyı üretir; sayfa kimliği çözer ve filtreyi BİR KEZ uygular.
- **Bağlı çalışma alanı: yalnız Yer İmleri (`bookmarks`).** "Görünümler"
  kavramı Görevler, Kariyer ve Medya'dan kaldırıldı: bu yüzeylerin normal
  filtreleri, URL durumu ve satır/ızgara/kanban tercihleri zaten anlaşılırdı ve
  kullanıcıdan açıklama gerektiren bir soyutlama istemiyorlardı. Altyapı
  (uçlar, `savedViews.ts`, sidebar sabitlenenleri) korunur; bu modüllerde
  `?saved=` eski bağlantıları sessizce yok sayılır.
- Modül kimliği = frontend registry kimliği. Backend bu alanı opak taşır.
- Bilinmeyen/eski kimlik, hedefi kapalı modül ve bozuk yanıt **sessizce yok
  sayılır**: sidebar veya çalışma alanı çökmez.
- Filtre sözleşmesi modül başına kapalıdır; tanınmayan anahtar uygulanmaz
  (Kariyer: `sanitizeOpportunityFilters`, Medya: URL parametre adları,
  Yer İmleri/`todo`: alan bazlı eşleme).

## 5. Ayarlar

Ray iki anlamsal gruba ayrılır:

```text
Tercihler   Genel & Görünüm · Home · Bildirimler & Çevre · Modüller · Kariyer Profili
Sistem      Agent & Bilgi · Entegrasyonlar · Durum & Kaynaklar · Sistem & Yedekleme
```

- **Sistem'in tek girişi Ayarlar'dır.** Kaynaklar (`/sources`) ve Sistem
  Durumu (`/health`) kendi rotalarını korur (bildirimler, eski bağlantılar,
  hata ayıklama) ama sidebar satırı tutmaz; sahipleri bu sekmedir.
- **Agent & Bilgi** (`?tab=brain`) zihin sınırlarının tek yüzeyidir: Agent
  bağlantısı (MCP) durumu, f0rknbrain Vault köprüsü, yerel model, proaktivite
  ve bekleyen kararların **salt okunur** özeti ile Hermes bağlantı tarifi.
  Onaylama/yürütme eylemleri burada DEĞİLDİR; tek karar yüzeyi
  Home → Bekleyen kararlar'dır.
- **Durum & Kaynaklar** (`?tab=status`) sistem özetini, ilgi gerekenler
  listesini, kaynak sağlığını (`SourceHealthAccordion`), ajan için tanılama
  paketini ve `Kaynak operasyonları → #/sources` bağlantısını TEK yüzeyde
  toplar. Sağlık sayfası (`/health`) aynı bileşenleri kullanır; ikinci bir
  uygulama yoktur.
- **Entegrasyonlar** yalnız DIŞ sağlayıcıları barındırır (Google Drive,
  GitHub, medya sağlayıcıları). Google bağlama akışı buradan başlar ve OAuth
  dönüşü `#/settings?tab=integrations`'a gelir. Obsidian Vault artık burada
  değildir: f0rknbrain bir sağlayıcı değil, bilgi sahibidir.
- **Kariyer Profili** (`?tab=career`) temel konum/çalışma izni tercihlerinin
  altında LinkedIn arama profillerini yönetir
  (`LinkedInProfilesEditor`; ekle/düzenle/sil/kaydet). Profiller gitignored
  yerel YAML'de kalır; repoya yazılmaz.
- **Bildirimler & Çevre** teslim/ortam tercihlerini tutar (masaüstü
  bildirimleri, hava durumu); proaktivite ayarları Agent & Bilgi'dedir.
- Sistem teşhisi (CPU/RAM/diskten) ve depolama raporu **Sistem & Yedekleme**
  altındadır; tema gibi kullanıcı tercihleriyle aynı yerde durmaz.
- RSS güncelleme/saklama ayarları "RSS otomasyonu" başlığıyla aynı sekmededir
  (kaynak otomasyonu bir tercih değil, işletim ayarıdır).
- Tanılama kartları birbirinden bağımsız düşer: `/agent/status`,
  `/obsidian/status`, `/proactivity/status`, `/execution/plans` veya
  `/auth/*/status` uçlarından biri hata verirse yalnız o kart "alınamadı +
  yeniden dene" gösterir; ayarlar sayfası çalışmaya devam eder.
- forkOS kendi MCP sunucusunun hazır olduğunu bilir; **Hermes istemcisinin
  bağlı olup olmadığını bilemez** ve böyle bir durum göstermez. Ekran yalnız
  bağlantı adresini ve önerilen istemci ayarını verir.
- Kullanıcıya görünen metinlerde iç katman kodları (H0…H7) GEÇMEZ. Katman
  adları kod, test ve geliştirici dokümanlarında yaşamaya devam eder; ajan
  tanılama paketindeki bölüm adları makine tarafından okunur.
- Sekme kimlikleri (`?tab=general|today|notifications|modules|career|brain|
  integrations|status|backup`) ve `?section=media-links` derin bağlantısı
  korunur.

## 6. Route uyumluluğu (KEEP_COMPAT)

Aşağıdaki rotalar bilinçli olarak korunur; eski kayıtlar, yer imleri, olay
geçmişi ve tarayıcı geçmişi kırılmaz:

| Rota | Durum | Gerekçe |
|---|---|---|
| `/notes` | KEEP_COMPAT | Eski Aktivite kayıtları ve `?focus=<uuid>` derin bağlantıları Bilgi köprüsüne gelir |
| `/statistics` | KEEP_COMPAT | `/activity`'ye kalıcı yönlendirme |
| `/study` | KEEP_COMPAT | Öğrenme modülünün eski yolu |
| `/inbox` | KEEP_COMPAT | Triyaj akışının kanonik yüzeyi; Home'daki `#/?triage=inbox` derin bağlantısı odak modunu açar |
| `/review/daily`, `/review/weekly` | Aktif | Değerlendirme kök hedefi + günlük/haftalık ayrımı |
| `/documents` | Gizli | Drive belgeleri kariyer bağlamında yaşar; eski `?focus=<id>` bağlantıları çalışır |
| `/feed` | Gizli | Okuma akışı Home'un ve RSS sayfasının parçası; eski bağlantı yaşar |
| `/activity/heatmap` | Gizli | Harita Etkinlik sayfasının içinde; eski bağlantı yaşar |
| `/health`, `/sources` | Gizli | Sahibi Ayarlar → Durum & Kaynaklar; bildirim ve hata ayıklama bağlantıları çalışır |
| `/media/...` alt rotaları | KEEP_COMPAT | Koleksiyon, istatistik, çöp, yaklaşan görünümleri |
| `/habits`, `/planner` | Aktif | Plan alanının alt satırları |
| `/opportunities?tab=...&focus=...` | Aktif | Sekme kimlikleri ve filtre parametreleri sözleşmedir |

`/today` rotası YOKTUR ve eklenmez: eski `#/today?triage=inbox` bağlantıları
kanonik `#/inbox` hedefine taşındı (toast aksiyonları ve Inbox komutları).

## 6b. Kaynak operasyonları ve sağlık dürüstlüğü

**Tek yüzey, iki çerçeve.** Kaynak operasyonlarının (katalog, yenileme, kapsam,
koşu geçmişi, önbellek, sorun süzgeci) TEK uygulaması
`frontend/src/modules/sources/` altındadır: sorgular ve mutasyonlar
`sourceOps.ts` içinde paylaşılır, sunum `SourcesWorkspace.tsx` içindedir.

```text
Sistem → Kaynaklar (#/sources, ?scope=media)  → tanı odaklı çerçeve
Kariyer → Kaynaklar (#/opportunities?tab=sources) → edinim odaklı çerçeve
```

İki yüzey aynı sorgu/mutasyon katmanını kullanır; ikinci bir fetch yolu YOKTUR.
`/sources` rotası ve `?scope=media` bilinçli olarak korunur (§6 tablosu).

**Yenileme dürüstlüğü.** İki eylem vardır ve etiketleri gerçek kapsamı söyler:

```text
Kritik + normal yenile → POST /sources/refresh { mode: "general" }   (slow_optin hariç)
Tam tarama             → POST /sources/refresh { mode: "full" }      (slow_optin dahil, onay ister)
```

Gövdesiz/`{}` istek "tümünü çek" DEĞİLDİR: backend varsayılanı `general`'dır ve
yavaş/isteğe bağlı kaynakları dışarıda bırakır.

**Sağlık dürüstlüğü kuralları (tüm yüzeyler):**

- `NO DATA ≠ HEALTHY`, `QUERY ERROR ≠ HEALTHY`, `UNKNOWN ≠ HEALTHY`. Bir
  tanılama sorgusu düştüğünde arayüz "sağlıklı" demez; "alınamadı — bu, sorun
  olmadığı anlamına gelmez" der ve yeniden denemeyi teklif eder
  (`@/core/DataState`).
- Sağlık EŞİKLERİ istemcide hesaplanmaz: karar backend özetinden gelir
  (`/sources/coverage`: `circuit_open`, `last_status`, `consecutive_empty`).
- Tek `empty` koşu sorun değildir; üst üste üç boş koşu "sessiz" sinyalidir.
- `disabled`/`kapalı` bir hata DEĞİLDİR (kapalı feed, kapalı worker, kapalı H6).
- Durum sözlüğü TEK kaynaktır: `@/core/sourceStatus` (etiket + ton + ilgi).
  Ham enum kullanıcıya çıkmaz; hata sınıfları okunaklı etiketlenir
  (`http_429` → "429", `parser` → "ayrıştırma").
- Genel durum skor değildir; bilinmeyen bir alt sistem varken "Sağlıklı"
  denmez, "Durum kısmen bilinmiyor" denir.

**Yerel ≠ internet.** `navigator.onLine` "internet yok" demektir, "yerel sunucu
kapalı" değil. Bu yüzden yerel işler çevrimdışı da çalışır (yerel yedek, kaynak
önbelleği bakımı, ayar yazmaları, Vault indeksi); yalnız dış ağa çıkan yazmalar
(`/auth/*`, `/system/refresh`, kaynak/RSS yenileme, hava durumu, medya
sağlayıcı senkronu) çevrimdışı kapıdadır (`@/core/api`).

**Ajan tanılaması.** Kullanıcı sorunları ve sistem durumunu Markdown paketi
olarak kopyalayabilir (`@/core/diagnostics`, saf biçimlendiriciler). Paket
yalnız var olan tanılama verisini taşır; sır, mutlak dosya yolu veya ham istek
başlığı içermez, verisi alınamayan bölümü "unknown — request failed" olarak
YAZAR ve talimat metni eklemez. Hata metinleri backend'de maskelenir
(`core/runs.py`).

---

## 7. Değişmeyen sınırlar

- Router kütüphanesi YOKTUR ve eklenmez: mevcut hash router derin bağlantı,
  parametre, geri/ileri ve rota eşleşmesini karşılar (`app/router.ts`).
- Tasarım sistemi değişmedi: renk, tipografi, boyut ve yarıçap tokenlardan gelir
  (`@/core/ui`).
- Komut paleti ikincil navigasyondur: sidebar'dan kalkan her capability en az
  bir yoldan erişilebilir kalır (Cmd/Ctrl+K, alt rota, Sabitlenenler veya
  bağlamsal eylem). "Daha fazla" kavramı YOKTUR; her hedef ya kök satırdır ya
  bir alanın alt satırıdır ya da sahipli bir yüzeyden (ör. Ayarlar → Durum &
  Kaynaklar) erişilir.
- Workspace deseni ortak kalır: 28 yüzeyin 24'ü `Workspace` /
  `WorkspaceRail*` / `WorkspaceScrollArea` primitiflerini kullanır. Bilinçli
  istisnalar: Home (pano), Odak (zamanlayıcı), Bilgi (Vault köprüsü), RSS
  (kendi iki panelli düzeni).

### Hedefler

`goal` registry modülü `/goals` rotasında birincil **Hedefler** alanına aittir.
Genel Bakış, Hedefler, Plan ve Geçmiş aynı çalışma alanındadır. Kariyer içindeki
eski hedef editörü özet ve Hedefleri aç bağlantısına dönüştürüldü.
