"""Layer B scrapers — job portals and tech boards.

Layer B is deliberately separate from Layer A. A broken HTML scraper must never
affect the ATS adapters, and the sync orchestrator treats every Layer B source
as its own failure domain.

What lives here:
  base.py        Rate-limited HTTP, robots.txt, response caching, mock replay,
                 and the ScraperBase/ScrapeBatch contracts every scraper shares.
  index.py       Registry key -> scraper class, discovered automatically.
  registry.py    Layer B source registry (data/portals.yaml).
  schemaorg.py   Shared schema.org ld+json / microdata helpers.
  <name>.py      One scraper per source (see the module docstrings).
  blocked.py     Sources assessed and found blocked — honest _BlockedScraper
                 subclasses that raise rather than fake an empty result.
"""

from .base import (
    CacheMode,
    RobotsPolicy,
    ScraperBase,
    ScraperError,
    ScraperHttpClient,
    ScraperPermanentError,
    ScraperTransientError,
)
from .registry import LayerBRegistry, LayerBSource, load_registry_b

__all__ = [
    "CacheMode",
    "LayerBRegistry",
    "LayerBSource",
    "RobotsPolicy",
    "ScraperBase",
    "ScraperError",
    "ScraperHttpClient",
    "ScraperPermanentError",
    "ScraperTransientError",
    "load_registry_b",
]
