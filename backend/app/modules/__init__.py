"""Modul registry.

Yeni modul eklemek = modules/<ad>/ klasoru + buraya bir satir.
main.py'ye, search'e, worker'a DOKUNMA -- hepsi bu listeyi okur.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import APIRouter


@dataclass(frozen=True)
class ModuleSpec:
    id: str
    title: str
    router: APIRouter
    entity_types: list[str] = field(default_factory=list)
    event_verbs: list[str] = field(default_factory=list)


from app.modules.bookmark import MODULE as bookmark_module  # noqa: E402
from app.modules.habit import MODULE as habit_module  # noqa: E402
from app.modules.pomodoro import MODULE as pomodoro_module  # noqa: E402
from app.modules.review import MODULE as review_module  # noqa: E402
from app.modules.rss import MODULE as rss_module  # noqa: E402
from app.modules.todo import MODULE as todo_module  # noqa: E402

MODULES: list[ModuleSpec] = [
    bookmark_module,
    rss_module,
    todo_module,
    pomodoro_module,
    habit_module,
    review_module,
]
