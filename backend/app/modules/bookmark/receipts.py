"""Durable capture receipts; canonical domain writes share the receipt transaction."""

from __future__ import annotations

import hashlib
import json
import uuid

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.entity import create_entity
from app.core.events import log_event
from app.core.models import EntityBacked
from app.db import Base


class CaptureReceipt(EntityBacked, Base):
    __tablename__ = "capture_receipt"
    ENTITY_TYPE = "capture_receipt"
    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    client_uuid: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), unique=True)
    fingerprint: Mapped[str]
    destination: Mapped[str]
    result: Mapped[dict] = mapped_column(JSONB)


def fingerprint(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


async def capture_once(session, data, destination, write):
    """Serialize concurrent clients and persist the original reply, including a lost HTTP reply."""
    identity = data.client_uuid
    digest = fingerprint({"destination": destination, "data": data.model_dump(mode="json")})
    lock = int.from_bytes(hashlib.sha256(identity.bytes).digest()[:8], "big", signed=True)
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock})
    receipt = await session.scalar(
        select(CaptureReceipt).where(CaptureReceipt.client_uuid == identity)
    )
    if receipt:
        if receipt.fingerprint != digest:
            raise HTTPException(409, "Aynı capture kimliği farklı içerikle kullanılamaz")
        session.info["capture_replayed"] = True
        return receipt.result, True
    result = await write()
    entity = await create_entity(session, type="capture_receipt", title="Capture teslim makbuzu")
    session.add(
        CaptureReceipt(
            id=entity.id,
            client_uuid=identity,
            fingerprint=digest,
            destination=destination,
            result=result,
        )
    )
    await log_event(
        session,
        verb="capture.delivered",
        entity_id=entity.id,
        entity_type="capture_receipt",
        payload={"destination": destination},
    )
    await session.commit()
    return result, False
