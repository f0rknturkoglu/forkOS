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


CAREEROPS_CATEGORY_A_BOARDS = frozenset({
    "4dayweek", "a16z-speedrun-talent", "agentic-jobs", "arbeitnow", "cryptocurrencyjobs",
    "echojobs", "generalist-world", "getonbrd", "hackernews", "himalayas", "jobicy",
    "jobspresso", "larajobs", "manfred", "nodesk", "nofluffjobs", "pythonorg",
    "remoteok", "remotive", "weworkremotely", "workingnomads", "yourator"
})

CAREEROPS_CATEGORY_C_AUTH = frozenset({"wttj"})

CAREEROPS_CATEGORY_D_TOOLS = frozenset({"local-parser", "telegram-channel"})

CAREEROPS_CATEGORY_E_BLOCKED = frozenset({"landingjobs", "justjoin"})


def classify_careerops_provider(provider_id: str) -> tuple[str, str]:
    """Classify a CareerOps provider into Category A, B, C, D, or E."""
    if provider_id in CAREEROPS_CATEGORY_A_BOARDS:
        return "A", "Genel Pano (Hedefsiz)"
    if provider_id in CAREEROPS_CATEGORY_C_AUTH:
        return "C", "Kimlik / API Anahtarı Gerekli"
    if provider_id in CAREEROPS_CATEGORY_D_TOOLS:
        return "D", "Araç / Entegrasyon"
    if provider_id in CAREEROPS_CATEGORY_E_BLOCKED:
        return "E", "Başsız HTTP Desteklenmiyor (Cloudflare)"
    return "B", "Hedefe Dayalı ATS / Şirket Portalı"
