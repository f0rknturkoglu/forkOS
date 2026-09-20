"""Vault bağlamı: kök çözümleme ve yazma kapısı.

Neden ayrı bir modül: bu iki iş (yapılandırılmış kökü çözmek ve yazmadan önce
kapıyı tutmak) Vault'a dokunan HER katmanın ihtiyacıdır — yönetilen notlar
(`service.py`) ve sıcak hafıza (`hot_memory.py`). İkinci bir zayıf kopya
üretmek yerine tek yerde tutulur.

Güvenlik sözleşmesi:
  - Tam dosya sistemi yolu hata mesajlarına yazılmaz; yalnızca dizin ADI.
  - Hata tipleri çağıranların HTTP kodlarına eşlenebilmesi için sabittir:
    yapılandırılmamış/erişilemez → RuntimeError, salt-okunur → PermissionError.
"""

from __future__ import annotations

import os
from pathlib import Path

from app.config import settings


def vault_context(
    vault_path_override: Path | None = None,
    vault_name_override: str | None = None,
) -> tuple[Path | None, str]:
    """(yapılandırılmış kök, kasa adı) çiftini döner.

    Kök `None` ise Vault yapılandırılmamıştır; çağıran bunu fail-closed
    davranışa çevirmelidir.
    """
    if vault_path_override is not None:
        v_root = vault_path_override
    else:
        v_root = settings.resolved_obsidian_vault_path

    if vault_name_override is not None:
        v_name = vault_name_override
    else:
        v_name = settings.resolved_obsidian_vault_name

    return v_root, v_name


def require_writable_vault() -> tuple[Path, str]:
    """Yazma öncesi kapı: yapılandırma + dizin + yazma izni.

    Hiçbir hata durumunda başka bir depoya (legacy Notlar, DB) düşülmez.
    """
    v_root, v_name = vault_context()
    if v_root is None:
        raise RuntimeError("Obsidian Vault yapılandırılmamış (OBSIDIAN_VAULT_PATH boş)")

    resolved_root = v_root.resolve()
    if not resolved_root.is_dir():
        raise RuntimeError(f"Obsidian Vault dizini bulunamadı: '{resolved_root.name}'")

    if not os.access(resolved_root, os.W_OK):
        raise PermissionError("Obsidian Vault dizinine yazma izni yok (salt-okunur)")

    return resolved_root, v_name
