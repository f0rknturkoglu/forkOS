from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

from app.integrations.career_ops.errors import CareerOpsSecurityError
from app.sources.forkjob_port import jobhunter_config_path


class CareerOpsDiscoveryConfigBuilder:
    """Projects forkOS canonical targeting preferences into disposable career-ops runtime config.

    Under Section 16-18, forkOS owns user preferences. This class converts forkOS
    config.yaml settings into an ephemeral portals.yml inside the career-ops
    runtime directory so the upstream scanner respects forkOS filters without
    becoming a second preference authority.
    """

    @classmethod
    def build_portals_yaml(cls, config_path: Path | None = None) -> str:
        resolved_path = config_path or jobhunter_config_path()
        raw_data: dict[str, Any] = {}
        if resolved_path.exists():
            try:
                raw_data = yaml.safe_load(resolved_path.read_text(encoding="utf-8")) or {}
            except Exception:
                raw_data = {}

        if not raw_data and config_path is None:
            # Fallback to repo backend/data/config.yaml if isolated test or empty default
            default_data_config = Path(__file__).resolve().parents[3] / "data" / "config.yaml"
            if default_data_config.exists():
                try:
                    raw_data = yaml.safe_load(default_data_config.read_text(encoding="utf-8")) or {}
                except Exception:
                    raw_data = {}

        scoring = raw_data.get("scoring") or {}

        # 1. Build positive title filter from role_terms + skills
        positive_keywords: list[str] = []
        for term in scoring.get("role_terms") or []:
            t = str(term).strip().lower()
            if t and t not in positive_keywords:
                positive_keywords.append(t)

        for skill in scoring.get("skills") or []:
            if isinstance(skill, dict):
                name = str(skill.get("name", "")).strip().lower()
                if name and name not in positive_keywords:
                    positive_keywords.append(name)
                for alias in skill.get("aliases") or []:
                    a = str(alias).strip().lower()
                    if a and a not in positive_keywords:
                        positive_keywords.append(a)
            elif isinstance(skill, str):
                s = skill.strip().lower()
                if s and s not in positive_keywords:
                    positive_keywords.append(s)

        # Section 18: Preserve broad discovery without drowning in garbage
        if not positive_keywords:
            if config_path is None:
                positive_keywords = ["software", "engineer", "developer", "backend"]
            else:
                raise CareerOpsSecurityError(
                    "Positive title keywords must not be empty (preventing uncapped directory sweep)"
                )

        # 2. Build negative title filter from kill_words and executive seniority
        negative_keywords: list[str] = []
        for kw in scoring.get("kill_words") or []:
            w = str(kw).strip().lower()
            if w and w not in negative_keywords:
                negative_keywords.append(w)

        for tier in scoring.get("seniority_tiers") or []:
            if isinstance(tier, dict) and tier.get("label") in {"executive", "principal"}:
                for word in tier.get("words") or []:
                    w = str(word).strip().lower()
                    if w and w not in negative_keywords:
                        negative_keywords.append(w)

        # 3. Build location filter
        location_pos: list[str] = ["remote"]
        for city in scoring.get("tr_office_cities") or []:
            c = str(city).strip().lower()
            if c and c not in location_pos:
                location_pos.append(c)

        for regional in ["turkey", "türkiye", "emea", "europe"]:
            if regional not in location_pos:
                location_pos.append(regional)

        projected = {
            "title_filter": {
                "positive": positive_keywords,
                "negative": negative_keywords,
            },
            "location_filter": {
                "positive": location_pos,
                "negative": ["us citizenship", "security clearance", "top secret"],
            },
        }

        return yaml.dump(projected, sort_keys=False, allow_unicode=True)

    @classmethod
    def project_to_runtime(
        cls,
        runtime_dir: Path,
        config_path: Path | None = None,
    ) -> Path:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        target = runtime_dir / "portals.yml"
        content = cls.build_portals_yaml(config_path=config_path)
        target.write_text(content, encoding="utf-8")
        return target
