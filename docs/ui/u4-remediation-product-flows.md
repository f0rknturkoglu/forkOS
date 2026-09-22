# forkOS — U4 Remediation: Product Flows

**Durum:** U4 REMEDIATION COMPLETE · U4 DOGFOOD PASS #2 REQUIRED. U4 henüz kapalı değil.

## Dogfood bulguları ve kararlar

U3 kabuğu çalışsa da alan başlığının yalnız aç/kapa yapması Öğrenme, Plan ve Kütüphane girişlerini gizliyordu. Plan'ın görev, hafta ve rutin ekranları aynı Todo verisini ayrı ürünler gibi sunuyordu. Kariyer'deki “kaydet” yer imi üretirken kullanıcının beklediği kısa liste durumuna geçmiyordu. Review ile Activity hem dönem anlatısını hem geçmiş bağlantılarını tekrarlıyordu. Genel finans akışı, yalnız abonelik takip etmek isteyen kullanıcıya gereksiz gelir/gider panosu gösteriyordu. RSS ve Feed aynı modülün iki rotası olmasına rağmen ayrı okuyucular gibi görünüyordu.

U4 kararı: domain tablolarını birleştirmek yerine mevcut registry, route, state machine ve event kanıtı üzerinde ekran sahipliğini düzeltmek. U1–U3'ün flat-first Section, açık Surface sınırı, Workspace, yerel toolbar, sakin yoğunluk ve klavye akışı ilkeleri korunur.

## Review ve Activity sahipliği

Review “Bu dönem ne anlama geldi?” sorusunun sahibidir. Haftalık, aylık ve yıllık dönemler URL'de `period=YYYY-MM-DD` ile taşınır. Önceki/sonraki dönem ve kayıt listesi Review'dedir. Günlük rota uyumluluk için kalır. Backend dönem sınırlarını yerel gün sınırı üzerinden hesaplar; yeni analitik tablo yoktur. Kayıt sırasında `review.stats` snapshot olur. Kaydedilmiş dönemin sayıları bu snapshot'tan okunur. `PATCH /reviews/{id}` yalnız notu kabul eder; dönem, tür, karar ve sayıları değiştirmez. Not değişimi append-only `review.note_updated` olayı üretir. Dönem özeti, tamamlananlar, önemli değişimler, istatistikler, açık kalanlar ve kendi notu ayrı görevler taşır.

Activity “Ne yaptım, ritmim nasıl değişti?” sorusunun sahibidir. Isı haritası, seri, özet ve trend üstte kalır. Ham olaylar kapalı “Detaylı geçmiş” bölümüne taşınır. Kişisel varsayılan akışta senkronizasyon, yedek, bakım ve otomatik medya olayları ile Review kaydı gizlenir; açık sistem filtresi ve backend event ledger korunur. Review geçmişi Activity'den kaldırıldı.

## Plan, Kariyer ve Öğrenme

Plan'ın yerel görünümleri Görevler, Bu Hafta ve Rutinlerdir. `/todos`, `/planner`, `/habits` çalışır. Üçü aynı `TodoComposer` ve `createTask` sözleşmesini kullanır. Haftalık görünümden açılan yeni görev seçili haftanın ilk gününe planlanır; gün alanı değiştirilebilir. Rutin görünümü tekrar kuralı olan Todo filtresidir ve oluşturucu haftalık tekrar önerir.

Kariyer'de ilanı kaydetmek keşif durumunu `shortlisted` yapar; “Kısa Listeye Al” eylemi ve görünür “Kısa Liste” filtresi vardır. Skor aralığı genel filtre panelinin içindedir. Çöpe atma hemen uygulanır, toast içindeki “Geri al” restore çağırır. Kalıcı silme hâlâ onay ister. Başvuruların varsayılanı Pipeline'dır; Takip ve İstatistik ayrı yerel görünümdür. Huni, hacim ve kırılım yalnız İstatistik'te açılır.

Öğrenme, Plan ve Kütüphane alan adları kendi landing rotasına gider; ayrı ok alt rotaları açar. Dar ray flyout korunur. Flashcard alanın altında yetenek olarak kalır; konu ağacı, kurs, tekrar, kaynak ve `/study` sözleşmeleri korunur.

## RSS, abonelikler ve Home

Kütüphane'deki okuma ürünü “RSS & Akış”tır. Varsayılan `/feed` birleşik RSS/Reddit/Hacker News/GitHub akışıdır; `/rss` kaynak yönetimine ve RSS okuyucuya gider. İki rota ortak yerel sekmelerle birbirine bağlıdır. Etkileşimli kaynak filtreleri Tabs düğmeleridir; canlı kaynak kimlikleri salt metin rozetidir. Akış gövdesinde `min-w-0`, `max-w-full` ve taşma sınırı vardır.

`/finance` rotası kalır fakat kullanıcı adı “Abonelikler”dir. Birincil yüzey aylık sabit yük, 7/30 günlük yaklaşan ödemeler, aktif abonelikler ve gerçek `recurring.paid` olaylarından ödeme geçmişini gösterir. Yeni `GET /recurring-payments/history` yalnız bu ödeme kanıtlarını okur. Genel gelir/gider verileri ve API'leri silinmez; birincil UI'da görünmez. Today ödeme hatırlatıcısı kalır. Home'un alttaki büyük metrik ızgarası kaldırıldı; günlük kısa özet hero altında ince yatay satırdır.

## Navigasyon ve uyumluluk

`/learning`, `/study`, `/todos`, `/planner`, `/habits`, `/feed`, `/rss`, `/finance`, `/review/daily`, `/review/weekly`, `/review/monthly`, `/review/yearly`, `/activity` korunur. Modül ve entity rotaları registry üzerinden çözülür. Calendar kodu, rotası ve projeksiyonu U4 kapsamında değiştirilmedi.

## API, QA ve doğrulama sınırı

Yeni Review PATCH ve abonelik ödeme geçmişi GET ucu frontend tarafından tüketilir. Review türleri OpenAPI ve üretilen TypeScript şemasında senkron tutulur. Yeni tablo veya migration yoktur. Testler dönem sınırı, snapshot'ın not düzenlemesinde değişmemesi, abonelik ödeme geçmişi, navigasyon, Plan oluşturma, Review, Activity, Kariyer ve okuyucu davranışlarını kapsar. Kod ve DOM düzeyinde QA yapılır; **tarayıcı otomasyonu, ekran görüntüsü ve görsel doğrulama bu görev talimatı gereği bilerek yapılmadı**. Bu nedenle responsive ve gerçek kullanım hissi ikinci dogfood turunda kullanıcı tarafından değerlendirilecektir.

## Ertelenen işler

**U5:** Kalan ekranların tam UI geçişi, gerçek kullanım sonrası görsel düzeltmeler ve Calendar'ın ayrı ele alınması.

**U6:** Event ledger boyut/indeks/saklama ve sorgu planı denetimi; operasyonel telemetri tekrarları; kullanılmayan Finance backend/şema temizliği; dar ekranda gizli inspector mount denetimi; registry/eager import bundle denetimi; genel ölü uyumluluk temizliği. Bu konular U4 sırasında varsayıma dayanarak optimize edilmedi.
