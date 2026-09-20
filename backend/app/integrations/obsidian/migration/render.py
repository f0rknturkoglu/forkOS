"""Migration frontmatter sozlesmesi ve govde donusumleri (PHASE 2, 3, 4, 12, 13, 14).

Govde donusumu SAF ve DETERMINISTIKTIR: ayni kaynak govde + ayni plan her
zaman ayni ciktiyi verir. Bu sayede dogrulama, Vault'taki govdenin sha256'sini
yeniden uretilen govdeyle karsilastirabilir (PHASE 21).
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.core.refs import CODE_SPAN, WIKILINK
from app.integrations.obsidian.frontmatter import render_markdown_with_frontmatter
from app.integrations.obsidian.migration.source import (
    SourceBookmark,
    SourceNote,
    SourceRelation,
)

#: Frontmatter sozlesme surumu. Uyumsuz surum = migration blocker.
MIGRATION_VERSION = 1

UNPLACED_MARKER = "<!-- forkos:migrated-attachments -->"
UNPLACED_HEADING = "## Ekler"

#: forkOS ek indirme URL'i (opsiyonel host oneki ile).
ATTACHMENT_URL = re.compile(
    r"(?:https?://[^\s/<>()]+)?/api/notes/(?P<note>[0-9a-fA-F-]{36})"
    r"/attachments/(?P<attachment>[A-Za-z0-9._~-]{1,64})"
)

_URL_IN_PARENS = r"[^()\s<>]+"
_MD_IMAGE = re.compile(
    rf"!\[(?P<alt>[^\]\n]*)\]\(\s*<?(?P<url>{_URL_IN_PARENS})>?"
    rf"(?:\s+[\"'][^\"']*[\"'])?\s*\)"
)
_MD_LINK = re.compile(
    rf"(?<!!)\[(?P<text>[^\]\n]*)\]\(\s*<?(?P<url>{_URL_IN_PARENS})>?"
    rf"(?:\s+[\"'][^\"']*[\"'])?\s*\)"
)


@dataclass
class WikilinkStats:
    rewritten: int = 0
    retained: int = 0
    unresolved: list[str] = field(default_factory=list)
    non_note: list[str] = field(default_factory=list)


@dataclass
class BodyResult:
    body: str
    wikilinks: WikilinkStats
    referenced_attachments: set[str] = field(default_factory=set)


def apply_outside_code(text: str, transform) -> str:
    """Donusumu YALNIZCA kod bloklari/satir ici kod DISINDA uygula."""
    parts: list[str] = []
    last = 0
    for match in CODE_SPAN.finditer(text or ""):
        parts.append(transform(text[last : match.start()]))
        parts.append(match.group(0))
        last = match.end()
    parts.append(transform(text[last:]))
    return "".join(parts)


def relation_entries(relations: tuple[SourceRelation, ...] | list[SourceRelation]) -> list[dict]:
    """`mentions` disindaki not iliskilerini kompakt metadata'ya cevirir (PHASE 4).

    `mentions` yazilmaz: onlar zaten govdedeki `[[wikilink]]`lerle temsil edilir.
    """
    entries = []
    for relation in sorted(
        (item for item in relations if item.relation != "mentions"),
        key=lambda item: (item.relation, str(item.target_id)),
    ):
        entry = {
            "relation": relation.relation,
            "target_id": str(relation.target_id),
            "target_type": relation.target_type,
        }
        if relation.target_title:
            entry["target_title"] = relation.target_title
        entries.append(entry)
    return entries


def canonical_tags(tags: tuple[str, ...] | list[str]) -> list[str]:
    """Etiketleri buyuk/kucuk harf duyarsiz tekille; yazim deterministik kalir."""
    ordered = sorted(
        (tag.strip() for tag in tags if tag and tag.strip()),
        key=lambda tag: (tag.casefold(), tag),
    )
    seen: set[str] = set()
    out: list[str] = []
    for tag in ordered:
        key = tag.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(tag)
    return out


def build_frontmatter(
    note: SourceNote,
    kind: str,
    *,
    migrated_at: str,
    bookmark: SourceBookmark | None = None,
    canvas_sidecar: str | None = None,
) -> dict:
    """Legacy notu Obsidian frontmatter sozlesmesine cevirir."""
    metadata: dict = {
        "forkos_id": str(note.note_id),
        "forkos_type": "note",
        "forkos_note_kind": kind,
        "title": note.title,
        "forkos_created_at": note.created_at.isoformat() if note.created_at else None,
        "forkos_updated_at": note.updated_at.isoformat() if note.updated_at else None,
        "forkos_migrated_at": migrated_at,
        "forkos_state": note.state,
        "forkos_pinned": note.pinned,
    }
    if note.project_id is not None:
        metadata["forkos_project_id"] = str(note.project_id)
    if note.journal_day is not None:
        metadata["forkos_journal_day"] = note.journal_day.isoformat()
    if note.source_bookmark_id is not None:
        metadata["forkos_source_bookmark_id"] = str(note.source_bookmark_id)
        if bookmark is not None and bookmark.url:
            metadata["source"] = bookmark.url
        if bookmark is not None and bookmark.title:
            metadata["source_title"] = bookmark.title
    if note.folder_id is not None:
        metadata["forkos_legacy_folder_id"] = str(note.folder_id)
    if note.state == "trashed" and note.trashed_from_archive:
        metadata["forkos_trashed_from_archive"] = True
    relations = relation_entries(note.relations)
    if relations:
        metadata["forkos_relations"] = relations
    if canvas_sidecar:
        metadata["forkos_canvas_sidecar"] = canvas_sidecar
    metadata["forkos_source_body_sha256"] = note.body_sha256
    metadata["forkos_migration_version"] = MIGRATION_VERSION
    tags = canonical_tags(note.tags)
    if tags:
        metadata["tags"] = tags
    return metadata


def render_note(metadata: dict, body: str) -> str:
    return render_markdown_with_frontmatter(metadata, body)


def _attachment_id_from_url(url: str) -> str | None:
    match = ATTACHMENT_URL.fullmatch(url.strip())
    return match.group("attachment") if match else None


def rewrite_attachment_refs(
    body: str, attachment_paths: dict[str, str]
) -> tuple[str, set[str]]:
    """`/api/notes/.../attachments/...` referanslarini Obsidian baglantisina cevir.

    Desteklenen bicimler: `![alt](url)`, `[metin](url)`, ciplak url. Kod bloklari
    ve satir ici kod DOKUNULMAZ. Cozulemeyen referanslar aynen kalir.
    """
    referenced: set[str] = set()

    def resolve(url: str) -> str | None:
        attachment_id = _attachment_id_from_url(url)
        if attachment_id is None:
            return None
        path = attachment_paths.get(attachment_id)
        if path is None:
            return None
        referenced.add(attachment_id)
        return path

    def transform(chunk: str) -> str:
        def image(match: re.Match) -> str:
            path = resolve(match.group("url"))
            return f"![[{path}]]" if path else match.group(0)

        def link(match: re.Match) -> str:
            path = resolve(match.group("url"))
            if not path:
                return match.group(0)
            text = (match.group("text") or "").strip()
            return f"[[{path}|{text}]]" if text else f"[[{path}]]"

        def bare(match: re.Match) -> str:
            path = resolve(match.group(0))
            return f"[[{path}]]" if path else match.group(0)

        chunk = _MD_IMAGE.sub(image, chunk)
        chunk = _MD_LINK.sub(link, chunk)
        return ATTACHMENT_URL.sub(bare, chunk)

    return apply_outside_code(body or "", transform), referenced


def _without_extension(path: str) -> str:
    return path[:-3] if path.lower().endswith(".md") else path


def rewrite_wikilinks(
    body: str,
    *,
    resolution: dict[str, tuple[uuid.UUID, str]],
    note_paths: dict[uuid.UUID, str],
    stem_index: dict[str, tuple[str, ...]],
) -> tuple[str, WikilinkStats]:
    """Cozulebilen not wikilink'lerini deterministik Vault yoluna baglar (PHASE 14).

    Basit `[[Baslik]]` yalnizca dosya adi (stem) o baslikla AYNI ve TEK ise
    korunur; aksi halde tam yola genisletilir. Not olmayan hedefler ve
    cozulemeyen linkler aynen birakilir.
    """
    stats = WikilinkStats()

    def transform(chunk: str) -> str:
        def replace(match: re.Match) -> str:
            target = match.group(1).strip()
            alias = (match.group(2) or "").strip()
            hit = resolution.get(target)
            if hit is None:
                if target and target not in stats.unresolved:
                    stats.unresolved.append(target)
                return match.group(0)

            entity_id, entity_type = hit
            path = note_paths.get(entity_id)
            if entity_type != "note" or path is None:
                if target and target not in stats.non_note:
                    stats.non_note.append(target)
                return match.group(0)

            stem = Path(path).stem.casefold()
            if stem == target.casefold() and len(stem_index.get(stem, ())) == 1:
                stats.retained += 1
                return match.group(0)

            stats.rewritten += 1
            display = alias or target
            return f"[[{_without_extension(path)}|{display}]]"

        return WIKILINK.sub(replace, chunk)

    return apply_outside_code(body or "", transform), stats


def append_unplaced_section(body: str, links: list[str]) -> str:
    """Govdede gecmeyen ekleri kesfedilebilir kilan isaretli bolumu ekle (PHASE 13)."""
    if not links:
        return body
    lines = [UNPLACED_MARKER, "", UNPLACED_HEADING, ""]
    lines.extend(f"- [[{path}]]" for path in links)
    block = "\n".join(lines)
    clean = (body or "").rstrip()
    return f"{clean}\n\n{block}" if clean else block


def build_body(
    note: SourceNote,
    *,
    attachment_paths: dict[str, str],
    resolution: dict[str, tuple[uuid.UUID, str]],
    note_paths: dict[uuid.UUID, str],
    stem_index: dict[str, tuple[str, ...]],
    reference_paths: dict[str, str] | None = None,
) -> BodyResult:
    """Tam govde donusumu: ek referanslari -> wikilink'ler -> yerlesmemis ekler.

    `attachment_paths` bu notun kendi ekleridir (yerlesmemis ek bolumu icin);
    `reference_paths` ise govdede gecen referanslari cozerken kullanilan
    (baska notlara ait olabilecek) tum ek haritasidir.
    """
    body, referenced = rewrite_attachment_refs(
        note.body, reference_paths if reference_paths is not None else attachment_paths
    )
    body, stats = rewrite_wikilinks(
        body, resolution=resolution, note_paths=note_paths, stem_index=stem_index
    )
    unplaced = sorted(
        path
        for attachment_id, path in attachment_paths.items()
        if attachment_id not in referenced
    )
    return BodyResult(
        body=append_unplaced_section(body, unplaced),
        wikilinks=stats,
        referenced_attachments=referenced,
    )
