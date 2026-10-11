import pytest

from app.integrations.career_ops.errors import (
    CareerOpsConfigurationError,
    CareerOpsError,
    CareerOpsSecurityError,
    CareerOpsTimeoutError,
    CareerOpsUnavailableError,
    CareerOpsVersionMismatchError,
)
from app.integrations.career_ops.models import (
    CareerOpsDoctorResult,
    CareerOpsIdentity,
    CareerOpsRuntimeStatus,
    CareerOpsStatusEnum,
)


@pytest.mark.no_database
def test_models_and_errors():
    identity = CareerOpsIdentity(
        repository="career-ops-hq/career-ops",
        version="1.34.0",
        commit="6326eb5d3804e8cb20d28acd5701a4e603a301f9",
    )
    assert identity.version == "1.34.0"

    runtime = CareerOpsRuntimeStatus(
        node_version="26.9.0",
        node_compatible=True,
        installed=True,
    )
    assert runtime.node_compatible is True

    doc = CareerOpsDoctorResult(
        status=CareerOpsStatusEnum.READY,
        expected_identity=identity,
        actual_identity=identity,
        runtime=runtime,
        capabilities_declared=23,
        capabilities_available=0,
        canonical_state_owner="forkOS PostgreSQL",
    )
    assert doc.status == CareerOpsStatusEnum.READY

    assert issubclass(CareerOpsVersionMismatchError, CareerOpsError)
    assert issubclass(CareerOpsUnavailableError, CareerOpsError)
    assert issubclass(CareerOpsSecurityError, CareerOpsError)
    assert issubclass(CareerOpsTimeoutError, CareerOpsError)
    assert issubclass(CareerOpsConfigurationError, CareerOpsError)
