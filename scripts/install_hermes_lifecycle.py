"""Install only the forkOS-owned A1 plugin into the active Hermes home."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path

NAME = "forkos-lifecycle"
SOURCE = Path(__file__).resolve().parents[1] / "tools" / "hermes" / NAME
FILES = ("plugin.yaml", "__init__.py")
MARKER = ".forkos-managed.json"
BYTECODE = re.compile(r"__init__\.cpython-\d+\.pyc")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(home: Path) -> Path:
    target = home / "plugins" / NAME
    if target.exists() or target.is_symlink():
        if not target.is_dir() or target.is_symlink() or not (target / MARKER).is_file():
            raise RuntimeError("existing plugin is not forkOS-managed; refusing overwrite")
        marker = json.loads((target / MARKER).read_text(encoding="utf-8"))
        if marker.get("owner") != "forkOS" or marker.get("name") != NAME:
            raise RuntimeError("plugin ownership marker does not match")
        for name in FILES:
            if not (target / name).is_file() or marker.get("hashes", {}).get(name) != digest(target / name):
                raise RuntimeError("managed plugin was edited locally; refusing overwrite")
        extras = {item.name for item in target.iterdir()} - set(FILES) - {MARKER, "__pycache__"}
        if extras:
            raise RuntimeError("plugin contains unmanaged files; refusing overwrite")
        cache = target / "__pycache__"
        if cache.exists():
            if (cache.is_symlink() or not cache.is_dir() or any(
                not child.is_file() or child.is_symlink() or not BYTECODE.fullmatch(child.name)
                for child in cache.iterdir()
            )):
                raise RuntimeError("plugin cache contains unmanaged files; refusing overwrite")
            shutil.rmtree(cache)
    else:
        target.mkdir(parents=True)
    for name in FILES:
        shutil.copy2(SOURCE / name, target / name)
    (target / MARKER).write_text(json.dumps({
        "owner": "forkOS", "name": NAME,
        "hashes": {name: digest(target / name) for name in FILES},
    }, sort_keys=True) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    home = Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes").expanduser().resolve()
    print(install(home))
