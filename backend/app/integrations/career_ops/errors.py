"""Typed exceptions for career-ops integration."""


class CareerOpsError(Exception):
    """Base error for career-ops integration."""


class CareerOpsConfigurationError(CareerOpsError):
    """Configuration missing or invalid."""


class CareerOpsUnavailableError(CareerOpsError):
    """Runtime, Node.js binary or checkout is not reachable."""


class CareerOpsVersionMismatchError(CareerOpsError):
    """Actual version or commit differs from expected pin."""


class CareerOpsTimeoutError(CareerOpsError):
    """Operation exceeded time limit."""


class CareerOpsExecutionError(CareerOpsError):
    """Subprocess failed or exited with non-zero code."""


class CareerOpsInvalidOutputError(CareerOpsError):
    """Output was malformed, truncated, or unparseable."""


class CareerOpsSecurityError(CareerOpsError):
    """Security invariant violated (e.g. non-allowlisted script)."""
