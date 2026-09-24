"""H3 evidence must bind to the first current source projection before inference."""

from __future__ import annotations

import pytest

from app.config import settings
from app.core.entity import create_entity
from app.db import SessionLocal
from app.integrations.agent.evidence import _note_candidate, retrieve_evidence
from app.integrations.judgment import context as context_service
from app.integrations.judgment.models import ContextVerdict
from app.integrations.judgment.snapshots import capture_snapshot
from app.integrations.obsidian.evidence import tokenize_query
from app.modules.project.models import Project


class LocalJudge:
    locality = "local"
    capabilities = frozenset({"context_relevance"})

    def __init__(self, mutate=None):
        self.mutate = mutate
        self.health_calls = 0
        self.judge_calls = 0

    async def health(self):
        self.health_calls += 1
        return True

    async def judge_context(self, request):
        self.judge_calls += 1
        if self.mutate:
            await self.mutate()
        return tuple(
            ContextVerdict(
                evidence_id=item.evidence_id,
                status="success",
                usefulness="useful",
                redundancy="unique",
            )
            for item in request.candidates
        )


@pytest.mark.parametrize("phase", ["before_first", "during_judge", "unchanged"])
async def test_vault_source_binding_races(tmp_path, monkeypatch, phase):
    vault = tmp_path / "Vault"
    vault.mkdir()
    note = vault / "Atlas.md"
    note.write_text("# Atlas\nRust deployment notes.\n", encoding="utf-8")
    monkeypatch.setattr(settings, "obsidian_vault_path", str(vault))

    async def change():
        note.write_text("# Atlas\nPython deployment notes.\n", encoding="utf-8")

    judge = LocalJudge(mutate=change if phase == "during_judge" else None)
    if phase == "before_first":
        original = context_service.retrieve_evidence

        async def retrieve_then_change(*args, **kwargs):
            bundle = await original(*args, **kwargs)
            assert bundle.evidence and all(item._source_revision for item in bundle.evidence)
            await change()
            return bundle

        monkeypatch.setattr(context_service, "retrieve_evidence", retrieve_then_change)

    async with SessionLocal() as session:
        result = await context_service.judge_context(
            session,
            query="Atlas Rust deployment",
            scope="knowledge",
            mode="shadow",
            provider=judge,
        )
    assert result.bundle.evidence
    assert result.effective_order == result.baseline_order
    if phase == "before_first":
        assert result.status == "invalid"
        assert result.degraded_reasons == ("CONTEXT_JUDGE_SOURCE_BINDING_FAILED",)
        assert judge.health_calls == judge.judge_calls == 0
    elif phase == "during_judge":
        assert result.status == "stale"
        assert judge.judge_calls == 1
    else:
        assert result.status == "success"
        assert judge.judge_calls == 1


async def test_project_child_projection_change_before_first_snapshot(monkeypatch):
    async with SessionLocal() as session:
        entity = await create_entity(
            session, type="project", title="Atlas", search_text="Atlas Rust"
        )
        project_id = entity.id
        session.add(Project(id=project_id, status="active", next_action="Rust release"))
        await session.commit()

    async def change():
        async with SessionLocal() as writer:
            project = await writer.get(Project, project_id)
            project.next_action = "Python release"
            await writer.commit()

    original = context_service.retrieve_evidence

    async def retrieve_then_change(*args, **kwargs):
        bundle = await original(*args, **kwargs)
        assert bundle.evidence[0].source_type == "entity"
        assert bundle.evidence[0]._source_revision
        await change()
        return bundle

    monkeypatch.setattr(context_service, "retrieve_evidence", retrieve_then_change)
    judge = LocalJudge()
    async with SessionLocal() as session:
        result = await context_service.judge_context(
            session,
            query="Atlas next action",
            entity_id=str(project_id),
            scope="operational",
            max_depth=0,
            mode="assist",
            provider=judge,
        )
    assert result.status == "invalid"
    assert result.degraded_reasons == ("CONTEXT_JUDGE_SOURCE_BINDING_FAILED",)
    assert result.effective_order == result.baseline_order
    assert judge.judge_calls == 0


async def test_private_revision_does_not_change_public_h3_evidence(tmp_path, monkeypatch):
    vault = tmp_path / "Vault"
    vault.mkdir()
    (vault / "Atlas.md").write_text("# Atlas\nRust deployment notes.\n", encoding="utf-8")
    monkeypatch.setattr(settings, "obsidian_vault_path", str(vault))
    async with SessionLocal() as session:
        bundle = await retrieve_evidence(session, query="Atlas Rust deployment", scope="knowledge")
    assert bundle.evidence[0]._source_revision
    assert bundle.evidence[0].model_copy()._source_revision == bundle.evidence[0]._source_revision
    assert "source_revision" not in bundle.model_dump_json()
    assert "vault_title_from_index" not in bundle.model_dump_json()


@pytest.mark.no_database
async def test_managed_vault_seed_without_index_uses_h3_filename_title(tmp_path, monkeypatch):
    vault = tmp_path / "Vault"
    vault.mkdir()
    (vault / "Atlas.md").write_text(
        "# Different heading\nRust deployment notes.\n", encoding="utf-8"
    )
    monkeypatch.setattr(settings, "obsidian_vault_path", str(vault))
    candidate = _note_candidate(
        vault,
        rel_path="Atlas.md",
        source_id="atlas",
        forkos_id=None,
        tier=0,
        rank=0,
        terms=tokenize_query("Rust"),
        relation_path=[],
        reason="managed seed",
        note=None,
    )
    assert candidate is not None
    assert candidate.item.title == "Atlas"
    assert candidate.item.model_copy()._vault_title_from_index is False
    snapshot = await capture_snapshot(None, candidate.item)
    assert snapshot.source_revision == candidate.item._source_revision
