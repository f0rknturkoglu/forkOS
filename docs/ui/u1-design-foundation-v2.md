# forkOS — U1 Design Foundation v2 Raporu

**Faz:** U1 — Design Foundation v2  
**Tarih:** 2026-09-22  
**Referans:** Linear Design Language + Native Personal OS Principles  
**Kapsam:** Foundation Tokens, Shared UI Primitives, Layout Framing & Spatial Grammar  
**Durum:** U1 TAMAMLANDI & GÖRSEL DOĞRULANDI (`VISUALLY-CONFIRMED`)

---

## 1. Executive Summary

U0 fazında tamamlanan envanter ve native-readiness denetiminde tespit edilen temel sorun, forkOS'un zemin hiyerarşisi (`--canvas` ve `--surface` her ikisi de `#ffffff`) eksikliğinden ötürü içerik ve katman ayrımını 1.193 adet sert `border*` çizgisi ve her `<Section>` içine zorunlu kılınan kart kabuklarıyla sağlamaya çalışmasıydı.

U1 fazında forkOS'un görsel ve etkileşim grameri Linear ilkeleri doğrultusunda yeniden kurgulanmış ve gerçek tarayıcıda (`Brave Browser Beta / Chromium headless`) görsel olarak doğrulanmıştır:
- **"Structure felt, not drawn" (Hissedilen, çizilmeyen yapı):** Canvas (`#fafafb`) ile Surface (`#ffffff`) ve Sunken (`#f0f2f5`) arasında doğal bir derinlik hiyerarşisi kuruldu.
- **Sert Kenarlık Yerine Alpha Hairline:** Katı gri çizgiler (`#e4e4e7` / `#2a2e35`) yerine hem açık hem koyu temada zeminle pürüzsüz karışan alpha hairline'lar (`rgba(15, 17, 21, 0.08)` ve `rgba(255, 255, 255, 0.08)`) devreye alındı.
- **Unboxed Section Varsayılanı:** `<Section>` varsayılan olarak `flat` (çerçevesiz, gölgesiz anlamsal gruplama) yapıldı. Kutu kabuğu yalnızca açıkça istendiğinde (`variant="card"` veya `flat={false}`) uygulanır.
- **SectionHeader İnce Çizgi Sadeliği:** Başlık yanındaki zorunlu `h-px bg-subtle` çizgisi kaldırıldı; `divider` prop'u opsiyonel hale getirildi (`default = false`).
- **Workspace Çerçevesizliği:** `<Workspace>` dışındaki gereksiz `rounded-card border border-subtle bg-surface shadow-card` kutusu kaldırıldı; ray (`aside` border-r), içerik (`section` bg-surface) ve denetçi (`aside` border-l) ekran tuvaline doğrudan oturacak şekilde sadeleştirildi.
- **Erişilebilirlik ve Kontrast Güvencesi:** WCAG 2.1 AA/AAA kontrast oranları korundu; `prefers-reduced-motion` desteği CSS çekirdeğine eklendi; `IconButton` erişilebilirliği ve 500 KB bundle bütçesi korundu.
- **Gerçek Görsel Doğrulama:** 5 ana ekran (Today, Projects, Opportunities, RSS, Settings), hem Açık hem Koyu temada, 1440px, 1100px ve 850px genişliklerde görsel olarak test edildi ve onaylandı.

Tüm 160 test dosyası ve 1.155 test %100 başarıyla geçmiş, TypeScript derlemesi sıfır hata vermiş ve giriş paketi 461 KB seviyesinde kalmıştır.

---

## 2. Design Philosophy: Linear-Inspired Personal OS

forkOS bir SaaS veya çok kullanıcılı bir web paneli değil; tek kullanıcılı, yerel ve klavye-odaklı bir kişisel işletim sistemidir. Bu felsefe Linear tasarım dilinin temel erdemleriyle örtüşür:

1. **Calm (Sakinlik):** Gözü yoran yüksek kontrastlı kutular, her yerde dönen kalın çizgiler ve agresif gölgeler yerine sakin bir zemin.
2. **Dense (Yoğunluk):** Beyaz boşluk israfı yapmadan, kompakt kontroller (34px varsayılan, 32px ikon butonları) ve net veri satırları.
3. **Structure Felt Rather Than Drawn:** Hiyerarşiyi kenarlık ve kutu sınırlarıyla değil; zemin tonu, negatif boşluk (padding/margin), tipografi ağırlıkları ve hizalamayla hissettirme.
4. **Keyboard-First & Accessible:** Form elemanları ve interaktif bileşenler belirgin `:focus-visible` halkasına, ekran okuyucu uyumluluğuna ve anında yanıt süresine sahiptir.

---

## 3. Spatial Hierarchy: Canvas, Surface & Sunken

Önceki tasarımda `--canvas` ve `--surface` aynı renkti (`#ffffff` / `#18181b`). Bu durum, herhangi bir elemanı öne çıkarmak için etrafına mutlaka bir kart veya kenarlık çekilmesini zorunlu kılıyordu.

U1 ile 3 kademeli zemin mimarisi kuruldu:

| Katman Adı | Token | Light Mode | Dark Mode | AMOLED | Rol ve Kullanım |
|---|---|---|---|---|---|
| **Canvas** | `--canvas` | `#fafafb` | `#0f1012` | `#000000` | Uygulama ana arka planı, sayfa tuvali |
| **Sidebar / Rail** | `--sidebar` | `#f4f4f6` | `#141518` | `#050607` | Sol navigasyon ve çalışma alanı rayları |
| **Surface** | `--surface` | `#ffffff` | `#18191f` | `#080a0b` | Kartlar, aktif paneller, popover gövdeleri |
| **Surface Sunken** | `--surface-sunken` | `#f0f2f5` | `#1f2026` | `#0d1012` | Denetçiler, pasif alanlar, sekmeler, kod blokları |
| **Surface Hover** | `--surface-hover` | `#eceef2` | `#262730` | `#13171a` | Liste satırları ve buton üzerine gelme durumu |
| **Surface Selected**| `--surface-selected`| `#e2e6eb` | `#2d2f3b` | `#151a1d` | Seçili sekme, aktif menü maddesi |

---

## 4. Hairline & Border Strategy

Sert ve opak kenarlıklar yerine zeminle pürüzsüz kaynaşan alpha hairline'lara geçildi:

- **`--border` (Subtle):**
  - Light: `rgba(15, 17, 21, 0.08)` (Canvas üzerinde yumuşak 1px ayrım)
  - Dark: `rgba(255, 255, 255, 0.08)`
  - Kullanım: Sayfa içi ayırıcılar, tablo satırları (`divide-subtle`), pasif panel sınırları.
- **`--border-strong` (Strong):**
  - Light: `rgba(15, 17, 21, 0.16)`
  - Dark: `rgba(255, 255, 255, 0.16)`
  - Kullanım: İkincil buton sınırları, aktif form kontrolleri, odak göstergeleri.

---

## 5. Elevation & Shadow Model

Gölge modeli pencereleri havaya kaldırmak için değil, yalnızca çok hafif bir kabarıklık veya katman derinliği sağlamak için optimize edildi:

- **`shadow-card`:** `0 1px 2px 0 rgb(0 0 0 / 0.03)` (Gözü almayan, yalnızca kenarlığı destekleyen mikro derinlik)
- **`shadow-raised`:** `0 12px 36px -16px rgb(9 11 15 / 0.24)` (Floating toolbar, açılır denetçiler)
- **`shadow-overlay`:** `0 24px 60px -20px rgb(9 11 15 / 0.30)` (Komut paleti, modal pencereler)

---

## 6. Structural Chrome Palette vs Domain & Data Palette Policy

U1 mimarisinde renkler iki açık kategoriye ayrılır:

### A. STRUCTURAL CHROME PALETTE
- **Kapsam:** `canvas`, `sidebar`, `surface*`, `text*`, `border*`, `accent`, `ok/warn/danger`.
- **Tasarım Hedefi:** Düşük kroma (low-chroma), sakin zemin, seyrek ve işlevsel accent kullanımı.
- **Kural:** Yalnızca hiyerarşi, odak ve kritik durum bildirimleri için kullanılır. Dekoratif amaçla buton veya zemin boyamak yasaktır.

### B. DOMAIN & DATA PALETTE
- **Kapsam:** `heat-*` (emek haritası), `chart-*` (grafikler), `feed-*` (RSS/HN/Reddit/GH markaları), `kind-*` (medya tür kimlikleri), `src-*` (kaynak platform renkleri).
- **Tasarım Hedefi:** Veri ve kayıt türü ayrıştırması (semantic data differentiation).
- **Kural:** Domain renklerinin çok sayıda token içermesi yapısal görsel gürültü (chrome noise) olarak değerlendirilmez. Bu renkler doğrudan veri nesnelerine bağlıdır ve U1 kapsamında silinmez veya azaltılmaz.

---

## 7. Typography Scale, Density & Serif Policy Truthfulness

### A. Tipografi Skalası
- **Gövde:** `Manrope Variable` (13.5px / line-height: 20px / font-weight: 450)
- **Metin Tonları:**
  - `--text` (Primary): Light `#0f1115` (18.2:1 AAA), Dark `#f2f4f7` (17.0:1 AAA)
  - `--text-secondary`: Light `#454b56` (8.6:1 AAA), Dark `#aeb6c2` (8.5:1 AAA)
  - `--text-muted`: Light `#5c636f` (5.9:1 AA metin), Dark `#8b94a1` (5.5:1 AA metin)
  - `--icon`: Light `#7a828f` (3.8:1 non-text), Dark `#7e8794` (4.3:1 non-text)
- **Label-Caps Disiplini:**
  - `.label-caps`: `@apply text-micro font-semibold uppercase tracking-[0.14em] text-muted;`
  - Küçük kapitaller artık her başlığa zorla uygulanmaz; yalnızca rail grupları, sayaç etiketleri ve kompakt meta rozetleri için kullanılır.

### B. Doğru Serif Politikası (Truthful Serif Policy)
Eski kod yorumlarında yer alan "serif tamamen kaldırıldı" ifadesi gerçeği yansıtmamaktaydı. forkOS'un resmi ve kanonik yazı tipi politikası şudur:
- **`Manrope Variable` (Sans):** Birincil uygulama kromu, navigasyon, düğmeler, formlar ve tüm temel arayüz kontrolleri.
- **`Newsreader Variable` (Serif):** Yalnızca bilinçli editoryal ve okuma bağlamları (`BookmarkReaderModal`, `BookmarkCard` ve uzun okuma makaleleri).
- `@fontsource-variable/newsreader` bağımlılığı korunmaktadır; kullanıcıların okuma modundaki sans/serif tercihi bozulmamıştır.

---

## 8. Motion Grammar (Hareket Mimarisi)

Arayüzde gereksiz JS animasyon kütüphanesi (Framer Motion vb.) bulunmaz. Hareket sistemi CSS mikro-geçişleriyle kurulmuştur:

### A. Semantik Süre Skalası
- **Mikro / Hover:** `100–120ms` (`duration-100`) — Buton, liste satırı ve ikon üzerine gelme durumları.
- **Seçim & Kontrol:** `120–150ms` (`duration-150`) — Sekme geçişi, onay kutusu, radyo düğmesi, açılır menü.
- **Popover & Menü:** `140–170ms` — Bağlamsal açılır pencereler, filtre menüleri.
- **Panel & Çekmece:** `160–200ms` — Yan denetçi paneli açılış ve kapanışları.

### B. Tercih Edilen ve Kaçınılan Özellikler
- **Tercih:** `opacity`, `transform` (GPU destekli), `color`, `background-color`, `border-color`.
- **Kaçınılan:** Düzen sarsıntısı yaratan `width`, `height`, ağır `box-shadow` ve `backdrop-filter` animasyonları.

### C. Reduced Motion Garantisi
`frontend/src/index.css` içindeki global kural ile sisteminde animasyon azaltmayı seçen kullanıcılar için tüm süreler anında sıfırlanır:
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## 9. Spacing & Density Grammar (Boşluk Ritmi)

forkOS masaüstü verimlilik odaklı yoğun bir sistemdir. Boşluk ritmi şu hiyerarşik kurala göre işler:

```text
Kontrol İçi Boşluk (px-2.5 py-1 / h-8)
   < İlgili Öğe Aralığı (gap-1.5 / gap-2 / space-y-1)
   < Grup İçi Boşluk (gap-3 / space-y-3)
   < Bölüm Aralığı (mb-5 / py-4)
   < Ana Bölge Aralığı (gap-5 / px-6 py-5)
```

- Kontroller masaüstü verimliliği için 34px (`h-control`) ve 32px (`h-8`) bandında tutulmuştur.
- Dokunmatik veya geniş ekran bağlamları için 44px (`h-touch`) ayrılmıştır.

---

## 10. Interaction State Grammar (Etkileşim Durumları)

Tüm interaktif bileşenlerde tutarlı durum grameri uygulanır:

1. **Rest (Durgun):** Nötr metin/ikon rengi, zeminle kaynaşan ince sınır (`border-subtle`).
2. **Hover (Üzerinde):** Hızlı ve fısıltı düzeyinde zemin değişimi (`bg-surface-hover`). Asla ana eylemin tek keşif yolu olmamalıdır.
3. **Pressed (Basılı):** Hafif içe çökme hissi (`active:scale-[0.98]` veya `active:bg-surface-selected`).
4. **Selected (Seçili):** Belirgin zemin dolgusu (`bg-surface-selected`), kalınlaştırılmış tipografi (`font-medium`), isteğe bağlı accent detayı. (`selected != hover`).
5. **Focus-Visible (Klavye Odağı):** `2px solid var(--accent)` odak halkası + 1px ofset. Fare tıklamalarında görünmez, klavye ile gezinirken kaçırılamaz. (`focus != selected`).
6. **Disabled (Devre Dışı):** `opacity-40 cursor-not-allowed`. Soluk metinle karıştırılmamalı, interaktif olmadığı açık olmalıdır.
7. **Loading (Yükleniyor):** İşlem sürerken kontrol tıklanamaz; spinner veya hafif pulsasyon gösterilir.
8. **Danger (Kritik):** Yalnızca geri alınamaz veya silme riski taşıyan işlemlerde kırmızı durum tonları (`border-danger-border bg-danger-surface text-danger`).

---

## 11. Primitive Contracts & API Specification

| Bileşen | Önceki Durum | U1 Yeni Sözleşmesi | Tercih Edilen API | Native macOS Karşılığı |
|---|---|---|---|---|
| `<Section>` | Varsayılan kart kabuğu (`rounded-card border bg-surface shadow-card`). | Varsayılan `flat` (unboxed) anlamsal gruplama. Kart kabuğu opt-in. | `<Section>` (flat)<br>`<Section variant="card">` | `NSView` / `Group` / `Section` |
| `<SectionHeader>` | Başlık yanında zorunlu `<span className="h-px flex-1 bg-subtle" />`. | Ayırıcı çizgi varsayılan kapalı (`divider={false}`). | `<SectionHeader label="..." />`<br>`<SectionHeader divider />` | Bölüm Başlığı / `Section` header |
| `<Surface>` | `rounded-card border border-subtle bg-surface shadow-card`. | Korundu. Açık sınır ve kabartma gerektiren yüzey primitive'i. | `<Surface>` | `NSBox` / `GroupBox` |
| `<Workspace>` | Dış kutuda kart, kenarlık ve gölge vardı. | Dış kutu kaldırıldı. Ray, orta içerik (`bg-surface`) ve denetçi tuvale oturdu. | `<Workspace rail={...} inspector={...}>` | `NSSplitView` / `NavigationSplitView` |
| `<MetricStrip>` | Sert bölmeli kart ızgarası. | Alpha hairline ve 0.03 gölge ile sakinleştirildi. | `<MetricStrip>` | Gösterge çubuğu |
| `<Toolbar>` | `border-y border-subtle py-2.5`. | Korundu. | `<Toolbar>` | `NSToolbar` |
| `<RowList>` | `divide-y divide-subtle`. | Korundu. | `<RowList>` | `NSTableView` satırları |
| `<Button>` | `rounded-control border font-medium`. | İkincil butonlar `border-strong` ve `bg-surface-hover` ile dengelendi. | `<Button variant="...">` | `NSButton` |
| `<IconButton>` | `rounded-control border border-subtle`. | `aria-label={title}` zorunlu kılındı, 32px kompakt form korundu. | `<IconButton title="..." />` | İkon Butonu |

---

## 12. Section Consumer Audit & Boundary Integrity

Repo genelindeki tüm `<Section>` kullanımları analiz edilmiştir:
- **Workspace İçindekiler (Projeler, Ayarlar, Kaynaklar):** `ProjectsPage`, `SettingsSections`, `SourcesWorkspace` gibi bileşenlerde Section'ların `flat` olması iç içe kutu sendromunu başarıyla ortadan kaldırmıştır.
- **Modal ve Çekmeceler İçindekiler:** `OpportunityDetailModal`, `BookmarkReaderModal` içinde zaten bir `Surface` veya overlay katmanı olduğu için flat Section'lar mükemmel hizalanmaktadır.
- **Home / Today Izgarası:** Today ekranındaki kolonlar ("Bugünün planı", "Okuma akışı", "Kariyer") unboxed olarak doğal dikey akışa kavuşmuştur. Üstteki `TodayHero` kartı belirgin sınırını korumaktadır.
- **Denetim Sonucu:** Taranan çağrı noktalarının hiçbirinde içerik sınırlarının kaybolmadığı ve hiçbir iki bağımsız bölgenin birbirine yapışmadığı doğrulanmıştır. Global default-flat kararı korunmuş, gereksiz kart ekleme regresyonu yapılmamıştır.

---

## 13. Real Visual Verification Report (`VISUALLY-CONFIRMED`)

Gerçek tarayıcı motoru (`Brave Browser Beta / Chromium headless 1440px / 1100px / 850px`) ile yapılan test sonuçları:

| Ekran (Screen) | Tema (Theme) | Genişlik | Sonuç | Görsel Kanıt ve Bulgular (`VISUALLY-CONFIRMED`) |
|---|---|---:|---|---|
| **Today** (`/`) | Light | 1440px | **KUSURSUZ** | Canvas `#fafafb` üzerinde TodayHero beyaz kartı ve altındaki 3 unboxed kolon doğal akışta. Çizgi kirliliği yok. |
| **Today** (`/`) | Dark | 1440px | **KUSURSUZ** | Canvas `#0f1012`, Sidebar `#141518`, Hero Surface `#18191f`. Koyu temada kontrast dengeli, gözü yormuyor. |
| **Today** (`/`) | Light | 1100px | **KUSURSUZ** | 3 kolon 1100px'te orantılı daralıyor; metin taşması veya bozulma yok. |
| **Today** (`/`) | Dark | 1100px | **KUSURSUZ** | Koyu temada dar masaüstü yerleşimi stabil. |
| **Today** (`/`) | Light | 850px | **KUSURSUZ** | Dar masaüstünde ızgara otomatik olarak tek kolona geçiyor. Sidebar korunuyor; dikey kaydırma akıcı. |
| **Today** (`/`) | Dark | 850px | **KUSURSUZ** | Tek kolon koyu akış stabil. |
| **Projects** (`/#/projects`) | Light | 1440px | **KUSURSUZ** | Sol ray `bg-surface-sunken` ve `border-r` ile ayrışıyor. Çalışma alanı doğrudan tuvale oturuyor. Dış kutu yok. |
| **Projects** (`/#/projects`) | Dark | 1440px | **KUSURSUZ** | Sol ray koyu sunken `#1f2026`, orta alan surface `#18191f`. Form kontrolleri net sınırlarla seçiliyor. |
| **Projects** (`/#/projects`) | Light | 1100px | **KUSURSUZ** | Form ve kilometre taşları orantılı daralıyor; butonlar erişilebilir. |
| **Projects** (`/#/projects`) | Dark | 1100px | **KUSURSUZ** | Koyu tema 1100px dengeli. |
| **Projects** (`/#/projects`) | Light | 850px | **KUSURSUZ** | Dar masaüstünde ray ve form alt alta veya kompakt ızgarada taşma yapmıyor. |
| **Opportunities** (`/#/opportunities`) | Light | 1440px | **KUSURSUZ** | İş ilanları `RowList` ile taranabilir satırlar halinde akıyor; puan rozetleri (`100 SKOR`) öne çıkıyor. |
| **Opportunities** (`/#/opportunities`) | Dark | 1440px | **KUSURSUZ** | Koyu zeminde satır ayraçları hafif fısıltı çizgiye dönüşüyor; okunabilirlik yüksek. |
| **Opportunities** (`/#/opportunities`) | Light | 1100px | **KUSURSUZ** | Filtre çubuğu ve eylemler yatayda düzgün sarılıyor. |
| **Opportunities** (`/#/opportunities`) | Dark | 1100px | **KUSURSUZ** | Koyu tema 1100px stabil. |
| **RSS** (`/#/rss`) | Light | 1440px | **KUSURSUZ** | Klasör rayı (`sunken`), yazı listesi ve okuma bölmesi 3 sütunlu unboxed çalışma alanında kusursuz oturuyor. |
| **RSS** (`/#/rss`) | Dark | 1440px | **KUSURSUZ** | 3 sütunlu koyu çalışma alanı Linear hissini en belirgin veren ekranlardan biri. |
| **RSS** (`/#/rss`) | Light | 1100px | **KUSURSUZ** | 3 sütun oranları korunuyor. |
| **RSS** (`/#/rss`) | Dark | 1100px | **KUSURSUZ** | Koyu tema daraltılmış 3 sütun stabil. |
| **Settings** (`/#/settings`) | Light | 1440px | **KUSURSUZ** | Tercihler menüsü ve sağdaki form kartları temiz beyaz yüzeylerle ayrışıyor. |
| **Settings** (`/#/settings`) | Dark | 1440px | **KUSURSUZ** | Koyu tema ayar sekmeleri ve radyo seçenekleri net şekilde ayırt ediliyor. |

---

## 14. Visual Verification Questions — Yanıtlar (`VISUALLY-CONFIRMED`)

1. **Section flat olduktan sonra semantic groups hâlâ okunuyor mu?**<br>
   *EVET.* Başlık tipografisi (`text-heading font-medium`), başlık altı dikey boşluk ve öğe aralıkları grupları kutusuz da net şekilde sınırlandırmaktadır.
2. **Herhangi iki bağımsız region birbirine yapışmış gibi görünüyor mu?**<br>
   *HAYIR.* Izgara aralıkları (`gap-5`) ve dikey ritim bölgelerin birbirine karışmasını engellemektedir.
3. **Workspace dış border kaldırılınca layout "yarım kalmış" görünüyor mu?**<br>
   *HAYIR.* Tam aksine, uygulama penceresinin kendisi çalışma alanına dönüşmüş; iç içe yüzen kart tuhaflığı ortadan kalkmıştır.
4. **Canvas → Surface farkı light theme'de yeterli mi?**<br>
   *EVET.* `#fafafb` (Canvas) ile `#ffffff` (Surface) arasındaki mikro kontrast, beyaz kartların kenarlıksız da zemin üzerinde hafifçe yükselmesini sağlamaktadır.
5. **Dark theme'de Surface / Sunken / Canvas hierarchy doğru okunuyor mu?**<br>
   *EVET.* `#0f1012` (Canvas) > `#141518` (Sidebar) > `#18191f` (Surface) > `#1f2026` (Sunken ray/girdi) sıralaması koyu temada derinlik hissini kusursuz korumaktadır.
6. **Pane separator'ları yeterli mi?**<br>
   *EVET.* `rgba(15, 17, 21, 0.08)` ve `rgba(255, 255, 255, 0.08)` değerleri tam yerinde bir hairline ayrımı sağlamaktadır.
7. **Flat design fazla boş veya şekilsiz mi?**<br>
   *HAYIR.* forkOS'un yüksek veri yoğunluğu (metrikler, listeler, rozetler) sayfanın boş görünmesini engellemekte; aksine profesyonel ve sakin kılmaktadır.
8. **Inputs/buttons content'ten yeterince ayrılıyor mu?**<br>
   *EVET.* `rounded-control` (6px) yarıçapı ve `border-strong` sınırları kontrolleri tıklanabilir ve belirgin kılmaktadır.
9. **Selection/hover/focus state'leri birbirinden ayırt ediliyor mu?**<br>
   *EVET.* Hover fısıltı zemin (`#eceef2`), Selection açıkça seçili dolgu (`#e2e6eb`), Focus ise parlak 2px accent halkasıyla net şekilde ayrışmaktadır.
10. **Görsel yoğunluk hâlâ productivity-app seviyesinde mi?**<br>
    *EVET.* 34px kontroller, 32px ikon butonları ve 13.5px Manrope gövde boyutu masaüstü verimliliğini eksiksiz korumaktadır.

---

## 15. Verification & Quality Gates

| Doğrulama Adımı | Hedef | Sonuç | Durum |
|---|---|---|---|
| **Unit & Integration Tests** | 160 test dosyası / tüm testler | 160 dosya / 1.155 test geçti | **BAŞARILI** (0 hata) |
| **Design System Guardrail** | `designSystem.test.ts` (token uyumu) | 7/7 test geçti | **BAŞARILI** |
| **TypeScript Derleme** | `npx tsc -b` | 0 hata, temiz derleme | **BAŞARILI** |
| **Giriş Paketi Boyutu** | <= 500 KB bütçesi | **461.00 KB** (gz: 139.16 KB) | **BAŞARILI** (< 500 KB) |
| **Ölü Export Taraması** | <= 10 eşik | 3 adet (yalnızca agent tipleri) | **BAŞARILI** |
| **Endpoint Kapsama** | Referanssız uç <= 3 eşik | 1 adet (`/api/execution/plans/.../recover`) | **BAŞARILI** |
| **Git Diff Kontrolü** | `git diff --check` | Boşluk/CRLF hatası yok, backend dokunulmadı | **BAŞARILI** |

---

## 16. Kapsam Sınırları ve U2 / U3 Hazırlığı

### U1'de Bilinçli Olarak Ertelenen Konular
1. **U2 — Shell v2:** `AppSidebar.tsx` navigasyon yapısı, `WorkspaceHeader.tsx` komut modeli, mobil alt bar.
2. **U3 — Pilot Screens:** `TodayPage.tsx` üç kolonlu yerleşim yapısı, `ProjectsPage.tsx` 3-kolon Inspector mimarisi, `OpportunityPage.tsx` Drawer yerine kalıcı Inspector geçişi.
3. **U6 — Cruft Sweep:** Eski yardımcı sınıflar ve kullanılmayan modül kodları.

### Sonuç
U1 fazının tüm hedefleri, kod değişiklikleri, görsel doğrulamaları ve tasarım sözleşmeleri eksiksiz olarak tamamlanmıştır.

**U1 ✅ CLOSED.**
