import pytest

from app.core.test_guard import assert_safe_test_database

pytestmark = pytest.mark.no_database


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+asyncpg://lifeos:lifeos@db:5432/lifeos",
        "postgresql+asyncpg://lifeos:lifeos@db:5432/postgres",
        "sqlite+aiosqlite:///:memory:",
        "not-a-database-url",
    ],
)
def test_rejects_non_test_databases(database_url: str) -> None:
    with pytest.raises(RuntimeError, match="test veritabanı"):
        assert_safe_test_database(database_url)


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+asyncpg://lifeos:lifeos@db-test:5432/forkos_test",
        "postgresql://tester:secret@localhost/project_integration_test",
    ],
)
def test_accepts_postgres_databases_with_test_suffix(database_url: str) -> None:
    assert_safe_test_database(database_url)
