# forkOS — U2 Shell v2 Dokümantasyonu ve Sözleşmesi

Bu doküman forkOS'un **U2 — Shell v2** fazında yenilenen global kabuk (shell), navigasyon, sidebar, üst araç çubuğu (header), komut paleti ve çalışma alanı modlarının kanonik mimari ve sözleşme kaydıdır.

---

## 1. Executive Summary & Design Philosophy

U2 fazının temel hedefi, uygulamanın dış çeperini (chrome / shell / navigation) karmaşadan arındırmak ve:

> **"The application itself is the workspace."**

ilkesini hayata geçirmektir.

Temel tasarım prensipleri:
- **Calm & Low-Noise:** Normal sistem durumunda (`healthy`, senkronize, yerel) araç çubuğu sessizdir. Kalıcı yeşil rozetler, gereksiz durum çipleri veya göz yoran animasyonlar bulunmaz.
- **Dense & Fast:** 36px/38px yükseklikler, 56px daraltılmış ray (rail), 150ms geçişler (`motion-reduce:transition-none`).
- **Linear-First & Desktop-Native:** Mac pencere yapısı ve Linear çalışma alanı hiyerarşisi referans alınmıştır.
- **Strict Scope Boundaries:** Sıfır backend değişikliği, U3 pilot ekranlarının (Today, Projects, Opportunities) iç içeriklerine dokunulmadan shell seviyesinde slot/contract hazırlanması.

---

## 2. Shell Architecture (Kabuk Mimarisi)

Uygulama hiyerarşisi tek bir kök flexbox altında iki ana sütundan oluşur:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ App Root (min-h-dvh bg-canvas text-primary)                            │
├──────────────┬─────────────────────────────────────────────────────────┤
│ AppSidebar   │ Workspace Column (flex-1 flex-col bg-canvas)            │
│              ├─────────────────────────────────────────────────────────┤
│ (240px wide  │ WorkspaceHeader (h-12 border-b border-subtle bg-canvas) │
│  or 56px     │  [Breadcrumb: Alan / Sayfa]          [Aksiyon Bütçesi]  │
│  rail mode)  ├─────────────────────────────────────────────────────────┤
│              │ Workspace Page Content                                  │
│              │  ┌───────────────────────────────────────────────────┐  │
│              │  │ WorkspaceToolbar (Opsiyonel Sayfa-İçi Araçlar)    │  │
│              │  ├───────────────────────────────────────────────────┤  │
│              │  │ WorkspaceBody (mode="bounded" | mode="full")      │  │
│              │  └───────────────────────────────────────────────────┘  │
└──────────────┴─────────────────────────────────────────────────────────┘
```

---

## 3. Navigation Deep-Routing Contract

`frontend/src/core/navigation.ts` içinde derin rota eşleme (`areaForPath`, `rowIsActive`) kuralları standartlaştırılmıştır:

1. **Prefix-Matching & Subroute Desteği:**
   - `/projects/proj-123` veya `/opportunities/opp-456` gibi alt rotalara gidildiğinde, ebeveyn ürün alanı (`areaForPath`) ve ilgili kenar çubuğu satırı (`rowIsActive`) aktif kalır.
   - Eşleme mantığı `path === row.path || path.startsWith(`${row.path}/`)` biçiminde çalışır; böylece derin gezinmelerde kenar çubuğu seçili durumunu kaybetmez.
2. **Sorgu Parametresi Ayrımı:**
   - `row.query` tanımlı satırlarda (örn. filtrelenmiş görünümler) `params.toString()` doğrulanır; query parametresi olmayan genel satırlarda alt yollar doğru şekilde ebeveynine bağlanır.

---

## 4. AppSidebar v2 Sözleşmesi

`frontend/src/core/shell/AppSidebar.tsx` bileşeni iki ana modda çalışır:

1. **Genişletilmiş Mod (240px / `w-sidebar`):**
   - **Başlık:** `f` marka ikonu (28px), `forkOS` başlığı, sağda kenar çubuğunu daraltma butonu (`PanelLeftClose`).
   - **Tümünü Genişlet / Daralt:** Alt grupları tek tıkla açıp kapatan kompakt `h-8` kontrol.
   - **Alanlar ve Satırlar:** Tek hedefli modüller doğrudan bağlantı (`SidebarLink`), çoklu görünüme sahip alanlar (`Plan`, `Öğrenme`, `Kütüphane`) akordeon başlığı ve alt satırlar olarak listelenir.
   - **Footer:** `Ayarlar` (`/settings`) sistem bağlantısı ve "Yerel çalışma alanı" etiketi.
2. **Daraltılmış Ray Modu (56px / `w-rail`):**
   - Masaüstünde kenar çubuğu `56px` genişliğe çekilir. İçerik alanı genişler.
   - **Uçan Menü (CollapsedAreaFlyout):** Alt satırları olan ürün alanlarına tıklandığında veya odaklanıldığında rayın hemen sağında (`left-[calc(100%+0.5rem)]`) uçan menü açılır.
   - **Erişilebilirlik & Klavye Etkileşimi:**
     - Yalnızca fare üzerine gelme (hover) değil; **tıklama (click)** ve **klavye (`Enter`, `Space`, `ArrowRight`)** ile açılır.
     - `Escape` veya `ArrowLeft` basıldığında menü kapanır ve odak tetikleyici butona geri döner.
     - Menü açıldığında ilk bağlantı otomatik odaklanır (`firstLinkRef.current?.focus()`).
   - **Overflow & Clipping Koruması:** Daraltılmış modda masaüstü gezinme konteyneri `md:overflow-visible` ve `md:transform-none` sınıflarını alarak popover'ın kesilmesini (clipping) engeller.

---

## 5. WorkspaceHeader / App Toolbar v2 Sözleşmesi

`frontend/src/core/shell/WorkspaceHeader.tsx` sayfanın üst bağlamını ve global eylemlerini yönetir:

1. **Sol Bölge — Bağlamsal Sayfa Kimliği (Contextual Page Identity):**
   - Ray daraltılmışsa kenar çubuğunu genişletme butonu (`PanelLeftOpen`) en solda yer alır.
   - Alan ikonu (örn. `Home`, `Layers`, `Rss`, `Sliders`) ve hiyerarşik ekmek kırıntısı başlığı (`Area / Page` veya tekil `Page`).
2. **Sağ Bölge — Katı Aksiyon Bütçesi (Strict Action Budget):**
   - Maksimum 4-5 öğe ile sınırlandırılmıştır:
     1. **Arama / Komut Tetikleyici:** Geniş ekranda `Ara veya komut... Ctrl K`, dar ekranda kompakt arama ikon butonu.
     2. **Aktif Odak (ActiveFocusIndicator):** Yalnızca aktif bir pomodoro/odak oturumu varsa render edilir.
     3. **Yenileme (RefreshCw):** Yalnızca aktif bir senkronizasyon/çalışma varsa dönen göstergeye dönüşür veya manuel yenileme başlatır.
     4. **Bildirim Zili (NotificationPanel):** Okunmamış sistem bildirimleri varsa sayaç rozetiyle açılır.
     5. **Taşma Menüsü (`MoreHorizontal` / `...`):** Seyrek kullanılan tüm global araçları toplar.
3. **Epistemik Sessizlik İlkesi (`hideWhenHealthy`):**
   - Sistem normal, yerel ve senkronize iken kalıcı yeşil durum LED'i veya "senkronize" rozeti render edilmez (`StatusLed` `hideWhenHealthy={true}`).
   - Yalnızca dikkat gerektiren `offline`, `degraded`, hata veya aktif kaynak yenileme durumlarında görünür uyarı yüzeyi devreye girer.
4. **Taşma Menüsü (Overflow Popover):**
   - **Tema Değiştirici:** Tek tıkla açık/koyu tema geçişi.
   - **Yenileme Kapsamı:** Kritik kaynaklar, Standart yenileme, Tam yenileme kapsam seçicisi.
   - **Hızlı Araçlar:** `/health` (Sistem durumu paneli), `/sources` (Kaynak sağlığı ve akışlar), `/settings` (Ayarlar).

---

## 6. Page-Local Toolbar & Workspace Modes Sözleşmesi

U3 pilot ekranlarının (Today, Projects, Opportunities) global header'ı kirletmeden sayfa-içi araçlarını konumlandırabilmesi için `frontend/src/core/workspace/` içinde iki temel primitif oluşturulmuştur:

```tsx
import { Workspace, WorkspaceToolbar, WorkspaceBody } from "@/core/workspace";
```

1. **`WorkspaceToolbar` Sözleşmesi:**
   - Sayfa başlığı altında, filtreler, sıralama, görünüm seçicileri (liste/kanban/ızgara) ve birincil sayfa eylemleri için ayrılmış yüzeydir.
   - Sol (`actions`) ve sağ (`rightActions`) slotları ile Linear tarzı araç çubuğu yerleşimi sunar.
2. **`WorkspaceBody` Sözleşmesi:**
   - `mode="bounded"`: Okuma, form, ayarlar ve odak ekranları için `max-w-5xl` genişlik sınırı ve dengeli padding uygular.
   - `mode="full"`: Kanban panoları, 3 sütunlu RSS okuyucusu, medya ızgaraları gibi tüm genişliği kullanması gereken ekranlar için sıfır yatay kısıtlama sağlar.

---

## 7. Command Palette v2 Sözleşmesi

`frontend/src/core/CommandPalette.tsx` tüm uygulamada `Cmd+K` / `Ctrl+K` ile açılan Linear/Raycast benzeri komut merkezidir:

1. **Kısayollar:**
   - `Cmd+K` / `Ctrl+K`: Paleti açar.
   - `Cmd+,` / `Ctrl+,`: Doğrudan `#/settings` (Ayarlar) sayfasına gider.
   - `Escape`: Paleti kapatır; girdi modundaysa önce girdi modundan çıkar.
2. **Anlamsal Gruplandırma:**
   - **`GEZİN`:** Tüm kayıtlı modüllerin ve ürün alanlarının birincil ve alt sayfalarını listeler (`Home`, `Plan / Görevler`, `Projeler`, `Finans` vb.).
   - **`ARAMA SONUÇLARI`:** `/api/search` üzerinden gelen global varlıkları (projeler, görevler, yer imleri) türe göre rozetleyerek sunar.
   - **`KOMUTLAR VE EYLEMLER`:** Modül komutları (örn. "Yeni görev", "İçe aktar") ve kabuk eylemleri (örn. "Temayı değiştir", "Ayarları aç").
3. **Görsel Tasarım:**
   - `bg-surface`, `rounded-overlay`, `shadow-overlay`, `border-strong`, alt kısımda klavye yönlendirme rozetleri (`↑↓ gez`, `↵ aç`, `esc kapat`).

---

## 8. Responsive Shell Behavior (Duyarlı Kabuk Davranışı)

| Görünüm Genişliği | Sidebar Davranışı | Header Davranışı | İçerik Davranışı |
|---|---|---|---|
| **≥ 1440px (Geniş Masaüstü)** | 240px açık (kullanıcı tercihine göre 56px ray) | Tam metin arama girdisi, breadcrumb, tam aksiyonlar | Geniş çalışma alanı / bounded içerik |
| **1024px – 1399px (Orta Masaüstü)** | 240px açık veya 56px ray | Tam veya yarı-kompakt arama | Dengeli oranlar |
| **768px – 1023px (Dar Masaüstü, örn. 850px)** | 56px daraltılmış ray + Uçan Menü (Flyout) | Kompakt arama ikon butonu + Overflow menü | Tekil veya iki sütunlu ızgara |
| **< 768px (Mobil)** | Sol çekmece (drawer overlay + backdrop scrim) | Mobil hamburger menü butonu | Tek sütun dikey akış |

---

## 9. Native macOS Mental Model Karşılıkları

forkOS web tabanlı olmasına rağmen macOS masaüstü tasarım metaforlarını birebir yansıtır:

| forkOS Shell Öğesi | Native macOS Karşılığı | Davranış Benzerliği |
|---|---|---|
| `AppSidebar` (240px) | `NSSplitViewItem.Sidebar` | Pencerenin soluna sabitlenen kategori ve bölüm listesi |
| `AppSidebar` (56px Rail) | Kompakt Simge Rayı (`Source List Mini`) | Sadece simgelerle yer tasarrufu sağlayan ince çubuk |
| `CollapsedAreaFlyout` | `NSPopover` / `NSMenu` | Ray öğesine basıldığında sağa açılan alt menü |
| `WorkspaceHeader` | `NSToolbar` (Unified Header) | Pencere başlığı ve aksiyon bütçesini birleştiren sakin şerit |
| `CommandPalette` | Spotlight / Raycast Window | Hızlı gezinme ve arama için klavye-odaklı modal |
| `OverflowMenu` | Menü Çubuğu Eklentisi / Overflow Action | Seyrek kullanılan sistem ayarları popover'ı |

---

## 10. U3 Pilot Screen Integration Contract

U3 fazında yeniden tasarlanacak üç pilot ekran (`Today`, `Projects`, `Opportunities`) için U2 kabuk sözleşmesi şu kuralları zorunlu kılar:

1. **Global Header'a Sayfa Eylemi Eklenemez:**
   - Ekran filtreleri, sıralama düğmeleri veya sayfa-içi "Yeni Ekle" butonları global `WorkspaceHeader` içine konulamaz.
   - Bu kontroller sayfa içinde `WorkspaceToolbar` slotu kullanılarak konumlandırılmalıdır.
2. **Konteyner Genişlik Seçimi:**
   - `Today`: `WorkspaceBody mode="bounded"` (max-w-5xl) veya sayfa özel akışı.
   - `Projects`: Sol ray + sağ detay için `WorkspaceBody mode="full"`.
   - `Opportunities`: Kanban modu için `mode="full"`, liste modu için `mode="bounded"`.
3. **Breadcrumb / Title Doğrulaması:**
   - Modül başlığı ve ikonu `ModuleSpec` ve `EntityTypeSpec` üzerinden otomatik türetilir; sayfa içinde ikinci bir H1 yazarken header ile çelişki üretilmemelidir.

---

## 11. Real Visual Verification Report (VISUALLY-CONFIRMED)

Test ortamı: Headless Chromium (`Brave Browser Beta`), yerel API ve frontend sunucusu (`127.0.0.1:5173`).

| Ekran / Yüzey | Tema | Genişlik | Değerlendirme | Bulgular & Görsel Kanıt |
|---|---|---:|---|---|
| **Today** (`/#/`) | Light | 1440px | **PASS** | Sessiz header; breadcrumb `Home`; arama çubuğu ve aksiyon bütçesi dengeli; unboxed 3 sütun. |
| **Today** (`/#/`) | Dark | 1440px | **PASS** | Koyu zemin `#0f1012`, sidebar `#141518`, header `#141518/95`. Kontrast sakin ve göz yormuyor. |
| **Today** (`/#/`) | Light | 1100px | **PASS** | 1100px'te 3 sütun orantılı daralıyor; yatay taşma sıfır. |
| **Today** (`/#/`) | Dark | 1100px | **PASS** | Koyu temada 1100px sütun oranları ve tipografi stabil. |
| **Today** (`/#/`) | Light | 850px | **PASS** | 850px dar masaüstünde tek sütun dikey akış; arama kompakt ikon butonuna geçiyor. |
| **Today** (`/#/`) | Dark | 850px | **PASS** | Koyu temada 850px kompakt yerleşim stabil. |
| **Projects** (`/#/projects`) | Light | 1440px | **PASS** | Breadcrumb `Projeler`; sol ray `bg-surface-sunken` ayrımı; form ve kilometre taşları net. |
| **Projects** (`/#/projects`) | Dark | 1440px | **PASS** | Koyu temada sol ray `#1f2026`, form yüzeyi `#18191f`. |
| **Opportunities** (`/#/opportunities`) | Light | 1440px | **PASS** | Breadcrumb `Kariyer`; filtre araçları hizalı; liste görünümü taranabilir. |
| **Opportunities** (`/#/opportunities`) | Dark | 1440px | **PASS** | Koyu temada satır sınırları fısıltı düzeyinde; puan rozetleri okunuyor. |
| **RSS** (`/#/rss`) | Light | 1440px | **PASS** | Breadcrumb `Kütüphane / RSS`; 3 sütunlu okuma kabuğu; unboxed Linear hissi yüksek. |
| **RSS** (`/#/rss`) | Dark | 1440px | **PASS** | Koyu temada 3 sütunlu RSS çalışma alanı stabil. |
| **Settings** (`/#/settings`) | Light | 1440px | **PASS** | Breadcrumb `Sistem / Ayarlar`; sol ayar sekmeleri, sağ form yüzeyi; temiz beyaz kartlar. |
| **Settings** (`/#/settings`) | Dark | 1440px | **PASS** | Koyu temada ayar sekmeleri ve radyo seçenekleri net. |
| **Collapsed Rail + Flyout** | Light | 1440px | **PASS** | 56px ray; `Plan` alanına gelindiğinde sağa açılan uçan menü (`Görevler`, `Haftalık plan`, `Rutinler`, `Takvim`, `Odak`). |
| **Collapsed Rail + Flyout** | Light | 850px | **PASS** | 850px'te daraltılmış ray üzerinde uçan menü kusursuz açılıyor; taşma veya kırılma yok. |
| **Header Overflow Menu** | Light | 1440px | **PASS** | `...` tıklandığında açılan popover: Tema düğmesi, Yenileme kapsamı seçicisi, Hızlı Araçlar (`/health`, `/sources`, `/settings`). |
| **Command Palette (Cmd+K)** | Light | 1440px | **PASS** | Merkez overlay; `GEZİN` başlığı altında ürün alanları ve sayfalar; klavye ipuçları (`↑↓ gez`, `↵ aç`, `esc kapat`). |

---

## 12. U2 Visual Questions Evaluation

1. **Header sakin ve sessiz mi? Normal sistem durumunda kalıcı yeşil rozetler/gürültü kayboldu mu?**  
   **PASS.** `StatusLed` bileşenine eklenen `hideWhenHealthy` özelliği sayesinde sistem normal ve sağlıklı iken header'da hiçbir kalıcı yeşil çip veya durum ledi render edilmez. Yalnızca dikkat gerektiren hata veya aktif senkronizasyon durumunda yüzey görünür.

2. **Bağlamsal sayfa kimliği (Breadcrumb: Alan / Sayfa) açık, net ve kalabalıktan uzak mı?**  
   **PASS.** Header'ın solunda modül ikonu ve hiyerarşik ekmek kırıntısı (örn. `Kütüphane / RSS`, `Sistem / Ayarlar`) kompakt bir şekilde yer alır.

3. **Header aksiyon bütçesi disiplinli mi (Arama + Aktif Odak + Yenileme + Taşma)?**  
   **PASS.** Sağ bölge kesin olarak 4 ana kontrol ile sınırlandırılmıştır; dağınık butonlar kaldırılmış ve taşma menüsüne toplanmıştır.

4. **Taşma menüsü (Overflow) tema, yenileme kapsamı ve ikincil rotaları temiz biçimde organize ediyor mu?**  
   **PASS.** `MoreHorizontal` butonuna tıklandığında açılan popover Görünüm (Tema), Yenileme kapsamı ve Hızlı Araçlar (`/health`, `/sources`, `/settings`) bölümlerini düzenli ve okunur bir hiyerarşide sunmaktadır.

5. **Sidebar daraltılmış ray modu (56px) stabil, masaüstü-uyumlu ve sakin hissettiriyor mu?**  
   **PASS.** Ray 56px genişlikte yalnızca alan ikonlarını barındırır; sol altta Ayarlar ikonu yer alır; geçiş 150ms sürmektedir.

6. **Daraltılmış ray uçan menüsü (Flyout) hem tıklama hem klavye ile (`Enter`, `Space`, `ArrowRight`, `Esc`) güvenilir çalışıyor mu?**  
   **PASS.** Uçan menü hover'a ek olarak tıklama ve klavye yön tuşları (`ArrowRight`, `Enter`, `Space`) ile açılmakta; `Escape` ile kapanarak odağı tetikleyiciye iade etmektedir.

7. **Derin rotalarda (`/projects/...`, `/rss?article=...`) ebeveyn navigasyon öğesi ve alan vurgusu korunuyor mu?**  
   **PASS.** `navigation.ts` içindeki prefix matching sayesinde `/projects/p-test` gibi alt rotalara gidildiğinde sidebar'daki `Projeler` satırı `aria-current="page"` ve aktif arka planını korumaktadır.

8. **Komut paleti (`Cmd+K`) anlamsal grupları (`Gezin`, `Arama Sonuçları`, `Komutlar`) ve kısayol yönlendirmelerini net gösteriyor mu?**  
   **PASS.** `cmdk` tabanlı palet `GEZİN` grubunda sayfaları, arama girdisiyle global varlıkları ve komutları net ayırıcı başlıklarla listelemektedir.

9. **`Cmd+,` / `Ctrl+,` kısayolu doğrudan Ayarlar sayfasına gidiyor mu?**  
   **PASS.** `Cmd+,` tuşlandığında palet açılmadan doğrudan `#/settings` rotasına yönlendirme gerçekleşmektedir.

10. **Tüm viewport'larda (1440px, 1100px, 850px) kabuk yatay taşma veya kırılma olmadan zarifçe uyum sağlıyor mu?**  
    **PASS.** 850px'te sidebar otomatik ray moduna, header arama girdisi kompakt ikon butonuna dönmekte; hiçbir yatay kaydırma çubuğu oluşmamaktadır.
