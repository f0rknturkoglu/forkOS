#!/usr/bin/env python3
"""Convenience runner for plan_note_vault_migration."""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.scripts.plan_note_vault_migration import main  # noqa: E402

if __name__ == "__main__":
    main()
