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
Home            /                     (bugünün planı, dikkat, kararlar)
Plan            /todos                Görevler · Haftalık plan · Rutinler · Takvim · Odak
Projeler        /projects
Kariyer         /opportunities        Keşfet · Başvurular · Duyurular · Profil · Kaynaklar
Öğrenme         /learning             Öğrenme · Kartlar · Tekrar
Kütüphane       /bookmarks            Yer İmleri · Belgeler · RSS · Okuma Akışı (/feed) · Medya · Bilgi
────────────────────────────────────────────────────────────────────────────
Sabitlenenler   (kullanıcının sabitlediği kayıtlı görünümler)
Daha fazla      Finans · Etkinlik & Ritim → Isı Haritası (/activity/heatmap) · Değerlendirme
────────────────────────────────────────────────────────────────────────────
Sistem          Sistem Durumu (/health, /sources) · Ayarlar (/settings)
```

Kurallar:

- Temiz kurulumda yalnız kök alanlar açıktır; alt satırlar kapalı başlar ve
  aktif rota kendi alanını otomatik açar (katlanma tercihi
  `forkos.sidebar.areas`). Ağaç görsel olarak konuşur: kök satır `h-9`/16px
  ikon, alan hedefi `h-8`/14px, hedefin alt rotası `h-7`/13px + daha derin girinti.
- Bir modül **çalışıyor olabilir** ama birincil navigasyonda satır tutmaz
  (ör. `inbox` bir triyaj akışıdır; girişi Home'daki gelen kutusu yüzeyidir).
  Bu, modülü devre dışı bırakmak DEĞİLDİR: rota, widget'lar ve komutlar aynen
  çalışır.
- Domain/backend modülleri birleştirilmez. Plan altındaki `todo`, `calendar` ve
  `pomodoro` ayrı servislerdir; yalnız aynı zihinsel çalışma alanında sunulur.
- Alan satırları registry'den türetilir: modülün birincil rotası + `navigation:
  "child"` işaretli rotalar + alan `links`'leri. Yeni bir alt rota eklemek için
  modül kaydına yazmak yeterlidir.

## 2. Home adlandırma sözleşmesi

Kullanıcıya görünen yüzeyin adı **Home**'dur. Teknik ad alanı `today` olarak
KALIR (isim değişikliği sözleşmeyi kırmaz):

| Katman | Ad | Not |
|---|---|---|
| Modül kimliği | `today` | Değişmez |
| Ayar anahtarları | `today.widget_order`, `today.widget_hidden`, `today.auto_suggestions` | Değişmez |
| Backend uçları | `/api/today/agenda` | Değişmez |
| Widget kimlikleri | `today.agenda`, `today.attention`, ... | Değişmez (kullanıcı tercihlerinin anahtarı) |
| localStorage | `lifeos.todayWidgetOrder`, `lifeos.todayWidgetHidden` | Değişmez |
| Görünen ad | **Home** | Sidebar, sekme, başlık |

Zamansal Türkçe ifadeler normal kalır: "Bugünün planı", "Bugün 3 görev",
"Bugüne ekle", "Bugün tekrar".

## 3. Home bileşenleri (temiz kurulum)

```text
Hero
Bekleyen kararlar   (H7; boşken hiç çizilmez)
Şimdi ve sırada     (süren kayıt + en fazla 3 sıradaki)
Dikkat              (son tarihler + takipler + okunmamış bildirimler; ≤ 5 satır)
Bugünün planı
```

Home bölgeleri (widget kimlikleri ve kullanıcı tercihleri DEĞİŞMEDİ):

```text
priority   Bekleyen kararlar (varsa tam genişlik; yoksa çizilmez)
main       Şimdi ve sırada · Bugünün planı
rail       Dikkat (+ Geciken görevler açılırsa)
secondary  Akış · Isı haritası · Ritim · Kartlar · Öğrenme · Medya · ...
```

Boş bölge ne çizilir ne yer tutar: main boşsa rail tek başına, rail boşsa main
tam genişlik. Eski "Plan/Akış/Durum" üç sütun modeli kaldırıldı; onun yerine
içerikten türeyen bölge şablonu var (`--home-cols`).

Yüzey sayısı bilinçli olarak azdır: Home "her modülden biraz" panosu değil,
"şu an ne yapıyorum, ne dikkat istiyor, benden hangi karar bekleniyor"
ekranıdır. İkincil yüzeyler (Akış, emek haritası, ritim, kart tekrarı, gelen
kutusu, öğrenme, medya devam, gecikenler, hızlı bağlantılar, belgeler, takvim,
finans, proje, kaynak sağlığı, değerlendirme) **kayıtlıdır** ve Ayarlar > Home
üzerinden tek tek açılabilir; Odaklı/Genel bakış presetleri korunur.

Kurallar:

- Bir uç hata verirse yalnız o kaynak düşer; Dikkat yüzeyi kalanı gösterir ve
  "Bazı kaynaklara ulaşılamadı" der. Hiçbir kaynak veri vermezse yüzey hiç
  çizilmez (sessizlik başarıdır).
- `Home render` canonical mutation TETİKLEMEZ: sayfa açılışı hiçbir ajan
  eylemi başlatmaz.
- Home'un temiz kurulum fan-out'u `modules/today/homeFanout.test.tsx` ile
  sabitlenmiştir (≤ 12 uç, tekrar yok).
- Briefing yüzeyi **ertelendi**: H5 review intelligence bugün yalnız ajan/MCP
  yüzeyinde (`forkos_review_intelligence`, `forkos_briefing`) var; HTTP sunumu
  yok. H5 çıktısının bir kısmı H6 proaktif bildirimlerine katlanıp Dikkat
  yüzeyine düşer. Yeni bir uç yazmak yerine bu bağlantı noktası korundu.

## 4. Sabitlenmiş görünümler

- Kaydetme/sabitleme/silme: `frontend/src/core/SavedViewPicker.tsx`
  (`GET|POST /views`, `PATCH|DELETE /views/{id}`).
- Sidebar "Sabitlenenler" bölümü sunucu sırasını korur
  (`pinned` → `position` → `id`).
- Derin bağlantı sözleşmesi: `#/<rota>?saved=<gorunum-id>`. Kenar çubuğu
  satırı bu bağlantıyı üretir; sayfa kimliği çözer ve filtreyi BİR KEZ uygular.
- Bağlı çalışma alanları: **Kariyer** (`opportunity`), **Medya** (`media`),
  **Yer İmleri** (`bookmarks`), **Görevler** (`todo`).
- Modül kimliği = frontend registry kimliği. Backend bu alanı opak taşır.
- Bilinmeyen/eski kimlik, hedefi kapalı modül ve bozuk yanıt **sessizce yok
  sayılır**: sidebar veya çalışma alanı çökmez.
- Filtre sözleşmesi modül başına kapalıdır; tanınmayan anahtar uygulanmaz
  (Kariyer: `sanitizeOpportunityFilters`, Medya: URL parametre adları,
  Yer İmleri/`todo`: alan bazlı eşleme).

## 5. Ayarlar

Ray iki anlamsal gruba ayrılır:

```text
Tercihler   Genel & Görünüm · Home · Bildirimler & Çevre · Modüller · Kariyer profili
Sistem      Brain & Agent · Entegrasyonlar · Sistem & Yedekleme
```

- **Brain & Agent** (`?tab=brain`) zihin sınırlarının tek yüzeyidir: Brain
  Interface (MCP) durumu, f0rknbrain Vault köprüsü, H4 yerel biliş, H6
  proaktivite ve H7 kararlarının **salt okunur** özeti ile Hermes bağlantı
  tarifi. Onaylama/yürütme eylemleri burada DEĞİLDİR; tek karar yüzeyi
  Home → Bekleyen kararlar'dır.
- **Entegrasyonlar** yalnız DIŞ sağlayıcıları barındırır (Google Drive,
  GitHub, medya sağlayıcıları). Obsidian Vault artık burada değildir:
  f0rknbrain bir sağlayıcı değil, bilgi sahibidir.
- **Bildirimler & Çevre** teslim/ortam tercihlerini tutar (masaüstü
  bildirimleri, hava durumu); H6 proaktivite oradan Brain & Agent'a taşındı.
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
- Sekme kimlikleri (`?tab=general|today|modules|notifications|career|brain|
  integrations|backup`) ve `?section=media-links` derin bağlantısı korunur.

## 6. Route uyumluluğu (KEEP_COMPAT)

Aşağıdaki rotalar bilinçli olarak korunur; eski kayıtlar, yer imleri, olay
geçmişi ve tarayıcı geçmişi kırılmaz:

| Rota | Durum | Gerekçe |
|---|---|---|
| `/notes` | KEEP_COMPAT | Eski Aktivite kayıtları ve `?focus=<uuid>` derin bağlantıları Bilgi köprüsüne gelir |
| `/statistics` | KEEP_COMPAT | `/activity`'ye kalıcı yönlendirme |
| `/study` | KEEP_COMPAT | Öğrenme modülünün eski yolu |
| `/inbox` | KEEP_COMPAT | Triyaj akışı; Home'dan `?triage=inbox` ile açılır |
| `/review/daily`, `/review/weekly` | KEEP_COMPAT | Uzun kuyrukta ("Daha fazla"); widget/komut girişleri durur |
| `/media/...` alt rotaları | KEEP_COMPAT | Koleksiyon, istatistik, çöp, yaklaşan görünümleri |
| `/today?triage=...` | KEEP_COMPAT | Eski Home derin bağlantıları (`/` ile aynı sayfa) |
| `/habits`, `/planner` | Aktif | Plan alanının alt satırları |
| `/opportunities?tab=...&focus=...` | Aktif | Sekme kimlikleri ve filtre parametreleri sözleşmedir |

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
  bir yoldan erişilebilir kalır (Cmd/Ctrl+K, alt rota, Sabitlenenler, Daha
  fazla veya bağlamsal eylem).
- Workspace deseni ortak kalır: 28 yüzeyin 24'ü `Workspace` /
  `WorkspaceRail*` / `WorkspaceScrollArea` primitiflerini kullanır. Bilinçli
  istisnalar: Home (pano), Odak (zamanlayıcı), Bilgi (Vault köprüsü), RSS
  (kendi iki panelli düzeni).
