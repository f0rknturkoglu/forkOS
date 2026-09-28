import json
from pathlib import Path
import subprocess

import pytest
from sqlalchemy import text

import app.modules  # noqa: F401 -- metadata bütün modüllerle dolsun
from app.config import settings
from app.core.test_guard import assert_safe_test_database
from app.db import Base, engine
from app.integrations.career_ops.config import (
    CAREER_OPS_PINNED_COMMIT,
    CAREER_OPS_PINNED_VERSION,
)

# pytest hiçbir koşulda kişisel `lifeos` veritabanına bağlanmamalı. Bu kontrol
# fixture'lardan önce çalışır; dolayısıyla yanlış URL tek sorgu bile atamaz.
assert_safe_test_database(settings.database_url)


def _truncate_statement() -> str:
    tables = ", ".join(f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables))
    return f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"


@pytest.fixture
def h4_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    """H4 açık ve iki yerel model yuvası yapılandırılmış (sağlayıcı betiklenir).

    Modül ad alanına import edilmesi GEREKMEZ: burada tanımlı olduğu için
    `h4_ready` parametresi her test modülünde çözülür. (Import + parametre
    kalıbı ruff'ta F811 "redefinition" üretiyordu.)
    """
    monkeypatch.setattr(settings, "h4_enabled", True)
    monkeypatch.setattr(settings, "h4_small_model", "small-model")
    monkeypatch.setattr(settings, "h4_medium_model", "medium-model")
    monkeypatch.setattr(settings, "h4_ollama_base_url", "http://127.0.0.1:11434")


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


@pytest.fixture(autouse=True)
def isolated_data_dirs(tmp_path_factory, monkeypatch: pytest.MonkeyPatch):
    """Testler KULLANICININ gercek veri dizinlerine YAZMAMALI.

    `assert_safe_test_database` veritabani icin ne yapiyorsa, dosya sistemi
    icin de bu: yerel belgeler, not ekleri, gorsel onbellegi ve yedekler
    gecici dizine yonlendirilir. Bir test kendi `monkeypatch`'i ile bunu
    ezebilir (o zaman kendi izolasyonundan sorumludur).
    """
    from app.modules.document import service as document_service
    from app.modules.media import artwork
    from app.modules.note import storage as attachment_storage
    from app.modules.system import backup
    from app.sources import forkjob_port

    root = tmp_path_factory.mktemp("appdata")
    monkeypatch.setattr(attachment_storage, "ATTACHMENTS_DIR", root / "attachments")
    monkeypatch.setattr(document_service, "DOCUMENTS_DIR", root / "documents")
    monkeypatch.setattr(backup, "BACKUP_DIR", root / "backups")
    monkeypatch.setattr(artwork, "default_asset_dir", lambda: root / "media")
    # Uyum profili: PUT /sources/forkjob-core/config bu dosyaya yazar; izole
    # edilmezse bir test kullanicinin kalibre ettigi profili EZER.
    monkeypatch.setattr(forkjob_port, "CONFIG_PATH", root / "config.yaml")
    monkeypatch.setattr(forkjob_port, "LEGACY_CONFIG_PATH", root / "legacy-config.yaml")
    return root


@pytest.fixture
def mock_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    checkout = tmp_path / "checkout"
    checkout.mkdir(parents=True, exist_ok=True)
    (checkout / "package.json").write_text(
        json.dumps({"name": "career-ops", "version": CAREER_OPS_PINNED_VERSION}),
        encoding="utf-8",
    )
    (checkout / ".git").mkdir(parents=True, exist_ok=True)
    (checkout / "scan-ats-full.mjs").write_text("// test", encoding="utf-8")
    (checkout / "doctor.mjs").write_text("// test", encoding="utf-8")
    (checkout / "path-resolver.mjs").write_text("// test", encoding="utf-8")
    (checkout / "liveness-api.mjs").write_text("// test", encoding="utf-8")
    (checkout / "liveness-browser.mjs").write_text("// test", encoding="utf-8")
    (checkout / "browser-extract.mjs").write_text("// test", encoding="utf-8")
    (checkout / "detect-reposts.mjs").write_text("// test", encoding="utf-8")
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda cmd, **kwargs: CAREER_OPS_PINNED_COMMIT if "rev-parse" in cmd else "v22.5.0",
    )
    return checkout
