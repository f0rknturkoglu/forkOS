"""V1 retired product. Schema and historical event vocabulary only; no active jobs or API."""
from fastapi import APIRouter

from app.modules.media import models as _models  # noqa: F401

router = APIRouter()


def _spec():
    from app.modules import EntityTypeSpec, ModuleSpec

    return ModuleSpec(id="media",
        title="Medya",
        router=router,
        entity_types=[
            EntityTypeSpec('media_item', 'Medya', 'Medyalar', '/activity', 'Film', searchable=False, linkable=False),
            EntityTypeSpec(
                'media_collection', 'Koleksiyon', 'Koleksiyonlar', '/activity', 'Library', searchable=False, linkable=False),
            EntityTypeSpec('media_unit', 'Bölüm', 'Bölümler', '/activity', 'FileVideo', searchable=False, linkable=False),
            EntityTypeSpec('media_cycle', 'Döngü', 'Döngüler', '/activity', 'RefreshCw', searchable=False, linkable=False),
            EntityTypeSpec('media_consumption', 'Tüketim', 'Tüketimler', '/activity', 'Play', searchable=False, linkable=False),
        ],
        event_verbs=[
            "media.item_added",
            "media.item_updated",
            "media.item_trashed",
            "media.item_restored",
            "media.item_deleted",
            "media.cycle_started",
            "media.cycle_completed",
            "media.cycle_reopened",
            "media.consumed",
            "media.session_logged",
            "media.progress_corrected",
            "media.collection_created",
            "media.collection_updated",
            "media.collection_deleted",
            "media.collection_item_added",
            "media.collection_item_removed",
            "media.release_discovered",
            "media.sync_completed",
            "media.sync_failed",
            "media.sync_empty",
            "media.artwork_pruned",
        ],
    )


MODULE = _spec()
