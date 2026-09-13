from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.opportunity.worker import _error_message, select_due_sources

pytestmark = pytest.mark.no_database


@dataclass
class FakeSource:
    id: str
    interval_minutes: int


def test_due_sources_honor_each_adapter_interval_and_oldest_due_first():
    now = datetime(2026, 8, 23, 12, tzinfo=UTC)
    never = FakeSource("never", 360)
    overdue = FakeSource("overdue", 60)
    recent = FakeSource("recent", 30)
    latest = {
        "overdue": now - timedelta(minutes=90),
        "recent": now - timedelta(minutes=10),
    }

    assert select_due_sources([recent, overdue, never], latest, now=now) == [
        never,
        overdue,
    ]


def test_error_message_never_discards_exception_type():
    assert _error_message(RuntimeError()) == "RuntimeError"
    assert _error_message(RuntimeError("upstream failed")) == "RuntimeError: upstream failed"


# ---------------------------------------------------------------------------
# Faz 3: kritik/slow_optin politikasi
# ---------------------------------------------------------------------------


def test_scheduler_never_polls_slow_optin_sources():
    """EURES/LinkedIn gibi opt-in kaynaklar kullanici secmeden kosmaz."""
    from app.modules.opportunity.worker import general_refresh_sources

    ids = {source.id for source in general_refresh_sources()}

    assert "jobhunter:eures" not in ids
    assert "jobhunter:linkedin" not in ids
    # Kullanici secmedigi surece calismayan her kaynak disarida kalmali.
    from app.sources.base import is_opt_in

    assert not any(is_opt_in(source) for source in general_refresh_sources())


def test_critical_sources_come_first_and_official_ones_lead():
    from app.modules.opportunity.worker import critical_source_ids

    ids = critical_source_ids()

    assert ids, "kritik kaynak listesi bos olmamali"
    assert {"osym", "ylsy"} <= set(ids)
    # Resmi/canonical kaynaklar listenin basinda olmali.
    assert ids[0] in {"osym", "ylsy", "yok", "yok-msc"}


def test_class_priority_beats_due_time():
    from app.modules.opportunity.worker import select_due_sources

    now = datetime(2026, 8, 23, 12, tzinfo=UTC)

    @dataclass
    class Source:
        id: str
        interval_minutes: int
        source_class: str = "normal"

    normal_old = Source("jobhunter:somewhere", 60, "normal")
    critical_new = Source("ylsy", 60, "critical")
    latest = {
        "jobhunter:somewhere": now - timedelta(minutes=600),
        "ylsy": now - timedelta(minutes=61),
    }

    assert select_due_sources([normal_old, critical_new], latest, now=now) == [
        critical_new,
        normal_old,
    ]


def test_env_flag_never_enables_on_garbage():
    from app.sources.base import env_flag

    assert env_flag("1") is True
    assert env_flag("true") is True
    assert env_flag(" YES ") is True
    assert env_flag("0") is False
    assert env_flag("false") is False
    assert env_flag("no") is False
    assert env_flag("") is False
    # Taninmayan deger guvenli tarafa duser: bu bir guvenlik anahtari.
    assert env_flag("maybe") is False
    assert env_flag(None) is False
    assert env_flag(None, default=True) is True


def test_linkedin_direct_access_is_off_unless_explicitly_enabled(monkeypatch):
    from app.sources.forkjob_core.scrapers.linkedin import resolve_linkedin_config

    monkeypatch.delenv("FORKJOB_LINKEDIN_ALLOW_DIRECT", raising=False)
    monkeypatch.delenv("LINKEDIN_ALLOW_DIRECT", raising=False)
    assert resolve_linkedin_config().allow_direct is False

    monkeypatch.setenv("FORKJOB_LINKEDIN_ALLOW_DIRECT", "0")
    assert resolve_linkedin_config().allow_direct is False

    monkeypatch.setenv("FORKJOB_LINKEDIN_ALLOW_DIRECT", "1")
    assert resolve_linkedin_config().allow_direct is True

    # Eski ad da calisir (mevcut .env dosyalari bozulmasin).
    monkeypatch.delenv("FORKJOB_LINKEDIN_ALLOW_DIRECT", raising=False)
    monkeypatch.setenv("LINKEDIN_ALLOW_DIRECT", "true")
    assert resolve_linkedin_config().allow_direct is True


def test_linkedin_proxy_env_names_are_consistent(monkeypatch):
    from app.sources.forkjob_core.scrapers.linkedin import resolve_linkedin_config

    monkeypatch.delenv("FORKJOB_LINKEDIN_PROXIES_FILE", raising=False)
    monkeypatch.delenv("LINKEDIN_PROXIES_FILE", raising=False)
    assert resolve_linkedin_config().proxy_file_env == "FORKJOB_LINKEDIN_PROXIES_FILE"

    # compose'un eski adi da kabul edilir; aksi halde proxy dosyasi sessizce yok sayilirdi.
    monkeypatch.setenv("LINKEDIN_PROXIES_FILE", "/tmp/proxies.txt")
    assert resolve_linkedin_config().proxy_file_env == "LINKEDIN_PROXIES_FILE"

    monkeypatch.setenv("FORKJOB_LINKEDIN_PROXIES_FILE", "/tmp/proxies.txt")
    assert resolve_linkedin_config().proxy_file_env == "FORKJOB_LINKEDIN_PROXIES_FILE"


def test_refresh_scope_selects_the_right_sources():
    from app.modules.system.refresh import REFRESH_SCOPES

    assert REFRESH_SCOPES == ("critical", "standard", "full")

    from app.modules.opportunity.worker import critical_source_ids, general_refresh_sources

    critical = set(critical_source_ids())
    general = {source.id for source in general_refresh_sources()}
    # Kritik kume genel kumenin alt kumesi; opt-in kaynaklar ikisine de girmez.
    assert critical <= general
    assert "jobhunter:linkedin" not in general
