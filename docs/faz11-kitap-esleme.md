# Faz 11 — Kitap tekilleştirme: `learning.book` → `media_item`

Kitaplar iki ayrı tabloda tutuluyordu (`learning.book` + `media_item kind='book'`).
`media_item` kazanır: OpenLibrary/Google Books sağlayıcıları, kapak, tekrar
okuma döngüsü, koleksiyonlar, Bugün widget'ı, ilerleme düzeltme geçmişi var;
`learning.book` bunların hiçbirine sahip değil.

## Alan eşlemesi

| `book` | `media_item` | Not |
|---|---|---|
| `id` | `id` | **Korunur** (kural 1: her şey entity.id'ye FK; event/link/tag/bookmark bağları kırılmaz) |
| `title` | `entity.title` | entity'de zaten |
| `author` | `meta.author` | media_item'da yazar kolonu yok; JSONB `meta`'ya yazılır. UI kitap listesinde `meta.author`'ı gösterir |
| `total_pages` | `total` + `progress_measure='page'` | Numeric'e otomatik cast |
| `current_page` | `progress` + `progress_measure='page'` | |
| `status` | `status` (map) | Aşağıya bak |
| `rating` | `score` | 1–5 puan, Integer |
| `started_at` | `started_at` | `date` → `timestamptz` (UTC gece yarısı) |
| `finished_at` | `finished_at` | aynı |
| `notes` | `notes` | |
| — | `meta.legacy_book=true` | Migration işareti: downgrade'de hangi kayıtların geri taşınacağını söyler |

## Status eşlemesi

`media_item` STATUSES = `planned | in_progress | paused | completed | dropped`
(check constraint). `book.status` serbest metindi; bilinen değerler map'lendi,
bilinmeyen güvenli varsayılana düşer.

| `book.status` | `media_item.status` |
|---|---|
| `want` | `planned` |
| `reading` | `in_progress` |
| `done` | `completed` |
| `finished` | `completed` |
| `paused` | `paused` |
| `dropped` | `dropped` |
| (diğer) | `planned` |

## Kararlar

- **Yazar meta'da**: media_item'a `author` kolonu eklemek yerine mevcut
  JSONB `meta` kullanıldı — medya tarafı sağlayıcı bilgilerini zaten
  meta'da tutuyor; ayrı kolon kategorik aramada lazım olursa sonradan
  eklenebilir (o zaman da migration gerekir, bu fazda gerek yok).
- **`legacy_book` işareti**: downgrade'i deterministik yapar. Bu işaret
  olmasaydı, migration'dan SONRA medyada kind='book' ile eklenen yeni
  kitaplar da downgrade'de yanlışlıkla book'a dönerdi.
- **`book` tablosu boşaltılıp düşürülür**: upgrade'de INSERT sonrası
  `DROP TABLE book`; entity.type'lar `media_item`'a güncellenir.
- **Geriye dönük bağlar**: entity.id korunduğu için link'ler (bookmark
  `saved_from`, tag'ler) ve event geçmişi aynen durur; `bookmark.queue_kind`
  dokunulmaz.

## Migration özeti (0027_book_to_media_item)

- `down_revision = "0025_drop_deadline_v"` (gerçek head, dosya adına güvenilmez).
- upgrade: 1) book → media_item INSERT (status map + meta), 2) entity.type
  güncelle, 3) DROP TABLE book.
- downgrade: 1) CREATE TABLE book (eski şema), 2) taşınanları geri INSERT
  (ters status map, meta.author), 3) entity.type geri al, 4) taşınan
  media_item kayıtlarını sil.
- Her SQL komutu ayrı `op.execute()` (kural 10 — asyncpg tek statement).
