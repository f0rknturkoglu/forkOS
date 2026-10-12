"""Closed server routing + purpose/model/profile-bound, CAS-protected cloud consent."""

import hashlib
import json
from datetime import UTC, datetime

import yaml
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text

from app.config import settings
from app.core.events import log_event
from app.modules.goal.studio_schemas import StudioConsentOut
from app.modules.system.models import Setting

KEY = "hermes.goal_studio.consent.v1"
PROVIDERS = {
    "custom": ("local_custom", "Yerel model"),
    "openai-codex": ("codex_oauth", "Codex OAuth"),
    "nous": ("nous_portal", "Nous Portal"),
}


def binding(config):
    model = config["model"]
    canonical = model["provider"]
    if canonical not in PROVIDERS:
        raise ValueError("Hermes sağlayıcısı izin listesinde değil")
    mode, label = PROVIDERS[canonical]
    value = {
        "provider": canonical,
        "model": model["default"],
        "base_url": settings.hermes_goal_base_url,
        "profile": "forkos-goal-studio",
        "config": config,
        "key_digest": hashlib.sha256(settings.hermes_goal_api_key.encode()).hexdigest(),
    }
    identity = hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "id": identity,
        "provider": canonical,
        "mode": mode,
        "label": label,
        "model": model["default"],
        "local": canonical == "custom",
    }


def revision(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


async def lock(db):
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext('forkos.hermes.goal.consent'))"))


async def consent(db, policy):
    row = await db.get(Setting, KEY, populate_existing=True)
    value = row.value if row else None
    enabled = False
    if isinstance(value, dict) and set(value) == {
        "version",
        "purpose",
        "policy_id",
        "allowed",
        "updated_at",
    }:
        enabled = (
            value["version"] == 1
            and value["purpose"] == "goal_studio"
            and value["policy_id"] == policy["id"]
            and value["allowed"] is True
        )
    return StudioConsentOut(revision=revision(value), policy_id=policy["id"], allowed=enabled)


async def update_consent(db, body):
    from app.modules.goal import studio_transport

    await lock(db)
    row = await db.get(Setting, KEY, populate_existing=True)
    value = row.value if row else None
    if body.revision != revision(value):
        raise HTTPException(409, "Hermes izni başka sekmede değişti; güncel durumu yeniden aç")
    policy = None
    if body.allowed:
        try:
            policy = binding(studio_transport.verified_profile())
        except (
            ValueError,
            ValidationError,
            OSError,
            TypeError,
            AttributeError,
            yaml.YAMLError,
        ) as exc:
            raise HTTPException(503, "Hermes profili doğrulanamadı; izin kaydedilmedi") from exc
        if policy["local"] or not settings.hermes_goal_api_key:
            raise HTTPException(
                422, "Bulut izni yalnız yapılandırılmış Codex OAuth / Nous profiline verilebilir"
            )
        if body.policy_id != policy["id"]:
            raise HTTPException(
                409, "Sağlayıcı veya model değişti; izni güncel profil için yeniden ver"
            )
    # Revoke works even with a broken/missing provider config; it never starts/refreshes OAuth.
    stored = {
        "version": 1,
        "purpose": "goal_studio",
        "policy_id": policy["id"] if policy else None,
        "allowed": body.allowed,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    if row is None:
        db.add(Setting(key=KEY, value=stored))
    else:
        row.value = stored
    await log_event(
        db,
        verb="settings.updated",
        payload={
            "key": KEY,
            "allowed": body.allowed,
            "provider": policy["mode"] if policy else None,
        },
    )
    await db.commit()
    return StudioConsentOut(
        revision=revision(stored), policy_id=policy["id"] if policy else None, allowed=body.allowed
    )
