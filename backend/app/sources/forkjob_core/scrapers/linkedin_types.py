"""Small LinkedIn-only transport contract and shared acquisition budget."""

import time
from dataclasses import dataclass, field
from typing import Protocol

from ..models import Job
from .base import ScrapeTelemetry


class LinkedInBudgetExceeded(Exception):
    pass


@dataclass
class LinkedInBudget:
    max_wall_seconds: float = 180
    max_requests: int = 40
    max_pages: int = 10
    max_details: int = 10
    started: float = field(default_factory=time.monotonic)
    requests: int = 0

    @property
    def remaining(self):
        return max(0, self.max_wall_seconds - (time.monotonic() - self.started))

    def reserve(self):
        if self.remaining <= 0 or self.requests >= self.max_requests:
            raise LinkedInBudgetExceeded("run_budget_reached")
        self.requests += 1


@dataclass
class LinkedInTransportResult:
    jobs: list[Job]
    errors: list[str]
    telemetry: ScrapeTelemetry
    transport: str
    attempted: int
    succeeded: int
    failed_profiles: list[int] = field(default_factory=list)
    fallback_profiles: list[int] = field(default_factory=list)


class LinkedInTransport(Protocol):
    async def search(self, profiles, client, budget: LinkedInBudget) -> LinkedInTransportResult: ...
