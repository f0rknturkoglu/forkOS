from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import runs
from app.core.events import log_event
from app.core.models import Event
from app.integrations.models import OAuthToken
from app.modules.project.models import GithubActivity, Project
from app.sources.github import GithubSource


async def sync(session: AsyncSession) -> int:
    credentials = await session.get(OAuthToken, "github")
    if credentials is None or not credentials.scopes:
        raise RuntimeError("GitHub bağlı değil")
    run = await runs.start_run(session, "github")
    try:
        items = await GithubSource(credentials.access_token, credentials.scopes).fetch()
        commits = 0
        for item in items:
            if item.extra["kind"] == "contribution":
                await session.execute(
                    insert(GithubActivity)
                    .values(
                        day=date.fromisoformat(item.title),
                        repo="_all",
                        commit_count=item.extra["count"],
                    )
                    .on_conflict_do_update(
                        index_elements=[GithubActivity.day, GithubActivity.repo],
                        set_={"commit_count": item.extra["count"]},
                    )
                )
                continue
            oid = item.extra["oid"]
            exists = (
                await session.execute(
                    select(Event.id).where(
                        Event.verb == "github.commit", Event.payload["oid"].astext == oid
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                continue
            repo = item.extra["repo"]
            await log_event(
                session,
                verb="github.commit",
                entity_type="project",
                payload={
                    "oid": oid,
                    "repo": repo,
                    "message": item.title,
                    "url": item.url,
                    "committed_at": item.published_at.isoformat() if item.published_at else None,
                },
            )
            projects = list(
                (
                    await session.execute(select(Project).where(Project.github_repo == repo))
                ).scalars()
            )
            for project in projects:
                project.last_activity_at = item.published_at or datetime.now(UTC)
            commits += 1
        await runs.finish_run(session, run, status=runs.OK, items_found=commits)
        await session.commit()
        return commits
    except Exception as exc:
        await runs.finish_run(session, run, status=runs.ERROR, error=str(exc))
        await session.commit()
        raise
