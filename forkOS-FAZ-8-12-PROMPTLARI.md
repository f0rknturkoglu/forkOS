# forkOS — Faz 8–12 Agent Promptları

> **Ön koşul:** Faz 0–7 tamamlandı (commit `3ca66c9`'a kadar). Bu fazlar onun üstüne biner.
> Her prompt bağımsız çalıştırılabilir ama **sırayla verilmeli** — Faz 12, Faz 11'e bağlı.
> Her fazın sonunda testleri koştur ve commit al.

## Sıra ve gerekçesi

| Faz | Ad | Neden bu sırada | Büyüklük |
|---|---|---|---|
| **8** | Isı haritası regresyonu + token guardrail'i | Görünür bug, tek dosyalık düzeltme, hiçbir şeyi bekletmiyor | XS |
| **9** | Plan / son tarih ayrımı | Günlük kullanımı bozan eksik; bağımsız | M |
| **10** | Değerlendirme modülünü nav'dan çıkar | Küçük, bağımsız, sidebar'da yer açar | S |
| **11** | Kitap tekilleştirme: `learning.book` → `media_item` | Veri migration'ı; Faz 12'nin kuracağı sayfanın altını temizler | M |
| **12** | Çalışma + Öğrenme birleşmesi | Faz 11'i bekler — düşecek tabloyu ekrana koymamak için | L |

```
Faz 8 ──┐
Faz 9 ──┼── (bağımsız, paralel verilebilir)
Faz 10 ─┘
Faz 11 ── Faz 12
```

---

## PROMPT — FAZ 8: Isı haritası kareleri görünmüyor + token regresyon guardrail'i

```
forkOS deposunda (/Users/furkanturkoglu/Downloads/forkOS) çalışıyorsun.
AGENTS.md ve CLAUDE.md'yi oku; kural 15 (renk/boyut/yarıçap yalnız tasarım
tokenlarından gelir) bu görevin tam merkezinde.

GÖREV: Bugün ekranındaki ve Etkinlik sayfasındaki "Emek haritası"nın kareleri
görünmüyor. Kök neden TESPİT EDİLDİ, aşağıda. Düzelt ve aynı sınıf hatanın
tekrar etmesini engelleyen bir guardrail ekle.

KÖK NEDEN (doğrulanmış):
  frontend/src/modules/activity/Heatmap.tsx:27
    const STEP_BG = ["bg-heat-0", "bg-heat-1", "bg-heat-2", "bg-heat-3", "bg-heat-4"]
  frontend/src/index.css:57-61 (açık tema) ve :145-149 (koyu tema)
    --heat-0 ... --heat-4  → HÂLÂ TANIMLI
  frontend/tailwind.config.js
    colors nesnesinde `heat` grubu YOK → Faz 2 commit'i 6a92d15 sırasında
    silinmiş (muhtemelen yeni `chart` grubu eklenirken gereksiz sanılmış).

  Sonuç: bg-heat-0..4 utility sınıfları hiç üretilmiyor, kareler saydam
  10x10px bağlantılar olarak render ediliyor.

  Kanıt:
    grep -o "bg-heat-[0-9]" frontend/dist/assets/*.css   → BOŞ
    grep -o "\-\-heat-0:[^;]*" frontend/dist/assets/*.css → --heat-0:#e4e7ec (var)

  Etkilenen iki yer (ikisi de STEP_BG kullanıyor):
    - yıl ızgarası (Heatmap.tsx:113)
    - alttaki "az ▢▢▢▢▢ çok" göstergesi (Heatmap.tsx:129)

1. DÜZELTME:
   tailwind.config.js colors nesnesine `heat` grubunu geri koy — `feed`, `kind`
   ve `chart` gruplarıyla AYNI biçimde, index.css'teki değişkenlere bağlayarak:
     heat: { 0: "var(--heat-0)", 1: "var(--heat-1)", 2: "var(--heat-2)",
             3: "var(--heat-3)", 4: "var(--heat-4)" }
   Yorumla neyi temsil ettiğini yaz (emek haritası basamakları, semantik değil).
   ALTERNATİF olarak core/ui.tsx'teki identityClasses() desenine
   (text-[color:var(--heat-N)]) geçirilebilir; ama `heat` bir ARKA PLAN
   basamağı, kimlik rengi değil — tailwind grubu doğru araç. Grubu geri koy.

2. `chart` GRUBUNU DA DENETLE:
   bg-chart-* de üretilen CSS'te yok. FinancePage.tsx `var(--chart-N)` değerini
   doğrudan inline/SVG fill olarak kullanıyor, tailwind grubunu kullanmıyor.
   Karar ver ve UYGULA: ya `chart` grubunu FinancePage'de gerçekten kullan,
   ya tailwind.config.js'ten kaldır. Kullanılmayan grup bırakma.

3. GUARDRAIL (asıl iş — bug'ın kendisi 5 satır):
   frontend/src/core/designSystem.test.ts şu an DESEN YASAKLIYOR ama
   "kullanılan token sınıfı gerçekten çözülüyor mu" diye BAKMIYOR. O yüzden
   Faz 2 bu regresyonu sessizce geçirdi.

   Yeni test ekle: src/ altındaki tüm .ts/.tsx dosyalarını tara, şu biçimdeki
   sınıfları topla:
     (bg|text|border|ring|fill|stroke)-<grup>-<ton>
   tailwind.config.js'ten colors nesnesini import et (ya da oku) ve her
   <grup>-<ton> çiftinin gerçekten tanımlı olduğunu doğrula. Tanımsız olan
   varsa testi kırdır ve hangi dosyada olduğunu yazdır.

   Ters yönü de kontrol et: tailwind.config.js'te tanımlı olup src/ içinde hiç
   kullanılmayan renk grubu varsa uyar (eşikli; `chart` kararına göre).

   Not: bu tarama string birleştirmeyle kurulan sınıfları (`bg-heat-${n}`)
   yakalayamaz. Heatmap.tsx zaten literal dizi kullanıyor (doğru desen).
   Testin başına bu sınırı yorum olarak yaz.

4. DOĞRULAMA — bu bug build çıktısında görünür, sadece test yeterli değil:
   cd frontend && npm run build
   grep -o "bg-heat-[0-9]" dist/assets/*.css | sort -u    → 5 satır gelmeli
   Sonra dev sunucusunu aç, Bugün ekranında ve #/activity sayfasında haritayı
   AÇIK ve KOYU temada ekran görüntüsüyle doğrula; kareler ve alttaki
   "az…çok" göstergesi görünür olmalı. Ekran görüntülerini output/ altına koy.

TAM DOĞRULAMA:
  cd frontend && npx vitest run && npm run build && npm run format:check
  node scripts/check-endpoint-coverage.mjs && node scripts/check-dead-exports.mjs

ÇIKTI: kök neden özeti, düzeltme, yeni guardrail testinin ne yakaladığı,
`chart` grubu kararı, açık+koyu ekran görüntüleri.
```

---

## PROMPT — FAZ 9: Plan / son tarih ayrımı ("Bugüne ekle" tarihlendirmiyor)

```
forkOS deposunda çalışıyorsun. AGENTS.md, CLAUDE.md (özellikle kural 13, 14, 16)
ve docs/mimari.md'yi oku.

GÖREV: Bugün ekranının sol sütunundaki akışta bir görevi "Bugüne ekle" yapınca
görev Görevler sayfasında (#/todos) hiçbir şekilde işaretlenmiyor ve
tarihlendirilmiyor. Kullanıcı planladığını başka hiçbir ekranda göremiyor.

MEVCUT DAVRANIŞ (doğrulanmış, bug değil — EKSİK ENTEGRASYON):
  frontend/src/modules/today/TodayAgendaWidget.tsx:143
    "Bugüne ekle" → POST /plan { entity_id, day, start_min?, duration_min? }
  backend/app/modules/todo/service.py:357  schedule()
    PlanSlot satırı yazar, log_event("plan.scheduled") atar.
    todo.due_at'a HİÇ DOKUNMAZ.
  backend/app/modules/todo/schemas.py:43  TodoOut
    plan ile ilgili tek bir alan yok.
  frontend/src/modules/todo/TodoRow.tsx
    plandan tamamen habersiz (proje ve milestone rozeti var, plan yok).

  Sonuç:
    Bugün paneli        → görev "Yapılacaklar"da görünür     ✓
    Haftalık planner    → görünür                             ✓
    /todos Görevler     → hiçbir değişiklik                   ✗
    /api/deadlines      → girmez (deadline_provider due_at'e bakar) ✗

ÇÖZÜM YÖNÜ — ÖNEMLİ, BUNU DEĞİŞTİRME:
  due_at'i SET ETME. Plan ile son tarih farklı kavramlar:
  "bugün yapmayı planlıyorum" ≠ "bugün teslim". due_at yazarsan yarın o görev
  gecikmiş görünür, öncelik sıralaması ve deadline widget'ı bozulur.
  Doğru çözüm: planı GÖRÜNÜR yap, ayrıca son tarih vermek için AYRI bir aksiyon.

1. BACKEND — TodoOut'a plan bilgisi ekle:
   - TodoOut'a: planned_day: date | None, planned_start_min: int | None
   - todo listeleme sorgusuna plan_slot join'i (LEFT JOIN, entity_id üzerinden).
     DİKKAT: bir görevin birden fazla günü olabilir; hangi kaydın döneceğini
     netleştir — öneri: BUGÜN veya en yakın gelecekteki slot; geçmiş slotlar
     dönmesin. Kararını kod yorumunda gerekçelendir.
   - N+1 sorgu üretme; tek sorguda topla.
   - plan_slot AGENTS.md kural 1'in dokümante edilmiş istisnası; yeni tablo açma.

2. FRONTEND — planı görünür yap:
   - TodoRow.tsx'e plan çipi: "bugün planlı" / "bugün 14:30" / "yarın planlı".
     Mevcut proje ve milestone rozetlerinin yanına, aynı Chip bileşeniyle.
     Ton semantik olmalı (tokenlardan); kimlik rengi kullanma.
   - Geçmiş güne planlanıp yapılmamış görev için ayrı ton (uyarı) düşün.
   - TodoPage'e "bugün planlı" filtresi — mevcut ?project= filtresiyle
     aynı desende URL parametresi olarak (?planned=today).

3. FRONTEND — eksik olan ters aksiyonu ekle:
   - TodoRow'a "bugüne tarihle" aksiyonu (due_at = bugün). Bu, "Bugüne ekle"den
     AYRI ve farklı bir şey; arayüzde ikisinin farkı anlaşılmalı.
     Etiketleri net seç: "plana al" (plan_slot) vs "son tarih ver" (due_at).
   - TodayAgendaWidget'taki "Bugüne ekle" düğmesinin başlığını/tooltip'ini
     de buna göre netleştir — kullanıcı ne olduğunu tahmin etmesin.

4. INVALIDATION (kural 14):
   plan yazma zaten "plan.write" olayını tetikliyor. "plan.write" listesine
   "todos" ekle — plan değişince Görevler sayfası da tazelensin.
   frontend/src/core/invalidation.test.ts'i buna göre genişlet.

5. TESTLER:
   - backend: planlanan görevin TodoOut'ta planned_day ile döndüğü;
     geçmiş slotun dönmediği; due_at'in DEĞİŞMEDİĞİ (regresyon koruması).
   - frontend: TodoRow plan çipini gösteriyor; ?planned=today filtresi çalışıyor;
     "bugüne tarihle" due_at yazıyor, "plana al" yazmıyor.

DOĞRULAMA:
  cd backend && python scripts/export_openapi.py
  cd frontend && npm run api:generate && npm run api:check
  cd frontend && npx vitest run && npm run build && npm run format:check
  make test CO="docker compose"
  cd backend && ruff check app tests scripts
ELLE AKIŞ: Bugün'de bir görevi "Bugüne ekle" → #/todos'ta plan çipi görünüyor,
due_at boş kalıyor. Ayrı "son tarih ver" aksiyonu due_at yazıyor.

ÇIKTI: eklenen alanlar, plan/son-tarih ayrımının arayüzde nasıl anlatıldığı,
testler, elle akış sonucu.
```

---

## PROMPT — FAZ 10: Değerlendirme modülünü navigasyondan çıkar

```
forkOS deposunda çalışıyorsun. AGENTS.md, CLAUDE.md ve docs/mimari.md'yi oku.

GÖREV: Değerlendirme (review) haftada bir kullanılıyor ama sidebar'da kalıcı
bir modül girişi tutuyor. Girişini Bugün paneline ve Etkinlik'e taşı.

ÖNEMLİ — MODÜLÜ DAĞITMA, SADECE GİRİŞ NOKTASINI TAŞI:
  review sadece bir özet değil, veri YAZAN bir akış:
    backend/app/modules/review/service.py:223  _apply_decisions()
    "drop" dediğin görevler status="dropped" oluyor, "carry" sonraki döneme
    taşınıyor. review tablosundaki note + decisions türetilemez veri.
  Ayrıca preview() her modülün event'ini birleştiriyor (pomodoro dakikaları,
  todo tamamlamaları, rutinler, çalışma konuları). Tek tek modüllere
  yedirilemez — hiçbiri "hafta" kavramını bilmiyor. Mantık çekirdekte kalır.

1. NAVİGASYONDAN ÇIKAR:
   - frontend/src/modules/review/index.ts'te group: "track" alanını kaldır
     (ya da modülü nav'da göstermeyecek biçimde işaretle — registry'nin
     bunu nasıl destekleyeceğine karar ver; gerekiyorsa ModuleSpec'e
     `hidden?: boolean` gibi TEK bir alan ekle ve core/registry.ts'te
     navigationModules() bunu filtrelesin).
     DİKKAT: Faz 1'de ModuleSpec'ten ölü alanlar temizlendi; yeni alan
     ekliyorsan gerçekten okunduğundan emin ol, yoksa aynı borcu geri getirirsin.
   - Rotalar (/review/daily, /review/weekly) ÇALIŞMAYA DEVAM ETMELİ.
   - Command Palette komutları KALSIN — Ctrl+K'dan erişilebilir olmalı.

2. GİRİŞ NOKTALARINI GÜÇLENDİR:
   - Bugün panelindeki ReviewWidget zaten iyi yazılmış (akşam 18:00'den önce
     hatırlatmıyor, yapıldıysa tek satıra iniyor). ASIL giriş noktası bu olacak.
     Haftalık değerlendirme için de aynı mantığı ekle: haftanın son günü /
     ilk günü "haftalık değerlendirme hazır" durumu.
   - Etkinlik sayfasına (#/activity) geçmiş değerlendirmelere giden bir bağlantı
     veya bölüm ekle — kaydedilmiş review'lar şu an hiçbir yerde listelenmiyor
     (GET /reviews ucu var).

3. ÖLÜ DAL TEMİZLİĞİ:
   backend/app/modules/review/service.py:49 civarı preview() hâlâ
   `Event.verb == "habit.checked"` sorguluyor. habit modülü Faz 1'de kaldırıldı;
   rutin sayımı artık todo.recur üzerinden geliyor.
   Geçmiş event'ler `event` tablosunda duruyor (append-only, kural 3) — o yüzden
   sorguyu kaldırmak eski haftaların rakamını değiştirir. KARAR VER:
   ya dalı koru ve "tarihsel veri için" diye yorumla, ya kaldır ve neden
   kaldırdığını yaz. Sessizce bırakma.

4. TESTLER:
   - review modülü sidebar'da görünmüyor ama rotaları çözülüyor
     (mevcut registryRouting.test.tsx desenini genişlet).
   - Command Palette'te review komutları hâlâ bulunuyor.
   - Etkinlik sayfası geçmiş review'ları listeliyor.

DOĞRULAMA:
  cd frontend && npx vitest run && npm run build && npm run format:check
  node scripts/check-endpoint-coverage.mjs   → GET /reviews artık kullanılmalı
  make test CO="docker compose"
  cd backend && ruff check app tests scripts

ÇIKTI: nav'dan nasıl çıkarıldığı, yeni giriş noktaları, habit dalı kararı.
```

---

## PROMPT — FAZ 11: Kitap tekilleştirme — `learning.book` → `media_item`

```
forkOS deposunda çalışıyorsun. AGENTS.md (özellikle kural 1, 2, 3, 9, 10),
CLAUDE.md ve docs/mimari.md'yi oku. Bu faz VERİ MİGRATION'I içerir; dikkatli ol.

GÖREV: Kitaplar iki ayrı tabloda tutuluyor. Tek tabloda topla.

MEVCUT DURUM (doğrulanmış):
  backend/app/modules/learning/models.py:34
    class Book(EntityBacked)  ENTITY_TYPE = "book"
    alanlar: author, status, total_pages, current_page, started_at,
             finished_at, rating, notes
  backend/app/modules/media/models.py:36-37
    media_item  kind = "book" | "audiobook"
    alanlar: progress, total, progress_measure, status, cycle'lar, provider,
             cover_path/cover_url, koleksiyon üyeliği, meta

  Aynı kitabı iki yere girebiliyorsun; ikisi birbirini görmüyor.
  Medya tarafı belirgin biçimde zengin: OpenLibrary + Google Books sağlayıcıları,
  kapak, tekrar okuma döngüsü (media_cycle), koleksiyonlar, Bugün widget'ı,
  ilerleme düzeltme geçmişi. learning.book bunların hiçbirine sahip değil.

KARAR: media_item kazanır. learning.book emekli olur.

1. ALAN EŞLEMESİ — önce yaz, sonra kodla:
   book.author        → media_item'da nereye? (meta mı, ayrı kolon mu?)
                        media_item'ın mevcut şemasını oku, uydurma.
   book.total_pages   → media_item.total (+ progress_measure = "page")
   book.current_page  → media_item.progress
   book.status        → media_item.status ("want" → "planned" vb.)
                        Eşlemeyi tam yaz; kayıp durum bırakma.
   book.rating        → media_item'da karşılığı var mı? yoksa nasıl taşınacak?
   book.started_at / finished_at → media_cycle mı, kolon mu?
   book.notes         → ?
   Eşlemeyi docs/faz11-kitap-esleme.md'ye tablo olarak yaz. Karşılığı olmayan
   alan varsa ya media_item'a ekle ya kaybını açıkça gerekçelendir.

2. MIGRATION (kural 9, 10):
   - Elle yaz, --autogenerate çıktısını kontrolsüz commit etme.
   - HER SQL komutu ayrı op.execute() — asyncpg tek prepared statement'a
     birden fazla komut almaz.
   - Adımlar: book satırlarını media_item'a taşı (entity.id KORUNUR — böylece
     mevcut link'ler, event'ler, tag'ler ve bookmark bağları kırılmaz),
     entity.type'ı "book" → "media_item" güncelle, sonra book tablosunu düşür.
   - entity.id'nin korunması ŞART: kural 1 gereği her şey entity.id'ye FK.
     Yeni id üretirsen geçmiş event'ler ve link'ler öksüz kalır.
   - down_revision'ı `alembic heads` çıktısındaki GERÇEK head'e ver;
     dosya adı numarasına güvenme (bkz. backend/alembic/README.md).
   - Migration'ı yazdıktan sonra alembic/README.md'deki zincir tablosunu güncelle.

3. KOD TEMİZLİĞİ:
   - learning modülünden Book modeli, şeması, servisi ve /books uçlarını kaldır.
   - EntityTypeSpec'ten "book" tipini kaldır (kural 13) — media_item zaten kayıtlı.
   - learning modülünün event_verbs'ünden "book.finished" çıkar; medya tarafında
     karşılığı var mı kontrol et, yoksa ekle.
   - frontend: LearningPage'in BooksTab'ı kalkar; kullanıcı kitap için Medya'ya
     gider. (Faz 12'de birleşik sayfada kaynak listesi olarak yeniden görünecek.)
   - core/types.ts'ten Book tipini kaldır.

4. GERİYE DÖNÜK BAĞLAR:
   Kitap entity'lerine bağlı mevcut link'ler ve bookmark kuyruğu
   (/learning/queue, bookmark.queue_kind) bozulmamalı. Migration'dan sonra
   bunları doğrulayan bir test yaz.

5. TESTLER:
   - Migration round-trip: book satırı → media_item, entity.id aynı kalıyor.
   - Taşınan kaydın event geçmişi ve link'leri duruyor.
   - backend/tests/test_migrations.py model↔migration karşılaştırması geçiyor.
   - Yedek/restore (system/backup.py) book tablosunu artık aramıyor —
     backup kapsamı metadata'sını güncelle, round-trip testi geçmeli.

DOĞRULAMA:
  make test CO="docker compose"
  cd backend && ruff check app tests scripts
  cd backend && python scripts/export_openapi.py
  cd frontend && npm run api:generate && npm run api:check
  cd frontend && npx vitest run && npm run build && npm run format:check
  node scripts/check-endpoint-coverage.mjs && node scripts/check-dead-exports.mjs

RİSK UYARISI: Bu veri kaybettirebilir. Migration'ı yazmadan önce
`make backup` çalıştırmayı öner ve upgrade() kadar downgrade()'i de yaz.

ÇIKTI: alan eşleme tablosu, migration özeti, kaldırılan uçlar, testler.
```

---

## PROMPT — FAZ 12: Çalışma + Öğrenme birleşmesi

```
forkOS deposunda çalışıyorsun. AGENTS.md, CLAUDE.md ve docs/mimari.md'yi oku.
Faz 11 (kitap tekilleştirme) TAMAMLANMIŞ olmalı — bu faz onun üstüne biner.

GÖREV: `study` ve `learning` modüllerini tek "Öğrenme" modülünde birleştir ve
aralarındaki bağı kur.

NEDEN (doğrulanmış):
  İkisi aynı işin iki yarısı ama kod tabanında BİRBİRİNE HİÇ DEĞMİYOR:
    study:    study_area → study_topic (ağaç, parent_id, confidence,
              target_min, last_studied_at)  = NE öğreniyorum
    learning: course (+ Faz 11'den sonra kitaplar media_item'da)
              + bookmark kuyruğu (queue_kind)  = NEYLE öğreniyorum
  grep ile doğrulandı: study modülü course/book'tan, learning modülü
  study/topic'ten hiç bahsetmiyor. Sıfır link, sıfır ortak sorgu.
  Sidebar'ın "Takip" grubunda yan yana iki ayrı giriş duruyor.

  Sonuç: "Lineer Cebir" konusunu çalışırken kullandığın Coursera kursunu iki
  ayrı sayfada, birbirinden habersiz takip ediyorsun.

1. BACKEND — MODÜLLERİ BİRLEŞTİR:
   - app/modules/study/ ve app/modules/learning/ → tek app/modules/learning/
     (adı sen seç; "learning" mevcut uçların çoğunu koruduğu için önerilir).
   - TABLOLAR AYNEN KALIR: study_area, study_topic, course. Şema değişikliği
     bu fazın işi DEĞİL; birleşen şey modül ve sayfa.
   - MODULES listesinde tek ModuleSpec: entity_types olarak study_area,
     study_topic, course (kural 13 — EntityTypeSpec'leri koru, rotalarını
     yeni birleşik sayfaya güncelle).
   - event_verbs'leri birleştir.
   - deadline_provider: kursun hedef tarihi varsa buradan besle (kural 16).
   - Uç yollarını KIRMA: /study/* ve /courses tek router altında toplansın
     ama yolları aynı kalsın; kırıcı değişiklik istiyorsan önce gerekçelendir.
   - Servis dosyası 600 satırı geçmesin (Faz 6 disiplini) — gerekiyorsa
     topics.py / resources.py diye böl.

2. KONU ↔ KAYNAK BAĞI (asıl kazanç):
   - Yeni şema YOK. Faz 3'te kurulan link altyapısını kullan:
       link(topic_id, resource_id, "learns_from")
     resource = course veya media_item (kitap/kurs/video farketmez).
   - İlişki sözlüğüne "learns_from" ekle (ileri/geri etiketiyle):
     örn. ("Kaynakları", "Çalışıldığı konu").
   - RelatedPanel zaten var — konu detayında kaynakları, kaynak detayında
     konuyu göstermek için onu kullan; paralel çözüm yazma.

3. FRONTEND — TEK SAYFA:
   - src/modules/study/ ve src/modules/learning/ → tek src/modules/learning/.
   - Sayfa düzeni: solda konu ağacı (study_area → study_topic), sağda seçili
     konunun kaynakları (bağlı course/media_item) + bookmark kuyruğu.
   - Konudan kaynağa bağlama: "kaynak ekle" → global aramadan seç → link kur.
   - modules/index.ts'ten bir satır düşer; sidebar "Takip" grubu bir giriş azalır.
   - StudyWidget ve varsa learning widget'ı tek Bugün widget'ında birleşsin:
     "devam eden konu + o konunun kaynağı". İki ayrı kutu olmasın.
   - Command Palette komutlarını birleştir; ölü komut bırakma.

4. TASARIM (kural 15):
   Yeni sayfa mevcut primitive'leri kullanacak: Section, RowList, Chip,
   Input/Select/Range/NumberInput, Empty. Ham HTML kontrolü, text-[Npx],
   sabit hex YOK. designSystem.test.ts zaten koruyor.

5. GÖÇ SONRASI TEMİZLİK:
   - Eski modül klasörleri tamamen silinsin; yarım bırakma.
   - core/types.ts'te artık kullanılmayan tipler kalmasın
     (check-dead-exports.mjs yakalar).
   - docs/mimari.md'yi güncelle: modül listesi ve "learns_from" ilişkisi.

6. TESTLER:
   - Birleşik modül tek ModuleSpec olarak kayıtlı, rotaları çözülüyor.
   - Konuya kaynak bağlama akışı (link kurulup RelatedPanel'de görünüyor).
   - Birleşik Bugün widget'ı render oluyor.
   - Eski /study ve /learning rotalarına gidince ne oluyor — yönlendirme
     ekliyorsan onu da test et.

DOĞRULAMA:
  cd backend && python scripts/export_openapi.py
  cd frontend && npm run api:generate && npm run api:check
  cd frontend && npx vitest run && npm run build && npm run format:check
  node scripts/check-endpoint-coverage.mjs && node scripts/check-dead-exports.mjs
  make test CO="docker compose"
  cd backend && ruff check app tests scripts
GÖRSEL: birleşik sayfayı 375 / 1280 px'te, açık ve koyu temada ekran
görüntüsüyle doğrula; output/ altına koy.

ÇIKTI: birleşen dosya yapısı, korunan/değişen uç yolları, learns_from
ilişkisinin nasıl kurulduğu, sidebar'ın son hali, ekran görüntüleri.
```

---

## Her fazdan sonra

```bash
cd frontend && npx vitest run && npm run build && npm run format:check
node scripts/check-endpoint-coverage.mjs && node scripts/check-dead-exports.mjs
cd .. && make test CO="docker compose"
cd backend && ruff check app tests scripts
```

Backend şeması değiştiyse önce:

```bash
cd backend && python scripts/export_openapi.py && cd ../frontend && npm run api:generate
```
