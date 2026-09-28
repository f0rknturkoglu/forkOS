"""Project canonical forkOS job sources into disposable provider scan targets."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import yaml

from app.sources.forkjob_core.registry import Registry
from app.sources.forkjob_port import jobhunter_config_path

PUBLIC_BOARDS: tuple[dict[str, Any], ...] = (
    {"name": "4 Day Week", "provider": "4dayweek", "max_pages": 2, "max_results": 50},
    {"name": "Arbeitnow", "provider": "arbeitnow", "max_pages": 2, "max_results": 100},
    {"name": "Himalayas", "provider": "himalayas", "max_results": 100},
    {"name": "Jobicy", "provider": "jobicy", "max_results": 100},
    {"name": "Jobspresso", "provider": "jobspresso", "max_results": 100},
    {"name": "Landing.jobs", "provider": "landingjobs", "max_results": 100},
    {"name": "Remotive", "provider": "remotive", "max_results": 100},
    {"name": "RemoteOK", "provider": "remoteok", "max_results": 100},
    {
        "name": "The Hub",
        "provider": "thehub",
        "thehub": {"countryCode": "EU", "includeRemote": True},
        "max_pages": 2,
        "max_results": 50,
    },
    {"name": "We Work Remotely", "provider": "weworkremotely", "max_results": 100},
    {"name": "Working Nomads", "provider": "workingnomads", "max_results": 100},
)


def _company_url(ats: str, token: str) -> str | None:
    if not token or not token.replace("-", "").replace("_", "").isalnum():
        return None
    hosts = {
        "greenhouse": f"https://job-boards.greenhouse.io/{token}",
        "lever": f"https://jobs.lever.co/{token}",
        "ashby": f"https://jobs.ashbyhq.com/{token}",
        "recruitee": f"https://{token}.recruitee.com",
        "smartrecruiters": f"https://careers.smartrecruiters.com/{token}",
        "workable": f"https://apply.workable.com/{token}",
    }
    return hosts.get(ats)


def build_provider_targets(
    *,
    registry: Registry | None = None,
    config_path: Path | None = None,
    extra_path: Path | None = None,
) -> dict[str, Any]:
    """Keep source truth in forkOS registries/user config, not upstream portals.yml."""
    registry = registry or Registry.load()
    companies = []
    for company in registry.enabled():
        if not company.verified:
            continue
        url = _company_url(company.ats, company.token)
        if url:
            companies.append(
                {
                    "name": company.name,
                    "provider": company.ats,
                    "careers_url": url,
                    "max_results": 25,
                }
            )

    boards = [dict(board) for board in PUBLIC_BOARDS]
    config = config_path or jobhunter_config_path()
    if config.exists():
        raw = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
        terms = [str(term).strip() for term in (raw.get("scoring") or {}).get("role_terms") or []]
        terms = [term for term in terms if term][:3]
        if terms:
            boards.append(
                {
                    "name": "Arbeitsagentur",
                    "provider": "arbeitsagentur",
                    "arbeitsagentur": {"keywords": terms, "days": 14, "size": 50},
                    "max_results": 100,
                }
            )

    # Optional user-owned targets extend the canonical forkOS source registry.
    # They are never stored in the pinned checkout or committed by the app.
    target_file = (
        extra_path or Path(__file__).resolve().parents[3] / "data" / "career-ops-targets.yaml.user"
    )
    if target_file.exists():
        extra = yaml.safe_load(target_file.read_text(encoding="utf-8")) or {}
        for key, destination in (("tracked_companies", companies), ("job_boards", boards)):
            for target in extra.get(key) or []:
                if isinstance(target, dict) and isinstance(target.get("name"), str):
                    destination.append(target)

    return {"tracked_companies": companies, "job_boards": boards}


def project_provider_targets(runtime_dir: Path, targets: dict[str, Any], since_days: int) -> Path:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    path = runtime_dir / f"provider-portals-{uuid.uuid4().hex}.yml"
    # JSON is valid YAML and avoids a second Node YAML parser dependency.
    path.write_text(
        json.dumps({**targets, "since_days": since_days}, ensure_ascii=False), encoding="utf-8"
    )
    return path
