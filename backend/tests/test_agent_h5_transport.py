"""H5 — gerçek `/mcp` taşıması: beş mod, hatalar, bozulma, değişmezlik."""

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
from app.modules.review.models import Review
from tests.agent_test_utils import (
    capture_db_content_fingerprint,
    capture_vault_fingerprint,
    forbid_outbound_network,  # noqa: F401  (autouse)
    legacy_notes_counts,
    mcp_session,
    table_counts,
    tool_payload,
)
from tests.h5_fixtures import make_event, make_project, make_todo, write_daily_note

ANCHOR = "2026-09-18T17:00:00+00:00"


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "H5TransportVault"
    path.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "H5TransportVault")
    return path


@pytest.fixture(autouse=True)
def reset_vault_index() -> AsyncIterator[None]:
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


async def _seed(session: AsyncSession, vault: Path) -> dict[str, str]:
    project = await make_project(session, title="forkjob", next_action="")
    todo = await make_todo(session, title="ALES denemesi", priority=3)
    await make_event(
        session,
        verb="pomodoro.completed",
        occurred_at=datetime(2026, 9, 18, 17, 0, tzinfo=UTC),
        entity=todo,
        payload={"minutes": 85, "topic": "ALES"},
    )
    write_daily_note(vault, "2026-09-19", "# 19 Eylül\n\nforkjob UI için minimum kaynak yaklaşımı.\n")
    await session.commit()
    return {"project_id": str(project.id), "todo_id": str(todo.id)}


async def test_five_modes_over_real_transport(db_session: AsyncSession, vault: Path) -> None:
    world = await _seed(db_session, vault)

    async with mcp_session() as session:
        continuity = await session.call_tool("forkos_review_intelligence", {"mode": "continuity"})
        daily = await session.call_tool(
            "forkos_review_intelligence", {"mode": "daily_close", "reference_date": "2026-09-18"}
        )
        weekly = await session.call_tool(
            "forkos_review_intelligence", {"mode": "weekly_review", "reference_date": "2026-09-20"}
        )
        delta = await session.call_tool(
            "forkos_review_intelligence",
            {"mode": "period_delta", "since": ANCHOR, "focus_entity_id": world["project_id"]},
        )
        consolidation = await session.call_tool(
            "forkos_review_intelligence", {"mode": "consolidation_review", "since": ANCHOR}
        )

    for result, mode in (
        (continuity, "continuity"),
        (daily, "daily_close"),
        (weekly, "weekly_review"),
        (delta, "period_delta"),
        (consolidation, "consolidation_review"),
    ):
        assert result.is_error is False, result.content
        payload = tool_payload(result)
        assert payload["mode"] == mode
        assert "coverage" in payload
        assert "source_manifest" in payload
        assert isinstance(payload["trace"], list)


async def test_continuity_over_transport_is_factual(
    db_session: AsyncSession, vault: Path
) -> None:
    await _seed(db_session, vault)

    async with mcp_session() as session:
        result = await session.call_tool("forkos_review_intelligence", {"mode": "continuity"})

    payload = tool_payload(result)
    data = payload["payload"]
    assert data["anchor"]["kind"] in {"last_meaningful_activity", "fallback", "explicit"}
    assert data["last_meaningful_activity"]["verb"] == "pomodoro.completed"
    for insight in data["state_changes"]:
        assert insight["support_refs"]


async def test_invalid_mode_is_rejected_over_transport() -> None:
    async with mcp_session() as session:
        result = await session.call_tool("forkos_review_intelligence", {"mode": "monthly_review"})

    assert result.is_error is True
    assert "mode" in result.content[0].text.lower()


async def test_naive_timestamp_is_rejected_over_transport() -> None:
    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_review_intelligence",
            {"mode": "period_delta", "since": "2026-09-18T10:00:00"},
        )

    assert result.is_error is True
    assert "INVALID_TIME_RANGE" in result.content[0].text


async def test_period_too_large_is_rejected_over_transport() -> None:
    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_review_intelligence",
            {"mode": "period_delta", "since": "2026-01-01T00:00:00+00:00"},
        )

    assert result.is_error is True
    assert "PERIOD_TOO_LARGE" in result.content[0].text


async def test_incompatible_arguments_are_rejected_over_transport() -> None:
    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_review_intelligence", {"mode": "daily_close", "since": ANCHOR}
        )

    assert result.is_error is True
    assert "INVALID_ARGUMENT" in result.content[0].text


async def test_unknown_focus_entity_is_rejected_over_transport() -> None:
    import uuid

    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_review_intelligence",
            {"mode": "continuity", "focus_entity_id": str(uuid.uuid4())},
        )

    assert result.is_error is True
    assert "INVALID_FOCUS_ENTITY" in result.content[0].text


async def test_vault_unavailable_degrades_over_transport(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§143: kasa yoksa operasyonel süreklilik ÇALIŞMAYA DEVAM EDER."""
    await _seed(db_session, vault)
    monkeypatch.setattr(settings, "obsidian_vault_path", str(vault / "yok"))

    async with mcp_session() as session:
        result = await session.call_tool("forkos_review_intelligence", {"mode": "continuity"})

    assert result.is_error is False, result.content
    payload = tool_payload(result)
    assert payload["payload"]["last_meaningful_activity"]["verb"] == "pomodoro.completed"
    assert payload["source_manifest"]["daily_notes_found"] == 0
    # Sessiz boş liste DEĞİL: kasa yokluğu açıkça bildirilir (§143).
    assert any("VAULT_UNAVAILABLE" in warning for warning in payload["warnings"])


async def test_h4_unavailable_degrades_over_transport(
    db_session: AsyncSession, vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§153: H4 kapalıyken H5 deterministik çıktıyı korur."""
    from tests.test_h5_consolidation import patch_h4

    await _seed(db_session, vault)
    patch_h4(monkeypatch, failure_code="MODEL_PROVIDER_UNAVAILABLE")

    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_review_intelligence", {"mode": "consolidation_review", "since": ANCHOR}
        )

    assert result.is_error is False, result.content
    payload = tool_payload(result)
    assert any("H4_UNAVAILABLE" in warning for warning in payload["warnings"])
    assert payload["payload"]["daily_notes"]
    assert payload["payload"]["promotion_candidates"] == []


async def test_h5_is_read_only_over_transport(
    db_session: AsyncSession, vault: Path
) -> None:
    """§172: H5 hiçbir şey yazmaz; Review/Todo/Entity sayıları değişmez."""
    await _seed(db_session, vault)
    db_before = await capture_db_content_fingerprint(db_session)
    vault_before = capture_vault_fingerprint(vault)
    counts_before = await table_counts(db_session)
    legacy_before = await legacy_notes_counts(db_session)

    async with mcp_session() as session:
        for mode in ("continuity", "daily_close", "weekly_review", "consolidation_review"):
            await session.call_tool("forkos_review_intelligence", {"mode": mode})

    assert await capture_db_content_fingerprint(db_session) == db_before
    assert capture_vault_fingerprint(vault) == vault_before
    assert await table_counts(db_session) == counts_before
    assert await legacy_notes_counts(db_session) == legacy_before
    for model in (Review, Link, Event):
        assert (await db_session.execute(select(func.count(model.id)))).scalar_one() >= 0
    assert (await db_session.execute(select(func.count(Review.id)))).scalar_one() == 0
    assert (await db_session.execute(select(func.count(Entity.id)))).scalar_one() == 2


async def test_h5_does_not_log_source_text(
    db_session: AsyncSession, vault: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """§93: kaynak metin forkOS uygulama loglarında YER ALMAZ."""
    marker = "OZEL-ISARET-METNI-77"
    await _seed(db_session, vault)
    write_daily_note(vault, "2026-09-20", f"# 20 Eylül\n\n{marker} notu.\n")
    await db_session.commit()

    with caplog.at_level("DEBUG"):
        async with mcp_session() as session:
            await session.call_tool("forkos_review_intelligence", {"mode": "daily_close"})

    assert all(
        marker not in record.getMessage()
        for record in caplog.records
        if record.name.startswith("app")
    )


async def test_h5_writes_nothing_through_mcp_even_with_knowledge(
    db_session: AsyncSession, vault: Path
) -> None:
    await _seed(db_session, vault)
    vault_before = capture_vault_fingerprint(vault)
    counts_before = await table_counts(db_session)

    async with mcp_session() as session:
        await session.call_tool(
            "forkos_review_intelligence", {"mode": "consolidation_review", "include_knowledge": True}
        )

    assert capture_vault_fingerprint(vault) == vault_before
    assert await table_counts(db_session) == counts_before


async def test_conflicting_managed_ids_are_reported_over_transport(
    db_session: AsyncSession, vault: Path
) -> None:
    """§159: çelişkili kimlik bilgi sinyalini belirsizleştirir; gizlenmez."""
    project = await make_project(db_session, title="forkjob")
    await db_session.commit()
    directory = vault / "20 Projects"
    directory.mkdir(parents=True, exist_ok=True)
    frontmatter = (
        "---\n"
        f"forkos_id: {project.id}\n"
        "forkos_type: project\n"
        "title: Aynı kimlik\n"
        "---\n\nGövde.\n"
    )
    (directory / "a.md").write_text(frontmatter, encoding="utf-8")
    (directory / "b.md").write_text(frontmatter, encoding="utf-8")

    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_review_intelligence", {"mode": "consolidation_review"}
        )

    assert result.is_error is False, result.content
    payload = tool_payload(result)
    assert any("CONFLICTING_KNOWLEDGE" in warning for warning in payload["warnings"])
    issues = [item["issue"] for item in payload["payload"]["knowledge_health"]]
    assert "managed_source_conflict" in issues


async def test_include_knowledge_is_rejected_where_it_has_no_effect() -> None:
    """§124: etkisiz modda bayrak sessizce yok sayılmaz."""
    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_review_intelligence",
            {"mode": "period_delta", "since": ANCHOR, "include_knowledge": False},
        )

    assert result.is_error is True
    assert "INVALID_ARGUMENT" in result.content[0].text
