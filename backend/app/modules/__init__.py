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
from app.modules.calendar import MODULE as calendar_module  # noqa: E402
from app.modules.document import MODULE as document_module  # noqa: E402
from app.modules.finance import MODULE as finance_module  # noqa: E402
from app.modules.habit import MODULE as habit_module  # noqa: E402
from app.modules.learning import MODULE as learning_module  # noqa: E402
from app.modules.media import MODULE as media_module  # noqa: E402
from app.modules.opportunity import MODULE as opportunity_module  # noqa: E402
from app.modules.pomodoro import MODULE as pomodoro_module  # noqa: E402
from app.modules.project import MODULE as project_module  # noqa: E402
from app.modules.review import MODULE as review_module  # noqa: E402
from app.modules.rss import MODULE as rss_module  # noqa: E402
from app.modules.study import MODULE as study_module  # noqa: E402
from app.modules.system import MODULE as system_module  # noqa: E402
from app.modules.todo import MODULE as todo_module  # noqa: E402
from app.modules.today import MODULE as today_module  # noqa: E402

MODULES: list[ModuleSpec] = [
    bookmark_module,
    rss_module,
    todo_module,
    today_module,
    pomodoro_module,
    habit_module,
    review_module,
    opportunity_module,
    study_module,
    learning_module,
    document_module,
    calendar_module,
    media_module,
    project_module,
    finance_module,
    system_module,
]
