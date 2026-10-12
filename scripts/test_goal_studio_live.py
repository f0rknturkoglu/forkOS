"""Explicit local-only smoke, isolated PostgreSQL *_test only; never personal/cloud data.

Run inside the isolated backend image with server-owned Goal Studio environment configured.
This is a manual release gate, not a pytest fixture or a startup task.
"""
import asyncio
from uuid import uuid4
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.modules.goal import service, studio, studio_transport
from app.modules.goal.models import KeyResult
from app.modules.goal.studio_schemas import StudioDecisionIn, StudioSessionIn, StudioTurnIn


async def main():
    if not settings.database_url.rsplit('/', 1)[-1].endswith('_test'):
        raise RuntimeError('Live smoke requires an isolated *_test database')
    async with SessionLocal() as db:
        state = await studio_transport.status(db)
        assert state.state == 'ready' and state.local is True and state.tools_verified
        item = await studio.start(db, StudioSessionIn(client_uuid=uuid4()))
        body = StudioTurnIn(client_uuid=uuid4(), message=(
            'Bu sentetik test için hedef ve ölçülebilir sonuç taslağı hazırla. '
            'Hedef: Closure smoke matematik pratiği. Sonuç: 10 problem çözmek. '
            'Mevcut ölçüm bilinmiyor, null kalsın. Plan veya alan oluşturma. '
            'operations sırasıyla goal.create (key goal) ve key_result.save (key kr, goal_ref goal) olmalı. '
            'Eksik başka bilgi yok. Sadece discussion/proposal JSON nesnesi döndür; Markdown ve düşünme metni yazma.'
            ' goal.create data yalnız title içersin. key_result.save data yalnız title ve target_value içersin; '
            'diğer alanları gönderme, source_config gönderilecekse {} olmalı, null değil.'
        ))
        result = await studio.turn(db, await studio.get_session(db, item.id), body)
        assert result.state == 'running', result.error
        original = result.id
        replay = await studio.turn(db, await studio.get_session(db, item.id), body)
        assert replay.id == original
        for _ in range(120):
            await asyncio.sleep(2)
            result = await studio.reconcile(db, await studio.get_session(db, item.id))
            if result.state != 'running':
                break
        assert result.runtime and result.runtime.provider == 'custom', (result.state, result.error)
        assert result.runtime.model == state.configured_model
        assert result.state == 'approval_pending' and result.revision, (result.state, result.error)
        decision = StudioDecisionIn(revision_id=result.revision.id, fingerprint=result.revision.fingerprint, decision='approve')
        applied = await studio.decide(db, await studio.get_session(db, item.id), decision)
        assert applied.state == 'applied'
        retry = await studio.decide(db, await studio.get_session(db, item.id), decision)
        assert retry.revision.results == applied.revision.results
        goal_id = next(value.id for value in applied.revision.results.values() if value.type == 'goal')
        goal = await service.get_goal(db, goal_id)
        results = (await db.scalars(select(KeyResult).where(KeyResult.goal_id == goal.id))).all()
        assert len(results) == 1 and results[0].manual_value is None
        print('LIVE PASS: tools=0, host bridge, custom/' + result.runtime.model + ', same UUID replay, real draft/revision, explicit approval, canonical Goal/KR, idempotent approval')


if __name__ == '__main__':
    asyncio.run(main())
