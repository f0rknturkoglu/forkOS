"""Modul registry.

Yeni modul eklemek = modules/<ad>/ klasoru + buraya bir satir.
main.py'ye, search'e, worker'a DOKUNMA -- hepsi bu listeyi okur.

Entity tipi, etiketi ve rotasi YALNIZCA EntityTypeSpec'te tanimlanir
(AGENTS.md kural 13). Frontend'de tip->rota sabiti yazilmaz.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from fastapi import APIRouter


@dataclass(frozen=True)
class EntityTypeSpec:
    """Aranabilir/linklenebilir entity tipinin TEK kayit defteri girdisi.

    route, frontend hash rotasidir; "{id}" varsa entity id'siyle degisir
    (ornek: "/bookmarks?focus={id}"). Rota olmayan tip listeye yonlendirilir.
    """

    type: str
    label: str
    label_plural: str
    route: str
    icon: str
    searchable: bool = True
    linkable: bool = True


@dataclass(frozen=True)
class DeadlineRow:
    entity_id: object
    type: str
    title: str
    due_at: object
    module: str
    sub_kind: str | None = None
    priority: int = 2


@dataclass(frozen=True)
class ModuleSpec:
    id: str
    title: str
    router: APIRouter
    entity_types: list[EntityTypeSpec] = field(default_factory=list)
    event_verbs: list[str] = field(default_factory=list)
    #: Son tarih ureten modul istege bagli saglayici verir (kural 16).
    #: deadline_v gibi elle SQL gorunumu YAZILMAZ -- /api/deadlines bunu toplar.
    deadline_provider: Callable[..., Awaitable[list[DeadlineRow]]] | None = None


from app.modules.bookmark import MODULE as bookmark_module  # noqa: E402
from app.modules.calendar import MODULE as calendar_module  # noqa: E402
from app.modules.document import MODULE as document_module  # noqa: E402
from app.modules.finance import MODULE as finance_module  # noqa: E402
from app.modules.flashcard import MODULE as flashcard_module  # noqa: E402
from app.modules.learning import MODULE as learning_module  # noqa: E402
from app.modules.media import MODULE as media_module  # noqa: E402
from app.modules.note import MODULE as note_module  # noqa: E402
from app.modules.opportunity import MODULE as opportunity_module  # noqa: E402
from app.modules.pomodoro import MODULE as pomodoro_module  # noqa: E402
from app.modules.proactivity import MODULE as proactivity_module  # noqa: E402
from app.modules.project import MODULE as project_module  # noqa: E402
from app.modules.review import MODULE as review_module  # noqa: E402
from app.modules.rss import MODULE as rss_module  # noqa: E402
from app.modules.statistics import MODULE as statistics_module  # noqa: E402
from app.modules.system import MODULE as system_module  # noqa: E402
from app.modules.today import MODULE as today_module  # noqa: E402
from app.modules.todo import MODULE as todo_module  # noqa: E402

MODULES: list[ModuleSpec] = [
    bookmark_module,
    rss_module,
    flashcard_module,
    todo_module,
    today_module,
    pomodoro_module,
    proactivity_module,
    review_module,
    opportunity_module,
    learning_module,
    document_module,
    calendar_module,
    media_module,
    note_module,
    project_module,
    finance_module,
    statistics_module,
    system_module,
]
