"""Anlamsal dogrulama (PHASE 21).

"Beklenen govde" kaynaktan yeniden uretilir ve Vault'taki dosyayla
karsilastirilir; yalnizca "dosya var mi" sorusu sorulmaz.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.integrations.obsidian.frontmatter import parse_frontmatter
from app.integrations.obsidian.migration.plan import (
    MigrationPlan,
    PlannedAttachment,
    PlannedNote,
    sha256_of,
)
from app.integrations.obsidian.migration.writer import canonical_json, read_text, sha256_file
from app.integrations.obsidian.security import resolve_safe_vault_path


@dataclass
class ExpectedNote:
    """Kaynaktan yeniden uretilen beklenen cikti."""

    frontmatter: dict
    body: str
    content: str
    migrated_at: str | None = None
    canvas_canonical_sha: str | None = None
    attachments: list[PlannedAttachment] = field(default_factory=list)
    wikilinks: object | None = None


def verify_note(vault_root: Path, planned: PlannedNote, expected: ExpectedNote) -> list[str]:
    """Tek notun kimlik, govde, metadata, ek ve canvas dogrulamasi."""
    errors: list[str] = []
    target = resolve_safe_vault_path(vault_root, planned.target_path)

    if not target.is_file():
        return [f"hedef dosya yok: {planned.target_path}"]

    content = read_text(target)
    metadata, body = parse_frontmatter(content)
    if not metadata:
        return [f"frontmatter okunamadı: {planned.target_path}"]

    note_id = str(planned.note.note_id)
    if str(metadata.get("forkos_id")) != note_id:
        errors.append(f"forkos_id uyuşmuyor: {metadata.get('forkos_id')} != {note_id}")
    if str(metadata.get("forkos_type")) != "note":
        errors.append(f"forkos_type 'note' değil: {metadata.get('forkos_type')}")
    if str(metadata.get("forkos_note_kind")) != planned.kind:
        errors.append(
            f"forkos_note_kind uyuşmuyor: {metadata.get('forkos_note_kind')} != {planned.kind}"
        )

    expected_metadata = dict(expected.frontmatter)
    expected_metadata.pop("forkos_migrated_at", None)
    actual_metadata = dict(metadata)
    actual_migrated_at = actual_metadata.pop("forkos_migrated_at", None)
    for key, value in expected_metadata.items():
        if key not in actual_metadata:
            errors.append(f"metadata eksik: {key}")
        elif actual_metadata[key] != value:
            errors.append(
                f"metadata uyuşmuyor: {key} = {actual_metadata[key]!r} != {value!r}"
            )
    for key in actual_metadata:
        if key not in expected_metadata:
            errors.append(f"beklenmeyen metadata alanı: {key}")

    if expected.migrated_at is not None and actual_migrated_at != expected.migrated_at:
        errors.append(
            f"forkos_migrated_at uyuşmuyor: {actual_migrated_at!r} != {expected.migrated_at!r}"
        )

    expected_body = (expected.body or "").strip()
    if (body or "").strip() != expected_body:
        errors.append(
            "gövde beklenen dönüşümle eşleşmiyor "
            f"(beklenen sha256 {sha256_of(expected_body.encode('utf-8'))[:12]}, "
            f"mevcut {sha256_of((body or '').strip().encode('utf-8'))[:12]})"
        )

    for attachment in expected.attachments:
        errors.extend(verify_attachment(vault_root, attachment))

    if planned.canvas_sidecar_path and expected.canvas_canonical_sha:
        errors.extend(
            verify_canvas(vault_root, planned.canvas_sidecar_path, expected.canvas_canonical_sha)
        )

    return errors


def verify_attachment(vault_root: Path, planned: PlannedAttachment) -> list[str]:
    """Ek dosyasi var mi, boyutu ve sha256'si tutuyor mu?"""
    target = resolve_safe_vault_path(vault_root, planned.vault_path)
    if not target.is_file():
        return [f"ek dosyası yok: {planned.vault_path}"]
    errors: list[str] = []
    try:
        actual_size = target.stat().st_size
        actual_digest = sha256_file(target)
    except OSError as exc:
        return [f"ek okunamadı: {planned.vault_path} ({exc})"]
    if planned.content_sha256 and actual_digest != planned.content_sha256:
        errors.append(
            f"ek sha256 uyuşmuyor: {planned.vault_path} "
            f"({actual_digest[:12]} != {planned.content_sha256[:12]})"
        )
    if planned.size and actual_size != planned.size:
        errors.append(
            f"ek boyutu uyuşmuyor: {planned.vault_path} ({actual_size} != {planned.size})"
        )
    return errors


def verify_canvas(vault_root: Path, relative_path: str, canonical_sha: str) -> list[str]:
    """Canvas yan dosyasi kayipsiz mi (kanonik JSON ozeti tutuyor mu)?"""
    target = resolve_safe_vault_path(vault_root, relative_path)
    if not target.is_file():
        return [f"canvas yan dosyası yok: {relative_path}"]
    try:
        payload = json.loads(read_text(target))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"canvas yan dosyası geçersiz JSON: {relative_path} ({exc})"]
    actual = sha256_of(canonical_json(payload).encode("utf-8"))
    if actual != canonical_sha:
        return [
            f"canvas kanonik özeti uyuşmuyor: {relative_path} ({actual[:12]} != {canonical_sha[:12]})"
        ]
    return []


def canvas_canonical_sha(canvas_state: dict) -> str:
    return sha256_of(canonical_json(canvas_state).encode("utf-8"))


def verify_plan_identity(plan: MigrationPlan) -> list[str]:
    """Plan kimliklerinin tekilligini dogrula (fail closed girdisi)."""
    errors: list[str] = []
    seen: set[str] = set()
    for note_id in plan.notes:
        key = str(note_id)
        if key in seen:
            errors.append(f"not kimliği tekrarlıyor: {key}")
        seen.add(key)
    paths: dict[str, str] = {}
    for note_id, entry in plan.notes.items():
        key = entry.target_path.casefold()
        if key in paths and paths[key] != str(note_id):
            errors.append(
                f"hedef yol çakışması: {entry.target_path} ({paths[key]} ve {note_id})"
            )
        paths[key] = str(note_id)
    return errors
