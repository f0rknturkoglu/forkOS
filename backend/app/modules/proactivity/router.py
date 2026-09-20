"""H6 kontrol uclari — inceleme, konfigurasyon ve kullanici override'i.

Bu uclar GENEL bir otomasyon yurutucusu DEGILDIR: kapali bir islem kumesi
(incele / ayarla / snooze / gecmis) sunar. H6 hicbir canonical kaydi
(Todo/Project/Opportunity/Vault/Review) degistirmez.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.proactivity import service
from app.modules.proactivity.schemas import (
    ProactivityConfigIn,
    ProactivityRuleIn,
    ProactivityRuleOut,
    ProactivityRunOut,
    ProactivityStatusOut,
    SnoozeIn,
)

router = APIRouter()


def _error(exc: service.ProactivityError) -> HTTPException:
    status = 404 if exc.code == "RUN_NOT_FOUND" else 422
    return HTTPException(status_code=status, detail=f"{exc.code}: {exc.message}")


@router.get("/proactivity/status", response_model=ProactivityStatusOut)
async def get_status(session: AsyncSession = Depends(get_session)) -> ProactivityStatusOut:
    return ProactivityStatusOut.model_validate(await service.status(session))


@router.put("/proactivity/config", response_model=ProactivityStatusOut)
async def put_config(
    data: ProactivityConfigIn, session: AsyncSession = Depends(get_session)
) -> ProactivityStatusOut:
    try:
        await service.configure(
            session,
            enabled=data.enabled,
            quiet_hours_start=data.quiet_hours_start,
            quiet_hours_end=data.quiet_hours_end,
            focus_deferral_enabled=data.focus_deferral_enabled,
            digest_time=data.digest_time,
        )
    except service.ProactivityError as exc:
        raise _error(exc) from exc
    await session.commit()
    return ProactivityStatusOut.model_validate(await service.status(session))


@router.get("/proactivity/rules", response_model=list[ProactivityRuleOut])
async def get_rules(session: AsyncSession = Depends(get_session)) -> list[ProactivityRuleOut]:
    await service.seed_rules(session)
    await session.commit()
    rules = await service.list_rules(session)
    return [
        ProactivityRuleOut(
            kind=rule.kind,
            version=rule.version,
            logical_key=rule.logical_key,
            enabled=rule.enabled,
            config=rule.config,
            snoozed_until=rule.snoozed_until,
        )
        for rule in rules
    ]


@router.put("/proactivity/rules/{kind}", response_model=ProactivityRuleOut)
async def put_rule(
    kind: str, data: ProactivityRuleIn, session: AsyncSession = Depends(get_session)
) -> ProactivityRuleOut:
    try:
        rule = await service.rule_set(
            session,
            kind=kind,
            enabled=data.enabled,
            config=data.config,
            scope_entity_id=data.scope_entity_id,
        )
    except service.ProactivityError as exc:
        raise _error(exc) from exc
    await session.commit()
    return ProactivityRuleOut(
        kind=rule.kind,
        version=rule.version,
        logical_key=rule.logical_key,
        enabled=rule.enabled,
        config=rule.config,
        snoozed_until=rule.snoozed_until,
    )


@router.get("/proactivity/history", response_model=list[ProactivityRunOut])
async def get_history(
    limit: int = Query(default=50, ge=1, le=service.MAX_HISTORY_RETURN),
    session: AsyncSession = Depends(get_session),
) -> list[ProactivityRunOut]:
    return [
        ProactivityRunOut.model_validate(item)
        for item in await service.history(session, limit=limit)
    ]


@router.post("/proactivity/runs/{run_id}/snooze", response_model=list[ProactivityRunOut])
async def snooze_run(
    run_id: int, data: SnoozeIn, session: AsyncSession = Depends(get_session)
) -> list[ProactivityRunOut]:
    try:
        await service.snooze(session, until=data.until, run_id=run_id)
    except service.ProactivityError as exc:
        raise _error(exc) from exc
    await session.commit()
    return [
        ProactivityRunOut.model_validate(item)
        for item in await service.history(session, limit=service.MAX_HISTORY_RETURN)
    ]


@router.delete("/proactivity/runs/{run_id}/snooze", response_model=list[ProactivityRunOut])
async def unsnooze_run(
    run_id: int, session: AsyncSession = Depends(get_session)
) -> list[ProactivityRunOut]:
    try:
        await service.unsnooze(session, run_id=run_id)
    except service.ProactivityError as exc:
        raise _error(exc) from exc
    await session.commit()
    return [
        ProactivityRunOut.model_validate(item)
        for item in await service.history(session, limit=service.MAX_HISTORY_RETURN)
    ]


@router.post("/proactivity/rules/{kind}/snooze", response_model=list[ProactivityRuleOut])
async def snooze_rule(
    kind: str, data: SnoozeIn, session: AsyncSession = Depends(get_session)
) -> list[ProactivityRuleOut]:
    """Kural duzeyinde override: "bu hafta dürtme" (§26/§108)."""
    try:
        await service.snooze(session, until=data.until, kind=kind)
    except service.ProactivityError as exc:
        raise _error(exc) from exc
    await session.commit()
    rules = await service.list_rules(session)
    return [
        ProactivityRuleOut(
            kind=rule.kind,
            version=rule.version,
            logical_key=rule.logical_key,
            enabled=rule.enabled,
            config=rule.config,
            snoozed_until=rule.snoozed_until,
        )
        for rule in rules
    ]
