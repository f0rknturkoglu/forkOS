"""Killable JobSpy child process; request and result are local JSON pipes."""

from __future__ import annotations

import contextlib
import json
import sys

from .linkedin import _import_jobspy_runner


def main() -> int:
    try:
        kwargs = json.load(sys.stdin)
        if not isinstance(kwargs, dict):
            return 2
        runner = _import_jobspy_runner()
        with contextlib.redirect_stdout(sys.stderr):
            frame = runner(**kwargs)
        sys.stdout.write(frame.to_json(orient="records", date_format="iso"))
        return 0
    except Exception:
        # JobSpy/proxy exceptions can contain credentials; never echo them.
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
