"""A3 köken sözleşmesi (§9/§34): her ifade YALNIZ teslim edilen kaynak kümesine bağlanır.

Kanıtlanan iddialar:

1. Teslim edilen kanonik kaynak ifadeyle eşleşirse `canonical_supported` olur ve
   referansın kimliği teslim edilen kaynağın kimliğidir.
2. Aynı turda teslim edilmiş İLGİSİZ bir kaynak ifadeye BAĞLANMAZ.
3. Hiçbir eşleşme yoksa ifade dürüstçe `turn_derived` kalır (`support_refs=[]`).
   Bu bir HATA değildir.
4. Kapsam çelişkisi (devir kapsamı A, kaynak kapsamı B) bağlanmayı engeller.
5. İfade başına referans tavanı ≤ 5'tir.
6. Çok kısa başlıklar (`MIN_TITLE_MATCH_CHARS`) yanlış eşleşme üretmez.
7. Tur-türevi her ifadenin devirde erişilebilir bir `turn_digest`'i vardır.
8. `observed_during_session` ifadesi tur satırına bağlanamaz ve okunduğunda
   `turn_digest`'i YOKTUR.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.modules.agent_episode import service as a3
from app.modules.agent_episode.distill import delivered_ref_from_source, match_support_refs
from app.modules.agent_episode.models import (
    AgentSessionEpisode,
    AgentSessionEpisodeItem,
    AgentSessionEpisodeTurn,
)
from app.modules.agent_lifecycle.models import AgentSession
from app.modules.agent_lifecycle.service import session_key
from tests.a3_fixtures import (
    NOW,
    Source,
    deliver,
    ingest,
    item_json,
    items_json,
    patch_provider,
    seal,
    start_session,
)
from tests.h4_test_provider import ScriptedProvider

PROJECT_A = "11111111-1111-1111-1111-111111111111"
PROJECT_B = "22222222-2222-2222-2222-222222222222"


async def _items_for(session, raw_session_id: str) -> list[AgentSessionEpisodeItem]:
    """Oturumun taslağındaki türetilmiş ifadeleri ordinal sırasıyla okur."""
    key = session_key("hermes", raw_session_id)
    episode_id = (
        await session.execute(
            select(AgentSessionEpisode.id)
            .join(AgentSession, AgentSession.id == AgentSessionEpisode.session_id)
            .where(AgentSession.session_key == key)
        )
    ).scalar_one()
    return list(
        (
            await session.execute(
                select(AgentSessionEpisodeItem)
                .where(AgentSessionEpisodeItem.episode_id == episode_id)
                .order_by(AgentSessionEpisodeItem.ordinal)
            )
        )
        .scalars()
        .all()
    )


# ---------------------------------------------------------------------------
# 1. Sadece teslim edilen kümeden
# ---------------------------------------------------------------------------


async def test_item_matches_the_delivered_canonical_source(
    monkeypatch: pytest.MonkeyPatch, h4_ready: None
) -> None:
    patch_provider(
        monkeypatch,
        ScriptedProvider(
            responses=[item_json("topic", "Alfa Projesi üzerinde çalışıldı.", "Alfa Projesi")]
        ),
    )
    async with SessionLocal() as session:
        row = await start_session(session, "prov-1")
        await deliver(
            session,
            row,
            raw_turn_id="t1",
            sources=[
                Source(
                    f"entity:{PROJECT_A}",
                    "project",
                    title="Alfa Projesi",
                    scope_project=PROJECT_A,
                )
            ],
        )
        await ingest(
            session,
            "prov-1",
            turn_id="t1",
            user="Alfa Projesi hakkında konuştuk",
            assistant="Evet, Alfa Projesi ilerliyor.",
        )
        items = await _items_for(session, "prov-1")

    assert len(items) == 1
    item = items[0]
    assert item.evidence_class == "canonical_supported"
    assert len(item.support_refs) == 1
    assert item.support_refs[0]["source_id"] == f"entity:{PROJECT_A}"


# ---------------------------------------------------------------------------
# 2. İlgisiz kaynak bağlanmaz
# ---------------------------------------------------------------------------


async def test_unrelated_delivered_source_is_not_attached(
    monkeypatch: pytest.MonkeyPatch, h4_ready: None
) -> None:
    patch_provider(
        monkeypatch,
        ScriptedProvider(
            responses=[item_json("topic", "Alfa Projesi üzerinde çalışıldı.", "Alfa Projesi")]
        ),
    )
    async with SessionLocal() as session:
        row = await start_session(session, "prov-2")
        await deliver(
            session,
            row,
            raw_turn_id="t1",
            sources=[
                Source(
                    f"entity:{PROJECT_A}", "project", title="Alfa Projesi", scope_project=PROJECT_A
                ),
                Source(
                    f"entity:{PROJECT_B}", "project", title="Beta Projesi", scope_project=PROJECT_B
                ),
            ],
        )
        await ingest(
            session,
            "prov-2",
            turn_id="t1",
            user="Alfa Projesi hakkında konuştuk",
            assistant="Evet, Alfa Projesi ilerliyor.",
        )
        items = await _items_for(session, "prov-2")

    assert len(items) == 1
    attached = {ref["source_id"] for ref in items[0].support_refs}
    assert f"entity:{PROJECT_A}" in attached
    assert f"entity:{PROJECT_B}" not in attached


# ---------------------------------------------------------------------------
# 3. Eşleşme yoksa dürüst boş
# ---------------------------------------------------------------------------


async def test_item_without_any_match_stays_turn_derived(
    monkeypatch: pytest.MonkeyPatch, h4_ready: None
) -> None:
    patch_provider(
        monkeypatch,
        ScriptedProvider(
            responses=[item_json("topic", "Bambaşka bir konu konuşuldu.", "ilgisiz bir konu")]
        ),
    )
    async with SessionLocal() as session:
        row = await start_session(session, "prov-3")
        await deliver(
            session,
            row,
            raw_turn_id="t1",
            sources=[
                Source(
                    f"entity:{PROJECT_A}", "project", title="Alfa Projesi", scope_project=PROJECT_A
                )
            ],
        )
        await ingest(
            session,
            "prov-3",
            turn_id="t1",
            user="ilgisiz bir konu ele alındı",
            assistant="tamamlandı",
        )
        items = await _items_for(session, "prov-3")

    assert len(items) == 1
    # Bu bir hata DEĞİLDİR: eşleşme yoksa dürüst davranış ifadeyi bağlamamaktır.
    assert items[0].support_refs == []
    assert items[0].evidence_class == "turn_derived"


# ---------------------------------------------------------------------------
# 4. Kapsam çelişkisi
# ---------------------------------------------------------------------------


@pytest.mark.no_database
def test_scope_conflict_blocks_binding_in_both_directions() -> None:
    ref_b = delivered_ref_from_source(
        Source(f"entity:{PROJECT_B}", "project", title="Alfa Projesi", scope_project=PROJECT_B)
    )
    ref_a = delivered_ref_from_source(
        Source(f"entity:{PROJECT_A}", "project", title="Alfa Projesi", scope_project=PROJECT_A)
    )
    assert ref_a is not None and ref_b is not None

    # Devir kapsamı A, kaynak kapsamı B.
    assert (
        match_support_refs(
            item_text="Alfa Projesi",
            source_excerpt="Alfa Projesi",
            delivered_refs=[ref_b],
            scope_project=PROJECT_A,
        )
        == []
    )
    # Devir kapsamı B, kaynak kapsamı A.
    assert (
        match_support_refs(
            item_text="Alfa Projesi",
            source_excerpt="Alfa Projesi",
            delivered_refs=[ref_a],
            scope_project=PROJECT_B,
        )
        == []
    )
    # Kapsamlar uyuşursa aynı eşleşme kurulur (çelişki testi boş değil).
    assert len(
        match_support_refs(
            item_text="Alfa Projesi",
            source_excerpt="Alfa Projesi",
            delivered_refs=[ref_a],
            scope_project=PROJECT_A,
        )
    ) == 1


# ---------------------------------------------------------------------------
# 5. Ref tavanı
# ---------------------------------------------------------------------------


async def test_support_refs_are_capped_at_five(
    monkeypatch: pytest.MonkeyPatch, h4_ready: None
) -> None:
    titles = [f"Proje {index}" for index in range(1, 7)]
    phrase = " ".join(titles)
    sources = [
        Source(f"entity:{index:08d}-0000-0000-0000-000000000000", "project", title=title)
        for index, title in enumerate(titles, start=1)
    ]
    patch_provider(
        monkeypatch, ScriptedProvider(responses=[item_json("topic", f"{phrase} ele alındı.", phrase)])
    )
    async with SessionLocal() as session:
        row = await start_session(session, "prov-5")
        await deliver(session, row, raw_turn_id="t1", sources=sources)
        await ingest(session, "prov-5", turn_id="t1", user=phrase, assistant="tamam")
        items = await _items_for(session, "prov-5")

    assert len(items) == 1
    assert len(items[0].support_refs) == 5


# ---------------------------------------------------------------------------
# 6. Kısa başlık eşleşmez
# ---------------------------------------------------------------------------


async def test_short_title_never_matches(monkeypatch: pytest.MonkeyPatch, h4_ready: None) -> None:
    patch_provider(
        monkeypatch,
        ScriptedProvider(responses=[item_json("topic", "ab konusu ele alındı.", "ab konusu")]),
    )
    async with SessionLocal() as session:
        row = await start_session(session, "prov-6")
        await deliver(
            session,
            row,
            raw_turn_id="t1",
            sources=[
                Source(
                    f"entity:{PROJECT_A}", "project", title="ab", scope_project=PROJECT_A
                )
            ],
        )
        await ingest(session, "prov-6", turn_id="t1", user="ab konusu ele alındı", assistant="tamam")
        items = await _items_for(session, "prov-6")

    assert len(items) == 1
    assert items[0].support_refs == []
    assert items[0].evidence_class == "turn_derived"


# ---------------------------------------------------------------------------
# 7. Tur-türevi item'ların digest'i erişilebilir
# ---------------------------------------------------------------------------


async def test_handoff_exposes_a_digest_for_every_turn_derived_item(
    monkeypatch: pytest.MonkeyPatch, h4_ready: None
) -> None:
    patch_provider(
        monkeypatch,
        ScriptedProvider(
            responses=[
                items_json(
                    [
                        ("topic", "Alfa Projesi üzerinde çalışıldı.", "Alfa Projesi"),
                        ("open_thread", "Başka bir konu açık kaldı.", "başka bir konu"),
                    ]
                )
            ]
        ),
    )
    async with SessionLocal() as session:
        row = await start_session(session, "prov-7")
        await deliver(
            session,
            row,
            raw_turn_id="t1",
            sources=[Source(f"entity:{PROJECT_A}", "project", title="Alfa Projesi")],
        )
        await ingest(
            session,
            "prov-7",
            turn_id="t1",
            user="Alfa Projesi üzerinde çalıştık; başka bir konu açık kaldı",
            assistant="anlaşıldı",
        )
        await seal(session, "prov-7")

        other = await start_session(session, "prov-7-other")
        handoff = await a3.select_recent_handoff(
            session, current_session_id=other.id, current_scope=None
        )

    assert handoff is not None
    turn_items = [
        item for item in handoff.items if item.evidence_class != "observed_during_session"
    ]
    assert turn_items, "en az bir tur-türevi ifade beklenirdi"
    for item in turn_items:
        assert item.turn_digest is not None
        assert len(item.turn_digest) == 64


# ---------------------------------------------------------------------------
# 8. observed_during_session: tur bağı ve digest
# ---------------------------------------------------------------------------


async def _seed_episode_with_turn(session, raw_session_id: str):
    """Doğrudan bir devir + tur satırı kurar (gözlem ifadesi için zemin)."""
    session_row = await start_session(session, raw_session_id)
    episode = AgentSessionEpisode(
        session_id=session_row.id,
        schema_version=1,
        status="draft",
        scope_project=None,
        started_at=NOW,
        sealed_at=None,
        turn_count=0,
        item_count=0,
        degraded_reasons=[],
        expires_at=NOW.replace(year=NOW.year + 1),
    )
    session.add(episode)
    await session.flush()
    turn = AgentSessionEpisodeTurn(
        episode_id=episode.id,
        turn_id=None,
        turn_key="k" * 64,
        status="extracted",
        turn_digest="a" * 64,
        item_count=1,
        delivered_refs=[],
        degraded_reasons=[],
        delivered_at=NOW,
        observed_at=NOW,
    )
    session.add(turn)
    await session.flush()
    return episode, turn


async def test_observed_item_cannot_be_bound_to_a_turn_row() -> None:
    async with SessionLocal() as session:
        episode, turn = await _seed_episode_with_turn(session, "prov-8a")
        session.add(
            AgentSessionEpisodeItem(
                episode_id=episode.id,
                episode_turn_id=turn.id,
                ordinal=0,
                kind="outcome",
                text="Oturum penceresinde bir gözlem gerçekleşti.",
                evidence_class="observed_during_session",
                support_refs=[
                    {
                        "source_id": f"entity:{PROJECT_A}",
                        "source_type": "project",
                        "source_version": None,
                        "scope_project": None,
                    }
                ],
            )
        )
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


async def test_observed_item_is_read_back_without_a_turn_digest() -> None:
    async with SessionLocal() as session:
        episode, _turn = await _seed_episode_with_turn(session, "prov-8b")
        session.add(
            AgentSessionEpisodeItem(
                episode_id=episode.id,
                episode_turn_id=None,
                ordinal=0,
                kind="outcome",
                text="Oturum penceresinde bir gözlem gerçekleşti.",
                evidence_class="observed_during_session",
                support_refs=[
                    {
                        "source_id": f"entity:{PROJECT_A}",
                        "source_type": "project",
                        "source_version": None,
                        "scope_project": None,
                    }
                ],
            )
        )
        episode.status = "sealed"
        episode.sealed_at = NOW
        episode.item_count = 1
        other = await start_session(session, "prov-8b-other")
        await session.commit()

        handoff = await a3.select_recent_handoff(
            session, current_session_id=other.id, current_scope=None
        )

    assert handoff is not None
    observed = [item for item in handoff.items if item.evidence_class == "observed_during_session"]
    assert observed, "gözlem ifadesi devirde görünmeliydi"
    assert observed[0].turn_digest is None


async def test_observed_item_requires_evidence_refs() -> None:
    """`observed_during_session` KANIT taşımak zorundadır (§9/§10) — fail-closed.

    H5'in `ReviewInsight` kilidi gibi bu kural DB düzeyinde zorlanır: ref'siz
    bir "gerçekleşti" iddiası uydurma olurdu. Ref'siz INSERT reddedilir; ref'li
    INSERT geçer ve geri okunur.
    """
    async with SessionLocal() as session:
        episode, _turn = await _seed_episode_with_turn(session, "prov-8c")
        session.add(
            AgentSessionEpisodeItem(
                episode_id=episode.id,
                episode_turn_id=None,
                ordinal=0,
                kind="outcome",
                text="Kanıtsız bir gözlem ifadesi.",
                evidence_class="observed_during_session",
                support_refs=[],
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    async with SessionLocal() as session:
        episode, _turn = await _seed_episode_with_turn(session, "prov-8d")
        session.add(
            AgentSessionEpisodeItem(
                episode_id=episode.id,
                episode_turn_id=None,
                ordinal=0,
                kind="outcome",
                text="Kanıtlı bir gözlem ifadesi.",
                evidence_class="observed_during_session",
                support_refs=[
                    {
                        "source_id": "event:42",
                        "source_type": "event",
                        "source_version": None,
                        "scope_project": None,
                    }
                ],
            )
        )
        await session.commit()
        stored = (
            await session.execute(
                select(AgentSessionEpisodeItem.support_refs).where(
                    AgentSessionEpisodeItem.episode_id == episode.id
                )
            )
        ).scalar_one()

    assert stored and stored[0]["source_id"] == "event:42"
