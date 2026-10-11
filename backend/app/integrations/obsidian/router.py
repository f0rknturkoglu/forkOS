from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.integrations.obsidian import service
from app.integrations.obsidian.models import (
    CaptureNoteIn,
    EnsureManagedNoteIn,
    UriOut,
    VaultItem,
    VaultStatus,
)

router = APIRouter(prefix="/obsidian", tags=["obsidian"])


def vault_http_error(exc: Exception) -> HTTPException:
    """Vault servis istisnalarını HTTP kodlarına eşler (tek yer).

    Vault köprüsünü çağıran HER router bunu kullanır; aksi halde aynı hata
    yüzeyi modül modül farklı kodlara düşer.
    """
    if isinstance(exc, service.VaultConflictError):
        return HTTPException(
            status_code=409,
            detail={
                "error": "conflict",
                "message": (
                    f"Bu kimlik ('{exc.forkos_id}') birden fazla Obsidian dosyasında kullanılıyor. "
                    "Çakışmayı Vault içinde çöz ve indeksi yenile."
                ),
                "forkos_id": exc.forkos_id,
                "conflicting_paths": exc.conflicting_paths,
            },
        )
    if isinstance(exc, service.VaultStaleWriteError):
        return HTTPException(
            status_code=409, detail={"error": "stale", "message": str(exc)}
        )
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, RuntimeError):
        # Vault yapılandırılmamış / erişilemez: legacy Notes'a DÜŞÜLMEZ.
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=500, detail="Vault işlemi başarısız")


@router.get("/status", response_model=VaultStatus)
async def get_status() -> VaultStatus:
    """Obsidian Vault entegrasyonunun durumu ve Obsidian bağlantıları.

    Path'in tam sistem yolunu browser'a ifşa etmez.
    """
    return service.get_vault_status()


@router.post("/index/refresh", response_model=VaultStatus)
async def refresh_index() -> VaultStatus:
    """Obsidian Vault dizinini yeniden tarar ve bellek içi indeksi tazeler."""
    return service.refresh_vault_index()


@router.get("/uri/search", response_model=UriOut)
async def search_uri_for(q: str = Query(min_length=1, max_length=200)) -> UriOut:
    """Vault içi arama URI'si. Parametre kodlaması sunucuda yapılır."""
    return UriOut(uri=service.vault_search_uri(q))


@router.get("/items/{forkos_id}", response_model=VaultItem)
async def get_item(forkos_id: uuid.UUID) -> VaultItem:
    """Belirtilen forkOS ID'sine karşılık gelen Vault dosyasını ve açılış URI'sini döner."""
    try:
        status = service.get_vault_status()
        if not status.available or not status.readable:
            raise RuntimeError("Obsidian Vault erişilemiyor; ayarları kontrol et")
        item = service.resolve_managed_item(str(forkos_id))
    except (service.VaultConflictError, RuntimeError, PermissionError) as exc:
        raise vault_http_error(exc) from exc
    if not item:
        raise HTTPException(
            status_code=404,
            detail=f"Vault içinde '{forkos_id}' ID'sine sahip yönetilen bir not bulunamadı.",
        )
    return item


@router.post("/capture", response_model=VaultItem, status_code=201)
async def capture_note(
    body: CaptureNoteIn, session: AsyncSession = Depends(get_session)
) -> VaultItem:
    """Hızlı yakalanan bilgi notunu doğrudan Vault'ta (`00 Inbox/`) oluşturur.

    Kimliği client_uuid veya sunucu üretir; forkOS veritabanında not kaydı OLUŞMAZ. İlişki
    hedefi (`relate_to`) sunucuda çözülür, istemcinin verdiği tip/başlık
    kullanılmaz.
    """
    try:
        return await service.capture_knowledge_note(
            session,
            body=body.body,
            title=body.title,
            relate_to=body.relate_to,
            tags=body.tags,
            client_uuid=body.client_uuid,
            source_url=body.source_url,
            folder=body.folder,
            pinned=body.pinned,
        )
    except (
        service.VaultConflictError,
        service.VaultStaleWriteError,
        service.VaultWriteError,
        PermissionError,
        ValueError,
        RuntimeError,
    ) as exc:
        raise vault_http_error(exc) from exc


@router.post("/ensure", response_model=VaultItem)
async def ensure_item(
    body: EnsureManagedNoteIn, session: AsyncSession = Depends(get_session)
) -> VaultItem:
    """Kanonik bilgi notunu (varsa) çözer, yoksa oluşturur.

    Başlık ve tip istemciden alınmaz; `entity` tablosundan çözülür. Aynı
    kimlikle ikinci çağrı yeni dosya üretmez.
    """
    try:
        return await service.ensure_entity_knowledge_note(session, body.forkos_id)
    except (
        service.VaultConflictError,
        service.VaultStaleWriteError,
        service.VaultWriteError,
        PermissionError,
        ValueError,
        RuntimeError,
    ) as exc:
        raise vault_http_error(exc) from exc
