# forkOS — Existing Dependency Inventory & Migration Boundaries

Bu belge, forkOS Slim vizyonu kapsamında mevcut kod tabanındaki **Notlar**, **Projeler** ve **Graf** bileşenlerinin gerçek bağımlılık haritasını ve gelecekteki sahiplik (ownership) sınırlarını kayıt altına alır.

---

## 1. Ürün Sınırları ve Mimari İlkeler

- **forkOS (Operational State / Execution System):** Günlük operasyon, zaman yönetimi, görevler, rutinler, ajanda, hedefler, kaynak akışları ve bildirimler.
- **Obsidian Vault (Human Knowledge / Long-Term Knowledge):** İnsan düşüncesi, araştırma, karar kayıtları, uzun yazılar, günlük yazılı günlükler, kavramsal öğrenme notları, wikilink'ler ve bilgi grafı.
- **Gelecek Ajan Katmanı:** forkOS'un anlık canlı durumu (live state) ile Vault'un uzun vadeli bilgi tabanını (knowledge) birleştirerek karar üretir.

---

## 2. Kapsamlı Bağımlılık Envanteri

Aşağıdaki tablo kod tabanı doğrudan taranarak oluşturulmuştur:

| Feature | Current Owner | Dependencies | Future Owner | Migration Difficulty | Action |
|---|---|---|---|---|---|
| **Note Core Entity & Text Body** | forkOS (`note` table, `Note.body`) | `Entity`, `EntityBacked`, DB TSVector search, `refs.py` | Obsidian Vault (`00 Inbox/`, `30 Knowledge/`) | Medium | `MOVE_TO_VAULT` |
| **Note Folders Tree** | forkOS (`note_folder` table) | `EntityBacked`, Self-referencing FK, `NotesExplorer.tsx` | Obsidian Vault (Filesystem klasörleri) | Easy | `MOVE_TO_VAULT` |
| **Note Attachments (Blobs)** | forkOS (`note_attachment`, `data/attachments/`) | Content-addressed SHA-256 store, `export.py`, `restore.py`, `maintenance.py` | Obsidian Vault (`Attachments/` klasörü) | Medium | `MOVE_TO_VAULT` |
| **Personal Daily Journal** | forkOS (`Note.journal_day` w/o project) | `note` table, `todayKey()`, calendar navigation | Obsidian Vault (`10 Daily/YYYY-MM-DD.md`) | Easy | `MOVE_TO_VAULT` |
| **Project Journal Entries** | forkOS (`Note.journal_day` + `project_id`) | `project.service.py`, `ProjectJournal.tsx`, `Note` | Obsidian Vault (`20 Projects/<Project>/Journal/`) | Medium | `MOVE_TO_VAULT` |
| **Excalidraw Canvas Notes** | forkOS (`Note.canvas_state`, `NoteCanvas.tsx`) | JSONB scene state, `@excalidraw/excalidraw` frontend | Obsidian Canvas / Excalidraw plugin | High | `REVIEW` |
| **Wikilinks Extraction & Mentions** | forkOS (`core/refs.py`, `WIKILINK` regex) | `Link` table (`relation='mentions'`), `core/links.py` | Obsidian Native Index (Yerel `[[...]]`) | Easy | `MOVE_TO_VAULT` |
| **Inline Tags Extraction** | forkOS (`core/refs.py`, `core/tags.py`) | `Tag` table, `Entity` tag links | Obsidian Native Tags (`#etiket`) | Easy | `MOVE_TO_VAULT` |
| **Backlinks Panel & API** | forkOS (`/entities/{id}/backlinks`, `graph.py`) | `Link.mentions`, `NotesPage.tsx` | Obsidian Native Backlinks | Easy | `MOVE_TO_VAULT` |
| **Notes Explorer UI** | forkOS (`NotesExplorer.tsx`) | `@/core/ui`, folder tree state, drag-drop | Obsidian Native File Explorer | Low (UI drop) | `DEPRECATE` |
| **Notes Page & Rich Editor** | forkOS (`NotesPage.tsx`) | Markdown editor, preview, media attachments UI | Obsidian Native Desktop/Mobile App | Low (UI drop) | `DEPRECATE` |
| **Slash Command Menu** | forkOS (`SlashCommandMenu.tsx`) | Note editor cursor state, task/date macros | Obsidian Native / Community plugins | Low (UI drop) | `DEPRECATE` |
| **Note Breadcrumbs** | forkOS (`NoteBreadcrumbs.tsx`, `noteNavigation.ts`) | Folder hierarchy, URL hash route | Obsidian Native Breadcrumbs | Low (UI drop) | `DEPRECATE` |
| **Bookmark Highlights to Note** | forkOS (`bookmark_highlight`, `bookmark/service.py`) | `bookmark` table, `NoteIn` creation | forkOS (Highlight saklama) + Vault Bridge | Medium | `BRIDGE` |
| **Note Entity Registry & Full Search** | forkOS (`EntityTypeSpec('note')`, `search_vec`) | `entity` search, Command Palette, global search | forkOS (Operational items) + Vault Index Bridge | Medium | `BRIDGE` |
| **Note Backup & Restore** | forkOS (`export.py`, `restore.py`) | Full JSON dump, base64 blobs carrying | Obsidian Vault (Git/Cloud yerel yedekleme) | Low | `SLIM` |
| **Project Core Entity & Status** | forkOS (`project` table) | `EntityBacked`, status, next_action, position | forkOS Operational State | None (Stay in forkOS) | `KEEP` |
| **Project Milestones & Deadlines** | forkOS (`milestone` table) | `EntityBacked`, `DeadlineRow`, `Milestones.tsx` | forkOS Operational State | None (Stay in forkOS) | `KEEP` |
| **Project-Todo Relationship** | forkOS (`Todo.project_id`, `Todo.milestone_id`) | `todo` table, parent/subtask inheritance | forkOS Operational Execution | None (Stay in forkOS) | `KEEP` |
| **Project GitHub Integration** | forkOS (`project.github_repo`, `GithubPanel.tsx`) | GitHub API, issue to todo conversion | forkOS Execution System | None (Stay in forkOS) | `KEEP` |
| **Project Activity Tracking** | forkOS (`last_activity_at`, GitHub commits) | `github_activity`, `today/service.py` | forkOS Operational State | None (Stay in forkOS) | `KEEP` |
| **Today Project Widget & Context** | forkOS (`ProjectsWidget.tsx`, `_project_context`) | Today rhythm scoring, focus sorting | forkOS Daily Execution | None (Stay in forkOS) | `KEEP` |
| **CaptureDialog Project Assignment** | forkOS (`CaptureDialog.tsx`) | Quick capture modal, task project selection | forkOS Operational State | None (Stay in forkOS) | `KEEP` |
| **Project Knowledge / Research / Specs**| forkOS (Dağınık proje günlükleri ve notlar) | `Note` records, `note_project_journal_day_uniq` | Obsidian Vault (`20 Projects/<Project>.md`) | Low (New bridge) | `BRIDGE` |
| **Domain Graph (Core)** | forkOS (`Entity`, `Link`, `Event` tables) | PK/FK backbone, operational relationships | forkOS Core Architecture | None (Core foundation) | `KEEP` |
| **Knowledge Graph Visualization UI** | forkOS (`GraphView.tsx`, `d3-force` SVG) | `/graph` endpoint, node physics, SVG render | Obsidian Native Knowledge Graph | Low (UI drop) | `DEPRECATE` |
| **Knowledge Graph Page** | forkOS (`GraphPage.tsx`, `/graph` route) | `GraphView`, depth slider, focus zoom | Obsidian Native Graph View | Low (UI drop) | `DEPRECATE` |

---

## 3. Ayrım Detayı: Domain Graph vs Knowledge Graph

### 3.1 Domain Graph (forkOS'un Omurgası — KESİNLİKLE KORUNACAK)
forkOS içindeki her işlem nesnesi (`todo`, `project`, `course`, `topic`, `bookmark`, `opportunity`, `expense`, `document`) `Entity` tablosuna bağlıdır ve nesneler arası operasyonel ilişkiler `Link` tablosunda saklanır.
Örnekler:
- `todo -> project` (aitlik)
- `todo -> study_topic` (öğrenme pratiği)
- `bookmark -> entity` (ilişkili kaynak)
- `opportunity -> note/document` (başvuru evrakı)

Bu ilişkiler forkOS'un yürütme motorudur, sorgulanabilir, atomik ve foreign-key güvencelidir. Kesinlikle silinmeyecek ve değiştirilmeyecektir.

### 3.2 Knowledge Graph UI (İnsan Bilgi Görselleştirmesi — OBSIDIAN'A DEVREDİLECEK)
Mevcut `GraphView.tsx` ve `GraphPage.tsx` bileşenleri:
- Notlar arasındaki `[[wikilink]]` bağlantılarını SVG üzerinde d3-force ile çizer.
- Not odaklı serbest gezinim sağlar.

Bu işlevsellik Obsidian'ın yerel graf motorunda (Graph View / Local Graph / Canvas) çok daha yüksek performansla, filtreleme, renklendirme ve derinlik desteğiyle halihazırda mevcuttur. forkOS frontend'indeki ağır SVG simülasyonu zamanla dejenere olmadan kullanımdan kaldırılabilir (`DEPRECATE`).

---

## 4. Aksiyon Grupları ve Geçiş Stratejisi

1. **KEEP (forkOS'ta Kalacaklar):**
   - Project entity, durumlar, sıradaki aksiyon (`next_action`).
   - Milestone ve teslim tarihleri (`due_at`).
   - Todo, rutinler, planlayıcı, alt görevler.
   - GitHub entegrasyonu (issue -> task).
   - Today widget'ları ve proje bağlamı.
   - `Entity`, `Link`, `Event` domain mimarisi.

2. **BRIDGE (Hibrit Köprü Kurulacaklar):**
   - Proje bilgi notları (`forkos_id` frontmatter ile Obsidian'da tek tıkla açılabilen `20 Projects/<Project>.md`).
   - Vault metadata index ve status API (`/api/obsidian/status`, `/api/obsidian/items/{id}`).
   - Gelecekte: Web'den kırpılan bookmark ve highlight özetlerinin Vault'a aktarımı.

3. **MOVE_TO_VAULT (Planlı Olarak Taşınacaklar - Bu turda değil, sonraki fazda):**
   - Kişisel notlar (`note` tablosu -> Markdown dosyaları).
   - Günlük yazılar (`journal_day` -> `10 Daily/YYYY-MM-DD.md`).
   - Proje günlükleri (`20 Projects/<Project>/Journal/`).
   - Ekler (`data/attachments` -> `Attachments/`).

4. **DEPRECATE (Gereksizleşip Kaldırılacak UI Katmanları):**
   - `NotesPage.tsx` (53 KB) ve `NotesExplorer.tsx` (25 KB).
   - `GraphView.tsx` ve `GraphPage.tsx`.
   - `SlashCommandMenu.tsx`.
   - `NoteCanvas.tsx`.

5. **SLIM (Hafifletilecekler):**
   - `export.py` ve `restore.py`: Not gövdesi ve binary ekleri taşımayı bırakıp saf operasyonel veritabanı yedeğine dönüşecek.
