from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

from app.integrations.obsidian.constants import ALLOWED_FORKOS_TYPES
from app.integrations.obsidian.frontmatter import extract_title, parse_frontmatter
from app.integrations.obsidian.models import VaultItem, VaultStatus
from app.integrations.obsidian.uri import open_file_uri


class VaultIndex:
    """Obsidian Vault için hafif, bellek içi managed dosya indeksi.

    - Sadece forkos_id ve forkos_type içeren managed Markdown dosyalarını takip eder.
    - Normal Obsidian dosyalarını güvenle yok sayar.
    - Bozuk YAML içeren dosyalar scan akışını bozmaz.
    - Duplicate forkos_id tespit edildiğinde rastgele birini seçmez, conflict olarak raporlar.
    """

    def __init__(self) -> None:
        self._items: dict[str, VaultItem] = {}
        self._conflicts: dict[str, list[str]] = {}
        self._invalid_files: list[str] = []
        self._last_scanned: float | None = None
        self._last_status: VaultStatus | None = None
        self._last_root: Path | None = None

    @property
    def is_scanned(self) -> bool:
        return self._last_scanned is not None

    @property
    def items(self) -> dict[str, VaultItem]:
        return dict(self._items)

    @property
    def conflicts(self) -> dict[str, list[str]]:
        return dict(self._conflicts)

    @property
    def invalid_files(self) -> list[str]:
        return list(self._invalid_files)

    def get_managed_count(self) -> int:
        return len(self._items)

    def get_conflict_count(self) -> int:
        return len(self._conflicts)

    def is_conflicted(self, forkos_id: str) -> bool:
        return str(forkos_id) in self._conflicts

    def get_conflict(self, forkos_id: str) -> list[str] | None:
        return self._conflicts.get(str(forkos_id))

    def get_item(self, forkos_id: str) -> VaultItem | None:
        return self._items.get(str(forkos_id))

    def get_items_by_type(self, forkos_type: str) -> list[VaultItem]:
        target_type = forkos_type.lower()
        return [item for item in self._items.values() if item.forkos_type.lower() == target_type]

    def add_or_update_item(self, item: VaultItem) -> None:
        if item.forkos_id in self._conflicts:
            raise ValueError(
                f"Cannot register '{item.forkos_id}' because it has unresolved duplicate conflicts in the vault: {self._conflicts[item.forkos_id]}"
            )
        self._items[item.forkos_id] = item

    def scan(self, vault_root: Path | None, vault_name: str = "Vault") -> VaultStatus:
        """Vault dizinini tarar, managed dosyaları ve çatışmaları belirler."""
        if vault_root is None:
            self._items.clear()
            self._conflicts.clear()
            self._invalid_files.clear()
            self._last_root = None
            status = VaultStatus(
                configured=False,
                available=False,
                writable=False,
                readable=False,
                vault_name=vault_name or "Vault",
                managed_files=0,
                conflicts=0,
                conflict_details={},
                invalid_files=[],
                diagnostic="OBSIDIAN_VAULT_PATH yapılandırılmamış",
            )
            self._last_status = status
            self._last_scanned = time.time()
            return status

        resolved_root = vault_root.resolve()
        self._last_root = resolved_root
        if not resolved_root.exists():
            self._items.clear()
            self._conflicts.clear()
            self._invalid_files.clear()
            status = VaultStatus(
                configured=True,
                available=False,
                writable=False,
                readable=False,
                vault_name=vault_name or resolved_root.name,
                managed_files=0,
                conflicts=0,
                conflict_details={},
                invalid_files=[],
                diagnostic=f"Vault dizini mevcut değil: '{resolved_root.name}'",
            )
            self._last_status = status
            self._last_scanned = time.time()
            return status

        if not resolved_root.is_dir():
            self._items.clear()
            self._conflicts.clear()
            self._invalid_files.clear()
            status = VaultStatus(
                configured=True,
                available=False,
                writable=False,
                readable=False,
                vault_name=vault_name or resolved_root.name,
                managed_files=0,
                conflicts=0,
                conflict_details={},
                invalid_files=[],
                diagnostic=f"Belirtilen yol bir dizin değil: '{resolved_root.name}'",
            )
            self._last_status = status
            self._last_scanned = time.time()
            return status

        readable = os.access(resolved_root, os.R_OK)
        writable = os.access(resolved_root, os.W_OK)

        new_items: dict[str, VaultItem] = {}
        new_conflicts: dict[str, list[str]] = {}
        new_invalid: list[str] = []

        if readable:
            for dirpath, dirnames, filenames in os.walk(resolved_root, followlinks=False):
                # Gizli dizinleri (.obsidian, .trash, .git vb.) ve dizin sembolik linklerini atla
                dirnames[:] = [
                    d
                    for d in dirnames
                    if not d.startswith(".") and not os.path.islink(os.path.join(dirpath, d))
                ]

                for fname in filenames:
                    if not fname.endswith(".md") or fname.startswith("."):
                        continue

                    file_path = Path(dirpath) / fname

                    # Sembolik link sinir kontrolu: dosyanin gercek yolu Vault koku icinde kalmali
                    try:
                        real_target = file_path.resolve(strict=True)
                        real_target.relative_to(resolved_root)
                    except (ValueError, OSError, RuntimeError):
                        # Vault disina tasan sembolik link, kirik link vb.
                        continue

                    if not real_target.is_file():
                        continue

                    try:
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        continue

                    frontmatter, body = parse_frontmatter(content)
                    if not frontmatter or not isinstance(frontmatter, dict):
                        continue

                    raw_id = frontmatter.get("forkos_id")
                    raw_type = frontmatter.get("forkos_type")
                    if not raw_id or not raw_type:
                        continue

                    rel_path = str(file_path.relative_to(resolved_root)).replace("\\", "/")

                    # Metaveri sozlesme dogrulamasi (Hardening 1)
                    raw_id_str = str(raw_id).strip()
                    try:
                        parsed_uuid = uuid.UUID(raw_id_str)
                        forkos_id = str(parsed_uuid)
                    except (ValueError, TypeError, AttributeError):
                        new_invalid.append(
                            f"{rel_path}: geçersiz forkos_id '{raw_id_str}' (UUID bekleniyor)"
                        )
                        continue

                    raw_type_str = str(raw_type).strip().lower()
                    if raw_type_str not in ALLOWED_FORKOS_TYPES:
                        new_invalid.append(
                            f"{rel_path}: geçersiz forkos_type '{raw_type_str}' (desteklenen: {sorted(ALLOWED_FORKOS_TYPES)})"
                        )
                        continue

                    forkos_type = raw_type_str

                    try:
                        stat = file_path.stat()
                        mtime = stat.st_mtime
                        size = stat.st_size
                    except OSError:
                        mtime = 0.0
                        size = 0

                    title = extract_title(frontmatter, body, fallback=file_path.stem)
                    uri = open_file_uri(vault_name, rel_path)

                    item = VaultItem(
                        forkos_id=forkos_id,
                        forkos_type=forkos_type,
                        title=title,
                        relative_path=rel_path,
                        open_uri=uri,
                        mtime=mtime,
                        size=size,
                    )

                    if forkos_id in new_conflicts:
                        new_conflicts[forkos_id].append(rel_path)
                    elif forkos_id in new_items:
                        existing = new_items.pop(forkos_id)
                        new_conflicts[forkos_id] = [existing.relative_path, rel_path]
                    else:
                        new_items[forkos_id] = item

        self._items = new_items
        self._conflicts = new_conflicts
        self._invalid_files = new_invalid
        self._last_scanned = time.time()

        diagnostic = None
        if not writable:
            diagnostic = "Vault dizininde yazma izni yok (salt-okunur)"
        elif new_invalid:
            diagnostic = f"{len(new_invalid)} dosyada geçersiz forkOS metaverisi tespit edildi"

        status = VaultStatus(
            configured=True,
            available=True,
            writable=writable,
            readable=readable,
            vault_name=vault_name or resolved_root.name,
            managed_files=len(self._items),
            conflicts=len(self._conflicts),
            conflict_details=self._conflicts,
            invalid_files=new_invalid,
            diagnostic=diagnostic,
        )
        self._last_status = status
        return status

    def current_status(self, vault_root: Path | None, vault_name: str = "Vault") -> VaultStatus:
        resolved_root = vault_root.resolve() if vault_root is not None else None
        if self._last_status is None or self._last_root != resolved_root:
            return self.scan(vault_root, vault_name)
        return self._last_status
