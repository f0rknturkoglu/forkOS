import pytest
from sqlalchemy import text

import app.modules  # noqa: F401 -- metadata bütün modüllerle dolsun
from app.config import settings
from app.core.test_guard import assert_safe_test_database
from app.db import Base, engine


# pytest hiçbir koşulda kişisel `lifeos` veritabanına bağlanmamalı. Bu kontrol
# fixture'lardan önce çalışır; dolayısıyla yanlış URL tek sorgu bile atamaz.
assert_safe_test_database(settings.database_url)


def _truncate_statement() -> str:
    tables = ", ".join(f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables))
    return f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"


@pytest.fixture(autouse=True)
async def clean_database(request: pytest.FixtureRequest):
    """Her DB testi temiz şemayla başlar; hiçbir test diğerini etkileyemez.

    pytest-asyncio her teste YENI bir event loop verir. Havuzda kalan asyncpg
    baglantilari onceki loop'a bagli oldugu icin bir sonraki test onlari
    kullanamaz; probe patlar ve test "Postgres yok" saniyla sessizce atlanir.
    """
    if request.node.get_closest_marker("no_database") is None:
        async with engine.begin() as connection:
            await connection.execute(text(_truncate_statement()))
    yield
    await engine.dispose()
