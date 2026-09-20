"""H3 — kanıt getirme davranışı (kabul senaryoları).

Bu dosya `obsidian/evidence.py` primitiflerini DEĞİL, orkestrasyonu ölçer:
hangi kanal çalıştı, kanıt nasıl bağlandı, sınırlar dürüst mü ve hiçbir şey
değişti mi.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import Entity, Event, Link
from app.db import SessionLocal
from app.integrations.agent import evidence as ev
from app.integrations.agent.evidence_models import MAX_EVIDENCE_LIMIT, MAX_TOTAL_EVIDENCE_CHARS
from app.integrations.obsidian.evidence import MAX_VAULT_SCAN_FILES
from app.integrations.obsidian.service import refresh_vault_index
from app.modules.project.models import Project
from app.modules.todo.models import Todo
from tests.agent_test_utils import (
    capture_db_content_fingerprint,
    capture_vault_fingerprint,
    forbid_outbound_network,  # noqa: F401  (autouse: H3 dış ağ çağrısı yapmaz)
    legacy_notes_counts,
    table_counts,
)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "H3Vault"
    path.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "H3Vault")
    return path


@pytest.fixture(autouse=True)
def reset_vault_index() -> AsyncIterator[None]:
    """Global yönetilen kasa indeksi testler arasında sızmasın.

    H1/H2 testleriyle AYNI desen: indeks süreç ömürlü bir tekildir; testler
    kendi geçici kasalarını kurduğu için her testte temizlenir.
    """
    from app.integrations.obsidian.service import vault_index

    def clear() -> None:
        vault_index._items.clear()
        vault_index._conflicts.clear()
        vault_index._invalid_files.clear()
        vault_index._last_scanned = None
        vault_index._last_status = None
        vault_index._last_root = None

    clear()
    yield
    clear()


# ---------------------------------------------------------------------------
# Kurulum yardımcıları
# ---------------------------------------------------------------------------


async def _entity(session: AsyncSession, *, type: str, title: str, search_text: str = "") -> Entity:
    entity = Entity(type=type, title=title, search_text=search_text)
    session.add(entity)
    await session.flush()
    return entity


async def _project(session: AsyncSession, *, title: str, stack: list[str] | None = None, **kwargs) -> Entity:
    entity = await _entity(session, type="project", title=title, search_text=" ".join(stack or []))
    session.add(
        Project(
            id=entity.id,
            status=kwargs.get("status", "active"),
            next_action=kwargs.get("next_action", ""),
            stack=stack or [],
            github_repo=kwargs.get("github_repo"),
        )
    )
    await session.flush()
    return entity


async def _todo(session: AsyncSession, *, title: str, project: Entity | None = None) -> Entity:
    entity = await _entity(session, type="todo", title=title)
    session.add(Todo(id=entity.id, status="open", priority=2))
    if project is not None:
        session.add(Link(from_id=entity.id, to_id=project.id, relation="belongs_to"))
    await session.flush()
    return entity


async def _link(session: AsyncSession, source: Entity, target: Entity, relation: str = "related") -> None:
    session.add(Link(from_id=source.id, to_id=target.id, relation=relation))
    await session.flush()


async def _event(
    session: AsyncSession,
    target: Entity,
    *,
    verb: str,
    payload: dict | None = None,
    occurred_at: datetime | None = None,
) -> Event:
    event = Event(
        entity_id=target.id,
        entity_type=target.type,
        verb=verb,
        payload=payload or {},
        occurred_at=occurred_at or datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
    )
    session.add(event)
    await session.flush()
    return event


def _note(
    vault: Path,
    rel_path: str,
    body: str,
    *,
    forkos_id: str | None = None,
    forkos_type: str | None = None,
    updated_at: str | None = None,
) -> Path:
    target = vault / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    header = ["---"]
    if forkos_id:
        header.append(f"forkos_id: {forkos_id}")
    if forkos_type:
        header.append(f"forkos_type: {forkos_type}")
    if updated_at:
        header.append(f"forkos_updated_at: {updated_at}")
    header.append("---")
    target.write_text("\n".join(header) + "\n" + body, encoding="utf-8")
    return target


def _vault_items(bundle: ev.EvidenceBundle) -> list:
    return [item for item in bundle.evidence if item.source_type == "vault"]


def _trace(bundle: ev.EvidenceBundle, stage: str):
    return next(step for step in bundle.retrieval_trace if step.stage == stage)


# ---------------------------------------------------------------------------
# A — açık proje kanıtı
# ---------------------------------------------------------------------------


async def test_explicit_project_evidence_covers_all_channels(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await _project(
        db_session,
        title="forkjob",
        stack=["Rust", "PostgreSQL"],
        next_action="Mimariyi yaz",
        github_repo="f0rknturkoglu/forkjob",
    )
    todo = await _todo(db_session, title="Rust mimarisini yaz", project=project)
    project_event = await _event(db_session, project, verb="project.updated", payload={"stack": ["Rust"]})
    todo_event = await _event(db_session, todo, verb="todo.created", payload={"status": "open"})
    _note(
        vault,
        "20 Projects/forkjob.md",
        "# forkjob\n\nGenel bakış.\n\n## Teknoloji Kararı\n\nRust seçildi; bellek güvenliği.\n",
        forkos_id=str(project.id),
        forkos_type="project",
        updated_at="2026-09-01T10:00:00+03:00",
    )
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(
        db_session, query="Rust mimari kararı", entity_id=str(project.id), scope="all"
    )

    assert bundle.entity_seed == str(project.id)
    assert bundle.sources_used == ["forkos", "f0rknbrain"]
    assert bundle.truncated is False

    seed_item = bundle.evidence[0]
    assert seed_item.evidence_id == f"entity:{project.id}"
    assert seed_item.source_type == "entity"
    assert "stack: [Rust, PostgreSQL]" in seed_item.excerpt
    assert seed_item.relation_path == []

    knowledge = next(item for item in _vault_items(bundle) if item.locator.forkos_id == str(project.id))
    assert knowledge.locator.heading == "Teknoloji Kararı"
    assert knowledge.updated_at == "2026-09-01T10:00:00+03:00"
    assert knowledge.relation_path[0].kind == "knowledge_pointer"
    assert knowledge.relation_path[0].relation == "knowledge_note"

    seed_events = [item for item in bundle.evidence if item.source_type == "event"]
    assert {item.source_id for item in seed_events} == {str(project_event.id), str(todo_event.id)}
    assert all(item.occurred_at for item in seed_events)

    neighbor = next(item for item in bundle.evidence if item.source_id == str(todo.id))
    assert neighbor.relation_path[0].kind == "entity_link"
    assert neighbor.relation_path[0].relation == "belongs_to"


async def test_evidence_order_follows_provenance_priority(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await _project(db_session, title="forkjob", stack=["Rust"])
    await _todo(db_session, title="Rust görevi", project=project)
    await _event(db_session, project, verb="project.updated", payload={"note": "Rust"})
    _note(vault, "20 Projects/forkjob.md", "# forkjob\n\n## Karar\n\nRust.\n", forkos_id=str(project.id), forkos_type="project")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust", entity_id=str(project.id))

    kinds = [item.source_type for item in bundle.evidence]
    assert kinds[0] == "entity"
    assert kinds[1] == "vault"
    assert "event" in kinds
    # Doğrudan çekirdek kanıtı, genel leksikal yedeğin önünde gelir (§47).
    assert kinds.index("vault") < kinds.index("entity", 1)


# ---------------------------------------------------------------------------
# B — aday tahmini yok
# ---------------------------------------------------------------------------


async def test_query_only_returns_candidates_without_expanding(
    db_session: AsyncSession, vault: Path
) -> None:
    first = await _project(db_session, title="Rust CLI", stack=["Rust"])
    second = await _project(db_session, title="Rust Backend", stack=["Rust"])
    linked_todo = await _todo(db_session, title="Rust bağlantılı görev", project=first)

    bundle = await ev.retrieve_evidence(db_session, query="Rust", scope="operational")

    candidate_ids = {ref.id for ref in bundle.resolved_entities}
    assert {str(first.id), str(second.id)} <= candidate_ids
    assert all(ref.resolution == "lexical_candidate" for ref in bundle.resolved_entities)
    assert all(ref.expanded is False for ref in bundle.resolved_entities)
    assert bundle.entity_seed is None
    # Görev yalnızca LEKSİKAL ADAY olarak gelebilir; grafikten gelmiş gibi
    # bir köken zinciri TAŞIMAZ (§18).
    assert all(not item.relation_path for item in bundle.evidence)
    assert all(
        item.relation_path == []
        for item in bundle.evidence
        if item.source_id == str(linked_todo.id)
    )
    assert bundle.recovery_hint == "Provide entity_id to traverse a specific operational entity."
    assert _trace(bundle, "graph").accepted == 0
    assert _trace(bundle, "events").considered == 0


async def test_query_only_knowledge_mode_does_not_crawl_links(
    db_session: AsyncSession, vault: Path
) -> None:
    _note(vault, "30 Knowledge/Rust.md", "# Rust\n\nRust bellek güvenliği.\n[[Python]]\n")
    _note(vault, "30 Knowledge/Python.md", "# Python\n\nRust ile karşılaştırma.\n")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust", scope="knowledge")

    paths = {item.locator.relative_path for item in bundle.evidence}
    assert "30 Knowledge/Python.md" in paths  # leksikal eşleşme
    assert all(hop.kind != "wikilink" for item in bundle.evidence for hop in item.relation_path)
    assert bundle.sources_used == ["f0rknbrain"]


# ---------------------------------------------------------------------------
# C/X — yönetilen not, başlık ve TAM satır numaraları
# ---------------------------------------------------------------------------


async def test_managed_note_heading_and_exact_line_locator(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await _project(db_session, title="forkjob")
    path = _note(
        vault,
        "20 Projects/forkjob.md",
        "# forkjob\n\nGiriş.\n\n## Architecture Decision\n\nRust was chosen for memory safety.\n\nDevam.\n",
        forkos_id=str(project.id),
        forkos_type="project",
    )
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust memory safety", entity_id=str(project.id))
    item = _vault_items(bundle)[0]

    assert item.locator.forkos_id == str(project.id)
    assert item.locator.relative_path == "20 Projects/forkjob.md"
    assert item.locator.heading == "Architecture Decision"
    assert item.locator.line_start is not None and item.locator.line_end is not None

    lines = path.read_text(encoding="utf-8").split("\n")
    assert item.excerpt == "\n".join(lines[item.locator.line_start - 1 : item.locator.line_end])
    assert "Rust was chosen" in item.excerpt
    assert item.truncated is False


# ---------------------------------------------------------------------------
# D — kasa çakışması
# ---------------------------------------------------------------------------


async def test_vault_conflict_is_reported_without_guessing(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await _project(db_session, title="conflicted", stack=["Rust"])
    shared_id = str(project.id)
    _note(vault, "20 Projects/a.md", "# A\n\nRust notu.\n", forkos_id=shared_id, forkos_type="project")
    _note(vault, "20 Projects/b.md", "# B\n\nRust notu.\n", forkos_id=shared_id, forkos_type="project")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust", entity_id=shared_id, scope="all")

    assert any("VAULT_CONFLICT" in warning for warning in bundle.warnings)
    # Operasyonel kanıt yine gelir (§86).
    assert any(item.evidence_id == f"entity:{project.id}" for item in bundle.evidence)
    # Çakışan kimlik hiçbir kasa kanıtında KİMLİK olarak sunulmaz ve
    # "yönetilen not" kökeni iddia edilmez.
    assert all(item.locator.forkos_id is None for item in _vault_items(bundle))
    assert not any(
        hop.kind == "knowledge_pointer" for item in _vault_items(bundle) for hop in item.relation_path
    )


# ---------------------------------------------------------------------------
# E/F/G/H — wikilink ve backlink kanıtı
# ---------------------------------------------------------------------------


async def test_direct_wikilink_evidence_keeps_provenance_path(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await _project(db_session, title="forkjob")
    _note(
        vault,
        "20 Projects/forkjob.md",
        "# forkjob\n\n## Kararlar\n\nRust kararı verildi.\n\n[[Rust]] notuna bak.\n",
        forkos_id=str(project.id),
        forkos_type="project",
    )
    _note(vault, "30 Knowledge/Rust.md", "# Rust\n\nRust bellek güvenliği sağlar.\n")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust kararı", entity_id=str(project.id))
    linked = next(item for item in _vault_items(bundle) if item.locator.relative_path == "30 Knowledge/Rust.md")

    assert [hop.kind for hop in linked.relation_path] == ["knowledge_pointer", "wikilink"]
    assert linked.relation_path[-1].from_ref == "vault:20 Projects/forkjob.md"
    assert "direct wikilink from '20 Projects/forkjob.md'" in linked.retrieval_reason
    assert linked.locator.heading == "Rust"


async def test_ambiguous_wikilink_is_never_guessed(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await _project(db_session, title="forkjob")
    _note(
        vault,
        "20 Projects/forkjob.md",
        "# forkjob\n\nRust kararı.\n\n[[Rust]]\n",
        forkos_id=str(project.id),
        forkos_type="project",
    )
    _note(vault, "30 Knowledge/Rust.md", "# Rust\n\nRust notu.\n")
    _note(vault, "40 Learning/Rust.md", "# Rust\n\nRust dersi.\n")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust kararı", entity_id=str(project.id))

    assert any("ambiguity" in warning for warning in bundle.warnings)
    assert not any(
        hop.kind == "wikilink" for item in bundle.evidence for hop in item.relation_path
    )


async def test_backlink_evidence_keeps_backlink_path(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await _project(db_session, title="forkjob")
    _note(
        vault,
        "20 Projects/forkjob.md",
        "# forkjob\n\nRust kararı verildi.\n",
        forkos_id=str(project.id),
        forkos_type="project",
    )
    _note(vault, "50 Career/decision.md", "# Karar\n\nRust seçimi gerekçesi.\n\n[[forkjob]]\n")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust kararı", entity_id=str(project.id))
    backlink = next(item for item in _vault_items(bundle) if item.locator.relative_path == "50 Career/decision.md")

    assert [hop.kind for hop in backlink.relation_path] == ["knowledge_pointer", "backlink"]
    assert backlink.relation_path[-1].relation == "backlink"
    assert "links to '20 Projects/forkjob.md'" in backlink.retrieval_reason


async def test_irrelevant_linked_note_is_not_evidence(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await _project(db_session, title="forkjob")
    _note(
        vault,
        "20 Projects/forkjob.md",
        "# forkjob\n\nRust kararı verildi.\n\n[[Alakasız]]\n",
        forkos_id=str(project.id),
        forkos_type="project",
    )
    _note(vault, "30 Knowledge/Alakasız.md", "# Alakasız\n\nBambu yetiştiriciliği üzerine notlar.\n")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust kararı", entity_id=str(project.id))

    paths = {item.locator.relative_path for item in _vault_items(bundle)}
    assert "30 Knowledge/Alakasız.md" not in paths
    assert _trace(bundle, "wikilinks").considered == 1


# ---------------------------------------------------------------------------
# I/J — olaylar: zaman filtresi ve tarih/şimdi ayrımı
# ---------------------------------------------------------------------------


async def test_event_time_filter_selects_only_the_window(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await _project(db_session, title="timebox")
    early = await _event(
        db_session, project, verb="project.updated", occurred_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC)
    )
    inside = await _event(
        db_session, project, verb="project.updated", occurred_at=datetime(2026, 9, 10, 9, 0, tzinfo=UTC)
    )
    late = await _event(
        db_session, project, verb="project.updated", occurred_at=datetime(2026, 9, 20, 9, 0, tzinfo=UTC)
    )

    bundle = await ev.retrieve_evidence(
        db_session,
        query="project",
        entity_id=str(project.id),
        scope="operational",
        since="2026-09-05T00:00:00Z",
        until="2026-09-15T00:00:00Z",
    )

    event_ids = {item.source_id for item in bundle.evidence if item.source_type == "event"}
    assert event_ids == {str(inside.id)}
    assert str(early.id) not in event_ids and str(late.id) not in event_ids
    assert "time window" in _trace(bundle, "events").description


async def test_current_state_and_history_stay_separate(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await _project(db_session, title="forkjob", status="active", stack=["Rust"])
    await _event(db_session, project, verb="project.paused", payload={"status": "paused"})
    _note(
        vault,
        "20 Projects/forkjob.md",
        "# forkjob\n\n## Teknoloji\n\nPrototype will use Python.\n",
        forkos_id=str(project.id),
        forkos_type="project",
    )
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Python Rust", entity_id=str(project.id))

    current = next(item for item in bundle.evidence if item.source_type == "entity" and item.source_id == str(project.id))
    history = next(item for item in bundle.evidence if item.source_type == "event")
    note = next(item for item in _vault_items(bundle) if item.locator.forkos_id == str(project.id))

    assert "status: active" in current.excerpt  # güncel gerçek yeniden yazılmaz
    assert "project.paused" in history.excerpt
    assert "Prototype will use Python" in note.excerpt
    assert current.evidence_id != history.evidence_id != note.evidence_id


# ---------------------------------------------------------------------------
# K — sıcak hafıza kanıt değildir
# ---------------------------------------------------------------------------


async def test_hot_memory_is_never_evidence(db_session: AsyncSession, vault: Path) -> None:
    phrase = "kuantum harmanlayici"
    _note(vault, "30 Knowledge/Not.md", f"# Not\n\n{phrase} üzerine çalışma.\n")
    _note(vault, "90 Agent/Memory/abc.md", f"# Tercih\n\n{phrase} sevilir.\n")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query=phrase, scope="knowledge")

    paths = {item.locator.relative_path for item in bundle.evidence}
    assert "30 Knowledge/Not.md" in paths
    assert not any(path and path.startswith("90 Agent") for path in paths)


# ---------------------------------------------------------------------------
# L/M/N — kapsam ve bozulmuş modlar
# ---------------------------------------------------------------------------


async def test_operational_scope_touches_no_vault(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = await _project(db_session, title="novault", stack=["Rust"])
    await _todo(db_session, title="Rust görevi", project=project)

    def _boom(*args, **kwargs):
        raise AssertionError("vault was touched")

    monkeypatch.setattr(ev, "vault_context", _boom)
    monkeypatch.setattr(ev, "resolve_managed_item", _boom)
    monkeypatch.setattr("app.integrations.obsidian.evidence.scan_evidence_notes", _boom)
    monkeypatch.setattr("app.integrations.obsidian.evidence.read_note_lines", _boom)

    # Kontrol: yama gerçekten etkin.
    with pytest.raises(AssertionError, match="vault was touched"):
        await ev.retrieve_evidence(db_session, query="Rust", entity_id=str(project.id), scope="all")

    bundle = await ev.retrieve_evidence(
        db_session, query="Rust", entity_id=str(project.id), scope="operational"
    )
    assert bundle.sources_used == ["forkos"]
    assert bundle.evidence


async def test_vault_unavailable_degrades_in_mixed_scope(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = await _project(db_session, title="degraded", stack=["Rust"])
    monkeypatch.setattr(settings, "obsidian_vault_path", str(vault / "does-not-exist"))

    bundle = await ev.retrieve_evidence(db_session, query="Rust", entity_id=str(project.id), scope="all")

    assert any("VAULT_UNAVAILABLE" in warning for warning in bundle.warnings)
    assert bundle.sources_used == ["forkos"]
    assert any(item.evidence_id == f"entity:{project.id}" for item in bundle.evidence)


async def test_knowledge_only_scope_fails_cleanly_without_vault(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "obsidian_vault_path", str(vault / "does-not-exist"))

    with pytest.raises(ev.EvidenceError, match="VAULT_UNAVAILABLE"):
        await ev.retrieve_evidence(db_session, query="Rust", scope="knowledge")


async def test_knowledge_scope_emits_no_operational_evidence(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await _project(db_session, title="forkjob", stack=["Rust"])
    await _event(db_session, project, verb="project.updated", payload={"note": "Rust"})
    _note(
        vault,
        "20 Projects/forkjob.md",
        "# forkjob\n\n## Karar\n\nRust seçildi.\n",
        forkos_id=str(project.id),
        forkos_type="project",
    )
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust", entity_id=str(project.id), scope="knowledge")

    assert bundle.sources_used == ["f0rknbrain"]
    assert all(item.source_type == "vault" for item in bundle.evidence)
    assert all(item.locator.entity_id is None for item in bundle.evidence)


# ---------------------------------------------------------------------------
# O/P — döngü ve patlama
# ---------------------------------------------------------------------------


async def test_cycles_terminate_and_visit_each_node_once(
    db_session: AsyncSession, vault: Path
) -> None:
    first = await _entity(db_session, type="note-free", title="Cycle A")
    second = await _entity(db_session, type="note-free", title="Cycle B")
    third = await _entity(db_session, type="note-free", title="Cycle C")
    await _link(db_session, first, second)
    await _link(db_session, second, third)
    await _link(db_session, third, first)

    bundle = await ev.retrieve_evidence(
        db_session, query="Cycle", entity_id=str(first.id), scope="operational", max_depth=2
    )

    entity_ids = [item.evidence_id for item in bundle.evidence if item.source_type == "entity"]
    assert len(entity_ids) == len(set(entity_ids))
    assert {str(second.id), str(third.id)} <= {item.source_id for item in bundle.evidence}
    assert _trace(bundle, "graph").accepted == 2


async def test_graph_explosion_is_capped_and_reported(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await _project(db_session, title="dense")
    for index in range(30):
        await _todo(db_session, title=f"Dense {index}", project=project)

    bundle = await ev.retrieve_evidence(
        db_session, query="Dense", entity_id=str(project.id), scope="operational", max_depth=1
    )

    graph_step = _trace(bundle, "graph")
    assert graph_step.accepted <= 24  # MAX_GRAPH_NODES - 1 (çekirdek hariç)
    assert graph_step.truncated is True
    assert bundle.truncated is True


# ---------------------------------------------------------------------------
# Q/R — bütçe ve determinizm
# ---------------------------------------------------------------------------


async def test_evidence_budget_is_honest(db_session: AsyncSession, vault: Path) -> None:
    project = await _project(db_session, title="budget", stack=["Rust"])
    for index in range(20):
        _note(
            vault,
            f"30 Knowledge/Rust-{index:02d}.md",
            f"# Rust {index}\n\nRust mimari kararı. " + ("dolgu " * 400),
        )
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(
        db_session, query="Rust mimari", entity_id=str(project.id), limit=MAX_EVIDENCE_LIMIT
    )

    assert len(bundle.evidence) <= MAX_EVIDENCE_LIMIT
    assert sum(len(item.excerpt) for item in bundle.evidence) <= MAX_TOTAL_EVIDENCE_CHARS
    assert bundle.truncated is True
    assert bundle.omitted_total > 0
    assert _trace(bundle, "budget").truncated is True


async def test_repeated_calls_are_deterministic(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await _project(db_session, title="stable", stack=["Rust"])
    await _todo(db_session, title="Stable görev", project=project)
    await _event(db_session, project, verb="project.updated", payload={"note": "Rust"})
    _note(
        vault,
        "20 Projects/stable.md",
        "# stable\n\n## Karar\n\nRust.\n\n[[Rust]]\n",
        forkos_id=str(project.id),
        forkos_type="project",
    )
    _note(vault, "30 Knowledge/Rust.md", "# Rust\n\nRust notu.\n")
    refresh_vault_index()

    first = await ev.retrieve_evidence(db_session, query="Rust kararı", entity_id=str(project.id))
    second = await ev.retrieve_evidence(db_session, query="Rust kararı", entity_id=str(project.id))

    assert first.model_dump() == second.model_dump()


# ---------------------------------------------------------------------------
# Değişmezlik (§165-§169)
# ---------------------------------------------------------------------------


async def test_retrieval_creates_no_rows_and_touches_no_files(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await _project(db_session, title="immutable", stack=["Rust"])
    await _todo(db_session, title="Immutable görev", project=project)
    await _event(db_session, project, verb="project.updated", payload={"note": "Rust"})
    _note(
        vault,
        "20 Projects/immutable.md",
        "# immutable\n\nRust kararı.\n\n[[Rust]]\n",
        forkos_id=str(project.id),
        forkos_type="project",
    )
    _note(vault, "30 Knowledge/Rust.md", "# Rust\n\nRust notu.\n")
    refresh_vault_index()

    db_before = await capture_db_content_fingerprint(db_session)
    vault_before = capture_vault_fingerprint(vault)
    counts_before = await table_counts(db_session)
    legacy_before = await legacy_notes_counts(db_session)

    await ev.retrieve_evidence(db_session, query="Rust kararı", entity_id=str(project.id), scope="all")
    await ev.retrieve_evidence(db_session, query="Rust", scope="knowledge")
    await ev.retrieve_evidence(db_session, query="Rust", scope="operational")

    assert await capture_db_content_fingerprint(db_session) == db_before
    assert capture_vault_fingerprint(vault) == vault_before
    assert await table_counts(db_session) == counts_before
    assert await legacy_notes_counts(db_session) == legacy_before

    events = (await db_session.execute(select(func.count(Event.id)))).scalar_one()
    assert events == 1  # yalnızca kurulumda yazılan olay


# ---------------------------------------------------------------------------
# §53 — arşivlenmiş kayıtlar dürüstçe temsil edilir
# ---------------------------------------------------------------------------


async def test_archived_neighbor_is_not_expanded_but_archived_seed_is_honest(
    db_session: AsyncSession, vault: Path
) -> None:
    from app.core.entity import archive_entity

    project = await _project(db_session, title="archive-seed", stack=["Rust"])
    archived = await _todo(db_session, title="Arşiv görev", project=project)
    await archive_entity(db_session, archived.id)
    await db_session.commit()

    bundle = await ev.retrieve_evidence(
        db_session, query="Arşiv", entity_id=str(project.id), scope="operational"
    )
    assert str(archived.id) not in {item.source_id for item in bundle.evidence}

    seeded = await ev.retrieve_evidence(
        db_session, query="arşiv görev", entity_id=str(archived.id), scope="operational"
    )
    seed_item = seeded.evidence[0]
    assert "archived_at" in seed_item.excerpt
    assert "(archived)" in seed_item.excerpt


# ---------------------------------------------------------------------------
# §78/§80 — tarama sınırları kanıta yansır
# ---------------------------------------------------------------------------


async def test_vault_scan_cap_is_reported_as_truncation(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for index in range(4):
        _note(vault, f"30 Knowledge/n-{index}.md", f"# Rust {index}\n\nRust notu.\n")
    monkeypatch.setattr("app.integrations.obsidian.evidence.MAX_VAULT_SCAN_FILES", 2)

    bundle = await ev.retrieve_evidence(db_session, query="Rust", scope="knowledge")

    assert bundle.truncated is True
    assert any("cap" in warning for warning in bundle.warnings)
    assert _trace(bundle, "vault_lexical").truncated is True
    assert MAX_VAULT_SCAN_FILES == 500


async def test_trace_stage_structure_is_scope_independent(
    db_session: AsyncSession, vault: Path
) -> None:
    """İz yapısı kapsama göre DEĞİŞMEZ (§130): aynı aşamalar, aynı sırada."""
    project = await _project(db_session, title="trace-owner", stack=["Rust"])
    expected = [
        "entity_resolution",
        "graph",
        "events",
        "managed_knowledge",
        "wikilinks",
        "backlinks",
        "vault_lexical",
        "budget",
    ]

    for kwargs in (
        {"scope": "operational"},
        {"scope": "operational", "entity_id": str(project.id)},
        {"scope": "knowledge"},
        {"scope": "knowledge", "entity_id": str(project.id)},
        {"scope": "all", "entity_id": str(project.id)},
    ):
        bundle = await ev.retrieve_evidence(db_session, query="Rust", **kwargs)  # type: ignore[arg-type]
        assert [step.stage for step in bundle.retrieval_trace] == expected


async def test_vault_note_cap_is_reported_as_truncation(
    db_session: AsyncSession, vault: Path
) -> None:
    """Kanal bir sınırla kesildiyse paket bunu SAKLAMAZ (§108/§216)."""
    from app.integrations.agent.evidence_models import MAX_VAULT_NOTES_CONSIDERED

    for index in range(20):
        _note(vault, f"30 Knowledge/R-{index:02d}.md", f"# Rust {index}\n\nRust notu.\n")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust", scope="knowledge", limit=15)

    assert len(bundle.evidence) <= MAX_VAULT_NOTES_CONSIDERED
    step = _trace(bundle, "vault_lexical")
    assert step.considered > step.accepted
    assert step.truncated is True
    assert bundle.truncated is True
