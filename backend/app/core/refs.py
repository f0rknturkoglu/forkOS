"""Govde metnindeki referanslar: [[wikilink]] ve satir ici #etiket.

Etiket havuzu ZATEN entity seviyesinde ve paylasimli (core/tags.py); burasi
onu "not govdesinden de beslenebilir" hale getirir -- ayri bir not-etiketi
kavrami YOKTUR. Wikilink'ler `mentions` iliskisine cevrilir; backlink paneli
ayni link tablosundan okur.

PHASE 3 SINIRI: `sync_refs` ve `parse_wikilinks` yalnizca legacy Notlar
govdesinden anlam tasir. Bilgi sahipligi Vault'a gectigi icin bu fonksiyonlar
artik hiçbir ÜRÜN akisindan cagrilmaz: tek cagiran, dondurulmus arsiv
yazicisidir (`app.modules.note.service`, PHASE 2 goc testlerinin kaynak
verisini uretir). Yeni bir urun ozelligi bu modulu BAGLAMAMALIDIR -- Vault
wikilink'lerini Obsidian cozer.

Cozulmemis wikilink (henuz o baslikta kayit yok) HATA DEGILDIR: link
yazilmaz, cagiran taraf onu "olusturulabilir" olarak gosterir.
"""

from __future__ import annotations

import re
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import tags as tag_svc
from app.core.links import link
from app.core.models import Entity, Link

#: [[Baslik]] ya da [[Baslik|gorunen metin]]. Ic ice koseli parantez yok.
WIKILINK = re.compile(r"\[\[([^\[\]|\n]{1,200}?)(?:\|([^\[\]\n]{0,200}))?\]\]")

#: #etiket -- Turkce harfler dahil. Basindaki karakter harf/rakam/`/`/`#`
#: OLMAMALI: markdown basligi ("# Baslik", bosluk var) ve URL cirpasi
#: ("site.com/#bolum") etiket sayilmaz.
INLINE_TAG = re.compile(
    r"(?<![\w#/=])#([A-Za-zÇĞİÖŞÜçğıöşü][\w\-çğıöşüÇĞİÖŞÜ]{0,63})",
    re.UNICODE,
)

#: Kod blogu ve satir ici kod -- icindeki #/[[ ]] ayristirilmaz.
CODE_SPAN = re.compile(r"```.*?```|`[^`\n]*`", re.S)


def _without_code(body: str) -> str:
    """Kod bloklarini bosluga cevirir; ofsetler bozulmasin diye ayni uzunlukta."""
    return CODE_SPAN.sub(lambda m: " " * len(m.group(0)), body)


def parse_wikilinks(body: str) -> list[str]:
    """Govdedeki [[hedef]] basliklari -- sirasi korunur, tekrarlar tekillesir."""
    seen: dict[str, None] = {}
    for match in WIKILINK.finditer(_without_code(body or "")):
        target = match.group(1).strip()
        if target:
            seen.setdefault(target, None)
    return list(seen)


def parse_tags(body: str) -> list[str]:
    """Govdedeki #etiketler. Kucuk/buyuk harf farki tag havuzunda erir."""
    seen: dict[str, None] = {}
    for match in INLINE_TAG.finditer(_without_code(body or "")):
        seen.setdefault(match.group(1), None)
    return list(seen)


async def resolve_titles(
    session: AsyncSession, titles: list[str]
) -> dict[str, tuple[uuid.UUID, str]]:
    """Baslik -> (entity id, tip). Buyuk/kucuk harf duyarsiz, arsivliler haric.

    TEK sorgu: cagiran taraf coklu not icin de bunu toplu kullanabilsin
    (liste ucunda N+1 olmasin).
    """
    if not titles:
        return {}
    lowered = [t.casefold() for t in titles]
    rows = (
        await session.execute(
            select(Entity.id, Entity.title, Entity.type)
            .where(func.lower(Entity.title).in_(lowered), Entity.archived_at.is_(None))
            .order_by(Entity.updated_at.desc())
        )
    ).all()
    # Ayni baslikta birden fazla kayit varsa en son guncellenen kazanir.
    by_lower: dict[str, tuple[uuid.UUID, str]] = {}
    for entity_id, title, type_ in rows:
        by_lower.setdefault(title.casefold(), (entity_id, type_))
    return {title: by_lower[title.casefold()] for title in titles if title.casefold() in by_lower}


async def sync_refs(
    session: AsyncSession,
    entity_id: uuid.UUID,
    body: str,
    *,
    extra_tags: list[str] | None = None,
) -> dict:
    """Govdeyi okuyup `mentions` baglarini ve etiketleri esitler (idempotent).

    Bag kumesi govdenin AYNASIDIR: metinden cikan wikilink'in bagi da gider.
    Elle kurulmus baska iliskiler (`notes_about`, `related`...) etkilenmez --
    yalnizca `mentions` yeniden yazilir.
    """
    targets = parse_wikilinks(body)
    resolved = await resolve_titles(session, targets)

    await session.execute(
        delete(Link).where(Link.from_id == entity_id, Link.relation == "mentions")
    )
    for target in targets:
        hit = resolved.get(target)
        if hit is not None and hit[0] != entity_id:
            await link(session, entity_id, hit[0], "mentions")

    names = list(dict.fromkeys([*(extra_tags or []), *parse_tags(body)]))
    await tag_svc.set_tags(session, entity_id, names)

    return {
        "tags": names,
        "links": [
            {"target": t, "id": resolved[t][0], "type": resolved[t][1]}
            for t in targets
            if t in resolved
        ],
        "unresolved": [t for t in targets if t not in resolved],
    }
