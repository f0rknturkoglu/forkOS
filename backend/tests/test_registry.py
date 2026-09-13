"""Kayit defteri sozlesmeleri (kural 13).

Her EntityTypeSpec.route frontend'de kayitli bir rota ile eslesmeli; tip->rota
bilgisi YALNIZCA EntityTypeSpec'te tutulur (frontend'de sabit yazilmaz).
"""

from __future__ import annotations

import re
from pathlib import Path

from app.core.registry import all_entity_types, all_event_verbs
from app.modules import MODULES

# Frontend registerModule route'lari (src/modules/*/index.ts). Yeni modul
# ekleyen buraya frontend rotasini da ekler -- kayit defteri ile senkron kalir.
FRONTEND_ROUTES = {
    "/bookmarks", "/inbox", "/rss", "/todos", "/planner", "/today", "/",
    "/pomodoro", "/review/daily", "/review/weekly", "/opportunities", "/sources",
    "/study", "/learning", "/documents", "/notes", "/calendar", "/media",
    "/media/collections", "/media/{id}",
    "/projects", "/finance", "/health", "/settings", "/activity", "/day",
    "/flashcard", "/statistics",
}


def test_registry_entity_types_routes_are_frontend_routes():
    for spec in all_entity_types():
        base = re.sub(r"\{id\}", "{id}", spec.route)
        # "{id}" yer tutucusu olan rotalar: /media/{id} gibi -- {id}'siz ana
        # kismi frontend rota setinde aranir.
        if "{id}" in base:
            prefix = base.split("{id}")[0].split("?")[0].rstrip("/") or "/"
            assert prefix in FRONTEND_ROUTES, (
                f"{spec.type} rotasi ({spec.route}) frontend'de yok"
            )
        else:
            queryless = base.split("?")[0]
            assert queryless in FRONTEND_ROUTES, (
                f"{spec.type} rotasi ({spec.route}) frontend'de yok"
            )


def test_registry_entity_types_are_unique():
    seen: dict[str, str] = {}
    for spec in all_entity_types():
        assert spec.type not in seen, f"yinelenen entity tipi: {spec.type}"
        seen[spec.type] = spec.route
    assert len(seen) >= 20, "kayit defteri beklenenden bos"


def test_module_entity_types_are_registered_in_their_module():
    for module in MODULES:
        for spec in module.entity_types:
            assert spec.type, f"{module.id}: bossuz entity tipi"


def test_study_topic_route_opens_the_exact_topic():
    study_topic = next(spec for spec in all_entity_types() if spec.type == "study_topic")
    assert study_topic.route == "/learning?focus={id}"


def test_learning_resource_route_opens_the_exact_resource():
    """Kaynak deep-link'i konu rotasina DUSMEZ: ayri `?resource=` tasir."""
    resource = next(spec for spec in all_entity_types() if spec.type == "learning_resource")
    assert resource.route == "/learning?resource={id}"


def test_every_logged_event_verb_is_registered():
    """Kodda cagrilan her `log_event(verb=...)` kayit defterinde bulunmali.

    Eksik verb, aktivite akisinda etiketsiz/anlamsiz satir demektir; sessizce
    eklenen yeni bir olay tipi fark edilmeden kalmasin diye bu test kilitler.
    """
    app_root = Path(__file__).resolve().parents[1] / "app"
    registered = set(all_event_verbs())
    used: dict[str, str] = {}
    for path in sorted(app_root.rglob("*.py")):
        relative = str(path.relative_to(app_root.parent))
        for verb in re.findall(r'verb="([a-z_.]+)"', path.read_text(encoding="utf-8")):
            used.setdefault(verb, relative)

    missing = sorted(verb for verb in used if verb not in registered)
    assert not missing, "kayit defterinde olmayan event verb'leri: " + ", ".join(
        f"{verb} ({used[verb]})" for verb in missing
    )


def test_frontend_routes_cover_entity_specs_and_search_flags():
    """Rota ve etiket yalnizca EntityTypeSpec'ten gelir; arama kumesi de oradan."""
    from app.core.search import searchable_types

    searchable = set(searchable_types())
    types = {spec.type for spec in all_entity_types()}
    assert searchable <= types
    # Rota/link hedefi olmayan destek tipleri global aramadan DISLANIR.
    assert "media_unit" not in searchable
    assert "note_folder" not in searchable
    # Kullaniciya gorunen ana tipler aranabilir kalir.
    assert {"opportunity", "career_story", "career_connection", "bookmark"} <= searchable


def test_opportunity_entity_routes_point_at_the_right_workspace():
    """Derin baglanti rotalari dogru sekmeyi acar: ?focus=, ?story=, ?connection=."""
    from app.core.registry import type_spec

    assert type_spec("opportunity").route == "/opportunities?focus={id}"
    assert type_spec("career_story").route == "/opportunities?story={id}"
    assert type_spec("career_connection").route == "/opportunities?connection={id}"
