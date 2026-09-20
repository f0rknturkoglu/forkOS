from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class VaultItem(BaseModel):
    forkos_id: str
    forkos_type: str
    title: str
    relative_path: str
    open_uri: str
    mtime: float = 0.0
    size: int = 0


class VaultStatus(BaseModel):
    configured: bool
    available: bool
    writable: bool
    readable: bool
    vault_name: str
    managed_files: int
    conflicts: int
    conflict_details: dict[str, list[str]] = Field(default_factory=dict)
    invalid_files: list[str] = Field(default_factory=list)
    diagnostic: str | None = None


class CreateManagedNoteIn(BaseModel):
    forkos_id: uuid.UUID
    forkos_type: str
    title: str
    target_folder: str | None = None
    initial_body: str | None = None
