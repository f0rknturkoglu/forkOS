# V1 ürün kapsamı — kanonik sözleşme

forkOS **Academic & Career LifeOS**: tek kullanıcılı ve local-only akademik/kariyer çalışma alanı.
Bu belge güncel ürün kapsamının tek karar kaynağıdır. AGENTS.md teknik guardrail'leri tamamlar.

## Korunan ürün yetenekleri

Home / Today; Inbox / Capture; görevler ve plan; projeler; hedefler ve strateji;
Career ve Academia; forkjob_core ve career-ops; Learning; bağımsız Flashcards / SRS;
Calendar ve doğrudan Todo oluşturma; Pomodoro sayaç, geçmiş, elle kayıt,
düzenleme/silme/analitik; RSS / Feed ve bağımsız Bookmarks; Activity; Reviews;
kullanıcıya açık Diagnostics; yerel backup / restore.

## Emekli yüzeyler

Medya, Finans, bağımsız Documents ve bağımsız Knowledge UI ürün değildir.
Google Drive entegrasyonu emeklidir. Bu ürünler için yeni API, mutation,
provider polling, scheduler işi, navigasyon, komut, widget veya ayar oluşturulmaz.

## Korunan altyapı ve sahiplik

Obsidian Vault ve bilgi köprüsü; agent memory, retrieval, semantic memory ve
mevcut MCP; Entity / Link / append-only Event; scheduler ve kaynak kuyruğu;
kariyer belge işleme, CV ve yerel attachment; Google Calendar; GitHub; yerel yedekler.
Career dokümanları Document modeli/servisini kullanabilir. Obsidian bilgi sahibidir;
forkOS ikinci bilgi deposu veya editörü kurmaz. RSS ve Bookmarks bağımsız kalır.

## Tarihsel uyumluluk ve veriler

Medya/Finans/legacy Notes tabloları ve dosyaları metadata/yedek/restore için korunur.
Emekli entity tipleri searchable/linkable değildir; olay etiketleri okunabilir kalır.
Medya tüketimi emek haritasında **medya (arşiv)** olarak gösterilir; Finans yalnız audit
akışında yer alır. Bunlar aktif ürün linki oluşturmaz.
Eski note focus URL'leri hafif Vault çözümleyicisini kullanır; diğer eski rotaların
hedefleri [navigasyon sözleşmesinde](../product-navigation.md) listelenmiştir.
Hiçbir kişisel DB, belge, Vault veya credential bu kapanış için silinmez.

## Ölçüm ve çapraz modül sınırları

Pomodoro canlı effort kayıtları `pomodoro_session` tablosundan; geçmiş işlem akışı
Event'ten gelir. Yerel başlangıç günü oturumun günüdür. Review snapshot'ları
oluşturuldukları kanıtı korur; canlı önizlemeler güncel kayıtları kullanır.
Learning / Reviews / Activity / Statistics bu semantiği paylaşır. Project timeline
ve agent action delta tarihsel işlem akışıdır; dönem delta içindeki odak süreleri
ayrıca güncel oturum kayıtlarından hesaplanır.
Goals mevcut sahip olduğu ilerleme sağlayıcılarını kullanır; yeni effort modeli yoktur.
Ortak registry, entity helper, invalidateAfter, SourceAdapter, loopback ve API
sözleşmeleri üzerinden bağımlılık kurulabilir; emekli runtime bağımlılığı kurulamaz.

## Entegrasyon izinleri

Yeni Google OAuth yalnız Calendar scopes ister. Önceden verilmiş Drive hesabı grant'i
scope değişince otomatik geri alınmaz; kullanıcı kendi Google hesap izinlerinden
yönetebilir. Yerel disconnect yalnız yerel token'i kaldırır; uzaktan revoke etmez.

## Gelecekte modül ekleme

Yeni ürün için bu kapsam açıkça güncellenir; korunacak veri ve sahiplik belirtilir.
Backend ve frontend tek registry noktalarına kaydedilir. API tüketimi, scheduler/MCP,
nav/komut/widget, migration, yerel gizlilik ve regresyon kontratları birlikte doğrulanır.
Emekli bir modül yalnız text ref veya tarihi DB kaydı var diye yeniden etkinleştirilmez.
