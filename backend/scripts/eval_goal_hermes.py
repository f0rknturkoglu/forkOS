"""Explicit live local inference evaluation, only in the disposable forkos_hermes_eval DB.

Run in the isolated API environment; never against the personal DB or a cloud provider.
Each result preserves individual outputs, repair stages, scoped inputs and token metadata.
This is instrumentation of the real Studio pipeline, not a mocked inference provider.
"""

import argparse
import asyncio
import json
import re
import time
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select

from app.config import settings
from app.core.models import Entity
from app.db import SessionLocal
from app.modules.goal import roadmap, service, strategy, studio, studio_inference, studio_transport
from app.modules.goal.context_snapshot import build
from app.modules.goal.models import Goal
from app.modules.goal.package_authoring import PackageDraft
from app.modules.goal.package_schemas import NodeData
from app.modules.goal.schemas import GoalIn
from app.modules.goal.strategy_schemas import KeyResultIn
from app.modules.goal.studio_schemas import StudioSessionIn, StudioTurnIn
from app.modules.project import service as projects
from app.modules.project.schemas import ProjectIn
from app.modules.todo import service as todos
from app.modules.todo.models import Todo
from app.modules.todo.schemas import TodoIn, TodoUpdate

CASES = {
    "yds": "YDS'den en az 55 puan almak istiyorum. Günde iki saat çalışabilirim.",
    "software": "forkOS V2'yi yayımlamak istiyorum. Eksik testleri ve release hazırlıklarını tamamlamalıyım.",
    "passport": "Pasaport başvurumu tamamlamak istiyorum.",
    "progress": "Neredeyiz, nasıl gidiyoruz?",
    "focus": "Bu hafta neye odaklanmalıyım?",
}


async def seed(db):
    existing = await db.scalar(
        select(Entity)
        .where(Entity.type == "goal", Entity.title == "Sentetik YDS 55+ hazırlığı")
        .order_by(Entity.id)
    )
    project_existing = await db.scalar(
        select(Entity)
        .where(Entity.type == "project", Entity.title == "forkOS — sentetik release projesi")
        .order_by(Entity.id)
    )
    if existing and project_existing:
        return existing.id, project_existing.id
    project = await projects.create(db, ProjectIn(title="forkOS — sentetik release projesi"))
    goal = await service.create_goal(db, GoalIn(title="Sentetik YDS 55+ hazırlığı"))
    gid = goal.id
    await strategy.save_kr(db, gid, KeyResultIn(title="YDS puanı", target_value=55, unit="puan"))
    for index, title in enumerate(
        ("Kelime tekrarı", "Paragraf çözümü", "Deneme yanlışlarını incele")
    ):
        task = await todos.create(db, TodoIn(title=title))
        tid = task.id
        await roadmap.save_node(db, gid, NodeData(title=title, kind="record"), target_id=tid)
        await db.commit()
        if index < 2:
            await todos.update(db, tid, TodoUpdate(status="done"))
    return gid, project["id"]


def useful(name, proposal, discussion, snapshot):
    if name in {"progress", "focus"}:
        percent = snapshot["roadmap"]["percent"]
        numeric = re.search(r"%\s*(\d+)|(?:yüzde\s+)(\d+)|(\d+)\s*%", discussion.casefold())
        actual = next((int(n) for n in numeric.groups() if n), None) if numeric else None
        pending = [t["title"].casefold() for t in snapshot["todos"] if t["status"] != "done"]
        return bool(
            (actual == percent or (name == "focus" and numeric is None))
            and any(title in discussion.casefold() for title in pending)
            and not re.search(
                r"55\s*puan(?:a)?\s*(?:ald|ulaş|başar)|gerides|geridey|tembell|motivasyonsuz",
                discussion.casefold(),
            )
            and len(discussion) <= 1800
            and proposal is None
        )
    if not proposal:
        return False
    ops = proposal.operations
    tasks = [op for op in ops if op.type == "todo.create"]
    topics = [op for op in ops if op.type == "learning.topic"]
    text = " ".join(op.data.title for op in tasks).casefold()
    if name == "yds":
        return bool(
            tasks
            and topics
            and any(op.type == "key_result.save" and op.data.target_value == 55 for op in ops)
        )
    if name == "software":
        return bool(
            tasks
            and not topics
            and "test" in text
            and re.search(r"release|yayın|yayımla|sürüm", text)
        )
    return bool(
        1 <= len(tasks) <= 5 and not topics and not any(op.type == "key_result.save" for op in ops)
    )


async def evaluate(args):
    if settings.database_url.rsplit("/", 1)[-1] != "forkos_hermes_eval":
        raise SystemExit("Live eval only permits the disposable forkos_hermes_eval database")
    status = await studio_transport.status()
    if status.state != "ready" or not status.local or not status.tools_verified:
        raise SystemExit("A verified, tool-free, authorized local Hermes profile is required")
    async with SessionLocal() as db:
        gid, _ = await seed(db)
    original_request = studio_transport.request
    original_parse = studio.public_reply
    original_task_parse = studio_inference.parse_reply
    stage = {}

    async def instrumented_request(method, path, **kwargs):
        start = time.monotonic()
        result = await original_request(method, path, **kwargs)
        if path == "/v1/runs" and method == "POST":
            body = kwargs["body"]
            stage["calls"].append(
                {
                    "run_id": result.get("run_id"),
                    "request": body,
                    "input_bytes": len(body["input"].encode()),
                    "instruction_bytes": len(body["instructions"].encode()),
                }
            )
        if path.startswith("/v1/runs/") and result.get("status") in {
            "completed",
            "failed",
            "cancelled",
        }:
            call = next((c for c in stage["calls"] if c["run_id"] == path.rsplit("/", 1)[-1]), None)
            if call is not None:
                call.update(
                    {
                        "status": result.get("status"),
                        "output": result.get("output"),
                        "usage": result.get("usage"),
                        "finish_reason": result.get("finish_reason"),
                        "response_keys": sorted(result),
                        "poll_seconds": time.monotonic() - start,
                    }
                )
        return result

    def instrumented_parse(output, **kwargs):
        try:
            result = original_parse(output, **kwargs)
            stage["parse"].append(
                {"valid": True, "has_proposal": result.get("proposal") is not None}
            )
            return result
        except ValueError as exc:
            stage["semantic"].append(False)
            stage["parse"].append(
                {"valid": False, "category": type(exc).__name__, "detail": str(exc)[:1200]}
            )
            raise

    def instrumented_task_parse(output, task, parser, unique_pairs):
        try:
            result = original_task_parse(output, task, parser, unique_pairs)
            semantic_valid = None
            if task == "author" and result.get("proposal"):
                try:
                    PackageDraft.model_validate(result["proposal"])
                    semantic_valid = True
                except ValueError:
                    semantic_valid = False
            stage["semantic"].append(semantic_valid)
            stage["parse"].append(
                {"valid": True, "has_proposal": result.get("proposal") is not None}
            )
            return result
        except ValueError as exc:
            stage["semantic"].append(False)
            stage["parse"].append(
                {
                    "valid": False,
                    "category": getattr(exc, "code", type(exc).__name__),
                    "detail": str(exc)[:1200],
                }
            )
            raise

    studio_transport.request = instrumented_request
    studio.public_reply = instrumented_parse
    studio_inference.parse_reply = instrumented_task_parse
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("")
    try:
        for name in args.cases:
            for attempt in range(args.attempts):
                stage = {"calls": [], "parse": [], "semantic": []}
                start = time.monotonic()
                async with SessionLocal() as db:
                    snapshot = await build(db, gid) if name in {"progress", "focus"} else None
                    before = [
                        await db.scalar(select(func.count()).select_from(model))
                        for model in (Goal, Todo)
                    ]
                    session = await studio.start(
                        db,
                        StudioSessionIn(
                            client_uuid=uuid4(), mode="living", goal_id=gid if snapshot else None
                        ),
                    )
                    row = await studio.get_session(db, session.id)
                    await studio.turn(
                        db, row, StudioTurnIn(client_uuid=uuid4(), message=CASES[name])
                    )
                    state = await studio.out(db, row)
                    timed_out = False
                    while state.state in {"running", "unknown_delivery"}:
                        if time.monotonic() - start > args.timeout:
                            timed_out = True
                            await studio.stop(db, row)
                            state = await studio.out(db, row)
                            break
                        await asyncio.sleep(1)
                        row = await studio.get_session(db, session.id)
                        state = await studio.reconcile(db, row)
                    final = state.revision.proposal if state.revision else None
                    discussion = (
                        state.messages[-1]["text"]
                        if state.messages and state.messages[-1]["role"] == "assistant"
                        else ""
                    )
                    after = [
                        await db.scalar(select(func.count()).select_from(model))
                        for model in (Goal, Todo)
                    ]
                    assert before == after, "Unapproved inference must not write Goal/Todo records"
                    turns = list(row.data.get("turns", {}).values())
                    repair = any(t.get("repair_attempted") for t in turns)
                    valid = (
                        bool(final)
                        if not snapshot
                        else bool(discussion and not state.error and final is None)
                    )
                    result = {
                        "scenario": name,
                        "attempt": attempt + 1,
                        "request": CASES[name],
                        "session_id": str(session.id),
                        "state": state.state,
                        "error": state.error,
                        "seconds": round(time.monotonic() - start, 2),
                        "timeout": timed_out,
                        "format_valid": bool(stage["parse"] and stage["parse"][-1]["valid"]),
                        "compiled": bool(final),
                        "applicable": valid,
                        "useful": useful(name, final, discussion, snapshot),
                        "first_attempt_applicable": valid and not repair,
                        "repair_attempted": repair,
                        "repair_success": valid and repair,
                        "discussion": discussion,
                        "canonical_snapshot": snapshot,
                        "diagnostics": stage,
                    }
                    result["turn_diagnostics"] = turns[-1].get("diagnostics", []) if turns else []
                    result["semantic_valid"] = (
                        bool(stage["semantic"] and stage["semantic"][-1]) if not snapshot else None
                    )
                    result["first_semantic_valid"] = (
                        bool(
                            stage["parse"]
                            and stage["parse"][0]["valid"]
                            and stage["semantic"]
                            and stage["semantic"][0]
                        )
                        if not snapshot
                        else None
                    )
                    with output.open("a") as stream:
                        stream.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
                    print(
                        json.dumps(
                            {
                                k: result[k]
                                for k in (
                                    "scenario",
                                    "attempt",
                                    "state",
                                    "seconds",
                                    "format_valid",
                                    "compiled",
                                    "useful",
                                    "repair_attempted",
                                    "timeout",
                                )
                            }
                        ),
                        flush=True,
                    )
    finally:
        studio_transport.request = original_request
        studio.public_reply = original_parse
        studio_inference.parse_reply = original_task_parse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempts", type=int, choices=range(1, 11), default=2)
    parser.add_argument("--cases", nargs="+", choices=list(CASES), default=list(CASES))
    parser.add_argument("--timeout", type=int, choices=range(30, 181), default=120)
    parser.add_argument("--output", required=True)
    asyncio.run(evaluate(parser.parse_args()))
