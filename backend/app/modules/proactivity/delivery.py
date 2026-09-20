"""H6 teslimi — kisa, deterministik, model GEREKTIRMEYEN bildirim kompozisyonu.

Worker Hermes olmadan da calismalidir; bu yuzden bildirim metni burada
KODLA kurulur (LLM cagrisi yok). Uzun baglam Hermes'in isidir: bu bir dikkat
artefaktidir, nihai muhakeme degil.

Metin KURALI: olgusal, suclayici olmayan, en fazla 3 satir. "Ihmal ediyorsun"
gibi psikolojik cikarim YASAK; "kayitli aktivite yok" denir.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.notifications import notify
from app.core.time import local_today

#: Bildirim govdesinde en fazla kac olgu (§82/§178).
MAX_SURFACE_FACTS = 3
#: Digest'te en fazla kac madde.
MAX_DIGEST_ITEMS = 10
#: Tek satirin ust siniri (tasan metin kirpilir, sessizce uzamaz).
MAX_FACT_CHARS = 160


def _clip(text: str, limit: int = MAX_FACT_CHARS) -> str:
    clean = " ".join(str(text).split())
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"


def fact_line(item: object) -> str | None:
    """H5 ciktisindan TEK olgu satiri — kaynak tipi ne olursa olsun.

    DIKKAT: `dict` nesnelerinin `.title()` METODU vardir; bu yuzden once tip
    kontrolu yapilir, sonra alan okunur. Aksi halde bildirim govdesine
    "<built-in method title ...>" sizardi.
    """
    if item is None:
        return None
    if isinstance(item, str):
        return _clip(item) or None
    if isinstance(item, dict):
        text = item.get("text")
        title = item.get("title")
        detail = item.get("detail")
    else:
        text = getattr(item, "text", None)
        title = getattr(item, "title", None)
        detail = getattr(item, "detail", None)
    if text:
        # Yalnizca bosluktan olusan metin OLGU DEGILDIR: bos madde yazilmaz.
        return _clip(text) or None
    if not title:
        return None
    return _clip(f"{title} — {detail}" if detail else str(title)) or None


def compose_facts(items: list[object], *, limit: int = MAX_SURFACE_FACTS) -> list[str]:
    """Kararli sirada, tekrarsiz, en fazla `limit` olgu."""
    facts: list[str] = []
    for item in items:
        line = fact_line(item)
        if line and line not in facts:
            facts.append(line)
        if len(facts) >= limit:
            break
    return facts


def _join(facts: list[str]) -> str | None:
    return "\n".join(f"• {fact}" for fact in facts) if facts else None


# ---------------------------------------------------------------------------
# Kosu teslimi
# ---------------------------------------------------------------------------


async def deliver_run(
    session: AsyncSession,
    *,
    run_id: int,
    logical_trigger_key: str,
    delivery_count: int,
    title: str,
    facts: list[str],
    importance: int,
    entity_id: object | None = None,
    now: datetime,
) -> int | None:
    """Kosuyu kullaniciya teslim eder ve bildirim kimligini doner.

    Dedup anahtari TESLIM EPISODUNA baglidir (kosu + kacinci teslim): ayni
    mantiksal kosul ikinci kez bildirim uretmez, ama cooldown sonrasi YENI
    episode mesrudur (§72).
    """
    key = f"proactivity:{logical_trigger_key}:{delivery_count + 1}"
    created = await notify(
        session,
        kind="proactivity",
        title=_clip(title, 120),
        # Gövde sınırı BURADA da dayatılır: çağıran fazla satır geçse bile
        # bildirim kısa kalır (dikkat artefaktı, H5 dökümü değil).
        body=_join([line for line in facts if line][:MAX_SURFACE_FACTS]),
        dedup_key=key,
        entity_id=entity_id,  # type: ignore[arg-type]
        importance=importance,
    )
    if not created:
        # Bildirim zaten vardi: kosu yine de "teslim edildi" sayilmaz, cagiran
        # karar verir. Burada None donmek "yeni teslim yok" demektir.
        return None
    from sqlalchemy import select

    from app.core.models import Notification

    return (
        await session.execute(select(Notification.id).where(Notification.dedup_key == key))
    ).scalar_one_or_none()


async def deliver_digest(
    session: AsyncSession,
    *,
    entries: list[tuple[str, list[str]]],
    now: datetime,
) -> int | None:
    """Birden fazla adayi TEK bildirime indirir (§75).

    Cagiran, birlesen her uyeyi teslimden hemen once YENIDEN dogrulamis
    olmalidir; burada bayat icerik karari verilmez, yalnizca metin kurulur.
    """
    if not entries:
        return None
    lines: list[str] = []
    for title, facts in entries[:MAX_DIGEST_ITEMS]:
        summary = " · ".join(facts) if facts else None
        lines.append(_clip(f"{title} — {summary}" if summary else title, 200))
    key = f"proactivity:digest:{local_today(now).isoformat()}"
    created = await notify(
        session,
        kind="proactivity.digest",
        title=f"Bekleyen {len(lines)} başlık",
        body="\n".join(f"• {line}" for line in lines),
        dedup_key=key,
        importance=1,
    )
    if not created:
        return None
    from sqlalchemy import select

    from app.core.models import Notification

    return (
        await session.execute(select(Notification.id).where(Notification.dedup_key == key))
    ).scalar_one_or_none()
