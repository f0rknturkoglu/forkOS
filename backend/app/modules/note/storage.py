"""Not eki blob deposu: content-addressed, dosya sisteminde.

Icerik `data/attachments/<sha256>` altinda durur. Dosya adi YALNIZCA ozetten
turetilir; istemciden gelen dosya adi hicbir zaman yol olarak kullanilmaz --
path traversal bu yuzden yapisal olarak imkansizdir (`blob_path` yalnizca 64
karakterlik hex kabul eder).

Ayni icerik tekrar yuklenirse ayni dosyaya yazilir: depolama dedup'li, yazma
idempotenttir. Yarim kalan bir yazimdan sonra tekrar denemek guvenlidir.

Yazim atomiktir: once gecici dosyaya yazilir, sonra yerine tasinir. Nihai ad
altinda asla yarim bir blob gorunmez.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path

#: Kalici veri dizini; container'da `/app/data/attachments`, repo kopyasinda
#: `backend/data/attachments` (bkz. compose.yaml -> kalici veri baglari).
ATTACHMENTS_DIR = Path(__file__).resolve().parents[3] / "data" / "attachments"

_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")


def is_digest(value: str) -> bool:
    return bool(_HEX64.match(value or ""))


def blob_path(digest: str) -> Path:
    """Ozetten dosya yolu. Gecersiz ozet ValueError verir (yol uretilemez)."""
    if not is_digest(digest):
        raise ValueError("gecersiz eki ozeti")
    return ATTACHMENTS_DIR / digest


def digest_of(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def store_blob(content: bytes) -> str:
    """Icerigi yaz (gerekiyorsa) ve ozetini doner. Idempotent + dedup'li."""
    digest = digest_of(content)
    target = blob_path(digest)
    if target.is_file() and target.stat().st_size == len(content):
        return digest
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=".attachment-", suffix=".tmp", dir=ATTACHMENTS_DIR
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as sink:
            sink.write(content)
            sink.flush()
            os.fsync(sink.fileno())
        os.replace(temporary, target)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise
    return digest


def read_blob(digest: str) -> bytes | None:
    try:
        path = blob_path(digest)
    except ValueError:
        return None
    try:
        return path.read_bytes()
    except OSError:
        return None


def delete_blob(digest: str) -> int:
    """Blob'u sil; kazanilan bayt sayisini doner (yoksa 0)."""
    try:
        path = blob_path(digest)
    except ValueError:
        return 0
    try:
        size = path.stat().st_size
        path.unlink()
    except OSError:
        return 0
    return size


def storage_stats() -> tuple[int, int]:
    """(dosya sayisi, toplam bayt) -- geçici dosyalar sayilmaz."""
    files = 0
    total = 0
    for _name, _mtime, size in iter_blobs():
        files += 1
        total += size
    return files, total


def iter_blobs() -> list[tuple[str, float, int]]:
    """(ad, mtime, bayt) uclusu; gecici dosyalar atlanir."""
    if not ATTACHMENTS_DIR.is_dir():
        return []
    rows: list[tuple[str, float, int]] = []
    for entry in ATTACHMENTS_DIR.iterdir():
        if not entry.is_file() or entry.name.startswith("."):
            continue
        try:
            stat = entry.stat()
        except OSError:
            continue
        rows.append((entry.name, stat.st_mtime, stat.st_size))
    return rows


async def prune_orphan_blobs(session, *, grace_seconds: int = 3600) -> int:
    """Hicbir satirin gostermedigi ek blob'larini sil (yetim temizligi).

    Kalici silme (not/entity) ile satirlar FK cascade'i sayesinde gider, ama
    DISKTEKI dosya dosya sisteminde oldugu icin silinmez. Yetimler bu yuzden
    burada, YAS ESIGIYLE temizlenir: yeni yuklenen bir blob'un satiri henuz
    commit edilmemis olabilir; esik bu yarisi imkansiz kilar.
    """
    import time

    from sqlalchemy import select

    from app.modules.note.models import NoteAttachment

    used = set((await session.execute(select(NoteAttachment.sha256).distinct())).scalars())
    cutoff = time.time() - grace_seconds
    removed = 0
    for name, mtime, _size in iter_blobs():
        if name in used or mtime >= cutoff:
            continue
        removed += 1 if delete_blob(name) else 0
    return removed
