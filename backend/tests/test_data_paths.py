"""Runtime veri yollarinin korunmasi.

Gunluk (stable) runtime'da kaynak kodu container'a KOPYALANIR; yalnizca
compose'da acikca baglanan dizinler host'ta kalir. Uygulamanin runtime'da
yazdigi bir dosya yanlis yere duserse container yeniden olusturulunca
kullanicinin verisi kaybolur. Bu yuzden iki sey kilitlenir:

  1. Yazilan yollar kalici veri dizininin (`data/`) altinda olmali.
  2. Eski konumdaki kisisel dosya, yeni konuma DEVRALINIR (silinmez).
"""

from __future__ import annotations

from pathlib import Path

from app.modules.document import service as document_service
from app.modules.media import artwork
from app.sources import forkjob_port

#: GERCEK (uretim) sabitleri modul import'unda yakalanir: conftest'in autouse
#: izolasyon fixture'i bu modul niteliklerini gecici dizine cevirir, ama
#: buradaki degerler uretim duzenini dogrular.
REAL_DOCUMENTS_DIR = document_service.DOCUMENTS_DIR
REAL_ASSETS_DIR = artwork.default_asset_dir()
REAL_CONFIG_PATH = forkjob_port.CONFIG_PATH


def test_written_paths_live_under_the_data_dir() -> None:
    """Belgeler, gorsel onbellegi ve uyum profili `data/` altinda olmali."""
    assert REAL_DOCUMENTS_DIR.parent.name == "data"
    assert REAL_DOCUMENTS_DIR.name == "documents"
    # Container'da /app/data/media, repo kopyasinda backend/data/media.
    assert REAL_ASSETS_DIR.name == "media"
    assert REAL_CONFIG_PATH.parent.name == "data"
    assert REAL_CONFIG_PATH.name == "config.yaml"


def test_test_runs_are_redirected_away_from_real_data_dirs(isolated_data_dirs: Path) -> None:
    """Testler kullanicinin gercek veri dizinlerine YAZMAMALI."""
    assert isolated_data_dirs / "documents" == document_service.DOCUMENTS_DIR
    assert artwork.default_asset_dir() == isolated_data_dirs / "media"
    assert isolated_data_dirs / "config.yaml" == forkjob_port.CONFIG_PATH
    assert REAL_DOCUMENTS_DIR != document_service.DOCUMENTS_DIR
    assert REAL_CONFIG_PATH != forkjob_port.CONFIG_PATH


def test_forkjob_core_config_inherits_legacy_file(tmp_path: Path, monkeypatch) -> None:
    """Eski `./config.yaml` yeni konuma KOPYALANIR; kisisel ayar kaybolmaz."""
    legacy = tmp_path / "legacy" / "config.yaml"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("scoring: {}\n", encoding="utf-8")
    target = tmp_path / "data" / "config.yaml"
    monkeypatch.setattr(forkjob_port, "CONFIG_PATH", target)
    monkeypatch.setattr(forkjob_port, "LEGACY_CONFIG_PATH", legacy)

    resolved = forkjob_port.forkjob_core_config_path()

    assert resolved == target
    assert target.read_text(encoding="utf-8") == "scoring: {}\n"
    assert legacy.exists(), "kullanicinin eski dosyasi SILINMEZ"

    # Ikinci cagri kopyalamayi tekrarlamaz.
    target.write_text("scoring: {calibrated: true}\n", encoding="utf-8")
    assert forkjob_port.forkjob_core_config_path() == target
    assert target.read_text(encoding="utf-8") == "scoring: {calibrated: true}\n"


def test_forkjob_core_config_does_not_touch_disk_without_legacy_file(
    tmp_path: Path, monkeypatch
) -> None:
    target = tmp_path / "data" / "config.yaml"
    monkeypatch.setattr(forkjob_port, "CONFIG_PATH", target)
    monkeypatch.setattr(forkjob_port, "LEGACY_CONFIG_PATH", tmp_path / "missing.yaml")

    assert forkjob_port.forkjob_core_config_path() == target
    assert not target.exists()
