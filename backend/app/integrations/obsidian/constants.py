from __future__ import annotations

#: Birinci sürümde izin verilen managed note tipleri
ALLOWED_FORKOS_TYPES: set[str] = {
    "note",
    "project",
    "learning",
    "career",
    "source",
    "memory",
}

#: Tip bazında varsayılan hedef klasörler
TYPE_DEFAULT_FOLDERS: dict[str, str] = {
    "note": "00 Inbox",
    "project": "20 Projects",
    "learning": "40 Learning",
    "career": "50 Career",
    "source": "60 Sources",
    "memory": "90 Agent",
}

#: Managed not türleri. PHASE 2 migration ile AYNI sözlük: yeni notlar da bu
#: değerleri yazar, böylece Vault indeksi tek şemayla okunur.
NOTE_KIND_PERSONAL = "personal"
NOTE_KIND_DAILY = "daily"
NOTE_KIND_PROJECT_JOURNAL = "project_journal"
NOTE_KIND_BOOKMARK = "bookmark_note"

ALLOWED_NOTE_KINDS: frozenset[str] = frozenset(
    {NOTE_KIND_PERSONAL, NOTE_KIND_DAILY, NOTE_KIND_PROJECT_JOURNAL, NOTE_KIND_BOOKMARK}
)

#: Kanonik klasör kökleri (PHASE 2 plan.py hiyerarşisiyle aynı).
#: Migration personal notları `00 Inbox/Imported/` altına koyar; yeni
#: yakalamalar `00 Inbox/` köküne yazılır -- ikisi çakışmaz.
INBOX_ROOT = "00 Inbox"
DAILY_ROOT = "10 Daily"
PROJECTS_ROOT = "20 Projects"
LEARNING_ROOT = "40 Learning"
SOURCES_ROOT = "60 Sources"
JOURNAL_FOLDER = "Journal"

#: Operasyonel entity tipi -> (forkos_type, kanonik klasör).
#: Bu tiplerin TEK bilgi notu olur; kimlik entity UUID'sidir.
#: `note` tipi, notun entity'nin KENDİSİ değil "hakkında" olduğu durumdur:
#: bu durumda frontmatter'a `notes_about` ilişkisi de yazılır.
ENTITY_KNOWLEDGE_TARGETS: dict[str, tuple[str, str]] = {
    "project": ("project", PROJECTS_ROOT),
    "study_topic": ("learning", LEARNING_ROOT),
    "bookmark": ("source", SOURCES_ROOT),
    "opportunity": ("note", INBOX_ROOT),
}

#: `forkos_type == "note"` olan kanonik notlarda ilişki metadata'sı yazılır;
#: proje/öğrenme/kaynak notları zaten kaydın kendisidir, ilişki gerekmez.
RELATED_ENTITY_NOTE_TYPES: frozenset[str] = frozenset({"note"})

#: Vault'ta kullanıcıya ait serbest frontmatter alanları; forkOS bunları
#: güncelleme sırasında KORUR (bkz. service.update_managed_note_body).
FORKOS_METADATA_PREFIX = "forkos_"

#: Bu öneki taşıyan ama servis tarafından bilinmeyen alanlar da kullanıcı
#: alanı sayılır ve aynen korunur.
FORKOS_OWNED_KEYS: frozenset[str] = frozenset(
    {
        "forkos_id",
        "forkos_type",
        "forkos_note_kind",
        "forkos_created_at",
        "forkos_updated_at",
        "forkos_captured_from",
        "forkos_entity_type",
        "forkos_project_id",
        "forkos_journal_day",
        "forkos_source_bookmark_id",
        "forkos_relations",
    }
)
