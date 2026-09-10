"""Faz 15: secret ayarlar yedekten/export'tan tamamen cikar.

- Secret siniflandirmasi `app.modules.system.secrets` TEK kaynak.
- Yedek payload'inda secret key adi da degeri de bulunmaz (maskeli bile yok).
- Eski yedekteki secret satirlari restore/import tarafindan atlanir.
- Isimde "key" gecmesine guvenilmez; kod taramasi acik listeyi korur.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy import text

from app.db import Base, SessionLocal
from app.modules.system import export, restore
from app.modules.system.models import Setting
from app.modules.system.secrets import SECRET_SETTING_KEYS, is_secret_setting

APP_DIR = Path(__file__).resolve().parents[1] / "app"

#: Isimden bagimsiz koruma: kodda gorunen secret-benzeri ayar anahtarlari
#: siniflandirmaya yazilmadan yedegin yolunu bulamaz.
SECRET_WORD = re.compile(r"(key|secret|token|password|client_id)$")


def _secret_setting_rows() -> list[dict]:
    return [
        {"key": "media.tmdb_key", "value": "tmdb-value"},
        {"key": "media.google_books_key", "value": "gbooks-value"},
        {"key": "media.igdb_client_id", "value": "igdb-id"},
        {"key": "media.igdb_client_secret", "value": "igdb-secret"},
        {"key": "media.rawg_key", "value": "rawg-value"},
    ]


async def test_backup_payload_contains_no_secret_settings() -> None:
    async with SessionLocal() as session:
        for row in _secret_setting_rows():
            session.add(Setting(key=row["key"], value=row["value"]))
        session.add(Setting(key="theme.mode", value="dark"))
        await session.commit()

        payload = await export.full_json(session)

        setting_rows = payload["modules"]["setting"]
        keys = {row["key"] for row in setting_rows}
        assert not keys & set(SECRET_SETTING_KEYS)
        assert "theme.mode" in keys
        # Degerler de hicbir yerde gormesin -- key adi bile yeterli kanit.
        blob = str(payload)
        for row in _secret_setting_rows():
            assert row["key"] not in blob
            assert row["value"] not in blob
        # OAuth token tablosu kapsam disi kalmaya devam eder.
        assert "oauth_token" not in payload["modules"]


async def test_nonsecret_settings_round_trip_through_restore() -> None:
    async with SessionLocal() as session:
        session.add(Setting(key="theme.mode", value="dark"))
        await session.commit()
        payload = await export.full_json(session)

        names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
        await session.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))
        await session.commit()

        summary = await restore.restore(session, payload)

        assert summary["setting"]["inserted"] == 1
        value = (
            await session.execute(text("select value from setting where key='theme.mode'"))
        ).scalar_one()
        assert value == "dark"


async def test_old_backup_secret_rows_are_not_imported() -> None:
    """Eski (güvenli olmayan) yedekte secret satiri varsa restore atlar."""
    payload = {
        "version": 1,
        "entities": [],
        "links": [],
        "events": [],
        "modules": {
            "setting": [
                {"key": "theme.mode", "value": "light"},
                *_secret_setting_rows(),
            ]
        },
    }
    async with SessionLocal() as session:
        summary = await restore.restore(session, payload)

        assert summary["setting"]["inserted"] == 1
        assert summary["setting"]["secret_skipped"] == len(_secret_setting_rows())
        stored = (
            await session.execute(text("select key from setting"))
        ).scalars().all()
        assert stored == ["theme.mode"]


@pytest.mark.no_database
def test_secret_words_in_code_require_classification() -> None:
    """Kodda secret-benzeri dotted ayar anahtari varsa siniflandirmada olmali."""
    uncovered: list[str] = []
    for path in sorted(APP_DIR.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        for literal in re.findall(r"[\"']([a-z0-9_]+(?:\.[a-z0-9_]+)+)[\"']", source):
            if SECRET_WORD.search(literal) and not is_secret_setting(literal):
                uncovered.append(f"{path.relative_to(APP_DIR)}: {literal}")
    assert not uncovered, (
        "Secret-benzeri ayar anahtarlari SECRET_SETTING_KEYS'e yazilmadan yedekten "
        "dislanamaz. Ekleyenler:\n" + "\n".join(uncovered)
    )
