"""Legacy Notes modülü — PHASE 3'te DONDURULMUŞ arşiv.

Bilgi sahipliği f0rknbrain Obsidian Vault'a taşındı. Bu modülün HTTP yüzeyi
KAPATILDI: eski `/notes` CRUD uçları artık kayıtlı değil (kural 17 gereği
tüketilmeyen uç bırakılmaz; kural 42/A seçeneği = en küçük uygulama).

Modül hâlâ kayıtlı, çünkü üç işi var:

  1. **Şema kaydı.** `models` import edilmezse `note`, `note_folder` ve
     `note_attachment` tabloları `Base.metadata`'dan düşer; Alembic, yedek ve
     geri yükleme yolları dondurulmuş arşivi göremez. Bu yüzden import
     ZİNCİRDEKİ YAN ETKİ olarak değil, burada AÇIKÇA yapılır.
  2. **Tarihsel kayıt defteri girdisi.** `note` / `note_folder` entity
     tipleri geçmiş Aktivite kayıtlarında ve `/notes?focus=<id>` derin
     bağlantılarında hâlâ geçiyor. Rotaları Bilgi köprüsüne işaret eder ama
     `searchable=False`, `linkable=False` oldukları için canlı bilgi kaydı
     gibi davranmazlar: global aramada çıkmaz, ilişki panellerinde görünmez.
  3. **Olay sözlüğü.** `note.*` event verb'leri append-only geçmişin
     etiketleridir; silinirse eski Aktivite satırları okunamaz hale gelir.
     Yeni `note.*` olayı ÜRETİLMEZ.

Bu modülün servis ve şema katmanları kaldırıldı: ürün akışları artık bilgi
yazmaz. Fiziksel tablolar ve `backend/data/attachments` kasıtlı olarak yerinde
bırakıldı; şema temizliği sonraki fazın işidir.
"""

from fastapi import APIRouter

from app.modules import EntityTypeSpec, ModuleSpec

#: Açık şema kaydı — bkz. modül docstring'i (1).
from app.modules.note import models as _models  # noqa: F401  (yan etki: tablo kaydı)

#: Legacy Notes HTTP yüzeyi kapalı: hiçbir rota kaydedilmez.
router = APIRouter()

MODULE = ModuleSpec(
    id="note",
    title="Notes",
    router=router,
    entity_types=[
        EntityTypeSpec(
            "note", "Not", "Notlar", "/notes?focus={id}", "StickyNote",
            searchable=False, linkable=False,
        ),
        EntityTypeSpec(
            "note_folder", "Not klasörü", "Not klasörleri",
            "/activity", "Folder", searchable=False, linkable=False,
        ),
    ],
    event_verbs=[
        "note.created", "note.updated", "note.pinned",
        "note.archived", "note.trashed", "note.restored", "note.archive_restored",
        "note.source_linked",
        "note.deleted", "note.attachment_added",
        "note.attachment_deleted", "note.moved", "note.folder_created",
        "note.folder_updated", "note.folder_deleted",
    ],
)
