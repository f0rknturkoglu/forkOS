"""A4: Semantic Memory servis katmanı.

Aday yönetimi, inceleme (confirm/reject) ve kontrollü terfi (promote).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import log_event
from app.core.models import Entity, Event
from app.integrations.obsidian import hot_memory as hot_storage
from app.integrations.obsidian import semantic_memory as sem_storage
from app.modules.agent_episode.models import AgentSessionEpisodeItem, AgentSessionEpisodeTurn
from app.modules.semantic_memory.models import AgentSemanticCandidate
from app.modules.semantic_memory.policy import (
    compute_candidate_key,
    compute_candidate_revision,
    is_privacy_blocked,
    normalize_statement,
    resolve_destination,
)
from app.modules.semantic_memory.schemas import (
    CandidateKind,
    CandidateStatus,
    PrimaryEvidenceClass,
    RelatedSemanticCard,
    SemanticCandidateConfirmIn,
    SemanticCandidateListResponse,
    SemanticCandidatePromoteIn,
    SemanticCandidatePromoteOut,
    SemanticCandidateRead,
    SemanticCandidateRefreshIn,
    SemanticCandidateRefreshOut,
    SemanticCandidateRejectIn,
    SemanticStatusOut,
)


def _to_read(
    c: AgentSemanticCandidate, cards: list[sem_storage.SemanticMemoryCard] | None = None
) -> SemanticCandidateRead:
    view = SemanticCandidateRead.model_validate(c)
    if cards:
        by_id = {card.card_id: card for card in cards if card.effective_status == "active"}
        view.possible_related_cards = [
            RelatedSemanticCard(card_id=card_id, statement=by_id[card_id].statement)
            for card_id in (c.possible_related_card_ids or [])
            if card_id in by_id
        ]
    return view


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

    query = query.order_by(
        AgentSemanticCandidate.last_seen_at.desc(), AgentSemanticCandidate.id.desc()
    )
    query = query.offset(offset).limit(limit)

    rows = (await session.execute(query)).scalars().all()
    root = sem_storage.readable_root()
    cards = sem_storage.scan_semantic_cards(root) if root is not None else []
    items = [_to_read(r, cards) for r in rows]

    # Durum sayıları
    counts_query = select(
        AgentSemanticCandidate.status, func.count(AgentSemanticCandidate.id)
    ).group_by(AgentSemanticCandidate.status)
    counts_result = await session.execute(counts_query)
    status_counts = dict(counts_result.all())

    total = sum(status_counts.values())

    return SemanticCandidateListResponse(
        items=items,
        total=total,
        status_counts=status_counts,
    )


async def get_candidate(
    session: AsyncSession, candidate_id: uuid.UUID, *, for_update: bool = False
) -> AgentSemanticCandidate:
    query = select(AgentSemanticCandidate).where(AgentSemanticCandidate.id == candidate_id)
    if for_update:
        query = query.with_for_update()
    row = (await session.execute(query)).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "SEMANTIC_CANDIDATE_NOT_FOUND", "message": "Aday bulunamadı"},
        )
    return row


async def _check_promotion_sources(
    session: AsyncSession, candidate: AgentSemanticCandidate
) -> None:
    """Privacy provenance ve desteklenen kanonik ref'leri terfi anında doğrular."""
    async def mark_stale() -> None:
        candidate.status = "stale"
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
            verb="semantic_candidate.stale",
            entity_id=None,
            payload={"candidate_id": str(candidate.id)},
        )
        await session.commit()

    refs = candidate.evidence_refs or []
    for entry in refs:
        ref = str(entry.get("ref") or "")
        family, _, value = ref.partition(":")
        if family == "episode_item":
            try:
                item_id = int(value)
            except ValueError:
                item_id = -1
            row = (
                await session.execute(
                    select(AgentSessionEpisodeItem, AgentSessionEpisodeTurn)
                    .outerjoin(
                        AgentSessionEpisodeTurn,
                        AgentSessionEpisodeItem.episode_turn_id == AgentSessionEpisodeTurn.id,
                    )
                    .where(AgentSessionEpisodeItem.id == item_id)
                )
            ).first()
            if row is None or row[1] is None or not row[1].semantic_memory_eligible:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "SEMANTIC_PRIVACY_BLOCKED",
                        "message": "Bu turun hafızaya alınmasına izin verilmedi",
                    },
                )
            if candidate.primary_evidence_class == "canonical_source":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "SEMANTIC_SOURCE_STALE",
                        "message": "Epizodik kayıt kanonik kaynak değildir",
                    },
                )
            continue
        if candidate.primary_evidence_class != "canonical_source":
            continue
        fresh = False
        if family == "event":
            try:
                event_id = int(value)
            except ValueError:
                event_id = -1
            event = await session.get(Event, event_id)
            if event is not None:
                fresh = event.entity_id is None or (
                    (entity := await session.get(Entity, event.entity_id)) is not None
                    and entity.archived_at is None
                )
        elif family == "entity":
            try:
                entity = await session.get(Entity, uuid.UUID(value))
                fresh = entity is not None and entity.archived_at is None
            except ValueError:
                pass
        elif family in ("vault", "semantic_memory", "hot_memory"):
            from app.modules.agent_continuity.models import AgentSessionSource
            from app.modules.agent_continuity.service import check_source_freshness

            source = AgentSessionSource(
                source_id=ref,
                source_type={
                    "vault": "vault_note",
                    "semantic_memory": "semantic_memory",
                    "hot_memory": "hot_memory",
                }[family],
            )
            fresh, _ = await check_source_freshness(session, source)
        if not fresh:
            await mark_stale()
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "SEMANTIC_SOURCE_STALE",
                    "message": "Kanonik kaynak artık güncel değil",
                },
            )
    if candidate.primary_evidence_class == "canonical_source" and not refs:
        await mark_stale()
        raise HTTPException(
            status_code=409,
            detail={"code": "SEMANTIC_SOURCE_STALE", "message": "Kanonik kaynak referansı yok"},
        )


async def refresh_candidates(
    session: AsyncSession, payload: SemanticCandidateRefreshIn
) -> SemanticCandidateRefreshOut:
    """H5'in kaynaklı aday çıkarımını A4 inceleme kayıtlarına dönüştürür."""
    from app.integrations.judgment.memory_sources import read_memory_source
    from app.integrations.review_intelligence import consolidation as h5_consolidation
    from app.integrations.review_intelligence import sources as h5_sources
    from app.integrations.review_intelligence.models import Collector

    created_count = 0
    updated_count = 0
    fragments: list[dict[str, Any]] = []
    if payload.include_episodes:
        episodes = await h5_sources.sealed_episode_items(session, limit=payload.limit)
        for item in episodes:
            if (
                not item["semantic_memory_eligible"]
                or item["scope_ambiguous"]
                or is_privacy_blocked(item["text"])
            ):
                continue
            fragments.append(
                {
                    "ref": item["ref"],
                    "text": f"{item['kind']}: {item['text']}",
                    "entity_id": None,
                    "scope_project": item["scope_project"],
                    "role": item.get("source_role"),
                    "digest": item.get("evidence_digest"),
                    "observed_at": item["created_at"],
                }
            )

    if payload.include_events:
        now = datetime.now(UTC)
        events, _ = await h5_sources.meaningful_events(
            session,
            start=now - timedelta(days=30),
            end=now,
            limit=payload.limit,
        )
        for event in events:
            if event.get("entity_id") and event.get("entity_type") != "project":
                continue
            title = str(event.get("title") or event.get("payload", {}).get("title") or "").strip()
            if title:
                fragments.append(
                    {
                        "ref": f"event:{event['id']}",
                        "text": f"{event['verb']}: {title}",
                        "entity_id": event.get("entity_id"),
                        "scope_project": event.get("entity_id")
                        if event.get("entity_type") == "project"
                        else None,
                        "role": "canonical",
                        "digest": None,
                        "observed_at": event["occurred_at"].isoformat(),
                    }
                )

    collector = Collector()
    proposals = await h5_consolidation.extract_promotion_candidates(
        session,
        collector,
        fragments=fragments,
        focus_entity_id=None,
    )
    by_ref = {fragment["ref"]: fragment for fragment in fragments}
    root = sem_storage.readable_root()
    active_cards = (
        [
            card
            for card in sem_storage.scan_semantic_cards(root)
            if card.effective_status == "active"
        ]
        if root is not None
        else []
    )
    for proposal in proposals:
        supports = [by_ref[ref] for ref in proposal.support_refs if ref in by_ref]
        if not supports:
            continue
        scopes = {item.get("scope_project") for item in supports}
        if len(scopes) != 1:
            continue
        scope_project = next(iter(scopes))
        scope = "project" if scope_project else "global"
        kind: CandidateKind = proposal.kind
        if is_privacy_blocked(proposal.text):
            continue
        roles = {item.get("role") for item in supports}
        evidence_class: PrimaryEvidenceClass = (
            "canonical_source"
            if roles == {"canonical"}
            else "explicit_user"
            if roles == {"user"} and all(item.get("digest") for item in supports)
            else "model_derived"
            if roles == {"assistant"}
            else "episode_derived"
        )
        initial_status: CandidateStatus = (
            "ready" if evidence_class in ("explicit_user", "canonical_source") else "needs_review"
        )
        candidate_key = compute_candidate_key(kind, scope, scope_project, None, proposal.text)
        related_ids = [
            card.card_id
            for card in active_cards
            if card.kind == kind
            and card.scope == scope
            and card.scope_project == scope_project
            and card.subject_key is None
            and normalize_statement(card.statement) != normalize_statement(proposal.text)
        ][:3]
        existing = (
            await session.execute(
                select(AgentSemanticCandidate).where(
                    AgentSemanticCandidate.candidate_key == candidate_key
                )
            )
        ).scalar_one_or_none()
        ref_entries = []
        for item in supports:
            source = await read_memory_source(session, item["ref"])
            if source is None or source.text != item["text"]:
                ref_entries = []
                break
            ref_entries.append(
                {
                    "ref": item["ref"],
                    "role": item.get("role"),
                    "digest": item.get("digest"),
                    "source_revision": source.revision,
                }
            )
        if not ref_entries:
            continue
        observed_at = min(datetime.fromisoformat(item["observed_at"]) for item in supports)
        moment = datetime.now(UTC)
        if existing is not None:
            if existing.status in ("promoted", "rejected", "stale"):
                continue
            new_refs = [ref for ref in ref_entries if ref not in existing.evidence_refs]
            if not new_refs:
                continue
            existing.evidence_refs = [*existing.evidence_refs, *new_refs]
            existing.possible_related_card_ids = related_ids
            existing.recurrence_count += len(new_refs)
            existing.last_seen_at = moment
            existing.revision = compute_candidate_revision(
                existing.id,
                existing.candidate_key,
                existing.status,
                existing.recurrence_count,
                existing.last_seen_at,
            )
            updated_count += 1
            continue
        cand_id = uuid.uuid4()
        session.add(
            AgentSemanticCandidate(
                id=cand_id,
                candidate_key=candidate_key,
                kind=kind,
                statement=proposal.text,
                scope=scope,
                scope_project=scope_project,
                subject_key=None,
                domains=[],
                suggested_destination=resolve_destination(kind, scope, scope_project),
                primary_evidence_class=evidence_class,
                evidence_refs=ref_entries,
                observed_at=observed_at,
                status=initial_status,
                reviewed_by=None,
                possible_related_card_ids=related_ids,
                warnings=list(proposal.warnings),
                recurrence_count=max(len(ref_entries), 1),
                first_seen_at=moment,
                last_seen_at=moment,
                revision=compute_candidate_revision(
                    cand_id, candidate_key, initial_status, max(len(ref_entries), 1), moment
                ),
            )
        )
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
    candidate = await get_candidate(session, candidate_id, for_update=True)

    if candidate.revision != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SEMANTIC_REVISION_MISMATCH",
                "message": "Aday revizyonu eşleşmiyor; lütfen sayfayı yenileyin",
            },
        )

    if candidate.status not in ("proposed", "needs_review", "ready"):
        raise HTTPException(
            status_code=409,
            detail={"code": "SEMANTIC_INVALID_STATE", "message": "Bu aday artık onaylanamaz"},
        )
    if candidate.status == "ready":
        return _to_read(candidate)

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

    await log_event(
        session,
        verb="semantic_candidate.confirmed",
        entity_id=None,
        payload={"candidate_id": str(candidate.id)},
    )
    await session.commit()
    await session.refresh(candidate)
    return _to_read(candidate)


async def reject_candidate(
    session: AsyncSession, candidate_id: uuid.UUID, payload: SemanticCandidateRejectIn
) -> SemanticCandidateRead:
    """Adayı reddeder ('rejected')."""
    candidate = await get_candidate(session, candidate_id, for_update=True)

    if candidate.revision != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SEMANTIC_REVISION_MISMATCH",
                "message": "Aday revizyonu eşleşmiyor; lütfen sayfayı yenileyin",
            },
        )

    if candidate.status not in ("proposed", "needs_review", "ready"):
        raise HTTPException(
            status_code=409,
            detail={"code": "SEMANTIC_INVALID_STATE", "message": "Bu aday artık reddedilemez"},
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

    await log_event(
        session,
        verb="semantic_candidate.rejected",
        entity_id=None,
        payload={"candidate_id": str(candidate.id)},
    )
    await session.commit()
    await session.refresh(candidate)
    return _to_read(candidate)


async def promote_candidate(
    session: AsyncSession, candidate_id: uuid.UUID, payload: SemanticCandidatePromoteIn
) -> SemanticCandidatePromoteOut:
    """Adayı kalıcı bilgiye terfi ettirir (durable vault veya hot memory)."""
    candidate = await get_candidate(session, candidate_id, for_update=True)

    # İdempotent: zaten terfi etmişse
    if candidate.status == "promoted":
        return SemanticCandidatePromoteOut(
            status="already_promoted",
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

    # Evidence class tek başına yetki vermez; tek yasal kaynak durum ready'dir.
    if candidate.status != "ready":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "SEMANTIC_REVIEW_REQUIRED"
                if candidate.status in ("proposed", "needs_review")
                else "SEMANTIC_INVALID_STATE",
                "message": "Yalnız hazır durumdaki aday terfi edebilir",
            },
        )

    await _check_promotion_sources(session, candidate)

    dest = payload.target_destination or candidate.suggested_destination
    if payload.supersedes and dest != "durable_vault":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "SEMANTIC_INVALID_SUPERSESSION",
                "message": "Eski kart yalnız kalıcı kart ile değiştirilebilir",
            },
        )

    if dest in ("operational", "procedural_candidate"):
        return SemanticCandidatePromoteOut(
            status="owner_action_required",
            card_id=None,
            relative_path=None,
            destination=dest,
            revision=candidate.revision,
        )
    if dest == "discard":
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
        await log_event(
            session,
            verb="semantic_candidate.rejected",
            entity_id=None,
            payload={"candidate_id": str(candidate.id), "destination": "discard"},
        )
        await session.commit()
        return SemanticCandidatePromoteOut(
            status="rejected",
            card_id=None,
            relative_path=None,
            destination=dest,
            revision=candidate.revision,
        )

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

        cards = sem_storage.scan_semantic_cards(root)
        supersedes_list = payload.supersedes or []
        if len(supersedes_list) != len(set(supersedes_list)) or len(supersedes_list) > 1:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "SEMANTIC_INVALID_SUPERSESSION",
                    "message": "Tek ve benzersiz bir eski kart seçilmeli",
                },
            )
        active_by_id = {card.card_id: card for card in cards if card.effective_status == "active"}
        for target_id in supersedes_list:
            target = active_by_id.get(target_id)
            if (
                target is None
                or target_id == str(candidate.id)
                or target.scope != candidate.scope
                or target.scope_project != candidate.scope_project
                or target.kind != candidate.kind
                or target.subject_key != candidate.subject_key
            ):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "SEMANTIC_INVALID_SUPERSESSION",
                        "message": "Eski kart bulunamadı veya kapsamı uygun değil",
                    },
                )

        def same_identity(card: sem_storage.SemanticMemoryCard) -> bool:
            return (
                card.effective_status == "active"
                and card.kind == candidate.kind
                and card.scope == candidate.scope
                and card.scope_project == candidate.scope_project
                and card.subject_key == candidate.subject_key
                and normalize_statement(card.statement) == normalize_statement(candidate.statement)
            )

        async def already_present(
            card: sem_storage.SemanticMemoryCard,
        ) -> SemanticCandidatePromoteOut:
            if supersedes_list:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "SEMANTIC_ALREADY_PRESENT",
                        "message": "Aynı aktif bilgi kartı zaten mevcut",
                    },
                )
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
                    "card_id": card.card_id,
                    "relative_path": card.relative_path,
                    "kind": candidate.kind,
                    "already_present": True,
                },
            )
            await session.commit()
            return SemanticCandidatePromoteOut(
                status="already_present",
                card_id=card.card_id,
                relative_path=card.relative_path,
                destination=dest,
                revision=candidate.revision,
            )

        duplicate = next((card for card in cards if same_identity(card)), None)
        if duplicate is not None:
            return await already_present(duplicate)

        identity = ":".join(
            (
                candidate.kind,
                candidate.scope,
                candidate.scope_project or "",
                candidate.subject_key or "",
                normalize_statement(candidate.statement),
            )
        )
        card_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"forkos-semantic:{identity}"))
        title = candidate.statement[:80].strip()

        try:
            card = sem_storage.create_semantic_card(
                root,
                card_id=card_uuid,
                kind=candidate.kind,  # type: ignore[arg-type]
                title=title,
                statement=candidate.statement,
                scope=candidate.scope,  # type: ignore[arg-type]
                scope_project=candidate.scope_project,
                subject_key=candidate.subject_key,
                domains=candidate.domains,
                observed_at=candidate.observed_at,
                valid_from=candidate.valid_from,
                valid_to=candidate.valid_to,
                primary_evidence_class=candidate.primary_evidence_class,  # type: ignore[arg-type]
                evidence_refs=candidate.evidence_refs,
                supersedes=supersedes_list,
                conditions=candidate.conditions,
                exceptions=candidate.exceptions,
                sensitivity=candidate.sensitivity,  # type: ignore[arg-type]
                remote_allowed=candidate.remote_allowed,
                rationale=candidate.rationale,
            )
            card_id = card.card_id
            rel_path = card.relative_path
        except sem_storage.SemanticStorageError as exc:
            if exc.code == "SEMANTIC_CARD_CONFLICT":
                existing = next(
                    (c for c in sem_storage.scan_semantic_cards(root) if c.card_id == card_uuid),
                    None,
                )
                if existing is not None and same_identity(existing):
                    return await already_present(existing)
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

        # Türü sessizce preference'a çevirmek epistemik anlamı bozardı.
        if candidate.kind not in hot_storage.KINDS:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "SEMANTIC_INVALID_DESTINATION",
                    "message": "Bu aday türü sıcak hafızaya yazılamaz",
                },
            )
        h2_kind = candidate.kind
        title = candidate.statement[:80].strip()

        try:
            mem = hot_storage.create_memory(
                root,
                kind=h2_kind,  # type: ignore[arg-type]
                title=title,
                text=candidate.statement,
                importance=2,
                source_mode="approved_candidate",
            )
            card_id = mem.memory_id
            rel_path = mem.relative_path
        except hot_storage.HotMemoryError as exc:
            raise HTTPException(
                status_code=400,
                detail={"code": exc.code, "message": str(exc)},
            ) from exc

    else:
        raise HTTPException(
            status_code=400,
            detail={"code": "SEMANTIC_INVALID_DESTINATION", "message": "Hedef desteklenmiyor"},
        )

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
    counts_query = select(
        AgentSemanticCandidate.status, func.count(AgentSemanticCandidate.id)
    ).group_by(AgentSemanticCandidate.status)
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
