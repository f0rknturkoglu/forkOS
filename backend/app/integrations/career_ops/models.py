"""Typed contracts and status models for career-ops integration."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CareerOpsStatusEnum(str, Enum):
    READY = "ready"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"
    VERSION_MISMATCH = "version_mismatch"
    MISCONFIGURED = "misconfigured"
    DEGRADED = "degraded"


class CapabilityStatus(str, Enum):
    SUPPORTED = "supported"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


class CareerOpsIdentity(BaseModel):
    repository: str
    version: str
    commit: str


class CareerOpsRuntimeStatus(BaseModel):
    node_version: str | None = None
    node_compatible: bool = False
    installed: bool = False
    details: str | None = None


class CareerOpsCapability(BaseModel):
    id: str
    domain: str
    name: str
    description: str
    status: CapabilityStatus = CapabilityStatus.UNAVAILABLE


class CareerOpsUpstreamOnboarding(BaseModel):
    """Informational upstream onboarding and configuration diagnostics."""

    onboarding_needed: bool = False
    missing: list[str] = Field(default_factory=list)
    unpersonalized: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    plugins: list[dict[str, Any]] = Field(default_factory=list)
    playwright_mcp: dict[str, Any] = Field(default_factory=dict)
    active_cli: str | None = None


class CareerOpsDoctorResult(BaseModel):
    status: CareerOpsStatusEnum
    expected_identity: CareerOpsIdentity
    actual_identity: CareerOpsIdentity | None = None
    runtime: CareerOpsRuntimeStatus
    upstream_onboarding: CareerOpsUpstreamOnboarding | None = None
    capabilities_declared: int = 0
    capabilities_available: int = 0
    canonical_state_owner: str = "forkOS PostgreSQL"
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
