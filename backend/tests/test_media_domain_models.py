from __future__ import annotations

from sqlalchemy import CheckConstraint, Numeric

from app.core import models as core_models
from app.core import notifications as core_notifications
from app.core import schemas as core_schemas
from app.core.router import router as core_router
from app.modules.media import MODULE
from app.modules.media import models as media_models
from app.modules.opportunity.router import router as opportunity_router

pytestmark = __import__("pytest").mark.no_database


def _column_names(model: type) -> set[str]:
    return {column.name for column in model.__table__.columns}


def _foreign_key(model: type, column_name: str):
    foreign_keys = list(model.__table__.c[column_name].foreign_keys)
    assert len(foreign_keys) == 1
    return foreign_keys[0]


def _check_sql(model: type) -> str:
    return " ".join(
        str(constraint.sqltext)
        for constraint in model.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    )


def test_media_item_exposes_provider_and_cached_summary_fields():
    MediaItem = media_models.MediaItem
    expected = {
        "id",
        "kind",
        "status",
        "progress",
        "total",
        "score",
        "notes",
        "started_at",
        "finished_at",
        "meta",
        "summary",
        "release_date",
        "progress_measure",
        "review",
        "favorite",
        "owned",
        "ownership",
        "monitored",
        "provider",
        "provider_id",
        "provider_ids",
        "cover_url",
        "cover_path",
        "backdrop_url",
        "backdrop_path",
        "last_synced_at",
    }
    assert _column_names(MediaItem) == expected

    for name in ("progress", "total"):
        column_type = MediaItem.__table__.c[name].type
        assert isinstance(column_type, Numeric)
        assert (column_type.precision, column_type.scale) == (12, 2)


def test_media_domain_models_are_entity_backed_with_expected_relationships():
    MediaItem = media_models.MediaItem
    MediaUnit = getattr(media_models, "MediaUnit", None)
    MediaCycle = getattr(media_models, "MediaCycle", None)
    MediaConsumption = getattr(media_models, "MediaConsumption", None)
    MediaCollection = getattr(media_models, "MediaCollection", None)
    assert all((MediaUnit, MediaCycle, MediaConsumption, MediaCollection))
    expected_entity_types = {
        MediaItem: "media_item",
        MediaUnit: "media_unit",
        MediaCycle: "media_cycle",
        MediaConsumption: "media_consumption",
        MediaCollection: "media_collection",
    }
    for model, entity_type in expected_entity_types.items():
        assert entity_type == model.ENTITY_TYPE
        assert _foreign_key(model, "id").target_fullname == "entity.id"
        assert _foreign_key(model, "id").ondelete == "CASCADE"

    assert _foreign_key(MediaUnit, "media_id").target_fullname == "media_item.id"
    assert _foreign_key(MediaUnit, "media_id").ondelete == "RESTRICT"
    assert _foreign_key(MediaUnit, "parent_id").target_fullname == "media_unit.id"
    assert _foreign_key(MediaUnit, "parent_id").ondelete == "SET NULL"
    assert _foreign_key(MediaCycle, "media_id").target_fullname == "media_item.id"
    assert _foreign_key(MediaCycle, "media_id").ondelete == "RESTRICT"
    assert _foreign_key(MediaConsumption, "media_id").target_fullname == "media_item.id"
    assert _foreign_key(MediaConsumption, "media_id").ondelete == "RESTRICT"
    assert _foreign_key(MediaConsumption, "cycle_id").target_fullname == "media_cycle.id"
    assert _foreign_key(MediaConsumption, "cycle_id").ondelete == "RESTRICT"
    assert _foreign_key(MediaConsumption, "unit_id").target_fullname == "media_unit.id"
    assert _foreign_key(MediaConsumption, "unit_id").ondelete == "SET NULL"

    assert _column_names(MediaUnit) == {
        "id",
        "media_id",
        "parent_id",
        "unit_type",
        "number",
        "duration_min",
        "release_at",
        "progress_total",
        "progress_measure",
        "provider",
        "provider_id",
        "provider_ids",
        "cover_url",
        "cover_path",
        "meta",
        "created_at",
        "updated_at",
    }
    assert _column_names(MediaCycle) == {
        "id",
        "media_id",
        "ordinal",
        "status",
        "started_at",
        "completed_at",
        "last_caught_up_at",
        "score",
        "notes",
        "created_at",
        "updated_at",
    }
    assert _column_names(MediaConsumption) == {
        "id",
        "media_id",
        "cycle_id",
        "unit_id",
        "client_uuid",
        "action",
        "measure",
        "amount",
        "progress_after",
        "occurred_at",
        "duration_min",
        "note",
        "meta",
        "created_at",
        "updated_at",
    }
    assert _column_names(MediaCollection) == {
        "id",
        "description",
        "color",
        "position",
        "created_at",
        "updated_at",
    }


def test_media_domain_constraints_and_partial_indexes_are_declared():
    MediaItem = media_models.MediaItem
    MediaUnit = getattr(media_models, "MediaUnit", None)
    MediaCycle = getattr(media_models, "MediaCycle", None)
    MediaConsumption = getattr(media_models, "MediaConsumption", None)
    assert all((MediaUnit, MediaCycle, MediaConsumption))
    item_indexes = {index.name: index for index in MediaItem.__table__.indexes}
    assert item_indexes["media_item_provider_ref_uniq"].unique
    item_where = item_indexes["media_item_provider_ref_uniq"].dialect_options[
        "postgresql"
    ]["where"]
    assert item_where is not None
    unit_indexes = {index.name: index for index in MediaUnit.__table__.indexes}
    assert "media_unit_media_idx" in unit_indexes
    assert "media_unit_provider_ref_uniq" in unit_indexes
    assert unit_indexes["media_unit_provider_ref_uniq"].unique
    unit_where = unit_indexes["media_unit_provider_ref_uniq"].dialect_options["postgresql"][
        "where"
    ]
    assert unit_where is not None

    cycle_constraints = {constraint.name for constraint in MediaCycle.__table__.constraints}
    assert "media_cycle_media_ordinal_uniq" in cycle_constraints
    cycle_indexes = {index.name: index for index in MediaCycle.__table__.indexes}
    assert cycle_indexes["media_cycle_one_open_idx"].unique
    cycle_where = cycle_indexes["media_cycle_one_open_idx"].dialect_options["postgresql"][
        "where"
    ]
    assert cycle_where is not None

    consumption_constraints = {
        constraint.name for constraint in MediaConsumption.__table__.constraints
    }
    assert "media_consumption_client_uuid_uniq" in consumption_constraints
    consumption_indexes = {
        index.name: index for index in MediaConsumption.__table__.indexes
    }
    assert "media_consumption_media_time_idx" in consumption_indexes
    assert "media_consumption_cycle_time_idx" in consumption_indexes

    assert "unit_type" in _check_sql(MediaUnit)
    assert "status" in _check_sql(MediaCycle)
    assert "action" in _check_sql(MediaConsumption)
    assert "measure" in _check_sql(MediaConsumption)

    link_indexes = {index.name for index in core_models.Link.__table__.indexes}
    assert "media_collection_item_link_idx" in link_indexes
    source_sync_indexes = {
        index.name for index in core_models.SourceSyncBatch.__table__.indexes
    }
    assert "source_sync_batch_scope_time_idx" in source_sync_indexes


def test_media_module_registers_all_searchable_entity_types():
    specs = {spec.type: spec for spec in MODULE.entity_types}
    assert set(specs) == {
        "media_item",
        "media_unit",
        "media_cycle",
        "media_consumption",
        "media_collection",
    }
    # Ic muhasebe kayitlari (bolum/dongu/tuketim) global aramada gorunmez;
    # yalnizca kutuphane kaydi ve koleksiyon aranabilir.
    assert specs["media_item"].searchable is True
    assert specs["media_collection"].searchable is True
    for entity_type in ("media_unit", "media_cycle", "media_consumption"):
        assert specs[entity_type].searchable is False, entity_type


def test_notification_ownership_and_routes_are_core_scoped():
    Notification = getattr(core_models, "Notification", None)
    NotificationOut = getattr(core_schemas, "NotificationOut", None)
    assert Notification is not None
    assert NotificationOut is not None
    assert Notification.__module__ == "app.core.models"
    assert NotificationOut.__module__ == "app.core.schemas"
    assert core_notifications.notify.__module__ == "app.core.notifications"

    core_paths = {route.path for route in core_router.routes}
    opportunity_paths = {route.path for route in opportunity_router.routes}
    expected = {
        "/notifications",
        "/notifications/{notification_id}/read",
        "/notifications/read-all",
        "/notifications/{notification_id}/dismiss",
        "/notifications/dismiss-all",
    }
    assert expected <= core_paths
    assert not expected & opportunity_paths


def test_source_sync_batch_has_non_nullable_opportunity_scope():
    SourceSyncBatch = core_models.SourceSyncBatch
    assert "scope" in SourceSyncBatch.__table__.c
    scope = SourceSyncBatch.__table__.c.scope
    assert not scope.nullable
    assert scope.default is not None
    assert scope.default.arg == "opportunity"
