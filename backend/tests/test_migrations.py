"""Migration'lar elle yaziliyor (kural 9) -- model ile ayrisirsa burada patlar.

Postgres'e ihtiyac duymaz: migration dosyalarindaki CREATE TABLE bloklarini
okuyup SQLAlchemy metadata'siyla karsilastirir.
"""
from __future__ import annotations

import pathlib
import re

import app.core.models  # noqa: F401  -- metadata dolsun
import app.modules  # noqa: F401
from app.db import Base

VERSIONS = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"

# Satir basindaki bunlar kolon degil, tablo kisiti
CONSTRAINT_KEYWORDS = ("primary", "unique", "constraint", "foreign", "check", "exclude")


def _tables_from_migrations() -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    for path in sorted(VERSIONS.glob("*.py")):
        sql = path.read_text(encoding="utf-8")
        for match in re.finditer(r"create table (\w+) \((.*?)\n\s*\);", sql, re.S | re.I):
            name, body = match.group(1), match.group(2)
            columns = set()
            for line in body.splitlines():
                line = line.strip().strip(",")
                if not line or line.startswith("--"):
                    continue
                first = line.split()[0].lower()
                if first in CONSTRAINT_KEYWORDS:
                    continue
                columns.add(first)
            tables[name] = columns
    return tables


def test_every_model_table_exists_in_migrations():
    migrated = _tables_from_migrations()
    missing = set(Base.metadata.tables) - set(migrated)
    assert not missing, f"migration'i olmayan tablo: {sorted(missing)}"


def test_model_columns_match_migration_columns():
    migrated = _tables_from_migrations()
    problems = []
    for name, table in Base.metadata.tables.items():
        model_columns = {c.name for c in table.columns}
        drift = model_columns - migrated.get(name, set())
        if drift:
            problems.append(f"{name}: {sorted(drift)}")
    assert not problems, f"model'de olup migration'da olmayan kolon: {problems}"


def test_module_tables_reference_entity():
    """Kural 1: her modul tablosunun PK'si entity.id'ye FK olmali."""
    core_tables = {"entity", "link", "event", "tag", "entity_tag", "saved_view", "source_run"}
    for name, table in Base.metadata.tables.items():
        if name in core_tables:
            continue
        pk_columns = list(table.primary_key.columns)
        assert len(pk_columns) == 1, f"{name}: tek kolonlu PK bekleniyor"
        targets = {fk.target_fullname for fk in pk_columns[0].foreign_keys}
        assert "entity.id" in targets, f"{name}.{pk_columns[0].name} entity.id'ye FK degil"


def test_revisions_form_a_single_chain():
    revisions, downs = {}, {}
    for path in sorted(VERSIONS.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        revision = re.search(r'^revision = "([^"]+)"', text, re.M)
        down = re.search(r"^down_revision = (?:\"([^\"]+)\"|None)", text, re.M)
        assert revision and down, f"{path.name}: revision/down_revision eksik"
        revisions[revision.group(1)] = path.name
        downs[revision.group(1)] = down.group(1)

    roots = [rev for rev, parent in downs.items() if parent is None]
    assert len(roots) == 1, f"tek bir baslangic revision'i olmali: {roots}"
    # Her parent gercekten var olmali ve iki revision ayni parent'i gostermemeli
    parents = [p for p in downs.values() if p is not None]
    assert len(parents) == len(set(parents)), "dallanma var: ayni down_revision iki kez"
    for parent in parents:
        assert parent in revisions, f"bilinmeyen down_revision: {parent}"
