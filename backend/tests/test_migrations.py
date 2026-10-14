"""Migration'lar elle yaziliyor (kural 10) -- model ile ayrisirsa burada patlar.

Postgres'e ihtiyac duymaz: migration dosyalarindaki SQL string'lerini okuyup
SQLAlchemy metadata'siyla karsilastirir.
"""

from __future__ import annotations

import ast
import pathlib
import re

import pytest

import app.core.models  # noqa: F401  -- metadata dolsun
import app.modules  # noqa: F401
from app.db import Base

pytestmark = pytest.mark.no_database

VERSIONS = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"

DDL_VERBS = ("create", "drop", "alter", "insert", "update", "delete", "comment")
# Satir basindaki bunlar kolon degil, tablo kisiti
CONSTRAINT_KEYWORDS = ("primary", "unique", "constraint", "foreign", "check", "exclude")


def _sql_literals(path: pathlib.Path) -> list[str]:
    """Dosyadaki SQL string sabitleri. Yorum ve docstring'leri disarida birakir."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = {ast.get_docstring(tree)}
    literals = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value.strip()
            if text in docstrings:
                continue
            if text.lower().startswith(DDL_VERBS):
                literals.append(text)
    return literals


def _table_columns(statement: str) -> tuple[str, set[str]] | None:
    match = re.match(r"create table (\w+) \(", statement, re.I)
    if not match:
        return None
    lines = statement.splitlines()[1:-1]
    candidates = [(len(line) - len(line.lstrip()), line.strip()) for line in lines if line.strip()]
    if not candidates:
        return match.group(1), set()
    base_indent = min(indent for indent, _ in candidates)
    columns = set()
    for indent, line in candidates:
        # Daha derin girintili satirlar bir onceki kolonun devami (ornek: search_vec)
        if indent > base_indent or line.startswith("--"):
            continue
        first = line.split()[0].lower().rstrip(",")
        if first in CONSTRAINT_KEYWORDS or not re.fullmatch(r"[a-z_][a-z0-9_]*", first):
            continue
        columns.add(first)
    return match.group(1), columns


def _tables_from_migrations() -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    for path in sorted(VERSIONS.glob("*.py")):
        for statement in _sql_literals(path):
            parsed = _table_columns(statement)
            if parsed:
                tables[parsed[0]] = parsed[1]
                continue
            altered = re.match(
                r"alter table (\w+) add column (?:if not exists )?(\w+)", statement, re.I
            )
            if altered:
                tables.setdefault(altered.group(1), set()).add(altered.group(2).lower())
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
    support_tables = {
        # A1 agent oturumları: içeriksiz, hash-kimlikli operasyonel gözlem.
        "agent_session",
        "agent_session_turn",
        # A2 agent context/continuity: ephemeral oturum bağlamı ve kaynak devamlılığı desteği.
        "agent_session_context",
        "agent_session_source",
        # A3 epizodik oturum devri: içeriksiz, türetilmiş ve ham transkript
        # kolonu bulunmayan destek kayıtları.
        "agent_session_episode",
        "agent_session_episode_turn",
        "agent_session_episode_item",
        "plan_slot",
        "habit_log",
        "opportunity_requirement",
        "notification",
        "oauth_token",
        "milestone",
        "github_activity",
        "setting",
        # Manuel scraper batch'i, source_run gibi operasyonel destek kaydidir.
        "source_sync_batch",
        # Durum gecis gecmisi -- event gibi append-only log, entity degil.
        "application_history",
        # Opportunity alt kaydi (1:N) -- plan_slot gibi tek entity'yi olcen destek tablosu.
        "interview",
        # Bir ilanin KAYNAK karsisindaki gozlemi (first/last seen, payload hash,
        # kapanma). Bagimsiz aranabilir/linklenebilir nesne degil; yalnizca tek
        # opportunity'yi olcen destek satiri (plan_slot ile ayni sinif).
        "opportunity_source_observation",
        # Bookmark okuma vurgusu (1:N) -- tek bir bookmark entity'sine bagli destek satiri.
        "bookmark_highlight",
        # Not eki metadata'si (1:N) -- tek bir notu olcen destek satiri.
        # Binary icerik `data/attachments/<sha256>` altinda; burada yalnizca
        # ad/mime/boyut/ozet var. Bagimsiz aranabilir/linklenebilir nesne degil.
        "note_attachment",
        # H6 proaktivite motoru: kural konfigurasyonu ve kosu yasam dongusu.
        # `source_run` ile ayni sinif operasyonel kayit -- aranabilir veya
        # linklenebilir nesne DEGIL. Kullaniciya donuk kayit `notification`
        # tablosudur; kosu gecmisi entity silinse de okunabilir kalmali.
        "proactivity_rule",
        "proactivity_run",
        # H7 karar/yürütme motoru: plan revizyonu, adım makbuzu, denetim izi.
        # `source_run` ile aynı sınıf operasyonel kayıt — aranabilir/linklenebilir
        # nesne DEĞİL. Kullanıcıya dönük karar yüzeyi API'dir.
        "execution_plan",
        "execution_receipt",
        "execution_decision",
        # A4 anlamsal terfi ve dayanıklı hafıza aday tablosu:
        # operasyonel inceleme durumu; kanonik bilgi f0rknbrain Vault'unda yaşar.
        "agent_semantic_candidate",
        # Kalıcı silinen ilanların tekrar içeri alınmasını önleyen tombstone tablosu.
        "opportunity_suppression",
    }
    for name, table in Base.metadata.tables.items():
        if name in core_tables or name in support_tables:
            continue
        pk_columns = list(table.primary_key.columns)
        assert len(pk_columns) == 1, f"{name}: tek kolonlu PK bekleniyor"
        targets = {fk.target_fullname for fk in pk_columns[0].foreign_keys}
        assert "entity.id" in targets, f"{name}.{pk_columns[0].name} entity.id'ye FK degil"


def test_no_statement_contains_multiple_commands():
    """asyncpg prepared statement'a BIRDEN FAZLA komut almaz.

    Alt alta yapistirilan SQL calisma aninda
    `cannot insert multiple commands into a prepared statement` ile patlar --
    yani migration hic kosmaz. Her DDL ayri bir op.execute() olmali.
    """
    for path in sorted(VERSIONS.glob("*.py")):
        for statement in _sql_literals(path):
            # Dollar-quote'lu fonksiyon govdesindeki ';' serbesttir
            body = re.sub(r"\$\$.*?\$\$", "", statement, flags=re.S)
            assert ";" not in body, (
                f"{path.name}: tek execute icinde birden fazla komut var -> {body[:60]!r}"
            )


def test_revisions_form_a_single_chain():
    revisions, downs = {}, {}
    for path in sorted(VERSIONS.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        revision = re.search(r'^revision = "([^"]+)"', text, re.MULTILINE)
        down = re.search(r'^down_revision = (?:"([^"]+)"|None)', text, re.MULTILINE)
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



def test_no_view_migrations():
    """Kural 16: son tarihler deadline_provider'dan toplanir; deadline_v gibi
    elle SQL gorunumleri YAZILMAZ. Tarihsel create view'lara (0016) eslik eden
    bir drop view OLMAK ZORUNDA; duzenli head'de view kalmaz."""
    creations: list[str] = []
    drops: list[str] = []
    for path in sorted(VERSIONS.glob("*.py")):
        body = path.read_text().lower()
        if "create view" in body:
            creations.append(path.name)
        if "drop view" in body:
            drops.append(path.name)
    # Her create'in daha sonra bir drop'u olmali (0016 -> 0025 gibi).
    for created in creations:
        assert created in drops or any(
            int(re.findall(r"\d{4}", created)[0]) < int(re.findall(r"\d{4}", drop)[0])
            for drop in drops
        ), f"{created}: create view var ama sonraki migration'da drop yok (kural 16)"
