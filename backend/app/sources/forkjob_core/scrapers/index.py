"""Layer B scraper index — maps source keys to scraper classes.

Scraper classes are discovered, not listed: every module in this package is
imported and every `ScraperBase` subclass registers itself under
`cls.registry_keys` (or `(cls.source_key,)`). The old explicit module list
rotted — a renamed class or a deleted file silently dropped the source.

Import errors are contained here on purpose: Layer B is the fragile half, and
one broken scraper file must never stop the others from loading, let alone
break a Layer A sync. What is *not* done here is swallowing the reason — a
failure is recorded and reported, because a scraper that vanishes silently is
indistinguishable from one that found nothing. A module that fails to import
cannot say which source keys it owns, so the reason is recorded under the
module's own name.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import fields, replace
from typing import Any

from .base import ScraperBase, ScraperConfig
from .registry import LayerBSource

#: Why a scraper failed to build, keyed by source. Surfaced by sync so a
#: bad config line is reported instead of silently skipping the source.
_CONSTRUCTION_ERRORS: dict[str, str] = {}

#: source key -> (class or None, reason it is unavailable)
_REGISTRY: dict[str, tuple[type[ScraperBase] | None, str]] = {}

#: Modules that are scaffolding, not scrapers.
_SKIP_MODULES = frozenset({"base", "index", "__init__"})


def _scraper_classes(module: Any) -> list[type[ScraperBase]]:
    """Every ScraperBase subclass defined in a module, in definition order."""
    return [
        obj
        for obj in vars(module).values()
        if isinstance(obj, type) and issubclass(obj, ScraperBase) and obj is not ScraperBase
    ]


def _discover() -> None:
    """Import every module in this package and register its scraper classes.

    A module with no ScraperBase subclass (e.g. schemaorg.py) registers
    nothing. A module that fails to import keeps the (None, reason) contract
    under its module name — the only key knowable before the import runs.
    """
    package = importlib.import_module(__package__)
    for info in pkgutil.iter_modules(package.__path__):
        if info.name in _SKIP_MODULES:
            continue
        module_name = f"{__package__}.{info.name}"
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            _REGISTRY[info.name] = (
                None,
                f"import {module_name} failed: {type(exc).__name__}: {exc}",
            )
            continue
        for scraper_cls in _scraper_classes(module):
            for key in scraper_cls.registry_keys or (scraper_cls.source_key,):
                if key:
                    _REGISTRY[key] = (scraper_cls, "")


_discover()


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
        scraper = scraper_cls(config=config, **kwargs)
    except TypeError:
        # Scraper does not take these settings — better a working scraper on
        # defaults than none at all.
        try:
            scraper = scraper_cls(config=config)
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

    # A registry entry without a base URL gets the portal's own URL — the
    # scraper needs it for robots.txt and reporting.
    if not scraper.base_url and source.url:
        scraper.base_url = source.url
    return scraper


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
