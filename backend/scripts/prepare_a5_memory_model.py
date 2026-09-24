"""Explicit one-time model download; never run from a judgment request."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.integrations.judgment.poorjev_memory import (
    MODEL_ID,
    MODEL_MANIFEST,
    MODEL_REVISION,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    destination = args.destination.resolve()
    if destination.exists() and any(destination.iterdir()):
        parser.error("Hedef dizin boş olmalı; var olan model/veriye dokunulmaz")
    destination.mkdir(parents=True, exist_ok=True)

    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=MODEL_ID,
        revision=MODEL_REVISION,
        local_dir=destination,
        allow_patterns=["*.json", "*.safetensors", "*.model", "*.txt"],
    )
    if not (destination / "config.json").is_file() or not list(
        destination.glob("*.safetensors")
    ):
        raise RuntimeError("Model dosyaları eksik; manifest oluşturulmadı")
    (destination / MODEL_MANIFEST).write_text(
        json.dumps({"model_id": MODEL_ID, "revision": MODEL_REVISION}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Local-only model ready: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
