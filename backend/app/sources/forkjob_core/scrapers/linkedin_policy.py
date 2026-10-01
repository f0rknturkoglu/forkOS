"""One fail-closed robots gate above both LinkedIn transports."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import unquote
from urllib.robotparser import RobotFileParser

from .base import USER_AGENT, ScraperPermanentError

ROOT = "https://www.linkedin.com"
ROBOTS_URL = ROOT + "/robots.txt"
SEARCH_PATH = "/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_PATH = "/jobs-guest/jobs/api/jobPosting/"
GEO_PATH = "/jobs-guest/api/typeaheadHits"
PATHS = ("/jobs", "/jobs/view/1", "/jobs-guest/", SEARCH_PATH, DETAIL_PATH + "1", GEO_PATH)


@dataclass(frozen=True)
class LinkedInPolicyState:
    allowed: bool
    checked_at: datetime
    reason: str | None
    robots_url: str = ROBOTS_URL


class LinkedInPolicyDenied(ScraperPermanentError):
    """Availability/policy denial, never a transport retry/fallback signal."""


class LinkedInPolicyGate:
    def __init__(self, ttl_seconds=300):
        self.ttl_seconds = min(300, max(1, ttl_seconds))
        self.state = None
        self._parser = None

    async def check(self, client, *, force=False):
        now = datetime.now(UTC)
        if (
            not force
            and self.state
            and now < self.state.checked_at + timedelta(seconds=self.ttl_seconds)
        ):
            return self.state
        allowed, reason, parser = False, "LinkedIn robots policy could not be verified", None
        try:
            if client is None:
                raise ValueError("HTTP client required")
            # No recursive robots lookup and no redirect/login/proxy retry.
            response = await client._read_bounded_response(
                "GET", ROBOTS_URL, follow_redirects=False, timeout=10
            )
            if (
                response.status_code != 200
                or "text/plain" not in response.headers.get("content-type", "").lower()
            ):
                raise ValueError("unexpected robots response")
            text = response.text
            lines = [line.split("#", 1)[0].strip() for line in text.splitlines()]
            if not any(line.lower().startswith("user-agent:") for line in lines) or not any(
                line.lower().startswith(("allow:", "disallow:")) for line in lines
            ):
                raise ValueError("missing robots directives")
            if not any(
                line.lower().split(":", 1)[-1].strip() in {"*", "forkjob", USER_AGENT.lower()}
                for line in lines
                if line.lower().startswith("user-agent:")
            ):
                raise ValueError("no explicit applicable crawler group")
            if "<html" in text.lower() or "<!doctype" in text.lower():
                raise ValueError("HTML instead of policy")
            parser = RobotFileParser(ROBOTS_URL)
            parser.parse(lines)
            applicable = [e for e in parser.entries if e.applies_to(USER_AGENT)]
            if not applicable and parser.default_entry:
                applicable = [parser.default_entry]
            if not applicable or not any(e.rulelines for e in applicable):
                raise ValueError("missing applicable route rules")
            if any(
                "*" in unquote(r.path) or "$" in unquote(r.path)
                for e in applicable
                for r in e.rulelines
            ):
                raise ValueError("ambiguous wildcard policy; no speculative permission")
            denied = [path for path in PATHS if not parser.can_fetch(USER_AGENT, ROOT + path)]
            allowed = not denied
            reason = (
                "LinkedIn robots.txt disallows acquisition routes: " + ", ".join(denied)
                if denied
                else None
            )
        except Exception as exc:
            # Cancellation (BaseException) must propagate. No raw body/URL secrets.
            reason = f"LinkedIn robots policy could not be verified ({type(exc).__name__})"
        self._parser = parser
        self.state = LinkedInPolicyState(allowed, now, reason)
        return self.state

    async def require(self, client, url=None):
        state = await self.check(client)
        if not state.allowed or (
            url and (not self._parser or not self._parser.can_fetch(USER_AGENT, url))
        ):
            raise LinkedInPolicyDenied(
                state.reason or "LinkedIn robots.txt disallows requested route"
            )
        return state


POLICY = LinkedInPolicyGate()
