"""forkOS Notes → Obsidian Vault migration paketi.

Genel akis:

    plan (kaynak + Vault durumu)  ->  preflight kapilari  ->  kopyala  ->  dogrula

Kaynak veritabani SALT OKUNUR; hedef yalnizca Vault'tur. `--dry-run` Vault'a
hicbir sey yazmaz.
"""

from __future__ import annotations

from app.integrations.obsidian.migration.engine import (
    APPLY,
    DRY_RUN,
    VERIFY,
    MigrationOutcome,
    PreflightReport,
    load_migration_inputs,
    read_vault_state,
    run_apply,
    run_dry_run,
    run_preflight,
    run_verify,
)
from app.integrations.obsidian.migration.manifest import MANIFEST_DIR

__all__ = [
    "APPLY",
    "DRY_RUN",
    "MANIFEST_DIR",
    "VERIFY",
    "MigrationOutcome",
    "PreflightReport",
    "load_migration_inputs",
    "read_vault_state",
    "run_apply",
    "run_dry_run",
    "run_preflight",
    "run_verify",
]
