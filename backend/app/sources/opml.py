"""OPML import. Ag ve DB'den bagimsiz saf fonksiyon -- test edilebilir kalsin.

Kategori = feed'i saran <outline> grubunun basligi (Feedly, Inoreader ve
NetNewsWire disa aktarimlari bu yapiyi kullanir).
"""
from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree


@dataclass(frozen=True)
class OpmlFeed:
    url: str
    title: str
    site_url: str | None = None
    category: str | None = None


def parse_opml(content: bytes | str) -> list[OpmlFeed]:
    """Ic ice gecmis outline'lari duzlestirir. Ayni URL bir kez doner."""
    if isinstance(content, str):
        content = content.encode()
    if len(content) > 2_000_000 or b"<!DOCTYPE" in content.replace(b"\x00",b"").upper() or b"<!ENTITY" in content.replace(b"\x00",b"").upper():
        raise ValueError("OPML boyut sınırı aşıldı veya DTD/entity içeriyor")
    root = ElementTree.fromstring(content)
    body = root.find("body")
    if body is None:
        return []

    feeds: list[OpmlFeed] = []
    seen: set[str] = set()

    def walk(node, category: str | None) -> None:
        for outline in node.findall("outline"):
            url = (outline.get("xmlUrl") or "").strip()
            title = (outline.get("title") or outline.get("text") or "").strip()
            if url:
                if url not in seen:
                    seen.add(url)
                    feeds.append(OpmlFeed(
                        url=url,
                        title=title or url,
                        site_url=(outline.get("htmlUrl") or "").strip() or None,
                        category=category,
                    ))
            else:
                # xmlUrl'i olmayan outline = klasor; basligi kategori olur
                walk(outline, title or category)

    walk(body, None)
    return feeds
