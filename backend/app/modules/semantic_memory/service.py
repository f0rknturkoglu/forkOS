"""A4: Semantic Memory servis katmanı.

Aday yönetimi, inceleme (confirm/reject) ve kontrollü terfi (promote).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import log_event
from app.integrations.obsidian import hot_memory as hot_storage
from app.integrations.obsidian import semantic_memory as sem_storage
from app.modules.agent_episode.models import AgentSessionEpisode, AgentSessionEpisodeItem
from app.modules.semantic_memory.models import AgentSemanticCandidate
from app.modules.semantic_memory.policy import (
    compute_candidate_key,
    compute_candidate_revision,
    is_privacy_blocked,
    resolve_destination,
)
from app.modules.semantic_memory.schemas import (
    CandidateKind,
    CandidateStatus,
    PrimaryEvidenceClass,
    SemanticCandidateConfirmIn,
    SemanticCandidateListResponse,
    SemanticCandidatePromoteIn,
    SemanticCandidatePromoteOut,
    SemanticCandidateRead,
    SemanticCandidateRefreshIn,
    SemanticCandidateRefreshOut,
    SemanticCandidateRejectIn,
    SemanticStatusOut,
    SuggestedDestination,
)


def _to_read(c: AgentSemanticCandidate) -> SemanticCandidateRead:
    return SemanticCandidateRead.model_validate(c)


async def list_candidates(
    session: AsyncSession,
    *,
    status: str | None = None,
    kind: str | None = None,
    destination: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> SemanticCandidateListResponse:
    """Kayıtlı semantik adayları listeler ve durum sayılarını döner."""
    query = select(AgentSemanticCandidate)
    if status:
        query = query.where(AgentSemanticCandidate.status == status)
    if kind:
        query = query.where(AgentSemanticCandidate.kind == kind)
    if destination:
        query = query.where(AgentSemanticCandidate.suggested_destination == destination)

    query = query.order_by(AgentSemanticCandidate.last_seen_at.desc(), AgentSemanticCandidate.id.desc())
    query = query.offset(offset).limit(limit)

    rows = (await session.execute(query)).scalars().all()
    items = [_to_read(r) for r in rows]

    # Durum sayıları
    counts_query = select(AgentSemanticCandidate.status, func.count(AgentSemanticCandidate.id)).group_by(
        AgentSemanticCandidate.status
    )
    counts_result = await session.execute(counts_query)
    status_counts = dict(counts_result.all())

    total = sum(status_counts.values())

    return SemanticCandidateListResponse(
        items=items,
        total=total,
        status_counts=status_counts,
    )


async def get_candidate(session: AsyncSession, candidate_id: uuid.UUID) -> AgentSemanticCandidate:
    row = (
        await session.execute(
            select(AgentSemanticCandidate).where(AgentSemanticCandidate.id == candidate_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "SEMANTIC_CANDIDATE_NOT_FOUND", "message": "Aday bulunamadı"},
        )
    return row


async def refresh_candidates(
    session: AsyncSession, payload: SemanticCandidateRefreshIn
) -> SemanticCandidateRefreshOut:
    """Mühürlenmiş epizodik oturum maddelerinden ve kanonik kaynaklardan adayları tazeler."""
    created_count = 0
    updated_count = 0

    if payload.include_episodes:
        # Mühürlenmiş epizot maddelerini çek
        ep_query = (
            select(AgentSessionEpisodeItem, AgentSessionEpisode)
            .join(AgentSessionEpisode, AgentSessionEpisodeItem.episode_id == AgentSessionEpisode.id)
            .where(AgentSessionEpisode.status.in_(("sealed", "sealed_degraded")))
            .order_by(AgentSessionEpisodeItem.created_at.desc())
            .limit(payload.limit)
        )
        results = (await session.execute(ep_query)).all()

        for ep_item, ep in results:
            stmt = (ep_item.text or "").strip()
            if not stmt:
                continue

            # Gizlilik vetosu
            if is_privacy_blocked(stmt):
                continue

            # Tür eşlemesi
            ep_kind = ep_item.kind
            mapped_kind: CandidateKind = "reference"
            if ep_kind == "session_decision":
                mapped_kind = "decision"
            elif ep_kind == "next_focus":
                mapped_kind = "goal"
            elif ep_kind == "open_thread":
                mapped_kind = "constraint"
            elif ep_kind == "topic":
                mapped_kind = "project_knowledge" if ep.scope_project else "reference"
            elif ep_kind == "outcome":
                mapped_kind = "lesson"

            # Kanıt sınıflandırması ve başlangıç durumu
            source_role = ep_item.source_role
            evidence_class: PrimaryEvidenceClass = "episode_derived"
            initial_status: CandidateStatus = "needs_review"

            if source_role == "user":
                evidence_class = "explicit_user"
                initial_status = "ready"
            elif source_role == "assistant":
                evidence_class = "model_derived"
                initial_status = "needs_review"

            scope = "project" if ep.scope_project else "global"
            scope_project = ep.scope_project
            candidate_key = compute_candidate_key(mapped_kind, scope, scope_project, None, stmt)

            # Mevcut adayı kontrol et
            existing = (
                await session.execute(
                    select(AgentSemanticCandidate).where(
                        AgentSemanticCandidate.candidate_key == candidate_key
                    )
                )
            ).scalar_one_or_none()

            now = datetime.now(UTC)
            ref_entry = {
                "ref": f"episode_item:{ep_item.id}",
                "role": source_role,
                "digest": ep_item.evidence_digest,
            }

            if existing is not None:
                # Güncelle
                existing.recurrence_count += 1
                existing.last_seen_at = now
                if ref_entry not in existing.evidence_refs:
                    existing.evidence_refs = [*existing.evidence_refs, ref_entry]
                if existing.status == "stale":
                    existing.status = initial_status
                existing.revision = compute_candidate_revision(
                    existing.id,
                    existing.candidate_key,
                    existing.status,
                    existing.recurrence_count,
                    existing.last_seen_at,
                )
                updated_count += 1
            else:
                cand_id = uuid.uuid4()
                dest = resolve_destination(mapped_kind, scope, scope_project)
                revision = compute_candidate_revision(cand_id, candidate_key, initial_status, 1, now)
                candidate = AgentSemanticCandidate(
                    id=cand_id,
                    candidate_key=candidate_key,
                    kind=mapped_kind,
                    statement=stmt,
                    scope=scope,
                    scope_project=scope_project,
                    subject_key=None,
                    domains=[],
                    suggested_destination=dest,
                    primary_evidence_class=evidence_class,
                    evidence_refs=[ref_entry],
                    observed_at=ep_item.created_at,
                    status=initial_status,
                    reviewed_by=None,
                    possible_related_card_ids=[],
                    warnings=[],
                    recurrence_count=1,
                    first_seen_at=now,
                    last_seen_at=now,
                    revision=revision,
                )
                session.add(candidate)
                created_count += 1

    await session.commit()

    total_query = select(func.count(AgentSemanticCandidate.id))
    total = (await session.execute(total_query)).scalar_one()

    return SemanticCandidateRefreshOut(
        created_count=created_count,
        updated_count=updated_count,
        total_candidates=total,
    )


async def confirm_candidate(
    session: AsyncSession, candidate_id: uuid.UUID, payload: SemanticCandidateConfirmIn
) -> SemanticCandidateRead:
    """Adayı kullanıcı tarafından onaylanmış ('ready') olarak işaretler."""
    candidate = await get_candidate(session, candidate_id)

    if candidate.revision != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SEMANTIC_REVISION_MISMATCH",
                "message": "Aday revizyonu eşleşmiyor; lütfen sayfayı yenileyin",
            },
        )

    candidate.status = "ready"
    candidate.reviewed_by = "user"
    candidate.last_seen_at = datetime.now(UTC)
    candidate.revision = compute_candidate_revision(
        candidate.id,
        candidate.candidate_key,
        candidate.status,
        candidate.recurrence_count,
        candidate.last_seen_at,
    )

    await session.commit()
    await session.refresh(candidate)
    return _to_read(candidate)


async def reject_candidate(
    session: AsyncSession, candidate_id: uuid.UUID, payload: SemanticCandidateRejectIn
) -> SemanticCandidateRead:
    """Adayı reddeder ('rejected')."""
    candidate = await get_candidate(session, candidate_id)

    if candidate.revision != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SEMANTIC_REVISION_MISMATCH",
                "message": "Aday revizyonu eşleşmiyor; lütfen sayfayı yenileyin",
            },
        )

    candidate.status = "rejected"
    candidate.reviewed_by = "user"
    candidate.last_seen_at = datetime.now(UTC)
    candidate.revision = compute_candidate_revision(
        candidate.id,
        candidate.candidate_key,
        candidate.status,
        candidate.recurrence_count,
        candidate.last_seen_at,
    )

    await session.commit()
    await session.refresh(candidate)
    return _to_read(candidate)


async def promote_candidate(
    session: AsyncSession, candidate_id: uuid.UUID, payload: SemanticCandidatePromoteIn
) -> SemanticCandidatePromoteOut:
    """Adayı kalıcı bilgiye terfi ettirir (durable vault veya hot memory)."""
    candidate = await get_candidate(session, candidate_id)

    # İdempotent: zaten terfi etmişse
    if candidate.status == "promoted":
        return SemanticCandidatePromoteOut(
            status="promoted",
            card_id=None,
            relative_path=None,
            destination=candidate.suggested_destination,
            revision=candidate.revision,
        )

    if candidate.revision != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SEMANTIC_REVISION_MISMATCH",
                "message": "Aday revizyonu eşleşmiyor; lütfen sayfayı yenileyin",
            },
        )

    # Katı Epistemik Kapı: explicit_user olmayan veya onaylanmamış aday terfi edemez!
    if candidate.primary_evidence_class != "explicit_user" and candidate.status != "ready":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "SEMANTIC_REVIEW_REQUIRED",
                "message": "Bu adayın terfi edebilmesi için kullanıcı tarafından onaylanması (confirm) gerekir.",
            },
        )

    dest = payload.target_destination or candidate.suggested_destination

    card_id: str | None = None
    rel_path: str | None = None

    if dest == "durable_vault":
        try:
            root = sem_storage.writable_root()
        except sem_storage.SemanticStorageError as exc:
            raise HTTPException(
                status_code=503,
                detail={"code": exc.code, "message": str(exc)},
            ) from exc

        card_uuid = str(uuid.uuid4())
        title = candidate.statement[:80].strip()
        supersedes_list = payload.supersedes or []

        try:
            card = sem_storage.create_semantic_card(
                root,
                card_id=card_uuid,
                kind=candidate.kind,  # type: ignore[arg-type]
                title=title,
                statement=candidate.statement,
                scope=candidate.scope,  # type: ignore[arg-type]
                scope_project=candidate.scope_project,
                domains=candidate.domains,
                primary_evidence_class=candidate.primary_evidence_class,  # type: ignore[arg-type]
                evidence_refs=candidate.evidence_refs,
                supersedes=supersedes_list,
                conditions=candidate.conditions,
                exceptions=candidate.exceptions,
                sensitivity=candidate.sensitivity,  # type: ignore[arg-type]
                remote_allowed=candidate.remote_allowed,
            )
            card_id = card.card_id
            rel_path = card.relative_path
        except sem_storage.SemanticStorageError as exc:
            raise HTTPException(
                status_code=400,
                detail={"code": exc.code, "message": str(exc)},
            ) from exc

    elif dest == "hot_memory":
        try:
            root = hot_storage.writable_root()
        except hot_storage.HotMemoryError as exc:
            raise HTTPException(
                status_code=503,
                detail={"code": exc.code, "message": str(exc)},
            ) from exc

        # H2 Hot Memory türleri: profile, preference, goal, constraint, decision, correction
        h2_kind = candidate.kind if candidate.kind in hot_storage.KINDS else "preference"
        title = candidate.statement[:80].strip()

        try:
            mem = hot_storage.create_memory(
                root,
                kind=h2_kind,  # type: ignore[arg-type]
                title=title,
                text=candidate.statement,
                source_mode="approved_candidate",
            )
            card_id = mem.memory_id
            rel_path = mem.relative_path
        except hot_storage.HotMemoryError as exc:
            raise HTTPException(
                status_code=400,
                detail={"code": exc.code, "message": str(exc)},
            ) from exc

    # Durumu güncelle
    candidate.status = "promoted"
    candidate.last_seen_at = datetime.now(UTC)
    candidate.revision = compute_candidate_revision(
        candidate.id,
        candidate.candidate_key,
        candidate.status,
        candidate.recurrence_count,
        candidate.last_seen_at,
    )

    await log_event(
        session,
        verb="semantic_candidate.promoted",
        entity_id=None,
        payload={
            "candidate_id": str(candidate.id),
            "destination": dest,
            "card_id": card_id,
            "relative_path": rel_path,
            "kind": candidate.kind,
        },
    )

    await session.commit()
    await session.refresh(candidate)

    return SemanticCandidatePromoteOut(
        status="promoted",
        card_id=card_id,
        relative_path=rel_path,
        destination=dest,
        revision=candidate.revision,
    )


async def get_status(session: AsyncSession) -> SemanticStatusOut:
    """Semantik hafıza durumu ve istatistiklerini döner."""
    counts_query = select(AgentSemanticCandidate.status, func.count(AgentSemanticCandidate.id)).group_by(
        AgentSemanticCandidate.status
    )
    counts_result = await session.execute(counts_query)
    status_counts = dict(counts_result.all())

    total = sum(status_counts.values())

    durable_card_count = 0
    root = sem_storage.readable_root()
    if root is not None and root.exists():
        cards = sem_storage.scan_semantic_cards(root)
        durable_card_count = len([c for c in cards if c.effective_status == "active"])

    return SemanticStatusOut(
        total_candidates=total,
        proposed_count=status_counts.get("proposed", 0),
        needs_review_count=status_counts.get("needs_review", 0),
        ready_count=status_counts.get("ready", 0),
        promoted_count=status_counts.get("promoted", 0),
        rejected_count=status_counts.get("rejected", 0),
        durable_card_count=durable_card_count,
    )
