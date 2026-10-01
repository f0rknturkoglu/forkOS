"""Bounded enrichment for boards whose public details share JobPosting JSON-LD."""

from ..models import canonical_url, norm_text
from ..normalize import html_to_text
from ..rich_text import merge_descriptions
from .base import ScraperError, ScraperPermanentError
from .schemaorg import job_posting_nodes, organisation_name, schema_job, text


async def enrich_job_details(scraper, client, jobs, budget):
    succeeded = 0
    errors = []
    for job in jobs[:budget]:
        try:
            postings = job_posting_nodes(await client.get_html(job.url))
            posting = next((p for p in postings if norm_text(text(p.get("title"))) == norm_text(job.title)), None)
            if not posting or not text(posting.get("description")):
                raise ScraperPermanentError("missing/mismatched JobPosting detail")
            url = posting.get("@id") or posting.get("url")
            if isinstance(url, str) and canonical_url(url) != canonical_url(job.url):
                raise ScraperPermanentError("mismatched detail URL")
            body = html_to_text(posting["description"])
            detail = schema_job(posting, url=job.url, source=job.source, layer=job.layer,
                company=organisation_name(posting.get("hiringOrganization")) or job.company,
                title=job.title, external_id=job.external_id, location=job.location,
                country=job.country, region=job.region, work_mode=job.work_mode, description=body)
            job.description = merge_descriptions(job.description, detail.description, prefer_incoming=True)
            job.salary = detail.salary or job.salary
            if job.company == "?":
                job.company = detail.company
            succeeded += 1
        except (ScraperError, ValueError, TypeError) as exc:
            errors.append("detail: " + str(exc))
    scraper.errors.extend(errors)
    return {"detail_requests": min(len(jobs), budget), "details_succeeded": succeeded,
            "detail_budget": budget, "richness_partial": succeeded < len(jobs)}
