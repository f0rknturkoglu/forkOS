"""A3 §11/§33 — tur damıtma: kaynağa bağlı çıkarım, dürüst degrade, uydurma yok.

Bu dosya H4'ü TAKLİT ETMEZ: gerçek `run_local_cognition` hattı (şema doğrulaması
ve `source_excerpt` grounding dahil) çalışır; yalnız yerel model sağlayıcısı
betiklenir. Bu yüzden "kaynakta olmayan alıntı reddedilir" iddiası uçtan uca
kanıtlanır.

Gözlemlenen davranış (buradaki iddiaların dayanağı):

- İki yerel yuva da yapılandırıldığında doğrulama hatası `local-small →
  local-medium` zincirini tüketir; H4 `LOCAL_CAPABILITY_UNAVAILABLE` döner ve A3
  bunu sınırlı bir gerekçe koduna indirger (`EPISODE_VALIDATION_FAILED` ya da
  `EPISODE_EXTRACTION_UNAVAILABLE`).
  `EPISODE_VALIDATION_FAILED` yalnız TEK yuva denendiğinde ve hata doğrulama
  kaynaklı olduğunda üretilir.
- Sağlayıcı hatası (`MODEL_PROVIDER_UNAVAILABLE`/`MODEL_UNAVAILABLE`) zinciri
  keser ve `LOCAL_COGNITION_UNAVAILABLE` olarak raporlanır.
- H4 kapalıysa (`H4_DISABLED`) hiçbir model çağrısı yapılmaz ve yine
  `LOCAL_COGNITION_UNAVAILABLE` döner.
- Hiçbir hata yolunda konuşmaya özgü anlamsal ifade ÜRETİLMEZ.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal
from app.modules.agent_episode import service as a3
from app.modules.agent_episode.models import AgentSessionEpisode, AgentSessionEpisodeItem
from tests.a3_fixtures import (
    Source,
    deliver,
    ingest,
    items_json,
    patch_provider,
    seal,
    start_session,
)
from tests.h4_test_provider import ScriptedProvider

#: Kullanıcı ve asistan metinleri: modelin alıntılayabileceği GEÇİCİ kaynak.
USER_MESSAGE = "Alfa projesi için sınav takvimini kontrol eder misin?"
ASSISTANT_RESPONSE = (
    "Alfa projesinin takvimi güncellendi. Beta modülü için açık bir iş kaldı: "
    "şema doğrulaması yazılacak. Sıradaki odak gama testleri."
)

#: Kaynağa bağlanabilen geçerli çıkarım: her `source_excerpt` kaynak metinde birebir var.
GROUNDED_ITEMS = [
    ("topic", "Alfa projesinin sınav takvimi ele alındı.", "Alfa projesinin takvimi güncellendi"),
    (
        "open_thread",
        "Beta modülünde şema doğrulaması yazılacak.",
        "Beta modülü için açık bir iş kaldı",
    ),
    ("next_focus", "Gama testlerine geçilecek.", "Sıradaki odak gama testleri"),
]


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def _stored_items(session: AsyncSession, session_row: Any) -> list[AgentSessionEpisodeItem]:
    """A1 oturumunun episode'undaki KALICI ifadeleri ordinal sırasıyla döner."""
    episode_id = (
        await session.execute(
            select(AgentSessionEpisode.id).where(
                AgentSessionEpisode.session_id == session_row.id
            )
        )
    ).scalar_one()
    rows = await session.execute(
        select(AgentSessionEpisodeItem)
        .where(AgentSessionEpisodeItem.episode_id == episode_id)
        .order_by(AgentSessionEpisodeItem.ordinal)
    )
    return list(rows.scalars().all())


@pytest.mark.usefixtures("h4_ready")
async def test_grounded_extraction_persists_items_without_degradation(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Geçerli, kaynağa bağlı çıkarım kalıcılaşır ve hiçbir gerekçe üretmez."""
    patch_provider(monkeypatch, ScriptedProvider(responses=[items_json(GROUNDED_ITEMS)]))
    session_row = await start_session(db_session, "a3-extract-grounded")
    await deliver(
        db_session,
        session_row,
        raw_turn_id="t1",
        sources=[Source("project:alfa", "project", title="Alfa Projesi")],
    )

    out = await ingest(
        db_session,
        "a3-extract-grounded",
        turn_id="t1",
        user=USER_MESSAGE,
        assistant=ASSISTANT_RESPONSE,
    )

    assert out.accepted is True
    assert out.duplicate is False
    assert out.derived_item_count == len(GROUNDED_ITEMS)
    # Kaynak defteri yazıldığı için SOURCE_BINDING_UNAVAILABLE yok; çıkarım da temiz.
    assert out.degraded_reasons == []

    stored = await _stored_items(db_session, session_row)
    assert [item.kind for item in stored] == [kind for kind, _, _ in GROUNDED_ITEMS]
    assert [item.text for item in stored] == [text for _, text, _ in GROUNDED_ITEMS]
    assert [item.ordinal for item in stored] == [0, 1, 2]
    for item in stored:
        assert item.evidence_class in {"turn_derived", "canonical_supported"}


@pytest.mark.usefixtures("h4_ready")
async def test_unsourced_excerpt_is_rejected_and_nothing_is_fabricated(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kaynakta bulunmayan `source_excerpt` grounding kapısından geçemez.

    Zincir tükendiğinde tüm denemeler `invalid` olduğu için sebep DOĞRULAMADIR:
    sınırlı kod `EPISODE_VALIDATION_FAILED` olur. Modelin uydurduğu ifade
    SAKLANMAZ ve tur düşmez.
    """
    patch_provider(
        monkeypatch,
        ScriptedProvider(
            responses=[
                items_json([("topic", "Uydurma bir konu işlendi.", "bu metin kaynakta yoktur")])
            ]
        ),
    )
    session_row = await start_session(db_session, "a3-extract-unsourced")
    await deliver(db_session, session_row, raw_turn_id="t1", sources=[])

    out = await ingest(
        db_session,
        "a3-extract-unsourced",
        turn_id="t1",
        user=USER_MESSAGE,
        assistant=ASSISTANT_RESPONSE,
    )

    assert out.derived_item_count == 0
    assert out.degraded_reasons == ["EPISODE_VALIDATION_FAILED"]
    assert await _stored_items(db_session, session_row) == []


@pytest.mark.usefixtures("h4_ready")
async def test_malformed_model_json_degrades_without_raising(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bozuk JSON bir doğrulama hatasıdır: tur düşmez, ifade üretilmez."""
    patch_provider(monkeypatch, ScriptedProvider(script="malformed_json"))
    session_row = await start_session(db_session, "a3-extract-malformed")
    await deliver(db_session, session_row, raw_turn_id="t1", sources=[])

    out = await ingest(
        db_session,
        "a3-extract-malformed",
        turn_id="t1",
        user=USER_MESSAGE,
        assistant=ASSISTANT_RESPONSE,
    )

    assert out.accepted is True
    assert out.derived_item_count == 0
    assert out.degraded_reasons == ["EPISODE_VALIDATION_FAILED"]
    assert await _stored_items(db_session, session_row) == []


async def test_h4_disabled_yields_no_semantic_items(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """H4 kapalıyken konuşmaya özgü hiçbir anlamsal ifade uydurulmaz."""
    monkeypatch.setattr(settings, "h4_enabled", False)
    session_row = await start_session(db_session, "a3-extract-h4-off")

    out = await ingest(
        db_session,
        "a3-extract-h4-off",
        turn_id="t1",
        user=USER_MESSAGE,
        assistant=ASSISTANT_RESPONSE,
    )

    assert out.derived_item_count == 0
    assert "LOCAL_COGNITION_UNAVAILABLE" in out.degraded_reasons
    assert await _stored_items(db_session, session_row) == []


@pytest.mark.usefixtures("h4_ready")
async def test_provider_timeout_is_bounded_and_degrades(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sağlayıcı zaman aşımı ingest'i askıda bırakmaz; sınırlı kodla degrade eder."""
    patch_provider(monkeypatch, ScriptedProvider(script="timeout"))
    session_row = await start_session(db_session, "a3-extract-timeout")
    await deliver(db_session, session_row, raw_turn_id="t1", sources=[])

    started = time.perf_counter()
    out = await ingest(
        db_session,
        "a3-extract-timeout",
        turn_id="t1",
        user=USER_MESSAGE,
        assistant=ASSISTANT_RESPONSE,
    )
    elapsed = time.perf_counter() - started

    assert elapsed < 5.0
    assert out.derived_item_count == 0
    assert out.degraded_reasons == ["LOCAL_COGNITION_UNAVAILABLE"]
    assert await _stored_items(db_session, session_row) == []


@pytest.mark.usefixtures("h4_ready")
async def test_missing_local_model_degrades(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Model kurulu değilse tur yine gözlenir; ifade uydurulmaz."""
    patch_provider(monkeypatch, ScriptedProvider(script="model_missing"))
    session_row = await start_session(db_session, "a3-extract-model-missing")
    await deliver(db_session, session_row, raw_turn_id="t1", sources=[])

    out = await ingest(
        db_session,
        "a3-extract-model-missing",
        turn_id="t1",
        user=USER_MESSAGE,
        assistant=ASSISTANT_RESPONSE,
    )

    assert out.derived_item_count == 0
    assert out.degraded_reasons == ["LOCAL_COGNITION_UNAVAILABLE"]
    assert await _stored_items(db_session, session_row) == []


@pytest.mark.usefixtures("h4_ready")
async def test_empty_model_output_degrades(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Boş model çıktısı doğrulamadan geçmez; uydurma yapılmaz."""
    patch_provider(monkeypatch, ScriptedProvider(script="empty_output"))
    session_row = await start_session(db_session, "a3-extract-empty-output")
    await deliver(db_session, session_row, raw_turn_id="t1", sources=[])

    out = await ingest(
        db_session,
        "a3-extract-empty-output",
        turn_id="t1",
        user=USER_MESSAGE,
        assistant=ASSISTANT_RESPONSE,
    )

    assert out.derived_item_count == 0
    assert out.degraded_reasons == ["EPISODE_VALIDATION_FAILED"]
    assert await _stored_items(db_session, session_row) == []


@pytest.mark.usefixtures("h4_ready")
async def test_empty_items_list_is_accepted_as_empty(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Doğrulanmış boş liste geçerlidir: ifade yok, dürüst `EPISODE_EMPTY` var."""
    patch_provider(monkeypatch, ScriptedProvider(responses=['{"items": []}']))
    session_row = await start_session(db_session, "a3-extract-empty-items")
    await deliver(db_session, session_row, raw_turn_id="t1", sources=[])

    out = await ingest(
        db_session,
        "a3-extract-empty-items",
        turn_id="t1",
        user=USER_MESSAGE,
        assistant=ASSISTANT_RESPONSE,
    )

    assert out.accepted is True
    assert out.derived_item_count == 0
    assert out.degraded_reasons == ["EPISODE_EMPTY"]
    assert await _stored_items(db_session, session_row) == []


async def test_h4_disabled_still_seals_as_empty(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """H4 yokken de mühürleme mümkündür: boş devir dürüstçe `sealed_empty` olur."""
    monkeypatch.setattr(settings, "h4_enabled", False)
    await start_session(db_session, "a3-extract-seal-h4-off")
    await ingest(
        db_session,
        "a3-extract-seal-h4-off",
        turn_id="t1",
        user=USER_MESSAGE,
        assistant=ASSISTANT_RESPONSE,
    )

    out = await seal(db_session, "a3-extract-seal-h4-off")

    assert out.sealed is True
    assert out.status == "sealed_empty"
    assert out.item_count == 0
    assert "EPISODE_EMPTY" in out.degraded_reasons


async def test_truncated_turn_is_visible_not_silently_swallowed(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kırpılmış tur sessizce yutulmaz: sınırlı kodla görünür kalır.

    Plugin `user_truncated`/`assistant_truncated` gönderir; sunucu bu bayrağı
    OKUMAZSA kırpılma bilgisi hiçbir yere yansımaz (sessiz no-op).
    """
    from app.modules.agent_episode.schemas import EpisodeTurnIn

    session_row = await start_session(db_session, "a3-extract-truncated")
    await deliver(db_session, session_row, raw_turn_id="t1", sources=[])

    out = await a3.ingest_turn(
        db_session,
        EpisodeTurnIn(
            schema_version=1,
            harness="hermes",
            session_id="a3-extract-truncated",
            turn_id="t1",
            platform="cli",
            user_message="kısa",
            assistant_response="kısa",
            assistant_truncated=True,
        ),
    )

    assert "EPISODE_INPUT_TRUNCATED" in out.degraded_reasons


async def test_turn_exceeding_the_composite_budget_is_rejected(
    db_session: AsyncSession,
) -> None:
    """Bileşik tur tavanı SUNUCUDA dayatılır, yalnız plugin'de değil."""
    from pydantic import ValidationError

    from app.modules.agent_episode.schemas import MAX_EPISODE_TURN_CHARS, EpisodeTurnIn

    with pytest.raises(ValidationError):
        EpisodeTurnIn(
            schema_version=1,
            harness="hermes",
            session_id="s",
            turn_id="t",
            platform="cli",
            user_message="x" * 2000,
            assistant_response="y" * (MAX_EPISODE_TURN_CHARS - 2000 + 1),
        )
