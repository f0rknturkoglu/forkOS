"""Kişisel veri, commit edilen kaynak dosyalarına sızmamalı (AGENTS.md, Faz 0).

LinkedIn arama profilleri ve kullanıcı RSS listesi kişisel veridir. Bu testler
runtime hedefinin git tarafından takip EDİLMEDİĞİNİ ve commit edilen şablonların
kişisel veri taşımadığını doğrular; gerçek kullanıcı dosyasına ihtiyaç duymaz.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from app.sources.forkjob_core import feeds as feeds_module
from app.sources.forkjob_core import linkedin_profiles as profiles_module
from app.sources.forkjob_core.feeds import Feeds
from app.sources.forkjob_core.linkedin_profiles import LinkedInProfiles

pytestmark = pytest.mark.no_database

REPO_ROOT = Path(__file__).resolve().parents[2]


def _tracked_paths() -> set[str]:
    """Repo köküne göre git'in takip ettiği dosyalar."""
    if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
        pytest.skip("Git metadata bu test ortamına bağlanmamış; host testi gerekir")
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return set(result.stdout.splitlines())


def _is_ignored(path: Path) -> bool:
    """`git check-ignore`: yol ignore ediliyorsa True."""
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", str(path.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


@pytest.mark.parametrize(
    "runtime_path",
    [
        profiles_module.USER_PROFILES_PATH,
        feeds_module.USER_FEEDS_PATH,
    ],
)
def test_runtime_user_file_is_never_tracked(runtime_path: Path) -> None:
    """Runtime hedefi git'te olamaz: aksi halde kişisel profil commit edilir."""
    relative = str(runtime_path.relative_to(REPO_ROOT))
    assert relative not in _tracked_paths(), f"{relative} git tarafından takip ediliyor"
    assert _is_ignored(runtime_path), f"{relative} .gitignore kapsamında değil"


@pytest.mark.parametrize(
    "template_path",
    [
        profiles_module.TEMPLATE_PROFILES_PATH,
        feeds_module.TEMPLATE_FEEDS_PATH,
    ],
)
def test_tracked_template_carries_no_personal_data(template_path: Path) -> None:
    """Commit edilen şablon boş bir örnek olmalı, kullanıcı kaydı değil."""
    raw = yaml.safe_load(template_path.read_text(encoding="utf-8")) or {}
    entries = [value for key, value in raw.items() if isinstance(value, list)]
    assert entries, f"{template_path.name} beklenen listeyi içermiyor"
    assert all(entry == [] for entry in entries), f"{template_path.name} kişisel kayıt içeriyor"


def test_linkedin_registry_has_no_personal_default_searches() -> None:
    """Kayıtlı kaynak, kullanıcının yerel aramalarına yabancı hedef eklememeli."""
    registry = profiles_module.TEMPLATE_PROFILES_PATH.with_name("portals.yaml")
    raw = yaml.safe_load(registry.read_text(encoding="utf-8")) or {}
    linkedin = next(portal for portal in raw["sources"] if portal["key"] == "linkedin")
    assert linkedin["config"]["searches"] == []


def test_save_targets_the_runtime_file_not_the_template(tmp_path: Path, monkeypatch) -> None:
    """Web UI'ın yazdığı dosya runtime hedefidir; şablon asla yazılmaz."""
    runtime_profiles = tmp_path / "linkedin-profiles.yaml.user"
    runtime_feeds = tmp_path / "feeds.yaml.user"
    monkeypatch.setattr(profiles_module, "USER_PROFILES_PATH", runtime_profiles)
    monkeypatch.setattr(feeds_module, "USER_FEEDS_PATH", runtime_feeds)

    profiles = LinkedInProfiles()
    profiles.add(profiles_module.LinkedInProfile(term="örnek arama"))
    assert runtime_profiles.exists()
    assert profiles.path == runtime_profiles

    feeds = Feeds()
    feeds.add(feeds_module.Feed(url="https://example.invalid/feed.xml"))
    assert runtime_feeds.exists()
    assert feeds.path == runtime_feeds


def test_saving_never_touches_the_tracked_data_directory(monkeypatch, tmp_path: Path) -> None:
    """Kullanıcı kaydı, takip edilen data/ dizinine yazılmamalı."""
    tracked_dir = profiles_module.TEMPLATE_PROFILES_PATH.parent
    before = {path.name: path.read_bytes() for path in tracked_dir.glob("*.yaml")}

    monkeypatch.setattr(profiles_module, "USER_PROFILES_PATH", tmp_path / "p.yaml.user")
    monkeypatch.setattr(feeds_module, "USER_FEEDS_PATH", tmp_path / "f.yaml.user")

    collection = LinkedInProfiles()
    collection.profiles = [profiles_module.LinkedInProfile(term="örnek arama")]
    collection.save()
    feeds = Feeds()
    feeds.feeds = [feeds_module.Feed(url="https://example.invalid/feed.xml")]
    feeds.save()

    after = {path.name: path.read_bytes() for path in tracked_dir.glob("*.yaml")}
    assert before == after


def test_legacy_profiles_are_adopted_once(tmp_path: Path, monkeypatch) -> None:
    """Eski sürümün takip edilen dosyaya yazdığı profiller kaybolmaz."""
    legacy = tmp_path / "linkedin-profiles.yaml"
    legacy.write_text(
        "version: 1\nprofiles:\n- term: eski arama\n  location: ankara\n",
        encoding="utf-8",
    )
    runtime = tmp_path / "linkedin-profiles.yaml.user"
    monkeypatch.setattr(profiles_module, "TEMPLATE_PROFILES_PATH", legacy)
    monkeypatch.setattr(profiles_module, "USER_PROFILES_PATH", runtime)

    collection = LinkedInProfiles.load()

    assert [profile.term for profile in collection] == ["eski arama"]
    assert runtime.exists()
    # Şablon bir kez okunur: ikinci yükleme artık runtime dosyasından gelir.
    legacy.write_text("version: 1\nprofiles:\n- term: sonradan eklenen\n", encoding="utf-8")
    assert [profile.term for profile in LinkedInProfiles.load()] == ["eski arama"]


def test_legacy_feeds_are_adopted_once(tmp_path: Path, monkeypatch) -> None:
    """Eski sürümün takip edilen dosyaya yazdığı feed'ler kaybolmaz."""
    legacy = tmp_path / "feeds.yaml"
    legacy.write_text(
        "version: 1\nfeeds:\n- url: https://example.invalid/eski.xml\n",
        encoding="utf-8",
    )
    runtime = tmp_path / "feeds.yaml.user"
    monkeypatch.setattr(feeds_module, "TEMPLATE_FEEDS_PATH", legacy)
    monkeypatch.setattr(feeds_module, "USER_FEEDS_PATH", runtime)

    collection = Feeds.load()

    assert [feed.url for feed in collection] == ["https://example.invalid/eski.xml"]
    assert runtime.exists()
    legacy.write_text("version: 1\nfeeds: []\n", encoding="utf-8")
    assert [feed.url for feed in Feeds.load()] == ["https://example.invalid/eski.xml"]


def test_missing_runtime_file_does_not_create_one(tmp_path: Path, monkeypatch) -> None:
    """Boş kurulumda gereksiz dosya üretilmez; yalnız taşıma yazar."""
    empty_template = tmp_path / "feeds.yaml"
    empty_template.write_text("version: 1\nfeeds: []\n", encoding="utf-8")
    runtime = tmp_path / "feeds.yaml.user"
    monkeypatch.setattr(feeds_module, "TEMPLATE_FEEDS_PATH", empty_template)
    monkeypatch.setattr(feeds_module, "USER_FEEDS_PATH", runtime)

    assert len(Feeds.load()) == 0
    assert not runtime.exists()
