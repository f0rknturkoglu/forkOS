# Bugün Dashboardı, Ritim Grafiği, Sidebar/Header ve Obsidianvari Notlar Tasarım Spesifikasyonu

Tarih: 2026-09-11  
Durum: Taslak (Kullanıcı İncelemesinde)

---

## 1. Amaç ve Kapsam

Kullanıcı deneyimini sadeleştirmek, görsel estetiği modernleştirmek ve modüller arası kopuklukları gidermek amacıyla 4 temel alanda kapsamlı iyileştirme yapılacaktır:

1. **Bugün Dashboardı:** "Bugünün Planı"ndaki işlevsiz "ekle" formu kaldırılacak; "Gün Özeti" widget'ı ile "Bugünün Planı" tek bir güçlü ve sade panelde birleştirilecek. Kart üzerinde tek satırlık hızlı görev ekleme input'u ile eklenen görevler anında listeye düşecek; kart üzerinden tek tıkla tamamlanıp veya silinebilecek.
2. **Ritim Grafiği:** `RhythmWidget` ve `ActivityPage` üzerindeki kaba, tek renkli ve anlamsız sütun grafiği baştan tasarlanacak. Odak (Pomodoro), Görev, Okuma/Not ve Başvuru kırılımlarını gösteren modern, yuvarlatılmış barlı, hover detaylı ve anlamlı bir aktivite grafiğine dönüştürülecek.
3. **Sidebar ve Header Uyumu:** Sidebar'daki eksik SVG'ler (alt rotalar vb.) tamamlanacak, açılıp kapanırken oluşan görsel sıçramalar (layout pop) CSS transition'lar ile pürüzsüzleştirilecek ve Header ile Sidebar hizalaması kusursuz hale getirilecek.
4. **Obsidianvari Notlar Dosya Gezgini:** Notlar ağacının ana menüdeki hantal ve dağınık yapısı kaldırılacak; `NotesPage` üzerinde Obsidian benzeri sol dosya gezgini (Vault Explorer) inşa edilecek. Klasör hiyerarşisi, satır içi klasör oluşturma (inline creation), okuma vurguları akıllı bölümü ve pürüzsüz not geçişleri sağlanacak.

---

## 2. Detaylı Tasarım ve Bileşen Mimarisi

### Bölüm 1: Bugün Dashboardı — Birleşik "Bugünün Planı"

- **Mevcut Durum:** Sol sütunda `today.rhythm` ("Gün özeti") ve `today.agenda` ("Bugünün planı") iki ayrı widget olarak duruyor. Plan widget'ındaki "ekle" butonu çok adımlı, karmaşık ve hantal bir form açıyor.
- **Yeni Tasarım (`TodayPlanWidget`):**
  - **Başlık & Faz Rozeti:** "Bugünün Planı" başlığı yanında günün fazı ("Sabah · 3 planlı · 1 geciken" veya "Akşam · Gün sonu değerlendirmesi").
  - **Üst Eylem / Uyarı Şeridi:**
    - Varsa takvim çakışması uyarısı.
    - Akşam fazında: "Değerlendirmeye Git" veya "Yarına Taşı" tek tık butonları.
  - **Hızlı Görev Ekleme (Inline Quick Composer):**
    - Doğrudan kartın üst/alt kısmında `Input` ("Bugüne görev ekle... (Enter ile kaydet)").
    - Enter'a basıldığında `api.post("/todos", { title, plan_day: todayKey(), priority: 2 })` çağrılır.
    - Görev anında "Yapılacaklar" grubunda belirir.
  - **Görev Grupları ve Hızlı Aksiyonlar:**
    - *Saatli*, *Rutinler*, *Planlı Yapılacaklar*, *Açık Görevler*, *Tamamlananlar*.
    - Her görev satırında:
      - Sol tarafta tek tıkla tamamlama dairesi/checkbox (`Circle` -> `Check`).
      - Sağ tarafta tek tıkla silme/çöpe atma butonu (`Trash2`).
  - **Registry Sadeleştirmesi:** `today.rhythm` ve `today.agenda` tekil `today.plan` olarak birleştirilir.

### Bölüm 2: Modern Ritim ve Aktivite Grafiği (`RhythmChart`)

- **Mevcut Durum:** `RhythmWidget` ve `ActivityPage` içindeki `MonthlyBars`, sabit yükseklikte sadece `bg-accent` renkli ince dikdörtgenlerden oluşuyor; hareketin ne olduğu anlaşılmıyor ve estetikten uzak.
- **Yeni Tasarım:**
  - **Çok Katmanlı (Stacked/Proportional) Bar Görünümü:**
    - Her ay için toplam hareket sayısı sütun yüksekliğini belirler.
    - Sütun içinde kategorilere göre zarif renk dilimleri:
      - Odak (Pomodoro): Amber/Accent
      - Görev & Rutin: Ok/Yeşil tonu
      - Okuma & Not: Info/Mavi tonu
      - Başvuru: Mor/İndigo tonu
    - Yumuşatılmış kenarlar (`rounded-t-sm`), modern boşluklar ve hafif arka plan kılavuz çizgileri.
  - **İnteraktif Popover / Tooltip:**
    - Ayın üzerine gelindiğinde zengin detay kutusu açılır:
      - Toplam hareket sayısı.
      - Detay dökümü: X Pomodoro, Y Görev, Z Okuma, W Başvuru.
  - **Ritim Özet Başlığı:**
    - Seri rozeti (Streak): Kesintisiz gün sayısı alev ikonuyla vurgulanır.
    - Aylık ortalama ve trend göstergesi.
  - Hem `RhythmWidget` (Bugün paneli için kompakt görünüm) hem de `ActivityPage` (geniş detaylı görünüm) aynı gelişmiş motoru kullanır.

### Bölüm 3: Sidebar ve Header Uyumu, SVG İkonlar & Pürüzsüz Geçiş

- **SVG Eksikleri:**
  - Alt rotalar (`/sources`, `/habits`, `/planner`, `/graph`) için `child` görünümünde ikon gizleme kaldırılacak; her birine uygun Lucide ikonu (`Radio`, `Repeat`, `CalendarRange`, `Share2`) atanacak.
  - Ana menüdeki tüm modüller (`today`, `todo`, `bookmarks`, `notes`, `media`, vb.) doğrulanmış, standart 16px Lucide SVG ikonlarıyla tutarlı hale getirilecek.
- **Pürüzsüz Açılma/Kapanma (Smooth Transitions):**
  - Anında kaybolan `md:hidden` yerine `overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out` kullanılacak.
  - Kenar çubuğu genişliği `w-sidebar` ile `w-rail` arasında pürüzsüz akacak.
  - Açma/kapama butonuna zarif rotasyon eklenecek.
- **Header ve Sidebar Hizalama:**
  - Header yüksekliği (`h-workspace-header`: 48px) ile Sidebar başlık yüksekliği (48px) birebir eşleştirilecek.
  - Sol logo ve başlık elemanları ile sağdaki WorkspaceHeader yatay ekseni tam piksel hizasında buluşacak.

### Bölüm 4: Obsidianvari Notlar Dosya Gezgini (`NotesExplorer`)

- **Konum:** `NotesPage` içine entegre, sol tarafta yer alan tam fonksiyonel bir **Vault Explorer** paneli.
- **Bileşen Yapısı:**
  - **Explorer Header:**
    - "Notlar & Kasa" başlığı ve not sayısı.
    - Üst aksiyon butonları:
      - `FilePlus`: Kök dizine yeni not aç.
      - `FolderPlus`: Kök dizine yeni klasör aç.
      - `FolderTree` / `ChevronsDownUp`: Tüm klasörleri daralt/genişlet.
      - `PanelLeftClose` / `PanelLeftOpen`: Not düzenlerken gezgini daralt/genişlet.
  - **Akıllı Bölüm — Okuma Vurguları:**
    - En üstte zarif bir `Highlighter` rozetli sanal bölüm ("Vurgular & Alıntılar", sayaçlı).
    - Tıklandığında makale vurguları görünümünü açar.
  - **Hiyerarşik Klasör Ağacı:**
    - İç içe açılabilen klasörler (`ChevronRight` döner ikon, `Folder` / `FolderOpen`).
    - Klasör üzerinde gezinirken (hover) beliren mikro aksiyonlar:
      - `+` Bu klasöre not ekle
      - `FolderPlus` Alt klasör ekle
      - `Pencil` Yeniden adlandır
      - `Trash2` Sil
  - **Satır İçi Oluşturma (Inline Creation):**
    - Klasör veya not ekleme butonuna basıldığında ağaç içinde tam o noktada otomatik odaklı bir input açılır.
    - `Enter`: Oluşturur ve açar.
    - `Escape`: İptal eder. Ayrı form butonları ile karmaşa yaratılmaz.
  - **Not Satırları:**
    - Belge ikonu (`FileText`), not başlığı, sabitleme rozeti (`Pin`), son güncelleme tarihi.
    - Sürükle-bırak ile klasörler arası taşıma.
  - **Ana Sidebar Temizliği:** Notlar sekmesi altındaki hantal liste ana menüden temizlenir; ana menüde yalnızca "Notlar" ve "Bilgi Grafı" kalır. Asıl dosya ağacı Notlar çalışma alanında rahatça kullanılır.

---

## 3. Doğrulama ve Test Planı

1. **Bugün Dashboardı:**
   - Yeni görev ekleme input'unun çalıştığı, görevin veritabanında oluştuğu ve plan listesine anında yansıdığı test edilecek.
   - Görevin tamamlanma ve silinme işlemlerinin çalıştığı doğrulanacak.
   - Eski `DailyRhythmWidget` testleri güncellenecek, birleşik `TodayAgendaWidget.test.tsx` yazılacak.
2. **Ritim Grafiği:**
   - `MonthlyBars` / `RhythmChart` yeni bileşeninin verilerle ve boş durumlarla doğru render edildiği test edilecek (`RhythmWidget.test.tsx`, `ActivityPage.test.tsx`).
3. **Sidebar & Header:**
   - `AppSidebar.test.tsx`: Tüm alt rotaların SVG ikonlarının render edildiği, daraltma/genişletme sınıflarının doğru çalıştığı test edilecek.
4. **Notlar Dosya Gezgini:**
   - `NotesPage.test.tsx` ve `NoteSidebarTree.test.tsx`: Klasör oluşturma, iç içe klasörler, not seçimi ve vurgular görünümüne geçiş test edilecek.
5. **Tasarim Sistemi & Kural Kontrolleri:**
   - `designSystem.test.ts` ve `invalidation.test.ts` çalıştırılacak.
   - `check-endpoint-coverage.mjs` ve `check-dead-exports.mjs` doğrulanacak.
   - SIFIR EMOJİ kuralı denetlenecek.
