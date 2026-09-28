"""Acquisition-only configuration for the pinned reverse-ATS scanner.

The scanner requires a portals.yml, but candidate preferences are ranking
inputs, not permission to discard listings before ingestion.
"""

from __future__ import annotations

from pathlib import Path

import yaml


class CareerOpsDiscoveryConfigBuilder:
    @classmethod
    def build_portals_yaml(cls, config_path: Path | None = None) -> str:
        """Allow every safe listing; operational bounds come from scan flags.

        ``config_path`` remains accepted for existing callers, but is never
        read: the candidate's skills, roles, locations and kill words must not
        affect acquisition. The pinned scanner treats an empty positive list
        as no title constraint and an empty location filter as unrestricted.
        """
        projected = {
            "title_filter": {"positive": [], "negative": []},
            "location_filter": {"strict": False},
        }
        return yaml.safe_dump(projected, sort_keys=False, allow_unicode=True)

    @classmethod
    def project_to_runtime(
        cls,
        runtime_dir: Path,
        config_path: Path | None = None,
    ) -> Path:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        target = runtime_dir / "portals.yml"
        target.write_text(cls.build_portals_yaml(config_path=config_path), encoding="utf-8")
        return target
