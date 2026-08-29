"""Disaster restore CLI (Faz 16).

Normal `/backup/restore` merge eder ve güvenlidir. Bu komut TÜM
veritabanını değiştirir — yalnızca gerçek felaket kurtarması için.

Kullanım (compose icinde):

    make disaster-restore FILE=backups/forkos-2026-08-29.json.gz CONFIRM=DISASTER-RESTORE

Guvenlik onlemleri:
- `--file` zorunlu ve somut bir yol olmali; glob/desen kabul edilmez.
- `--confirm DISASTER-RESTORE` yazilmadan hicbir sey yapilmaz.
- Baslamadan once mevcut DB'nin pg_dump yedegi alinir.
- Restore sonrasi tablo sayilari + FK butunlugu dogrulanir.
- Hata durumunda guvenlik yedeginin yolu raporlanir; komut sifir olmayan
  kodla cikar.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import subprocess
import sys
from pathlib import Path

from app.db import SessionLocal, engine
from app.modules.system import restore
from app.modules.system.disaster import disaster_restore

CONFIRM_VALUE = "DISASTER-RESTORE"
BACKUP_DIR = Path("/app/backups")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="JSON/gzip yedek dosyasi (mutlak yol)")
    parser.add_argument(
        "--confirm",
        required=True,
        help=f"Onay degeri; tam olarak '{CONFIRM_VALUE}' olmali",
    )
    parser.add_argument(
        "--safety-dir", default=str(BACKUP_DIR),
        help="Guvenlik yedeginin yazilacagi dizin",
    )
    args = parser.parse_args(argv)

    # Somut dosya yolu zorunlu: glob/desen yok.
    candidate = Path(args.file)
    if any(ch in args.file for ch in "*?["):
        raise SystemExit("HATA: --file somut bir dosya yolu olmali; glob/desen yasak.")
    if not candidate.is_file():
        raise SystemExit(f"HATA: dosya bulunamadi: {candidate}")
    if args.confirm != CONFIRM_VALUE:
        raise SystemExit(
            f"HATA: onay gerekli. --confirm '{CONFIRM_VALUE}' yazmadan islem baslamaz."
        )
    return args


def _safety_dump(database_url: str, safety_dir: Path) -> Path:
    """Mevcut DB'nin guvenlik yedegi. Onemli: hata durumunda geri donulecek yer."""
    safety_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    target = safety_dir / f"pre-disaster-{stamp}.dump"
    psql_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    result = subprocess.run(
        ["pg_dump", "--format=custom", "--file", str(target), psql_url],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"guvenlik yedegi alinamadi: {result.stderr[:400]}")
    return target


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    from app.config import settings

    print(f"[1/4] Guvenlik yedegi aliniyor -> {args.safety_dir}")
    safety = _safety_dump(settings.database_url, Path(args.safety_dir))
    print(f"      kaydedildi: {safety}")

    content = Path(args.file).read_bytes()
    payload = restore.parse_backup(content)
    inspection = restore.inspect_payload(payload)
    if inspection["unknown_tables"]:
        print(f"HATA: bilinmeyen tablolar: {inspection['unknown_tables']}")
        print(f"      guvenlik yedegi: {safety}")
        return 1
    if inspection["integrity_ok"] is False:
        print("HATA: yedek butunlugu bozuk (manifest satir sayilari uymuyor).")
        print(f"      guvenlik yedegi: {safety}")
        return 1

    async def _swap() -> dict:
        async with SessionLocal() as session:
            return await disaster_restore(session, payload)

    print("[2/4] Temiz schema + yedek yukleniyor")
    try:
        result = asyncio.run(_swap())
    except Exception as exc:  # noqa: BLE001 -- CLI raporu
        print(f"HATA: restore basarisiz: {type(exc).__name__}: {exc}")
        print(f"      guvenlik yedegi: {safety}")
        return 1
    finally:
        engine.dispose()

    verification = result["verification"]
    print("[3/4] Dogrulama tamam")
    print(f"      entity={verification['row_counts'].get('entity')} "
          f"link={verification['row_counts'].get('link')} "
          f"event={verification['row_counts'].get('event')} "
          f"orphan_links={verification['orphan_links']} "
          f"orphan_parents={verification['orphan_parents']}")
    print("[4/4] Restore tamamlandi. API ve worker'i yeniden baslatabilirsin.")
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
