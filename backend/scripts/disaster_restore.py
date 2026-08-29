"""Disaster restore CLI (Faz 16, Faz 28).

Normal `/backup/restore` merge eder ve güvenlidir. Bu komut TÜM
veritabanını değiştirir — yalnızca gerçek felaket kurtarması için.

Kullanım (compose icinde, Makefile hedefi):

    make disaster-restore FILE=backups/forkos-2026-08-29.json.gz CONFIRM=DISASTER-RESTORE

Faz 28 akisi (Makefile orkestre eder):
1. API ve worker yazmalari durdurulur.
2. Safety dump DB konteynerinde pg_dump ile alinir (API imajinda pg_dump
   YOK; `make backup` ayni deseni kullanir). CLI'ye `--safety-dump` yolu
   verilir; dosya yoksa/boşsa CLI DB'ye DOKUNMAZ.
3. CLI migration'lari `head`'e ceker (alembic upgrade head).
4. Tek transaction icinde: temizle -> yukle -> dogrula -> commit.
   Hata varsa rollback + safety dump yolu raporlanir.
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.system import restore
from app.modules.system.disaster import disaster_restore

CONFIRM_VALUE = "DISASTER-RESTORE"
#: scripts/ dizini; alembic.ini bir ust dizinde (backend/).
BACKEND_DIR = Path(__file__).resolve().parent.parent


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="JSON/gzip yedek dosyasi (mutlak yol)")
    parser.add_argument(
        "--confirm",
        required=True,
        help=f"Onay degeri; tam olarak '{CONFIRM_VALUE}' olmali",
    )
    parser.add_argument(
        "--safety-dump", required=True,
        help="Safety dump yolu (Makefile db konteynerinde pg_dump ile alir)",
    )
    args = parser.parse_args(argv)

    candidate = Path(args.file)
    if any(ch in args.file for ch in "*?["):
        raise SystemExit("HATA: --file somut bir dosya yolu olmali; glob/desen yasak.")
    if not candidate.is_file():
        raise SystemExit(f"HATA: dosya bulunamadi: {candidate}")
    if args.confirm != CONFIRM_VALUE:
        raise SystemExit(
            f"HATA: onay gerekli. --confirm '{CONFIRM_VALUE}' yazmadan islem baslamaz."
        )
    safety = Path(args.safety_dump)
    if not safety.is_file() or safety.stat().st_size == 0:
        raise SystemExit(
            f"HATA: safety dump yok/boş: {safety} -- truncate/import BASLAMAZ."
        )
    return args


def _alembic_upgrade_head(database_url: str) -> None:
    """Migration'lari head'e ceker. Basarisizsa akis durur (Faz 28)."""
    env = {**__import__("os").environ, "DATABASE_URL": database_url}
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"migration basarisiz: {result.stdout[-400:]}{result.stderr[-400:]}")


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    from app.config import settings

    safety = Path(args.safety_dump)
    print(f"[1/5] Safety dump dogrulandi: {safety} ({safety.stat().st_size} bytes)")

    print("[2/5] Migration'lar head'e cekiliyor (alembic upgrade head)")
    try:
        _alembic_upgrade_head(settings.database_url)
    except RuntimeError as exc:
        print(f"HATA: {exc}")
        print(f"      safety dump: {safety}")
        return 1
    print("      ok")

    content = Path(args.file).read_bytes()
    payload = restore.parse_backup(content)
    inspection = restore.inspect_payload(payload)
    if inspection["unknown_tables"]:
        print(f"HATA: bilinmeyen tablolar: {inspection['unknown_tables']}")
        print(f"      safety dump: {safety}")
        return 1
    if inspection["integrity_ok"] is False:
        print("HATA: yedek butunlugu bozuk (manifest satir sayilari uymuyor).")
        print(f"      safety dump: {safety}")
        return 1

    # CLI app-disidir: paylasilan engine yerine kendi engine'ini kullanir
    # (pytest/uygulama loop'larindan bagimsiz -- Faz 28).
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _swap() -> dict:
        async with session_factory() as session:
            return await disaster_restore(session, payload)

    print("[3/5] Tek transaction: temizle + yukle + dogrula")
    try:
        result = asyncio.run(_swap())
    except Exception as exc:  # noqa: BLE001 -- CLI raporu
        print(f"HATA: restore basarisiz: {type(exc).__name__}: {exc}")
        print("      ROLLBACK yapildi -- mevcut veri yerinde.")
        print(f"      safety dump: {safety}")
        return 1
    finally:
        asyncio.run(engine.dispose())

    verification = result["verification"]
    print("[4/5] Dogrulama tamam")
    print(f"      entity={verification['row_counts'].get('entity')} "
          f"link={verification['row_counts'].get('link')} "
          f"event={verification['row_counts'].get('event')} "
          f"orphan_links={verification['orphan_links']} "
          f"orphan_parents={verification['orphan_parents']}")
    print("[5/5] Restore COMMIT edildi. API ve worker'i yeniden baslatabilirsin.")
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
