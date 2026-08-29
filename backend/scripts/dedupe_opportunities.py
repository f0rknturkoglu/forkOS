"""Duplicate iş ilanı kümelerini varsayılan olarak sadece raporla."""

from __future__ import annotations

import argparse
import asyncio
import json

from app.db import SessionLocal
from app.modules.opportunity.service import merge_duplicate_clusters


async def run(*, apply: bool) -> None:
    async with SessionLocal() as session:
        summary = await merge_duplicate_clusters(session, dry_run=not apply)
        print(json.dumps({"mode": "apply" if apply else "dry-run", **summary.to_dict()}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply", action="store_true", help="Güvenli duplicate kayıtları kalıcı birleştir"
    )
    args = parser.parse_args()
    asyncio.run(run(apply=args.apply))


if __name__ == "__main__":
    main()
