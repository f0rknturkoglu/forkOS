from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text

from app.core import runs as run_svc
from app.core.models import Event, Notification, SourceRun
from app.core.source_sync import reconcile_stale_runs
from app.db import engine
from app.modules.opportunity.models import Opportunity
from app.modules.opportunity.service import ingest_jobs
from app.sources.forkjob_core.models import WorkMode


@dataclass
class _MockJob:
    title: str
    url: str
    company: str
    location: str
    description: str
    external_id: str | None = None
    work_mode: WorkMode = WorkMode.REMOTE
    salary: str | None = None
    kind: str = "job"

    def to_row(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "company": self.company,
            "location": self.location,
            "description": self.description,
            "external_id": self.external_id,
            "forkjob": {
                "country": "ES",
                "region": "EU",
                "score": 60,
            },
        }


async def test_check_stalled_notifies_and_deduplicates_streak():
    source = f"test-stalled-{uuid.uuid4().hex[:8]}"
    label = f"Label-{source}"

    async with engine.begin() as conn:
        # 1. Henüz 2 boş koşu varken stalled tetiklenmemeli
        await conn.execute(
            text(
                "insert into source_run (source, status, started_at, finished_at) "
                "values (:s, 'empty', now() - interval '20 minutes', now()), "
                "       (:s, 'empty', now() - interval '10 minutes', now())"
            ),
            {"s": source},
        )

    from app.db import SessionLocal

    async with SessionLocal() as session:
        alerted = await run_svc.check_stalled(session, source, label=label)
        await session.commit()
        assert alerted is False

    # 2. 3. boş koşu geldiğinde tam olarak tetiklenmeli ve notification tablosuna yazmalı
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "insert into source_run (source, status, started_at, finished_at) "
                "values (:s, 'empty', now(), now())"
            ),
            {"s": source},
        )

    async with SessionLocal() as session:
        alerted = await run_svc.check_stalled(session, source, label=label)
        await session.commit()
        assert alerted is True

        # Notification tablosu kontrolü (Kural 6)
        notifications = list(
            (
                await session.execute(
                    select(Notification).where(Notification.kind == "source_stalled")
                )
            ).scalars().all()
        )
        assert any(label in n.title or label in n.body for n in notifications)

        # Event tablosu kontrolü
        events = list(
            (
                await session.execute(
                    select(Event).where(
                        Event.verb == "source.stalled",
                        Event.payload["source"].astext == source,
                    )
                )
            ).scalars().all()
        )
        assert len(events) == 1

    # 3. 4. boş koşu (aynı streak devam ediyor) tekrar bildirim ve event atmamalı
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "insert into source_run (source, status, started_at, finished_at) "
                "values (:s, 'empty', now(), now())"
            ),
            {"s": source},
        )

    async with SessionLocal() as session:
        alerted = await run_svc.check_stalled(session, source, label=label)
        await session.commit()
        assert alerted is False

        # Event sayısı hala 1 olmalı
        events = list(
            (
                await session.execute(
                    select(Event).where(
                        Event.verb == "source.stalled",
                        Event.payload["source"].astext == source,
                    )
                )
            ).scalars().all()
        )
        assert len(events) == 1


async def test_reconcile_stale_runs_dynamic_timeout():
    now = datetime.now(UTC)
    std_source = f"test:std:{uuid.uuid4().hex[:6]}"
    eures_source = "jobhunter:eures"

    async with engine.begin() as conn:
        # Standart kaynak: 25 dakika önce başladı (15dk eşiğini aştı -> abandoned olmalı)
        await conn.execute(
            text(
                "insert into source_run (source, status, started_at) "
                "values (:s, 'running', :t)"
            ),
            {"s": std_source, "t": now - timedelta(minutes=25)},
        )
        # EURES: 25 dakika önce başladı (15dk eşiğini aştı ama 60dk eşiğinde -> running kalmalı)
        await conn.execute(
            text(
                "insert into source_run (source, status, started_at) "
                "values (:s, 'running', :t)"
            ),
            {"s": eures_source, "t": now - timedelta(minutes=25)},
        )

    from app.db import SessionLocal

    async with SessionLocal() as session:
        # Standart 15dk eşiği ile uzlaşma
        cutoff = now - timedelta(minutes=15)
        reconciled = await reconcile_stale_runs(session, older_than=cutoff)
        await session.commit()
        assert reconciled >= 1

        # Standart kaynak terk edildi
        std_row = (
            await session.execute(
                select(SourceRun).where(SourceRun.source == std_source)
            )
        ).scalar_one()
        assert std_row.status == "abandoned"

        # EURES hala koşuyor olmalı!
        eures_row = (
            await session.execute(
                select(SourceRun)
                .where(SourceRun.source == eures_source)
                .order_by(SourceRun.id.desc())
            )
        ).scalars().first()
        assert eures_row.status == "running"


async def test_ingest_jobs_deduplicates_same_source_url():
    test_url = f"https://example.com/jobs/{uuid.uuid4().hex}"
    source = "test-board"

    job1 = _MockJob(
        title="Backend Dev",
        url=test_url,
        company="Acme Corp",
        location="Remote",
        description="Python async developer",
        external_id="ext-original-1",
    )

    from app.db import SessionLocal

    async with SessionLocal() as session:
        added = await ingest_jobs(session, [job1], source_label=source)
        await session.commit()
        assert added == 1

        opps = (
            await session.execute(
                select(Opportunity).where(Opportunity.url == test_url)
            )
        ).scalars().all()
        assert len(opps) == 1
        assert opps[0].organization == "Acme Corp"

    # İkinci geliş: Aynı URL, aynı kaynak, farklı veya None external_id
    job2 = _MockJob(
        title="Backend Dev (Senior)",
        url=test_url,
        company="Acme Corp",
        location="Madrid",
        description="Updated python async developer",
        external_id=None,
    )

    async with SessionLocal() as session:
        added = await ingest_jobs(session, [job2], source_label=source)
        await session.commit()
        # İkinci geliş yeni kayıt açmamalı (added == 0)
        assert added == 0

        # Veritabanında hala tek kayıt olmalı
        opps = (
            await session.execute(
                select(Opportunity).where(Opportunity.url == test_url)
            )
        ).scalars().all()
        assert len(opps) == 1
        assert opps[0].country == "ES"
