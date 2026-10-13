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
from contextlib import suppress
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select

from app.config import settings
from app.core.models import Entity
from app.db import SessionLocal
from app.modules.goal import (
    roadmap,
    semantic_pipeline,
    semantic_planning,
    service,
    strategy,
    studio,
    studio_inference,
    studio_transport,
)
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

CASES.update(
    {
        "document": "Yarın önemli bir belgeyi teslim etmek istiyorum.",
        "python": "Üç ay içinde temel Python öğrenmek ve küçük bir uygulama yazmak istiyorum.",
        "mixed": "İş görüşmelerine hazırlanmak ve portföyümdeki projeleri düzenlemek istiyorum.",
        "long_term": "Beş yılda akademik kariyerimi geliştirmek istiyorum.",
        "revision_one": "Bir yeni görev ekle: sonuç belgesini incele.",
        "revision_two": "İki yeni görev ekleyebilir miyiz?",
        "revision_topic": "Gramer bölümüne bir konu ekle.",
        "revision_resource": "Zamanlar konusuna bir alıştırma kaynağı ihtiyacı ekle.",
        "revision_attach": "Kanonik ek kontrol görevini bu hedefe bağla.",
        "revision_move": "İlk çalışmayı yarına taşı.",
        "revision_reduce": "Çalışmaları biraz azaltabilir misin?",
        "revision_detach": "Eksikleri listele işini yol haritasından çıkar.",
        "revision_rename": "Gramer aşamasının adını Dil pratiği yap.",
        "revision_replan": "Önümüzdeki hafta ne yapacağımızı yeniden planlayalım.",
    }
)
HOLDOUT = {
    "yds": "Yabancı dil sınavında 55 ve üzerini hedefliyorum; her gün 120 dakika ayıracağım.",
    "software": "forkOS'un ikinci sürümünü çıkarmadan önce eksik testleri yazıp çalıştırmak, hataları gidermek ve dağıtım paketini hazırlamak istiyorum.",
    "passport": "Pasaport müracaatımı sonuçlandırmak için yapılacakları düzenle; doğrulanmamış koşulları kesin bilgi gibi yazma.",
    "document": "Önemli evrakımı yarına kadar teslim etmem gerekiyor, kısa bir iş listesi hazırlar mısın?",
    "python": "Üç ay sonra basit bir Python programı geliştirebilmek istiyorum; temelden öğrenmeye ihtiyacım var.",
    "mixed": "Mülakat pratiği yapmak ve portföy projelerimin sunumunu iyileştirmek için birlikte bir plan istiyorum.",
    "long_term": "Önümüzdeki beş yılda akademik ilerlememe yön verecek dönemli bir hedef istiyorum.",
    "progress": "Kaydettiğim işler açısından şu anki durumumu özetler misin?",
    "focus": "Sıradaki çalışma olarak hangisine zaman ayırmam daha mantıklı?",
    "revision_one": "Bu aşamaya bir deneme daha ekleyelim.",
    "revision_two": "Mevcut plana tam iki ilave iş öner.",
    "revision_topic": "Gramer bölümünde yeni bir öğrenme konusu da olsun.",
    "revision_resource": "Zamanlar için uygun bir kaynak bulma ihtiyacını ekleyelim.",
    "revision_attach": "Mevcut Kanonik ek kontrol işini hedefin yol haritasına bağlayalım.",
    "revision_move": "İlk çalışmanın gününü yarın olarak değiştirelim.",
    "revision_reduce": "Planı biraz hafiflet.",
    "revision_detach": "Eksikleri listele adımını bu hedeften ayırabilir miyiz?",
    "revision_rename": "Gramer aşamasını Dil pratiği diye yeniden adlandıralım.",
    "revision_replan": "Gelecek haftanın çalışmalarını yeniden düzenleyebilir misin?",
}


async def revision_fixture(db):
    from app.core.time import local_today
    from app.modules.learning import service as learning
    from app.modules.learning.schemas import AreaIn, TopicIn
    from app.modules.todo.schemas import PlanSlotIn

    goal = await service.create_goal(db, GoalIn(title="Sentetik revizyon " + str(uuid4())[:8]))
    gid = goal.id
    phase = await roadmap.save_node(db, gid, NodeData(title="Gramer", kind="phase"))
    phase_id = phase.id
    area = await learning.create_area(db, AreaIn(title="Sentetik çalışma " + str(uuid4())[:8]))
    topic = await learning.create_topic(db, TopicIn(area_id=area["id"], title="Zamanlar"))
    await roadmap.save_node(
        db,
        gid,
        NodeData(title="Zamanlar", kind="record"),
        target_id=topic["id"],
        parent_id=phase_id,
    )
    for index, title in enumerate(("İlk çalışma", "Eksikleri listele")):
        task = await todos.create(db, TodoIn(title=title))
        await roadmap.save_node(
            db, gid, NodeData(title=title, kind="record"), target_id=task.id, parent_id=phase_id
        )
        await db.commit()
        await todos.schedule(
            db,
            PlanSlotIn(
                entity_id=task.id,
                day=local_today() + timedelta(days=index * 2),
                duration_min=25,
            ),
        )
    return gid


async def seed(db):
    extra = await db.scalar(
        select(Entity).where(Entity.type == "todo", Entity.title == "Kanonik ek kontrol")
    )
    if not extra:
        await todos.create(db, TodoIn(title="Kanonik ek kontrol"))
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
    if args.semantic:
        settings.goal_studio_semantic_enabled = True
    status = await studio_transport.status()
    if status.state != "ready" or not status.local or not status.tools_verified:
        raise SystemExit("A verified, tool-free, authorized local Hermes profile is required")
    async with SessionLocal() as db:
        gid, _ = await seed(db)
    original_request = studio_transport.request
    original_parse = studio.public_reply
    original_task_parse = studio_inference.parse_reply
    original_accept = semantic_pipeline.accept
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

    def instrumented_accept(data, prior, output, unique_pairs):
        name = prior["pipeline"]["stage"]
        item = {"stage": name, "json_valid": False, "schema_valid": False, "gate_valid": False}
        stage.setdefault("stages", []).append(item)
        try:
            value = semantic_pipeline.normalized_stage_value(
                semantic_pipeline._json(output, unique_pairs), prior["pipeline"]
            )
            item["json_valid"] = True
            schema = {
                "route": semantic_pipeline.Route,
                "requirements": semantic_planning.Requirements,
                "draft": semantic_planning.SemanticDraft,
                "revision": semantic_planning.SemanticRevision,
                "coach": semantic_planning.CoachingReply,
            }.get(name)
            if name == "review":
                schema = (
                    semantic_pipeline.CoachingReview
                    if prior["pipeline"].get("coaching")
                    or prior["pipeline"].get("semantic_revision")
                    else semantic_planning.QualityReview
                )
            schema.model_validate(value)
            item["schema_valid"] = True
            accepted = original_accept(data, prior, output, unique_pairs)
            item["gate_valid"] = True
            return accepted
        except ValueError as exc:
            item.update(category=getattr(exc, "code", type(exc).__name__), detail=str(exc)[:1200])
            raise

    studio_transport.request = instrumented_request
    studio.public_reply = instrumented_parse
    studio_inference.parse_reply = instrumented_task_parse
    semantic_pipeline.accept = instrumented_accept
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.touch(exist_ok=False)
    try:
        for name in args.cases:
            for attempt in range(args.attempts):
                stage = {"calls": [], "parse": [], "semantic": [], "stages": []}
                start = time.monotonic()
                async with SessionLocal() as db:
                    is_revision = name.startswith("revision_")
                    current_goal = await revision_fixture(db) if is_revision else gid
                    snapshot = (
                        await build(db, current_goal)
                        if name in {"progress", "focus"} or is_revision
                        else None
                    )
                    message = HOLDOUT[name] if args.holdout else CASES[name]
                    before = [
                        await db.scalar(select(func.count()).select_from(model))
                        for model in (Goal, Todo)
                    ]
                    session = await studio.start(
                        db,
                        StudioSessionIn(
                            client_uuid=uuid4(),
                            mode="living",
                            goal_id=current_goal if snapshot else None,
                            long_term=name == "long_term",
                        ),
                    )
                    row = await studio.get_session(db, session.id)
                    await studio.turn(db, row, StudioTurnIn(client_uuid=uuid4(), message=message))
                    state = await studio.out(db, row)
                    timed_out = False
                    while state.state in {"running", "unknown_delivery"}:
                        if time.monotonic() - start > args.timeout:
                            timed_out = True
                            with suppress(HTTPException):
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
                        if not snapshot or is_revision
                        else bool(discussion and not state.error and final is None)
                    )
                    result = {
                        "scenario": name,
                        "attempt": attempt + 1,
                        "request": message,
                        "session_id": str(session.id),
                        "state": state.state,
                        "error": state.error,
                        "seconds": round(time.monotonic() - start, 2),
                        "timeout": timed_out,
                        "format_valid": bool(stage["parse"] and stage["parse"][-1]["valid"]),
                        "compiled": bool(final),
                        "applicable": valid,
                        "useful": useful(name, final, discussion, snapshot)
                        if name in {"yds", "software", "passport"}
                        else valid,
                        "cohort": "holdout" if args.holdout else "fixed",
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
                    pipeline = turns[-1].get("pipeline", {}) if turns else {}
                    result["pipeline"] = pipeline
                    result["facts"] = state.messages[-1].get("facts") if state.messages else None
                    stages = stage["stages"]
                    result["format_valid"] = (
                        bool(stages and stages[-1]["schema_valid"])
                        if pipeline
                        else result["format_valid"]
                    )
                    result["planning_intent_valid"] = (
                        any(x["stage"] == "requirements" and x["schema_valid"] for x in stages)
                        if not snapshot
                        else None
                    )
                    result["semantic_valid"] = (
                        any(x["stage"] in {"draft", "revision"} and x["gate_valid"] for x in stages)
                        if not snapshot or is_revision
                        else None
                    )
                    result["reference_resolution"] = result["semantic_valid"]
                    result["first_semantic_valid"] = (
                        next(
                            (
                                x["gate_valid"]
                                for x in stages
                                if x["stage"] in {"draft", "revision"}
                            ),
                            False,
                        )
                        if not snapshot or is_revision
                        else None
                    )
                    result["inference_calls"] = len(stage["calls"])
                    result["capability_selection"] = pipeline.get("requirements", {}).get("needs")
                    result["semantic_draft"] = pipeline.get("semantic_draft") or pipeline.get(
                        "semantic_revision"
                    )
                    result["semantic_pipeline_enabled"] = settings.goal_studio_semantic_enabled
                    result["operator_review"] = None
                    result["quality_proxy"] = result.pop("useful")
                    result["runtime_capabilities"] = studio_transport.generation_capabilities()
                    result["token_usage"] = {
                        key: sum((c.get("usage") or {}).get(key, 0) or 0 for c in stage["calls"])
                        for key in ("input_tokens", "output_tokens", "total_tokens")
                    }
                    result["input_bytes"] = sum(
                        c.get("input_bytes", 0) + c.get("instruction_bytes", 0)
                        for c in stage["calls"]
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
                                    "quality_proxy",
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
        semantic_pipeline.accept = original_accept


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempts", type=int, choices=range(1, 11), default=2)
    parser.add_argument("--cases", nargs="+", choices=list(CASES), default=list(CASES))
    parser.add_argument("--timeout", type=int, choices=range(30, 181), default=120)
    parser.add_argument("--holdout", action="store_true")
    parser.add_argument(
        "--semantic",
        action="store_true",
        help="Explicitly opt into the experimental semantic pipeline",
    )
    parser.add_argument("--output", required=True)
    asyncio.run(evaluate(parser.parse_args()))
