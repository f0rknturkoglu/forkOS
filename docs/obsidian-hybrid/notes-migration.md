# forkOS — Notes Migration Design: Moving Knowledge to Obsidian Vault

Bu doküman, gelecekteki geçiş aşamasında forkOS içindeki notların, günlüklerin, eklerin ve çizimlerin Obsidian Vault'a nasıl taşınacağını (migration design) ayrıntılandırır.

> [!IMPORTANT]
> Bu tur bir temel (foundation) ve envanter turudur. **Bu aşamada gerçek bir veri taşıması yapılmaz.** Burada tanımlanan kurallar, sonraki fazda çalıştırılacak migration executor tarafından birebir uygulanacaktır.

---

## 1. Klasör Yapısı ve Hedef Dağılımı

Vault'taki kök klasör mimarisi:

```text
Vault/
├── 00 Inbox/
│   └── Imported/       <-- forkOS'tan taşınan kişisel serbest notlar
├── 10 Daily/           <-- forkOS günlük yazıları (10 Daily/YYYY-MM-DD.md)
├── 20 Projects/        <-- Proje ana notları ve proje günlükleri
│   └── <Project Name>/
│       ├── <Project Name>.md
│       └── Journal/
│           └── YYYY-MM-DD.md
├── 30 Knowledge/       <-- İnsan tarafından organize edilecek kalıcı bilgi
├── 40 Learning/        <-- Öğrenme/çalışma notları
├── 50 Career/          <-- Kariyer ve fırsat notları
├── 60 Sources/         <-- Kaynak ve okuma notları
├── 90 Agent/           <-- Ajan bellek ve sistem çıktıları
└── Attachments/        <-- Tüm görsel, ses ve doküman ekleri
```

---

## 2. Not Türlerinin Dönüşüm Kuralları

### 2.1 Kişisel Serbest Notlar (Personal Notes)
- **Problem:** forkOS'taki serbest notlar `00 Inbox/` mu yoksa `30 Knowledge/` altına mı gitmeli?
- **Tasarım Kararı:** **Otomatik tahmin YAPILMAZ.**
  - Yazılımın kullanıcının hangi notunu "inbox" hangi notunu "kalıcı bilgi" sayacağını heuristiklerle tahmin etmesi bilgi mimarisini kirletir.
  - Tüm kişisel serbest notlar ilk geçişte deterministik olarak:
    `00 Inbox/Imported/[Klasör Adı/]<Sanitize Edilmiş Başlık>.md`
    altına yazılır.
  - Eğer not forkOS'ta bir `note_folder` içindeyse, o klasör hiyerarşisi `Imported/` altında korunur.
  - Kullanıcı Obsidian'ın güçlü dosya yöneticisinde bu notları istediği zaman `30 Knowledge/` veya alt konulara sürükleyip bırakabilir. `forkos_id` frontmatter'da korunduğu için dosyanın taşınması forkOS entegrasyonunu bozmaz.

### 2.2 Günlük Notlar (Daily Notes)
- **Kaynak:** `Note.journal_day IS NOT NULL` ve `Note.project_id IS NULL`.
- **Hedef:** `10 Daily/YYYY-MM-DD.md`
- **Biçim:**
  - Frontmatter:
    ```yaml
    ---
    forkos_id: "<note-uuid>"
    forkos_type: note
    created_at: "..."
    updated_at: "..."
    ---
    ```
  - İçerik: Orijinal günlük gövdesi.
  - Eğer aynı gün için birden fazla günlük notu varsa (nadir durum), deterministik olarak birleştirilir veya `YYYY-MM-DD (1).md` olarak ayrılır.

### 2.3 Proje Günlükleri (Project Journals)
- **Kaynak:** `Note.journal_day IS NOT NULL` ve `Note.project_id IS NOT NULL`.
- **Hedef:** `20 Projects/<Proje Başlığı>/Journal/YYYY-MM-DD.md`
- **Gerekçe:** Proje günlüğü, genel kişisel günlükten farklı bir bağlama sahiptir; projenin kararlarını, sprint güncellemelerini ve teknik adımlarını belgeler. Proje klasörünün altında izole olması Obsidian'da proje bağlamında çalışırken büyük kolaylık sağlar.

---

## 3. Ekler (Attachments) ve Medya Bağlantıları

### 3.1 Mevcut Durum
- forkOS ekleri content-addressed olarak `backend/data/attachments/<sha256>` dosya adıyla tutar.
- Metadata `note_attachment` tablosunda (`id`, `note_id`, `name`, `mime`, `sha256`) saklanır.
- Not gövdesindeki bağlantılar `/api/notes/{note_id}/attachments/{attachment_id}` veya base64 gömülüdür.

### 3.2 Hedef Vault Mimarisi: `Attachments/`
- **Hedef Yol:** `Attachments/<Orijinal_Dosya_Adi>` veya çakışma durumunda `Attachments/<Ad>_<sha256[:8]>.<uzanti>`.
- **Link Yeniden Yazımı (Rewrite):**
  - Not gövdesindeki yerel API URL'leri (`/api/notes/.../attachments/...`) Obsidian standart wikilink ek sözdizimine dönüştürülür:
    `![[Attachments/<Dosya_Adi>]]`
- **Dedup vs Named Copies Analizi:**
  - *Seçenek A (Tekil Hash):* Dosyalar diskte sha256 adıyla kalır (`![[Attachments/a1b2c3d4...png]]`). Ergonomi çok düşüktür; Obsidian içinde kullanıcı ne olduğunu anlayamaz.
  - *Seçenek B (Kullanıcı Dostu Adlar - TERCİH EDİLEN):* Dosyalar orijinal adlarıyla `Attachments/` klasörüne kopyalanır. Eğer aynı ada sahip iki farklı içerik varsa dosya adına kısa hash soneki eklenir: `screenshot_a8f12b.png`.
  - Bu yaklaşım Obsidian arama, önizleme ve mobil kullanım ergonomisini maksimize eder.

---

## 4. Wikilink ve Etiket Uyumluluğu

- forkOS'un halihazırda kullandığı regex (`core/refs.py`):
  - `[[Hedef Başlık]]` ve `[[Hedef Başlık|Görünen Metin]]`
  - `#etiket` (Türkçe karakter destekli)
- Bu yapı Obsidian'ın yerel wikilink ve tag standardıyla **%100 uyumludur**.
- Hiçbir sözdizimsel dönüştürme gerekmez; taşınan dosyalar Obsidian'da açıldığı anda bağlantılar ve etiketler yerel graf ve arama motoru tarafından anında tanınacaktır.

---

## 5. Excalidraw Canvas Notları

- **Mevcut Durum:** forkOS `note.canvas_state` JSONB alanında ham Excalidraw sahne verisi tutmaktadır.
- **Uyumluluk Değerlendirmesi:** `PARTIAL / REVIEW`
  - Obsidian'ın yerel `.canvas` formatı JSON tabanlıdır ancak Excalidraw sahne formatından farklıdır (düğümler, kartlar ve kenarlar modelini kullanır).
  - Obsidian topluluğunun popüler **Obsidian Excalidraw** eklentisi mevcuttur ve ham Excalidraw JSON'unu `.excalidraw.md` içine gömerek birebir render eder.
- **Karar:**
  - Canvas çizimi içeren notlar geçiş sırasında `.excalidraw.md` eklenti formatında veya notun yanında `<Başlık>.excalidraw.json` yardımcı dosyası olarak dışa aktarılacaktır.
  - Kullanıcıya migration raporunda bu notlar açıkça listelenecektir.
