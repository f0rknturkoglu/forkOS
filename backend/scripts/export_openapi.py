"""Export FastAPI's OpenAPI schema as a deterministic checked-in snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "openapi.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail instead of writing when the checked-in schema differs from runtime.",
    )
    args = parser.parse_args()
    payload = json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != payload:
            print("openapi.json runtime sözleşmesinden farklı; export_openapi.py çalıştırın.")
            return 1
        print(f"{OUTPUT} runtime sözleşmesiyle güncel")
        return 0
    OUTPUT.write_text(payload, encoding="utf-8")
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
