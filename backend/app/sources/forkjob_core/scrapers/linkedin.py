"""Optional proxy-routed LinkedIn collection powered by python-jobspy."""

from __future__ import annotations

import asyncio
import importlib
import math
import os
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from ..linkedin_profiles import LinkedInProfiles
from ..models import DateSource, Job, Layer, WorkMode, canonical_url
from ..normalize import html_to_text, parse_datetime, parse_location
from .base import (
    ScrapeBatch,
    ScraperBase,
    ScraperConfig,
    ScraperHttpClient,
    ScraperPermanentError,
)

_LINKEDIN_ID_RE = re.compile(r"/jobs/view/(\d+)")
_ALLOWED_PROXY_SCHEMES = frozenset({"http", "https", "socks4", "socks5"})
_LOCAL_PROXY_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


@dataclass(slots=True)
class LinkedInConfig:
    """Secret-safe connection settings for the LinkedIn source."""

    proxy_file_env: str = "FORKJOB_LINKEDIN_PROXIES_FILE"
    allow_direct: bool = False


class LinkedInScraper(ScraperBase):
    """Run configurable LinkedIn searches as one isolated Layer B source."""

    source_key = "linkedin"
    label = "LinkedIn"
    base_url = "https://www.linkedin.com/jobs"

    def __init__(
        self,
        config: ScraperConfig | None = None,
        *,
        searches: Sequence[Mapping[str, Any]] | None = None,
        proxy_file_env: str = "FORKJOB_LINKEDIN_PROXIES_FILE",
        allow_direct: bool = False,
        ca_cert_env: str = "FORKJOB_LINKEDIN_CA_CERT",
        user_agent_env: str = "FORKJOB_LINKEDIN_USER_AGENT",
        runner: Callable[..., Any] | None = None,
    ) -> None:
        super().__init__(config)
        self.searches = [dict(search) for search in (searches or [])]
        # Merge user-defined profiles from data/linkedin-profiles.yaml.
        self.searches = _merge_user_profiles(self.searches)
        self.linkedin_config = LinkedInConfig(
            proxy_file_env=proxy_file_env,
            allow_direct=allow_direct,
        )
        self.ca_cert_env = ca_cert_env
        self.user_agent_env = user_agent_env
        self._runner = runner

    async def scrape(self, client: ScraperHttpClient) -> ScrapeBatch:
        del client  # JobSpy owns its HTTP clients, proxy rotation, and TLS setup.
        runner = self._runner or _import_jobspy_runner()
        proxies = load_proxies(self.linkedin_config, os.environ)
        attempted = len(self.searches)
        if not attempted:
            return ScrapeBatch(
                jobs=[],
                errors=["LinkedIn has no configured search profiles"],
                attempted=0,
                succeeded=0,
            )

        jobs: list[Job] = []
        errors: list[str] = []
        succeeded = 0
        for index, profile in enumerate(self.searches, start=1):
            name = _text(profile.get("name")) or f"profile-{index}"
            try:
                kwargs = self._runner_kwargs(profile, proxies)
                frame = await asyncio.to_thread(runner, **kwargs)
                records = frame.to_dict(orient="records")
                if not isinstance(records, list):
                    raise TypeError("JobSpy result is not record-oriented")
                for row in records:
                    if isinstance(row, Mapping):
                        job = job_from_row(row)
                        if job is not None:
                            jobs.append(job)
                succeeded += 1
            except Exception as exc:
                detail = redact_proxy_secrets(f"{type(exc).__name__}: {exc}", proxies)
                errors.append(f"{name}: {detail}")

        return ScrapeBatch(
            jobs=_deduplicate(jobs),
            errors=errors,
            attempted=attempted,
            succeeded=succeeded,
        )

    def _runner_kwargs(self, profile: Mapping[str, Any], proxies: list[str]) -> dict[str, Any]:
        term = _text(profile.get("term"))
        if not term:
            raise ValueError("search term is required")
        kwargs: dict[str, Any] = {
            "site_name": "linkedin",
            "search_term": term,
            "location": _text(profile.get("location")),
            "results_wanted": int(profile.get("results_wanted") or 50),
            "proxies": proxies or None,
            "linkedin_fetch_description": bool(profile.get("fetch_description", False)),
        }
        for key in ("hours_old", "is_remote"):
            if profile.get(key) is not None:
                kwargs[key] = profile[key]
        ca_cert = (os.environ.get(self.ca_cert_env) or "").strip()
        if ca_cert:
            kwargs["ca_cert"] = ca_cert
        user_agent = (os.environ.get(self.user_agent_env) or "").strip()
        if user_agent:
            kwargs["user_agent"] = user_agent
        return kwargs


def _import_jobspy_runner() -> Callable[..., Any]:
    try:
        module = importlib.import_module("jobspy")
    except (ImportError, ModuleNotFoundError):
        raise ScraperPermanentError(
            'LinkedIn scraping requires: uv pip install -e ".[linkedin]"'
        ) from None
    runner = getattr(module, "scrape_jobs", None)
    if not callable(runner):
        raise ScraperPermanentError("jobspy.scrape_jobs is unavailable")
    return runner


def _deduplicate(jobs: Sequence[Job]) -> list[Job]:
    unique: list[Job] = []
    external_ids: set[str] = set()
    urls: set[str] = set()
    for job in jobs:
        url_key = canonical_url(job.url)
        if job.external_id and job.external_id in external_ids:
            continue
        if url_key in urls:
            continue
        unique.append(job)
        urls.add(url_key)
        if job.external_id:
            external_ids.add(job.external_id)
    return unique


def load_proxies(config: LinkedInConfig, environ: Mapping[str, str]) -> list[str]:
    """Load one proxy per line without ever echoing proxy credentials."""
    configured_path = (environ.get(config.proxy_file_env) or "").strip()
    if not configured_path:
        if config.allow_direct:
            return []
        raise ScraperPermanentError(f"LinkedIn proxy file is required; set {config.proxy_file_env}")

    path = Path(configured_path).expanduser()
    if not path.is_file():
        raise ScraperPermanentError("LinkedIn proxy file not found")

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ScraperPermanentError(
            f"LinkedIn proxy file could not be read: {type(exc).__name__}"
        ) from None

    proxies: list[str] = []
    for line_number, raw in enumerate(lines, start=1):
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        if value.lower() == "localhost":
            if not config.allow_direct:
                raise ScraperPermanentError(
                    f"LinkedIn proxy host localhost is not allowed (line {line_number})"
                )
            proxies.append(value)
            continue
        _validate_proxy(value, line_number)
        proxies.append(value)

    if not proxies and not config.allow_direct:
        raise ScraperPermanentError("LinkedIn proxy file contains no usable proxies")
    return proxies


def _validate_proxy(value: str, line_number: int) -> None:
    candidate = value if "://" in value else f"http://{value}"
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError:
        raise ScraperPermanentError(f"Invalid LinkedIn proxy on line {line_number}") from None

    if parsed.scheme.lower() not in _ALLOWED_PROXY_SCHEMES:
        raise ScraperPermanentError(f"Unsupported LinkedIn proxy scheme on line {line_number}")
    host = (parsed.hostname or "").lower()
    if not host or port is None:
        raise ScraperPermanentError(f"Invalid LinkedIn proxy on line {line_number}")
    if host in _LOCAL_PROXY_HOSTS:
        raise ScraperPermanentError(
            f"LinkedIn proxy host {host} is not allowed (line {line_number})"
        )


def redact_proxy_secrets(message: str, proxies: Sequence[str]) -> str:
    """Replace known proxy URLs and credentials with a host-only marker."""
    redacted = str(message)
    for proxy in proxies:
        candidate = proxy if "://" in proxy else f"http://{proxy}"
        try:
            parsed = urlsplit(candidate)
            host = parsed.hostname or "hidden"
            port = parsed.port
        except ValueError:
            host, port, parsed = "hidden", None, None
        marker = f"<proxy:{host}{f':{port}' if port else ''}>"
        redacted = redacted.replace(proxy, marker).replace(candidate, marker)
        if parsed is not None:
            for secret in (parsed.username, parsed.password):
                if secret:
                    redacted = redacted.replace(secret, "***")
                    redacted = redacted.replace(unquote(secret), "***")
    return redacted


def job_from_row(row: Mapping[str, Any]) -> Job | None:
    """Convert one JobSpy record into forkjob's source-independent Job model."""
    title = _text(row.get("title"))
    direct_url = _text(row.get("job_url_direct"))
    linkedin_url = _text(row.get("job_url"))
    url = direct_url or linkedin_url
    if not title or not url:
        return None

    description = html_to_text(_text(row.get("description")))
    location = _text(row.get("location"))
    location_info = parse_location(location, description=description)
    remote_value = _boolean(row.get("is_remote"))
    if remote_value is True:
        work_mode = WorkMode.REMOTE
        remote: bool | None = True
    elif remote_value is False:
        work_mode = location_info.work_mode
        remote = False
    else:
        work_mode = location_info.work_mode
        remote = True if work_mode is WorkMode.REMOTE else None

    posted_at = _datetime(row.get("date_posted"))
    external_id = _text(row.get("id")) or _linkedin_id(linkedin_url)
    department = (
        " | ".join(
            value
            for value in (
                _text(row.get("job_function")),
                _text(row.get("job_level")),
            )
            if value
        )
        or None
    )

    return Job.build(
        url=url,
        source="linkedin",
        layer=Layer.B,
        company=_text(row.get("company")) or "?",
        title=title,
        external_id=external_id,
        location=location,
        city=location_info.city,
        country=location_info.country,
        region=location_info.region,
        remote=remote,
        work_mode=work_mode,
        department=department,
        description=description,
        salary=_salary(row),
        posted_at=posted_at,
        date_source=DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED,
    )


def _clean(value: Any) -> Any | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if type(value).__name__ in {"NAType", "NaTType"}:
        return None
    return value


def _text(value: Any) -> str | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    text = str(cleaned).strip()
    return text or None


def _boolean(value: Any) -> bool | None:
    cleaned = _clean(value)
    if isinstance(cleaned, bool):
        return cleaned
    if isinstance(cleaned, (int, float)):
        return bool(cleaned)
    if isinstance(cleaned, str):
        lowered = cleaned.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return None


def _datetime(value: Any) -> datetime | None:
    cleaned = _clean(value)
    if isinstance(cleaned, datetime):
        return cleaned if cleaned.tzinfo else cleaned.replace(tzinfo=UTC)
    if isinstance(cleaned, date):
        return datetime.combine(cleaned, time.min, tzinfo=UTC)
    if isinstance(cleaned, str):
        return parse_datetime(cleaned)
    return None


def _linkedin_id(url: str | None) -> str | None:
    match = _LINKEDIN_ID_RE.search(url or "")
    return match.group(1) if match else None


def _salary(row: Mapping[str, Any]) -> str | None:
    low = _number(row.get("min_amount"))
    high = _number(row.get("max_amount"))
    if low is None and high is None:
        return None
    currency = _text(row.get("currency")) or ""
    interval = _text(row.get("interval"))
    if low is not None and high is not None and low != high:
        amount = f"{low:g}-{high:g}"
    else:
        amount = f"{(low if low is not None else high):g}"
    prefix = f"{currency} " if currency else ""
    suffix = f"/{interval}" if interval else ""
    return f"{prefix}{amount}{suffix}"


def _number(value: Any) -> float | None:
    cleaned = _clean(value)
    if isinstance(cleaned, bool):
        return None
    if isinstance(cleaned, (int, float)):
        return float(cleaned)
    try:
        return float(str(cleaned)) if cleaned is not None else None
    except (TypeError, ValueError):
        return None


def _merge_user_profiles(defaults: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Append user-defined LinkedIn search profiles to the defaults.

    Load errors are swallowed — a missing or malformed profiles file must never
    block a sync. Defaults alone are the safe fallback.
    """
    try:
        user = LinkedInProfiles.load()
    except Exception:
        return defaults
    if not user.profiles:
        return defaults
    return user.merge_with_defaults(defaults)
