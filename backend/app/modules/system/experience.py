"""Versioned product preferences in existing Settings; no feed or activity on read."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from sqlalchemy import func, select, text

from app.core.events import log_event
from app.core.models import Entity
from app.modules.system.models import Setting

KEY = "product.experience.v1"
Provider = Literal["hn", "gh", "hf", "reddit"]
Channel = Literal["hn", "gh", "hf", "reddit", "rss"]
Journey = Literal["general", "goal", "planning", "learning", "career"]


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FeedBundle(Closed):
    id: UUID
    title: str = Field(min_length=1, max_length=60)
    channels: list[Channel] = Field(default_factory=list, max_length=5)
    feed_ids: list[UUID] = Field(default_factory=list, max_length=50)


class FeedPreferences(Closed):
    providers: list[Provider] = Field(default_factory=list, max_length=4)
    rss_enabled: bool = False
    subreddits: list[str] = Field(default_factory=list, max_length=20)
    bundles: list[FeedBundle] = Field(default_factory=list, max_length=12)

    @field_validator("subreddits")
    @classmethod
    def communities(cls, values):
        import re

        if any(not re.fullmatch(r"[A-Za-z0-9_]{1,50}", v) for v in values):
            raise ValueError("Geçerli subreddit adı kullan")
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def distinct(self):
        if len(set(self.providers)) != len(self.providers):
            raise ValueError("Kaynaklar tekrarlanamaz")
        if len({b.id for b in self.bundles}) != len(self.bundles):
            raise ValueError("Seçki kimlikleri tekrarlanamaz")
        for bundle in self.bundles:
            if len(set(bundle.channels)) != len(bundle.channels) or len(
                set(bundle.feed_ids)
            ) != len(bundle.feed_ids):
                raise ValueError("Seçki kaynakları tekrarlanamaz")
        return self


class OnboardingState(Closed):
    version: Literal[1] = 1
    status: Literal["new", "in_progress", "completed", "dismissed"] = "new"
    phase: Literal["welcome", "journey", "sources", "tour", "checklist"] = "welcome"
    journey: Journey | None = None
    active_tour: str | None = Field(default=None, max_length=40)
    active_step: str | None = Field(default=None, max_length=60)
    visited_steps: list[str] = Field(default_factory=list, max_length=80)
    skipped_steps: list[str] = Field(default_factory=list, max_length=80)
    dismissed_hints: list[str] = Field(default_factory=list, max_length=80)
    feed_setup: Literal["pending", "chosen", "skipped"] = "pending"


class ExperienceData(Closed):
    version: Literal[1] = 1
    onboarding: OnboardingState = Field(default_factory=OnboardingState)
    feed: FeedPreferences = Field(default_factory=FeedPreferences)
    updated_at: datetime | None = None


class ExperienceOut(ExperienceData):
    revision: str
    first_run: bool
    counts: dict[str, int]
    warnings: list[str] = Field(default_factory=list)
    invalid_feed_ids: list[UUID] = Field(default_factory=list)


class ExperienceRepairIn(Closed):
    revision: str = Field(min_length=64, max_length=64)


class ExperienceUpdate(Closed):
    revision: str = Field(min_length=64, max_length=64)
    onboarding: OnboardingState | None = None
    feed: FeedPreferences | None = None


def revision(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


async def read(session):
    from app.modules.rss.models import Feed

    row = await session.get(Setting, KEY, populate_existing=True)
    warning = []
    if row:
        try:
            state = ExperienceData.model_validate(row.value)
        except ValidationError:
            state = ExperienceData(onboarding=OnboardingState(status="dismissed"))
            warning = [
                "Rehber tercihi eski veya okunamıyor; mevcut veriler korundu. Rehberden yeniden başlayabilirsin."
            ]
    else:
        # Persisted subreddit choice is affirmative; DEFAULTS is not. RSS records are subscriptions.
        legacy = await session.get(Setting, "news.subreddits")
        feed_exists = bool(await session.scalar(select(Feed.id).limit(1)))
        communities = legacy.value if legacy and isinstance(legacy.value, list) else []
        try:
            prefs = FeedPreferences(
                rss_enabled=feed_exists,
                providers=["reddit"] if communities else [],
                subreddits=communities,
            )
        except ValidationError:
            prefs = FeedPreferences(rss_enabled=feed_exists)
        state = ExperienceData(feed=prefs)
    counts = dict(
        (
            await session.execute(
                select(Entity.type, func.count())
                .where(Entity.archived_at.is_(None))
                .group_by(Entity.type)
            )
        ).all()
    )
    from app.modules.system.settings_schema import RUNTIME_SETTING_KEYS

    configured = bool(
        await session.scalar(
            select(Setting.key)
            .where(Setting.key != KEY, Setting.key.not_in(RUNTIME_SETTING_KEYS))
            .limit(1)
        )
    )
    # Neither failed HTTP nor an unreadable preference is evidence of an empty installation.
    first_run = row is None and not counts and not configured
    ids = {identity for bundle in state.feed.bundles for identity in bundle.feed_ids}
    actual = set(await session.scalars(select(Feed.id).where(Feed.id.in_(ids)))) if ids else set()
    invalid = sorted(ids - actual, key=str)
    if invalid:
        warning.append(
            f"Seçkilerde {len(invalid)} silinmiş RSS aboneliği referansı var. Üyelikleri onarabilirsin."
        )
    return ExperienceOut(
        **state.model_dump(),
        revision=revision(row.value if row else None),
        first_run=first_run,
        counts=counts,
        warnings=warning,
        invalid_feed_ids=invalid,
    )


async def lock(session):
    """Global preference lock BEFORE RSS URL/entity locks; all writers share this order."""
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext('forkos.product.experience'))")
    )


async def store(session, state, *, payload=None, commit=True):
    state.updated_at = datetime.now(UTC)
    row = await session.get(Setting, KEY, populate_existing=True)
    if row is None:
        session.add(Setting(key=KEY, value=state.model_dump(mode="json")))
    else:
        row.value = state.model_dump(mode="json")
    await log_event(session, verb="settings.updated", payload={"key": KEY, **(payload or {})})
    await session.flush()
    if commit:
        await session.commit()


async def repair_feed_memberships(
    session, *, expected_revision=None, removed_ids=None, commit=True
):
    """Explicit repair or atomic RSS deletion: remove only absent/selected memberships, never bundles."""
    await lock(session)
    current = await read(session)
    if expected_revision is not None and current.revision != expected_revision:
        raise HTTPException(
            409, "Tercihler başka bir sekmede değişti. Güncel seçimleri yeniden aç."
        )
    row = await session.get(Setting, KEY, populate_existing=True)
    if row is None:
        return current
    try:
        state = ExperienceData.model_validate(row.value)
    except ValidationError as exc:
        raise HTTPException(409, "Bu tercih sürümü okunamıyor; kayıt değiştirilmedi") from exc
    invalid = set(current.invalid_feed_ids) if removed_ids is None else set(removed_ids)
    removed = 0
    for bundle in state.feed.bundles:
        kept = [identity for identity in bundle.feed_ids if identity not in invalid]
        removed += len(bundle.feed_ids) - len(kept)
        bundle.feed_ids = kept
    if removed:
        await store(
            session,
            state,
            payload={"repair": "rss_memberships", "removed_memberships": removed},
            commit=commit,
        )
    return await read(session)


async def update(session, body, *, commit=True):
    from app.modules.rss.models import Feed

    await lock(session)
    current = await read(session)
    if body.revision != current.revision:
        raise HTTPException(
            409, "Tercihler başka bir sekmede değişti. Güncel seçimleri yeniden aç."
        )
    state = ExperienceData.model_validate(
        current.model_dump(
            exclude={"revision", "first_run", "counts", "warnings", "invalid_feed_ids"}
        )
    )
    if body.feed is not None:
        if "reddit" in body.feed.providers and not body.feed.subreddits:
            raise HTTPException(422, "Reddit için en az bir topluluk seç veya Reddit’i kapat")
        ids = {identity for bundle in body.feed.bundles for identity in bundle.feed_ids}
        if ids:
            actual = set(await session.scalars(select(Feed.id).where(Feed.id.in_(ids))))
            if actual != ids:
                raise HTTPException(422, "Seçkide artık bulunmayan bir RSS aboneliği var")
        state.feed = body.feed
    if body.onboarding is not None:
        if body.onboarding.status == "completed":
            journey_type = {
                "goal": "goal",
                "planning": "todo",
                "learning": "study_topic",
                "career": "opportunity",
            }.get(body.onboarding.journey)
            if body.onboarding.feed_setup == "pending" or not body.onboarding.visited_steps:
                raise HTTPException(
                    422, "Kaynak seçimini tamamla veya geç; en az bir çalışma alanını keşfet"
                )
            if journey_type and not current.counts.get(journey_type):
                raise HTTPException(422, "İlk gerçek kaydını oluştur veya rehberi şimdilik kapat")
        state.onboarding = body.onboarding
    await store(session, state, commit=commit)
    return await read(session)


async def enabled(session, provider):
    from app.modules.rss.models import Feed

    row = await session.get(Setting, KEY)
    if row:
        try:
            prefs = ExperienceData.model_validate(row.value).feed
            if provider == "rss":
                return prefs.rss_enabled
            return provider in prefs.providers and (provider != "reddit" or bool(prefs.subreddits))
        except ValidationError:
            return False
    if provider == "rss":
        return bool(await session.scalar(select(Feed.id).limit(1)))
    if provider == "reddit":
        legacy = await session.get(Setting, "news.subreddits")
        return bool(legacy and isinstance(legacy.value, list) and legacy.value)
    return False


async def activate_rss(session, *, commit=True):
    """Explicit reader subscription/import opts in; pending gallery add does not."""
    await lock(session)
    current = await read(session)
    if not current.feed.rss_enabled:
        await update(
            session,
            ExperienceUpdate(
                revision=current.revision,
                feed=current.feed.model_copy(update={"rss_enabled": True}),
            ),
            commit=commit,
        )
