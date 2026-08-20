"""Layer B scrapers — Spanish job portals and tech boards.

Layer B is deliberately separate from Layer A. A broken HTML scraper must never
affect the ATS adapters, and the sync orchestrator treats every Layer B source
as its own failure domain.

What lives here:
  base.py        Rate-limited HTTP, robots.txt, response caching, mock replay.
  registry.py    Layer B source registry (data/portals.yaml).
  infojobs.py    InfoJobs REST API.
  manfred.py     Manfred REST API (structured tech jobs, salary transparency).
  jobfluent.py   JobFluent — HTML scraping.
  tecnoempleo.py Tecnoempleo — HTML scraping (TODO: selectors).
  ticjob.py      Ticjob Spain — HTML scraping (TODO: selectors).
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
from .registry import LayerBSource, LayerBRegistry, load_registry_b

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
