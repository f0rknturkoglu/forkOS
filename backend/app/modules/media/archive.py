"""Read-only location of preserved media assets; no acquisition or cleanup."""
import os
from pathlib import Path


def default_asset_dir() -> Path:
    configured = os.getenv("MEDIA_ASSET_DIR")
    if configured:
        return Path(configured)
    if Path("/app").is_dir():
        return Path("/app/data/media")
    return Path(__file__).resolve().parents[3] / "data" / "media"
