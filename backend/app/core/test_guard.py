from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def assert_safe_test_database(database_url: str) -> None:
    """Testlerin kişisel forkOS veritabanına bağlanmasını engelle."""
    try:
        url = make_url(database_url)
    except ArgumentError as exc:
        raise RuntimeError("Geçerli bir test veritabanı URL'si gerekli") from exc

    database = (url.database or "").lower()
    if url.get_backend_name() != "postgresql" or not database.endswith("_test"):
        raise RuntimeError("PostgreSQL test veritabanı adı '_test' ile bitmeli")
