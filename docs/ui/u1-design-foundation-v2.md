# forkOS — U1 Design Foundation v2 Raporu

**Faz:** U1 — Design Foundation v2  
**Tarih:** 2026-09-22  
**Referans:** Linear Design Language + Native Personal OS Principles  
**Kapsam:** Foundation Tokens, Shared UI Primitives, Layout Framing & Spatial Grammar  

---

## 1. Executive Summary

U0 fazında tamamlanan envanter ve native-readiness denetiminde tespit edilen temel sorun, forkOS'un zemin hiyerarşisi (`--canvas` ve `--surface` her ikisi de `#ffffff`) eksikliğinden ötürü içerik ve katman ayrımını 1.193 adet sert `border*` çizgisi ve her `<Section>` içine zorunlu kılınan kart kabuklarıyla sağlamaya çalışmasıydı.

U1 fazında forkOS'un görsel ve etkileşim grameri Linear ilkeleri doğrultusunda yeniden kurgulanmıştır:
- **"Structure felt, not drawn" (Hissedilen, çizilmeyen yapı):** Canvas (`#fafafb`) ile Surface (`#ffffff`) ve Sunken (`#f0f2f5`) arasında doğal bir derinlik hiyerarşisi kuruldu.
- **Sert Kenarlık Yerine Alpha Hairline:** Katı gri çizgiler (`#e4e4e7` / `#2a2e35`) yerine hem açık hem koyu temada zeminle pürüzsüz karışan alpha hairline'lar (`rgba(15, 17, 21, 0.08)` ve `rgba(255, 255, 255, 0.08)`) devreye alındı.
- **Unboxed Section Varsayılanı:** `<Section>` varsayılan olarak `flat` (çerçevesiz, gölgesiz anlamsal gruplama) yapıldı. Kutu kabuğu yalnızca açıkça istendiğinde (`variant="card"` veya `flat={false}`) uygulanır.
- **SectionHeader İnce Çizgi Sadeliği:** Başlık yanındaki zorunlu `h-px bg-subtle` çizgisi kaldırıldı; `divider` prop'u opsiyonel hale getirildi (`default = false`).
- **Workspace Çerçevesizliği:** `<Workspace>` dışındaki gereksiz `rounded-card border border-subtle bg-surface shadow-card` kutusu kaldırıldı; ray (`aside` border-r), içerik (`section` bg-surface) ve denetçi (`aside` border-l) ekran tuvaline doğrudan oturacak şekilde sadeleştirildi.
- **Erişilebilirlik ve Kontrast Güvencesi:** WCAG 2.1 AA/AAA kontrast oranları korundu; `prefers-reduced-motion` desteği CSS çekirdeğine eklendi; `IconButton` erişilebilirliği ve 500 KB bundle bütçesi korundu.

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

## 6. Typography Scale & Density

- **Gövde:** `Manrope Variable` (13.5px / line-height: 20px / font-weight: 450)
- **Metin Tonları:**
  - `--text` (Primary): Light `#0f1115` (18.2:1 AAA), Dark `#f2f4f7` (17.0:1 AAA)
  - `--text-secondary`: Light `#454b56` (8.6:1 AAA), Dark `#aeb6c2` (8.5:1 AAA)
  - `--text-muted`: Light `#5c636f` (5.9:1 AA metin), Dark `#8b94a1` (5.5:1 AA metin)
  - `--icon`: Light `#7a828f` (3.8:1 non-text), Dark `#7e8794` (4.3:1 non-text)
- **Label-Caps Disiplini:**
  - `.label-caps`: `@apply text-micro font-semibold uppercase tracking-[0.14em] text-muted;`
  - Küçük kapitaller artık her başlığa zorla uygulanmaz; yalnızca rail grupları, sayaç etiketleri ve kompakt meta rozetleri için kullanılır.

---

## 7. Primitive Contracts & Migration Table

| Bileşen | Önceki Durum | U1 Yeni Sözleşmesi | Gerekçe & Etki |
|---|---|---|---|
| `<Section>` | Varsayılan `card` shell (`rounded-card border border-subtle bg-surface shadow-card`). Başlık altında sabit `border-b`. | Varsayılan `flat` (unboxed). Kutu kabuğu için `variant="card"` veya `flat={false}` gereklidir. `titleVariant="heading"` doğal başlık. | Sayfalardaki kutu gürültüsü ortadan kalktı. Akış dikey boşluklarla sakinleşti. |
| `<SectionHeader>` | Başlık yanında zorunlu `<span className="h-px flex-1 bg-subtle" />` çizgisi. | Çizgi varsayılan kapalı (`divider={false}`). Yalnızca `divider={true}` istendiğinde çizilir. | Tüm sayfalarda yatay çizgi kirliliği temizlendi. |
| `<Surface>` | `rounded-card border border-subtle bg-surface shadow-card` | Değişmeden korundu. | Belirgin görsel sınır gerektiren form ve paneller için açık sınır primitive'i. |
| `<Workspace>` | Dış sarmalayıcıda `rounded-card border border-subtle bg-surface shadow-card`. | Dış kutu ve gölge kaldırıldı (`grid min-h-workspace-body overflow-hidden`). İçerik bölümü `bg-surface`. | Çalışma alanları tarayıcı tuvaline pürüzsüz entegre oldu; iç içe kutu hissi bitti. |
| `<MetricStrip>` | `divide-x divide-subtle rounded-card border border-subtle bg-surface shadow-card` | Yumuşatılmış alpha hairline ve 0.03 shadow ile sakinleşti. | Sayısal göstergeler içerikle yarışmıyor. |
| `<Toolbar>` | `border-y border-subtle py-2.5` | Korundu (alpha hairline ile daha temiz). | Filtre ve eylem seridi. |
| `<RowList>` | `divide-y divide-subtle` | Korundu. | Liste satırları için yalın yapı. |
| `<Button>` | `rounded-control border font-medium` | `border-strong` ve `bg-surface-hover` ile daha sakin etkileşim. | Buton hiyerarşisi netleşti. |
| `<IconButton>` | `rounded-control border border-subtle bg-surface` | `aria-label={title}` zorunlu kılındı, alpha hairline ile inceltildi. | 32px kompakt Mac-native hissi. |

---

## 8. Reduced Motion & Accessibility Standard

`frontend/src/index.css` içine standart prefers-reduced-motion kuralı entegre edildi:
```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```
- Sistem ayarlarında hareketi azaltmayı seçen kullanıcılar için tüm animasyonlar anında tamamlanır.
- Odak göstergeleri (`:focus-visible`) 2px accent rengiyle erişilebilir kılınmıştır.

---

## 9. Verification & Quality Gates

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

## 10. Sonraki Fazlara Hazırlık ve Kapsam Sınırları

### U1'de Bilinçli Olarak Yapılmayanlar (Deferred Scope)
1. **U2 — Shell v2:** `AppSidebar.tsx`, `WorkspaceHeader.tsx`, mobil alt çubuk ve pencere kontrolleri U1 kapsamına alınmamıştır.
2. **U3 — Pilot Screens:** `TodayPage.tsx`, `ProjectsPage.tsx`, `OpportunityPage.tsx` özel yerleşimleri U1'de yeniden tasarlanmamıştır. Primitiveler güncellendiği için bu sayfalar otomatik olarak daha sakin bir görünüme kavuşmuştur; ancak sayfa içi mimari geçişleri U3'te yapılacaktır.
3. **U6 — Cruft Sweep:** Eski yardımcı sınıflar ve kullanılmayan modül kodları U6 fazında temizlenecektir.

### U2 Fazına Geçiş Durumu
Tasarım temeli (renkler, zemin hiyerarşisi, hairline kenarlıklar, yumuşak gölgeler, unboxed section ve sadeleştirilmiş workspace) başarıyla kuruldu ve doğrulandı. forkOS artık **U2 — Shell v2** fazına başlamak için tam hazır durumdadır.
