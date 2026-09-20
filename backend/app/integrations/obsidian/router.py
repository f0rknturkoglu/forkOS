from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from app.integrations.obsidian import service
from app.integrations.obsidian.models import CreateManagedNoteIn, VaultItem, VaultStatus

router = APIRouter(prefix="/obsidian", tags=["obsidian"])


@router.get("/status", response_model=VaultStatus)
async def get_status() -> VaultStatus:
    """Obsidian Vault entegrasyonunun durumunu döner.

    Path'in tam sistem yolunu browser'a ifşa etmez.
    """
    return service.get_vault_status()


@router.post("/index/refresh", response_model=VaultStatus)
async def refresh_index() -> VaultStatus:
    """Obsidian Vault dizinini yeniden tarar ve bellek içi indeksi tazeler."""
    return service.refresh_vault_index()


@router.get("/items/{forkos_id}", response_model=VaultItem)
async def get_item(forkos_id: uuid.UUID) -> VaultItem:
    """Belirtilen forkOS ID'sine karşılık gelen Vault dosyasını ve açılış URI'sini döner."""
    item = service.resolve_managed_item(str(forkos_id))
    if not item:
        raise HTTPException(
            status_code=404,
            detail=f"Vault içinde '{forkos_id}' ID'sine sahip yönetilen bir not bulunamadı.",
        )
    return item


@router.post("/items", response_model=VaultItem, status_code=201)
async def create_item(body: CreateManagedNoteIn) -> VaultItem:
    """Vault içinde forkOS ile yönetilen yeni bir Markdown belgesi oluşturur."""
    try:
        return service.create_managed_note(
            forkos_id=body.forkos_id,
            forkos_type=body.forkos_type,
            title=body.title,
            target_folder=body.target_folder,
            initial_body=body.initial_body,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
