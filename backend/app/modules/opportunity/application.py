"""Opportunity application CRM: basvuru akisi, gecmis, gorusme, takip, funnel."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import touch_entity
from app.core.events import log_event
from app.core.links import Link
from app.core.models import Entity
from app.core.time import local_zone
from app.modules import DeadlineRow
from app.modules.document.models import Document
from app.modules.opportunity import lifecycle
from app.modules.opportunity.cover_letter_integrity import sync_application_cover_letter
from app.modules.opportunity.models import (
    Application,
    ApplicationHistory,
    Interview,
    Opportunity,
)
from app.modules.opportunity.schemas import (
    ApplicationIn,
    ApplicationOut,
    ApplicationTimelineOut,
    ApplyIn,
    FollowupOut,
    FunnelBreakdownRow,
    FunnelOut,
    FunnelRow,
    FunnelVolumeRow,
    HistoryOut,
    InterviewIn,
    InterviewOut,
    OpportunityOut,
    TimelineEntryOut,
)

#: Geriye donuk isim: CRM akisinin sirasi artik lifecycle'dan gelir.
STATUS_FLOW = list(lifecycle.APPLICATION_FLOW)
TERMINAL_STATUSES = set(lifecycle.APPLICATION_TERMINAL)


REJECTION_REASONS = [
    "maas uyumsuz",
    "ilan kapandi",
    "uyum yetersiz",
    "cevap alinamadi",
    "pozisyon dolduruldu",
    "diger",
]


def _validate_transition(from_status: str, to_status: str) -> None:
    lifecycle.validate_application_transition(from_status, to_status)


_UNSET = object()


async def _record_status_change(
    session: AsyncSession,
    item: Opportunity,
    to_status: str,
    *,
    from_status: object = _UNSET,
    scope: str = "application",
    note: str | None = None,
) -> None:
    """Gecis gecmisini ve event i yazar; durum alani henuz degismemistir.

    ``from_status`` verilmezse ``item.status`` kullanilir; acikca ``None``
    verilirse "onceki durum yok" (ornek: ilk basvuru kaydi) demektir.
    """
    previous = item.status if from_status is _UNSET else from_status
    session.add(
        ApplicationHistory(
            id=uuid.uuid4(),
            opportunity_id=item.id,
            from_status=previous,
            to_status=to_status,
            scope=scope,
            note=note,
        )
    )
    await log_event(
        session,
        verb="opportunity.status_changed",
        entity_id=item.id,
        entity_type="opportunity",
        payload={"from": previous, "to": to_status, "scope": scope, "note": note},
    )


async def transition_status(
    session: AsyncSession,
    item_id: uuid.UUID,
    *,
    to: str,
    note: str | None = None,
) -> OpportunityOut | None:
    """Kesif/duyuru durumu gecisi (tur bazli kume)."""
    from app.modules.opportunity.service import _out

    item = await session.get(Opportunity, item_id)
    if item is None:
        return None
    if item.trashed_at is not None:
        raise ValueError("cop durumundaki kayit gecis kabul etmez")
    lifecycle.validate_discovery_transition(item.kind, item.status, to)
    await _record_status_change(session, item, to, scope="discovery", note=note)
    item.status = to
    await touch_entity(session, item.id)
    await session.commit()
    row = (
        await session.execute(
            select(Opportunity, Entity.title).join(Entity).where(Opportunity.id == item_id)
        )
    ).one()
    return _out(row)


async def transition_application(
    session: AsyncSession,
    item_id: uuid.UUID,
    *,
    to: str,
    note: str | None = None,
    rejection_reason: str | None = None,
) -> Application | None:
    """Basvuru hatti gecisi; basvuru kaydi yoksa dokunmaz."""
    app = await session.get(Application, item_id)
    item = await session.get(Opportunity, item_id)
    if app is None or item is None:
        return None
    if item.trashed_at is not None:
        raise ValueError("cop durumundaki kayit gecis kabul etmez")
    lifecycle.validate_application_transition(app.status, to)
    from_status = app.status
    if to == "rejected" and rejection_reason:
        item.rejection_reason = rejection_reason
    if to == "applied" and item.applied_at is None:
        item.applied_at = datetime.now(UTC)
    if to in lifecycle.APPLICATION_TERMINAL:
        item.follow_up_at = None
    app.status = to
    app.status_changed_at = datetime.now(UTC)
    app.updated_at = datetime.now(UTC)
    await _record_status_change(
        session, item, to, from_status=from_status, scope="application", note=note
    )
    await touch_entity(session, item.id)
    await session.commit()
    return app


async def get_application(
    session: AsyncSession,
    item_id: uuid.UUID,
) -> ApplicationOut | None:
    app = await session.get(Application, item_id)
    if app is None:
        return None
    return ApplicationOut(
        opportunity_id=app.opportunity_id,
        cv_document_id=app.cv_document_id,
        cv_title=app.cv_title,
        cv_modified_at=app.cv_modified_at,
        cover_letter=app.cover_letter,
        company_research=app.company_research,
        salary_expectation=app.salary_expectation,
        posting_snapshot=app.posting_snapshot or {},
        note=app.note,
        status=app.status,
        status_changed_at=app.status_changed_at,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


def _snapshot_posting(item: Opportunity) -> dict[str, Any]:
    """Basvuru anindaki ilan hali; sonraki degisikliklerden etkilenmez."""
    fk = (item.raw or {}).get("forkjob") or {}
    return {
        "url": item.url,
        "organization": item.organization,
        "location": item.location,
        "remote": item.remote,
        "compensation": item.compensation,
        "found_at": item.found_at.isoformat() if item.found_at else None,
        "description": fk.get("description") or (item.raw or {}).get("description") or "",
    }


async def apply(
    session: AsyncSession,
    item_id: uuid.UUID,
    data: ApplyIn,
) -> OpportunityOut | None:
    """Basvuru: basvuru kaydi 'applied' olur; kesif durumu kisayokta alinir."""
    from app.modules.opportunity.service import _out

    item = await session.get(Opportunity, item_id)
    if item is None:
        return None
    if not lifecycle.is_job_kind(item.kind):
        raise ValueError("Başvuru yalnızca iş ilanları için oluşturulabilir")
    doc = None
    doc_title = None
    if data.cv_document_id is not None:
        row = (
            await session.execute(
                select(Document, Entity.title)
                .join(Entity, Entity.id == Document.id)
                .where(Document.id == data.cv_document_id)
            )
        ).first()
        if row is not None:
            doc, doc_title = row

    app = await session.get(Application, item_id)
    now = datetime.now(UTC)
    if app is None:
        app = Application(
            opportunity_id=item_id,
            posting_snapshot=_snapshot_posting(item),
            status="applied",
            status_changed_at=now,
        )
        session.add(app)
        await _record_status_change(
            session, item, "applied", from_status=None, scope="application"
        )
    elif app.status != "applied":
        # Hazirlik asamasi (`preparing`) "Basvur" ile KESIN olarak basvuruya
        # gecer. Eskiden yalnizca CRM alanlari guncellenir, durum `preparing`
        # kalir ve hicbir gecmis/olay yazilmazdi: kullanici basvurdugunu
        # sandigi halde huni onu hic gormuyordu.
        lifecycle.validate_application_transition(app.status, "applied")
        from_status = app.status
        app.status = "applied"
        app.status_changed_at = now
        await _record_status_change(
            session, item, "applied", from_status=from_status, scope="application"
        )
    if doc is not None:
        app.cv_document_id = data.cv_document_id
        app.cv_title = doc_title
        app.cv_modified_at = doc.drive_modified_at
    if data.cover_letter is not None:
        sync_application_cover_letter(app, data.cover_letter)
    for key in ("company_research", "salary_expectation", "note"):
        value = getattr(data, key)
        if value is not None:
            setattr(app, key, value)
    app.updated_at = now

    if item.applied_at is None:
        item.applied_at = now
    # Kesif dongusunde ilan artik "kesfedildi" degil, takip ediliyor.
    if lifecycle.is_job_kind(item.kind) and item.status in {"discovered", "dismissed"}:
        await _record_status_change(
            session, item, "shortlisted", from_status=item.status, scope="discovery"
        )
        item.status = "shortlisted"
    # Basvuru ilanin kendi kaydini da tazeler: arama sonucu ve "son guncelleme"
    # basvuruyu gostermeli.
    await touch_entity(session, item.id)
    await session.commit()
    row = (
        await session.execute(
            select(Opportunity, Entity.title).join(Entity).where(Opportunity.id == item_id)
        )
    ).one()
    return _out(row, application=app)


async def upsert_application(
    session: AsyncSession,
    item_id: uuid.UUID,
    data: ApplicationIn,
) -> ApplicationOut | None:
    if await session.get(Opportunity, item_id) is None:
        return None
    app = await session.get(Application, item_id)
    if app is None:
        item = await session.get(Opportunity, item_id)
        if item is not None and not lifecycle.is_job_kind(item.kind):
            raise ValueError("Başvuru kaydı yalnızca iş ilanları için oluşturulabilir")
        # CRM alanlari kaydediliyorsa kayit artik takip ediliyor: hazirlik asamasi.
        app = Application(
            opportunity_id=item_id,
            status="preparing",
            status_changed_at=datetime.now(UTC),
        )
        session.add(app)
    if data.cv_document_id is not None:
        row = (
            await session.execute(
                select(Document, Entity.title)
                .join(Entity, Entity.id == Document.id)
                .where(Document.id == data.cv_document_id)
            )
        ).first()
        if row is not None:
            doc, doc_title = row
            app.cv_document_id = data.cv_document_id
            app.cv_title = doc_title
            app.cv_modified_at = doc.drive_modified_at
    if data.cover_letter is not None:
        sync_application_cover_letter(app, data.cover_letter)
    for key in ("company_research", "salary_expectation", "note"):
        value = getattr(data, key)
        if value is not None:
            setattr(app, key, value)
    app.updated_at = datetime.now(UTC)
    await session.commit()
    return await get_application(session, item_id)


async def list_history(session: AsyncSession, item_id: uuid.UUID) -> list[HistoryOut]:
    rows = await session.execute(
        select(ApplicationHistory)
        .where(ApplicationHistory.opportunity_id == item_id)
        .order_by(ApplicationHistory.at.desc())
    )
    return [
        HistoryOut(
            id=r.id,
            from_status=r.from_status,
            to_status=r.to_status,
            at=r.at,
            note=r.note,
            scope=r.scope,
        )
        for r in rows.scalars()
    ]


_DISCOVERY_LABELS = {
    "discovered": "İlan keşfedildi",
    "shortlisted": "Kısa listeye alındı",
    "dismissed": "İlan elendi",
    "archived": "İlan arşivlendi",
    "closed": "İlan kapandı",
    "new": "Duyuru alındı",
    "reviewed": "Duyuru incelendi",
    "watching": "Duyuru takibe alındı",
    "action_required": "Duyuruda aksiyon gerekiyor",
    "applied": "Başvuru yapıldı",
    "completed": "Duyuru tamamlandı",
    "expired": "Duyurunun süresi geçti",
}

_APPLICATION_LABELS = {
    "preparing": "Başvuru hazırlanıyor",
    "applied": "Başvuru gönderildi",
    "interview": "Görüşme aşamasına geçildi",
    "offer": "Teklif alındı",
    "accepted": "Teklif kabul edildi",
    "rejected": "Ret alındı",
    "withdrawn": "Başvuru geri çekildi",
    "closed": "Başvuru kapatıldı",
}


async def timeline(session: AsyncSession, item_id: uuid.UUID) -> ApplicationTimelineOut | None:
    """Birlesik basvuru zaman cizelgesi -- event/history kayitlarindan deterministik.

    Ayni girdiler her cagrida ayni sirada uretilir; hicbir alan tahmin edilmez.
    """
    from app.modules.opportunity.models import Interview
    from app.modules.todo.models import Todo

    item = await session.get(Opportunity, item_id)
    if item is None:
        return None

    entries: list[TimelineEntryOut] = []

    def add(
        kind: str,
        at: datetime | None,
        title: str,
        *,
        detail: str | None = None,
        status: str | None = None,
    ) -> None:
        if at is None:
            return
        entries.append(
            TimelineEntryOut(kind=kind, at=at, title=title, detail=detail, status=status)
        )

    add("discovered", item.found_at, "İlan keşfedildi", detail=item.source)

    history = (
        await session.execute(
            select(ApplicationHistory)
            .where(ApplicationHistory.opportunity_id == item_id)
            .order_by(ApplicationHistory.at)
        )
    ).scalars()
    for entry in history:
        if entry.scope == "discovery":
            add(
                "status",
                entry.at,
                _DISCOVERY_LABELS.get(entry.to_status, entry.to_status),
                detail=entry.note,
                status=entry.to_status,
            )
        else:
            kind = "status"
            if entry.to_status == "offer":
                kind = "offer"
            elif entry.to_status == "rejected":
                kind = "rejection"
            add(
                kind,
                entry.at,
                _APPLICATION_LABELS.get(entry.to_status, entry.to_status),
                detail=entry.note,
                status=entry.to_status,
            )

    app = await session.get(Application, item_id)
    if app is not None:
        if app.cv_title:
            add(
                "document",
                app.cv_modified_at or app.created_at,
                f"Kullanılan CV: {app.cv_title}",
                detail=app.cv_modified_at.isoformat() if app.cv_modified_at else None,
            )
        add("followup", item.follow_up_at, "Takip tarihi belirlendi")

    interviews = (
        await session.execute(
            select(Interview)
            .where(Interview.opportunity_id == item_id)
            .order_by(Interview.scheduled_at)
        )
    ).scalars()
    for interview in interviews:
        add(
            "interview",
            interview.scheduled_at,
            f"Görüşme planlandı: {interview.stage}",
            detail=interview.notes or interview.outcome,
        )

    todo_rows = (
        await session.execute(
            select(Todo, Entity.title)
            .join(Entity, Entity.id == Todo.id)
            .join(Link, Link.to_id == Todo.id)
            .where(Link.from_id == item_id, Link.relation == "application_step")
        )
    ).all()
    for todo, title in todo_rows:
        add("todo", todo.created_at or todo.due_at, f"Görev: {title}", detail=todo.status)

    note_rows = (
        await session.execute(
            select(Entity.id, Entity.title, Entity.created_at)
            .join(Link, Link.from_id == Entity.id)
            .where(Link.to_id == item_id, Link.relation == "notes_about")
        )
    ).all()
    for _note_id, note_title, created_at in note_rows:
        add("note", created_at, f"Not: {note_title}")

    entries.sort(key=lambda entry: entry.at)
    return ApplicationTimelineOut(opportunity_id=item_id, entries=entries)


async def list_interviews(session: AsyncSession, item_id: uuid.UUID) -> list[InterviewOut]:
    rows = await session.execute(
        select(Interview)
        .where(Interview.opportunity_id == item_id)
        .order_by(Interview.scheduled_at.asc().nulls_last(), Interview.position)
    )
    return [
        InterviewOut(
            id=r.id,
            opportunity_id=r.opportunity_id,
            stage=r.stage,
            mode=r.mode,
            scheduled_at=r.scheduled_at,
            duration_min=r.duration_min,
            notes=r.notes,
            outcome=r.outcome,
            salary_stated=r.salary_stated,
            position=r.position,
        )
        for r in rows.scalars()
    ]


async def add_interview(
    session: AsyncSession,
    item_id: uuid.UUID,
    data: InterviewIn,
) -> InterviewOut | None:
    if await session.get(Opportunity, item_id) is None:
        return None
    position = 1 + len(
        list(
            (
                await session.execute(
                    select(Interview.id).where(Interview.opportunity_id == item_id)
                )
            ).scalars()
        )
    )
    row = Interview(opportunity_id=item_id, position=position, **data.model_dump())
    session.add(row)
    await log_event(
        session,
        verb="opportunity.interview_added",
        entity_id=item_id,
        entity_type="opportunity",
        payload={
            "stage": data.stage,
            "salary_stated": bool(data.salary_stated),
        },
    )
    await session.commit()
    return InterviewOut(
        id=row.id,
        opportunity_id=item_id,
        stage=row.stage,
        mode=row.mode,
        scheduled_at=row.scheduled_at,
        duration_min=row.duration_min,
        notes=row.notes,
        outcome=row.outcome,
        salary_stated=row.salary_stated,
        position=row.position,
    )


async def patch_interview(
    session: AsyncSession,
    interview_id: uuid.UUID,
    data: InterviewIn,
) -> InterviewOut | None:
    row = await session.get(Interview, interview_id)
    if row is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    await log_event(
        session,
        verb="opportunity.interview_updated",
        entity_id=row.opportunity_id,
        entity_type="opportunity",
        payload={"interview_id": str(row.id), "salary_stated": bool(row.salary_stated)},
    )
    await session.commit()
    return InterviewOut(
        id=row.id,
        opportunity_id=row.opportunity_id,
        stage=row.stage,
        mode=row.mode,
        scheduled_at=row.scheduled_at,
        duration_min=row.duration_min,
        notes=row.notes,
        outcome=row.outcome,
        salary_stated=row.salary_stated,
        position=row.position,
    )


async def delete_interview(session: AsyncSession, interview_id: uuid.UUID) -> bool:
    row = await session.get(Interview, interview_id)
    if row is None:
        return False
    await log_event(
        session,
        verb="opportunity.interview_deleted",
        entity_id=row.opportunity_id,
        entity_type="opportunity",
        payload={"interview_id": str(row.id)},
    )
    await session.delete(row)
    await session.commit()
    return True


def _pct(numerator: int, denominator: int) -> float | None:
    """Sifir paydada yaniltici %0 yerine None doner (UI '—' gosterir)."""
    return round(numerator / denominator * 100, 1) if denominator else None


#: Ilk yanit sayilan durumlar.
_RESPONSE_STATUSES = {"interview", "offer", "accepted", "rejected"}
_INTERVIEW_STATUSES = {"interview", "offer", "accepted"}

#: Basvuru hattinda "bu asamaya ulasti" sayilan durumlar. Huni STOK DEGIL
#: KOHORT okur: reddedilmis bir basvuru da gorusmeye ulasmis olabilir.
_REACHED_STAGES: tuple[tuple[str, frozenset[str]], ...] = (
    (
        "applied",
        frozenset({"applied", "interview", "offer", "accepted", "rejected", "closed", "withdrawn"}),
    ),
    ("interview", frozenset({"interview", "offer", "accepted"})),
    ("offer", frozenset({"offer", "accepted"})),
    ("accepted", frozenset({"accepted"})),
    ("rejected", frozenset({"rejected"})),
)


def _reached_stages(statuses: set[str], current: str) -> set[str]:
    """Bir basvurunun gecmiste ULAS'tigi asamalar.

    Guncel durum tek basina yetmez: `rejected` bir kayit daha once `interview`
    gormus olabilir; huni oranlari bu yuzden gecmis + guncel durumun
    birlesiminden turetilir (olay kaydi olmadan olusan eski kayitlar icin de
    guncel durum yedek olarak kullanilir).
    """
    seen = set(statuses)
    seen.add(current)
    reached: set[str] = set()
    for stage, members in _REACHED_STAGES:
        if seen & members:
            reached.add(stage)
    return reached


def _breakdown(rows: list[dict[str, Any]], key: str, label_key: str | None = None) -> list[
    FunnelBreakdownRow
]:
    buckets: dict[str, dict[str, Any]] = {}
    for row in rows:
        raw = row.get(key) or ""
        bucket_key = raw.strip() or "bilinmiyor"
        bucket = buckets.setdefault(
            bucket_key,
            {
                "label": (row.get(label_key) if label_key else None) or bucket_key,
                "total": 0,
                "responded": 0,
                "interviewed": 0,
                "offers": 0,
            },
        )
        bucket["total"] += 1
        reached = row.get("reached") or set()
        if row.get("responded"):
            bucket["responded"] += 1
        if "interview" in reached:
            bucket["interviewed"] += 1
        if "offer" in reached:
            bucket["offers"] += 1
    out = [
        FunnelBreakdownRow(
            key=key_value,
            label=str(data["label"]),
            total=data["total"],
            responded=data["responded"],
            interviewed=data["interviewed"],
            offers=data["offers"],
            response_rate=_pct(data["responded"], data["total"]),
            interview_rate=_pct(data["interviewed"], data["total"]),
        )
        for key_value, data in buckets.items()
    ]
    out.sort(key=lambda row: (-row.total, row.key))
    return out


#: (etiket, baslangic, bitis) uclusu; bitis HARIC.
Bucket = tuple[str, datetime, datetime]


def _weekly_buckets(count: int) -> list[Bucket]:
    """Gercek takvim haftalari (ISO): 7 gunluk kayar blok degil."""
    zone = local_zone()
    now = datetime.now(zone)
    monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    starts = [monday - timedelta(weeks=index) for index in range(count)]
    return [
        (start.strftime("%G-W%V"), start, start + timedelta(weeks=1)) for start in reversed(starts)
    ]


def _monthly_buckets(count: int) -> list[Bucket]:
    """Gercek takvim aylari: `30 gunluk blok` ay etiketiyle gizlenmez."""
    zone = local_zone()
    now = datetime.now(zone)
    cursor = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    starts: list[datetime] = []
    for _ in range(count):
        starts.append(cursor)
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    buckets: list[Bucket] = []
    for start in reversed(starts):
        # Bir sonraki ayin ilk gunu: 32 gun ekleyip gun 1'e sabitlemek her ay icin dogrudur.
        end = (start + timedelta(days=32)).replace(day=1)
        buckets.append((start.strftime("%Y-%m"), start, end))
    return buckets


def _calendar_volume(rows: list[dict[str, Any]], *, buckets: list[Bucket]) -> list[FunnelVolumeRow]:
    """Basvuru hacmini takvim kovalarina yerlestirir (yerel saat dilimi)."""
    zone = local_zone()
    counts = {key: 0 for key, _start, _end in buckets}
    for row in rows:
        applied_at = row["applied_at"]
        if applied_at is None:
            continue
        moment = applied_at.astimezone(zone)
        for key, start, end in buckets:
            if start <= moment < end:
                counts[key] += 1
                break
    return [FunnelVolumeRow(period=key, applied=value) for key, value in counts.items()]


async def funnel(session: AsyncSession) -> FunnelOut:
    """CRM hunisi: yalnizca gercek basvuru kayitlari uzerinden.

    Kesfedilmis ilanlar (``opportunity.status``) buraya hicbir sekilde girmez;
    payda ``application`` tablosudur.
    """
    rows = (
        await session.execute(
            select(Application, Opportunity, Entity.title)
            .join(Opportunity, Opportunity.id == Application.opportunity_id)
            .join(Entity, Entity.id == Application.opportunity_id)
            .where(Opportunity.trashed_at.is_(None))
        )
    ).all()

    counts: dict[str, int] = {}
    for app, _opp, _title in rows:
        counts[app.status] = counts.get(app.status, 0) + 1
    total = sum(counts.values())
    tracked = sum(counts.get(status, 0) for status in lifecycle.APPLICATION_FLOW)
    by_status = [FunnelRow(status=status, count=counts.get(status, 0)) for status in lifecycle.APPLICATION_FLOW]

    # Gecmis YALNIZCA bu basvurular icin okunur: tum tablo bellege alinmaz.
    application_ids = [app.opportunity_id for app, _opp, _title in rows]
    history: dict[uuid.UUID, list[ApplicationHistory]] = {}
    if application_ids:
        history_rows = (
            await session.execute(
                select(ApplicationHistory).where(
                    ApplicationHistory.scope == "application",
                    ApplicationHistory.opportunity_id.in_(application_ids),
                )
            )
        ).scalars()
        for entry in history_rows:
            history.setdefault(entry.opportunity_id, []).append(entry)

    enriched: list[dict[str, Any]] = []
    first_response_deltas: list[float] = []
    interview_deltas: list[float] = []
    cohort: dict[str, int] = {stage: 0 for stage, _members in _REACHED_STAGES}
    for app, opp, title in rows:
        entries = sorted(history.get(app.opportunity_id, []), key=lambda e: e.at)
        applied_at = next(
            (e.at for e in entries if e.to_status == "applied"), opp.applied_at
        )
        response_at = next(
            (
                e.at
                for e in entries
                if e.to_status in _RESPONSE_STATUSES and applied_at is not None and e.at > applied_at
            ),
            None,
        )
        interview_at = next(
            (
                e.at
                for e in entries
                if e.to_status in _INTERVIEW_STATUSES and applied_at is not None and e.at > applied_at
            ),
            None,
        )
        responded = response_at is not None or app.status in _RESPONSE_STATUSES
        if applied_at is not None and response_at is not None:
            first_response_deltas.append((response_at - applied_at).total_seconds() / 86400)
        if applied_at is not None and interview_at is not None:
            interview_deltas.append((interview_at - applied_at).total_seconds() / 86400)
        reached = _reached_stages({e.to_status for e in entries}, app.status)
        for stage in reached:
            cohort[stage] += 1
        enriched.append(
            {
                "status": app.status,
                "responded": responded,
                "reached": reached,
                "source": opp.source,
                "cv": app.cv_title or "CV kaydedilmemis",
                "role": opp.category or "kategorisiz",
                "country": opp.country or "bilinmiyor",
                "work_mode": (opp.remote or "").strip().lower() or "bilinmiyor",
                "organization": opp.organization,
                "title": title,
                "applied_at": applied_at,
            }
        )

    def ratio(lower: str, upper: str) -> float | None:
        """Kohort orani: `lower` asamasina ulasanlarin kaci `upper`a ulasti?

        Stok sayimi degil: `interview` asamasina ulasip sonra `rejected` olan
        kayit da paydaya ve paya girer.
        """
        base = cohort.get(lower, 0)
        return round(cohort.get(upper, 0) / base * 100, 1) if base else None

    conversions = {
        "applied_to_interview": ratio("applied", "interview"),
        "interview_to_offer": ratio("interview", "offer"),
        "offer_to_accepted": ratio("offer", "accepted"),
        "applied_to_rejected": ratio("applied", "rejected"),
        "applied_total": cohort.get("applied", 0),
        "response_rate": _pct(
            sum(1 for row in enriched if row["responded"]), cohort.get("applied", 0)
        ),
        "interview_rate": ratio("applied", "interview"),
    }

    reason_rows = (
        await session.execute(
            select(Opportunity.rejection_reason, func.count())
            .select_from(Application)
            .join(Opportunity, Opportunity.id == Application.opportunity_id)
            .where(Application.status == "rejected", Opportunity.rejection_reason.is_not(None))
            .group_by(Opportunity.rejection_reason)
            .order_by(func.count().desc())
        )
    ).all()

    def avg(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 1) if values else None

    weekly_volume = _calendar_volume(enriched, buckets=_weekly_buckets(12))
    monthly_volume = _calendar_volume(enriched, buckets=_monthly_buckets(12))

    cohort_size = cohort.get("applied", 0)
    return FunnelOut(
        total=total,
        tracked=tracked,
        by_status=by_status,
        conversions=conversions,
        cohort=cohort,
        cohort_size=cohort_size,
        min_cohort_size=lifecycle.MIN_FUNNEL_COHORT,
        sufficient=cohort_size >= lifecycle.MIN_FUNNEL_COHORT,
        rejection_reasons=[
            {"reason": reason or "belirsiz", "count": count} for reason, count in reason_rows
        ],
        avg_first_response_days=avg(first_response_deltas),
        avg_applied_to_interview_days=avg(interview_deltas),
        by_source=_breakdown(enriched, "source"),
        by_cv=_breakdown(enriched, "cv"),
        by_role=_breakdown(enriched, "role"),
        by_country=_breakdown(enriched, "country"),
        by_work_mode=_breakdown(enriched, "work_mode"),
        weekly_volume=weekly_volume,
        monthly_volume=monthly_volume,
    )


async def list_followups(
    session: AsyncSession,
    *,
    days: int = 30,
) -> list[FollowupOut]:
    """Yaklasan takipler -- yalnizca gercek basvuru kayitlari uzerinden."""
    cutoff = datetime.now(UTC) + timedelta(days=days)
    rows = (
        await session.execute(
            select(Application, Opportunity, Entity.title)
            .join(Opportunity, Opportunity.id == Application.opportunity_id)
            .join(Entity, Entity.id == Application.opportunity_id)
            .where(
                Opportunity.follow_up_at.is_not(None),
                Opportunity.follow_up_at <= cutoff,
                Application.status.not_in(list(lifecycle.APPLICATION_TERMINAL)),
                Opportunity.trashed_at.is_(None),
            )
            .order_by(Opportunity.follow_up_at)
        )
    ).all()
    return [
        FollowupOut(
            id=app.opportunity_id,
            title=title,
            status=app.status,
            follow_up_at=opp.follow_up_at,
            note=opp.notes,
        )
        for app, opp, title in rows
    ]


async def deadline_provider(session: AsyncSession) -> list[DeadlineRow]:
    """Firsat son tarihleri + mulakat saatleri (kural 16; deadline_v yerine)."""
    from app.core.deadlines import rows_with_titles
    from app.modules.opportunity.models import Interview, Opportunity

    # Kesif dongusunde hala ilgilenilen ilanlar + duyurular; gecmis son
    # tarihler hatirlatma uretmez (kural: terminal/arsiv/gecten deadline yok).
    now = datetime.now(UTC)
    # ScalarResult tek gezinmelidir; aksi halde id/due haritalari bos kalir
    # ve satirlar /api/deadlines'tan sessizce duser (bkz. todo/service.py).
    opps = list(
        (
            await session.execute(
                select(Opportunity).where(
                    Opportunity.deadline_at.is_not(None),
                    Opportunity.deadline_at >= now,
                    Opportunity.status.in_(sorted(lifecycle.ACTIVE_DISCOVERY_STATUSES)),
                    Opportunity.trashed_at.is_(None),
                )
            )
        ).scalars()
    )
    ids = [o.id for o in opps]
    due = {o.id: o.deadline_at for o in opps}
    sub = {o.id: o.kind for o in opps}
    prio = {o.id: o.priority for o in opps}
    rows = await rows_with_titles(
        session,
        type_="opportunity",
        module="opportunity",
        ids=ids,
        due_at=due,
        sub_kind=sub,
        priority=prio,
    )

    # Mulakatlar kendi entity'sine sahip DEGIL: deadline satiri ust firsatin
    # entity'sine baglanir, basligi gorusme baglamini tasir, sub_kind=interview.
    # rows_with_titles entity id'sine gore tekillestirdigi icin burada elle
    # kurulur -- ayni ilanin birden fazla gorusmesi olabilir.
    interviews = (
        await session.execute(
            select(Interview, Entity.title)
            .join(Opportunity, Opportunity.id == Interview.opportunity_id)
            .join(Entity, Entity.id == Interview.opportunity_id)
            .outerjoin(Application, Application.opportunity_id == Interview.opportunity_id)
            .where(
                Interview.scheduled_at.is_not(None),
                Interview.scheduled_at >= datetime.now(UTC),
                Opportunity.trashed_at.is_(None),
                Entity.archived_at.is_(None),
                # Kapanmis basvurunun gecmis gorusmesi takvimde gorunmez.
                or_(Application.opportunity_id.is_(None),
                    Application.status.not_in(list(lifecycle.APPLICATION_TERMINAL))),
            )
            .order_by(Interview.scheduled_at)
        )
    ).all()
    for interview, title in interviews:
        rows.append(
            DeadlineRow(
                entity_id=interview.opportunity_id,
                type="opportunity",
                title=f"{title} — Görüşme ({interview.stage})",
                due_at=interview.scheduled_at,
                module="opportunity",
                sub_kind="interview",
                priority=1,
                # Gorusmenin KENDI kimligi: ayni ilanin iki gorusmesi ayri
                # kosullardir ve baslik/sira ile ayirt EDILEMEZ.
                condition_id=str(interview.id),
            )
        )
    return rows
