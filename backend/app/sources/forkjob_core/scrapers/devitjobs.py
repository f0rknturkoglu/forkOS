"""Netherlands TechJobs board, independently registered from DE/CH.

2026-10-01 local HTTP to robots, listing, RSS and jobsLight returns 403.
Keep disabled until transport works; retired /api/jobs does not mean the
current board is dead.
"""

from .techjobs_family import TechJobsFamilyScraper, TechJobsSiteSpec


class DevITJobsScraper(TechJobsFamilyScraper):
    source_key = "devitjobs"
    spec = TechJobsSiteSpec(
        source_key, "DevITJobs Netherlands", "devitjobs.nl", "NL", "Netherlands", "EUR"
    )
