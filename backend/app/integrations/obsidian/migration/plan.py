"""Deterministik hedef yol plani (PHASE 1, 5, 6, 11).

Plan, yazmadan ONCE tamamen hesaplanir: her notun hedef yolu, her ekin Vault
yolu ve stem indeksi tek turda belirlenir. Boylece ayni kaynak + ayni Vault
durumu her makinede AYNI plani uretir; "Title (1).md" gibi siraya bagli
adlandirma YOKTUR.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.integrations.obsidian.migration.source import (
    AttachmentUnavailable,
    SourceAttachment,
    SourceNote,
    SourceSnapshot,
    read_attachment_bytes,
)
from app.integrations.obsidian.security import sanitize_filename

#: Legacy not turleri. `forkos_type` HER ZAMAN `note` kalir; tur burada yasar.
PERSONAL = "personal"
DAILY = "daily"
PROJECT_JOURNAL = "project_journal"
BOOKMARK_NOTE = "bookmark_note"
NOTE_KINDS: tuple[str, ...] = (PERSONAL, DAILY, PROJECT_JOURNAL, BOOKMARK_NOTE)

PERSONAL_ROOT = "00 Inbox/Imported"
DAILY_ROOT = "10 Daily"
PROJECTS_ROOT = "20 Projects"
SOURCES_ROOT = "60 Sources/Imported"
ATTACHMENTS_ROOT = "Attachments"
CANVAS_SIDECAR_ROOT = "Attachments/Legacy Canvas"

#: Sonek uzunluklari: once kisa, gerekirse daha uzun (deneme sirasi sabit).
_SUFFIX_WIDTHS: tuple[int, ...] = (8, 12, 16, 32)

_VALID_EXT = re.compile(r"\A\.[A-Za-z0-9]{1,10}\Z")


class MigrationBlocked(Exception):
    """Fail-closed: plan guvenle kurulamadi (cakisma cozulemedi vb.)."""


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def classify_note_kind(note: SourceNote) -> str:
    """PHASE 1 onceligi: proje gunlugu > gunluk > yer imi > kisisel."""
    if note.project_id is not None and note.journal_day is not None:
        return PROJECT_JOURNAL
    if note.journal_day is not None:
        return DAILY
    if note.source_bookmark_id is not None:
        return BOOKMARK_NOTE
    return PERSONAL


def resolve_folder_path(
    folder_id: uuid.UUID | None,
    folder_map: dict[uuid.UUID, tuple[str, uuid.UUID | None]],
) -> tuple[str, list[str]]:
    """Not klasor hiyerarsisini kokten yapraka dogru rekursif cozer.

    Returns:
        (folder_path_prefix, warnings)
        Ornek cikti: ("Programming/Backend/ASP.NET/", [])
    """
    if folder_id is None:
        return "", []

    if folder_id not in folder_map:
        return "", [f"Bilinmeyen klasör referansı: {folder_id}"]

    segments: list[str] = []
    visited: set[uuid.UUID] = set()
    warnings: list[str] = []
    curr: uuid.UUID | None = folder_id

    while curr is not None:
        if curr in visited:
            warnings.append(f"Klasör hiyerarşisinde döngü tespit edildi: {curr}")
            break
        visited.add(curr)

        if curr not in folder_map:
            warnings.append(f"Klasör hiyerarşisinde eksik üst klasör referansı: {curr}")
            break

        title, parent_id = folder_map[curr]
        segments.append(sanitize_filename(title or "Folder"))
        curr = parent_id

    segments.reverse()
    if segments:
        return "/".join(segments) + "/", warnings
    return "", warnings


def note_stem(title: str) -> str:
    return sanitize_filename(title or "Untitled")


def note_base_path(
    note: SourceNote,
    kind: str,
    *,
    snapshot: SourceSnapshot,
) -> tuple[str, list[str]]:
    """Notun kanonik (cakismasiz) hedef yolu ve klasor uyarilari."""
    if kind == PROJECT_JOURNAL:
        project_title = snapshot.projects.get(note.project_id) if note.project_id else None
        project_name = sanitize_filename(project_title or "Project")
        day = note.journal_day.isoformat() if note.journal_day else "undated"
        return f"{PROJECTS_ROOT}/{project_name}/Journal/{day}.md", []

    if kind == DAILY:
        day = note.journal_day.isoformat() if note.journal_day else "undated"
        return f"{DAILY_ROOT}/{day}.md", []

    root = SOURCES_ROOT if kind == BOOKMARK_NOTE else PERSONAL_ROOT
    folder_part, warnings = resolve_folder_path(
        note.folder_id,
        {fid: (folder.title, folder.parent_id) for fid, folder in snapshot.folders.items()},
    )
    return f"{root}/{folder_part}{note_stem(note.title)}.md", warnings


def suffixed_path(base_path: str, note_id: uuid.UUID, width: int = 8) -> str:
    """`00 Inbox/Imported/Baslik--a1b2c3d4.md` (deterministik, siraya bagli degil)."""
    path = Path(base_path)
    digest = uuid.UUID(str(note_id)).hex
    return str(path.with_name(f"{path.stem}--{digest[:width]}{path.suffix}"))


def sanitize_attachment_name(name: str) -> tuple[str, str, str]:
    """(sanitize edilmis tam ad, govde, uzanti) dondurur."""
    raw = Path(str(name or "").replace("\\", "/")).name.strip()
    suffix = Path(raw).suffix
    if not _VALID_EXT.match(suffix):
        clean = sanitize_filename(raw)
        return clean, clean, ""
    stem = sanitize_filename(raw[: -len(suffix)])
    clean_suffix = suffix.lower()
    return f"{stem}{clean_suffix}", stem, clean_suffix


def collect_vault_paths(vault_root: Path) -> set[str]:
    """Vault'taki TUM dosyalarin (gizli dizinler haric) casefold edilmis yollari."""
    root = vault_root.resolve()
    paths: set[str] = set()
    if not root.is_dir():
        return paths
    for dirpath, dirnames, filenames in root.walk(follow_symlinks=False):
        dirnames[:] = [
            d for d in dirnames if not d.startswith(".") and not (Path(dirpath) / d).is_symlink()
        ]
        for name in filenames:
            if name.startswith("."):
                continue
            target = Path(dirpath) / name
            try:
                if target.is_symlink() or not target.is_file():
                    continue
                relative = target.relative_to(root)
            except (OSError, ValueError):
                continue
            paths.add(str(relative).casefold())
    return paths


@dataclass
class PlannedAttachment:
    attachment_id: str
    note_id: uuid.UUID
    original_name: str
    vault_path: str
    generation: str
    size: int
    content_sha256: str | None = None
    content: bytes | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class PlannedNote:
    note: SourceNote
    kind: str
    target_path: str
    base_path: str
    warnings: list[str] = field(default_factory=list)
    #: `None` (temiz yol) | duplicate_title | unmanaged_file | managed_reuse
    collision: str | None = None
    attachment_paths: dict[str, str] = field(default_factory=dict)
    canvas_sidecar_path: str | None = None


@dataclass
class MigrationPlan:
    snapshot: SourceSnapshot
    notes: dict[uuid.UUID, PlannedNote]
    attachments: dict[str, PlannedAttachment]
    path_collisions: dict[str, list[str]]
    stem_index: dict[str, tuple[str, ...]]
    blocked: list[str] = field(default_factory=list)


def _plan_note_paths(
    snapshot: SourceSnapshot,
    existing_paths: set[str],
    managed_by_id: dict[str, str],
) -> tuple[dict[uuid.UUID, PlannedNote], dict[str, list[str]]]:
    planned: dict[uuid.UUID, PlannedNote] = {}
    grouped: dict[str, list[str]] = {}
    display: dict[str, str] = {}

    for note in sorted(snapshot.notes, key=lambda n: str(n.note_id)):
        kind = classify_note_kind(note)
        base_path, warnings = note_base_path(note, kind, snapshot=snapshot)
        planned[note.note_id] = PlannedNote(
            note=note, kind=kind, target_path=base_path, base_path=base_path, warnings=warnings
        )
        key = base_path.casefold()
        grouped.setdefault(key, []).append(str(note.note_id))
        display.setdefault(key, base_path)

    collisions = {
        display[key]: ids for key, ids in sorted(grouped.items()) if len(ids) > 1
    }

    claimed: set[str] = set()
    for note_id in sorted(planned, key=str):
        entry = planned[note_id]
        managed_path = managed_by_id.get(str(note_id))
        if managed_path:
            entry.target_path = managed_path
            entry.collision = "managed_reuse"
            claimed.add(managed_path.casefold())
            continue

        base = entry.base_path
        duplicated = len(grouped[base.casefold()]) > 1
        if not duplicated and base.casefold() not in existing_paths:
            entry.target_path = base
        else:
            entry.collision = "duplicate_title" if duplicated else "unmanaged_file"
            entry.target_path = free_suffixed_path(base, note_id, existing_paths, claimed)
        claimed.add(entry.target_path.casefold())

    return planned, collisions


def free_suffixed_path(
    base_path: str,
    note_id: uuid.UUID,
    existing_paths: set[str] | None = None,
    claimed: set[str] | None = None,
) -> str:
    """Cakisma halinde deterministik sonekli yolu uret (plan ve yazma ani kullanir)."""
    for width in _SUFFIX_WIDTHS:
        candidate = suffixed_path(base_path, note_id, width)
        key = candidate.casefold()
        if key not in (existing_paths or set()) and key not in (claimed or set()):
            return candidate
    raise MigrationBlocked(
        f"Çakışma çözülemedi: '{base_path}' için deterministik ad bulunamadı (not {note_id})"
    )


def _plan_attachments(
    snapshot: SourceSnapshot, existing_paths: set[str]
) -> tuple[dict[str, PlannedAttachment], list[str]]:
    """Ekin Vault yolunu belirle; icerik YALNIZCA karar icin gerekiyorsa okunur."""
    grouped: dict[str, list[tuple[uuid.UUID, SourceAttachment]]] = {}
    for note in snapshot.notes:
        for attachment in note.attachments:
            full, _stem, _suffix = sanitize_attachment_name(attachment.name)
            grouped.setdefault(full.casefold(), []).append((note.note_id, attachment))

    planned: dict[str, PlannedAttachment] = {}
    blocked: list[str] = []
    for items in grouped.values():
        shared = len(items) > 1
        for note_id, attachment in items:
            stem, suffix = sanitize_attachment_name(attachment.name)[1:]
            base = f"{ATTACHMENTS_ROOT}/{stem}{suffix}"
            entry = PlannedAttachment(
                attachment_id=attachment.attachment_id,
                note_id=note_id,
                original_name=attachment.name,
                vault_path=base,
                generation=attachment.generation,
                size=attachment.size,
            )
            existing = planned.get(attachment.attachment_id)
            if existing is not None:
                entry.error = "ek kimliği birden fazla notta görünüyor"
                planned[f"{attachment.attachment_id}#{note_id}"] = entry
                blocked.append(f"{attachment.attachment_id}: ek kimliği tekrarlıyor")
                continue

            if shared or base.casefold() in existing_paths:
                _load_content(entry, attachment)
            if shared:
                digest = entry.content_sha256 or sha256_of(
                    f"unavailable:{attachment.attachment_id}".encode()
                )
                entry.vault_path = f"{ATTACHMENTS_ROOT}/{stem}--{digest[:8]}{suffix}"
            planned[attachment.attachment_id] = entry
    return planned, blocked


def _load_content(entry: PlannedAttachment, attachment: SourceAttachment) -> None:
    try:
        entry.content = read_attachment_bytes(attachment)
        entry.content_sha256 = sha256_of(entry.content)
    except AttachmentUnavailable as exc:
        entry.error = str(exc)


def _stem_index(notes: dict[uuid.UUID, PlannedNote]) -> dict[str, tuple[str, ...]]:
    index: dict[str, list[str]] = {}
    for entry in notes.values():
        stem = Path(entry.target_path).stem.casefold()
        if entry.target_path not in index.setdefault(stem, []):
            index[stem].append(entry.target_path)
    return {stem: tuple(paths) for stem, paths in index.items()}


def build_plan(
    snapshot: SourceSnapshot,
    *,
    existing_paths: set[str] | None = None,
    managed_by_id: dict[str, str] | None = None,
) -> MigrationPlan:
    """Kaynaktan tam plan uret (Vault'a YAZMAZ)."""
    existing = {path.casefold() for path in (existing_paths or set())}
    notes, collisions = _plan_note_paths(snapshot, existing, managed_by_id or {})
    attachments, blocked = _plan_attachments(snapshot, existing)

    for note_id, entry in notes.items():
        entry.attachment_paths = {
            aid: item.vault_path
            for aid, item in attachments.items()
            if item.note_id == note_id
        }
        if entry.note.has_canvas:
            entry.canvas_sidecar_path = f"{CANVAS_SIDECAR_ROOT}/{note_id}.excalidraw.json"

    return MigrationPlan(
        snapshot=snapshot,
        notes=notes,
        attachments=attachments,
        path_collisions=collisions,
        stem_index=_stem_index(notes),
        blocked=blocked,
    )
