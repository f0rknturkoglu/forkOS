"""A3 gizlilik sözleşmesi (§5/§32): ham transkript hiçbir yerde kalıcılaşmaz.

Kanıtlanan iddialar:

1. A3 tablolarında ham transkript kolonu YOKTUR (şema kanıtı, DB'siz).
2. `user_message`/`assistant_response` DB'ye yazılmaz (A3 + A1/A2 destek tabloları).
3. Ham metin log kayıtlarına sızmaz; degrade logları yalnız istisna TÜRÜNÜ taşır.
4. Güvenli yanıt modelleri ham konuşma alanı dışa vurmaz (DB'siz).
5. `conversation_history` ve fazladan transkript alanları şemada REDDEDİLİR (DB'siz).
6. Kaynaktan uzun birebir kopya taşıyan madde reddedilir (`VERBATIM_LEAKAGE`).
7. Köken digest'i saklanır ve deterministik olarak yeniden üretilebilir.
"""

from __future__ import annotations

import json
import logging
import re

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.db import SessionLocal
from app.modules.agent_continuity import service as continuity_service
from app.modules.agent_continuity.models import AgentSessionContext, AgentSessionSource
from app.modules.agent_episode import service as a3
from app.modules.agent_episode.distill import compute_turn_digest
from app.modules.agent_episode.models import (
    AgentSessionEpisode,
    AgentSessionEpisodeItem,
    AgentSessionEpisodeTurn,
)
from app.modules.agent_episode.schemas import (
    EpisodeFinalizeIn,
    EpisodeStatusOut,
    EpisodeTurnIn,
    EpisodeTurnOut,
)
from app.modules.agent_lifecycle.models import AgentSession, AgentSessionTurn
from app.modules.agent_lifecycle.service import turn_key
from tests.a3_fixtures import (
    A3_RAW_SECRET,
    Source,
    deliver,
    ingest,
    item_json,
    patch_provider,
    seal,
    start_session,
)
from tests.h4_test_provider import ScriptedProvider

EPISODE_TABLES = (AgentSessionEpisode, AgentSessionEpisodeTurn, AgentSessionEpisodeItem)
SUPPORT_TABLES = (AgentSession, AgentSessionTurn, AgentSessionContext, AgentSessionSource)

#: Kolon/alan adlarında geçmesi ham transkript taşındığının kanıtı olan parçalar.
FORBIDDEN_NAME_FRAGMENTS = ("message", "response", "prompt", "transcript", "history", "content")

_SOURCE_ID = "entity:11111111-1111-1111-1111-111111111111"


async def _serialized_rows(session, tables) -> dict[str, list[str]]:
    """Tabloların TÜM kolonlarını okur ve JSON'a serileştirir (varlık kanıtı için)."""
    dumped: dict[str, list[str]] = {}
    for table in tables:
        rows = (await session.execute(select(*table.__table__.c))).all()
        dumped[table.__tablename__] = [
            json.dumps(dict(row._mapping), default=str, ensure_ascii=False) for row in rows
        ]
    return dumped


def _joined(dumped: dict[str, list[str]]) -> str:
    return "\n".join(row for rows in dumped.values() for row in rows)


# ---------------------------------------------------------------------------
# 1. Şema kanıtı (DB'siz)
# ---------------------------------------------------------------------------


@pytest.mark.no_database
def test_episode_tables_expose_no_raw_transcript_columns() -> None:
    for table in EPISODE_TABLES:
        columns = set(table.__table__.c.keys())
        leaked = sorted(
            column
            for column in columns
            if any(fragment in column for fragment in FORBIDDEN_NAME_FRAGMENTS)
        )
        assert leaked == [], f"{table.__tablename__} exposes transcript-like columns: {leaked}"


# ---------------------------------------------------------------------------
# 2. Ham transkript DB'ye yazılmaz
# ---------------------------------------------------------------------------


async def test_raw_user_and_assistant_messages_are_never_persisted(
    monkeypatch: pytest.MonkeyPatch, h4_ready: None
) -> None:
    patch_provider(
        monkeypatch,
        ScriptedProvider(responses=[item_json("topic", "Turda bir konu ele alındı.", "kullanıcı")]),
    )
    async with SessionLocal() as session:
        row = await start_session(session, "privacy-1")
        await deliver(
            session,
            row,
            raw_turn_id="t1",
            sources=[Source(_SOURCE_ID, "project", title="Alfa Projesi")],
        )
        out = await ingest(
            session,
            "privacy-1",
            turn_id="t1",
            user=f"kullanıcı {A3_RAW_SECRET} mesajı",
            assistant=f"asistan {A3_RAW_SECRET} yanıtı",
        )
        assert out.accepted is True
        dumped = await _serialized_rows(session, EPISODE_TABLES + SUPPORT_TABLES)

    # Kanıt boş tablolara dayanmasın: gerçekten satır yazıldı.
    assert dumped["agent_session_episode_turn"], "tur kökeni yazılmalıydı"
    assert dumped["agent_session_episode_item"], "türetilmiş ifade yazılmalıydı"
    assert A3_RAW_SECRET not in _joined(dumped)


# ---------------------------------------------------------------------------
# 3. Log sızıntısı yok
# ---------------------------------------------------------------------------


async def test_raw_transcript_never_reaches_logs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, h4_ready: None
) -> None:
    caplog.set_level(logging.DEBUG)
    patch_provider(
        monkeypatch,
        ScriptedProvider(
            responses=[item_json("topic", "Alfa Projesi üzerinde çalışıldı.", "kullanıcı")]
        ),
    )

    async def _leaky_probe(session, source_row):  # noqa: ANN001 - test double
        raise RuntimeError(f"freshness probe failed while handling {A3_RAW_SECRET}")

    monkeypatch.setattr(continuity_service, "check_source_freshness", _leaky_probe)

    async with SessionLocal() as session:
        first = await start_session(session, "privacy-logs-a")
        await deliver(
            session,
            first,
            raw_turn_id="t1",
            sources=[Source(_SOURCE_ID, "project", title="Alfa Projesi")],
        )
        await ingest(
            session,
            "privacy-logs-a",
            turn_id="t1",
            user=f"kullanıcı {A3_RAW_SECRET} mesajı",
            assistant=f"asistan {A3_RAW_SECRET} yanıtı",
        )
        await seal(session, "privacy-logs-a")

        # Yeni oturumun ilk turu: devir seçimi tazelik probunu çalıştırır.
        other = await start_session(session, "privacy-logs-b")
        await deliver(
            session,
            other,
            raw_turn_id="t1",
            sources=[Source(_SOURCE_ID, "project", title="Alfa Projesi")],
        )

    # Degrade yolu gerçekten koştu (yoksa iddia boş olurdu)...
    assert any("RuntimeError" in record.getMessage() for record in caplog.records)
    # ...ama istisna METNİ loglanmadı.
    assert A3_RAW_SECRET not in caplog.text


async def test_ledger_degradation_log_carries_only_the_exception_type(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, h4_ready: None
) -> None:
    caplog.set_level(logging.DEBUG)

    async def _boom(*args, **kwargs):  # noqa: ANN002, ANN003 - test double
        raise RuntimeError(A3_RAW_SECRET)

    monkeypatch.setattr(a3, "record_delivered", _boom)

    async with SessionLocal() as session:
        row = await start_session(session, "privacy-logs-ledger")
        handoff, rendered, degraded = await a3.observe_turn_delivery(
            session,
            session_row=row,
            raw_turn_id="t1",
            turn_db_id=None,
            sources=[Source(_SOURCE_ID, "project", title="Alfa Projesi")],
            is_first_turn=False,
        )

    assert handoff is None and rendered is None
    assert "SOURCE_BINDING_UNAVAILABLE" in degraded
    assert any("RuntimeError" in record.getMessage() for record in caplog.records)
    assert A3_RAW_SECRET not in caplog.text


# ---------------------------------------------------------------------------
# 4./5. Güvenli şemalar (DB'siz)
# ---------------------------------------------------------------------------


@pytest.mark.no_database
def test_safe_response_models_expose_no_raw_conversation_fields() -> None:
    for model in (EpisodeTurnOut, EpisodeStatusOut):
        leaked = sorted(
            name
            for name in model.model_fields
            if any(fragment in name for fragment in FORBIDDEN_NAME_FRAGMENTS)
        )
        assert leaked == [], f"{model.__name__} exposes raw conversation fields: {leaked}"


@pytest.mark.no_database
def test_turn_schema_rejects_conversation_history() -> None:
    with pytest.raises(ValidationError):
        EpisodeTurnIn(
            schema_version=1,
            harness="hermes",
            session_id="s",
            turn_id="t",
            conversation_history=[{"role": "user", "content": "raw"}],
        )


@pytest.mark.no_database
def test_finalize_schema_rejects_extra_transcript_fields() -> None:
    with pytest.raises(ValidationError):
        EpisodeFinalizeIn(
            schema_version=1,
            harness="hermes",
            session_id="s",
            transcript="raw transcript",
        )


# ---------------------------------------------------------------------------
# 6. Uzun birebir kopya reddedilir
# ---------------------------------------------------------------------------


async def test_long_verbatim_copy_of_the_turn_is_rejected(
    monkeypatch: pytest.MonkeyPatch, h4_ready: None
) -> None:
    user = f"kullanıcı {A3_RAW_SECRET} " + "kelime " * 40
    leaked_text = user[:150]
    patch_provider(
        monkeypatch,
        ScriptedProvider(responses=[item_json("topic", leaked_text, user[:20])]),
    )
    async with SessionLocal() as session:
        await start_session(session, "privacy-verbatim")
        out = await ingest(
            session, "privacy-verbatim", turn_id="t1", user=user, assistant="kısa yanıt"
        )
        dumped = await _serialized_rows(session, EPISODE_TABLES)

    assert out.derived_item_count == 0
    assert "VERBATIM_LEAKAGE" in out.degraded_reasons
    assert A3_RAW_SECRET not in _joined(dumped)


# ---------------------------------------------------------------------------
# 7. Digest var, ham metin yok
# ---------------------------------------------------------------------------


async def test_stored_turn_digest_is_reproducible_and_input_bound(
    monkeypatch: pytest.MonkeyPatch, h4_ready: None
) -> None:
    patch_provider(
        monkeypatch,
        ScriptedProvider(responses=[item_json("topic", "Tur kaydedildi.", "kullanıcı")]),
    )
    user, assistant = "kullanıcı mesajı", "asistan yanıtı"
    async with SessionLocal() as session:
        row = await start_session(session, "privacy-digest")
        session_key = row.session_key
        await ingest(session, "privacy-digest", turn_id="t1", user=user, assistant=assistant)
        key = turn_key(session_key, "t1")
        stored = (
            await session.execute(
                select(AgentSessionEpisodeTurn.turn_digest).where(
                    AgentSessionEpisodeTurn.turn_key == key
                )
            )
        ).scalar_one()

    expected = compute_turn_digest(
        session_key=session_key, turn_key=key, user_text=user, assistant_text=assistant
    )
    assert stored == expected
    assert re.fullmatch(r"[0-9a-f]{64}", stored or ""), stored
    # Deterministik: aynı girdi aynı digest.
    assert (
        compute_turn_digest(
            session_key=session_key, turn_key=key, user_text=user, assistant_text=assistant
        )
        == expected
    )
    # Girdiye bağlı: farklı tur içeriği farklı digest.
    assert (
        compute_turn_digest(
            session_key=session_key, turn_key=key, user_text=user, assistant_text="başka yanıt"
        )
        != expected
    )


# ---------------------------------------------------------------------------
# 8. Kısa kimlik bilgisi / sır sızıntısı reddedilir (A3.1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "secret_payload",
    [
        "sk-ant-api03-abcdef123456789012345678",
        "password=supersecretpassword123",
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-ID4nzNQbu",
        "ghp_123456789012345678901234567890123456",
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...",
    ],
)
async def test_derived_item_containing_secret_pattern_is_rejected(
    monkeypatch: pytest.MonkeyPatch, h4_ready: None, secret_payload: str
) -> None:
    user = f"Kullanıcı ayar sordu: {secret_payload}"
    derived_text = f"Anahtar tanımlandı: {secret_payload}"
    patch_provider(
        monkeypatch,
        ScriptedProvider(responses=[item_json("reference", derived_text, secret_payload[:25])]),
    )
    async with SessionLocal() as session:
        await start_session(session, "privacy-secret-leak")
        out = await ingest(
            session, "privacy-secret-leak", turn_id="t1", user=user, assistant="tamam"
        )
        items = (
            await session.execute(
                select(AgentSessionEpisodeItem)
            )
        ).scalars().all()
        dumped = await _serialized_rows(session, EPISODE_TABLES)

    assert out.derived_item_count == 0
    assert len(items) == 0
    assert "SECRET_LEAKAGE" in out.degraded_reasons
    assert secret_payload not in _joined(dumped)
