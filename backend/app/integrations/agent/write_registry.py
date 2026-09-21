"""H1 yazma aksiyonlarinin MAKINE-OKUNUR kayit defteri.

Neden var: H1 MCP araclari 11 yazmayi nce gövdeyle kaydeder; H7 gibi baska bir
tuketici de AYNI eylemleri (ayni girdi modelleri, ayni canonical servisler)
kullanmak zorundadir. Aksiyon sozlugunu ikinci kez elle yazmak yerine burada
TEK yerde, H1'in gercek fonksiyonlari ve Pydantic modelleriyle tanimlanir.

Kilit nokta (§55): serbest `tool_name + arbitrary JSON` YOKTUR. Adimlar yalnizca
bu kapali kumeden secilebilir; yeni yetenek eklemek H1'e fonksiyon eklemektir.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.integrations.agent.write_models import (
    ApplicationTransitionIn,
    BookmarkCaptureIn,
    BookmarkUpdateIn,
    BrainCaptureIn,
    BrainSaveToEntityIn,
    OpportunityTransitionIn,
    ProjectUpdateIn,
    TodoCreateIn,
    TodoPlanIn,
    TodoUpdateIn,
)


class TodoCompleteIn(BaseModel):
    """`complete_todo` pozisyonel imza tasir; H7 icin ince zarf."""

    todo_id: str


@dataclass(frozen=True)
class WriteActionSpec:
    """Bir H1 yazma aksiyonunun sozlesmesi.

    `runner_name`, H1 modulundeki fonksiyon adidir. Cozumleme TEMBELDIR:
    modul importu sirasinda `agent.actions` cekilmez (aksi halde actions →
    modul registry → execution → registry dongusu olusur).
    """

    name: str
    tool: str
    model: type[BaseModel]
    runner_name: str
    #: Hedef kimligini tasiyan alan (freshness/target dogrulamasi icin).
    target_field: str | None = None
    #: Pozisyonel imzali aksiyonlar icin ince uyarlama gerekir (or. complete).
    positional: str | None = None
    #: Yan etki alani: `db` (tek islem, canonical servis commit eder) ya da
    #: `vault` (dosya sistemi; DB islemiyle AYNI atomik sinir DEGIL).
    side_effect_domain: str = "db"
    #: Kesinti sonrasi tekrar guvenligi: `safe` (yeni kayit degil, ayni
    #: girdiyle idempotent), `detectable` (mevcut durumdan anlasilabilir),
    #: `ambiguous` (sonuc belirsiz; MUTABAKAT gerekir).
    replay_safety: str = "detectable"


def runner_for(spec: WriteActionSpec) -> Callable[..., Awaitable[Any]]:
    """H1 fonksiyonunu TEMBEL cozer (tek yetki kaynagi: actions modulu)."""
    from app.integrations.agent import actions as actions_svc

    function = getattr(actions_svc, spec.runner_name, None)
    if function is None:
        raise ActionLookupError("UNKNOWN_ACTION", f"H1 aksiyonu bulunamadi: {spec.runner_name}")
    return function


async def run_action(session: Any, spec: WriteActionSpec, data: BaseModel) -> Any:
    """H1 aksiyonunu calistirir; pozisyonel imzalar burada uyarlanir."""
    function = runner_for(spec)
    if spec.positional:
        return await function(session, getattr(data, spec.positional))
    return await function(session, data)


class ActionLookupError(Exception):
    """Sinirli aksiyon cozumleme hatasi (H1 fonksiyonu bulunamadi)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


#: KAPALI aksiyon kumesi. Sirasi kanonik listeleme sirasidir.
WRITE_ACTIONS: tuple[WriteActionSpec, ...] = (
    WriteActionSpec("todo_create", "forkos_todo_create", TodoCreateIn, "create_todo"),
    WriteActionSpec("todo_update", "forkos_todo_update", TodoUpdateIn, "update_todo", "todo_id"),
    WriteActionSpec(
        "todo_complete",
        "forkos_todo_complete",
        TodoCompleteIn,
        "complete_todo",
        "todo_id",
        positional="todo_id",
    ),
    WriteActionSpec("todo_plan", "forkos_todo_plan", TodoPlanIn, "plan_todo", "todo_id"),
    WriteActionSpec(
        "project_update", "forkos_project_update", ProjectUpdateIn, "update_project", "project_id"
    ),
    WriteActionSpec(
        "opportunity_transition",
        "forkos_opportunity_transition",
        OpportunityTransitionIn,
        "transition_opportunity",
        "opportunity_id",
    ),
    WriteActionSpec(
        "application_transition",
        "forkos_application_transition",
        ApplicationTransitionIn,
        "transition_application",
        "opportunity_id",
    ),
    WriteActionSpec(
        "bookmark_capture", "forkos_bookmark_capture", BookmarkCaptureIn, "capture_bookmark"
    ),
    WriteActionSpec(
        "bookmark_update", "forkos_bookmark_update", BookmarkUpdateIn, "update_bookmark", "bookmark_id"
    ),
    # Vault yazmalari: kesintide sonuc BELIRSIZDIR (dosya sistemi atomik degil).
    WriteActionSpec(
        "brain_capture",
        "brain_capture",
        BrainCaptureIn,
        "capture_brain_note",
        side_effect_domain="vault",
        replay_safety="ambiguous",
    ),
    WriteActionSpec(
        "brain_save_to_entity",
        "brain_save_to_entity",
        BrainSaveToEntityIn,
        "save_to_entity_brain",
        "forkos_id",
        side_effect_domain="vault",
        replay_safety="ambiguous",
    ),
)

BY_NAME: dict[str, WriteActionSpec] = {spec.name: spec for spec in WRITE_ACTIONS}

#: H7 adimlarinda kabul edilen eylem adlari.
ACTION_NAMES: frozenset[str] = frozenset(BY_NAME)

#: Yan etki alanlari.
SIDE_EFFECT_DOMAINS: frozenset[str] = frozenset({"db", "vault"})

#: Metin argumanlari icin ust sinir (sınırsız gövde tasima yok, §64).
MAX_TEXT_ARGUMENT = 20000


def target_of(spec: WriteActionSpec, data: BaseModel) -> str | None:
    """Adimin hedef kimligi (yoksa None: or. yeni kayit olusturma)."""
    if spec.target_field is None:
        return None
    value = getattr(data, spec.target_field, None)
    if value is None:
        return None
    try:
        uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return str(value)
    return str(value)
