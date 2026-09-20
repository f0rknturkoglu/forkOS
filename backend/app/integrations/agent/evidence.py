"""H3 kanıt orkestrasyonu — yapısal durum + olay geçmişi + kasa bilgisi.

Sıra kasıtlıdır ve asla ters çevrilmez::

    YAPI ÖNCE  →  HAM KAYNAK / KÖKEN  →  LEKSİKAL  →  (anlamsal: H3'te YOK)

forkOS zaten deterministik yapıya sahiptir (Entity, Link, Event, yönetilen kasa
işaretçileri). Bu yüzden H3 hiçbir zaman bir modele "ilişkileri yeniden keşfet"
demez; var olan ilişkiyi okur ve **kökeniyle birlikte** gösterir.

Sahipsizlik ilkesi: H3 hiçbir doğruluğa sahip DEĞİLDİR. Var olan kanonik
kaynaklardan sınırlı bir kanıt görünümü türetir. Yeni tablo, kalıcı indeks,
vektör deposu, gömme (embedding), model çağrısı veya yanıt üretimi YOKTUR.

Öncelik katmanları (§46) — düşük sayı önce gelir::

    10  çekirdek entity'nin güncel durumu
    20  çekirdeğin yönetilen kasa notu
    30  çekirdeğe bağlı olaylar
    40  doğrudan operasyonel komşular
    50  komşuların yönetilen notları
    60  komşulara bağlı olaylar
    70  doğrudan wikilink / backlink kanıtı
    80  genel kasa leksikal yedeği
    90  sorgu-only entity adayları

Kapsam ayrımı (§21/§143): `scope="operational"` Vault'a HİÇ dokunmaz. Bunu
sağlamak için H3, gömülü kasa işaretçisi taşıyan H0 bağlam sarmalayıcılarını
(`get_project_context`/`get_entity_context`) kullanmaz; onların altındaki
kanonik alanları/servisleri doğrudan okur. Aksi hâlde "operational" bir çağrı
sessizce Markdown okurdu.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.links import FROZEN_LEGACY_ENTITY_TYPES
from app.core.models import Entity, Event, Link
from app.integrations.agent import context as ctx_svc
from app.integrations.agent.evidence_models import (
    DEFAULT_EVIDENCE_DEPTH,
    DEFAULT_EVIDENCE_LIMIT,
    MAX_AMBIGUOUS_LINK_SAMPLES,
    MAX_ENTITY_CANDIDATES,
    MAX_EVENT_EVIDENCE,
    MAX_EVENT_SCAN_ROWS,
    MAX_EVIDENCE_DEPTH,
    MAX_EVIDENCE_EXCERPT_CHARS,
    MAX_EVIDENCE_LIMIT,
    MAX_GRAPH_NODES,
    MAX_LINK_ROWS_PER_NODE,
    MAX_QUERY_LENGTH,
    MAX_RETRIEVAL_REASON_CHARS,
    MAX_TOTAL_EVIDENCE_CHARS,
    MAX_VAULT_NOTES_CONSIDERED,
    MAX_WARNING_CHARS,
    MAX_WARNINGS,
    MIN_EVIDENCE_DEPTH,
    MIN_EVIDENCE_LIMIT,
    MIN_QUERY_LENGTH,
    MIN_USEFUL_EXCERPT_CHARS,
    EvidenceBundle,
    EvidenceItem,
    EvidenceLocator,
    EvidencePathHop,
    EvidenceScope,
    EvidenceSourceDomain,
    ResolvedEntityRef,
    RetrievalTraceStep,
)
from app.integrations.agent.models import sanitize_payload
from app.integrations.obsidian import evidence as vault_ev
from app.integrations.obsidian.frontmatter import parse_frontmatter
from app.integrations.obsidian.service import VaultConflictError, resolve_managed_item
from app.integrations.obsidian.vault import vault_context
from app.modules.project import service as project_svc
from app.modules.project.models import Milestone, Project

#: Öncelik katmanları (§46). Küçük sayı = daha doğrudan kanıt.
TIER_SEED_ENTITY = 10
TIER_SEED_KNOWLEDGE = 20
TIER_SEED_EVENT = 30
TIER_NEIGHBOR_ENTITY = 40
TIER_NEIGHBOR_KNOWLEDGE = 50
TIER_NEIGHBOR_EVENT = 60
TIER_VAULT_LINK = 70
TIER_VAULT_LEXICAL = 80
TIER_ENTITY_CANDIDATE = 90

#: Operasyonel kanıtın gövdesinde tutulacak en fazla açık görev başlığı.
MAX_TODO_LINES = 5

VALID_SCOPES: tuple[EvidenceScope, ...] = ("all", "operational", "knowledge")


class EvidenceError(Exception):
    """Model-okunur, sınırlı H3 hatası. Ham yığın izi veya mutlak yol taşımaz."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass
class _Candidate:
    """Bütçe uygulanmadan önceki kanıt adayı.

    `lines` + `focus` snippet'in kalan bütçeye kırpılabilmesi içindir: kırpma
    daima odak satırını korur, böylece eşleşme kanıttan düşmez.
    """

    item: EvidenceItem
    tier: int
    rank: int
    lines: list[str]
    focus: int = 0


# ---------------------------------------------------------------------------
# Küçük yardımcılar
# ---------------------------------------------------------------------------


def _bounded_reason(text: str) -> str:
    return text[:MAX_RETRIEVAL_REASON_CHARS]


def _add_warning(warnings: list[str], text: str) -> None:
    if len(warnings) >= MAX_WARNINGS:
        return
    warnings.append(text[:MAX_WARNING_CHARS])


def _parse_time(value: str | None, label: str) -> datetime | None:
    """Zaman sınırını katı biçimde ayrıştırır (§22).

    Naif (saat dilimsiz) damga REDDEDİLİR: yerel saat varsayımı sessiz bir
    yanlış cevaba dönüşürdü.
    """
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text)
    except (ValueError, TypeError) as exc:
        raise EvidenceError(
            "INVALID_TIME_RANGE", f"'{label}' is not a valid ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvidenceError(
            "INVALID_TIME_RANGE", f"'{label}' must include a timezone offset (e.g. +03:00 or Z)"
        )
    return parsed


def _frontmatter_of(lines: list[str]) -> dict[str, Any]:
    """Yalnızca frontmatter bloğunu ayrıştırır (tüm dosyayı yeniden okumaz)."""
    end = vault_ev.body_start_line(lines)
    if end <= 0:
        return {}
    frontmatter, _ = parse_frontmatter("\n".join(lines[:end]) + "\n")
    return frontmatter if isinstance(frontmatter, dict) else {}


def _optional_timestamp(value: object) -> str | None:
    """Frontmatter zaman damgasını ISO-8601 dizesine çevirir.

    YAML, tırnaksız bir ISO damgasını `datetime` nesnesine çevirir; `str()`
    tarih ve saati BOŞLUKLA ayırırdı. Sözleşme ISO-8601'dir, bu yüzden açıkça
    yeniden serileştirilir.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _entity_ref(entity: Entity, *, resolution: str, expanded: bool) -> ResolvedEntityRef:
    return ResolvedEntityRef(
        id=str(entity.id),
        type=entity.type,
        title=entity.title,
        route=ctx_svc.resolve_route(entity.type, entity.id),
        resolution=resolution,  # type: ignore[arg-type]
        expanded=expanded,
    )


def _knowledge_hop(entity_id: uuid.UUID, rel_path: str) -> EvidencePathHop:
    return EvidencePathHop(
        kind="knowledge_pointer",
        from_ref=f"entity:{entity_id}",
        relation="knowledge_note",
        to_ref=f"vault:{rel_path}",
    )


def _vault_item(
    *,
    source_id: str,
    rel_path: str,
    forkos_id: str | None,
    title: str,
    excerpt: vault_ev.Excerpt,
    updated_at: str | None,
    relation_path: list[EvidencePathHop],
    reason: str,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=f"vault:{source_id}#{excerpt.heading or 'root'}",
        source_type="vault",
        source_id=source_id,
        title=title,
        locator=EvidenceLocator(
            forkos_id=forkos_id,
            relative_path=rel_path,
            heading=excerpt.heading,
            line_start=excerpt.line_start,
            line_end=excerpt.line_end,
        ),
        excerpt=excerpt.text,
        updated_at=updated_at,
        relation_path=relation_path,
        retrieval_reason=_bounded_reason(reason),
        truncated=excerpt.truncated,
    )


# ---------------------------------------------------------------------------
# Çekirdek çözümlemesi
# ---------------------------------------------------------------------------


async def _load_entity(session: AsyncSession, raw_id: str) -> Entity:
    try:
        entity_uuid = uuid.UUID(str(raw_id).strip())
    except (ValueError, AttributeError, TypeError) as exc:
        raise EvidenceError("INVALID_UUID", "entity_id is not a valid UUID") from exc

    entity = (
        await session.execute(select(Entity).where(Entity.id == entity_uuid))
    ).scalar_one_or_none()
    if entity is None:
        raise EvidenceError("ENTITY_NOT_FOUND", "The requested entity does not exist")

    if entity.type in FROZEN_LEGACY_ENTITY_TYPES:
        raise EvidenceError(
            "FROZEN_ENTITY_UNAVAILABLE",
            "Legacy note entities are a frozen archive. Active knowledge lives in "
            "f0rknbrain; use knowledge retrieval instead.",
        )
    return entity


# ---------------------------------------------------------------------------
# Operasyonel kanıt
# ---------------------------------------------------------------------------


def _entity_projection_lines(entity: Entity, details: list[str]) -> list[str]:
    lines = [f"type: {entity.type}", f"title: {entity.title}"]
    lines.extend(details)
    lines.append(f"created_at: {entity.created_at.isoformat() if entity.created_at else '-'}")
    lines.append(f"updated_at: {entity.updated_at.isoformat() if entity.updated_at else '-'}")
    if entity.archived_at is not None:
        lines.append(f"archived_at: {entity.archived_at.isoformat()} (archived)")
    if entity.search_text:
        lines.append(f"summary: {' '.join(entity.search_text.split())[:400]}")
    return lines


async def _project_details(session: AsyncSession, entity: Entity) -> list[str]:
    """Projenin kanonik operasyonel alanları (§50/§51) — Vault'a dokunmaz."""
    row = (
        await session.execute(
            select(Project, Entity.title).join(Entity, Entity.id == Project.id).where(Project.id == entity.id)
        )
    ).first()
    if row is None:
        return ["status: (project row missing)"]

    project, _title = row
    stack = ", ".join(str(item) for item in (project.stack or []))
    details = [
        f"status: {project.status}",
        f'next_action: "{project.next_action or ""}"',
        f"stack: [{stack}]",
        f"github_repo: {project.github_repo or '-'}",
    ]

    todos = await project_svc.project_todos(session, entity.id)
    open_todos = [todo for todo in todos if todo.status != "done"]
    details.append(f"open_todos: {len(open_todos)}")
    for todo in open_todos[:MAX_TODO_LINES]:
        due = f", due {todo.due_at.date().isoformat()}" if todo.due_at else ""
        details.append(f"  - {todo.title} ({todo.status}{due})")

    milestones = list(
        (
            await session.execute(
                select(Milestone)
                .where(Milestone.project_id == entity.id)
                .order_by(Milestone.position.asc(), Milestone.due_at.asc().nulls_last())
            )
        ).scalars()
    )
    completed = [m for m in milestones if m.completed_at is not None]
    details.append(f"milestones: {len(milestones)} ({len(completed)} completed)")
    return details


async def _entity_candidate(
    session: AsyncSession,
    entity: Entity,
    *,
    tier: int,
    rank: int,
    reason: str,
    relation_path: list[EvidencePathHop],
) -> _Candidate:
    """Bir entity'nin GÜNCEL durumunu deterministik projeksiyonla kanıtlar."""
    details = await _project_details(session, entity) if entity.type == "project" else []
    lines = _entity_projection_lines(entity, details)
    text = "\n".join(lines)[:MAX_EVIDENCE_EXCERPT_CHARS]
    truncated = len("\n".join(lines)) > MAX_EVIDENCE_EXCERPT_CHARS
    item = EvidenceItem(
        evidence_id=f"entity:{entity.id}",
        source_type="entity",
        source_id=str(entity.id),
        title=entity.title,
        locator=EvidenceLocator(entity_id=str(entity.id)),
        excerpt=text,
        updated_at=entity.updated_at.isoformat() if entity.updated_at else None,
        relation_path=relation_path,
        retrieval_reason=_bounded_reason(reason),
        truncated=truncated,
    )
    return _Candidate(item=item, tier=tier, rank=rank, lines=lines)


async def _expand_graph(
    session: AsyncSession, root: Entity, max_depth: int
) -> tuple[dict[uuid.UUID, Entity], dict[uuid.UUID, list[EvidencePathHop]], dict[uuid.UUID, int], bool]:
    """Deterministik, sınırlı BFS (§54/§55).

    Ziyaret kümesi + derinlik tavanı + düğüm tavanı birlikte çalışır; döngü
    oluşsa bile her düğüm en fazla bir kez ziyaret edilir. Özyinelemeli
    sınırsız DFS YOKTUR.
    """
    visited: dict[uuid.UUID, Entity] = {root.id: root}
    paths: dict[uuid.UUID, list[EvidencePathHop]] = {root.id: []}
    depths: dict[uuid.UUID, int] = {root.id: 0}
    frontier: list[uuid.UUID] = [root.id]
    truncated = False
    depth = 0

    while frontier and depth < max_depth:
        row_cap = MAX_LINK_ROWS_PER_NODE * max(len(frontier), 1)
        links = list(
            (
                await session.execute(
                    select(Link)
                    .where(or_(Link.from_id.in_(frontier), Link.to_id.in_(frontier)))
                    .order_by(Link.relation, Link.from_id, Link.to_id)
                    .limit(row_cap + 1)
                )
            ).scalars()
        )
        if len(links) > row_cap:
            links = links[:row_cap]
            truncated = True

        others = {
            other_id
            for link in links
            for other_id in (link.from_id, link.to_id)
            if other_id not in visited
        }
        entities: dict[uuid.UUID, Entity] = {}
        if others:
            entities = {
                entity.id: entity
                for entity in (
                    await session.execute(select(Entity).where(Entity.id.in_(others)))
                ).scalars()
            }

        frontier_set = set(frontier)
        rows: list[tuple[str, str, str, str, str, uuid.UUID, Entity]] = []
        for link in links:
            for self_id, other_id, direction in (
                (link.from_id, link.to_id, "outgoing"),
                (link.to_id, link.from_id, "incoming"),
            ):
                if self_id not in frontier_set:
                    continue
                other = entities.get(other_id)
                if other is None or other.id in visited:
                    continue
                if other.type in FROZEN_LEGACY_ENTITY_TYPES:
                    continue
                # Arşivlenmiş komşular varsayılan olarak GENİŞLETİLMEZ (§53):
                # güncel durumu olmayan bir kaydı çekirdeğin komşusu gibi
                # sunmak yanıltıcı olurdu.
                if other.archived_at is not None:
                    continue
                rows.append(
                    (link.relation, direction, other.type, other.title.casefold(), str(other.id), self_id, other)
                )
        rows.sort(key=lambda row: (row[0], row[1], row[2], row[3], row[4]))

        next_frontier: list[uuid.UUID] = []
        for relation, _direction, _type, _title, _other_key, self_id, other in rows:
            if len(visited) >= MAX_GRAPH_NODES:
                truncated = True
                break
            visited[other.id] = other
            paths[other.id] = [
                *paths[self_id],
                EvidencePathHop(
                    kind="entity_link",
                    from_ref=f"entity:{self_id}",
                    relation=relation,
                    to_ref=f"entity:{other.id}",
                ),
            ]
            depths[other.id] = depth + 1
            next_frontier.append(other.id)

        frontier = next_frontier
        depth += 1

    return visited, paths, depths, truncated


async def _event_candidates(
    session: AsyncSession,
    *,
    visited: dict[uuid.UUID, Entity],
    paths: dict[uuid.UUID, list[EvidencePathHop]],
    root_id: uuid.UUID,
    since: datetime | None,
    until: datetime | None,
    terms: vault_ev.QueryTerms,
) -> tuple[list[_Candidate], int, bool]:
    """Çekirdeğe ve gezinilen düğümlere bağlı olaylar (§58-§64).

    Tek sınırlı sorgu kullanılır (düğüm başına sorgu YOKTUR). Olaylar yalnızca
    yapısal bir çapaya bağlı olarak çekilir; global olay metin araması yoktur.
    """
    if not visited:
        return [], 0, False

    ids = list(visited.keys())
    stmt = (
        select(Event, Entity.title)
        .outerjoin(Entity, Entity.id == Event.entity_id)
        .where(Event.entity_id.in_(ids))
    )
    if since is not None:
        stmt = stmt.where(Event.occurred_at >= since)
    if until is not None:
        stmt = stmt.where(Event.occurred_at <= until)
    stmt = stmt.order_by(Event.occurred_at.desc(), Event.id.desc()).limit(MAX_EVENT_SCAN_ROWS)

    rows = list((await session.execute(stmt)).all())
    truncated = len(rows) >= MAX_EVENT_SCAN_ROWS
    if not rows:
        return [], 0, truncated

    tokens = frozenset(terms.tokens)
    ranked: list[tuple[bool, float, int, Event, str]] = []
    for event, title in rows:
        payload = sanitize_payload(event.payload or {})
        matching = bool(
            (tokens & vault_ev.words_of(event.verb))
            or (tokens & vault_ev.words_of(title or ""))
            or (tokens & vault_ev.words_of(json.dumps(payload, default=str)[:600]))
        )
        ranked.append(
            (
                matching,
                -event.occurred_at.timestamp(),
                -event.id,
                event,
                title or "",
            )
        )
    ranked.sort(key=lambda row: (not row[0], row[1], row[2]))

    candidates: list[_Candidate] = []
    for matching, _ts, _event_key, event, title in ranked[:MAX_EVENT_EVIDENCE]:
        owner = visited.get(event.entity_id) if event.entity_id else None
        is_seed = event.entity_id == root_id
        depth = 1 if owner is None else 0
        excerpt_lines = [f"{event.verb}" + (f' · entity="{title}"' if title else "")]
        payload_text = json.dumps(sanitize_payload(event.payload or {}), ensure_ascii=False, default=str)
        if payload_text and payload_text != "{}":
            excerpt_lines.append(f"payload={payload_text[:MAX_EVIDENCE_EXCERPT_CHARS]}")
        excerpt = "\n".join(excerpt_lines)[:MAX_EVIDENCE_EXCERPT_CHARS]

        if is_seed:
            anchor = "the explicit entity seed"
        elif owner is not None:
            anchor = f'a depth-{depth} related entity ("{title}")'
        else:
            anchor = "a traversed entity"
        reason = f"event on {anchor}" + (
            "; query terms matched the event" if matching else "; most recent in the window"
        )

        item = EvidenceItem(
            evidence_id=f"event:{event.id}",
            source_type="event",
            source_id=str(event.id),
            title=event.verb + (f' · {title}' if title else ""),
            locator=EvidenceLocator(
                event_id=event.id,
                entity_id=str(event.entity_id) if event.entity_id else None,
            ),
            excerpt=excerpt,
            occurred_at=event.occurred_at.isoformat(),
            updated_at=event.occurred_at.isoformat(),
            relation_path=list(paths.get(event.entity_id, [])) if event.entity_id else [],
            retrieval_reason=_bounded_reason(reason),
            truncated=len("\n".join(excerpt_lines)) > MAX_EVIDENCE_EXCERPT_CHARS,
        )
        candidates.append(
            _Candidate(
                item=item,
                tier=TIER_SEED_EVENT if is_seed else TIER_NEIGHBOR_EVENT,
                rank=depth,
                lines=excerpt_lines,
            )
        )

    return candidates, len(rows), truncated


async def _operational_evidence(
    session: AsyncSession,
    *,
    seed: Entity | None,
    terms: vault_ev.QueryTerms,
    since: datetime | None,
    until: datetime | None,
    effective_depth: int,
) -> tuple[list[_Candidate], list[ResolvedEntityRef], list[RetrievalTraceStep], bool]:
    """Yapısal (operasyonel) kanal. Vault'a HİÇ dokunmaz."""
    candidates: list[_Candidate] = []
    resolved: list[ResolvedEntityRef] = []
    trace: list[RetrievalTraceStep] = []
    truncated = False

    if seed is None:
        found = await ctx_svc.search_operational_context(
            session, terms.phrase or " ".join(terms.tokens), limit=MAX_ENTITY_CANDIDATES
        )
        trace.append(
            RetrievalTraceStep(
                stage="entity_resolution",
                description="Lexical operational entity candidates (no explicit seed).",
                considered=len(found),
                accepted=len(found),
                truncated=False,
            )
        )
        for hit in found:
            entity = (
                await session.execute(select(Entity).where(Entity.id == uuid.UUID(hit.id)))
            ).scalar_one_or_none()
            if entity is None:
                continue
            resolved.append(_entity_ref(entity, resolution="lexical_candidate", expanded=False))
            candidate = await _entity_candidate(
                session,
                entity,
                tier=TIER_ENTITY_CANDIDATE,
                rank=0,
                reason="lexical operational candidate; not graph-expanded (no explicit seed)",
                relation_path=[],
            )
            candidates.append(candidate)

        trace.append(
            RetrievalTraceStep(
                stage="graph",
                description=(
                    "Graph expansion skipped: no explicit entity seed "
                    "(effective max_depth=0)."
                ),
                considered=0,
                accepted=0,
                truncated=False,
            )
        )
        trace.append(
            RetrievalTraceStep(
                stage="events",
                description="Event evidence skipped: events require an explicit entity seed.",
                considered=0,
                accepted=0,
                truncated=False,
            )
        )
        return candidates, resolved, trace, truncated

    resolved.append(_entity_ref(seed, resolution="explicit_seed", expanded=effective_depth > 0))
    candidates.append(
        await _entity_candidate(
            session,
            seed,
            tier=TIER_SEED_ENTITY,
            rank=0,
            reason="explicit entity seed; current operational state",
            relation_path=[],
        )
    )
    trace.append(
        RetrievalTraceStep(
            stage="entity_resolution",
            description="Explicit entity seed resolved and used as the retrieval root.",
            considered=1,
            accepted=1,
            truncated=False,
        )
    )

    visited, paths, depths, graph_truncated = await _expand_graph(session, seed, effective_depth)
    truncated = truncated or graph_truncated
    neighbors = [entity for entity_id, entity in visited.items() if entity_id != seed.id]
    trace.append(
        RetrievalTraceStep(
            stage="graph",
            description=(
                "Expanded the explicit seed through canonical Link relationships "
                f"at depth {effective_depth}."
            ),
            considered=len(visited) - 1,
            accepted=len(neighbors),
            truncated=graph_truncated,
        )
    )
    for neighbor in sorted(neighbors, key=lambda entity: (depths[entity.id], str(entity.id))):
        candidates.append(
            await _entity_candidate(
                session,
                neighbor,
                tier=TIER_NEIGHBOR_ENTITY,
                rank=depths[neighbor.id],
                reason=(
                    f"depth-{depths[neighbor.id]} related entity via "
                    f"'{paths[neighbor.id][-1].relation}' link"
                ),
                relation_path=paths[neighbor.id],
            )
        )

    events, scanned, events_truncated = await _event_candidates(
        session,
        visited=visited,
        paths=paths,
        root_id=seed.id,
        since=since,
        until=until,
        terms=terms,
    )
    truncated = truncated or events_truncated
    candidates.extend(events)
    window = " with the requested time window" if (since or until) else ""
    trace.append(
        RetrievalTraceStep(
            stage="events",
            description=(
                f"Read append-only events for the seed and {len(neighbors)} traversed "
                f"entit(ies){window}; ranked by query-term match then recency."
            ),
            considered=scanned,
            accepted=len(events),
            truncated=events_truncated,
        )
    )

    return candidates, resolved, trace, truncated


# ---------------------------------------------------------------------------
# Kasa kanıtı
# ---------------------------------------------------------------------------


def _vault_root() -> Path | None:
    root, _name = vault_context()
    if root is None or not root.is_dir():
        return None
    return root


def _managed_note(forkos_id: uuid.UUID) -> tuple[str | None, str | None, bool]:
    """Yönetilen notu KANONİK çözücüyle taze olarak bulur (§85).

    Döner: (göreli yol, forkos_id, çakışma var mı). Eski DB durumundaki yol
    dizesine GÜVENİLMEZ; kimlik `forkos_id`'dir.
    """
    try:
        item = resolve_managed_item(forkos_id)
    except VaultConflictError:
        return None, None, True
    if item is None:
        return None, None, False
    return item.relative_path, item.forkos_id, False


def _vault_match_reason(note: vault_ev.NoteRef) -> str:
    matched = ", ".join(note.matched) if note.matched else "no field"
    return f"query tokens matched ({matched})"


def _note_candidate(
    root: Path,
    *,
    rel_path: str,
    source_id: str,
    forkos_id: str | None,
    tier: int,
    rank: int,
    terms: vault_ev.QueryTerms,
    relation_path: list[EvidencePathHop],
    reason: str,
    note: vault_ev.NoteRef | None,
) -> _Candidate | None:
    """Bir notu snippet'e dönüştürür; okunamıyorsa None döner (sessiz değil)."""
    lines = vault_ev.read_note_lines(root, rel_path)
    if lines is None:
        return None

    sections = vault_ev.build_sections(lines, vault_ev.body_start_line(lines))
    if not sections:
        return None
    excerpt = vault_ev.extract_excerpt(lines, sections, terms, max_chars=MAX_EVIDENCE_EXCERPT_CHARS)
    if excerpt is None:
        return None

    frontmatter = _frontmatter_of(lines)
    title = note.title if note is not None else Path(rel_path).stem
    # Kimlik ÇAĞIRANDAN gelir; frontmatter'dan geri okunmaz. Aksi hâlde
    # çakışan bir `forkos_id` "yönetilen not" iddiası olarak geri sızardı (§86).
    item = _vault_item(
        source_id=source_id,
        rel_path=rel_path,
        forkos_id=forkos_id,
        title=title,
        excerpt=excerpt,
        updated_at=_optional_timestamp(frontmatter.get("forkos_updated_at")),
        relation_path=relation_path,
        reason=reason,
    )
    focus = excerpt.line_start - 1
    return _Candidate(item=item, tier=tier, rank=rank, lines=lines, focus=focus)


def _wikilink_hop(anchor_rel_path: str, target_rel_path: str) -> EvidencePathHop:
    return EvidencePathHop(
        kind="wikilink",
        from_ref=f"vault:{anchor_rel_path}",
        relation="wikilink",
        to_ref=f"vault:{target_rel_path}",
    )


def _backlink_hop(anchor_rel_path: str, source_rel_path: str) -> EvidencePathHop:
    return EvidencePathHop(
        kind="backlink",
        from_ref=f"vault:{source_rel_path}",
        relation="backlink",
        to_ref=f"vault:{anchor_rel_path}",
    )


async def _knowledge_evidence(
    *,
    root: Path,
    terms: vault_ev.QueryTerms,
    seed: Entity | None,
    neighbors: list[tuple[Entity, int, list[EvidencePathHop]]],
    index: vault_ev.EvidenceNoteIndex,
    warnings: list[str],
) -> tuple[list[_Candidate], list[RetrievalTraceStep], bool]:
    """Kasa kanalı: yönetilen notlar, wikilink/backlink ve leksikal yedek."""
    candidates: list[_Candidate] = []
    trace: list[RetrievalTraceStep] = []
    truncated = index.truncated
    for warning in index.warnings:
        _add_warning(warnings, warning)

    anchors: list[tuple[str, list[EvidencePathHop], str, int]] = []
    anchor_depths: dict[str, int] = {}
    conflicted_ids: set[str] = set()

    if seed is not None:
        rel_path, forkos_id, conflicted = _managed_note(seed.id)
        if conflicted:
            conflicted_ids.add(str(seed.id))
        elif rel_path is not None:
            anchors.append((rel_path, [_knowledge_hop(seed.id, rel_path)], str(seed.id), TIER_SEED_KNOWLEDGE))

    # Kanal bazlı kesme bayrakları (§108): bir kanal sınırla kesildiyse paket
    # bunu SAKLAMAZ.
    if len(neighbors) > MAX_VAULT_NOTES_CONSIDERED:
        truncated = True

    for entity, depth, path in neighbors[:MAX_VAULT_NOTES_CONSIDERED]:
        rel_path, _forkos_id, conflicted = _managed_note(entity.id)
        if conflicted:
            conflicted_ids.add(str(entity.id))
            continue
        if rel_path is not None:
            anchors.append(
                (rel_path, [*path, _knowledge_hop(entity.id, rel_path)], str(entity.id), TIER_NEIGHBOR_KNOWLEDGE)
            )
            anchor_depths[rel_path] = depth


    conflicted_ids.update(index.conflicted_forkos_ids)

    considered = 0
    accepted = 0
    ambiguous = 0
    ambiguous_samples: list[str] = []
    unresolved = 0
    wikilink_considered = 0
    wikilink_accepted = 0
    backlink_considered = 0
    backlink_accepted = 0

    for rel_path, relation_path, source_id, tier in anchors:
        note = index.by_path(rel_path)
        if tier == TIER_SEED_KNOWLEDGE:
            reason = (
                "managed knowledge note of the explicit entity seed"
                + (f"; {_vault_match_reason(note)}" if note is not None and note.matched else "")
            )
        else:
            if note is None or note.score == 0:
                continue
            depth = anchor_depths.get(rel_path, 1)
            reason = (
                f"managed knowledge note of a depth-{depth} related entity; "
                f"{_vault_match_reason(note)}"
            )

        considered += 1
        candidate = _note_candidate(
            root,
            rel_path=rel_path,
            source_id=source_id,
            forkos_id=note.forkos_id if note is not None else None,
            tier=tier,
            rank=-note.score if note is not None else 0,
            terms=terms,
            relation_path=relation_path,
            reason=reason,
            note=note,
        )
        if candidate is not None:
            candidates.append(candidate)
            accepted += 1

        # --- bir kasa hopu: doğrudan wikilink + doğrudan backlink (§95) ---
        if note is None:
            continue
        anchor_knowledge_hop = _knowledge_hop(uuid.UUID(source_id), rel_path)
        for target in note.wikilinks:
            wikilink_considered += 1
            resolution = index.resolve(target)
            if resolution.status == "ambiguous":
                ambiguous += 1
                for sample in resolution.candidates:
                    if sample not in ambiguous_samples:
                        ambiguous_samples.append(sample)
                continue
            if resolution.status != "resolved" or resolution.rel_path is None:
                unresolved += 1
                continue
            linked = index.by_path(resolution.rel_path)
            if linked is None or linked.score == 0:
                # Bağ tek başına kanıt değildir (§99): içerik sorguyla
                # ilgili değilse gövde dökülmez.
                continue
            candidate = _note_candidate(
                root,
                rel_path=linked.rel_path,
                source_id=linked.forkos_id or linked.rel_path,
                forkos_id=linked.forkos_id,
                tier=TIER_VAULT_LINK,
                rank=-linked.score,
                terms=terms,
                relation_path=[anchor_knowledge_hop, _wikilink_hop(rel_path, linked.rel_path)],
                reason=f"direct wikilink from '{rel_path}'; {_vault_match_reason(linked)}",
                note=linked,
            )
            if candidate is not None:
                candidates.append(candidate)
                wikilink_accepted += 1

        for backlink_path in vault_ev.find_backlinks(index, rel_path):
            backlink_considered += 1
            backlink_note = index.by_path(backlink_path)
            if backlink_note is None or backlink_note.score == 0:
                continue
            candidate = _note_candidate(
                root,
                rel_path=backlink_note.rel_path,
                source_id=backlink_note.forkos_id or backlink_note.rel_path,
                forkos_id=backlink_note.forkos_id,
                tier=TIER_VAULT_LINK,
                rank=-backlink_note.score,
                terms=terms,
                relation_path=[anchor_knowledge_hop, _backlink_hop(rel_path, backlink_note.rel_path)],
                reason=f"links to '{rel_path}'; {_vault_match_reason(backlink_note)}",
                note=backlink_note,
            )
            if candidate is not None:
                candidates.append(candidate)
                backlink_accepted += 1

    if ambiguous:
        samples = ", ".join(sorted(ambiguous_samples)[:MAX_AMBIGUOUS_LINK_SAMPLES])
        _add_warning(
            warnings,
            f"Vault wikilink ambiguity: {ambiguous} link(s) matched multiple safe notes and "
            f"were not traversed (no target was guessed). Candidates: {samples}",
        )

    trace.append(
        RetrievalTraceStep(
            stage="managed_knowledge",
            description=(
                "Resolved managed knowledge notes with the canonical vault index "
                f"for {len(anchors)} anchor(s)."
            ),
            considered=considered,
            accepted=accepted,
            truncated=index.truncated,
        )
    )
    trace.append(
        RetrievalTraceStep(
            stage="wikilinks",
            description=(
                f"Followed direct outbound wikilinks of {len(anchors)} anchored note(s) with one "
                f"Vault hop; {ambiguous} ambiguous and {unresolved} unresolved target(s) were "
                "skipped (no target was guessed)."
            ),
            considered=wikilink_considered,
            accepted=wikilink_accepted,
            truncated=False,
        )
    )
    trace.append(
        RetrievalTraceStep(
            stage="backlinks",
            description=(
                f"Scanned {index.files_read} safe note(s) for resolved links pointing at the "
                "anchor(s); only query-relevant notes became evidence."
            ),
            considered=backlink_considered,
            accepted=backlink_accepted,
            truncated=index.truncated,
        )
    )

    # Leksikal yedek: sorguyla eşleşen güvenli notlar (§71-§77)
    lexical_found = [note for note in index.notes if note.score > 0]
    lexical = sorted(lexical_found, key=lambda note: (-note.score, note.rel_path))[
        :MAX_VAULT_NOTES_CONSIDERED
    ]
    if len(lexical_found) > MAX_VAULT_NOTES_CONSIDERED:
        truncated = True
    lexical_accepted = 0
    for note in lexical:
        # Çakışan kimlik KİMLİK OLARAK SUNULMAZ (§86); not yine de kanıt
        # olabilir -- ama o zaman yoluyla, "yönetilen not" iddiası olmadan.
        managed_id = None if note.forkos_id in index.conflicted_forkos_ids else note.forkos_id
        if note.forkos_id and managed_id is None:
            conflicted_ids.add(note.forkos_id)
        candidate = _note_candidate(
            root,
            rel_path=note.rel_path,
            source_id=managed_id or note.rel_path,
            forkos_id=managed_id,
            tier=TIER_VAULT_LEXICAL,
            rank=-note.score,
            terms=terms,
            relation_path=[],
            reason=f"global Vault lexical fallback; {_vault_match_reason(note)}",
            note=note,
        )
        if candidate is not None:
            candidates.append(candidate)
            lexical_accepted += 1

    if conflicted_ids:
        _add_warning(
            warnings,
            f"VAULT_CONFLICT: {len(conflicted_ids)} managed note id(s) are claimed by multiple "
            "files; those notes were served by path only and no target was guessed.",
        )

    trace.append(
        RetrievalTraceStep(
            stage="vault_lexical",
            description=(
                f"Deterministically scanned {index.files_read} safe knowledge note(s) with "
                "token-based lexical ranking (no embeddings); at most "
                f"{MAX_VAULT_NOTES_CONSIDERED} best note(s) were promoted to evidence."
            ),
            considered=len(lexical_found),
            accepted=lexical_accepted,
            truncated=index.truncated or len(lexical_found) > MAX_VAULT_NOTES_CONSIDERED,
        )
    )

    return candidates, trace, truncated


# ---------------------------------------------------------------------------
# Bütçe ve paket
# ---------------------------------------------------------------------------


def _shrink(candidate: _Candidate, remaining: int) -> tuple[EvidenceItem, bool] | None:
    """Adayı kalan bütçeye kırpar (§149).

    Kırpma DAİMA odak satırını korur; kırpılmış öğe, `truncated=True` ve
    kırpılan aralığa uyan satır numaralarıyla döner. Yeterli anlamlı pay
    kalmıyorsa öğe atlanır (uydurma yok).
    """
    item = candidate.item
    if len(item.excerpt) <= remaining:
        return item, False

    lines = candidate.lines
    focus = min(max(candidate.focus, 0), len(lines) - 1)
    if lines and len(lines[focus]) > remaining:
        if remaining < MIN_USEFUL_EXCERPT_CHARS:
            return None
        trimmed = item.model_copy(update={"excerpt": lines[focus][:remaining], "truncated": True})
        return trimmed, True

    start = end = focus
    used = len(lines[focus]) if lines else 0
    below, above = focus + 1, focus - 1
    while True:
        grew = False
        if below < len(lines):
            cost = len(lines[below]) + 1
            if used + cost <= remaining:
                used += cost
                end = below
                below += 1
                grew = True
        if above >= 0:
            cost = len(lines[above]) + 1
            if used + cost <= remaining:
                used += cost
                start = above
                above -= 1
                grew = True
        if not grew:
            break

    if not lines or used < MIN_USEFUL_EXCERPT_CHARS:
        return None

    locator = item.locator
    if locator.line_start is not None:
        locator = locator.model_copy(update={"line_start": start + 1, "line_end": end + 1})
    trimmed = item.model_copy(
        update={"excerpt": "\n".join(lines[start : end + 1]), "truncated": True, "locator": locator}
    )
    return trimmed, True


def _select_evidence(
    candidates: list[_Candidate], *, limit: int
) -> tuple[list[EvidenceItem], int, bool]:
    """Öncelik sırasına göre tekilleştirir ve bütçeye oturtur (§46-§48/§148)."""
    ordered = sorted(candidates, key=lambda candidate: (candidate.tier, candidate.rank, candidate.item.evidence_id))

    selected: list[EvidenceItem] = []
    seen: set[str] = set()
    used_chars = 0
    omitted = 0
    truncated = False

    for candidate in ordered:
        if candidate.item.evidence_id in seen:
            omitted += 1
            continue
        if len(selected) >= limit:
            omitted += 1
            truncated = True
            continue

        remaining = MAX_TOTAL_EVIDENCE_CHARS - used_chars
        shrunk = _shrink(candidate, remaining)
        if shrunk is None:
            omitted += 1
            truncated = True
            continue

        item, was_shrunk = shrunk
        seen.add(item.evidence_id)
        selected.append(item)
        used_chars += len(item.excerpt)
        truncated = truncated or was_shrunk

    return selected, omitted, truncated


#: İz aşamalarının SABİT sırası (§44/§130). Aynı istek her zaman aynı
#: aşama kümesini, aynı sırada döndürür; kapsam yalnızca içerikleri değiştirir.
_TRACE_ORDER: tuple[str, ...] = (
    "entity_resolution",
    "graph",
    "events",
    "managed_knowledge",
    "wikilinks",
    "backlinks",
    "vault_lexical",
    "budget",
)


def _ordered_trace(steps: list[RetrievalTraceStep]) -> list[RetrievalTraceStep]:
    """İzi sabit aşama sırasına oturtur (yineleme yok, sıra deterministik)."""
    by_stage = {step.stage: step for step in steps}
    return [by_stage[stage] for stage in _TRACE_ORDER if stage in by_stage]


def _recovery_hint(
    *,
    has_seed: bool,
    evidence_count: int,
    candidate_count: int,
    vault_unavailable: bool,
    wants_knowledge: bool,
) -> str | None:
    """Yalnızca EYLEME DÖNÜK ipucu (§110). Genel dolgu yok."""
    if not evidence_count and wants_knowledge and vault_unavailable:
        return "Configure the Obsidian Vault (OBSIDIAN_VAULT_PATH) to include knowledge evidence."
    if not has_seed and candidate_count:
        return "Provide entity_id to traverse a specific operational entity."
    if not evidence_count:
        return "Use a more specific query, or provide an entity_id for structural traversal."
    return None


# ---------------------------------------------------------------------------
# Genel giriş noktası
# ---------------------------------------------------------------------------


async def retrieve_evidence(
    session: AsyncSession,
    *,
    query: str,
    entity_id: str | None = None,
    scope: EvidenceScope = "all",
    since: str | None = None,
    until: str | None = None,
    max_depth: int = DEFAULT_EVIDENCE_DEPTH,
    limit: int = DEFAULT_EVIDENCE_LIMIT,
) -> EvidenceBundle:
    """Sorgu/iddia için sınırlı, kökenli ve incelenebilir kanıt getirir.

    Salt-okunurdur: hiçbir tabloya yazmaz, hiçbir dosyayı değiştirmez, hiçbir
    olay (Event) üretmez. Model çağrısı ve dış ağ erişimi YOKTUR.
    """
    query_text = (query or "").strip()
    if not query_text:
        raise EvidenceError("INVALID_QUERY", "query is required and must not be blank")
    if len(query_text) < MIN_QUERY_LENGTH:
        raise EvidenceError("QUERY_TOO_SHORT", f"query must be at least {MIN_QUERY_LENGTH} characters")
    if len(query_text) > MAX_QUERY_LENGTH:
        raise EvidenceError("QUERY_TOO_LONG", f"query must be at most {MAX_QUERY_LENGTH} characters")
    if scope not in VALID_SCOPES:
        raise EvidenceError("INVALID_SCOPE", f"scope must be one of {list(VALID_SCOPES)}")

    since_dt = _parse_time(since, "since")
    until_dt = _parse_time(until, "until")
    if since_dt is not None and until_dt is not None and since_dt > until_dt:
        raise EvidenceError("INVALID_TIME_RANGE", "'since' must not be later than 'until'")

    requested_depth = max(MIN_EVIDENCE_DEPTH, min(int(max_depth), MAX_EVIDENCE_DEPTH))
    requested_limit = max(MIN_EVIDENCE_LIMIT, min(int(limit), MAX_EVIDENCE_LIMIT))

    seed: Entity | None = None
    if entity_id is not None and str(entity_id).strip():
        seed = await _load_entity(session, str(entity_id))

    if (since_dt is not None or until_dt is not None) and seed is None:
        raise EvidenceError(
            "TIME_FILTER_REQUIRES_ENTITY_SEED",
            "since/until filter Event evidence only; provide an entity_id to anchor the search",
        )

    # Sorgu-only modda grafik gezinmesi YOKTUR: aday tahmin edilip kök yapılmaz.
    effective_depth = requested_depth if seed is not None else MIN_EVIDENCE_DEPTH
    wants_operational = scope in ("all", "operational")
    wants_knowledge = scope in ("all", "knowledge")
    terms = vault_ev.tokenize_query(query_text)

    candidates: list[_Candidate] = []
    resolved: list[ResolvedEntityRef] = []
    trace: list[RetrievalTraceStep] = []
    warnings: list[str] = []
    sources_used: list[EvidenceSourceDomain] = []
    truncated = False

    neighbors: list[tuple[Entity, int, list[EvidencePathHop]]] = []
    if seed is not None and wants_operational:
        visited, paths, depths, _graph_truncated = await _expand_graph(session, seed, effective_depth)
        neighbors = sorted(
            (
                (entity, depths[entity.id], paths[entity.id])
                for entity_id, entity in visited.items()
                if entity_id != seed.id
            ),
            key=lambda row: (row[1], str(row[0].id)),
        )

    if wants_operational:
        operational, resolved, operational_trace, operational_truncated = await _operational_evidence(
            session,
            seed=seed,
            terms=terms,
            since=since_dt,
            until=until_dt,
            effective_depth=effective_depth,
        )
        candidates.extend(operational)
        trace.extend(operational_trace)
        truncated = truncated or operational_truncated
        sources_used.append("forkos")

    vault_unavailable = False
    if wants_knowledge:
        root = _vault_root()
        if root is None:
            vault_unavailable = True
            _add_warning(
                warnings,
                "VAULT_UNAVAILABLE: the Obsidian Vault is not configured or not readable; "
                "knowledge evidence was skipped.",
            )
            if scope == "knowledge":
                raise EvidenceError(
                    "VAULT_UNAVAILABLE",
                    "The Obsidian Vault is not configured or not readable; knowledge evidence "
                    "is unavailable.",
                )
        else:
            index = vault_ev.scan_evidence_notes(root, terms)
            knowledge, knowledge_trace, knowledge_truncated = await _knowledge_evidence(
                root=root,
                terms=terms,
                seed=seed,
                neighbors=neighbors,
                index=index,
                warnings=warnings,
            )
            candidates.extend(knowledge)
            trace.extend(knowledge_trace)
            truncated = truncated or knowledge_truncated
            sources_used.append("f0rknbrain")
    else:
        trace.append(
            RetrievalTraceStep(
                stage="managed_knowledge",
                description="Knowledge channels skipped: scope does not include knowledge.",
                considered=0,
                accepted=0,
                truncated=False,
            )
        )
        trace.append(
            RetrievalTraceStep(
                stage="wikilinks",
                description="Knowledge channels skipped: scope does not include knowledge.",
                considered=0,
                accepted=0,
                truncated=False,
            )
        )
        trace.append(
            RetrievalTraceStep(
                stage="backlinks",
                description="Knowledge channels skipped: scope does not include knowledge.",
                considered=0,
                accepted=0,
                truncated=False,
            )
        )
        trace.append(
            RetrievalTraceStep(
                stage="vault_lexical",
                description="Knowledge channels skipped: scope does not include knowledge.",
                considered=0,
                accepted=0,
                truncated=False,
            )
        )

    if wants_knowledge and not wants_operational:
        # Knowledge-only: operasyonel aşamalar ATLANIR ama izden DÜŞMEZ; aksi
        # hâlde iz yapısı kapsama göre değişir ve karşılaştırılamaz olurdu (§130).
        trace.append(
            RetrievalTraceStep(
                stage="entity_resolution",
                description=(
                    "Knowledge-only scope: an explicit entity was used only as a stable bridge "
                    "to its managed note; no operational resolution ran."
                ),
                considered=1 if seed is not None else 0,
                accepted=1 if seed is not None else 0,
                truncated=False,
            )
        )
        trace.append(
            RetrievalTraceStep(
                stage="graph",
                description=(
                    "Graph expansion skipped: operational Link traversal belongs to the "
                    "operational scope."
                ),
                considered=0,
                accepted=0,
                truncated=False,
            )
        )
        trace.append(
            RetrievalTraceStep(
                stage="events",
                description=(
                    "Event evidence skipped: append-only history is operational state and "
                    "requires the operational scope."
                ),
                considered=0,
                accepted=0,
                truncated=False,
            )
        )

    evidence, omitted, budget_truncated = _select_evidence(candidates, limit=requested_limit)
    truncated = truncated or budget_truncated
    trace.append(
        RetrievalTraceStep(
            stage="budget",
            description=(
                f"Ranked {len(candidates)} candidate(s) by provenance priority, deduplicated by "
                f"evidence ID and applied the item/character budgets (limit={requested_limit}, "
                f"total_chars={MAX_TOTAL_EVIDENCE_CHARS})."
            ),
            considered=len(candidates),
            accepted=len(evidence),
            truncated=budget_truncated,
        )
    )

    return EvidenceBundle(
        query=query_text,
        entity_seed=str(seed.id) if seed is not None else None,
        resolved_entities=resolved,
        evidence=evidence,
        retrieval_trace=_ordered_trace(trace),
        sources_used=sources_used,
        truncated=truncated,
        omitted_total=omitted,
        warnings=warnings,
        recovery_hint=_recovery_hint(
            has_seed=seed is not None,
            evidence_count=len(evidence),
            candidate_count=len([ref for ref in resolved if ref.resolution == "lexical_candidate"]),
            vault_unavailable=vault_unavailable,
            wants_knowledge=wants_knowledge,
        ),
    )
