"""A1.1b No-source-mutation invariant regression and state fingerprint test.

Proves that agent lifecycle observations:
1. NEVER mutate canonical `entity` or any operational domain state (content, identity, row count).
2. NEVER write to the append-only `event` activity log (`log_event`).
3. NEVER modify H2 Hot Memory files or f0rknbrain Vault files.
4. NEVER mutate execution/proactivity/task state.
5. ONLY modify support tables: `agent_session` and `agent_session_turn`.
6. Negative proofs verify that UPDATE, INSERT, DELETE, and Vault mutations are reliably detected.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.config import settings
from app.core.models import Entity, Event, Link, Notification
from app.db import SessionLocal
from app.main import app
from app.modules.agent_episode import service as a3
from app.modules.agent_lifecycle.models import AgentSession, AgentSessionTurn
from app.modules.bookmark.models import Bookmark
from app.modules.execution.models import ExecutionDecision, ExecutionPlan, ExecutionReceipt
from app.modules.flashcard.models import FlashcardCard
from app.modules.opportunity.models import Application, Opportunity
from app.modules.pomodoro.models import PomodoroSession
from app.modules.proactivity.models import ProactivityRule, ProactivityRun
from app.modules.project.models import Milestone, Project
from app.modules.review.models import Review
from app.modules.todo.models import Todo
from tests.a3_fixtures import (
    deliver,
    ingest,
    items_json,
    patch_provider,
    seal,
    start_session,
)
from tests.h4_test_provider import ScriptedProvider

DOMAIN_MODELS = [
    Entity,
    Event,
    Link,
    Notification,
    Todo,
    Project,
    Milestone,
    Opportunity,
    Application,
    Bookmark,
    FlashcardCard,
    PomodoroSession,
    Review,
    ProactivityRule,
    ProactivityRun,
    ExecutionPlan,
    ExecutionReceipt,
    ExecutionDecision,
]


def _snapshot_vault_files(vault_path: Path | None) -> dict[str, str]:
    if not vault_path or not vault_path.exists():
        return {}
    hashes = {}
    for p in vault_path.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            hashes[str(p.relative_to(vault_path))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashes


async def snapshot_domain_state() -> dict[str, dict[str, Any]]:
    """Tüm kanonik modeller için row count, row identity ve row content fingerprint'i alır."""
    async with SessionLocal() as db:
        snapshots: dict[str, dict[str, Any]] = {}
        for model in DOMAIN_MODELS:
            table = model.__table__
            pk_cols = list(table.primary_key.columns)
            # Use Core select(*table.c) to eagerly load all columns without ORM deferred loading issues
            stmt = select(*table.c).order_by(*pk_cols)
            res = await db.execute(stmt)
            rows = res.mappings().all()

            row_reprs = []
            identities = []
            for r in rows:
                col_dict: dict[str, Any] = {}
                for col_name, val in r.items():
                    if isinstance(val, (datetime, uuid.UUID)):
                        col_dict[col_name] = str(val)
                    elif isinstance(val, (dict, list)):
                        col_dict[col_name] = json.dumps(val, sort_keys=True, default=str)
                    else:
                        col_dict[col_name] = str(val) if val is not None else None
                row_reprs.append(tuple(sorted(col_dict.items())))
                identities.append(tuple(str(r[c.name]) for c in pk_cols))

            raw_bytes = repr(row_reprs).encode("utf-8")
            digest = hashlib.sha256(raw_bytes).hexdigest()
            snapshots[table.name] = {
                "count": len(rows),
                "digest": digest,
                "identities": identities,
            }
        return snapshots


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def test_lifecycle_observation_never_mutates_domain_state_or_files(client: AsyncClient) -> None:
    vault_dir = settings.resolved_obsidian_vault_path

    state_before = await snapshot_domain_state()
    vault_before = _snapshot_vault_files(vault_dir)

    endpoint = "/api/agent/lifecycle/event"
    events = [
        {"schema_version": 1, "event": "session_start", "harness": "hermes", "session_id": "inv_sess_1", "turn_id": "t1", "platform": "desktop"},
        {"schema_version": 1, "event": "session_start", "harness": "hermes", "session_id": "inv_sess_1", "turn_id": "t1", "platform": "desktop"},
        {"schema_version": 1, "event": "turn_seen", "harness": "hermes", "session_id": "inv_sess_1", "turn_id": "t1", "platform": "desktop"},
        {"schema_version": 1, "event": "turn_seen", "harness": "hermes", "session_id": "inv_sess_1", "turn_id": "t2", "platform": "desktop"},
        {"schema_version": 1, "event": "session_finalize", "harness": "hermes", "session_id": "inv_sess_1", "platform": "desktop"},
        {"schema_version": 1, "event": "session_finalize", "harness": "hermes", "session_id": "inv_sess_1", "platform": "desktop"},
    ]

    for ev in events:
        resp = await client.post(endpoint, json=ev)
        assert resp.status_code == 200

    rejected = await client.post(endpoint, json={"schema_version": 1, "event": "turn_seen", "harness": "hermes", "session_id": "inv_sess_1", "turn_id": "t3", "platform": "desktop"})
    assert rejected.status_code == 409

    state_after = await snapshot_domain_state()
    vault_after = _snapshot_vault_files(vault_dir)

    # Invariant 1: Row count, identities and content SHA-256 digest are 100% identical for all 18 tables
    for table_name, snap_before in state_before.items():
        snap_after = state_after[table_name]
        assert snap_after["count"] == snap_before["count"], (
            f"INVARIANT VIOLATION: Domain table '{table_name}' count changed from "
            f"{snap_before['count']} to {snap_after['count']}"
        )
        assert snap_after["identities"] == snap_before["identities"], (
            f"INVARIANT VIOLATION: Domain table '{table_name}' identities changed"
        )
        assert snap_after["digest"] == snap_before["digest"], (
            f"INVARIANT VIOLATION: Domain table '{table_name}' row content digest changed"
        )

    # Invariant 2: No event log / activity log was written
    assert state_after["event"]["count"] == state_before["event"]["count"], "INVARIANT VIOLATION: event log count was written"
    assert state_after["event"]["digest"] == state_before["event"]["digest"], "INVARIANT VIOLATION: event log content was written"

    # Invariant 3: Vault / Hot memory files were not modified
    assert vault_after == vault_before, "INVARIANT VIOLATION: Vault/Hot memory files were modified"

    # Invariant 4: ONLY agent_session and agent_session_turn were written
    async with SessionLocal() as db:
        session_count = await db.scalar(select(func.count()).select_from(AgentSession))
        turn_count = await db.scalar(select(func.count()).select_from(AgentSessionTurn))
        assert session_count >= 1
        assert turn_count >= 2


async def test_invariant_detects_row_update(client: AsyncClient) -> None:
    """Negatif ispat: Bir domain satırı UPDATE edildiğinde fingerprint mutlaka değişir."""
    # 1. Bir todo oluştur
    resp = await client.post("/api/todos", json={"title": "Invariant Update Test Initial"})
    assert resp.status_code == 201
    todo_id = resp.json()["id"]

    state_before = await snapshot_domain_state()

    # 2. Satırı güncelle (hem entity hem todo tablosundaki alanları değiştir)
    patch_resp = await client.patch(
        f"/api/todos/{todo_id}",
        json={"title": "Invariant Update Test Changed", "status": "done"},
    )
    assert patch_resp.status_code == 200

    state_after = await snapshot_domain_state()

    # Row count aynı kalmasına rağmen hem entity hem todo tablosunun digest'i değişmelidir
    assert state_before["todo"]["count"] == state_after["todo"]["count"]
    assert state_before["todo"]["digest"] != state_after["todo"]["digest"], (
        "Negative proof failed: row update was NOT detected on todo table!"
    )
    assert state_before["entity"]["count"] == state_after["entity"]["count"]
    assert state_before["entity"]["digest"] != state_after["entity"]["digest"], (
        "Negative proof failed: row update was NOT detected on entity table!"
    )


async def test_invariant_detects_row_insert(client: AsyncClient) -> None:
    """Negatif ispat: Bir domain satırı INSERT edildiğinde fingerprint mutlaka değişir."""
    state_before = await snapshot_domain_state()

    resp = await client.post("/api/todos", json={"title": "Invariant Insert Test New"})
    assert resp.status_code == 201

    state_after = await snapshot_domain_state()
    assert state_before["todo"]["count"] != state_after["todo"]["count"]
    assert state_before["todo"]["digest"] != state_after["todo"]["digest"]


async def test_invariant_detects_row_delete(client: AsyncClient) -> None:
    """Negatif ispat: Bir domain satırı DELETE edildiğinde fingerprint mutlaka değişir."""
    resp = await client.post("/api/todos", json={"title": "Invariant Delete Target"})
    assert resp.status_code == 201
    todo_id = resp.json()["id"]

    state_before = await snapshot_domain_state()

    del_resp = await client.delete(f"/api/todos/{todo_id}")
    assert del_resp.status_code == 204

    state_after = await snapshot_domain_state()
    assert state_before["todo"]["count"] != state_after["todo"]["count"]
    assert state_before["todo"]["digest"] != state_after["todo"]["digest"]


def test_invariant_detects_vault_mutation(tmp_path: Path) -> None:
    """Negatif ispat: Kasa dosyasında 1 bayt bile değişirse file snapshot bunu yakalar."""
    test_file = tmp_path / "test_note.md"
    test_file.write_text("initial content", encoding="utf-8")

    snapshot_1 = _snapshot_vault_files(tmp_path)

    test_file.write_text("mutated content", encoding="utf-8")
    snapshot_2 = _snapshot_vault_files(tmp_path)

    assert snapshot_1 != snapshot_2, "Negative proof failed: file modification was NOT detected by vault snapshot!"


async def test_a3_episode_ingest_finalize_and_handoff_mutate_no_canonical_state(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§27: A3 yalnız kendi üç tablosunu yazar; kanonik durum ve Vault sabit kalır.

    Gerçek bir tur üretilir (H4 hattı çalışır, ifade gerçekten damıtılır), oturum
    mühürlenir ve bir sonraki oturum devri seçer. Bu zincirin hiçbir adımı
    kanonik operasyonel durumu, H7 yürütme durumunu, bildirimleri, olay
    defterini veya Vault dosyalarını değiştirmemelidir.
    """
    item_text = "A3 devir kaydı açıldı"
    patch_provider(
        monkeypatch,
        ScriptedProvider(responses=[items_json([("open_thread", item_text, item_text)])]),
    )
    vault_dir = settings.resolved_obsidian_vault_path

    state_before = await snapshot_domain_state()
    vault_before = _snapshot_vault_files(vault_dir)

    # Bu invariantın H7 yürütme tablolarını ve bildirimleri GERÇEKTEN kapsadığını kanıtla.
    for required in ("execution_plan", "execution_decision", "execution_receipt", "notification"):
        assert required in state_before, f"coverage gap: '{required}' is not fingerprinted"

    async with SessionLocal() as db:
        source_row = await start_session(db, "a3_inv_sess_a", turn_id="t1")
        await deliver(db, source_row, raw_turn_id="t1", sources=[])
        await ingest(
            db, "a3_inv_sess_a", turn_id="t1", user=item_text, assistant=item_text
        )
        sealed = await seal(db, "a3_inv_sess_a")
        assert sealed.item_count >= 1
        follower = await start_session(db, "a3_inv_sess_b", turn_id="t1")
        handoff = await a3.select_recent_handoff(
            db, current_session_id=follower.id, current_scope=None
        )
        assert handoff is not None
        assert [item.text for item in handoff.items] == [item_text]

    state_after = await snapshot_domain_state()
    vault_after = _snapshot_vault_files(vault_dir)

    for table_name, snap_before in state_before.items():
        snap_after = state_after[table_name]
        assert snap_after["count"] == snap_before["count"], (
            f"INVARIANT VIOLATION: A3 changed domain table '{table_name}' row count"
        )
        assert snap_after["identities"] == snap_before["identities"], (
            f"INVARIANT VIOLATION: A3 changed domain table '{table_name}' identities"
        )
        assert snap_after["digest"] == snap_before["digest"], (
            f"INVARIANT VIOLATION: A3 changed domain table '{table_name}' row content"
        )

    assert vault_after == vault_before, "INVARIANT VIOLATION: A3 modified Vault/Hot memory files"
