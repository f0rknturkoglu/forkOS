# forkOS — Notes Migration Design: Moving Knowledge to Obsidian Vault

Bu doküman, forkOS içindeki notların, günlüklerin, eklerin ve çizimlerin Obsidian Vault'a nasıl taşındığını (migration design) ayrıntılandırır.

> [!IMPORTANT]
> §1–§5 tasarım aşamasının kaydıdır; uygulanan gerçek §6'dadır. Taşıma (PHASE 2)
> **yapıldı** ve bilgi sahipliği devri (PHASE 3) **gerçekleşti**: forkOS artık
> Notlar'ın çalışma zamanı sahibi değildir, notlar f0rknbrain Vault'unda yaşar.
> Devrin sözleşmesi: `docs/obsidian-hybrid/phase3-cutover.md`.

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

### 3.1 Göç öncesi durum (tasarım kaydı)
- forkOS ekleri content-addressed olarak `backend/data/attachments/<sha256>` dosya adıyla tutuyordu.
- Metadata `note_attachment` tablosunda (`id`, `note_id`, `name`, `mime`, `sha256`) saklanıyordu.
- Not gövdesindeki bağlantılar `/api/notes/{note_id}/attachments/{attachment_id}` biçimindeydi veya base64 gömülüydü.

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

- **Mevcut Durum:** forkOS `note.canvas_state` JSONB alanında ham Excalidraw sahne verisi tutuyordu. PHASE 3'ten sonra bu alan **dondurulmuş arşiv**tir: hiçbir ürün akışı yazmaz, tuval arayüzü kaldırılmıştır (`@excalidraw/excalidraw` bağımlılığı dahil).
- **Uyumluluk Değerlendirmesi:** `PARTIAL / REVIEW`
  - Obsidian'ın yerel `.canvas` formatı JSON tabanlıdır ancak Excalidraw sahne formatından farklıdır (düğümler, kartlar ve kenarlar modelini kullanır).
  - Obsidian topluluğunun popüler **Obsidian Excalidraw** eklentisi mevcuttur ve ham Excalidraw JSON'unu `.excalidraw.md` içine gömerek birebir render eder.
- **Karar:**
  - Canvas çizimi içeren notlar geçiş sırasında `.excalidraw.md` eklenti formatında veya notun yanında `<Başlık>.excalidraw.json` yardımcı dosyası olarak dışa aktarılacaktır.
  - Kullanıcıya migration raporunda bu notlar açıkça listelenecektir.

---

# 6. Uygulanan Migration (Faz 2) — Gerçekleşen Durum

> [!NOTE]
> Yukarıdaki bölümler tasarım aşamasının kaydıdır. Bu bölüm, kopya+doğrulama
> migration'ının **uygulanmış gerçeğini** tanımlar ve önceki tasarımdan bilinçli
> olarak ayrıldığı noktaları belirtir.

## 6.0 Tasarımdan ayrılan kararlar

| Tasarım (§) | Uygulanan (§6) | Gerekçe |
|---|---|---|
| §2.2 günlük yinelenirse `YYYY-MM-DD (1).md` | `Başlık--<id8>.md` | Sıraya bağlı ad üretmek tekrar çalıştırmayı deterministik yapmaz |
| §3.2 ek adı `<Ad>_<sha8>.<uzantı>` | `Attachments/<Ad>--<sha8>.<uzantı>` | Tek ve tutarlı sonek biçimi; uzantı korunur |
| §3.2 yalnızca yeni ek kuşağı | Her iki kuşak (JSONB + blob) doğrudan okunur | Dönüşüm çağrılmadan da eksiksiz kopya |
| §4 "dönüştürme gerekmez" | Yinelenen başlık/tarih hedefleri tam yola genişletilir | Başlık çözümlemesi belirsiz kalmasın |
| §5 `<Başlık>.excalidraw.json` | `Attachments/Legacy Canvas/<uuid>.excalidraw.json` | Deterministik, çakışmasız, gizli olmayan ama işaretli yol |
| §2.3 proje günlüğü tipi | `forkos_type: note` + `forkos_note_kind: project_journal` | Vault'ta `project` tipi yalnızca proje bilgi notuna aittir |

## 6.1 Araç

```bash
python -m app.scripts.migrate_notes_to_vault --dry-run   # varsayılan
python -m app.scripts.migrate_notes_to_vault --apply
python -m app.scripts.migrate_notes_to_vault --verify
```

`--dry-run` Vault'a hiçbir şey yazmaz (manifest dahil). Kaynak veritabanı her
modda salt-okunur `REPEATABLE READ, READ ONLY` transaction içinde okunur.

Kod: `backend/app/integrations/obsidian/migration/`
(`source.py`, `plan.py`, `render.py`, `writer.py`, `manifest.py`, `verify.py`, `engine.py`).

## 6.2 Not türleri ve öncelik

`forkos_type` **her zaman** `note`tur — proje günlükleri dahil. Tür, ek alanda taşınır:

```yaml
forkos_note_kind: personal | daily | project_journal | bookmark_note
```

Öncelik (deterministik):

```text
project_id + journal_day  -> project_journal   (20 Projects/<Proje>/Journal/YYYY-MM-DD.md)
journal_day               -> daily             (10 Daily/YYYY-MM-DD.md)
source_bookmark_id        -> bookmark_note     (60 Sources/Imported/[<klasör>/]<Başlık>.md)
otherwise                 -> personal          (00 Inbox/Imported/[<klasör>/]<Başlık>.md)
```

`forkos_type: project` **yalnızca** projenin kanonik bilgi notunda bulunur
(`forkos_id` = Proje UUID'si); migration bu dosyaya dokunmaz.

## 6.3 Frontmatter sözleşmesi (`forkos_migration_version: 1`)

```yaml
---
forkos_id: "<legacy Note UUID>"
forkos_type: note
forkos_note_kind: personal
title: "<legacy Entity.title>"
forkos_created_at: "2026-09-14T12:00:00+00:00"   # ORIJINAL entity zamanı
forkos_updated_at: "2026-09-14T12:00:00+00:00"
forkos_migrated_at: "2026-09-20T09:00:00+00:00"  # kopyalama zamanı (ayrı alan)
forkos_state: active | archived | trashed
forkos_pinned: false
forkos_project_id: "<uuid>"          # yalnızca anlamlıysa
forkos_journal_day: "2026-09-14"     # yalnızca anlamlıysa
forkos_source_bookmark_id: "<uuid>"  # yalnızca anlamlıysa
source: "https://…"                  # yer imi bağlamı
source_title: "…"
forkos_legacy_folder_id: "<uuid>"
forkos_relations:                    # `mentions` DIŞINDAKİ not ilişkileri
  - relation: notes_about
    target_id: "<uuid>"
    target_type: opportunity
    target_title: "…"
forkos_canvas_sidecar: "Attachments/Legacy Canvas/<uuid>.excalidraw.json"
forkos_source_body_sha256: "<legacy body sha256>"
forkos_migration_version: 1
tags: [python, backend]
---
```

`trashed` arşivden baskındır; arşivden çöpe atılmışsa `forkos_trashed_from_archive: true`
eklenir. `forkos_migrated_at` dışındaki tüm alanlar kaynaktan deterministik olarak
türetilir; bu yüzden tekrar çalıştırma aynı baytı üretir.

## 6.4 Etiketler

Etiketler paylaşılan entity etiket sisteminden (`core/tags.py`) okunur, gövdedeki
`#etiket`ler dahil. YAML'a yazılır; gövdeye **etiket metni enjekte edilmez**.
Büyük/küçük harf duyarsız tekilleştirilir, yazım deterministiktir.

## 6.5 Ekler (iki kuşak)

Her iki depolama kuşağı doğrudan okunur — `convert_legacy_attachments()` **çağrılmaz**:

| Kuşak | Kaynak | Doğrulama |
|---|---|---|
| Yeni | `note_attachment` satırı + `data/attachments/<sha256>` | blob içeriğinin sha256'sı satırdaki özetle ve `size` ile karşılaştırılır |
| Legacy | `note.attachments` JSONB + base64 `data` | base64 çözülür, `size` doğrulanır |

- Hedef: `Attachments/<orijinal ad>`; aynı ad + farklı içerik → `Attachments/<ad>--<sha8>.<uzantı>`.
- Aynı içerik zaten varsa yeniden kullanılır (kopya oluşmaz).
- Eksik/bozuk ek: not `failed` işaretlenir, migration başarı iddia etmez.
- Kaynak blob **asla silinmez**.

Gövde referansları tam Markdown ifadeleri düzeyinde yeniden yazılır:

```markdown
![d](/api/notes/<n>/attachments/<a>)   ->  ![[Attachments/d.png]]
[PDF](/api/notes/<n>/attachments/<a>)  ->  [[Attachments/report.pdf|PDF]]
```

Kod blokları ve satır içi kod dokunulmaz. Gövdeye yerleştirilmemiş ekler
işaretli bir bölümle keşfedilebilir kalır:

```markdown
<!-- forkos:migrated-attachments -->

## Ekler

- [[Attachments/file-a.pdf]]
```

## 6.6 Wikilink'ler

- Hedef başlık forkOS'un mevcut çözümlemesiyle (`core/refs.py`) bir nota çözülür.
- Dosya adı (stem) başlıkla aynı **ve tek** ise bağlantı sade kalır.
- Aksi halde (yinelenen başlık, dosya adı farklı, günlük/tarih hedefi) tam yola genişletilir:
  `[[10 Daily/2026-01-05|Günlük hedefi]]`.
- Çözülemeyen bağlantılar ve not olmayan hedefler **aynen korunur** (Obsidian'da geçerli davranış).

## 6.7 Canvas

`canvas_state` boş değilse kayıpsız yan dosya yazılır:

```text
Attachments/Legacy Canvas/<note-uuid>.excalidraw.json
```

JSON hiçbir şemaya dönüştürülmez; kanonik JSON özeti manifest'e ve
`forkos_canvas_sidecar` alanına yazılır. Obsidian Canvas'a dönüşüm iddiası yoktur.

## 6.8 Deterministik çakışma politikası

- Aynı taban yola düşen notlar: `Başlık--<id8>.md` (id soneki). `(1)`, `(2)` YOK.
- Yönetilmeyen mevcut dosya: üzerine yazılmaz, id sonekli yol kullanılır.
- Aynı `forkos_id` iki dosyada: fail-closed; apply başlamaz.
- `forkos_id` ile kayıtlı managed dosya: doğrulanır, yeniden yazılmaz.

## 6.9 Manifest ve doğrulama kanıtı

```text
<Vault>/.forkos-migration/notes-v1/{manifest.json,report.md,errors.json}
```

Manifest her nottan sonra atomik yazılır (kesintiden sonra aynı `--apply` devam eder).
Durumlar: `planned | copied | verified | skipped_existing | blocked | failed | diverged`.

`--verify` yalnızca "dosya var mı" diye bakmaz; kimlik, gövde (yeniden üretilen
dönüşümle karşılaştırma), metadata, ek boyutu/özeti, canvas kanonik özeti ve
Vault indeks tekilliğini kontrol eder.

## 6.10 Kaynak parmak izi

Notlar, klasörler, ek satırları, legacy JSONB içerikleri, etiketler,
not kaynaklı link'ler ve canvas verisi üzerinden hesaplanan deterministik
sha256'dır. Rapor `SOURCE_FINGERPRINT_BEFORE` ve `AFTER` değerlerini yazar;
**eşit olmalıdır** — kaynağın değişmediğinin kanıtı budur.

## 6.11 Bu fazın sınırı ve sonrası

PHASE 2'nin sınırı buydu: taşıma kopya + doğrulamaydı, Notes sahipliği hâlâ
forkOS'taydı ve kaynak el değmemiş kalıyordu (parmak izi before == after).

**PHASE 3 bu sınırı kapattı.** Bilgi sahipliği private f0rknbrain Vault'una
geçti; legacy Notlar'ın çalışma zamanı yüzeyi kapandı (`/api/notes*`,
`/api/note-folders*` ve `/api/graph` rota kaydı YOKTUR; bilgi grafı
görselleştirmesi kaldırıldı) ve proje günlüğü, proje bilgi notu, öğrenme bilgi
notu, kaynak notu ile hızlı yakalama akışları Vault köprüsüne bağlandı. Legacy
tablolar, `data/attachments` deposu ve `note.*` olayları **dondurulmuş arşiv**
olarak yerinde durur; hiçbir migration tablo DROP etmez ve günlük bakım artık
ek dönüşümü çalıştırmaz. Bu belgedeki göç aracı ve doğrulama akışı
dondurulmuş kaynağa karşı aynen geçerlidir.

Devrin sözleşmesi, çalışma zamanı gereksinimleri, fail-closed davranış ve
geri dönüş yolu: `docs/obsidian-hybrid/phase3-cutover.md`.
