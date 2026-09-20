"""H1 fırsat/başvuru yaşam döngüsü adaptörleri.

İki hat KESİN olarak ayrıdır (§36): fırsatın keşif/duyuru durumu ile başvuru
CRM hattı aynı araçla karıştırılmaz. Her ikisi de canonical lifecycle
doğrulamasından geçer; burada geçiş matrisi kopyalanmaz.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.db import SessionLocal
from app.integrations.agent.actions import (
    ActionError,
    transition_application,
    transition_opportunity,
)
from app.integrations.agent.write_models import (
    ApplicationTransitionIn,
    OpportunityTransitionIn,
)
from app.modules.opportunity.models import Application, Opportunity
from tests.agent_test_utils import (
    forbid_outbound_network,  # noqa: F401  (autouse ağ koruması)
    table_counts,
)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def _make_opportunity(
    session: AsyncSession,
    *,
    kind: str = "job",
    status: str = "discovered",
    title: str = "Acme Backend Engineer",
    organization: str | None = "Acme",
) -> uuid.UUID:
    opportunity_id = uuid.uuid4()
    session.add(Entity(id=opportunity_id, type="opportunity", title=title, search_text=""))
    # `title` Entity'de yaşar (Opportunity modelinde kolon yoktur).
    session.add(
        Opportunity(
            id=opportunity_id,
            kind=kind,
            status=status,
            organization=organization,
            found_at=datetime.now(UTC),
        )
    )
    await session.commit()
    return opportunity_id


# ---------------------------------------------------------------------------
# forkos_opportunity_transition (keşif / duyuru)
# ---------------------------------------------------------------------------


async def test_discovery_transition_uses_canonical_lifecycle(db_session: AsyncSession) -> None:
    opportunity_id = await _make_opportunity(db_session)
    before_counts = await table_counts(db_session)

    receipt = await transition_opportunity(
        db_session,
        OpportunityTransitionIn(
            opportunity_id=str(opportunity_id),
            expected_status="discovered",
            to_status="shortlisted",
        ),
        request_id="o1",
    )

    assert receipt.status == "executed"
    assert receipt.before == {"status": "discovered", "kind": "job"}
    assert receipt.after == {"status": "shortlisted"}
    assert receipt.changed_fields == ["status"]

    item = await db_session.get(Opportunity, opportunity_id)
    assert item is not None and item.status == "shortlisted"

    after_counts = await table_counts(db_session)
    assert after_counts["application"] == before_counts["application"]
    assert after_counts["bookmark"] == before_counts["bookmark"]
    assert after_counts["todo"] == before_counts["todo"]


async def test_announcement_transition_uses_announcement_flow(db_session: AsyncSession) -> None:
    opportunity_id = await _make_opportunity(
        db_session, kind="scholarship", status="new", title="Burs Duyurusu"
    )

    receipt = await transition_opportunity(
        db_session,
        OpportunityTransitionIn(
            opportunity_id=str(opportunity_id),
            expected_status="new",
            to_status="watching",
        ),
    )
    assert receipt.status == "executed"
    assert receipt.after == {"status": "watching"}


async def test_opportunity_stale_status_blocks_write(db_session: AsyncSession) -> None:
    opportunity_id = await _make_opportunity(db_session, status="discovered")

    with pytest.raises(ActionError, match="STALE_ACTION"):
        await transition_opportunity(
            db_session,
            OpportunityTransitionIn(
                opportunity_id=str(opportunity_id),
                expected_status="shortlisted",
                to_status="dismissed",
            ),
        )

    item = await db_session.get(Opportunity, opportunity_id)
    assert item is not None and item.status == "discovered"


async def test_opportunity_invalid_transition_is_rejected(db_session: AsyncSession) -> None:
    opportunity_id = await _make_opportunity(db_session, kind="job", status="discovered")

    with pytest.raises(ActionError, match="INVALID_TRANSITION"):
        await transition_opportunity(
            db_session,
            OpportunityTransitionIn(
                opportunity_id=str(opportunity_id),
                expected_status="discovered",
                to_status="interview",  # başvuru hattı değeri: keşif akışında geçersiz
            ),
        )

    item = await db_session.get(Opportunity, opportunity_id)
    assert item is not None and item.status == "discovered"


async def test_opportunity_unknown_target_fails(db_session: AsyncSession) -> None:
    with pytest.raises(ActionError, match="TARGET_NOT_FOUND"):
        await transition_opportunity(
            db_session,
            OpportunityTransitionIn(
                opportunity_id=str(uuid.uuid4()),
                expected_status="discovered",
                to_status="shortlisted",
            ),
        )


# ---------------------------------------------------------------------------
# forkos_application_transition (CRM hattı)
# ---------------------------------------------------------------------------


async def test_first_apply_creates_application_via_canonical_service(
    db_session: AsyncSession,
) -> None:
    opportunity_id = await _make_opportunity(db_session, status="shortlisted")

    receipt = await transition_application(
        db_session,
        ApplicationTransitionIn(
            opportunity_id=str(opportunity_id), expected_status=None, to_status="applied"
        ),
        request_id="a1",
    )

    assert receipt.status == "executed"
    assert receipt.target_type == "application"
    assert receipt.after["status"] == "applied"

    app = await db_session.get(Application, opportunity_id)
    assert app is not None and app.status == "applied"


async def test_application_transition_without_row_is_rejected(db_session: AsyncSession) -> None:
    """§37: kayıt yoksa `applied` dışındaki hedefler reddedilir."""
    opportunity_id = await _make_opportunity(db_session, status="shortlisted")

    with pytest.raises(ActionError, match="APPLICATION_NOT_FOUND"):
        await transition_application(
            db_session,
            ApplicationTransitionIn(
                opportunity_id=str(opportunity_id), to_status="interview"
            ),
        )

    assert await db_session.get(Application, opportunity_id) is None


async def test_application_transition_chain_and_stale_guard(db_session: AsyncSession) -> None:
    opportunity_id = await _make_opportunity(db_session, status="shortlisted")
    await transition_application(
        db_session,
        ApplicationTransitionIn(opportunity_id=str(opportunity_id), to_status="applied"),
    )

    moved = await transition_application(
        db_session,
        ApplicationTransitionIn(
            opportunity_id=str(opportunity_id),
            expected_status="applied",
            to_status="interview",
        ),
    )
    assert moved.status == "executed"
    assert moved.before == {"status": "applied"}
    assert moved.after == {"status": "interview"}

    with pytest.raises(ActionError, match="STALE_ACTION"):
        await transition_application(
            db_session,
            ApplicationTransitionIn(
                opportunity_id=str(opportunity_id),
                expected_status="applied",  # artık interview
                to_status="offer",
            ),
        )

    app = await db_session.get(Application, opportunity_id)
    assert app is not None and app.status == "interview"


async def test_terminal_application_states_are_allowed(db_session: AsyncSession) -> None:
    """§39: kabul/ret gibi terminal durumlar operasyonel state'tir, silme değildir."""
    opportunity_id = await _make_opportunity(db_session, status="shortlisted")
    await transition_application(
        db_session,
        ApplicationTransitionIn(opportunity_id=str(opportunity_id), to_status="applied"),
    )
    await transition_application(
        db_session,
        ApplicationTransitionIn(
            opportunity_id=str(opportunity_id),
            expected_status="applied",
            to_status="rejected",
            rejection_reason="Pozisyon kapatıldı",
        ),
    )

    app = await db_session.get(Application, opportunity_id)
    assert app is not None and app.status == "rejected"
    item = await db_session.get(Opportunity, opportunity_id)
    assert item is not None and item.rejection_reason == "Pozisyon kapatıldı"


async def test_same_status_transition_is_noop(db_session: AsyncSession) -> None:
    opportunity_id = await _make_opportunity(db_session, status="shortlisted")
    await transition_application(
        db_session,
        ApplicationTransitionIn(opportunity_id=str(opportunity_id), to_status="applied"),
    )

    receipt = await transition_application(
        db_session,
        ApplicationTransitionIn(
            opportunity_id=str(opportunity_id),
            expected_status="applied",
            to_status="applied",
        ),
    )
    assert receipt.status == "noop"
    assert receipt.summary == "Application already applied"


async def test_application_history_is_append_only(db_session: AsyncSession) -> None:
    """Geçiş geçmişi yalnızca EKLENİR; H1 hiçbir kaydı silmez."""
    from app.modules.opportunity.models import ApplicationHistory

    opportunity_id = await _make_opportunity(db_session, status="shortlisted")
    await transition_application(
        db_session,
        ApplicationTransitionIn(opportunity_id=str(opportunity_id), to_status="applied"),
    )
    await transition_application(
        db_session,
        ApplicationTransitionIn(
            opportunity_id=str(opportunity_id), expected_status="applied", to_status="interview"
        ),
    )

    rows = (
        await db_session.execute(
            select(ApplicationHistory).where(ApplicationHistory.opportunity_id == opportunity_id)
        )
    ).scalars().all()
    assert len(rows) >= 2
