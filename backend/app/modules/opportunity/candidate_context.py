"""CandidateCareerContext: Canonical, typed, provenance-backed candidate context (C4/C5).

Every important fact used by the Career Specialist must have provenance:
- Key, value, source_type, source_id, confidence, verified.
- No silently inferred unsupported years of experience, tools, employment, achievements or metrics.
- Deterministic revision hash for staleness detection.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any, Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.modules.document.models import Document
from app.modules.opportunity.models import CareerStory
from app.sources.forkjob_port import jobhunter_config_path, load_config


class CandidateFact(BaseModel):
    model_config = ConfigDict(extra="ignore")

    key: str
    value: Any
    source_type: Literal["config", "career_story", "document", "system_setting", "manual"]
    source_id: str | None = None
    confidence: float = 1.0
    verified: bool = True


class CandidateCareerContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    facts: list[CandidateFact] = Field(default_factory=list)
    revision: str = ""
    profile_summary: str = ""
    target_roles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    experience_years: float | None = None
    location: str = ""
    remote_preference: str = "remote_or_hybrid"
    work_authorization: list[str] = Field(default_factory=list)
    sponsorship_required: bool | None = None
    salary_min: float | None = None
    salary_currency: str | None = None
    career_stories: list[dict[str, Any]] = Field(default_factory=list)
    base_cv: dict[str, Any] | None = None

    def get_fact(self, key: str) -> CandidateFact | None:
        for f in self.facts:
            if f.key == key:
                return f
        return None

    def has_verified_skill(self, skill_name: str) -> bool:
        norm = skill_name.strip().lower()
        for f in self.facts:
            if f.key.startswith("skill:") and f.verified:
                if str(f.value).strip().lower() == norm:
                    return True
        return False


def compute_candidate_context_revision(facts: list[CandidateFact]) -> str:
    """Deterministic hash of sorted facts for evaluation/package staleness checking."""
    fact_tokens = []
    for f in sorted(facts, key=lambda x: (x.key, str(x.value))):
        val_str = json.dumps(f.value, sort_keys=True) if isinstance(f.value, (dict, list)) else str(f.value)
        fact_tokens.append(f"{f.key}:{val_str}:{f.source_type}:{f.source_id or ''}:{f.verified}")
    serialized = "|".join(fact_tokens)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


async def build_candidate_career_context(session: AsyncSession) -> CandidateCareerContext:
    """Build candidate context strictly from canonical, verified data."""
    facts: list[CandidateFact] = []

    # 1. Configured skills and targeting preferences (forkjob / data / config.yaml)
    try:
        from pathlib import Path
        cfg_path = jobhunter_config_path()
        if not cfg_path.exists():
            fallback_path = Path(__file__).resolve().parents[3] / "data" / "config.yaml"
            if fallback_path.exists():
                cfg_path = fallback_path
        cfg = load_config(cfg_path)
        scoring_cfg = getattr(cfg, "scoring", None)
        if scoring_cfg:
            # Skills
            skills_list = getattr(scoring_cfg, "skills", []) or []
            for s in skills_list:
                s_name = getattr(s, "name", str(s))
                facts.append(
                    CandidateFact(
                        key=f"skill:{s_name.lower()}",
                        value=s_name,
                        source_type="config",
                        source_id="config.yaml#scoring.skills",
                        confidence=1.0,
                        verified=True,
                    )
                )
                aliases = getattr(s, "aliases", []) or []
                for alias in aliases:
                    facts.append(
                        CandidateFact(
                            key=f"skill_alias:{s_name.lower()}:{alias.lower()}",
                            value=alias,
                            source_type="config",
                            source_id="config.yaml#scoring.skills.aliases",
                            confidence=0.9,
                            verified=True,
                        )
                    )

            # Target roles
            role_terms = getattr(scoring_cfg, "role_terms", []) or []
            for r in role_terms:
                facts.append(
                    CandidateFact(
                        key=f"target_role:{r.lower()}",
                        value=r,
                        source_type="config",
                        source_id="config.yaml#scoring.role_terms",
                        confidence=1.0,
                        verified=True,
                    )
                )
    except Exception:
        pass

    # 2. Verified CareerStories (STAR+R)
    res_stories = await session.execute(
        select(CareerStory, Entity.title)
        .join(Entity, Entity.id == CareerStory.id)
        .where(
            Entity.archived_at.is_(None),
            CareerStory.provenance.in_(("existing", "supported")),
        )
    )
    stories_data: list[dict[str, Any]] = []
    for story, title in res_stories.all():
        story_dict = {
            "id": str(story.id),
            "title": title or "",
            "situation": story.situation or "",
            "task": story.task or "",
            "action": story.action or "",
            "result": story.result or "",
            "reflection": story.reflection or "",
            "tags": list(story.tags or []),
            "provenance": story.provenance,
        }
        stories_data.append(story_dict)
        facts.append(
            CandidateFact(
                key=f"career_story:{story.id}",
                value=story_dict,
                source_type="career_story",
                source_id=str(story.id),
                confidence=1.0,
                verified=True,
            )
        )
        for tag in story.tags or []:
            facts.append(
                CandidateFact(
                    key=f"story_tag:{tag.lower()}",
                    value=tag,
                    source_type="career_story",
                    source_id=str(story.id),
                    confidence=1.0,
                    verified=True,
                )
            )

    # 3. Base CV Document (if present)
    base_cv_dict: dict[str, Any] | None = None
    res_cv = await session.execute(
        select(Document, Entity.title)
        .join(Entity, Entity.id == Document.id)
        .where(
            Entity.archived_at.is_(None),
            Document.category.in_(("cv", "resume", "ozgecmis")),
        )
        .order_by(Document.synced_at.desc())
        .limit(1)
    )
    cv_row = res_cv.first()
    if cv_row:
        cv_doc, cv_title = cv_row
        base_cv_dict = {
            "document_id": str(cv_doc.id),
            "title": cv_title or "Base CV",
            "category": cv_doc.category,
            "mime": cv_doc.mime,
        }
        facts.append(
            CandidateFact(
                key=f"base_cv:{cv_doc.id}",
                value=base_cv_dict,
                source_type="document",
                source_id=str(cv_doc.id),
                confidence=1.0,
                verified=True,
            )
        )

    # Extract high-level lists from facts
    skills = [str(f.value) for f in facts if f.key.startswith("skill:") and f.verified]
    target_roles = [str(f.value) for f in facts if f.key.startswith("target_role:") and f.verified]
    revision = compute_candidate_context_revision(facts)

    return CandidateCareerContext(
        facts=facts,
        revision=revision,
        profile_summary="Candidate profile assembled from canonical forkOS configuration and verified evidence.",
        target_roles=target_roles,
        skills=skills,
        career_stories=stories_data,
        base_cv=base_cv_dict,
    )
