import pytest

from app.db import engine


@pytest.fixture(autouse=True)
async def dispose_engine():
    """Her testten sonra baglanti havuzunu bosalt.

    pytest-asyncio her teste YENI bir event loop verir. Havuzda kalan asyncpg
    baglantilari onceki loop'a bagli oldugu icin bir sonraki test onlari
    kullanamaz; probe patlar ve test "Postgres yok" saniyla sessizce atlanir.
    """
    yield
    await engine.dispose()
