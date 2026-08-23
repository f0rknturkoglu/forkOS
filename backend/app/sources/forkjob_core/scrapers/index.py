"""Layer B scraper index — maps source keys to scraper classes.

Import errors are contained here on purpose: Layer B is the fragile half, and
one broken scraper file must never stop the others from loading, let alone
break a Layer A sync. What is *not* done here is swallowing the reason — a
failure is recorded and reported, because a scraper that vanishes silently is
indistinguishable from one that found nothing.
"""

from __future__ import annotations

import importlib
from dataclasses import fields, replace
from typing import Any

from .base import ScraperBase, ScraperConfig
from .registry import LayerBSource

#: Why a scraper failed to build, keyed by source. Surfaced by sync so a
#: bad config line is reported instead of silently skipping the source.
_CONSTRUCTION_ERRORS: dict[str, str] = {}

#: source key -> (class or None, reason it is unavailable)
_REGISTRY: dict[str, tuple[type[ScraperBase] | None, str]] = {}

_MODULES = [
    ("app.sources.forkjob_core.scrapers.manfred", "ManfredScraper", "manfred"),
    ("app.sources.forkjob_core.scrapers.kariyernet", "KariyerNetScraper", "kariyernet"),
    ("app.sources.forkjob_core.scrapers.arbeitnow", "ArbeitnowScraper", "arbeitnow"),
    ("app.sources.forkjob_core.scrapers.bebee", "BebeeScraper", "bebee"),
    ("app.sources.forkjob_core.scrapers.linkedin", "LinkedInScraper", "linkedin"),
    ("app.sources.forkjob_core.scrapers.jobfluent", "JobFluentScraper", "jobfluent"),
    ("app.sources.forkjob_core.scrapers.tecnoempleo", "TecnoempleoScraper", "tecnoempleo"),
    ("app.sources.forkjob_core.scrapers.ticjob", "TicjobScraper", "ticjob"),
    ("app.sources.forkjob_core.scrapers.jobicy", "JobicyScraper", "jobicy"),
    ("app.sources.forkjob_core.scrapers.remoteok", "RemoteOkScraper", "remoteok"),
    ("app.sources.forkjob_core.scrapers.eures", "EuresScraper", "eures"),
    ("app.sources.forkjob_core.scrapers.jobgether", "JobgetherScraper", "jobgether"),
    ("app.sources.forkjob_core.scrapers.remotive", "RemotiveScraper", "remotive"),
    ("app.sources.forkjob_core.scrapers.himalayas", "HimalayasScraper", "himalayas"),
    ("app.sources.forkjob_core.scrapers.justjoinit", "JustJoinItScraper", "justjoinit"),
    ("app.sources.forkjob_core.scrapers.pending", "RemoteRocketshipScraper", "remoterocketship"),
    ("app.sources.forkjob_core.scrapers.eurotechjobs", "EuroTechJobsScraper", "eurotechjobs"),
    (
        "app.sources.forkjob_core.scrapers.wearedevelopers",
        "WeAreDevelopersScraper",
        "wearedevelopers",
    ),
    ("app.sources.forkjob_core.scrapers.weworkremotely", "WeWorkRemotelyScraper", "weworkremotely"),
    ("app.sources.forkjob_core.scrapers.wellfound", "WellfoundScraper", "wellfound"),
    ("app.sources.forkjob_core.scrapers.devitjobs", "DevITJobsScraper", "devitjobs"),
    ("app.sources.forkjob_core.scrapers.workingnomads", "WorkingNomadsScraper", "workingnomads"),
    ("app.sources.forkjob_core.scrapers.nofluffjobs", "NoFluffJobsScraper", "nofluffjobs"),
    ("app.sources.forkjob_core.scrapers.relocateme", "RelocateMeScraper", "relocateme"),
    ("app.sources.forkjob_core.scrapers.landingjobs", "LandingJobsScraper", "landingjobs"),
    ("app.sources.forkjob_core.scrapers.honeypot", "HoneypotScraper", "honeypot"),
    ("app.sources.forkjob_core.scrapers.offerzen", "OfferZenScraper", "offerzen"),
    ("app.sources.forkjob_core.scrapers.hackernews", "HackerNewsScraper", "hackernews"),
    ("app.sources.forkjob_core.scrapers.jobspresso", "JobspressoScraper", "jobspresso"),
    ("app.sources.forkjob_core.scrapers.jobtech", "JobTechScraper", "jobtech"),
    ("app.sources.forkjob_core.scrapers.customfeeds", "CustomFeedsScraper", "customfeeds"),
    ("app.sources.forkjob_core.scrapers.consider", "ConsiderScraper", "consider-sequoia"),
    ("app.sources.forkjob_core.scrapers.consider", "ConsiderScraper", "consider-a16z"),
    ("app.sources.forkjob_core.scrapers.gulftalent", "GulfTalentScraper", "gulftalent"),
    ("app.sources.forkjob_core.scrapers.fourdayweek", "FourDayWeekScraper", "fourdayweek"),
    ("app.sources.forkjob_core.scrapers.solidjobs", "SolidJobsScraper", "solidjobs"),
    ("app.sources.forkjob_core.scrapers.bulldogjob", "BulldogjobScraper", "bulldogjob"),
    ("app.sources.forkjob_core.scrapers.arcdev", "ArcDevScraper", "arcdev"),
    ("app.sources.forkjob_core.scrapers.freelancermap", "FreelancermapScraper", "freelancermap"),
    ("app.sources.forkjob_core.scrapers.web3career", "Web3CareerScraper", "web3career"),
    (
        "app.sources.forkjob_core.scrapers.realworkfromanywhere",
        "RealWorkFromAnywhereScraper",
        "realworkfromanywhere",
    ),
    ("app.sources.forkjob_core.scrapers.dailyremote", "DailyRemoteScraper", "dailyremote"),
    ("app.sources.forkjob_core.scrapers.javascriptjobs", "JavascriptJobsScraper", "javascriptjobs"),
    ("app.sources.forkjob_core.scrapers.dynamitejobs", "DynamiteJobsScraper", "dynamitejobs"),
    ("app.sources.forkjob_core.scrapers.blocked", "CryptoJobsListScraper", "cryptojobslist"),
    ("app.sources.forkjob_core.scrapers.blocked", "RubyOnRemoteScraper", "rubyonremote"),
    ("app.sources.forkjob_core.scrapers.blocked", "NodeskScraper", "nodesk"),
]


def _load(module_name: str, class_name: str) -> tuple[type[ScraperBase] | None, str]:
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        return None, f"import {module_name} failed: {type(exc).__name__}: {exc}"
    scraper_cls = getattr(module, class_name, None)
    if scraper_cls is None:
        return None, f"{module_name} has no {class_name}"
    return scraper_cls, ""


for _module, _class, _key in _MODULES:
    _REGISTRY[_key] = _load(_module, _class)


def get_scraper(source: LayerBSource, config: ScraperConfig | None = None) -> ScraperBase | None:
    """Instantiate a scraper for a registry entry, or None if unavailable.

    Per-source settings from portals.yaml (`config:`) are passed through as
    keyword arguments when the scraper accepts them — that is how Manfred gets
    its `max_offers` budget.
    """
    entry = _REGISTRY.get(source.key)
    if entry is None:
        return None
    scraper_cls, _reason = entry
    if scraper_cls is None:
        return None

    kwargs: dict[str, Any] = dict(source.config or {})

    # Transport settings belong to ScraperConfig, not to the scraper's own
    # constructor. Without this split they land in **kwargs, raise TypeError
    # and get silently dropped — which is how EURES would have been polled
    # every 2s when its robots.txt asks for 10.
    transport = {f.name for f in fields(ScraperConfig)}
    overrides = {k: kwargs.pop(k) for k in list(kwargs) if k in transport}
    if overrides:
        base = config or ScraperConfig()
        config = replace(base, **overrides)

    try:
        return scraper_cls(config=config, **kwargs)
    except TypeError:
        # Scraper does not take these settings — better a working scraper on
        # defaults than none at all.
        try:
            return scraper_cls(config=config)
        except Exception as exc:
            _CONSTRUCTION_ERRORS[source.key] = f"{type(exc).__name__}: {exc}"
            return None
    except Exception as exc:
        # Recorded rather than swallowed. A silent None here meant sync just
        # skipped the source: an unquoted `no` in the EURES country list became
        # the boolean False, crashed the constructor, and the whole source
        # vanished from the run without a word.
        _CONSTRUCTION_ERRORS[source.key] = f"{type(exc).__name__}: {exc}"
        return None


def unavailable_reason(key: str) -> str:
    """Why a key has no usable scraper. Empty string means it is fine."""
    if key in _CONSTRUCTION_ERRORS:
        return f"config rejected by the scraper — {_CONSTRUCTION_ERRORS[key]}"
    entry = _REGISTRY.get(key)
    if entry is None:
        return f"{key} is not registered"
    return entry[1]


def available_scrapers() -> list[str]:
    """Keys whose scraper class imported successfully."""
    return [key for key, (cls, _) in _REGISTRY.items() if cls is not None]


def broken_scrapers() -> dict[str, str]:
    """Keys that failed to import, mapped to the reason."""
    return {key: reason for key, (cls, reason) in _REGISTRY.items() if cls is None}


def all_registered() -> list[str]:
    return list(_REGISTRY.keys())
