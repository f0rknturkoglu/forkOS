from __future__ import annotations

#: Birinci sürümde izin verilen managed note tipleri
ALLOWED_FORKOS_TYPES: set[str] = {
    "note",
    "project",
    "learning",
    "career",
    "source",
    "memory",
}

#: Tip bazında varsayılan hedef klasörler
TYPE_DEFAULT_FOLDERS: dict[str, str] = {
    "note": "00 Inbox",
    "project": "20 Projects",
    "learning": "40 Learning",
    "career": "50 Career",
    "source": "60 Sources",
    "memory": "90 Agent",
}
