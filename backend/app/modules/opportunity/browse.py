"""Fırsat çalışma alanı için filtreli, sayfalanmış okuma sorguları."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Integer, String, case, cast, extract, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.modules.opportunity.models import Opportunity
from app.modules.opportunity.schemas import OpportunityBrowseOut
from app.modules.opportunity.service import _out, attach_applications


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
    archetype: str | None = None
    recommendation: str | None = None
    period_days: int | None = None
    year: int | None = None
    min_score: float | None = None
    max_score: float | None = None
    skill: str | None = None
    min_skill_match: float | None = None
    max_skill_match: float | None = None
    #: any | computed | uncomputed -- null semantigini kaybetmemek icin.
    skill_match_state: str | None = None
    sort: str = "score"
    offset: int = 0
    limit: int = 40


def _effective_date():
    return func.coalesce(Opportunity.published_at, Opportunity.found_at)


def _conditions(filters: BrowseFilters):
    conditions = []
    if filters.section == "trash":
        conditions.append(Opportunity.trashed_at.is_not(None))
    else:
        conditions.append(Opportunity.trashed_at.is_(None))
        conditions.append(
            Opportunity.kind == "job" if filters.section == "jobs" else Opportunity.kind != "job"
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
    if filters.region:
        conditions.append(Opportunity.region == filters.region)
    if filters.remote:
        conditions.append(_remote_bucket() == filters.remote)
    if filters.archetype:
        conditions.append(Opportunity.evaluation["archetype"].astext == filters.archetype)
    if filters.recommendation:
        conditions.append(Opportunity.evaluation["recommendation"].astext == filters.recommendation)
    # Skor araligi KAPSAYICIDIR (min <= score <= max). null skor aralik
    # filtrelerine girmez; 0 ile -1 ayri degerlerdir.
    if filters.min_score is not None:
        conditions.append(Opportunity.score >= filters.min_score)
    if filters.max_score is not None:
        conditions.append(Opportunity.score <= filters.max_score)
    effective_date = _effective_date()
    if filters.period_days:
        conditions.append(effective_date >= datetime.now(UTC) - timedelta(days=filters.period_days))
    if filters.year:
        conditions.append(extract("year", effective_date) == filters.year)
    if filters.skill and filters.skill.strip():
        # reasons JSONB'de METIN olarak duruyor; beceri eslesmesi baslik ve
        # aciklamadan yapilir (has_key ifadesi sessizce hicbir sey dondurmuyordu).
        needle = f"%{filters.skill.strip().lower()}%"
        description = func.lower(func.coalesce(Opportunity.raw["forkjob"]["description"].astext, ""))
        conditions.append(
            func.lower(Entity.title).like(needle) | description.like(needle)
        )
    if filters.min_skill_match is not None:
        conditions.append(Opportunity.skill_match_ratio >= filters.min_skill_match)
    if filters.max_skill_match is not None:
        conditions.append(Opportunity.skill_match_ratio <= filters.max_skill_match)
    if filters.skill_match_state == "computed":
        conditions.append(Opportunity.skill_match_ratio.is_not(None))
    elif filters.skill_match_state == "uncomputed":
        conditions.append(Opportunity.skill_match_ratio.is_(None))
    if filters.search and filters.search.strip():
        query = func.plainto_tsquery("simple", func.immutable_unaccent(filters.search.strip()))
        conditions.append(Entity.search_vec.op("@@")(query))
    return conditions


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
    effective_date = _effective_date()
    # Deterministik tie-break: sayfalama sirasinda kayit atlanmaz/tekrarlanmaz.
    stable = (Entity.title.asc(), Opportunity.id.asc())
    if filters.sort == "oldest":
        return (effective_date.asc(), *stable)
    if filters.sort == "deadline":
        return (Opportunity.deadline_at.asc().nulls_last(), effective_date.desc(), *stable)
    if filters.sort == "skill_match":
        # Yuksek oran once; esitlikte genel skor, sonra tarih, sonra id/title.
        # Hesaplanmamis (null) oranlar en sonda kalir.
        return (
            Opportunity.skill_match_ratio.desc().nulls_last(),
            Opportunity.score.desc().nulls_last(),
            effective_date.desc(),
            *stable,
        )
    if filters.sort == "newest" or filters.section == "announcements":
        return (effective_date.desc(), *stable)
    if filters.sort == "score_asc":
        return (Opportunity.score.asc().nulls_last(), effective_date.desc(), *stable)
    return (Opportunity.score.desc().nulls_last(), effective_date.desc(), *stable)


def _facet_expressions(filters: BrowseFilters) -> dict[str, object]:
    """Facet ifadeleri. Filtre ile facet AYNI ifadeyi kullanir."""
    items: dict[str, object] = {
        "categories": Opportunity.category,
        "sources": Opportunity.source,
        "statuses": Opportunity.status,
        "regions": Opportunity.region,
        "remote": _remote_bucket(),
        "archetypes": Opportunity.evaluation["archetype"].astext,
        "recommendations": Opportunity.evaluation["recommendation"].astext,
        "years": cast(extract("year", _effective_date()), Integer),
    }
    if filters.section == "announcements":
        items["announcement_sources"] = case(
            (Opportunity.source == "ylsy", literal("ylsy")),
            (Opportunity.source == "osym", literal("osym")),
            else_=literal("other"),
        )
    return items


async def _facets(
    session: AsyncSession, conditions, filters: BrowseFilters
) -> dict[str, dict[str, int]]:
    """Tum facet'leri TEK gidis-donusle uretir (onceden 8 ardil sorgu vardi).

    Her facet ayni WHERE kosullarini ve filtreyle ayni ifadeyi kullanir; bu
    yuzden chip sayisi ile chip'e tiklayinca gelen kayit sayisi tutarlidir.
    """
    expressions = _facet_expressions(filters)
    parts = [
        select(
            literal(name, String).label("facet"),
            cast(expr, String).label("value"),
            func.count().label("count"),
        )
        .select_from(Opportunity)
        .join(Entity, Entity.id == Opportunity.id)
        .where(*conditions, expr.is_not(None))
        .group_by(cast(expr, String))
        for name, expr in expressions.items()
    ]
    rows = (await session.execute(union_all(*parts))).all()
    facets: dict[str, dict[str, int]] = {name: {} for name in expressions}
    for facet, value, count in rows:
        if facet is None or value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        facets[facet][text] = facets[facet].get(text, 0) + count
    return facets


async def browse_opportunities(
    session: AsyncSession, filters: BrowseFilters
) -> OpportunityBrowseOut:
    conditions = _conditions(filters)
    base = (
        select(Opportunity, Entity.title)
        .join(Entity, Entity.id == Opportunity.id)
        .where(*conditions)
    )
    rows = (
        await session.execute(
            base.order_by(*_order(filters)).offset(filters.offset).limit(filters.limit)
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
    # Facet'lar sayfalama (offset > 0) sirasinda degismez; yalnizca ilk sayfada hesaplanir.
    facets = await _facets(session, conditions, filters) if filters.offset == 0 else {}

    out_items = [_out(row, include_raw=False) for row in rows]
    from app.modules.opportunity.intelligence import enrich_opportunities

    out_items = await enrich_opportunities(session, rows, out_items)
    out_items = await attach_applications(session, rows, out_items)
    return OpportunityBrowseOut(
        items=out_items,
        total=total,
        offset=filters.offset,
        limit=filters.limit,
        section_counts={
            "jobs": count_row[0],
            "announcements": count_row[1],
            "trash": count_row[2],
        },
        facets=facets,
    )
