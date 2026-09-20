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
    assert_continuous_path,
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


# ---------------------------------------------------------------------------
# H3.1 — Link yönü (kanonik anlam ASLA ters çevrilmez)
# ---------------------------------------------------------------------------


async def test_incoming_link_preserves_canonical_relation_and_direction(
    db_session: AsyncSession, vault: Path
) -> None:
    """§125: `Todo --belongs_to--> Project`, çekirdek Project → direction=incoming."""
    project = await _project(db_session, title="direction-in")
    todo = await _todo(db_session, title="Yön görevi", project=project)

    bundle = await ev.retrieve_evidence(
        db_session, query="Yön", entity_id=str(project.id), scope="operational"
    )
    item = next(entry for entry in bundle.evidence if entry.source_id == str(todo.id))
    hop = item.relation_path[0]

    assert hop.kind == "entity_link"
    assert hop.relation == "belongs_to"  # kanonik ad korunur
    assert hop.direction == "incoming"  # to_id → from_id yönünde geçildi
    assert hop.from_ref == f"entity:{project.id}"
    assert hop.to_ref == f"entity:{todo.id}"


async def test_outgoing_link_preserves_canonical_relation_and_direction(
    db_session: AsyncSession, vault: Path
) -> None:
    """§126: `Project --references--> Repo`, çekirdek Project → direction=outgoing."""
    project = await _project(db_session, title="direction-out")
    repo = await _entity(db_session, type="source", title="Repo kaydı")
    await _link(db_session, project, repo, "references")

    bundle = await ev.retrieve_evidence(
        db_session, query="Repo", entity_id=str(project.id), scope="operational"
    )
    item = next(entry for entry in bundle.evidence if entry.source_id == str(repo.id))
    hop = item.relation_path[0]

    assert hop.relation == "references"
    assert hop.direction == "outgoing"
    assert hop.from_ref == f"entity:{project.id}"
    assert hop.to_ref == f"entity:{repo.id}"


async def test_mixed_direction_depth_two_relation_path(
    db_session: AsyncSession, vault: Path
) -> None:
    """§12: A --references--> B ve C --belongs_to--> B; A'dan C'ye yol iki yönlü."""
    a = await _project(db_session, title="mixed-a")
    b = await _entity(db_session, type="source", title="mixed-b")
    c = await _entity(db_session, type="todo", title="mixed-c")
    await _link(db_session, a, b, "references")
    await _link(db_session, c, b, "belongs_to")

    bundle = await ev.retrieve_evidence(
        db_session, query="mixed", entity_id=str(a.id), scope="operational", max_depth=2
    )
    item = next(entry for entry in bundle.evidence if entry.source_id == str(c.id))

    assert [(hop.relation, hop.direction) for hop in item.relation_path] == [
        ("references", "outgoing"),
        ("belongs_to", "incoming"),
    ]
    assert item.relation_path[0].to_ref == item.relation_path[1].from_ref == f"entity:{b.id}"


async def test_non_entity_hops_carry_no_direction(
    db_session: AsyncSession, vault: Path
) -> None:
    """§73: knowledge_pointer / wikilink / backlink yön taşımaz."""
    project = await _project(db_session, title="nohop-dir")
    _note(
        vault,
        "20 Projects/nohop-dir.md",
        "# nohop-dir\n\n## Karar\n\nRust kararı.\n\n[[Rust]]\n",
        forkos_id=str(project.id),
        forkos_type="project",
    )
    _note(vault, "30 Knowledge/Rust.md", "# Rust\n\nRust notu.\n")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(
        db_session, query="Rust kararı", entity_id=str(project.id), scope="knowledge"
    )
    hops = [hop for item in bundle.evidence for hop in item.relation_path]
    assert hops
    assert all(hop.direction is None for hop in hops if hop.kind != "entity_link")
    assert all(hop.direction is not None for hop in hops if hop.kind == "entity_link")


# ---------------------------------------------------------------------------
# H3.1 — Tam köken zinciri (komşu → not → bağ)
# ---------------------------------------------------------------------------


async def test_neighbor_managed_note_keeps_entity_link_prefix(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await _project(db_session, title="chain-prefix")
    todo = await _todo(db_session, title="Zincir görevi", project=project)
    _note(
        vault,
        "20 Projects/zincir.md",
        "# Zincir görevi\n\n## Karar\n\nRust kararı burada.\n",
        forkos_id=str(todo.id),
        forkos_type="note",
    )
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust kararı", entity_id=str(project.id))
    note_item = next(
        item for item in _vault_items(bundle) if item.locator.forkos_id == str(todo.id)
    )

    assert [hop.kind for hop in note_item.relation_path] == ["entity_link", "knowledge_pointer"]
    assert note_item.relation_path[0].relation == "belongs_to"
    assert note_item.relation_path[0].direction == "incoming"


async def test_neighbor_wikilink_keeps_full_seed_to_source_path(
    db_session: AsyncSession, vault: Path
) -> None:
    """§127: komşu notun wikilink'i `entity_link` önekini KAYBETMEZ."""
    project = await _project(db_session, title="chain-link")
    todo = await _todo(db_session, title="Zincir bağı", project=project)
    _note(
        vault,
        "20 Projects/zincir-bag.md",
        "# Zincir bağı\n\n## Karar\n\nRust kararı.\n\n[[Rust]]\n",
        forkos_id=str(todo.id),
        forkos_type="note",
    )
    _note(vault, "30 Knowledge/Rust.md", "# Rust\n\nRust notu.\n")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust kararı", entity_id=str(project.id))
    linked = next(
        item for item in _vault_items(bundle) if item.locator.relative_path == "30 Knowledge/Rust.md"
    )

    assert [hop.kind for hop in linked.relation_path] == [
        "entity_link",
        "knowledge_pointer",
        "wikilink",
    ]
    assert linked.relation_path[0].from_ref == f"entity:{project.id}"
    assert linked.relation_path[0].to_ref == f"entity:{todo.id}"
    assert linked.relation_path[1].to_ref == "vault:20 Projects/zincir-bag.md"


async def test_neighbor_backlink_keeps_full_seed_to_source_path(
    db_session: AsyncSession, vault: Path
) -> None:
    """§128: backlink de aynı tam zinciri taşır."""
    project = await _project(db_session, title="chain-back")
    todo = await _todo(db_session, title="Zincir geri", project=project)
    _note(
        vault,
        "20 Projects/zincir-geri.md",
        "# Zincir geri\n\n## Karar\n\nRust kararı.\n",
        forkos_id=str(todo.id),
        forkos_type="note",
    )
    _note(
        vault,
        "50 Career/karar.md",
        "# Karar\n\nRust gerekçesi.\n\n[[zincir-geri]]\n",
    )
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust kararı", entity_id=str(project.id))
    backlink = next(
        item for item in _vault_items(bundle) if item.locator.relative_path == "50 Career/karar.md"
    )

    assert [hop.kind for hop in backlink.relation_path] == [
        "entity_link",
        "knowledge_pointer",
        "backlink",
    ]
    assert backlink.relation_path[0].direction == "incoming"
    assert backlink.relation_path[-1].kind == "backlink"


async def test_depth_two_neighbor_wikilink_keeps_all_entity_hops(
    db_session: AsyncSession, vault: Path
) -> None:
    """§129: derinlik-2 zincirde İKİ entity_link hop'u da korunur."""
    project = await _project(db_session, title="deep-chain")
    middle = await _entity(db_session, type="source", title="Orta kayıt")
    leaf = await _entity(db_session, type="todo", title="Yaprak görev")
    await _link(db_session, middle, project, "belongs_to")
    await _link(db_session, leaf, middle, "belongs_to")
    _note(
        vault,
        "30 Knowledge/yaprak.md",
        "# Yaprak görev\n\n## Karar\n\nRust kararı burada.\n\n[[Rust]]\n",
        forkos_id=str(leaf.id),
        forkos_type="note",
    )
    _note(vault, "30 Knowledge/Rust.md", "# Rust\n\nRust notu.\n")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(
        db_session, query="Rust kararı", entity_id=str(project.id), max_depth=2
    )
    linked = next(
        item for item in _vault_items(bundle) if item.locator.relative_path == "30 Knowledge/Rust.md"
    )

    assert [hop.kind for hop in linked.relation_path] == [
        "entity_link",
        "entity_link",
        "knowledge_pointer",
        "wikilink",
    ]
    assert [hop.direction for hop in linked.relation_path[:2]] == ["incoming", "incoming"]
    assert linked.relation_path[0].to_ref == f"entity:{middle.id}"
    assert linked.relation_path[1].to_ref == f"entity:{leaf.id}"


# ---------------------------------------------------------------------------
# H3.1 — Olay dürüstlüğü (tarama nöbetçisi + kanıt tavanı)
# ---------------------------------------------------------------------------


async def _event_only_bundle(
    db_session: AsyncSession, project: Entity, **kwargs
) -> ev.EvidenceBundle:
    return await ev.retrieve_evidence(
        db_session, query="olay", entity_id=str(project.id), scope="operational", **kwargs
    )


async def test_eight_events_do_not_mark_event_channel_truncated(
    db_session: AsyncSession, vault: Path
) -> None:
    """§130: tam 8 uygun olay → tavan DOLMADI, dürüst `truncated=false`."""
    project = await _project(db_session, title="eight")
    for index in range(8):
        await _event(db_session, project, verb=f"event.verb{index}")

    bundle = await _event_only_bundle(db_session, project)

    step = _trace(bundle, "events")
    assert step.accepted == 8
    assert step.truncated is False
    assert bundle.truncated is False


async def test_nine_events_mark_event_channel_truncated(
    db_session: AsyncSession, vault: Path
) -> None:
    """§131: 9 uygun olay → 8 kanıt, kanal `truncated=true`."""
    project = await _project(db_session, title="nine")
    for index in range(9):
        await _event(db_session, project, verb=f"event.verb{index}")

    bundle = await _event_only_bundle(db_session, project)

    step = _trace(bundle, "events")
    assert step.considered == 9
    assert step.accepted == 8
    assert step.truncated is True


async def test_event_truncation_propagates_to_bundle(
    db_session: AsyncSession, vault: Path
) -> None:
    """§25/§132: kanal kesmesi pakete yayılır — ve kaynağı iz'de görünür."""
    project = await _project(db_session, title="propagate")
    for index in range(9):
        await _event(db_session, project, verb=f"event.verb{index}")

    bundle = await _event_only_bundle(db_session, project)

    assert bundle.truncated is True
    assert _trace(bundle, "events").truncated is True
    # Kesme olay kanalından geldi; genel bütçe tavana takılmadı.
    assert _trace(bundle, "budget").truncated is False


async def test_exact_scan_cap_uses_plus_one_probe(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§132: tam tarama tavanı kadar satır → kesilmedi (nöbetçi kanıtı)."""
    monkeypatch.setattr(ev, "MAX_EVENT_SCAN_ROWS", 3)
    project = await _project(db_session, title="scan-exact")
    for index in range(3):
        await _event(db_session, project, verb=f"event.verb{index}")

    bundle = await _event_only_bundle(db_session, project)

    step = _trace(bundle, "events")
    assert step.considered == 3
    assert step.accepted == 3
    assert step.truncated is False
    assert bundle.truncated is False


async def test_scan_cap_plus_one_marks_truncated(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§132: tavan+1 satır → tarama kesildi ve bildirildi."""
    monkeypatch.setattr(ev, "MAX_EVENT_SCAN_ROWS", 3)
    project = await _project(db_session, title="scan-over")
    for index in range(4):
        await _event(db_session, project, verb=f"event.verb{index}")

    bundle = await _event_only_bundle(db_session, project)

    step = _trace(bundle, "events")
    assert step.considered == 3  # pencere tavanı
    assert step.truncated is True
    assert bundle.truncated is True


# ---------------------------------------------------------------------------
# H3.1 — Olay gerekçesindeki GERÇEK BFS derinliği
# ---------------------------------------------------------------------------


async def test_seed_event_reason_is_explicit_seed(
    db_session: AsyncSession, vault: Path
) -> None:
    project = await _project(db_session, title="depth-seed")
    event = await _event(db_session, project, verb="project.updated")

    bundle = await _event_only_bundle(db_session, project)
    item = next(entry for entry in bundle.evidence if entry.source_id == str(event.id))

    assert "the explicit entity seed" in item.retrieval_reason
    assert item.relation_path == []


async def test_depth_one_event_reason_reports_depth_one(
    db_session: AsyncSession, vault: Path
) -> None:
    """§29: komşu olayı "depth-0" diye etiketleyemez."""
    project = await _project(db_session, title="depth-one")
    todo = await _todo(db_session, title="Derinlik bir", project=project)
    event = await _event(db_session, todo, verb="todo.updated")

    bundle = await _event_only_bundle(db_session, project)
    item = next(entry for entry in bundle.evidence if entry.source_id == str(event.id))

    assert "depth-1 related entity" in item.retrieval_reason
    assert "depth-0" not in item.retrieval_reason
    assert [(hop.relation, hop.direction) for hop in item.relation_path] == [
        ("belongs_to", "incoming")
    ]


async def test_depth_two_event_reason_reports_depth_two(
    db_session: AsyncSession, vault: Path
) -> None:
    """§133: derinlik-2 olayı hem gerekçede hem 2 hop'luk yolda görünür."""
    project = await _project(db_session, title="depth-two")
    todo = await _todo(db_session, title="Derinlik ara", project=project)
    leaf = await _entity(db_session, type="todo", title="Derinlik iki")
    await _link(db_session, leaf, todo, "belongs_to")
    event = await _event(db_session, leaf, verb="todo.updated")

    bundle = await _event_only_bundle(db_session, project, max_depth=2)
    item = next(entry for entry in bundle.evidence if entry.source_id == str(event.id))

    assert "depth-2 related entity" in item.retrieval_reason
    assert len(item.relation_path) == 2
    assert [hop.direction for hop in item.relation_path] == ["incoming", "incoming"]


# ---------------------------------------------------------------------------
# H3.1 — İstek başına TEK yapısal gezinme
# ---------------------------------------------------------------------------


async def test_scope_all_expands_operational_graph_once(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§134: bir istekte BFS tam olarak bir kez çalışır."""
    project = await _project(db_session, title="once")
    todo = await _todo(db_session, title="Tek gezinme", project=project)
    _note(
        vault,
        "20 Projects/tek.md",
        "# Tek gezinme\n\n## Karar\n\nRust kararı.\n",
        forkos_id=str(todo.id),
        forkos_type="note",
    )
    refresh_vault_index()

    calls = {"count": 0}
    real_expand = ev._expand_graph

    async def counting_expand(session, root, max_depth):
        calls["count"] += 1
        return await real_expand(session, root, max_depth)

    monkeypatch.setattr(ev, "_expand_graph", counting_expand)

    bundle = await ev.retrieve_evidence(
        db_session, query="Rust kararı", entity_id=str(project.id), scope="all", max_depth=2
    )

    assert calls["count"] == 1
    assert _trace(bundle, "graph").accepted >= 1
    assert str(todo.id) in {item.source_id for item in bundle.evidence}


async def test_operational_event_and_vault_neighbor_use_same_graph_path(
    db_session: AsyncSession, vault: Path
) -> None:
    """§37: üç kanal da AYNI gezinme anlık görüntüsünden türetilir."""
    project = await _project(db_session, title="shared")
    todo = await _todo(db_session, title="Paylaşılan görev", project=project)
    event = await _event(db_session, todo, verb="todo.updated")
    _note(
        vault,
        "20 Projects/paylasilan.md",
        "# Paylaşılan görev\n\n## Karar\n\nRust kararı.\n\n[[Rust]]\n",
        forkos_id=str(todo.id),
        forkos_type="note",
    )
    _note(vault, "30 Knowledge/Rust.md", "# Rust\n\nRust notu.\n")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust kararı", entity_id=str(project.id))

    entity_item = next(item for item in bundle.evidence if item.source_id == str(todo.id))
    event_item = next(item for item in bundle.evidence if item.source_id == str(event.id))
    note_item = next(item for item in _vault_items(bundle) if item.locator.forkos_id == str(todo.id))
    linked_item = next(
        item for item in _vault_items(bundle) if item.locator.relative_path == "30 Knowledge/Rust.md"
    )

    first_hop = entity_item.relation_path[0]
    for other in (event_item, note_item, linked_item):
        assert other.relation_path[0] == first_hop
    assert (first_hop.relation, first_hop.direction) == ("belongs_to", "incoming")


# ---------------------------------------------------------------------------
# H3.1 — Global bütçe kırpması kaynak bölümünü AŞMAZ
# ---------------------------------------------------------------------------


def _architecture_fixture(vault: Path, project: Entity) -> Path:
    body = (
        "# forkjob\n\n"
        "## Old Decision\n\n"
        "Python was considered for the prototype.\n\n"
        + "Python dolgu satırı burada.\n" * 20
        + "\n## Architecture Decision\n\n"
        "Rust was selected because of memory safety.\n"
        + "Rust dolgu satırı burada.\n" * 60
    )
    return _note(
        vault,
        "20 Projects/shrink.md",
        body,
        forkos_id=str(project.id),
        forkos_type="project",
    )


async def test_global_budget_shrink_never_crosses_heading_section(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§137: kırpma önceki başlığa TAŞMAZ; `heading` yalan söylemez."""
    project = await _project(db_session, title="shrink")
    path = _architecture_fixture(vault, project)
    refresh_vault_index()
    monkeypatch.setattr(ev, "MAX_TOTAL_EVIDENCE_CHARS", 400)

    bundle = await ev.retrieve_evidence(
        db_session, query="Rust memory safety", entity_id=str(project.id), scope="knowledge", limit=1
    )
    item = bundle.evidence[0]

    lines = path.read_text(encoding="utf-8").split("\n")
    section_start = next(
        index for index, line in enumerate(lines) if line.strip() == "## Architecture Decision"
    )

    assert item.locator.heading == "Architecture Decision"
    assert item.truncated is True
    assert item.locator.line_start >= section_start + 1
    assert "Python" not in item.excerpt
    assert len(item.excerpt) <= 400


async def test_shrunk_vault_locator_line_range_remains_exact(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§48: kırpılmış snippet'in satır numaraları FİZİKSEL satırlardır."""
    project = await _project(db_session, title="shrink-lines")
    path = _architecture_fixture(vault, project)
    refresh_vault_index()
    monkeypatch.setattr(ev, "MAX_TOTAL_EVIDENCE_CHARS", 400)

    bundle = await ev.retrieve_evidence(
        db_session, query="Rust memory safety", entity_id=str(project.id), scope="knowledge", limit=1
    )
    item = bundle.evidence[0]

    lines = path.read_text(encoding="utf-8").split("\n")
    span = "\n".join(lines[item.locator.line_start - 1 : item.locator.line_end])
    section_start = next(
        index for index, line in enumerate(lines) if line.strip() == "## Architecture Decision"
    )

    assert span.startswith(item.excerpt)
    assert lines[item.locator.line_start - 1].startswith(item.excerpt.split("\n")[0])
    assert item.locator.line_start >= section_start + 1  # yukarı taşmadı
    assert "Python" not in item.excerpt


async def test_single_overlong_line_keeps_correct_heading_and_line(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§49: tek satır bütçeyi aşarsa önek kırpılır; başlık ve satır doğru kalır."""
    project = await _project(db_session, title="overlong")
    path = _note(
        vault,
        "20 Projects/overlong.md",
        "# forkjob\n\n## Architecture Decision\n\nRust "
        + "x" * 3000
        + "\n\n## Sonraki\n\nbaşka\n",
        forkos_id=str(project.id),
        forkos_type="project",
    )
    refresh_vault_index()
    monkeypatch.setattr(ev, "MAX_TOTAL_EVIDENCE_CHARS", 200)

    bundle = await ev.retrieve_evidence(
        db_session, query="Rust", entity_id=str(project.id), scope="knowledge", limit=1
    )
    item = bundle.evidence[0]

    lines = path.read_text(encoding="utf-8").split("\n")
    assert item.locator.heading == "Architecture Decision"
    assert item.locator.line_start == item.locator.line_end
    assert item.truncated is True
    assert lines[item.locator.line_start - 1].startswith(item.excerpt)
    assert "başka" not in item.excerpt


# ---------------------------------------------------------------------------
# H3.2 — Backlink köken sürekliliği ve tek-satır locator dürüstlüğü
# ---------------------------------------------------------------------------


async def test_direct_seed_backlink_relation_path_is_continuous(
    db_session: AsyncSession, vault: Path
) -> None:
    """§8: `Project → Project.md → Decision.md` zinciri kopuk olamaz."""
    project = await _project(db_session, title="direct-back")
    _note(
        vault,
        "20 Projects/direct-back.md",
        "# direct-back\n\n## Karar\n\nRust kararı.\n",
        forkos_id=str(project.id),
        forkos_type="project",
    )
    _note(vault, "50 Career/karar.md", "# Karar\n\nRust gerekçesi.\n\n[[direct-back]]\n")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(
        db_session, query="Rust kararı", entity_id=str(project.id), scope="knowledge"
    )
    backlink = next(
        item for item in _vault_items(bundle) if item.locator.relative_path == "50 Career/karar.md"
    )

    assert_continuous_path(backlink.relation_path)
    assert [hop.kind for hop in backlink.relation_path] == ["knowledge_pointer", "backlink"]
    assert backlink.relation_path[0].to_ref == "vault:20 Projects/direct-back.md"
    assert backlink.relation_path[1].from_ref == "vault:20 Projects/direct-back.md"
    assert backlink.relation_path[1].to_ref == "vault:50 Career/karar.md"


async def test_neighbor_backlink_relation_path_is_continuous(
    db_session: AsyncSession, vault: Path
) -> None:
    """§7/§156: komşu üzerinden gelen backlink de baştan sona bitişiktir."""
    project = await _project(db_session, title="neighbor-back")
    todo = await _todo(db_session, title="Geri görev", project=project)
    _note(
        vault,
        "20 Projects/geri-gorev.md",
        "# Geri görev\n\n## Karar\n\nRust kararı.\n",
        forkos_id=str(todo.id),
        forkos_type="note",
    )
    _note(vault, "50 Career/karar.md", "# Karar\n\nRust gerekçesi.\n\n[[geri-gorev]]\n")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust kararı", entity_id=str(project.id))
    backlink = next(
        item for item in _vault_items(bundle) if item.locator.relative_path == "50 Career/karar.md"
    )

    assert_continuous_path(backlink.relation_path)
    assert [hop.kind for hop in backlink.relation_path] == [
        "entity_link",
        "knowledge_pointer",
        "backlink",
    ]
    assert backlink.relation_path[0].from_ref == f"entity:{project.id}"
    assert backlink.relation_path[0].to_ref == f"entity:{todo.id}"
    assert backlink.relation_path[1].to_ref == "vault:20 Projects/geri-gorev.md"
    assert backlink.relation_path[2].from_ref == "vault:20 Projects/geri-gorev.md"
    assert backlink.relation_path[2].to_ref == "vault:50 Career/karar.md"


async def test_vault_relation_paths_are_adjacent_hop_continuous(
    db_session: AsyncSession, vault: Path
) -> None:
    """§5: bütün kasa kanıtlarında ardışık hop'lar bitişik olmalı."""
    project = await _project(db_session, title="continuity")
    todo = await _todo(db_session, title="Süreklilik görevi", project=project)
    await _event(db_session, todo, verb="todo.updated")
    _note(
        vault,
        "20 Projects/sureklilik.md",
        "# Süreklilik görevi\n\n## Karar\n\nRust kararı burada.\n\n[[Rust]]\n",
        forkos_id=str(todo.id),
        forkos_type="note",
    )
    _note(vault, "30 Knowledge/Rust.md", "# Rust\n\nRust notu.\n")
    _note(vault, "50 Career/karar.md", "# Karar\n\nRust gerekçesi.\n\n[[sureklilik]]\n")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust kararı", entity_id=str(project.id))

    vault_items = _vault_items(bundle)
    assert len(vault_items) >= 3
    for item in vault_items:
        assert_continuous_path(item.relation_path)
    # Operasyonel ve olay kanıtları da aynı kurala uyar.
    for item in bundle.evidence:
        assert_continuous_path(item.relation_path)


async def test_backlink_final_ref_is_evidence_source(
    db_session: AsyncSession, vault: Path
) -> None:
    """§6: kasa kanıtının son hop'u KAYNAĞIN KENDİSİNE işaret eder."""
    project = await _project(db_session, title="final-ref")
    todo = await _todo(db_session, title="Son referans", project=project)
    _note(
        vault,
        "20 Projects/son-referans.md",
        "# Son referans\n\n## Karar\n\nRust kararı.\n\n[[Rust]]\n",
        forkos_id=str(todo.id),
        forkos_type="note",
    )
    _note(vault, "30 Knowledge/Rust.md", "# Rust\n\nRust notu.\n")
    _note(vault, "50 Career/karar.md", "# Karar\n\nRust gerekçesi.\n\n[[son-referans]]\n")
    refresh_vault_index()

    bundle = await ev.retrieve_evidence(db_session, query="Rust kararı", entity_id=str(project.id))

    for item in _vault_items(bundle):
        if not item.relation_path:
            continue
        assert item.relation_path[-1].to_ref == f"vault:{item.locator.relative_path}"


async def test_global_shrink_multiline_excerpt_to_single_focus_updates_locator(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§11/§157: çok satırlı snippet tek odak satırına düşerse locator GÜNCELLENİR."""
    from app.integrations.obsidian import evidence as vault_evidence

    project = await _project(db_session, title="focus-shrink")
    long_line = "Rust " + "x" * 790
    body = (
        "# forkjob\n\n"
        "## Old Decision\n\n"
        "Python was considered.\n\n"
        "## Architecture Decision\n\n"
        "short context line\n"
        f"{long_line}\n"
        "another short line\n"
    )
    path = _note(
        vault,
        "20 Projects/focus.md",
        body,
        forkos_id=str(project.id),
        forkos_type="project",
    )
    refresh_vault_index()

    lines = path.read_text(encoding="utf-8").split("\n")
    focus_index = next(index for index, line in enumerate(lines) if line.startswith("Rust "))
    sections = vault_evidence.build_sections(lines, vault_evidence.body_start_line(lines))
    initial = vault_evidence.extract_excerpt(
        lines, sections, vault_evidence.tokenize_query("Rust"), max_chars=1200
    )

    # 1) İlk çıkarım ÇOK satırlıdır (bölüm bütçeye sığdı).
    assert initial is not None
    assert initial.line_start < initial.line_end
    assert initial.truncated is False

    # 2) Global bütçe snippet'i tek odak satırının önekine indirir.
    monkeypatch.setattr(ev, "MAX_TOTAL_EVIDENCE_CHARS", 200)
    bundle = await ev.retrieve_evidence(
        db_session, query="Rust", entity_id=str(project.id), scope="knowledge", limit=1
    )
    item = bundle.evidence[0]

    assert item.truncated is True
    assert item.locator.heading == "Architecture Decision"
    assert item.locator.line_start == item.locator.line_end == focus_index + 1
    assert item.excerpt == lines[focus_index][:200]
