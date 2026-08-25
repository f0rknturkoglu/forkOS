"""Kayit defteri sozlesmeleri (kural 13).

Her EntityTypeSpec.route frontend'de kayitli bir rota ile eslesmeli; tip->rota
bilgisi YALNIZCA EntityTypeSpec'te tutulur (frontend'de sabit yazilmaz).
"""

from __future__ import annotations

import re

from app.core.registry import all_entity_types
from app.modules import MODULES

# Frontend registerModule route'lari (src/modules/*/index.ts). Yeni modul
# ekleyen buraya frontend rotasini da ekler -- kayit defteri ile senkron kalir.
FRONTEND_ROUTES = {
    "/bookmarks", "/inbox", "/rss", "/todos", "/planner", "/today", "/",
    "/pomodoro", "/review/daily", "/review/weekly", "/opportunities", "/sources",
    "/study", "/learning", "/documents", "/calendar", "/media", "/media/collections", "/media/{id}",
    "/projects", "/finance", "/health", "/settings", "/activity", "/day",
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
