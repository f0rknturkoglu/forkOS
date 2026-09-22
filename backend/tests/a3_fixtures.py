"""A3 testleri için ortak kurulum yardımcıları.

`test_*.py` DEĞİLDİR (pytest toplamaz).

Buradaki kurulum H4'ü TAKLİT ETMEZ: gerçek `run_local_cognition` hattı çalışır
(doğrulama ve `source_excerpt` grounding dahil), yalnız yerel model sağlayıcısı
betiklenir. Böylece "geçersiz alıntı reddedilir" gibi iddialar uçtan uca
kanıtlanır.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.local_cognition import service as lc_svc
from app.modules.agent_episode import service as a3
from app.modules.agent_episode.schemas import (
    EpisodeFinalizeIn,
    EpisodeTurnIn,
)
from app.modules.agent_lifecycle import service as a1
from app.modules.agent_lifecycle.schemas import LifecycleEventIn
from tests.h4_test_provider import ScriptedProvider  # noqa: F401  (yeniden dışa aktarım)

#: Ham transkript kalıcılaşmadığını kanıtlamak için kullanılan işaret.
A3_RAW_SECRET = "A3_RAW_SECRET_XYZ_987654"

#: Sabitlenmiş zaman: devir seçimi ve saklama testleri deterministik olsun.
NOW = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)


#: `h4_ready` fixture'ı `tests/conftest.py` içinde tanımlıdır; modül
#: ad alanına import etmek gerekmez (F811'i önler).


def patch_provider(monkeypatch: pytest.MonkeyPatch, provider: Any) -> None:
    """H4'ün sağlayıcı kurulumunu betikli sağlayıcıyla değiştirir.

    Gerçek orkestrasyon, doğrulama ve grounding korunur.
    """
    monkeypatch.setattr(lc_svc, "OllamaProvider", lambda *args, **kwargs: provider)


class Source:
    """A2'nin teslim ettiği kaynağın asgari taklidi (`BootstrapSourceRef`)."""

    def __init__(
        self,
        source_id: str,
        source_type: str = "project",
        *,
        source_version: str | None = "v1",
        scope_project: str | None = None,
        title: str | None = None,
    ) -> None:
        self.source_id = source_id
        self.source_type = source_type
        self.source_version = source_version
        self.scope_project = scope_project
        self.title = title


def item_json(kind: str, text: str, excerpt: str) -> str:
    """`episodic_turn_v1` çıktısı: tek geçerli madde."""
    return json.dumps(
        {"items": [{"kind": kind, "text": text, "source_excerpt": excerpt}]}, ensure_ascii=False
    )


def items_json(entries: list[tuple[str, str, str]]) -> str:
    """`episodic_turn_v1` çıktısı: `(kind, text, excerpt)` üçlülerinden."""
    return json.dumps(
        {
            "items": [
                {"kind": kind, "text": text, "source_excerpt": excerpt}
                for kind, text, excerpt in entries
            ]
        },
        ensure_ascii=False,
    )


async def start_session(
    session: AsyncSession, raw_session_id: str, *, turn_id: str = "t1"
) -> Any:
    """A1 oturumu başlatır ve satırı döner."""
    await a1.observe(
        session,
        LifecycleEventIn(
            schema_version=1,
            event="session_start",
            harness="hermes",
            session_id=raw_session_id,
            turn_id=turn_id,
            platform="cli",
        ),
    )
    return await a3._session_row(session, "hermes", raw_session_id)


async def deliver(
    session: AsyncSession,
    session_row: Any,
    *,
    raw_turn_id: str,
    sources: list[Source],
    is_first_turn: bool = True,
) -> None:
    """`/turn` ucunun A3 tarafını çalıştırır (defter yazımı + devir seçimi)."""
    await a3.observe_turn_delivery(
        session,
        session_row=session_row,
        raw_turn_id=raw_turn_id,
        turn_db_id=None,
        sources=sources,
        is_first_turn=is_first_turn,
    )


async def ingest(
    session: AsyncSession,
    raw_session_id: str,
    *,
    turn_id: str,
    user: str | None = "kullanıcı mesajı",
    assistant: str | None = "asistan yanıtı",
) -> Any:
    """`/episode/turn` ucunu çağırır."""
    return await a3.ingest_turn(
        session,
        EpisodeTurnIn(
            schema_version=1,
            harness="hermes",
            session_id=raw_session_id,
            turn_id=turn_id,
            platform="cli",
            user_message=user,
            assistant_response=assistant,
        ),
    )


async def seal(session: AsyncSession, raw_session_id: str) -> Any:
    """`/episode/finalize` ucunu çağırır."""
    return await a3.finalize(
        session,
        EpisodeFinalizeIn(
            schema_version=1, harness="hermes", session_id=raw_session_id, platform="cli"
        ),
    )


def age_episode(session: AsyncSession, episode: Any, *, days: int) -> None:
    """Mühürlenmiş bir devri yaşlandırır (saklama testleri için)."""
    episode.sealed_at = episode.sealed_at - timedelta(days=days)
    episode.expires_at = episode.expires_at - timedelta(days=days)
