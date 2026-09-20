from __future__ import annotations

import contextlib
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings
from app.integrations.obsidian.constants import ALLOWED_FORKOS_TYPES, TYPE_DEFAULT_FOLDERS
from app.integrations.obsidian.frontmatter import render_markdown_with_frontmatter
from app.integrations.obsidian.index import VaultIndex
from app.integrations.obsidian.models import VaultItem, VaultStatus
from app.integrations.obsidian.security import resolve_safe_vault_path, sanitize_filename
from app.integrations.obsidian.uri import open_file_uri


class VaultConflictError(Exception):
    """Belirtilen forkOS ID'si Vault içinde birden fazla dosyada tespit edildiğinde fırlatılır."""

    def __init__(self, forkos_id: str, conflicting_paths: list[str]) -> None:
        self.forkos_id = forkos_id
        self.conflicting_paths = conflicting_paths
        super().__init__(
            f"Vault içinde '{forkos_id}' kimliğine sahip birden fazla dosya bulundu: {conflicting_paths}"
        )


vault_index = VaultIndex()


def _get_vault_context(
    vault_path_override: Path | None = None,
    vault_name_override: str | None = None,
) -> tuple[Path | None, str]:
    if vault_path_override is not None:
        v_root = vault_path_override
    else:
        v_root = settings.resolved_obsidian_vault_path

    if vault_name_override is not None:
        v_name = vault_name_override
    else:
        v_name = settings.resolved_obsidian_vault_name

    return v_root, v_name


def get_vault_status(
    vault_path_override: Path | None = None,
    vault_name_override: str | None = None,
) -> VaultStatus:
    v_root, v_name = _get_vault_context(vault_path_override, vault_name_override)
    return vault_index.current_status(v_root, v_name)


def refresh_vault_index(
    vault_path_override: Path | None = None,
    vault_name_override: str | None = None,
) -> VaultStatus:
    v_root, v_name = _get_vault_context(vault_path_override, vault_name_override)
    return vault_index.scan(v_root, v_name)


def resolve_managed_item(
    forkos_id: str | uuid.UUID,
    vault_path_override: Path | None = None,
    vault_name_override: str | None = None,
) -> VaultItem | None:
    fid = str(forkos_id)
    if not vault_index.is_scanned:
        refresh_vault_index(vault_path_override, vault_name_override)

    if vault_index.is_conflicted(fid):
        raise VaultConflictError(fid, vault_index.conflicts[fid])

    item = vault_index.get_item(fid)
    if item:
        v_root, _ = _get_vault_context(vault_path_override, vault_name_override)
        if v_root:
            try:
                real_file = resolve_safe_vault_path(v_root, item.relative_path)
                if not real_file.is_file():
                    # Dosya taşınmış veya silinmişse yeniden tara
                    refresh_vault_index(vault_path_override, vault_name_override)
                    if vault_index.is_conflicted(fid):
                        raise VaultConflictError(fid, vault_index.conflicts[fid])
                    return vault_index.get_item(fid)
            except VaultConflictError:
                raise
            except Exception:
                return None
    return item


def _default_body_for_type(forkos_type: str, title: str) -> str:
    if forkos_type == "project":
        return (
            f"# {title}\n\n"
            "## Amaç\n\n"
            "## Şu anki durum\n\n"
            "## Kararlar\n\n"
            "## Araştırma\n\n"
            "## Referanslar\n"
        )
    return f"# {title}\n"


def create_managed_note(
    forkos_id: uuid.UUID | str,
    forkos_type: str,
    title: str,
    target_folder: str | None = None,
    initial_body: str | None = None,
    vault_path_override: Path | None = None,
    vault_name_override: str | None = None,
) -> VaultItem:
    v_root, v_name = _get_vault_context(vault_path_override, vault_name_override)
    if v_root is None:
        raise RuntimeError("Obsidian Vault yapılandırılmamış (OBSIDIAN_VAULT_PATH boş)")

    resolved_root = v_root.resolve()
    if not resolved_root.is_dir():
        raise RuntimeError(f"Obsidian Vault dizini bulunamadı: '{resolved_root.name}'")

    status = get_vault_status(v_root, v_name)
    if not status.writable:
        raise PermissionError("Obsidian Vault dizinine yazma izni yok (salt-okunur)")

    clean_type = str(forkos_type).strip().lower()
    if clean_type not in ALLOWED_FORKOS_TYPES:
        raise ValueError(
            f"Desteklenmeyen forkos_type: '{forkos_type}'. İzin verilenler: {sorted(ALLOWED_FORKOS_TYPES)}"
        )

    str_id = str(forkos_id)

    # 0. Çakışma kontrolü: Bu forkos_id birden fazla dosyada mevcutsa fail-closed!
    if not vault_index.is_scanned:
        refresh_vault_index(vault_path_override, vault_name_override)
    if vault_index.is_conflicted(str_id):
        raise VaultConflictError(str_id, vault_index.conflicts[str_id])

    # 1. Zaten aynı forkos_id ile kayıtlı bir dosya var mı? (İdempotent koruma)
    existing = resolve_managed_item(str_id, v_root, v_name)
    if existing:
        return existing

    base_name = sanitize_filename(title)

    # 2. Kanonik yerleşim düzeni (Fix 4)
    # Projeler: 20 Projects/<Project Name>/<Project Name>.md
    # Diğerleri: <Default Folder>/<Title>.md
    if clean_type == "project":
        parent_folder = target_folder or TYPE_DEFAULT_FOLDERS.get("project", "20 Projects")
        parent_stripped = parent_folder.rstrip("/")
        if not (parent_stripped.endswith(f"/{base_name}") or parent_stripped == base_name):
            folder_name = f"{parent_stripped}/{base_name}"
        else:
            folder_name = parent_stripped
    else:
        folder_name = target_folder or TYPE_DEFAULT_FOLDERS.get(clean_type, "00 Inbox")

    target_dir = resolve_safe_vault_path(resolved_root, folder_name)
    target_dir.mkdir(parents=True, exist_ok=True)

    now_iso = datetime.now(UTC).isoformat()
    frontmatter = {
        "forkos_id": str_id,
        "forkos_type": clean_type,
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    body = initial_body if initial_body is not None else _default_body_for_type(clean_type, title)
    full_content = render_markdown_with_frontmatter(frontmatter, body)

    # 3. Atomik ve güvenli dosya oluşturma (Hardening 2)
    # os.O_CREAT | os.O_EXCL ile mevcut dosyaların üzerine yazılması engellenir.
    counter = 0
    target_file: Path | None = None
    while True:
        candidate_name = f"{base_name}.md" if counter == 0 else f"{base_name} ({counter}).md"
        candidate_file = target_dir / candidate_name
        try:
            fd = os.open(candidate_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            try:
                with open(fd, "w", encoding="utf-8") as f:
                    f.write(full_content)
            except Exception:
                with contextlib.suppress(OSError):
                    candidate_file.unlink(missing_ok=True)
                raise
            target_file = candidate_file
            break
        except FileExistsError:
            counter += 1

    rel_path = str(target_file.relative_to(resolved_root)).replace("\\", "/")
    stat = target_file.stat()
    item = VaultItem(
        forkos_id=str_id,
        forkos_type=clean_type,
        title=title,
        relative_path=rel_path,
        open_uri=open_file_uri(v_name, rel_path),
        mtime=stat.st_mtime,
        size=stat.st_size,
    )
    vault_index.add_or_update_item(item)
    return item
