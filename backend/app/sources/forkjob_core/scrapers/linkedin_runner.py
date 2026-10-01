"""Killable JobSpy child process; request and result are local JSON pipes."""

from __future__ import annotations

import contextlib
import json
import logging
import sys

from .linkedin_jobspy import _import_jobspy_runner, jobspy_version


def main() -> int:
    try:
        kwargs = json.load(sys.stdin)
        if not isinstance(kwargs, dict):
            return 2
        runner = _import_jobspy_runner()

        class WarningCounter(logging.Handler):
            count = 0

            def emit(self, record):
                if record.levelno >= logging.WARNING:
                    self.count += 1

        warnings = WarningCounter()
        logging.getLogger().addHandler(warnings)
        for name, logger in logging.Logger.manager.loggerDict.items():
            if isinstance(logger, logging.Logger) and (
                "jobspy" in name.lower() or "linkedin" in name.lower()
            ):
                logger.addHandler(warnings)
        with contextlib.redirect_stdout(sys.stderr):
            frame = runner(**kwargs)
        sys.stdout.write(
            json.dumps(
                {
                    "records": json.loads(frame.to_json(orient="records", date_format="iso")),
                    "columns": list(frame.columns),
                    "warning_count": warnings.count,
                    "jobspy_version": jobspy_version(),
                }
            )
        )
        return 0
    except Exception:
        # JobSpy/proxy exceptions can contain credentials; never echo them.
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
