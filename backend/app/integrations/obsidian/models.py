from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class VaultItem(BaseModel):
    """Vault içinde forkOS tarafından yönetilen tek Markdown dosyası.

    Yalnızca Vault köküne GÖRELİ yol döner; tam dosya sistemi yolu asla
    browser'a çıkmaz.
    """

    forkos_id: str
    forkos_type: str
    title: str
    relative_path: str
    open_uri: str
    mtime: float = 0.0
    size: int = 0
    #: Vault indeksinin yapısal metadata'sı (tam gövde ASLA indekslenmez).
    note_kind: str | None = None
    entity_type: str | None = None
    project_id: str | None = None
    journal_day: str | None = None
    source_bookmark_id: str | None = None
    relation_count: int = 0


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
    #: Obsidian URI'leri tek yerden üretilir (kural: istemci yol/URI kurmaz).
    open_uri: str | None = None
    inbox_uri: str | None = None
    daily_uri: str | None = None


class UriOut(BaseModel):
    uri: str


class CaptureNoteIn(BaseModel):
    """Hızlı yakalama: yeni bilgi notu; client_uuid varsa tekrar güvenli kimlik."""

    body: str = Field(min_length=1)
    title: str | None = None
    #: Doluysa not bu forkOS kaydına `notes_about` ile bağlanır. Tip/başlık
    #: istemciden ALINMAZ; sunucu `entity` tablosundan çözer.
    relate_to: uuid.UUID | None = None
    tags: list[str] = Field(default_factory=list)
    client_uuid: uuid.UUID | None = None
    source_url: str | None = None
    folder: str | None = None
    pinned: bool = False


class EnsureManagedNoteIn(BaseModel):
    """Kanonik bilgi notu: kimliği verilen kalkın entity'sine bağlıdır."""

    forkos_id: uuid.UUID
