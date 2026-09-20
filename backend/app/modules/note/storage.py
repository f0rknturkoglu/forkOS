"""Not eki blob deposu: content-addressed, dosya sisteminde.

PHASE 3 NOTU: Bu depo DONDURULMUŞ arşivin bir parçasıdır. Ürün akışı artık
yeni not eki yazmaz; kalan çağıranlar yedek/geri yükleme uyumluluğu
(`system/export.py`, `system/restore.py`), PHASE 2 göç aracı ve arşiv
boyutu raporudur. Silme budama yolu (yetim blob GC) bilinçli olarak
kaldırıldı: PHASE 3 §5 gereği `data/attachments` içeriği "yetim" görünse
bile silinmez.

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
