"""Career Ops: mulakat hafizasi, gerceklik denetimi ve yerel warm-intro agi."""

from __future__ import annotations

import csv
import hashlib
import io
import re
import unicodedata
import uuid
from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import archive_entity, create_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity
from app.modules.opportunity import service
from app.modules.opportunity.intelligence import parse_compensation
from app.modules.opportunity.models import (
    Application,
    CareerConnection,
    CareerStory,
    Interview,
    Opportunity,
)
from app.modules.opportunity.schemas import (
    CareerConnectionOut,
    CareerConnectionsImportOut,
    CareerStoryIn,
    CareerStoryOut,
    CareerStoryPatch,
    CoverLetterOut,
    CoverLetterReviewOut,
    InterviewOut,
    InterviewPrepOut,
    OpportunityConnectionsOut,
    SalaryClaimOut,
    SalaryConsistencyOut,
)

COMPANY_STOP_WORDS = {
    "a",
    "as",
    "co",
    "company",
    "corp",
    "corporation",
    "gmbh",
    "group",
    "inc",
    "limited",
    "llc",
    "ltd",
    "plc",
    "sirketi",
    "the",
}

CONNECTION_HEADERS = {
    "first_name": ("first name", "ad"),
    "last_name": ("last name", "soyad"),
    "profile_url": ("url", "profile url", "linkedin url"),
    "email": ("email address", "email", "e-posta"),
    "company": ("company", "company name", "şirket", "sirket"),
    "position": ("position", "title", "pozisyon"),
    "connected_on": ("connected on", "connection date", "bağlantı tarihi"),
}

GENERIC_COVER_PHRASES = (
    "i am excited to apply",
    "i am thrilled to apply",
    "leverage my skills",
    "dynamic team",
    "fast-paced environment",
    "passionate about",
    "perfect fit",
    "dear hiring manager",
    "to whom it may concern",
    "delve into",
)

COMMON_WORDS = {
    "about",
    "after",
    "again",
    "because",
    "before",
    "could",
    "from",
    "have",
    "into",
    "other",
    "that",
    "their",
    "there",
    "these",
    "this",
    "using",
    "with",
    "would",
}


def normalize_company(value: str | None) -> str:
    """Kurum adini hukuki eklerden arindirip kararlı token anahtarina cevirir."""
    if not value:
        return ""
    ascii_value = "".join(
        char
        for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )
    tokens = re.findall(r"[a-z0-9]+", ascii_value.replace("&", " and "))
    return " ".join(sorted({token for token in tokens if token not in COMPANY_STOP_WORDS}))


def _connection_identity(row: dict[str, str]) -> str:
    stable = (
        (
            row.get("profile_url")
            or row.get("email")
            or "|".join(
                (
                    row.get("first_name", ""),
                    row.get("last_name", ""),
                    normalize_company(row.get("company")),
                    row.get("position", ""),
                )
            )
        )
        .strip()
        .casefold()
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _parse_connected_on(value: str | None) -> date | None:
    if not value:
        return None
    for pattern in ("%d %b %Y", "%d %B %Y", "%m/%d/%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(value.strip(), pattern).date()
        except ValueError:
            continue
    return None


def _decode_csv(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "cp1254", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Connections.csv metin kodlamasi okunamadi")


def parse_connections_csv(content: bytes) -> list[dict[str, str]]:
    """LinkedIn'in basina aciklama satiri koyabilen CSV disari aktarimini okur."""
    text = _decode_csv(content)
    lines = text.splitlines()
    header_index = next(
        (
            index
            for index, line in enumerate(lines)
            if "first name" in line.casefold() and "company" in line.casefold()
        ),
        None,
    )
    if header_index is None:
        raise ValueError("Connections.csv basliklari bulunamadi")
    reader = csv.DictReader(io.StringIO("\n".join(lines[header_index:])))
    result: list[dict[str, str]] = []
    for raw in reader:
        normalized_raw = {
            (key or "").strip().casefold(): (value or "").strip() for key, value in raw.items()
        }
        row = {
            field: next(
                (normalized_raw.get(alias, "") for alias in aliases if normalized_raw.get(alias)),
                "",
            )
            for field, aliases in CONNECTION_HEADERS.items()
        }
        if any(row.values()):
            result.append(row)
    return result


def _connection_name(connection: CareerConnection) -> str:
    return " ".join(
        part for part in (connection.first_name, connection.last_name) if part
    ).strip() or (connection.email or connection.profile_url or "Adsiz baglanti")


def _connection_out(connection: CareerConnection) -> CareerConnectionOut:
    return CareerConnectionOut(
        id=connection.id,
        name=_connection_name(connection),
        first_name=connection.first_name,
        last_name=connection.last_name,
        profile_url=connection.profile_url,
        email=connection.email,
        company=connection.company,
        position=connection.position,
        connected_on=connection.connected_on,
    )


async def import_connections(
    session: AsyncSession,
    content: bytes,
) -> CareerConnectionsImportOut:
    rows = parse_connections_csv(content)
    keys = {_connection_identity(row) for row in rows}
    existing = {
        item.identity_key: item
        for item in (
            await session.execute(
                select(CareerConnection).where(CareerConnection.identity_key.in_(keys))
            )
        ).scalars()
    }
    created = updated = skipped = 0
    for row in rows:
        identity_key = _connection_identity(row)
        title = " ".join(part for part in (row["first_name"], row["last_name"]) if part).strip()
        title = title or row["email"] or row["profile_url"] or "Adsiz baglanti"
        search_text = " ".join(
            value
            for value in (row["email"], row["company"], row["position"], row["profile_url"])
            if value
        )
        connection = existing.get(identity_key)
        values = {
            "first_name": row["first_name"] or None,
            "last_name": row["last_name"] or None,
            "profile_url": row["profile_url"] or None,
            "email": row["email"] or None,
            "company": row["company"] or None,
            "normalized_company": normalize_company(row["company"]),
            "position": row["position"] or None,
            "connected_on": _parse_connected_on(row["connected_on"]),
        }
        if connection is None:
            entity = await create_entity(
                session,
                type="career_connection",
                title=title,
                search_text=search_text,
            )
            connection = CareerConnection(id=entity.id, identity_key=identity_key, **values)
            session.add(connection)
            existing[identity_key] = connection
            created += 1
            continue
        changed = any(getattr(connection, key) != value for key, value in values.items())
        if not changed:
            skipped += 1
            continue
        for key, value in values.items():
            setattr(connection, key, value)
        await touch_entity(session, connection.id, title=title, search_text=search_text)
        updated += 1
    await log_event(
        session,
        verb="career_connections.imported",
        entity_type="career_connection",
        payload={"rows": len(rows), "created": created, "updated": updated, "skipped": skipped},
    )
    await session.commit()
    return CareerConnectionsImportOut(
        total_rows=len(rows),
        created=created,
        updated=updated,
        skipped=skipped,
    )


async def list_connections(
    session: AsyncSession,
    *,
    search: str | None = None,
    limit: int = 200,
) -> list[CareerConnectionOut]:
    statement = (
        select(CareerConnection)
        .join(Entity, Entity.id == CareerConnection.id)
        .where(Entity.archived_at.is_(None))
        .order_by(Entity.title, CareerConnection.company)
        .limit(limit)
    )
    if search and search.strip():
        needle = f"%{search.strip()}%"
        statement = statement.where(
            Entity.title.ilike(needle)
            | Entity.search_text.ilike(needle)
            | CareerConnection.company.ilike(needle)
        )
    return [_connection_out(item) for item in (await session.execute(statement)).scalars()]


def _company_matches(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    left_tokens, right_tokens = set(left.split()), set(right.split())
    if not left_tokens or not right_tokens:
        return False
    shared = left_tokens & right_tokens
    return bool(shared) and len(shared) / min(len(left_tokens), len(right_tokens)) >= 0.75


async def opportunity_connections(
    session: AsyncSession,
    opportunity_id: uuid.UUID,
) -> OpportunityConnectionsOut | None:
    opportunity = await session.get(Opportunity, opportunity_id)
    if opportunity is None:
        return None
    normalized = normalize_company(opportunity.organization)
    if not normalized:
        return OpportunityConnectionsOut(organization=opportunity.organization)
    rows = (
        await session.execute(
            select(CareerConnection)
            .join(Entity, Entity.id == CareerConnection.id)
            .where(Entity.archived_at.is_(None), CareerConnection.normalized_company.is_not(None))
            .order_by(Entity.title)
        )
    ).scalars()
    matches = [item for item in rows if _company_matches(normalized, item.normalized_company or "")]
    return OpportunityConnectionsOut(
        organization=opportunity.organization,
        normalized_organization=normalized,
        connections=[_connection_out(item) for item in matches],
    )


def _story_search_text(data: CareerStoryIn | CareerStoryPatch, *, title: str) -> str:
    values = [
        title,
        data.situation,
        data.task,
        data.action,
        data.result,
        data.reflection,
        " ".join(data.tags or []),
    ]
    return " ".join(value for value in values if value)


def _story_out(story: CareerStory, title: str, updated_at) -> CareerStoryOut:
    return CareerStoryOut(
        id=story.id,
        title=title,
        situation=story.situation,
        task=story.task,
        action=story.action,
        result=story.result,
        reflection=story.reflection,
        provenance=story.provenance,
        tags=story.tags or [],
        updated_at=updated_at,
    )


async def list_stories(session: AsyncSession) -> list[CareerStoryOut]:
    rows = (
        await session.execute(
            select(CareerStory, Entity.title, Entity.updated_at)
            .join(Entity, Entity.id == CareerStory.id)
            .where(Entity.archived_at.is_(None))
            .order_by(Entity.updated_at.desc(), Entity.title)
        )
    ).all()
    return [_story_out(story, title, updated_at) for story, title, updated_at in rows]


async def create_story(session: AsyncSession, data: CareerStoryIn) -> CareerStoryOut:
    entity = await create_entity(
        session,
        type="career_story",
        title=data.title,
        search_text=_story_search_text(data, title=data.title),
    )
    story = CareerStory(
        id=entity.id,
        situation=data.situation,
        task=data.task,
        action=data.action,
        result=data.result,
        reflection=data.reflection,
        provenance=data.provenance,
        tags=data.tags,
    )
    session.add(story)
    await log_event(
        session,
        verb="career_story.created",
        entity_id=entity.id,
        entity_type="career_story",
        payload={"provenance": data.provenance},
    )
    await session.commit()
    await session.refresh(entity)
    return _story_out(story, entity.title, entity.updated_at)


async def patch_story(
    session: AsyncSession,
    story_id: uuid.UUID,
    data: CareerStoryPatch,
) -> CareerStoryOut | None:
    row = (
        await session.execute(
            select(CareerStory, Entity)
            .join(Entity, Entity.id == CareerStory.id)
            .where(CareerStory.id == story_id)
        )
    ).first()
    if row is None:
        return None
    story, entity = row
    patch = data.model_dump(exclude_unset=True)
    title = patch.pop("title", None) or entity.title
    for key, value in patch.items():
        setattr(story, key, value)
    await touch_entity(
        session,
        story.id,
        title=title,
        search_text=_story_search_text(
            CareerStoryPatch(
                situation=story.situation,
                task=story.task,
                action=story.action,
                result=story.result,
                reflection=story.reflection,
                provenance=story.provenance,
                tags=story.tags,
            ),
            title=title,
        ),
    )
    await log_event(
        session,
        verb="career_story.updated",
        entity_id=story.id,
        entity_type="career_story",
        payload={"provenance": story.provenance},
    )
    await session.commit()
    await session.refresh(entity)
    return _story_out(story, entity.title, entity.updated_at)


async def archive_story(session: AsyncSession, story_id: uuid.UUID) -> bool:
    story = await session.get(CareerStory, story_id)
    if story is None:
        return False
    await archive_entity(session, story_id)
    await log_event(
        session,
        verb="career_story.archived",
        entity_id=story_id,
        entity_type="career_story",
    )
    await session.commit()
    return True


async def salary_consistency(
    session: AsyncSession,
    opportunity_id: uuid.UUID,
) -> SalaryConsistencyOut:
    interviews = list(
        (
            await session.execute(
                select(Interview)
                .where(
                    Interview.opportunity_id == opportunity_id,
                    Interview.salary_stated.is_not(None),
                )
                .order_by(Interview.position)
            )
        ).scalars()
    )
    application = await session.get(Application, opportunity_id)
    return salary_consistency_of(application, interviews)


def salary_consistency_of(
    application: Application | None,
    interviews: Sequence[Interview],
) -> SalaryConsistencyOut:
    """Saf hesap: toplu okuma yapan cagiranlar da ayni kurali kullanir."""
    claims: list[SalaryClaimOut] = []
    normalized: set[tuple[int | None, int | None, str | None]] = set()
    if application and application.salary_expectation:
        app_stmt = application.salary_expectation.strip()
        if app_stmt:
            low, high, currency = parse_compensation(app_stmt)
            claims.append(
                SalaryClaimOut(
                    interview_id=application.opportunity_id,
                    stage="Başvuru beklentisi",
                    statement=app_stmt,
                    pay_min=low,
                    pay_max=high,
                    currency=currency,
                )
            )
            if low is not None:
                normalized.add((low, high, currency))
    for interview in interviews:
        statement = (interview.salary_stated or "").strip()
        if not statement:
            continue
        low, high, currency = parse_compensation(statement)
        claims.append(
            SalaryClaimOut(
                interview_id=interview.id,
                stage=interview.stage,
                statement=statement,
                pay_min=low,
                pay_max=high,
                currency=currency,
            )
        )
        if low is not None:
            normalized.add((low, high, currency))
    inconsistent = len(normalized) > 1
    return SalaryConsistencyOut(
        inconsistent=inconsistent,
        claims=claims,
        warning=(
            "Başvuru formu ve mülakat turlarında belirtilen ücret tutarları birbiriyle uyuşmuyor."
            if inconsistent
            else None
        ),
    )


def _significant_words(value: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-zA-ZÀ-ž0-9+#.]+", value.casefold())
        if len(word) >= 5 and word not in COMMON_WORDS
    }


def _story_matches(text: str, stories: Sequence[CareerStoryOut]) -> list[uuid.UUID]:
    letter_words = _significant_words(text)
    result: list[uuid.UUID] = []
    for story in stories:
        tag_words = _significant_words(" ".join(story.tags))
        evidence = " ".join(
            value or ""
            for value in (
                story.title,
                story.situation,
                story.task,
                story.action,
                story.result,
                story.reflection,
            )
        )
        # Bir etiket bilincli olarak verilen, diller arasi da korunabilen guclu
        # bir bagdir. Serbest metinde ise yanlis eslesmeyi azaltmak icin iki
        # ayri kanit kelimesi ariyoruz.
        if letter_words & tag_words or len(letter_words & _significant_words(evidence)) >= 2:
            result.append(story.id)
    return result


async def review_cover_letter(session: AsyncSession, text: str) -> CoverLetterReviewOut:
    lowered = text.casefold()
    generic = [phrase for phrase in GENERIC_COVER_PHRASES if phrase in lowered]
    stories = await list_stories(session)
    matched_story_ids = _story_matches(text, stories)
    sentences = [chunk.strip() for chunk in re.split(r"[.!?]+", text) if chunk.strip()]
    has_metric = re.search(
        r"\b\d+(?:[.,]\d+)?\s*(?:%|x|k|m|users?|clients?|days?|weeks?)?\b", text, re.I
    )
    first_person = len(re.findall(r"\b(?:i|my|we|our|ben|benim|biz|bizim)\b", lowered))

    flags: list[str] = []
    suggestions: list[str] = []
    if generic:
        flags.append("Genel ve kalıp ifadeler baskın.")
        suggestions.append("Kalıp girişleri çıkarıp doğrudan ilgili deneyim ve sonuçla başla.")
    if not matched_story_ids:
        flags.append("Hikâye bankasındaki somut deneyimlerle bağ zayıf.")
        suggestions.append("Bir STAR+R hikâyesinden eylem ve ölçülebilir sonucu ekle.")
    if not has_metric:
        flags.append("Ölçülebilir sonuç görünmüyor.")
        suggestions.append("Mümkünse süre, oran, kapsam veya çıktı ekle.")
    if len(sentences) < 3:
        flags.append("Metin bağlam kurmak için fazla kısa.")
    if first_person == 0:
        flags.append("Metin kişisel sahipliği göstermiyor.")
        suggestions.append("Senin ne yaptığını açık bir özne ve fiille belirt.")

    score = 82 - min(32, len(generic) * 8)
    score += 8 if matched_story_ids else -10
    score += 5 if has_metric else -8
    score += 3 if first_person >= 2 else -4
    score = min(100, max(0, score))
    return CoverLetterReviewOut(
        score=score,
        generic_phrases=generic,
        matched_story_ids=matched_story_ids,
        flags=flags,
        suggestions=suggestions,
    )


# ---------------------------------------------------------------------------
# Toplu okumalar: kariyer panelleri kayit basina istek atmaz.
# ---------------------------------------------------------------------------


def _job_application_rows_stmt():
    """Basvuru kayitlari: ilan + baslik + CRM satiri (tek sorgu)."""
    return (
        select(Opportunity, Entity.title, Application)
        .join(Entity, Entity.id == Opportunity.id)
        .join(Application, Application.opportunity_id == Opportunity.id)
        .where(Opportunity.trashed_at.is_(None))
        .order_by(Application.status_changed_at.desc().nulls_last(), Opportunity.id.asc())
    )


async def cover_letters(session: AsyncSession) -> list[CoverLetterOut]:
    """Kaydedilmis on yazilar TEK sorguda; panel kayit basina istek atmaz."""
    rows = (
        await session.execute(
            select(Opportunity.id, Entity.title, Opportunity.organization, Application.cover_letter)
            .join(Entity, Entity.id == Opportunity.id)
            .join(Application, Application.opportunity_id == Opportunity.id)
            .where(
                Opportunity.trashed_at.is_(None),
                Application.cover_letter.is_not(None),
                func.length(func.trim(Application.cover_letter)) > 0,
            )
            .order_by(Application.updated_at.desc(), Opportunity.id.asc())
        )
    ).all()
    return [
        CoverLetterOut(
            opportunity_id=opportunity_id, title=title, organization=organization, cover_letter=text
        )
        for opportunity_id, title, organization, text in rows
    ]


async def interview_prep(session: AsyncSession) -> list[InterviewPrepOut]:
    """Mulakat hazirligi: gorusmeler ve maas tutarliligi TEK turda okunur.

    Onceden her basvuru icin iki ayri istek atiliyordu (2N istek). Burada
    basvurular, gorusmeler ve CRM satirlari uc sorguda alinip bellekte
    gruplanir; maas tutarliligi ayni saf helper ile hesaplanir.
    """
    rows = (await session.execute(_job_application_rows_stmt())).all()
    if not rows:
        return []
    opportunity_ids = [opportunity.id for opportunity, _title, _app in rows]
    interviews: dict[uuid.UUID, list[Interview]] = {item_id: [] for item_id in opportunity_ids}
    for interview in (
        await session.execute(
            select(Interview)
            .where(Interview.opportunity_id.in_(opportunity_ids))
            .order_by(Interview.position)
        )
    ).scalars():
        interviews.setdefault(interview.opportunity_id, []).append(interview)

    groups: list[InterviewPrepOut] = []
    for opportunity, title, application in rows:
        rows_for_item = interviews.get(opportunity.id, [])
        groups.append(
            InterviewPrepOut(
                opportunity=service._out((opportunity, title), include_raw=False),
                interviews=[
                    InterviewOut(
                        id=interview.id,
                        opportunity_id=interview.opportunity_id,
                        stage=interview.stage,
                        mode=interview.mode,
                        scheduled_at=interview.scheduled_at,
                        duration_min=interview.duration_min,
                        notes=interview.notes,
                        outcome=interview.outcome,
                        salary_stated=interview.salary_stated,
                        position=interview.position,
                    )
                    for interview in rows_for_item
                ],
                salary=salary_consistency_of(application, rows_for_item),
            )
        )
    return groups
