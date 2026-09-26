"""Typed contracts and status models for career-ops integration."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt


class CareerOpsStatusEnum(str, Enum):
    READY = "ready"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"
    VERSION_MISMATCH = "version_mismatch"
    MISCONFIGURED = "misconfigured"
    DEGRADED = "degraded"


class CapabilityStatus(str, Enum):
    SUPPORTED = "supported"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


class CareerOpsCapabilityContext(BaseModel):
    enabled: bool = True
    core_ready: bool = True
    discovery_enabled: bool = True
    browser_ready: bool = False



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
    browser_ready: bool = False
    canonical_state_owner: str = "forkOS PostgreSQL"
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class CareerOpsDiscoveredJob(BaseModel):
    model_config = ConfigDict(extra="ignore")
    company: str
    title: str
    url: str
    location: str | None = None
    posted_at: str | None = None
    date_status: str = "unknown"
    blacklisted: bool = False
    note: str | None = None
    source: str = ""
    upstream_metadata: dict[str, Any] = Field(default_factory=dict)


class CareerOpsDiscoveryResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    provider: str
    date: str = ""
    since_days: int = 7
    companies_available: int = 0
    companies_scanned: int = 0
    cap_hit: bool = False
    stopped_by_outage: bool = False
    dataset_status: Any = "ok"
    unreachable_boards: int = 0
    retired_boards_skipped: int = 0
    postings_kept: int = 0
    is_partial: bool = False
    partial_detail: str = ""
    offers: list[CareerOpsDiscoveredJob] = Field(default_factory=list)


class CareerOpsOfferReceipt(BaseModel):
    model_config = ConfigDict(extra="allow")

    company: str
    title: str
    url: str
    location: str | None = None
    postedAt: str | None = None
    dateStatus: str | None = None
    blacklisted: StrictBool | None = None
    note: str | None = None
    source: str | None = None


class CareerOpsScanReceipt(BaseModel):
    model_config = ConfigDict(extra="allow")

    date: str | None = None
    sources: list[str] | None = None
    resumed: StrictBool | None = None
    sinceDays: StrictInt | None = None
    companiesAvailable: StrictInt | None = None
    companiesScanned: StrictInt | None = None
    capHit: StrictBool | None = None
    stoppedByOutage: StrictBool | None = None
    datasetStatus: str | dict[str, Any] | None = None
    unreachableBoards: StrictInt | None = None
    retiredBoardsSkipped: StrictInt | None = None
    cappedBoards: StrictInt | None = None
    offers: list[Any] = Field(default_factory=list)


class CareerOpsLivenessReceipt(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: str
    status: Literal["active", "expired", "uncertain"]
    code: str
    reason: str
    method: Literal["api", "browser", "bridge"]
    checked_at: str


class CareerOpsJobExtractionResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: str
    title: str = ""
    text: str = ""
    error: str | None = None
    code: str | None = None


class CareerOpsRepostAppearance(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: str
    date: str
    title: str


class CareerOpsRepostCluster(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    company: str
    role: str
    repost_count: int = Field(alias="repostCount")
    first_seen: str = Field(alias="firstSeen")
    last_seen: str = Field(alias="lastSeen")
    days_span: int = Field(alias="daysSpan")
    appearances: list[CareerOpsRepostAppearance] = Field(default_factory=list)

