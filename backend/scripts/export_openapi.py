"""Export FastAPI's OpenAPI schema as a deterministic checked-in snapshot."""

from __future__ import annotations

import json
from pathlib import Path

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "openapi.json"


def main() -> None:
    payload = json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    OUTPUT.write_text(payload, encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
