"""Migration manifest'i: kalici, atomik yazilan kesif kaniti (PHASE 7, 22).

`<Vault>/.forkos-migration/notes-v1/` altinda durur. Vault tarayicisi gizli
dizinleri atladigi icin manifest managed dosya sayilmaz.

Yazma yarim kalmasi durumunda manifest BOZULMAZ: her yazma gecici dosyaya
yazilip `os.replace` ile yerine konur.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MANIFEST_VERSION = 1
MIGRATION_NAME = "notes-v1"
MANIFEST_DIR = f".forkos-migration/{MIGRATION_NAME}"
MANIFEST_FILE = "manifest.json"
REPORT_FILE = "report.md"
ERRORS_FILE = "errors.json"

PLANNED = "planned"
COPIED = "copied"
VERIFIED = "verified"
SKIPPED_EXISTING = "skipped_existing"
BLOCKED = "blocked"
FAILED = "failed"
DIVERGED = "diverged"

ALL_STATUSES: tuple[str, ...] = (
    PLANNED,
    COPIED,
    VERIFIED,
    SKIPPED_EXISTING,
    BLOCKED,
    FAILED,
    DIVERGED,
)

#: `READY_FOR_CUTOVER` yalnizca bu durumlarla YES olabilir.
OK_STATUSES: tuple[str, ...] = (VERIFIED, SKIPPED_EXISTING)


class ManifestIncompatible(Exception):
    """Manifest surumu bu migration surumuyle uyusmuyor (fail closed)."""


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def write_json_atomic(path: Path, payload: Any) -> None:
    write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n")


@dataclass
class NoteEntry:
    note_id: str
    title: str
    note_kind: str
    target_path: str
    status: str
    source_body_sha256: str
    migrated_body_sha256: str | None = None
    migrated_at: str | None = None
    created_this_run: bool = False
    collision: str | None = None
    base_path: str | None = None
    attachments: list[dict] = field(default_factory=list)
    canvas: dict | None = None
    wikilinks: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "note_id": self.note_id,
            "title": self.title,
            "note_kind": self.note_kind,
            "target_path": self.target_path,
            "base_path": self.base_path,
            "status": self.status,
            "collision": self.collision,
            "source_body_sha256": self.source_body_sha256,
            "migrated_body_sha256": self.migrated_body_sha256,
            "migrated_at": self.migrated_at,
            "created_this_run": self.created_this_run,
            "attachments": self.attachments,
            "canvas": self.canvas,
            "wikilinks": self.wikilinks,
            "warnings": self.warnings,
            "errors": self.errors,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> NoteEntry:
        return cls(
            note_id=str(payload["note_id"]),
            title=str(payload.get("title") or ""),
            note_kind=str(payload.get("note_kind") or ""),
            target_path=str(payload.get("target_path") or ""),
            status=str(payload.get("status") or PLANNED),
            source_body_sha256=str(payload.get("source_body_sha256") or ""),
            migrated_body_sha256=payload.get("migrated_body_sha256"),
            migrated_at=payload.get("migrated_at"),
            created_this_run=bool(payload.get("created_this_run")),
            collision=payload.get("collision"),
            base_path=payload.get("base_path"),
            attachments=list(payload.get("attachments") or []),
            canvas=payload.get("canvas"),
            wikilinks=dict(payload.get("wikilinks") or {}),
            warnings=list(payload.get("warnings") or []),
            errors=list(payload.get("errors") or []),
        )


@dataclass
class Manifest:
    vault_root: str
    vault_name: str
    generated_at: str
    updated_at: str
    manifest_version: int = MANIFEST_VERSION
    migration: str = MIGRATION_NAME
    source_fingerprint_before: str | None = None
    source_fingerprint_after: str | None = None
    notes: dict[str, NoteEntry] = field(default_factory=dict)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "manifest_version": self.manifest_version,
            "migration": self.migration,
            "vault_root": self.vault_root,
            "vault_name": self.vault_name,
            "generated_at": self.generated_at,
            "updated_at": self.updated_at,
            "source_fingerprint_before": self.source_fingerprint_before,
            "source_fingerprint_after": self.source_fingerprint_after,
            "summary": self.summary,
            "notes": {
                note_id: entry.to_dict()
                for note_id, entry in sorted(self.notes.items())
            },
        }

    @classmethod
    def from_dict(cls, payload: dict) -> Manifest:
        version = int(payload.get("manifest_version") or 0)
        if version != MANIFEST_VERSION:
            raise ManifestIncompatible(
                f"Manifest sürümü uyumsuz: {version} (beklenen {MANIFEST_VERSION})"
            )
        return cls(
            vault_root=str(payload.get("vault_root") or ""),
            vault_name=str(payload.get("vault_name") or ""),
            generated_at=str(payload.get("generated_at") or ""),
            updated_at=str(payload.get("updated_at") or ""),
            manifest_version=version,
            migration=str(payload.get("migration") or MIGRATION_NAME),
            source_fingerprint_before=payload.get("source_fingerprint_before"),
            source_fingerprint_after=payload.get("source_fingerprint_after"),
            notes={
                str(note_id): NoteEntry.from_dict(entry)
                for note_id, entry in (payload.get("notes") or {}).items()
            },
            summary=dict(payload.get("summary") or {}),
        )


def manifest_dir(vault_root: Path) -> Path:
    return Path(vault_root) / MANIFEST_DIR


def manifest_path(vault_root: Path) -> Path:
    return manifest_dir(vault_root) / MANIFEST_FILE


def load_manifest(vault_root: Path) -> Manifest | None:
    """Manifest'i oku; yoksa None, bozuksa/uyumsuzsa hata (fail closed)."""
    path = manifest_path(vault_root)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ManifestIncompatible("Manifest kök nesnesi bir sözlük değil")
    return Manifest.from_dict(payload)


def save_manifest(vault_root: Path, manifest: Manifest) -> None:
    write_json_atomic(manifest_path(vault_root), manifest.to_dict())


def write_errors(vault_root: Path, payload: dict) -> None:
    write_json_atomic(manifest_dir(vault_root) / ERRORS_FILE, payload)


def write_report(vault_root: Path, text: str) -> None:
    write_text_atomic(manifest_dir(vault_root) / REPORT_FILE, text)
