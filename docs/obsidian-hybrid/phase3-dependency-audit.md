# PHASE 3 — Legacy Notes bağımlılık denetimi

Her yüzeyin legacy Notlar'a olan bağımlılığı, yeni sahibi ve uygulanan
karar (silindi / korundu / köprülendi). Denetim, silme işleminden ÖNCE
yapıldı; silme kümesi bu tablodan türetildi.

Kısaltmalar: **S** = silindi, **K** = korundu, **B** = Vault'a köprülendi.

## 1. Frontend — legacy Notlar yüzeyi

| Surface | Legacy Notes dependency | New owner | Replacement | Karar |
|---|---|---|---|---|
| `modules/notes/NotesPage.tsx` (1278 LOC) | `/notes` CRUD, `/note-folders`, canvas, ekler, arşiv/çöp | f0rknbrain | `modules/knowledge/KnowledgePage.tsx` | **S** |
| `modules/notes/NotesExplorer.tsx` (667) | `/notes`, `/note-folders` | f0rknbrain | Obsidian dosya gezgini | **S** |
| `modules/notes/NotesExplorer.test.tsx` (293) | aynı | — | — | **S** |
| `modules/notes/NotesPage.test.tsx` (253) | aynı | — | `KnowledgePage.test.tsx` | **S** |
| `modules/notes/NoteCanvas.tsx` (258) | `canvas_state`, ekler, Excalidraw | Obsidian Canvas | Obsidian yerel canvas | **S** |
| `modules/notes/canvasAttachments.ts` (49) | `NoteAttachment` | — | — | **S** |
| `modules/notes/NoteCanvas.test.ts` (40) | `/api/notes/.../attachments` | — | — | **S** |
| `modules/notes/CanvasErrorBoundary.tsx` (31) | NoteCanvas sarmalayıcısı | — | — | **S** |
| `modules/notes/SlashCommandMenu.tsx` (189) | not editörü | — | — | **S** |
| `modules/notes/SlashCommandMenu.test.ts` (29) | not editörü | — | — | **S** |
| `modules/notes/BookmarkHighlights.tsx` (81) | `/highlights` çekmecesi | Obsidian araması | `Vault'ta ara` | **S** |
| `modules/notes/NoteBreadcrumbs.tsx` (58) | `/notes?folder=` | — | — | **S** |
| `modules/notes/noteNavigation.ts` (29) | `/notes` yolları | — | — | **S** |
| `modules/notes/index.ts` (26) | modül kaydı + `/graph` rotası | Bilgi köprüsü | `modules/knowledge/index.ts` | **S** |
| `core/wikilinks.ts` (29 + 39 test) | `[[wikilink]]` yardımcıları | Obsidian | Obsidian yerel çözümleme | **S** |
| `modules/flashcard/NoteFlashcardPanel.tsx` (48) | not → kart paneli | — | — | **S** |
| `modules/learning/TopicNotes.tsx` (269) | `GET /notes?about=`, `POST/DELETE /notes`, `notes_about` | f0rknbrain | `TopicKnowledgeNote.tsx` | **B** |
| `modules/learning/TopicNotes.test.tsx` (193) | aynı | — | `TopicKnowledgeNote.test.tsx` | **S** |
| `modules/projects/ProjectJournal.tsx` (203) | `PUT /projects/{id}/journal/{day}` | f0rknbrain | `ProjectActivityTimeline` + `ProjectJournalBridge` | **B** |
| `modules/projects/ProjectJournal.test.tsx` (172) | aynı | — | iki yeni test dosyası | **S** |
| `modules/projects/ProjectKnowledgeNote.tsx` | `POST /obsidian/items` (istemci kimliği) | zaten Vault | `ensureVaultItem(project.id)` | **B** |
| `ProjectJournalNote` / `resolved_links` / `unresolved_links` / `canvas_state` tipleri | legacy Notlar sözleşmesi | — | — | **S** |
| `runtimeQueries.ts` içindeki `note.*` sorgu anahtarı | `note.write` invalidation | — | — | **S** |

### Korunan ortak yüzeyler (gerekçeli)

| Surface | Neden korundu | Kalan tüketici |
|---|---|---|
| `core/Markdown.tsx` | paylaşılan Markdown görünümü | `flashcard/ReviewSession.tsx` |
| `core/markdownParser.ts` | ayrıştırıcı | `core/Markdown.tsx` |
| `core/capture.ts` / `CaptureDialog.tsx` | görev/kart/bağlantı yakalama akışları | `app/App.tsx`, `DropCapture`, flashcard, pomodoro, settings |
| `core/BacklinksPanel.tsx` | operasyonel ilişki yüzeyi | `learning/TopicDetail.tsx`, `media/MediaDetailPage.tsx` |
| `core/RelatedPanel.tsx` | operasyonel ilişki yüzeyi | tüm detay sayfaları |
| `core/obsidian.ts` | Vault köprüsü istemcisi | projects, learning, bookmarks, inbox, media, opportunity, settings |
| `core/entityRegistry.ts` | tipli rota/label kayıt defteri | tüm arama ve ilişki yüzeyleri |
| `core/Markdown.tsx` ek (attachment) API'si | YOK — tek tüketicisi NotesPage'di | kaldırıldı (**S**) |

## 2. Frontend — bilgi grafi

| Surface | Legacy Notes dependency | New owner | Replacement | Karar |
|---|---|---|---|---|
| `core/GraphView.tsx` (357) | yok — `/graph` ucu | — | — | **S** |
| `core/graphLayout.ts` (162) + testi (90) | yok | — | — | **S** |
| `core/graphInteraction.ts` (75) + testi (64) | yok | — | — | **S** |
| `modules/learning/GraphPage.tsx` (72) + testi (47) | `/notes?focus=` geri bağlantısı | — | — | **S** |
| `/graph` rotası + `graph.open` komutu | insan bilgi grafi görselleştirmesi | — | — | **S** |
| `d3-force` + `@types/d3-force` | tek tüketici `GraphView.tsx` | — | — | **S** |
| `@excalidraw/excalidraw` (+ build plumbing) | tek tüketici `NoteCanvas.tsx` | Obsidian Canvas | — | **S** |
| **Domain grafi** (`Entity`/`Link`/`Event`, `RelatedPanel`, `BacklinksPanel`, `belongs_to`, `prepares_for`, `learns_from`…) | yok | forkOS | korunur | **K** |

> §19/§20 ayrımı: **insan bilgi grafi GÖRSELLEŞTİRMESİ** kalkar; **domain
> grafiği** (varlık/ilişki altyapısı) aynen kalır. `/graph` ucunun tek HTTP
> tüketicisi `GraphView.tsx` idi, bu yüzden uç da kaldırıldı. Backlinks okuması
> operasyonel paneller için kaldı ve arşiv tiplerini süzer.

## 3. Backend — legacy Notlar çalışma zamanı

| Surface | Legacy Notes dependency | New owner | Replacement | Karar |
|---|---|---|---|---|
| `modules/note/router.py` (17 rota) | yazma + okuma CRUD | — | — | **S** (rota kaydı yok) |
| `modules/note/service.py` ürün yolları (927 → 536 LOC) | liste/okuma/ikili içerik/görünürlük geçişleri/ek dönüşümü | — | — | **S** |
| `modules/note/schemas.py` | HTTP sözleşmeleri | — | — | **K** (arşiv yazıcısının girdileri) |
| `modules/note/models.py` | `note`, `note_folder`, `note_attachment` şeması | forkOS arşivi | — | **K** (§5) |
| `modules/note/storage.py` | blob deposu | forkOS arşivi | — | **K** (yedek/göç uyumu); budama yolu **S** |
| `modules/note/__init__.py` router kaydı | CRUD yüzeyi | — | boş `APIRouter` | **S** |
| `modules/system/maintenance.py` `attachments` adımı | `convert_legacy_attachments`, `prune_orphan_blobs` | — | — | **S** |
| `modules/project/service.py` `upsert_journal_note` | `Note`/`NoteIn`/`NoteUpdate` | f0rknbrain | `POST /projects/{id}/journal/{day}/obsidian` | **B** |
| `modules/project/service.py` `journal()` not birleştirme | `Note` join | forkOS (olaylar) | `[{day, events}]` | **B** |
| `modules/learning/service.py` `_note_count` + `note_count` alanı | `notes_about` sayımı | f0rknbrain | `TopicKnowledgeNote` köprüsü | **S** |
| `modules/learning/service.py` `topic_impact` `notes` kolonu | `notes_about` sayımı | — | — | **S** |
| `modules/bookmark/service.py` `create_note_from_bookmark` | `Note` satırı + `source_bookmark_id` | f0rknbrain | `POST /bookmarks/{id}/source-note` | **B** |
| `modules/opportunity/router.py` `GET /opportunities/{id}/notes` | not listesi | — | — | **S** |
| `modules/opportunity/router.py` `POST /research-note` | `NoteIn`/`Note` | f0rknbrain | `POST /obsidian/ensure` + şablon gövde | **B** |
| `core/graph.py` `build()` + `GET /graph` | bilgi grafi görselleştirmesi | — | — | **S** |
| `core/graph.py` `backlinks()` | `mentions` bağları | forkOS | `core/links.py::backlinks` (+ arşiv süzgeci) | **K** (taşındı) |
| `core/links.py::related()` | arşiv not bağlarını canlı gösteriyordu | forkOS | `ARCHIVED_ENTITY_TYPES` süzgeci | **K** (düzeltildi) |
| `core/refs.py::sync_refs` | wikilink → `mentions` bağı | dondurulmuş arşiv yazıcısı | yalnız göç testi verisi üretir | **K** (sınırlandı) |
| `core/search.py` `searchable_types()` | `note` aranabilirdi | forkOS | `EntityTypeSpec.searchable=False` | **K** (düzeltildi) |
| `core/router.py` `GET /entities/{id}/backlinks` | `mentions` okuması | forkOS | `link_svc.backlinks` | **K** |
| `system/export.py`, `restore.py`, `storage_report.py`, `disaster.py` | yedek/geri yükleme uyumu | forkOS | — | **K** (§52/§53) |
| `integrations/obsidian/migration/**`, `scripts/migrate_notes_to_vault.py` | göç motoru | forkOS aracı | — | **K** (§7/§64) |
| Alembic migration'ları | `note*` tablolarını DROP etmez | forkOS arşivi | — | **K** (§5) |

## 4. Diğer tüketiciler

| Surface | Legacy Notes dependency | New owner | Replacement | Karar |
|---|---|---|---|---|
| `core/CaptureDialog.tsx` (Not sekmesi) | `POST /notes`, `pinned`, `relate_to` | f0rknbrain | `POST /obsidian/capture` | **B** |
| `core/capture.ts` (note dalı) | `POST /notes`, `note.write` | f0rknbrain | `captureVaultNote` + `obsidian.write` | **B** |
| `modules/bookmarks/BookmarkReaderModal.tsx` | `POST /bookmarks/{id}/create-note`, `/notes?focus=` | f0rknbrain | `POST /bookmarks/{id}/source-note` | **B** |
| `modules/inbox/InboxFocusTriageModal.tsx` | aynı | f0rknbrain | aynı | **B** |
| `modules/media/MediaDetailPage.tsx` not bestecisi | `POST /notes {relate_to}` | f0rknbrain | `POST /obsidian/capture` | **B** |
| `modules/media/MediaDetailPage.tsx` `notes` alanı | **domain alanı** (Note entity değil) | forkOS | dokunulmadı | **K** |
| `modules/opportunity/OpportunityDetailSections.tsx` not paneli | `GET /opportunities/{id}/notes`, `PATCH /notes/{id}` | f0rknbrain | `OpportunityKnowledgeSection` köprüsü | **B** |
| `modules/opportunity/AnnouncementDetail.tsx` | `POST /notes` | f0rknbrain | `captureVaultNote` | **B** |
| `modules/opportunity/JobDetail.tsx` | `POST /research-note` (note yükü) | f0rknbrain | aynı uç → `VaultItem` | **B** |
| `modules/opportunity` `notes`/`note` alanları | **domain alanları** | forkOS | dokunulmadı | **K** |
| `extension/` | `/notes` kullanmıyor (yalnız `/capture`) | — | — | **K** |

## 5. Karara bağlanan sorular

1. **Legacy router nasıl kapatıldı?** §42/B (410 compatibility router) yerine
   §42/A seçildi: hiçbir legacy rota kayıtlı değil. Gerekçe: (a) `extension`
   `/notes` kullanmıyor, dolayısıyla bekleyen bir istemci kuyruğu yok;
   (b) kayıtlı ama tüketilmeyen 17 uç `check-endpoint-coverage` eşiğini
   aşardı (kural 17). Eski bir istemci net bir 404 alır; hiçbir yazma oluşmaz.
2. **`note` / `note_folder` neden MODULES'te kaldı?** Şema kaydı
   (`Base.metadata`), tarihsel Aktivite/deep-link yönlendirmesi ve `note.*`
   olay sözlüğü için. `searchable=False`, `linkable=False` ile canlı bilgi
   kaydı gibi davranmazlar.
3. **`note/service.py` neden tamamen silinmedi?** PHASE 2 göç testleri (45
   test) kaynak verisini onunla üretiyor. Ürün yolları silindi, geriye
   yalnızca arşiv yazıcısı kaldı; dosya başlığı bu sınırı açıkça yazar.
4. **Opportunity araştırma notu neden `ensure`?** §38 gövdeyi `00 Inbox/` +
   ilişki olarak tarif eder; `ensure` bu klasörü kullanır ama kimliği fırsat
   UUID'sine bağlar, böylece "get-or-create" davranışı (idempotans) korunur.
5. **Daily note nasıl ele alındı?** forkOS günlük dosya YAZMAZ (§59): taşınmış
   günlük varsa onu açar, yoksa Obsidian'ın kendi `obsidian://daily` akışına
   devreder. Böylece çift günlük oluşmaz.
