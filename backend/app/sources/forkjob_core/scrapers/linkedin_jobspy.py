"""Retained killable JobSpy fallback; live acquisition obeys LinkedIn robots."""

from __future__ import annotations

import asyncio
import importlib
import json
import math
import os
import re
import signal
import sys
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from app.sources.base import ScrapeTelemetry, env_flag

from ..linkedin_profiles import LinkedInProfiles
from ..models import Job, Layer, WorkMode, canonical_url, date_source_for
from ..normalize import html_to_text, parse_datetime, parse_location
from ..rich_text import enrich
from .base import (
    ScrapeBatch,
    ScraperConfig,
    ScraperHttpClient,
    ScraperPermanentError,
)
from .linkedin_types import LinkedInTransportResult

_LINKEDIN_ID_RE = re.compile(r"/jobs/view/(\d+)")
_ALLOWED_PROXY_SCHEMES = frozenset({"http", "https", "socks4", "socks5"})
_LOCAL_PROXY_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


@dataclass(slots=True)
class LinkedInConfig:
    """Secret-safe connection settings for the LinkedIn source."""

    proxy_file_env: str = "FORKJOB_LINKEDIN_PROXIES_FILE"
    allow_direct: bool = False


#: Direct (proxy'siz) LinkedIn erisimi icin ortam degiskenleri. Kanonik ad
#: `FORKJOB_` onekini tasir; eski `LINKEDIN_` adlari mevcut `.env` dosyalari
#: bozulmasin diye okunmaya devam eder. Varsayilan KAPALI: bu bir guvenlik
#: anahtaridir, yanlislikla acilmamali.
_ALLOW_DIRECT_ENV = ("FORKJOB_LINKEDIN_ALLOW_DIRECT", "LINKEDIN_ALLOW_DIRECT")
_PROXY_FILE_ENV = ("FORKJOB_LINKEDIN_PROXIES_FILE", "LINKEDIN_PROXIES_FILE")


def resolve_linkedin_config(
    *,
    proxy_file_env: str = "FORKJOB_LINKEDIN_PROXIES_FILE",
    allow_direct: bool | None = None,
    environ: Mapping[str, str] | None = None,
) -> LinkedInConfig:
    """Ortam degiskenlerinden LinkedIn baglanti ayarini coz.

    Acikca verilen `allow_direct` kazanir (testler ve cagiran kod icin);
    verilmezse `FORKJOB_LINKEDIN_ALLOW_DIRECT` okunur ve yoksa KAPALI kalir.
    """
    env = os.environ if environ is None else environ
    resolved_proxy_env = proxy_file_env
    for name in _PROXY_FILE_ENV:
        if env.get(name):
            resolved_proxy_env = name
            break
    if allow_direct is None:
        raw = next((env[name] for name in _ALLOW_DIRECT_ENV if name in env), None)
        allow_direct = env_flag(raw, default=False)
    return LinkedInConfig(proxy_file_env=resolved_proxy_env, allow_direct=bool(allow_direct))


class LinkedInJobSpyTransport:
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
        allow_direct: bool | None = None,
        ca_cert_env: str = "FORKJOB_LINKEDIN_CA_CERT",
        user_agent_env: str = "FORKJOB_LINKEDIN_USER_AGENT",
        runner: Callable[..., Any] | None = None,
    ) -> None:
        self.config = config or ScraperConfig()
        self.searches = [dict(search) for search in (searches or [])]
        # Merge user-defined profiles from data/linkedin-profiles.yaml.
        # Profile merging belongs to the single-source facade.
        # `allow_direct` acikca verilmediyse ortamdan cozulur ve yoksa KAPALI
        # kalir: proxy'siz LinkedIn erisimi yanlislikla acilmamali.
        self.linkedin_config = resolve_linkedin_config(
            proxy_file_env=proxy_file_env, allow_direct=allow_direct
        )
        self.ca_cert_env = ca_cert_env
        self.user_agent_env = user_agent_env
        self._runner = runner

    def record_telemetry(self, **kwargs):
        self.telemetry = ScrapeTelemetry(**kwargs)
        return self.telemetry

    async def search(self, profiles, client, budget):
        self.searches = profiles
        self.budget = budget
        batch = await self.scrape(client)
        return LinkedInTransportResult(
            batch.jobs,
            batch.errors,
            batch.telemetry,
            "jobspy_v1",
            batch.attempted,
            batch.succeeded,
            batch.telemetry.metadata.get("failed_profiles", []),
        )

    async def scrape(self, client: ScraperHttpClient) -> ScrapeBatch:
        attempted = len(self.searches)
        if not attempted:
            telemetry = self.record_telemetry(
                items_seen=0,
                items_returned=0,
                pages_fetched=None,
                page_limit=None,
                result_limit=0,
                cap_hit=False,
                partial_reason=None,
                stop_reason="no_profiles",
                metadata={
                    "profiles_attempted": 0,
                    "profiles_succeeded": 0,
                    "profiles_failed": 0,
                },
            )
            return ScrapeBatch(
                jobs=[],
                errors=["LinkedIn has no configured search profiles"],
                attempted=0,
                succeeded=0,
                telemetry=telemetry,
            )
        # Report the actionable configuration failure before importing JobSpy.
        # A disabled source with no profiles must not be labelled a proxy error.
        proxies = load_proxies(self.linkedin_config, os.environ)
        if self._runner is None:
            _import_jobspy_runner()  # dependency check before the first child process
        runner = self._runner

        total_results_wanted = 0
        profile_cap_hit = False

        jobs: list[Job] = []
        errors: list[str] = []
        succeeded = 0
        failed_profiles = []
        for index, profile in enumerate(self.searches, start=1):
            name = _text(profile.get("name")) or f"profile-{index}"
            jobs_before = len(jobs)
            try:
                results_wanted = max(1, int(profile.get("results_wanted") or 50))
                total_results_wanted += results_wanted
                if getattr(self, "budget", None) and self.budget.remaining <= 0:
                    raise TimeoutError("run_budget_reached")
                kwargs = self._runner_kwargs(profile, proxies[:1])
                if runner is None:
                    records = await asyncio.wait_for(
                        _run_jobspy_isolated(kwargs),
                        timeout=min(180, self.budget.remaining)
                        if getattr(self, "budget", None)
                        else 180,
                    )
                else:
                    frame = await asyncio.to_thread(runner, **kwargs)
                    records = frame.to_dict(orient="records")
                warnings = 0
                if isinstance(records, dict):
                    warnings = records.get("warning_count", 0)
                    columns = records.get("columns", [])
                    if not {"title", "company", "job_url"} <= set(columns):
                        raise ValueError("JobSpy column contract is missing")
                    records = records.get("records")
                if not isinstance(records, list):
                    raise TypeError("JobSpy result is not record-oriented")
                for row in records:
                    if isinstance(row, Mapping):
                        job = job_from_row(row)
                        if job is not None:
                            jobs.append(job)
                            if len(jobs) - jobs_before >= results_wanted:
                                break
                if records and len(jobs) == jobs_before:
                    raise ValueError("JobSpy nonempty output has no valid LinkedIn identity rows")
                if warnings or not records:
                    raise ValueError("JobSpy warnings or unverified empty output")
                succeeded += 1
                if len(jobs) - jobs_before >= results_wanted:
                    profile_cap_hit = True
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                failed_profiles.append(index - 1)
                detail = redact_proxy_secrets(f"{type(exc).__name__}: {exc}", proxies)
                errors.append(f"{name}: {detail}")

        deduped = _deduplicate(jobs)
        cap_hit = profile_cap_hit or (
            total_results_wanted > 0 and len(deduped) >= total_results_wanted
        )
        partial_reason = None
        if errors and succeeded > 0:
            stop_reason = "some_profiles_failed"
            partial_reason = f"some_profiles_failed: {len(errors)} of {attempted} profiles failed"
        elif cap_hit:
            stop_reason = "profile_limit_reached"
            partial_reason = "profile_limit_reached: results_wanted reached"
        elif errors and succeeded == 0:
            stop_reason = "profile_errors"
            partial_reason = "all_profiles_failed"
        else:
            stop_reason = "exhausted"

        telemetry = self.record_telemetry(
            items_seen=len(jobs),
            items_returned=len(deduped),
            pages_fetched=None,
            page_limit=None,
            result_limit=total_results_wanted,
            cap_hit=cap_hit,
            partial_reason=partial_reason,
            stop_reason=stop_reason,
            metadata={
                "transport": "jobspy_v1",
                "jobspy_version": jobspy_version(),
                "failed_profiles": failed_profiles,
                "profiles_attempted": attempted,
                "profiles_succeeded": succeeded,
                "profiles_failed": len(errors),
            },
        )

        return ScrapeBatch(
            jobs=deduped,
            errors=errors,
            attempted=attempted,
            succeeded=succeeded,
            telemetry=telemetry,
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
        from .base import USER_AGENT

        user_agent = USER_AGENT
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


async def _run_jobspy_isolated(kwargs: Mapping[str, Any]) -> dict[str, Any]:
    """Run JobSpy in a killable process so source cancellation cannot leave a thread."""
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "app.sources.forkjob_core.scrapers.linkedin_runner",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        stdout, _ = await asyncio.wait_for(
            process.communicate(json.dumps(dict(kwargs)).encode("utf-8")),
            timeout=180,
        )
        if process.returncode != 0:
            raise RuntimeError(f"JobSpy subprocess exited with code {process.returncode}")
        records = json.loads(stdout)
        if not isinstance(records, (list, dict)):
            raise TypeError("JobSpy result is not record-oriented")
        return records
    finally:
        if process.returncode is None:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            await process.wait()


def _deduplicate(jobs: Sequence[Job]) -> list[Job]:
    from ..rich_text import merge_descriptions

    unique = []
    by_id, by_url = {}, {}
    for job in jobs:
        url = canonical_url(job.url)
        previous = by_id.get(job.external_id) or by_url.get(url)
        if previous:
            previous.description = merge_descriptions(previous.description, job.description)
            if not previous.salary:
                previous.salary = job.salary
        else:
            unique.append(job)
            by_id[job.external_id] = job
            by_url[url] = job
    return unique


def load_proxies(config: LinkedInConfig, environ: Mapping[str, str]) -> list[str]:
    """Load one proxy per line without ever echoing proxy credentials."""
    configured_path = (environ.get(config.proxy_file_env) or "").strip()
    if not configured_path:
        if config.allow_direct:
            return []
        raise ScraperPermanentError(
            f"LinkedIn proxy file is required when direct scraping is disabled; set {config.proxy_file_env}"
        )

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
    url = canonical_url(direct_url or linkedin_url) if direct_url or linkedin_url else None
    company = _text(row.get("company"))
    from .linkedin_parsing import linkedin_identity

    identity, fallback_url = linkedin_identity(linkedin_url)
    if not title or not company or not url or not fallback_url:
        return None
    if (
        urlsplit(url).scheme not in {"http", "https"}
        or not urlsplit(url).hostname
        or urlsplit(url).username
    ):
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
    external_id = identity or fallback_url
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
        company=company,
        title=title,
        external_id=external_id,
        location=location,
        city=location_info.city,
        country=location_info.country,
        region=location_info.region,
        remote=remote,
        work_mode=work_mode,
        department=department,
        description=enrich(
            description,
            "linkedin",
            {
                "Seniority": _text(row.get("job_level")),
                "Employment type": _text(row.get("job_type")),
                "Job function": _text(row.get("job_function")),
                "Industry": _text(row.get("company_industry")),
                "Application URL": direct_url,
            },
        ),
        salary=_salary(row),
        posted_at=posted_at,
        date_source=date_source_for(posted_at)[1],
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
    from .linkedin_parsing import linkedin_identity

    return linkedin_identity(url)[0]


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


def jobspy_version():
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("python-jobspy")
    except PackageNotFoundError:
        return None
