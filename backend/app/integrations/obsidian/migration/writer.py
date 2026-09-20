"""Vault'a yazma ilkelleri (PHASE 12, 15, 20).

Kurallar:
- Var olan dosyanin UZERINE YAZILMAZ; olusturma `O_CREAT | O_EXCL` iledir.
- Icerik ayniysa dosya yeniden kullanilir (idempotent tekrar calistirma).
- Icerik farkliysa (kullanici Obsidian'da duzenlemis olabilir) dosya
  `diverged` isaretlenir ve raporlanir.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path

from app.integrations.obsidian.frontmatter import parse_frontmatter
from app.integrations.obsidian.migration.plan import (
    ATTACHMENTS_ROOT,
    PlannedAttachment,
    sanitize_attachment_name,
    sha256_of,
)
from app.integrations.obsidian.migration.source import SourceAttachment, read_attachment_bytes
from app.integrations.obsidian.security import resolve_safe_vault_path

CREATED = "created"
REUSED = "reused"
DIVERGED = "diverged"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(payload: object) -> str:
    """Semantik (anahtar sirasindan bagimsiz) JSON gosterimi."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def create_exclusive(path: Path, data: bytes) -> None:
    """Yeni dosyayi atomik ve rakipsiz olustur; var olan dosyaya DOKUNMA."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    try:
        with open(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        with contextlib.suppress(OSError):
            path.unlink(missing_ok=True)
        raise


def normalized_note(content: str) -> tuple[dict, str]:
    """Karsilastirma icin: `forkos_migrated_at` disarida, govde kirpilmis."""
    metadata, body = parse_frontmatter(content or "")
    cleaned = dict(metadata or {})
    cleaned.pop("forkos_migrated_at", None)
    return cleaned, (body or "").strip()


def compare_note(existing: str, expected: str) -> bool:
    """Mevcut dosya beklenen icerikle AYNI mi (migration zamani haric)?"""
    return normalized_note(existing) == normalized_note(expected)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_note(vault_root: Path, relative_path: str, content: str) -> tuple[str, str | None]:
    """Not dosyasini yaz ya da mevcut olani degerlendir.

    Returns: (status, existing_content | None)
    """
    target = resolve_safe_vault_path(vault_root, relative_path)
    if target.is_file():
        existing = read_text(target)
        if compare_note(existing, content):
            return REUSED, existing
        return DIVERGED, existing
    try:
        create_exclusive(target, content.encode("utf-8"))
    except FileExistsError:
        existing = read_text(target)
        if compare_note(existing, content):
            return REUSED, existing
        return DIVERGED, existing
    return CREATED, None


def _attachment_candidates(planned: PlannedAttachment, digest: str) -> list[str]:
    stem, suffix = sanitize_attachment_name(planned.original_name)[1:]
    candidates = [planned.vault_path]
    for width in (8, 12, 16, 32, 64):
        candidate = f"{ATTACHMENTS_ROOT}/{stem}--{digest[:width]}{suffix}"
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def write_attachment(
    vault_root: Path,
    planned: PlannedAttachment,
    source: SourceAttachment,
) -> tuple[str, str, str | None, str | None]:
    """Eki Vault'a kopyala; icerik ayniysa mevcut dosyayi kullan.

    Returns: (vault_path, status, sha256, error)
    """
    try:
        data = planned.content if planned.content is not None else read_attachment_bytes(source)
    except Exception as exc:  # noqa: BLE001 - per-note hata raporlanir
        return planned.vault_path, DIVERGED, None, str(exc)

    digest = planned.content_sha256 or sha256_of(data)

    for candidate in _attachment_candidates(planned, digest):
        target = resolve_safe_vault_path(vault_root, candidate)
        if target.is_file():
            try:
                existing_digest = sha256_file(target)
            except OSError as exc:
                return candidate, DIVERGED, digest, f"mevcut ek okunamadı: {exc}"
            if existing_digest == digest:
                return candidate, REUSED, digest, None
            continue
        try:
            create_exclusive(target, data)
        except FileExistsError:
            continue
        return candidate, CREATED, digest, None

    return planned.vault_path, DIVERGED, digest, "ek için deterministik ad bulunamadı"


def write_canvas_sidecar(
    vault_root: Path, relative_path: str, canvas_state: dict
) -> tuple[str, str, str | None]:
    """Canvas verisini KAYIPSIZ yan dosya olarak yaz (PHASE 15).

    Returns: (status, canonical_sha256, error)
    """
    canonical = canonical_json(canvas_state)
    canonical_sha = sha256_of(canonical.encode("utf-8"))
    content = json.dumps(canvas_state, ensure_ascii=False, indent=2) + "\n"
    target = resolve_safe_vault_path(vault_root, relative_path)

    if target.is_file():
        try:
            existing = json.loads(read_text(target))
        except (OSError, json.JSONDecodeError) as exc:
            return DIVERGED, canonical_sha, f"yan dosya okunamadı: {exc}"
        if canonical_json(existing) == canonical:
            return REUSED, canonical_sha, None
        return DIVERGED, canonical_sha, "yan dosya kaynaktan farklı (elle değiştirilmiş olabilir)"

    try:
        create_exclusive(target, content.encode("utf-8"))
    except FileExistsError:
        return DIVERGED, canonical_sha, "yan dosya bu arada oluşturuldu"
    return CREATED, canonical_sha, None
