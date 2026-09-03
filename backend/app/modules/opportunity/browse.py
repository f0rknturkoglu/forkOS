"""Fırsat çalışma alanı için filtreli, sayfalanmış okuma sorguları."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Float, case, cast, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.modules.opportunity.models import Opportunity
from app.modules.opportunity.schemas import OpportunityBrowseOut
from app.modules.opportunity.service import _out


@dataclass(frozen=True)
class BrowseFilters:
    section: str = "jobs"
    announcement_source: str | None = None
    category: str | None = None
    search: str | None = None
    status: str | None = None
    source: str | None = None
    region: str | None = None
    remote: str | None = None
    period_days: int | None = None
    year: int | None = None
    min_score: float | None = None
    max_score: float | None = None
    skill: str | None = None
    min_skill_match: float | None = None
    sort: str = "score"
    offset: int = 0
    limit: int = 40


def _conditions(filters: BrowseFilters):
    conditions = []
    if filters.section == "trash":
        conditions.append(Opportunity.trashed_at.is_not(None))
    else:
        conditions.append(Opportunity.trashed_at.is_(None))
        conditions.append(
            Opportunity.kind == "job"
            if filters.section == "jobs"
            else Opportunity.kind != "job"
        )
    if filters.announcement_source == "ylsy":
        conditions.append(Opportunity.source == "ylsy")
    elif filters.announcement_source == "osym":
        conditions.append(Opportunity.source == "osym")
    elif filters.announcement_source == "other":
        conditions.append(Opportunity.source.not_in(("ylsy", "osym")))
    if filters.category:
        conditions.append(Opportunity.category == filters.category)
    if filters.status:
        conditions.append(Opportunity.status == filters.status)
    if filters.source:
        conditions.append(Opportunity.source == filters.source)
    if filters.remote:
        conditions.append(_remote_bucket() == filters.remote)
    score = _score_expression()
    if filters.min_score is not None:
        conditions.append(score >= filters.min_score)
    if filters.max_score is not None:
        conditions.append(score <= filters.max_score)
    effective_date = func.coalesce(Opportunity.published_at, Opportunity.found_at)
    if filters.period_days:
        conditions.append(
            effective_date >= datetime.now(UTC) - timedelta(days=filters.period_days)
        )
    if filters.year:
        conditions.append(extract("year", effective_date) == filters.year)
    if filters.skill and filters.skill.strip():
        s = filters.skill.strip().lower()
        conditions.append(
            Opportunity.raw["forkjob"]["reasons"].astext.ilike(f'%"{s}"%')
            | Entity.title.ilike(f"%{s}%")
        )
    if filters.min_skill_match is not None and filters.min_skill_match > 0:
        conditions.append(
            Opportunity.raw["forkjob"]["reasons"].astext.ilike('%"skills":%')
        )
    if filters.search and filters.search.strip():
        query = func.plainto_tsquery(
            "simple", func.immutable_unaccent(filters.search.strip())
        )
        conditions.append(Entity.search_vec.op("@@")(query))
    return conditions


def _score_expression():
    return cast(Opportunity.raw["forkjob"]["score"].astext, Float)


def _remote_bucket():
    """Ham remote metnini kanonik kovalara indirger.

    Frontend `remoteKind`'ın aynı semantiği: remote/hybrid anahtar kelimeleri
    (TR + EN), bilinen ofis sözcükleri onsite; gerisi unknown. Facet ve filtre
    aynı ifadeyi kullanır — chip'e tıklayınca liste o chip ile eşleşir.
    """
    raw = func.lower(func.coalesce(Opportunity.remote, ""))
    return case(
        (
            raw.like("%remote%")
            | raw.like("%uzaktan%")
            | raw.like("%wfh%")
            | raw.like("%uzak çalışma%"),
            "remote",
        ),
        (
            raw.like("%hybrid%") | raw.like("%hibrit%") | raw.like("%karma%"),
            "hybrid",
        ),
        (raw.in_(["onsite", "office", "on-site", "ofis"]), "onsite"),
        else_="unknown",
    )


def _order(filters: BrowseFilters):
    effective_date = func.coalesce(Opportunity.published_at, Opportunity.found_at)
    stable = (Entity.title.asc(), Opportunity.id.asc())
    score = _score_expression()
    if filters.sort == "oldest":
        return (effective_date.asc(), *stable)
    if filters.sort == "deadline":
        return (Opportunity.deadline_at.asc().nulls_last(), effective_date.desc(), *stable)
    if filters.sort == "skill_match":
        has_skills = case(
            (Opportunity.raw["forkjob"]["reasons"].astext.like('%"skills":%'), 1),
            else_=0,
        )
        return (has_skills.desc(), score.desc().nulls_last(), effective_date.desc(), *stable)
    if filters.sort == "newest" or filters.section == "announcements":
        return (effective_date.desc(), *stable)
    if filters.sort == "score_asc":
        return (score.asc().nulls_last(), effective_date.desc(), *stable)
    return (score.desc().nulls_last(), effective_date.desc(), *stable)


async def _facet(
    session: AsyncSession, conditions, expression, *, label: str
) -> dict[str, int]:
    rows = (
        await session.execute(
            select(expression.label(label), func.count())
            .select_from(Opportunity)
            .join(Entity, Entity.id == Opportunity.id)
            .where(*conditions, expression.is_not(None))
            .group_by(expression)
        )
    ).all()
    return {str(value): count for value, count in rows}


async def browse_opportunities(
    session: AsyncSession, filters: BrowseFilters
) -> OpportunityBrowseOut:
    conditions = _conditions(filters)
    base = (
        select(Opportunity, Entity.title)
        .join(Entity, Entity.id == Opportunity.id)
        .where(*conditions)
    )
    fetch_limit = (
        filters.limit * 3
        if (filters.min_skill_match or filters.sort == "skill_match")
        else filters.limit
    )
    rows = (
        await session.execute(
            base.order_by(*_order(filters)).offset(filters.offset).limit(fetch_limit)
        )
    ).all()
    total = (
        await session.execute(
            select(func.count())
            .select_from(Opportunity)
            .join(Entity, Entity.id == Opportunity.id)
            .where(*conditions)
        )
    ).scalar_one()

    active = Opportunity.trashed_at.is_(None)
    count_row = (
        await session.execute(
            select(
                func.count().filter(active, Opportunity.kind == "job"),
                func.count().filter(active, Opportunity.kind != "job"),
                func.count().filter(Opportunity.trashed_at.is_not(None)),
            ).select_from(Opportunity)
        )
    ).one()
    announcement_group = case(
        (Opportunity.source == "ylsy", "ylsy"),
        (Opportunity.source == "osym", "osym"),
        else_="other",
    )
    # Facet'lar sayfalama (offset > 0) sirasinda degismez; yalnizca ilk sayfada (offset == 0) hesaplanir.
    if filters.offset == 0:
        facets = {
            "categories": await _facet(
                session, conditions, Opportunity.category, label="category"
            ),
            "sources": await _facet(session, conditions, Opportunity.source, label="source"),
            "statuses": await _facet(session, conditions, Opportunity.status, label="status"),
            "regions": await _facet(session, conditions, Opportunity.region, label="region"),
            "remote": await _facet(session, conditions, _remote_bucket(), label="remote"),
            "years": await _facet(
                session,
                conditions,
                extract("year", func.coalesce(Opportunity.published_at, Opportunity.found_at)),
                label="year",
            ),
        }
        if filters.section == "announcements":
            facets["announcement_sources"] = await _facet(
                session, conditions, announcement_group, label="announcement_source"
            )
    else:
        facets = {}
    out_items = [_out(row, include_raw=False) for row in rows]
    if filters.min_skill_match is not None and filters.min_skill_match > 0:
        out_items = [
            it for it in out_items
            if it.skill_match and it.skill_match.match_ratio >= filters.min_skill_match
        ]
    if filters.sort == "skill_match":
        out_items.sort(
            key=lambda it: (it.skill_match.match_ratio if it.skill_match else 0.0, it.score or 0.0),
            reverse=True,
        )
    return OpportunityBrowseOut(
        items=out_items[:filters.limit],
        total=total if filters.min_skill_match is None else len(out_items),
        offset=filters.offset,
        limit=filters.limit,
        section_counts={
            "jobs": count_row[0],
            "announcements": count_row[1],
            "trash": count_row[2],
        },
        facets=facets,
    )
