"""Runtime storage for user-authored jobhunter data.

The `data/*.yaml` files next to this module ship with the app, so a tracked
file must never hold something the user creates through the web UI: personal
search profiles and feeds would end up committed to git.

The convention is a sibling `<name>.user` file. It is what `.gitignore`
excludes, it is what the web UI reads and writes, and it starts empty. The
tracked file keeps its old name and its old shape but is now only a template —
safe to commit, safe to overwrite on upgrade.
"""

from __future__ import annotations

from pathlib import Path

#: Suffix marking a runtime file that must stay out of git.
USER_SUFFIX = ".user"


def user_path(template: Path) -> Path:
    """Git-ignored runtime sibling of a tracked template."""
    return template.with_name(template.name + USER_SUFFIX)


def is_user_path(path: Path) -> bool:
    """Is this a runtime file (as opposed to a tracked template)?"""
    return path.name.endswith(USER_SUFFIX)
