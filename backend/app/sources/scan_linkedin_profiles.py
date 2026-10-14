"""Scan user-configured LinkedIn profiles and ingest jobs into forkOS opportunities."""

import asyncio
from jobspy import scrape_jobs

from app.db import SessionLocal
from app.core import runs
from app.modules.opportunity.service import ingest_jobs
from app.modules.opportunity.worker import NativeJob
from app.sources.forkjob_core.linkedin_profiles import LinkedInProfiles
from app.sources.forkjob_core.scrapers.linkedin_jobspy import job_from_row
from app.sources.forkjob_port import job_to_raw


async def scan_all_profiles():
    profiles_mgr = LinkedInProfiles.load()
    profiles = profiles_mgr.profiles
    if not profiles:
        print("No LinkedIn profiles configured.")
        return

    print(f"Starting LinkedIn scan for {len(profiles)} user-configured profiles...")

    all_native_jobs = []

    for idx, p in enumerate(profiles, start=1):
        term = p.term
        location = p.location or "Turkey"
        results_wanted = p.results_wanted or 50
        hours_old = p.hours_old or 720
        is_remote = p.is_remote
        fetch_desc = bool(p.fetch_description)

        print(f"[{idx}/{len(profiles)}] Scraping '{term}' (location: {location}, wanted: {results_wanted}, hours: {hours_old})...")
        try:
            kwargs = {
                "site_name": ["linkedin"],
                "search_term": term,
                "location": location,
                "results_wanted": results_wanted,
                "hours_old": hours_old,
                "linkedin_fetch_description": fetch_desc,
            }
            if is_remote is not None:
                kwargs["is_remote"] = is_remote

            jobs_df = scrape_jobs(**kwargs)
            profile_jobs = []
            if not jobs_df.empty:
                for _, row in jobs_df.iterrows():
                    j = job_from_row(row)
                    if j is not None:
                        profile_jobs.append(NativeJob(job_to_raw(j)))

            print(f"  -> Found {len(profile_jobs)} valid jobs for '{term}'.")
            all_native_jobs.extend(profile_jobs)
        except Exception as e:
            print(f"  -> Error scraping '{term}': {e}")

    # Deduplicate within batch by external_id or url
    unique_jobs = []
    seen = set()
    for nj in all_native_jobs:
        key = nj.external_id or nj.url
        if key not in seen:
            seen.add(key)
            unique_jobs.append(nj)

    print(f"\nTotal unique LinkedIn jobs collected: {len(unique_jobs)}")

    if unique_jobs:
        async with SessionLocal() as session:
            run = await runs.start_run(session, "forkjob_core:linkedin")
            added = await ingest_jobs(session, unique_jobs, "forkjob_core:linkedin")
            await runs.finish_run(
                session,
                run,
                status=runs.OK,
                items_found=len(unique_jobs),
            )
            await session.commit()
            print(f"Ingestion complete! Newly created opportunities: {added}, Total touched: {len(unique_jobs)}")
    else:
        print("No jobs found to ingest.")


if __name__ == "__main__":
    asyncio.run(scan_all_profiles())
